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
from ..models.instruction import QuizInstructions


class BenchmarkRunner:

    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.config_hash = ConfigLoader.hash_config(config)
        self.metrics: Dict[str, BaseMetric] = {}
        self.evaluators: Dict[str, LLMProvider] = {}
        self.logger = logging.getLogger(__name__)
        self._init_evaluators()
        self._init_metrics()

    def _init_evaluators(self) -> None:
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
        if quizzes is None:
            self.logger.info("Loading quizzes from %s...", self.config.input_output.quiz_directory)
            quizzes = IOUtils.load_all_quizzes(self.config.input_output.quiz_directory)
            self.logger.info("Loaded %s quizzes", len(quizzes))

        if not quizzes:
            raise ValueError("No quizzes to evaluate")

        if source_texts is None:
            source_texts = self._load_source_texts(quizzes)

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
        source_texts = {}
        source_dir = Path(self.config.input_output.source_directory)
        for quiz in quizzes:
            source_path = source_dir / quiz.source_material
            if source_path.exists():
                try:
                    # Check if it's a directory (folder with multiple lecture files)
                    if source_path.is_dir():
                        source_texts[quiz.quiz_id] = self._load_multiple_sources(source_path)
                        self.logger.info(
                            "Loaded source folder for quiz %s: %s", quiz.quiz_id, source_path
                        )
                    else:
                        # Single file
                        source_texts[quiz.quiz_id] = IOUtils.load_source_text(str(source_path))
                except Exception as e:
                    self.logger.warning("Failed to load source for %s: %s", quiz.quiz_id, e)
            else:
                self.logger.warning("Source path not found: %s", source_path)
        return source_texts

    def _load_multiple_sources(self, folder_path: Path) -> str:
        """Load and combine multiple source files from a folder.

        Args:
            folder_path: Path to folder containing source files

        Returns:
            Combined text from all source files, separated by headers

        """
        combined_text = ""
        loaded_files = []

        # Supported file extensions
        supported_extensions = {".md", ".pdf"}

        # Sort files for consistent ordering
        files = sorted(folder_path.rglob("*"))

        for file_path in files:
            if file_path.suffix.lower() in supported_extensions and file_path.is_file():
                try:
                    file_content = IOUtils.load_source_text(str(file_path))
                    # Add a header for each file so the LLM knows where content comes from
                    file_header = f"\n\n{'=' * 60}\n[Source: {file_path.name}]\n{'=' * 60}\n\n"
                    combined_text += file_header + file_content
                    loaded_files.append(file_path.name)
                except Exception as e:
                    self.logger.warning("Failed to load file %s: %s", file_path.name, e)

        if not loaded_files:
            raise ValueError(f"No supported source files found in {folder_path}")

        self.logger.info("Loaded %d source files from folder: %s", len(loaded_files), loaded_files)

        return combined_text

    def _evaluate_quiz_level(
        self,
        metric: BaseMetric,
        evaluator: LLMProvider,
        quiz: Quiz,
        source_text: Optional[str],
        parameters: Dict,
        instructions: Optional[QuizInstructions] = None,
    ) -> Optional[MetricResult]:
        try:
            result = metric.evaluate(
                quiz=quiz,
                source_text=source_text,
                llm_client=evaluator,
                instructions=instructions,
                **parameters,
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
        instructions: Optional[QuizInstructions] = None,
    ) -> Optional[MetricResult]:
        try:
            result = metric.evaluate(
                question=question,
                quiz=quiz,
                source_text=source_text,
                llm_client=evaluator,
                instructions=instructions,
                **parameters,
            )
            return MetricResult(
                metric_name=metric.name,
                metric_version=metric.version,
                score=result.score,
                evaluator_model=evaluator.model_name,
                quiz_id=quiz.quiz_id,
                question_id=question.question_id,
                parameters=parameters,
                raw_response=result.raw_response,
            )
        except Exception as e:
            self.logger.error("Error evaluating question %s: %s", question.question_id, e)
            return None

    @staticmethod
    def _check_difficulty_compliance(
        quiz_id: str,
        metric_results: List[MetricResult],
        instructions: Optional[QuizInstructions],
    ) -> Optional[float]:
        """Aggregate per-question difficulty scores and check against the requested band.

        Per-question scores are never modified. If the mean falls outside the
        requested band, a penalty proportional to the distance is applied to the
        mean to produce an adjusted quiz-level difficulty score.

        Returns the adjusted mean (or raw mean if no instructions / in band).
        """
        if not instructions or not instructions.difficulty:
            return None

        difficulty_scores = [r.score for r in metric_results if r.metric_name == "difficulty"]
        if not difficulty_scores:
            return None

        mean_difficulty = round(sum(difficulty_scores) / len(difficulty_scores), 1)
        bands = {
            "easy": (0.0, 40.0),
            "medium": (35.0, 65.0),
            "hard": (60.0, 100.0),
        }
        low, high = bands.get(str(instructions.difficulty), (0.0, 100.0))
        in_band = low <= mean_difficulty <= high

        if in_band:
            print(
                f"\n[Difficulty Compliance — {quiz_id}]"
                f"\n  Requested : {instructions.difficulty} (band {low}–{high})"
                f"\n  Mean score: {mean_difficulty}  ✓ within band"
                f"\n  Questions : {len(difficulty_scores)} scored"
                f"\n  Adjusted  : {mean_difficulty} (no penalty)"
            )
            return mean_difficulty

        # Distance outside the band as fraction of full scale, capped at 30pts
        distance = max(mean_difficulty - high, low - mean_difficulty)
        penalty = round(min(distance * 0.5, 30.0), 1)
        adjusted = round(max(0.0, min(100.0, mean_difficulty - penalty)), 1)

        print(
            f"\n[Difficulty Compliance — {quiz_id}]"
            f"\n  Requested : {instructions.difficulty} (band {low}–{high})"
            f"\n  Mean score: {mean_difficulty}  ✗ outside band by {distance:.1f} pts"
            f"\n  Penalty   : -{penalty} → adjusted mean = {adjusted}"
            f"\n  Questions : {len(difficulty_scores)} scored"
            f"\n  Note      : Quiz overall difficulty does not match the "
            f"'{instructions.difficulty}' instruction."
        )
        return adjusted

    def _evaluate_quiz(
        self, quiz: Quiz, source_text: Optional[str], run_number: int
    ) -> BenchmarkResult:
        started_at = datetime.now()
        metric_results = []

        instructions = IOUtils.load_instructions(
            quiz=quiz,
            instructions_dir=self.config.input_output.instructions_directory,
        )
        if instructions:
            self.logger.info("Instructions loaded for quiz %s", quiz.quiz_id)

        for metric_config in self.config.get_enabled_metrics():
            metric = self.metrics.get(metric_config.name)
            if metric is None:
                self.logger.warning("Skipping %s: metric not initialized", metric_config.name)
                continue

            for evaluator_name in metric_config.evaluators:
                evaluator = self.evaluators.get(evaluator_name)
                if evaluator is None:
                    self.logger.warning("Skipping evaluator %s: not initialized", evaluator_name)
                    continue

                self.logger.info("Running %s with %s...", metric_config.name, evaluator_name)

                if metric.scope == MetricScope.QUESTION_LEVEL:
                    for question in quiz.questions:
                        result = self._evaluate_question(
                            metric,
                            evaluator,
                            quiz,
                            question,
                            source_text,
                            metric_config.parameters,
                            instructions,
                        )
                        if result:
                            metric_results.append(result)
                else:
                    result = self._evaluate_quiz_level(
                        metric,
                        evaluator,
                        quiz,
                        source_text,
                        metric_config.parameters,
                        instructions,
                    )
                    if result:
                        metric_results.append(result)

        # ── Difficulty compliance: runs after ALL metrics, outside the loop ── #
        adjusted_difficulty = self._check_difficulty_compliance(
            quiz.quiz_id, metric_results, instructions
        )

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
            metadata={
                "quiz_title": quiz.title,
                "num_questions": quiz.num_questions,
                "instructions": instructions.model_dump() if instructions else None,
                "adjusted_difficulty": adjusted_difficulty,
            },
        )
