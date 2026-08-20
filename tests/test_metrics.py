"""Tests for metric implementations."""

import json

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.metrics.distractor import DistractorQualityMetric
from src.metrics.base import ScoreResponse
from src.metrics.homogeneous_options import HomogeneousOptionsMetric
from src.metrics.phase import Phase, PhaseInput, PhaseOutput
from src.metrics.accuracy import FactualAccuracyMetric
from src.metrics.answer_key_correctness import (
    AnswerKeyCorrectnessMetric,
    detect_catch_all_options,
)
from src.metrics.objective_alignment import (
    ObjectiveAlignmentMetric,
    get_learning_objective,
)
from src.models.quiz import QuizQuestion, QuestionType, Quiz
from src.models.result import EvaluationResult
from tests.conftest import MockLLMProvider


def make_question() -> QuizQuestion:
    return QuizQuestion(
        question_id="q1",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="What is 2+2?",
        options=["2", "3", "4", "5"],
        correct_answer="4",
    )


def make_quiz() -> Quiz:
    return Quiz(
        quiz_id="quiz_1",
        title="Test Quiz",
        source_material="source.md",
        questions=[make_question()],
    )


def make_phase_input(metric, phase_name, **kwargs) -> PhaseInput:
    """Helper: build a PhaseInput with the correct prompt_builder for the given phase."""
    return PhaseInput(
        prompt_builder=metric.get_prompt_builder(phase_name),
        **kwargs,
    )


@pytest.mark.parametrize("score", [42.0, 88.0, 85.5])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric, DistractorQualityMetric, FactualAccuracyMetric])
def test_simple_metric_parse_score_success(metric_cls, score):
    """Single-stage metrics should parse a PhaseOutput with a valid score."""
    metric = metric_cls()
    output = PhaseOutput(phase_name="scoring", data={"score": score})
    assert metric.parse_score(output) == score


@pytest.mark.parametrize("score", [-1, 101])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric, DistractorQualityMetric, FactualAccuracyMetric])
def test_simple_metric_parse_score_failure(metric_cls, score):
    """Single-stage metrics should reject out-of-range scores."""
    metric = metric_cls()
    output = PhaseOutput(phase_name="scoring", data={"score": score})
    with pytest.raises(ValueError):
        metric.parse_score(output)


def test_difficulty_phase_requires_question():
    """Difficulty prompt builder should raise ValueError when question is missing."""
    metric = DifficultyMetric()
    inp = make_phase_input(metric, "score")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_difficulty_phase_builds_prompt():
    """Difficulty prompt builder should return a non-empty string."""
    metric = DifficultyMetric()
    inp = make_phase_input(metric, "score", question=make_question())
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_difficulty_param_validation():
    """DifficultyMetric should reject invalid param types and unknown params."""
    metric = DifficultyMetric()
    with pytest.raises(ValueError, match="should be of type str"):
        metric.validate_params(rubric=123)
    with pytest.raises(ValueError, match="Unknown parameter"):
        metric.validate_params(unknown_param="x")


def test_clarity_phase_requires_question():
    """Clarity prompt builder should raise ValueError when question is missing."""
    metric = ClarityMetric()
    inp = make_phase_input(metric, "score")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_clarity_phase_builds_prompt():
    """Clarity prompt builder should return a non-empty string."""
    metric = ClarityMetric()
    inp = make_phase_input(metric, "score", question=make_question())
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_coverage_parse_score_success():
    """CoverageMetric should extract final_score from PhaseOutput."""
    metric = CoverageMetric()
    output = PhaseOutput(
        phase_name="coverage_scoring",
        data={
            "final_score": 67.5,
            "sub_scores": {"breadth": 20.0, "depth": 22.5, "balance": 15.0, "critical": 10.0},
            "topics_in_source": [],
            "topics_covered": [],
            "critical_concepts": [],
            "critical_covered": [],
            "breadth_reasoning": "",
            "depth_reasoning": "",
            "balance_reasoning": "",
            "critical_reasoning": "",
        },
    )
    assert metric.parse_score(output) == 67.5


def test_coverage_parse_score_invalid():
    """CoverageMetric should reject out-of-range final_score."""
    metric = CoverageMetric()
    output = PhaseOutput(phase_name="coverage_scoring", data={"final_score": 101})
    with pytest.raises(ValueError):
        metric.parse_score(output)


