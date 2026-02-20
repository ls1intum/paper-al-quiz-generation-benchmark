"""Main benchmark runner implementation."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from ..evaluators.base import LLMProvider
from ..evaluators.factory import LLMProviderFactory
from ..evaluators.lm_studio import LMStudioProvider
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

        # Initialize evaluators
        self._init_evaluators()

        # Initialize metrics
        self._init_metrics()

    def _init_evaluators(self) -> None:
        """Initialize all configured LLM evaluators."""
        # Fail early for LM Studio prerequisites (env/server/model availability).
        LMStudioProvider.preflight(self.config.evaluators)

        for eval_name, eval_config in self.config.evaluators.items():
            try:
                evaluator = LLMProviderFactory.create(eval_config)
                self.evaluators[eval_name] = evaluator
                print(f"Initialized evaluator: {eval_name} ({eval_config.model})")
            except Exception as e:
                if eval_config.provider == "lm_studio":
                    raise RuntimeError(
                        f"Failed to initialize LM Studio evaluator '{eval_name}': {e}"
                    ) from e
                print(f"Warning: Failed to initialize evaluator {eval_name}: {e}")

    def _init_metrics(self) -> None:
        """Initialize all configured metrics."""
        for metric_config in self.config.get_enabled_metrics():
            try:
                metric = MetricRegistry.create(metric_config.name)
                self.metrics[metric_config.name] = metric
                print(f"Initialized metric: {metric_config.name} v{metric.version}")
            except Exception as e:
                print(f"Warning: Failed to initialize metric {metric_config.name}: {e}")

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
            print(f"Loading quizzes from {self.config.input_output.quiz_directory}...")
            quizzes = IOUtils.load_all_quizzes(self.config.input_output.quiz_directory)
            print(f"Loaded {len(quizzes)} quizzes")

        if not quizzes:
            raise ValueError("No quizzes to evaluate")

        # Load source texts if not provided
        if source_texts is None:
            source_texts = self._load_source_texts(quizzes)

        # Run benchmark for specified number of runs
        all_results = []
        for run_number in range(1, self.config.runs + 1):
            print(f"\n{'='*60}")
            print(f"Starting Run {run_number}/{self.config.runs}")
            print(f"{'='*60}")

            for quiz in quizzes:
                print(f"\nEvaluating quiz: {quiz.title} ({quiz.quiz_id})")
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
                    print(f"Warning: Failed to load source for {quiz.quiz_id}: {e}")
            else:
                print(f"Warning: Source file not found: {source_file}")

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
            print(f"    Error evaluating quiz: {e}")
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
            print(f"    Error evaluating question {question.question_id}: {e}")
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
                print(f"  Skipping {metric_config.name}: not initialized")
                continue

            # Run with each configured evaluator
            for evaluator_name in metric_config.evaluators:
                evaluator = self.evaluators.get(evaluator_name)
                if evaluator is None:
                    print(f"  Skipping evaluator {evaluator_name}: not initialized")
                    continue

                print(f"  Running {metric_config.name} with {evaluator_name}...")

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
