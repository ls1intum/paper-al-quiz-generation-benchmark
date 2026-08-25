"""Main benchmark runner implementation."""

import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

from ..evaluators.base import LLMProvider, TransientLLMError
from ..evaluators.factory import LLMProviderFactory
from ..evaluators.ollama import OllamaProvider
from ..metrics.base import BaseMetric, MetricScope
from ..metrics.registry import MetricRegistry
from ..models.config import BenchmarkConfig
from ..models.instruction import QuizInstructions
from ..models.quiz import Quiz, QuizQuestion
from ..models.result import BenchmarkResult, EvaluationResult, MetricResult
from ..utils.config_loader import ConfigLoader
from ..utils.io import IOUtils

logger = logging.getLogger(__name__)


class BenchmarkRunner:

    def __init__(self, config: BenchmarkConfig) -> None:
        self.config = config
        self.config_hash = ConfigLoader.hash_config(config)
        self.metrics: dict[str, BaseMetric] = {}
        self.evaluators: dict[str, LLMProvider] = {}
        self.logger = logging.getLogger(__name__)
        self._attempted: int = 0
        self._cell_failures: list[dict] = []
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
                # Fail loud for every provider, not just ollama. A declared evaluator that is
                # silently skipped means a sweep completes with fewer judges than planned, and
                # that only surfaces by reading metadata.json afterwards -- by which point tens
                # of thousands of calls have been spent. To exclude a model, remove it from the
                # config; the per-model configs make that trivial.
                raise RuntimeError(
                    f"Failed to initialize evaluator '{eval_name}' "
                    f"(provider={eval_config.provider}, model={eval_config.model}): {e}. "
                    f"Remove it from the config if the omission is intended."
                ) from e

    def _init_metrics(self) -> None:
        for metric_config in self.config.get_enabled_metrics():
            try:
                metric = MetricRegistry.create(metric_config.name)
                self.metrics[metric_config.name] = metric
                self.logger.info("Initialized metric: %s v%s", metric_config.name, metric.version)
            except Exception as e:  # noqa: BLE001
                self.logger.warning("Failed to initialize metric %s: %s", metric_config.name, e)

    def run(
        self, quizzes: list[Quiz] | None = None, source_texts: dict[str, str] | None = None
    ) -> list[BenchmarkResult]:
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

    def _load_source_texts(self, quizzes: list[Quiz]) -> dict[str, str]:
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
                except Exception as e:  # noqa: BLE001
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
                except Exception as e:  # noqa: BLE001
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
        source_text: str | None,
        parameters: dict,
        instructions: QuizInstructions | None = None,
    ) -> tuple[EvaluationResult, MetricResult] | None:
        self._attempted += 1
        try:
            evaluator.reset_usage()
            result = metric.evaluate(
                quiz=quiz,
                source_text=source_text,
                llm_client=evaluator,
                instructions=instructions,
                **parameters,
            )
            usage = evaluator.get_accumulated_usage()
            return result, MetricResult(
                metric_name=metric.name,
                metric_version=metric.version,
                score=result.score,
                evaluator_model=evaluator.model_name,
                quiz_id=quiz.quiz_id,
                question_id=None,
                parameters=parameters,
                raw_response=result.raw_response,
                usage=usage,
            )
        except TransientLLMError as e:
            self.logger.error("Transient failure evaluating quiz %s: %s", quiz.quiz_id, e)
            self._cell_failures.append({
                "category": "transient",
                "metric": metric.name,
                "evaluator": evaluator.model_name,
                "quiz_id": quiz.quiz_id,
                "question_id": None,
                "error": str(e),
            })
            return None
        except Exception as e:  # noqa: BLE001
            self.logger.error("Error evaluating quiz %s: %s", quiz.quiz_id, e)
            self._cell_failures.append({
                "category": "skipped",
                "metric": metric.name,
                "evaluator": evaluator.model_name,
                "quiz_id": quiz.quiz_id,
                "question_id": None,
                "error": str(e),
            })
            return None

    def _expand_quiz_result(
        self,
        metric: BaseMetric,
        result: EvaluationResult,
        evaluator: LLMProvider,
        quiz: Quiz,
        parameters: dict,
        usage: dict[str, int] | None = None,
    ) -> list[MetricResult]:
        """Split a quiz-level result into per-question rows, when the metric has them.

        Metrics that judge each question internally expose those judgements via
        expand_question_results. Returning them as separate rows is what makes
        the scores joinable per question; an empty list means the caller keeps
        the quiz-level row as-is.
        """
        try:
            return [
                MetricResult(
                    metric_name=metric.name,
                    metric_version=metric.version,
                    score=score,
                    evaluator_model=evaluator.model_name,
                    quiz_id=quiz.quiz_id,
                    question_id=question_id,
                    parameters=parameters,
                    raw_response=raw_response,
                    usage=usage,
                )
                for question_id, score, raw_response in metric.expand_question_results(result)
            ]
        except Exception as e:  # noqa: BLE001
            self.logger.error("Error expanding %s for quiz %s: %s", metric.name, quiz.quiz_id, e)
            return []

    def _evaluate_question(
        self,
        metric: BaseMetric,
        evaluator: LLMProvider,
        quiz: Quiz,
        question: QuizQuestion,
        source_text: str | None,
        parameters: dict,
        instructions: QuizInstructions | None = None,
    ) -> tuple[MetricResult, dict] | None:
        self._attempted += 1
        try:
            evaluator.reset_usage()
            result = metric.evaluate(
                question=question,
                quiz=quiz,
                source_text=source_text,
                llm_client=evaluator,
                instructions=instructions,
                **parameters,
            )
            usage = evaluator.get_accumulated_usage()
            metric_result = MetricResult(
                metric_name=metric.name,
                metric_version=metric.version,
                score=result.score,
                evaluator_model=evaluator.model_name,
                quiz_id=quiz.quiz_id,
                question_id=question.question_id,
                parameters=parameters,
                raw_response=result.raw_response,
                usage=usage,
            )
            return metric_result, result.metadata.get("phases", {})
        except TransientLLMError as e:
            self.logger.error(
                "Transient failure evaluating question %s: %s", question.question_id, e
            )
            self._cell_failures.append({
                "category": "transient",
                "metric": metric.name,
                "evaluator": evaluator.model_name,
                "quiz_id": quiz.quiz_id,
                "question_id": question.question_id,
                "error": str(e),
            })
            return None
        except Exception as e:  # noqa: BLE001
            self.logger.error("Error evaluating question %s: %s", question.question_id, e)
            self._cell_failures.append({
                "category": "skipped",
                "metric": metric.name,
                "evaluator": evaluator.model_name,
                "quiz_id": quiz.quiz_id,
                "question_id": question.question_id,
                "error": str(e),
            })
            return None

    def get_completeness_report(self) -> dict:
        failed = [c for c in self._cell_failures if c["category"] == "transient"]
        skipped = [c for c in self._cell_failures if c["category"] == "skipped"]
        present = self._attempted - len(self._cell_failures)
        return {
            "expected": self._attempted,
            "present": present,
            "skipped": len(skipped),
            "failed": len(failed),
            "complete": len(failed) == 0,
            "failed_cells": failed,
            "skipped_cells": skipped,
        }

    @staticmethod
    def _check_difficulty_compliance(
        quiz_id: str,
        metric_results: list[MetricResult],
        instructions: QuizInstructions | None,
    ) -> float | None:
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
            logger.debug(
                "\n[Difficulty Compliance — %s]"
                "\n  Requested : %s (band %s–%s)"
                "\n  Mean score: %s  ✓ within band"
                "\n  Questions : %s scored"
                "\n  Adjusted  : %s (no penalty)",
                quiz_id,
                instructions.difficulty,
                low,
                high,
                mean_difficulty,
                len(difficulty_scores),
                mean_difficulty,
            )
            return mean_difficulty

        # Distance outside the band as fraction of full scale, capped at 30pts
        distance = max(mean_difficulty - high, low - mean_difficulty)
        penalty = round(min(distance * 0.5, 30.0), 1)
        adjusted = round(max(0.0, min(100.0, mean_difficulty - penalty)), 1)

        logger.debug(
            "\n[Difficulty Compliance — %s]"
            "\n  Requested : %s (band %s–%s)"
            "\n  Mean score: %s  ✗ outside band by %.1f pts"
            "\n  Penalty   : -%s → adjusted mean = %s"
            "\n  Questions : %s scored"
            "\n  Note      : Quiz overall difficulty does not match the "
            "'%s' instruction.",
            quiz_id,
            instructions.difficulty,
            low,
            high,
            mean_difficulty,
            distance,
            penalty,
            adjusted,
            len(difficulty_scores),
            instructions.difficulty,
        )
        return adjusted

    def _check_language_compliance(
        self,
        quiz: Quiz,
        metric_results: list[MetricResult],
        source_text: str | None,
        instructions: QuizInstructions | None,
    ) -> float | None:
        """Check the quiz against the requested language, once per quiz.

        Grammar is scored per question and in whatever language the item is
        actually written in, so the language-mismatch question -- a property of
        the quiz, not of any one item -- is asked here instead. Per-question
        scores are never modified: a language mismatch is an instruction
        compliance failure, not a grammar defect, and mixing the two would make
        the per-item grammar scores mean two things at once.

        Returns the compliance-adjusted mean grammar score, or None when there
        is nothing to check.
        """
        if not instructions or not instructions.language:
            return None

        by_evaluator: dict[str, list[float]] = {}
        for result in metric_results:
            if result.metric_name == "grammatical_correctness":
                by_evaluator.setdefault(result.evaluator_model, []).append(result.score)
        if not by_evaluator:
            return None

        try:
            metric = MetricRegistry.create("grammatical_correctness")
        except ValueError:
            return None

        adjusted_scores = []
        for evaluator_model, scores in by_evaluator.items():
            evaluator = next(
                (e for e in self.evaluators.values() if e.model_name == evaluator_model), None
            )
            if evaluator is None:
                continue
            try:
                # Each judge assesses its own compliance, over its own scores.
                adjusted_scores.append(
                    metric.adjust_score_for_custom_prompt(
                        raw_score=round(sum(scores) / len(scores), 1),
                        interpreted_instruction="",
                        quiz=quiz,
                        source_text=source_text,
                        llm_client=evaluator,
                        instructions=instructions,
                    )
                )
            except Exception as e:  # noqa: BLE001
                self.logger.error(
                    "Error checking language compliance for quiz %s: %s", quiz.quiz_id, e
                )

        if not adjusted_scores:
            return None
        return round(sum(adjusted_scores) / len(adjusted_scores), 1)

    def _evaluate_quiz(
        self, quiz: Quiz, source_text: str | None, run_number: int
    ) -> BenchmarkResult:
        started_at = datetime.now(tz=UTC)
        metric_results: list[MetricResult] = []
        phase_details = []

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
                    question_results: list[MetricResult | None] = []
                    for question in quiz.questions:
                        q_evaluated = self._evaluate_question(
                            metric,
                            evaluator,
                            quiz,
                            question,
                            source_text,
                            metric_config.parameters,
                            instructions,
                        )
                        if q_evaluated is not None:
                            mr, phases = q_evaluated
                            question_results.append(mr)
                            phase_details.append(
                                {
                                    "metric_name": metric.name,
                                    "evaluator_model": evaluator.model_name,
                                    "quiz_id": quiz.quiz_id,
                                    "question_id": question.question_id,
                                    "run_number": run_number,
                                    "phases": phases,
                                }
                            )
                        else:
                            question_results.append(None)
                    # P0-2a: fail loud if every question failed for this metric
                    if quiz.questions and all(r is None for r in question_results):
                        raise RuntimeError(
                            f"Metric '{metric_config.name}' failed for every question "
                            f"in quiz '{quiz.quiz_id}' — this indicates a systematic "
                            f"metric or configuration error, not a transient failure."
                        )
                    metric_results.extend(r for r in question_results if r is not None)
                else:
                    quiz_evaluated = self._evaluate_quiz_level(
                        metric,
                        evaluator,
                        quiz,
                        source_text,
                        metric_config.parameters,
                        instructions,
                    )
                    if quiz_evaluated:
                        evaluation, result = quiz_evaluated
                        phase_details.append(
                            {
                                "metric_name": metric.name,
                                "evaluator_model": evaluator.model_name,
                                "quiz_id": quiz.quiz_id,
                                "question_id": None,
                                "run_number": run_number,
                                "phases": evaluation.metadata.get("phases", {}),
                            }
                        )
                        # Per-question rows replace the aggregate row rather than
                        # joining it: sharing one metric_name would pool item
                        # scores with a quiz-level summary in every downstream mean.
                        expanded = self._expand_quiz_result(
                            metric,
                            evaluation,
                            evaluator,
                            quiz,
                            metric_config.parameters,
                            usage=result.usage,
                        )
                        metric_results.extend(expanded or [result])

        # ── Instruction compliance: runs after ALL metrics, outside the loop ── #
        # Both metrics score one question at a time, so their quiz-level
        # compliance questions are asked once here rather than once per item.
        # Neither touches the per-question rows.
        adjusted_difficulty = self._check_difficulty_compliance(
            quiz.quiz_id, metric_results, instructions
        )
        adjusted_grammar = self._check_language_compliance(
            quiz, metric_results, source_text, instructions
        )

        completed_at = datetime.now(tz=UTC)

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
                "adjusted_grammar": adjusted_grammar,
                "phase_details": phase_details,
            },
        )