def test_coverage_extract_phase_requires_source_text():
    """Coverage extract prompt builder should raise when source_text is missing."""
    metric = CoverageMetric()
    inp = make_phase_input(metric, "extract")
    with pytest.raises(ValueError, match="requires source_text"):
        inp.prompt_builder(inp)


def test_coverage_extract_phase_builds_prompt():
    """Coverage extract prompt builder should return a non-empty string."""
    metric = CoverageMetric()
    inp = make_phase_input(metric, "extract", source_text="Python is a language.")
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_coverage_map_phase_requires_question():
    """Coverage map prompt builder should raise when question is missing."""
    metric = CoverageMetric()
    inp = make_phase_input(metric, "map")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_coverage_map_phase_builds_prompt():
    """Coverage map prompt builder should return a non-empty string."""
    metric = CoverageMetric()
    extract_output = PhaseOutput(
        phase_name="extract",
        data={"topics": ["functions", "data types"], "critical_concepts": ["functions"]},
    )
    inp = make_phase_input(
        metric,
        "map",
        question=make_question(),
        accumulated={"extract": extract_output},
    )
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_coverage_score_phase_requires_extract_and_map():
    """Coverage score prompt builder should raise when extract or map output is missing."""
    metric = CoverageMetric()

    # Missing both
    inp = make_phase_input(metric, "score", quiz=make_quiz(), source_text="text")
    with pytest.raises(ValueError, match="requires outputs from extract and map phases"):
        inp.prompt_builder(inp)

    # extract present, map missing
    inp = make_phase_input(
        metric,
        "score",
        quiz=make_quiz(),
        source_text="text",
        accumulated={
            "extract": PhaseOutput(
                phase_name="extract",
                data={"topics": ["t1"], "critical_concepts": ["t1"]},
            )
        },
    )
    with pytest.raises(ValueError, match="requires outputs from extract and map phases"):
        inp.prompt_builder(inp)


def test_coverage_score_phase_builds_prompt():
    """Coverage score prompt builder should return a non-empty string."""
    metric = CoverageMetric()
    accumulated = {
        "extract": PhaseOutput(
            phase_name="extract",
            data={"topics": ["functions", "data types"], "critical_concepts": ["functions"]},
        ),
        "map": PhaseOutput(
            phase_name="map",
            data={
                "results": [
                    {
                        "topics": ["functions"],
                        "cognitive_level_label": "recall",
                        "cognitive_level_score": 1,
                    }
                ]
            },
        ),
    }
    inp = make_phase_input(metric, "score", quiz=make_quiz(), accumulated=accumulated)
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_coverage_evaluate_requires_quiz():
    """Coverage evaluate() should raise when quiz is missing."""
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires a quiz"):
        metric.evaluate(source_text="text", llm_client=mock_llm)


def test_coverage_evaluate_requires_source_text():
    """Coverage evaluate() should raise when source_text is missing."""
    metric = CoverageMetric()
    mock_llm = MockLLMProvider(model="mock-model")
    with pytest.raises(ValueError, match="requires source_text"):
        metric.evaluate(quiz=make_quiz(), llm_client=mock_llm)


def test_coverage_param_validation():
    """CoverageMetric should validate granularity parameter type."""
    metric = CoverageMetric()
    with pytest.raises(ValueError, match="should be of type str"):
        metric.validate_params(granularity=10)

def test_distractor_quality_analyze_phase_requires_question():
    """Distractor quality analyze prompt builder should raise ValueError when question is missing."""
    metric = DistractorQualityMetric()
    inp = make_phase_input(metric, "analyze", source_text="Sample text")
    with pytest.raises(ValueError, match="distractor_quality analyze phase requires a question"):
        inp.prompt_builder(inp)

def test_distractor_quality_analyze_phase_requires_source_text():
    """Distractor quality analyze prompt builder should raise ValueError when source_text is missing."""
    metric = DistractorQualityMetric()
    inp = make_phase_input(metric, "analyze", question=make_question())
    with pytest.raises(ValueError, match="distractor_quality analyze phase requires source_text"):
        inp.prompt_builder(inp)

def test_distractor_quality_analyze_phase_builds_prompt():
    """Distractor quality analyze prompt builder should return a non-empty string."""
    metric = DistractorQualityMetric()
    inp = make_phase_input(metric, "analyze", question=make_question(), source_text="Sample text")
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0

