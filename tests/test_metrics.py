"""Tests for metric implementations."""

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.metrics.phase import PhaseInput, PhaseOutput
from src.models.quiz import QuizQuestion, QuestionType, Quiz
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
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric])
def test_simple_metric_parse_score_success(metric_cls, score):
    """Single-stage metrics should parse a PhaseOutput with a valid score."""
    metric = metric_cls()
    output = PhaseOutput(phase_name="scoring", data={"score": score})
    assert metric.parse_score(output) == score


@pytest.mark.parametrize("score", [-1, 101])
@pytest.mark.parametrize("metric_cls", [DifficultyMetric, ClarityMetric])
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
        metric, "map",
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
        metric, "score",
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
            data={"results": [
                {"topics": ["functions"], "cognitive_level_label": "recall", "cognitive_level_score": 1}
            ]},
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