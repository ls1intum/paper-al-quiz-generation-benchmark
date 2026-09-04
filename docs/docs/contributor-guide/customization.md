---
title: Customization
sidebar_position: 2
---

## Customization

### Adding Custom Metrics

A metric declares **phases**. Each phase either calls the LLM with a prompt you build
and a Pydantic schema it must return, or runs a plain Python function. The last
phase's output is what reaches `raw_response`, so a metric that wants its score to
follow deterministically from a verdict puts the Python phase last.

#### Step 1: Create the metric class

Create `src/metrics/validity.py`:

```python
from collections.abc import Callable
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .base import BaseMetric, MetricScope
from .phase import Phase, PhaseInput

# Four evenly spaced levels, best to worst, with no midpoint: a verdict and its
# number can then never disagree, and "somewhere in the middle" is not offered.
VALIDITY_SCORES = {"strong": 100.0, "adequate": 66.7, "weak": 33.3, "none": 0.0}


class ValidityJudgeResponse(BaseModel):
    """The judge's verdict and its evidence. Deliberately carries no score."""

    model_config = ConfigDict(extra="forbid")

    # Evidence fields come first: the model writes them before committing to a
    # verdict, so the verdict follows the reasoning rather than the reverse.
    rationale: str
    validity_level: Literal["strong", "adequate", "weak", "none"]


class ValidityResponse(ValidityJudgeResponse):
    """Final output: the verdict plus the score derived from it."""

    applicable: bool
    score: float = Field(ge=0, le=100)


class ValidityMetric(BaseMetric):
    """Evaluates whether an item measures the construct it intends to measure."""

    @property
    def name(self) -> str:
        return "validity"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    @property
    def phases(self) -> list[Phase]:
        return [
            Phase("judge", ValidityJudgeResponse),
            Phase("finalize", ValidityResponse, processor=self._finalize),
        ]

    def get_prompt_builder(self, phase_name: str) -> Callable[[PhaseInput], str]:
        builders = {"judge": self._build_judge_prompt}
        if phase_name not in builders:
            raise ValueError(f"Unknown phase '{phase_name}' for metric '{self.name}'")
        return builders[phase_name]

    @staticmethod
    def _build_judge_prompt(inp: PhaseInput) -> str:
        if inp.question is None:
            raise ValueError("validity judge phase requires a question")

        question = inp.question
        options = "\n".join(f"{i}. {o}" for i, o in enumerate(question.options, 1))
        # Never interpolate a bare None -- say what is absent.
        source = inp.source_text or "No source material is available; use expert knowledge."

        return f"""Judge whether this item measures the construct it intends to measure.

Stem: {question.question_text}
Options:
{options}
Marked correct answer: {question.correct_answer}

Source material: {source}

Levels:
- "strong": measures the intended construct directly.
- "adequate": measures it with minor validity concerns.
- "weak": measures something adjacent to it.
- "none": does not measure the intended construct.

Respond with ONLY a JSON object matching this schema:
{{"rationale": "<reasoning>", "validity_level": "strong" | "adequate" | "weak" | "none"}}"""

    @staticmethod
    def _finalize(inp: PhaseInput) -> dict[str, Any]:
        judge_output = inp.accumulated.get("judge")
        if judge_output is None:
            raise ValueError("finalize phase requires output from judge phase")

        judged = judge_output.data
        return {
            "rationale": judged.get("rationale", ""),
            "validity_level": judged["validity_level"],
            "applicable": True,
            "score": VALIDITY_SCORES[judged["validity_level"]],
        }
```

Two conventions worth following, both load-bearing:

- **Quiz-level metrics** set `scope` to `MetricScope.QUIZ_LEVEL` and read `inp.quiz`
  instead of `inp.question`. A quiz-level metric that also wants per-question rows
  overrides `expand_question_results`; one that does not simply omits it and produces
  a single row with an empty `question_id`.
- **A metric that can abstain** returns `applicable: false` with a score of `100.0`,
  and its name must be added to `_METRICS_WITH_APPLICABLE` in
  `src/analysis/aggregator.py`. Forgetting that silently counts every abstention as a
  perfect score in the mean.