def test_distractor_quality_score_phase_requires_analyze_output():
    """Distractor quality score prompt builder should raise ValueError when analyze output is missing."""
    metric = DistractorQualityMetric()
    # Missing 'accumulated' entirely
    inp = make_phase_input(metric, "score")
    with pytest.raises(ValueError, match="requires 'analyze' phase output in accumulated"):
        inp.prompt_builder(inp)

def test_distractor_quality_score_phase_builds_prompt():
    """Distractor quality score prompt builder should return a non-empty string."""
    metric = DistractorQualityMetric()
    analyze_output = PhaseOutput(
        phase_name="analyze",
        data={
            "plausibility_analysis": "test",
            "misconception_analysis": "test",
            "discrimination_analysis": "test",
            "collective_analysis": "test",
            "difficulty_calibration": "test",
        }
    )
    inp = make_phase_input(
        metric,
        "score",
        accumulated={"analyze": analyze_output}
    )
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
def test_homogeneous_options_parse_score_success():
    """HomogeneousOptionsMetric should extract score from aggregate output."""
    metric = HomogeneousOptionsMetric()
    output = PhaseOutput(
        phase_name="aggregate",
        data={
            "num_questions_total": 2,
            "num_questions_applicable": 1,
            "num_excluded": 1,
            "mean_question_score": 90.0,
            "median_question_score": 90.0,
            "major_violation_rate": 0.0,
            "perfect_homogeneity_rate": 0.0,
            "issue_distribution": [],
            "question_scores": [],
            "aggregation_reasoning": "reasoning",
            "score": 90.0,
        },
    )
    assert metric.parse_score(output) == 90.0


def test_homogeneous_options_analyze_phase_requires_question():
    """Analyze prompt builder should raise when question is missing."""
    metric = HomogeneousOptionsMetric()
    inp = make_phase_input(metric, "analyze_options")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_factual_accuracy_phase_requires_question():
    """Factual accuracy prompt builder should raise ValueError when question is missing."""
    metric = FactualAccuracyMetric()
    inp = make_phase_input(metric, "score")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_homogeneous_options_analyze_phase_builds_prompt():
    """Analyze prompt builder should return a non-empty string."""
    metric = HomogeneousOptionsMetric()
    inp = make_phase_input(metric, "analyze_options", question=make_question())
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_homogeneous_options_score_phase_requires_analysis():
    """Score prompt builder should raise when analysis output is missing."""
    metric = HomogeneousOptionsMetric()
    inp = make_phase_input(metric, "score_question", question=make_question())
    with pytest.raises(ValueError, match="requires output from analyze_options phase"):
        inp.prompt_builder(inp)


def test_homogeneous_options_score_phase_builds_prompt():
    """Score prompt builder should return a non-empty string."""
    metric = HomogeneousOptionsMetric()
    accumulated = {
        "analyze_options": PhaseOutput(
            phase_name="analyze_options",
            data={
                "results": [
                    {
                        "question_id": "q1",
                        "applicable": True,
                        "exclusion_reason": None,
                        "option_analyses": [
                            {
                                "option_text": "2",
                                "grammatical_form": "numeric_expression",
                                "content_type": "numeric_value",
                                "is_complete_sentence": False,
                                "contains_code": False,
                                "contains_numeric_expression": True,
                                "length_bucket": "very_short",
                                "reasoning": "A number",
                            }
                        ],
                        "dominant_grammatical_pattern": "numeric_expression",
                        "dominant_content_type": "numeric_value",
                        "structural_outliers": [],
                    }
                ]
            },
        )
    }
    inp = make_phase_input(
        metric,
        "score_question",
        question=make_question(),
        accumulated=accumulated,
    )
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_homogeneous_options_aggregate_phase_requires_score_results():
    """Aggregate processor should raise when score results are missing."""
    metric = HomogeneousOptionsMetric()
    inp = PhaseInput(prompt_builder=None, quiz=make_quiz())
    with pytest.raises(ValueError, match="requires output from score_question phase"):
        metric.phases[-1].process(inp, llm_client=None)


def test_factual_accuracy_phase_builds_prompt():
    """Factual accuracy prompt builder should return a non-empty string."""
    metric = FactualAccuracyMetric()
    inp = make_phase_input(metric, "score", question=make_question())
    prompt = inp.prompt_builder(inp)
    assert isinstance(prompt, str)
    assert len(prompt) > 0


