"""Tests for metric implementations."""

import pytest

from src.metrics.difficulty import DifficultyMetric
from src.metrics.coverage import CoverageMetric
from src.metrics.clarity import ClarityMetric
from src.metrics.base import ScoreResponse
from src.metrics.homogeneous_options import HomogeneousOptionsMetric
from src.metrics.phase import Phase, PhaseInput, PhaseOutput
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