Fan-out phases (`Phase(..., fan_out=True)`) run once per question and receive
`inp.question`; their results arrive at later phases as a flat list, so each
fan-out schema should carry `question_id` and the prompt should ask the model to
echo it back.

#### Step 2: Register the metric

Registration is manual, in `main.py`:

```python
from src.metrics.validity import ValidityMetric

def register_metrics() -> None:
    """Register all available metrics."""
    ...
    MetricRegistry.register(ValidityMetric)
```

Export it from `src/metrics/__init__.py` as well. The test fixture
`registered_metrics` calls `register_metrics()` directly, so nothing else needs
updating there — but `tests/conftest.py`'s `MockLLMProvider._sniff_response` needs a
branch keyed on a JSON field name unique to your schema, or runner-level tests will
feed your metric a hash-derived `{"score": n}` that fails schema validation.

#### Step 3: Use it in a configuration

```yaml
metrics:
  - name: "validity"
    version: "1.0"
    evaluators: ["gpt4"]
```

The `version` string in the YAML is not checked against the class. The version
recorded on every result row always comes from the code, and it is how output from
two versions of a prompt stays separable when bundles are merged — so change a
metric's construct by **bumping `version`**, never by editing a prompt in place.

---

### Adding Custom Evaluators

#### Step 1: Create Provider Class

Create `src/evaluators/custom_provider.py`:

```python
from .base import LLMProvider
import requests

class CustomProvider(LLMProvider):
    """Custom LLM provider implementation"""
    
    def __init__(self, api_key: str, endpoint: str, model: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model
    
    def generate(self, 
                 prompt: str, 
                 temperature: float = 0.0, 
                 max_tokens: int = 1000, 
                 **kwargs) -> str:
        """Call your custom API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        response = requests.post(
            f"{self.endpoint}/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        return response.json()["choices"][0]["text"]
    
    @property
    def model_name(self) -> str:
        return self.model
    
    @property
    def provider_type(self) -> str:
        return "custom"
```

#### Step 2: Register in Factory

In `src/evaluators/factory.py`:

```python
from .custom_provider import CustomProvider

class LLMProviderFactory:
    @staticmethod
    def create(provider_config: Dict[str, Any]) -> LLMProvider:
        provider_type = provider_config.get("provider")
        
        if provider_type == "custom":
            return CustomProvider(
                api_key=os.getenv("CUSTOM_API_KEY"),
                endpoint=os.getenv("CUSTOM_ENDPOINT"),
                model=provider_config["model"]
            )
        elif provider_type == "openai":
            # ... existing providers
            pass
```

#### Step 3: Use in Configuration

```yaml
evaluators:
  my_custom_model:
    provider: "custom"
    model: "my-model-v1"
    temperature: 0.0
    max_tokens: 500
```

---

### Customizing Analysis

You can write custom analysis scripts to extract insights:

```python
import json
import pandas as pd
from pathlib import Path

# Load results
results_file = Path("data/results/results_20240115_103000.json")
with open(results_file) as f:
    results_data = json.load(f)

# Convert to DataFrame for analysis
records = []
for result in results_data:
    quiz_id = result['quiz_id']
    run_num = result['run_number']
    
    for metric in result['metrics']:
        records.append({
            'quiz_id': quiz_id,
            'run': run_num,
            'metric': metric['metric_name'],
            'evaluator': metric['evaluator_model'],
            'question_id': metric.get('question_id'),
            'score': metric['score']
        })

df = pd.DataFrame(records)

# Analysis examples
print("Average scores by metric:")
print(df.groupby('metric')['score'].mean())

print("\nEvaluator agreement:")
pivot = df.pivot_table(
    values='score', 
    index=['quiz_id', 'question_id', 'metric'],
    columns='evaluator',
    aggfunc='mean'
)
print(pivot.corr())

print("\nQuestions with highest variance:")
variance = df.groupby(['quiz_id', 'question_id', 'metric'])['score'].var()
print(variance.nlargest(10))
```

---