def test_python_phase_processor_validates_schema():
    """Phase.process should support deterministic Python processors."""
    phase = Phase(
        "score",
        ScoreResponse,
        processor=lambda inp: {"score": 77.5},
    )
    result = phase.process(PhaseInput(prompt_builder=None), llm_client=None)
    assert result == {"score": 77.5}


def test_homogeneous_options_aggregate_phase_computes_result():
    """Aggregate phase should compute quiz-level metrics without an LLM call."""
    metric = HomogeneousOptionsMetric()
    accumulated = {
        "score_question": PhaseOutput(
            phase_name="score_question",
            data={
                "results": [
                    {
                        "question_id": "q1",
                        "applicable": True,
                        "grammatical_parallelism_score": 90.0,
                        "content_type_homogeneity_score": 80.0,
                        "format_consistency_score": 100.0,
                        "question_score": 87.5,
                        "severity": "none",
                        "issues": [],
                        "rationale": "parallel numeric values",
                    }
                ]
            },
        )
    }
    inp = PhaseInput(prompt_builder=None, quiz=make_quiz(), accumulated=accumulated)
    result = metric.phases[-1].process(inp, llm_client=None)
    assert result["score"] == 87.5
    assert result["num_questions_applicable"] == 1
    assert "Aggregated 1 applicable questions" in result["aggregation_reasoning"]


def test_homogeneous_options_evaluate_end_to_end():
    """HomogeneousOptionsMetric should evaluate all phases with structured responses."""
    metric = HomogeneousOptionsMetric()
    mock_llm = MockLLMProvider(
        model="mock-model",
        responses=[
            {
                "question_id": "q1",
                "applicable": True,
                "exclusion_reason": None,
                "option_analyses": [
                    {
                        "option_text": "2",
                        "grammatical_form": "numeric_expression",
                        "content_type": "numeric_value",
                        "is_complete_sentence": False,
                        "contains_code": False,
                        "contains_numeric_expression": True,
                        "length_bucket": "very_short",
                        "reasoning": "A number",
                    },
                    {
                        "option_text": "3",
                        "grammatical_form": "numeric_expression",
                        "content_type": "numeric_value",
                        "is_complete_sentence": False,
                        "contains_code": False,
                        "contains_numeric_expression": True,
                        "length_bucket": "very_short",
                        "reasoning": "A number",
                    },
                ],
                "dominant_grammatical_pattern": "numeric_expression",
                "dominant_content_type": "numeric_value",
                "structural_outliers": [],
            },
            {
                "question_id": "q1",
                "applicable": True,
                "grammatical_parallelism_score": 95.0,
                "content_type_homogeneity_score": 95.0,
                "format_consistency_score": 100.0,
                "question_score": 95.5,
                "severity": "none",
                "issues": [],
                "rationale": "All options are parallel.",
            },
        ],
    )

    result = metric.evaluate(quiz=make_quiz(), llm_client=mock_llm)
    assert result.score == 95.5
    assert '"score": 95.5' in result.raw_response


# ── answer_key_correctness ───────────────────────────────────────────────── #


def _judge(key_correct: bool, **overrides) -> dict:
    """A judge-phase response; overrides fill in the diagnostic sub-fields."""
    return {
        "key_correct": key_correct,
        "defensible_correct_options": overrides.get("defensible", []),
        "misclassified_options": overrides.get("misclassified", []),
        "issue_flags": overrides.get("flags", []),
        "rationale": overrides.get("rationale", "mock rationale"),
    }


def _evaluate_key(question, judge_response) -> tuple:
    """Run the metric over one question, returning (EvaluationResult, parsed raw_response)."""
    metric = AnswerKeyCorrectnessMetric()
    mock_llm = MockLLMProvider(model="mock-model", responses=[judge_response])
    result = metric.evaluate(question=question, llm_client=mock_llm)
    return result, json.loads(result.raw_response)


def test_answer_key_prompt_requires_question():
    """Judge prompt builder should raise ValueError when question is missing."""
    metric = AnswerKeyCorrectnessMetric()
    inp = make_phase_input(metric, "judge")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_answer_key_prompt_includes_options_and_key():
    """Judge prompt should present every option and the marked key."""
    metric = AnswerKeyCorrectnessMetric()
    inp = make_phase_input(metric, "judge", question=make_question())
    prompt = inp.prompt_builder(inp)

    for option in make_question().options:
        assert option in prompt
    assert "Marked Correct Answer (key): 4" in prompt
    assert "single_choice" in prompt


