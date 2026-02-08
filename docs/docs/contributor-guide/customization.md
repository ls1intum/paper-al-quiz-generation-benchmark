---
title: Customization
sidebar_position: 2
---

## Customization

### Adding Custom Metrics

#### Step 1: Create Metric Class

Create a new file `src/metrics/validity.py`:

```python
from .base import BaseMetric, MetricScope
from src.models.quiz import QuizQuestion, Quiz
from typing import Optional

class ValidityMetric(BaseMetric):
    """Evaluates whether question measures what it intends to measure"""
    
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
    def description(self) -> str:
        return "Assesses construct validity: does the question measure the intended knowledge or skill?"
    
    def get_prompt(self, 
                   question: Optional[QuizQuestion] = None,
                   quiz: Optional[Quiz] = None,
                   source_text: Optional[str] = None,
                   **params) -> str:
        
        learning_objective = params.get('learning_objective', '')
        
        return f"""Evaluate the construct validity of this assessment question.
        
Question: {question.question_text}
Options: {', '.join(question.options)}
Correct Answer: {question.correct_answer}

Learning Objective: {learning_objective}

Source Material:
{source_text[:500] if source_text else 'Not provided'}

Rate the validity on a 0-100 scale:
- 0-25: Question does not measure the intended construct
- 26-50: Question partially measures intended construct but has major validity issues
- 51-75: Question measures intended construct with minor validity concerns
- 76-100: Question has strong construct validity

Respond with only a number 0-100."""
    
    def parse_response(self, llm_response: str) -> float:
        import re
        # Extract first number found in response
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', llm_response)
        if match:
            score = float(match.group(1))
            # Clamp to 0-100 range
            return max(0.0, min(100.0, score))
        raise ValueError(f"Could not parse score from response: {llm_response}")
```

#### Step 2: Register Metric

In `main.py`:

```python
from src.metrics.validity import ValidityMetric

def register_metrics():
    """Register all available metrics"""
    MetricRegistry.register(AlignmentMetric)
    MetricRegistry.register(CognitiveLevelMetric)
    MetricRegistry.register(ClarityMetric)
    MetricRegistry.register(DistractorQualityMetric)
    MetricRegistry.register(ValidityMetric)  # Add your new metric
```

#### Step 3: Use in Configuration

```yaml
metrics:
  - name: "validity"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      learning_objective: "auto_extract"
```

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

