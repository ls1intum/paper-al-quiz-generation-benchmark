"""Main benchmark runner implementation."""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..evaluators.base import LLMProvider
from ..evaluators.factory import LLMProviderFactory
from ..evaluators.ollama import OllamaProvider
from ..metrics.base import BaseMetric, MetricScope
from ..metrics.registry import MetricRegistry
from ..models.config import BenchmarkConfig
from ..models.quiz import Quiz, QuizQuestion
from ..models.result import BenchmarkResult, MetricResult
from ..utils.config_loader import ConfigLoader
from ..utils.io import IOUtils


class BenchmarkRunner:
    """Orchestrates benchmark execution.

    This class manages the complete benchmark workflow:
    1. Load configuration
    2. Initialize evaluators and metrics
    3. Load quizzes and source materials
    4. Execute evaluations across multiple runs
    5. Save results
    """

    def __init__(self, config: BenchmarkConfig) -> None:
        """Initialize the benchmark runner.

        Args:
            config: Benchmark configuration
        """
        self.config = config
        self.config_hash = ConfigLoader.hash_config(config)
        self.metrics: Dict[str, BaseMetric] = {}
        self.evaluators: Dict[str, LLMProvider] = {}
        self.logger = logging.getLogger(__name__)

        # Initialize evaluators
        self._init_evaluators()

        # Initialize metrics
        self._init_metrics()

    def _init_evaluators(self) -> None:
        """Initialize all configured LLM evaluators."""
        # Fail early for Ollama prerequisites (env/server/model availability).
        OllamaProvider.preflight(self.config.evaluators)

        for eval_name, eval_config in self.config.evaluators.items():
            try:
                evaluator = LLMProviderFactory.create(eval_config)
                self.evaluators[eval_name] = evaluator
                self.logger.info("Initialized evaluator: %s (%s)", eval_name, eval_config.model)
            except Exception as e:
                if eval_config.provider == "ollama":
                    raise RuntimeError(
                        f"Failed to initialize Ollama evaluator '{eval_name}': {e}"
                    ) from e
                self.logger.warning("Failed to initialize evaluator %s: %s", eval_name, e)

    def _init_metrics(self) -> None:
        """Initialize all configured metrics."""
        for metric_config in self.config.get_enabled_metrics():
            try:
                metric = MetricRegistry.create(metric_config.name)
                self.metrics[metric_config.name] = metric
                self.logger.info("Initialized metric: %s v%s", metric_config.name, metric.version)
            except Exception as e:
                self.logger.warning("Failed to initialize metric %s: %s", metric_config.name, e)

    def run(
        self, quizzes: Optional[List[Quiz]] = None, source_texts: Optional[Dict[str, str]] = None
    ) -> List[BenchmarkResult]:
        """Execute the complete benchmark.

        Args:
            quizzes: List of quizzes to evaluate (if None, loads from config)
            source_texts: Dict mapping quiz_id to source text (if None, loads from config)

        Returns:
            List of all benchmark results
        """
        # Load quizzes if not provided
        if quizzes is None:
            self.logger.info("Loading quizzes from %s...", self.config.input_output.quiz_directory)
            quizzes = IOUtils.load_all_quizzes(self.config.input_output.quiz_directory)
            self.logger.info("Loaded %s quizzes", len(quizzes))

        if not quizzes:
            raise ValueError("No quizzes to evaluate")

        # Load source texts if not provided
        if source_texts is None:
            source_texts = self._load_source_texts(quizzes)

        # Run benchmark for specified number of runs
        all_results = []
        for run_number in range(1, self.config.runs + 1):
            self.logger.info("%s", "=" * 60)
            self.logger.info("Starting Run %s/%s", run_number, self.config.runs)
            self.logger.info("%s", "=" * 60)

            for quiz in quizzes:
                self.logger.info("Evaluating quiz: %s (%s)", quiz.title, quiz.quiz_id)
                result = self._evaluate_quiz(quiz, source_texts.get(quiz.quiz_id), run_number)
                all_results.append(result)

        return all_results

    def _load_source_texts(self, quizzes: List[Quiz]) -> Dict[str, str]:
        """Load source texts for quizzes.

        Args:
            quizzes: List of quizzes

        Returns:
            Dict mapping quiz_id to source text
        """
        source_texts = {}
        source_dir = Path(self.config.input_output.source_directory)

        for quiz in quizzes:
            source_file = source_dir / quiz.source_material
            if source_file.exists():
                try:
                    source_texts[quiz.quiz_id] = IOUtils.load_source_text(str(source_file))
                except Exception as e:
                    self.logger.warning("Failed to load source for %s: %s", quiz.quiz_id, e)
            else:
                self.logger.warning("Source file not found: %s", source_file)

        return source_texts

    def _evaluate_quiz_level(
        self,
        metric: BaseMetric,
        evaluator: LLMProvider,
        quiz: Quiz,
        source_text: Optional[str],
        parameters: Dict,
    ) -> Optional[MetricResult]:
        """Evaluate entire quiz with a metric."""
        try:
            # Metrics handle their own logic
            result = metric.evaluate(
                quiz=quiz, source_text=source_text, llm_client=evaluator, **parameters
            )

            return MetricResult(
                metric_name=metric.name,
                metric_version=metric.version,
                score=result.score,
                evaluator_model=evaluator.model_name,
                quiz_id=quiz.quiz_id,
                question_id=None,
                parameters=parameters,
                raw_response=result.raw_response,
            )

        except Exception as e:
            self.logger.error("Error evaluating quiz %s: %s", quiz.quiz_id, e)
            return None

    def _evaluate_question(
        self,
        metric: BaseMetric,
        evaluator: LLMProvider,
        quiz: Quiz,
        question: QuizQuestion,
        source_text: Optional[str],
        parameters: Dict,
    ) -> Optional[MetricResult]:
        """Evaluate a single question with a metric."""
        try:
            # Metrics handle their own logic
            result = metric.evaluate(
                question=question,
                quiz=quiz,
                source_text=source_text,
                llm_client=evaluator,
                **parameters,
            )

            return MetricResult(
                metric_name=metric.name,
                metric_version=metric.version,
                score=result.score,  # Extract score
                evaluator_model=evaluator.model_name,
                quiz_id=quiz.quiz_id,
                question_id=question.question_id,
                parameters=parameters,
                raw_response=result.raw_response,  # Extract raw_response
            )

        except Exception as e:
            self.logger.error("Error evaluating question %s: %s", question.question_id, e)
            return None

    def _evaluate_quiz(
        self, quiz: Quiz, source_text: Optional[str], run_number: int
    ) -> BenchmarkResult:
        """Evaluate a single quiz with all configured metrics.

        Args:
            quiz: Quiz to evaluate
            source_text: Source material text
            run_number: Current run number

        Returns:
            BenchmarkResult with all metric results
        """
        started_at = datetime.now()
        metric_results = []

        # Process each configured metric
        for metric_config in self.config.get_enabled_metrics():
            metric = self.metrics.get(metric_config.name)
            if metric is None:
                self.logger.warning("Skipping %s: metric not initialized", metric_config.name)
                continue

            # Run with each configured evaluator
            for evaluator_name in metric_config.evaluators:
                evaluator = self.evaluators.get(evaluator_name)
                if evaluator is None:
                    self.logger.warning("Skipping evaluator %s: not initialized", evaluator_name)
                    continue

                self.logger.info("Running %s with %s...", metric_config.name, evaluator_name)

                # Evaluate based on metric scope
                if metric.scope == MetricScope.QUESTION_LEVEL:
                    # Evaluate each question
                    for question in quiz.questions:
                        result = self._evaluate_question(
                            metric, evaluator, quiz, question, source_text, metric_config.parameters
                        )
                        if result:
                            metric_results.append(result)
                else:  # QUIZ_LEVEL
                    # Evaluate entire quiz
                    result = self._evaluate_quiz_level(
                        metric, evaluator, quiz, source_text, metric_config.parameters
                    )
                    if result:
                        metric_results.append(result)

        completed_at = datetime.now()

        return BenchmarkResult(
            benchmark_id=str(uuid.uuid4()),
            benchmark_version=self.config.version,
            config_hash=self.config_hash,
            quiz_id=quiz.quiz_id,
            run_number=run_number,
            metrics=metric_results,
            started_at=started_at,
            completed_at=completed_at,
            metadata={"quiz_title": quiz.title, "num_questions": quiz.num_questions},
        )