def test_answer_key_prompt_without_source_asks_for_expert_knowledge():
    """Missing source_text must not render as 'None' (see accuracy.py:60)."""
    metric = AnswerKeyCorrectnessMetric()
    inp = make_phase_input(metric, "judge", question=make_question())
    prompt = inp.prompt_builder(inp)

    assert "Source Material: None" not in prompt
    assert "general expert knowledge" in prompt


@pytest.mark.parametrize(
    "options,expected",
    [
        (["Paris", "All of the above"], ["All of the above"]),
        (["Keine der genannten", "Berlin"], ["Keine der genannten"]),
        (["(Alle oben genannten)"], ["(Alle oben genannten)"]),
        (["None of these statements is true"], ["None of these statements is true"]),
        # Must NOT overflag ordinary domain prose.
        (["A list of all listed items"], []),
        (["All answers are stored in a hash map"], []),
        (["The method returns all answers"], []),
    ],
)
def test_detect_catch_all_options(options, expected):
    """Catch-all detection covers English and German without flagging domain text."""
    assert detect_catch_all_options(options) == expected


def test_answer_key_correct_single_choice_scores_100():
    """A correctly keyed single_choice item passes with no flags."""
    result, data = _evaluate_key(make_question(), _judge(True, defensible=["4"]))

    assert result.score == 100.0
    assert data["key_correct"] is True
    assert data["issue_flags"] == []
    assert data["catch_all_options"] == []


def test_answer_key_multiple_choice_omitted_correct_option():
    """An unkeyed but defensible option flags multiple_defensible and fails."""
    question = QuizQuestion(
        question_id="q_mc",
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_text="Which are prime?",
        options=["2", "3", "4"],
        correct_answer=["2"],
    )
    result, data = _evaluate_key(
        question,
        _judge(False, defensible=["2", "3"], misclassified=["3"], flags=["multiple_defensible"]),
    )

    assert result.score == 0.0
    assert data["issue_flags"] == ["multiple_defensible"]
    assert data["misclassified_options"] == ["3"]


def test_answer_key_wrong_keyed_option():
    """A keyed option that is actually incorrect flags keyed_answer_wrong."""
    question = QuizQuestion(
        question_id="q_wrong",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="What is 2+2?",
        options=["2", "3", "4", "5"],
        correct_answer="5",
    )
    result, data = _evaluate_key(
        question, _judge(False, defensible=["4"], misclassified=["5"], flags=["keyed_answer_wrong"])
    )

    assert result.score == 0.0
    assert data["issue_flags"] == ["keyed_answer_wrong"]


def test_answer_key_catch_all_overrides_a_passing_judge():
    """A catch-all option fails the item even when the judge said the key is fine."""
    question = QuizQuestion(
        question_id="q_catch_all",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="Which apply?",
        options=["Speed", "Cost", "All of the above"],
        correct_answer="All of the above",
    )
    result, data = _evaluate_key(question, _judge(True, defensible=["All of the above"]))

    assert result.score == 0.0
    assert data["key_correct"] is False
    assert data["issue_flags"] == ["catch_all_present"]
    assert data["catch_all_options"] == ["All of the above"]


def test_answer_key_empty_key_does_not_crash():
    """An item with no marked answer evaluates to a failing result, not an exception."""
    question = QuizQuestion(
        question_id="q_empty_key",
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_text="Which statements hold?",
        options=["A", "B", "C"],
        correct_answer=[],
    )
    result, data = _evaluate_key(question, _judge(True, defensible=[]))

    assert result.score == 0.0
    assert data["key_correct"] is False
    assert "no_correct_option" in data["issue_flags"]


def test_answer_key_raw_response_carries_diagnostics():
    """raw_response must expose the full diagnostic payload, not just a score."""
    result, _ = _evaluate_key(make_question(), _judge(True, defensible=["4"]))

    for field in (
        "key_correct",
        "defensible_correct_options",
        "misclassified_options",
        "issue_flags",
        "catch_all_options",
        "rationale",
        "score",
    ):
        assert f'"{field}"' in result.raw_response


def test_answer_key_unknown_judge_flags_are_dropped():
    """Flags outside the four known issue flags never reach the output."""
    _, data = _evaluate_key(
        make_question(), _judge(False, flags=["multiple_defensible", "ambiguous_key", "nonsense"])
    )

    assert data["issue_flags"] == ["multiple_defensible"]


# ── objective_alignment ──────────────────────────────────────────────────── #

OBJECTIVE = "Streams — Du verstehst das Konzept von Streams und kannst sie anwenden."


def make_question_with_objective(objective=OBJECTIVE) -> QuizQuestion:
    metadata = {"topic": "Streams", "domain": "java"}
    if objective is not None:
        metadata["learning_objective"] = objective
    return QuizQuestion(
        question_id="q_lo",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="Which call turns a List into a Stream?",
        options=["list.stream()", "list.iterator()", "list.toArray()", "list.size()"],
        correct_answer="list.stream()",
        metadata=metadata,
    )


def _judge_alignment(level: str, **overrides) -> dict:
    return {
        "alignment_level": level,
        "matched_objective_aspects": overrides.get("matched", ["applying streams"]),
        "missing_or_misaligned_aspects": overrides.get("missing", []),
        "rationale": overrides.get("rationale", "mock rationale"),
    }


def _evaluate_alignment(question, judge_response) -> tuple:
    metric = ObjectiveAlignmentMetric()
    mock_llm = MockLLMProvider(model="mock-model", responses=[judge_response])
    result = metric.evaluate(question=question, llm_client=mock_llm)
    return result, json.loads(result.raw_response)


def test_objective_alignment_prompt_requires_question():
    metric = ObjectiveAlignmentMetric()
    inp = make_phase_input(metric, "judge")
    with pytest.raises(ValueError, match="requires a question"):
        inp.prompt_builder(inp)


def test_objective_alignment_prompt_includes_objective_and_item():
    """The objective must appear verbatim, alongside the options and the marked answer."""
    metric = ObjectiveAlignmentMetric()
    question = make_question_with_objective()
    inp = make_phase_input(metric, "judge", question=question)
    prompt = inp.prompt_builder(inp)

    assert OBJECTIVE in prompt
    for option in question.options:
        assert option in prompt
    assert "Marked Correct Answer: list.stream()" in prompt
    assert "Source Material: None" not in prompt


@pytest.mark.parametrize(
    "metadata,expected",
    [
        ({}, None),
        ({"learning_objective": None}, None),
        ({"learning_objective": ""}, None),
        ({"learning_objective": "   "}, None),
        ({"learning_objective": "  Streams  "}, "Streams"),
    ],
)
def test_get_learning_objective(metadata, expected):
    """An absent key, a null, and a whitespace-only string all mean 'no objective'."""
    question = QuizQuestion(
        question_id="q",
        question_type=QuestionType.SINGLE_CHOICE,
        question_text="t",
        options=["a", "b"],
        correct_answer="a",
        metadata=metadata,
    )
    assert get_learning_objective(question) == expected


@pytest.mark.parametrize(
    "level,expected_score",
    [("direct", 100.0), ("partial", 66.7), ("weak", 33.3), ("none", 0.0)],
)
def test_objective_alignment_level_determines_score(level, expected_score):
    """The score is derived from the level, never supplied by the judge."""
    result, data = _evaluate_alignment(make_question_with_objective(), _judge_alignment(level))

    assert result.score == expected_score
    assert data["alignment_level"] == level
    assert data["applicable"] is True


def test_objective_alignment_direct_echoes_objective():
    result, data = _evaluate_alignment(make_question_with_objective(), _judge_alignment("direct"))

    assert result.score == 100.0
    assert data["learning_objective"] == OBJECTIVE
    assert data["matched_objective_aspects"] == ["applying streams"]


def test_objective_alignment_weak_preserved_in_raw_response():
    """A weak verdict keeps its level and its evidence in raw_response."""
    result, data = _evaluate_alignment(
        make_question_with_objective(),
        _judge_alignment("weak", matched=["stream vocabulary"], missing=["applying streams"]),
    )

    assert '"alignment_level": "weak"' in result.raw_response
    assert result.score == 33.3
    assert data["missing_or_misaligned_aspects"] == ["applying streams"]


def test_objective_alignment_missing_objective_is_not_applicable():
    """An item with no objective is excluded, whatever the judge answered."""
    question = make_question_with_objective(objective=None)
    # The judge is fed a contradicting "direct" verdict; it must be discarded.
    result, data = _evaluate_alignment(question, _judge_alignment("direct"))

    assert data["applicable"] is False
    assert data["alignment_level"] == "not_applicable"
    assert data["learning_objective"] is None
    assert data["matched_objective_aspects"] == []
    assert result.score == 100.0


def test_objective_alignment_blank_objective_is_not_applicable():
    """A whitespace-only objective is treated the same as an absent one."""
    _, data = _evaluate_alignment(
        make_question_with_objective(objective="   "), _judge_alignment("direct")
    )

    assert data["applicable"] is False
    assert data["alignment_level"] == "not_applicable"


def test_objective_alignment_raw_response_carries_diagnostics():
    result, _ = _evaluate_alignment(make_question_with_objective(), _judge_alignment("partial"))

    for field in (
        "applicable",
        "alignment_level",
        "learning_objective",
        "matched_objective_aspects",
        "missing_or_misaligned_aspects",
        "rationale",
        "score",
    ):
        assert f'"{field}"' in result.raw_response


# ── homogeneous_options per-question expansion ───────────────────────────── #


def _homogeneity_result(*entries) -> EvaluationResult:
    return EvaluationResult(
        score=90.0,
        raw_response="{}",
        metadata={"phases": {"score_question": {"results": list(entries)}}},
    )


def _question_score(question_id="q1", applicable=True, score=87.5, severity="none", issues=None):
    return {
        "question_id": question_id,
        "applicable": applicable,
        "grammatical_parallelism_score": 90.0,
        "content_type_homogeneity_score": 85.0,
        "format_consistency_score": 95.0,
        "question_score": score,
        "severity": severity,
        "issues": issues if issues is not None else [],
        "rationale": "mock rationale",
    }


def test_expand_question_results_default_is_empty():
    """Metrics with no per-question breakdown give the runner nothing extra."""
    result = EvaluationResult(score=50.0, raw_response="{}", metadata={})
    assert FactualAccuracyMetric().expand_question_results(result) == []


def test_homogeneous_options_expands_one_row_per_question():
    metric = HomogeneousOptionsMetric()
    rows = metric.expand_question_results(
        _homogeneity_result(
            _question_score("q1", score=87.5),
            _question_score("q2", score=62.0, severity="minor", issues=["length_outlier"]),
        )
    )

    assert [(qid, score) for qid, score, _ in rows] == [("q1", 87.5), ("q2", 62.0)]


def test_homogeneous_options_expanded_raw_response_carries_diagnostics():
    metric = HomogeneousOptionsMetric()
    rows = metric.expand_question_results(
        _homogeneity_result(_question_score("q1", severity="minor", issues=["length_outlier"]))
    )

    data = json.loads(rows[0][2])
    assert data["severity"] == "minor"
    assert data["issues"] == ["length_outlier"]
    assert data["rationale"] == "mock rationale"
    assert data["applicable"] is True


def test_homogeneous_options_expands_not_applicable_questions():
    """True/false items keep their existing excluded-but-present behaviour."""
    metric = HomogeneousOptionsMetric()
    rows = metric.expand_question_results(
        _homogeneity_result(
            _question_score("q_tf", applicable=False, score=100.0, issues=["not_applicable"])
        )
    )

    assert len(rows) == 1
    assert rows[0][1] == 100.0
    assert json.loads(rows[0][2])["applicable"] is False


@pytest.mark.parametrize(
    "metadata",
    [
        {},
        {"phases": {}},
        {"phases": {"score_question": {"results": []}}},
        {"phases": {"score_question": "not a dict"}},
    ],
)
def test_homogeneous_options_expansion_tolerates_missing_phase(metadata):
    """A malformed run yields no rows instead of raising, so the aggregate survives."""
    result = EvaluationResult(score=90.0, raw_response="{}", metadata=metadata)
    assert HomogeneousOptionsMetric().expand_question_results(result) == []


def test_homogeneous_options_expansion_skips_entries_without_question_id():
    metric = HomogeneousOptionsMetric()
    entry = _question_score("q1")
    del entry["question_id"]
    rows = metric.expand_question_results(_homogeneity_result(entry, _question_score("q2")))

    assert [qid for qid, _, _ in rows] == ["q2"]
