# Quiz Generation Benchmark Framework

A comprehensive, stateless benchmark framework for evaluating AI-generated quizzes using multiple LLM-based metrics.

## Features

- **Flexible Metric System**: Easily add custom metrics for evaluating quiz quality
- **Multi-LLM Support**: Compare evaluations across different LLMs (GPT-4, GPT-3.5, Claude, open-source models)
- **Clean Architecture**: Type-safe Python with clear interfaces and separation of concerns
- **Reproducible Results**: Deterministic evaluation with versioning and configuration hashing
- **Statistical Aggregation**: Automatic calculation of mean, median, std dev across multiple runs
- **Extensible Design**: Add new metrics, evaluators, and analysis methods easily

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd paper-al-quiz-generation-benchmark

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

```bash
# Copy environment template
cp config/.env.example .env

# Edit .env with your API keys
# Required: At least one LLM provider's API key
nano .env
```

### 3. Prepare Data

Create your quiz files in `data/quizzes/` and source materials in `data/inputs/`:

**Example Quiz Format** (`data/quizzes/example_quiz.json`):
```json
{
  "quiz_id": "quiz_001",
  "title": "Introduction to Python",
  "source_material": "python_basics.md",
  "questions": [
    {
      "question_id": "q1",
      "question_type": "single_choice",
      "question_text": "What is the output of print(2 + 2)?",
      "options": ["2", "4", "22", "Error"],
      "correct_answer": "4",
      "source_reference": "Section 2.1",
      "metadata": {}
    }
  ],
  "metadata": {},
  "created_at": "2024-01-15T10:00:00"
}
```

**Source Material** (`data/inputs/python_basics.md`):
```markdown
# Python Basics

## Section 2.1: Arithmetic Operations
Python supports basic arithmetic operations...
```

### 4. Run Benchmark

```bash
# Run with example configuration
python main.py --config config/benchmark_example.yaml

# View results in data/results/
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed architecture documentation.

### Project Structure

```
paper-al-quiz-generation-benchmark/
├── src/
│   ├── models/          # Data models (Quiz, Result, Config)
│   ├── metrics/         # Metric implementations
│   ├── evaluators/      # LLM provider abstractions
│   ├── runners/         # Benchmark execution
│   ├── analysis/        # Results aggregation and reporting
│   └── utils/           # Configuration and I/O utilities
├── data/
│   ├── inputs/          # Source markdown files
│   ├── quizzes/         # Generated quizzes (JSON)
│   └── results/         # Benchmark results
├── config/              # Configuration files
├── tests/               # Unit tests
└── main.py             # CLI entry point
```

## Usage

### Basic Usage

```bash
python main.py --config config/benchmark_example.yaml
```

### Advanced Options

```bash
# Use custom .env file
python main.py --config config/my_benchmark.yaml --env .env.production

# Skip aggregation (only save raw results)
python main.py --config config/my_benchmark.yaml --no-aggregate

# Custom output prefix
python main.py --config config/my_benchmark.yaml --output-prefix my_experiment
```

## Configuration

### Benchmark Configuration (YAML)

```yaml
benchmark:
  name: "my-benchmark"
  version: "1.0.0"
  runs: 5  # Number of evaluation runs

evaluators:
  gpt4:
    provider: "azure_openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"
    enabled: true

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

### Environment Variables

```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# OpenAI
OPENAI_API_KEY=your-api-key

# Anthropic
ANTHROPIC_API_KEY=your-api-key
```

## Available Metrics

### 1. Difficulty
Evaluates cognitive complexity using Bloom's Taxonomy or Webb's DOK.

**Parameters:**
- `rubric`: "bloom_taxonomy", "webb_dok", or "custom"
- `target_audience`: "high_school", "undergraduate", or "graduate"

**Scope:** Question-level

### 2. Coverage
Assesses how well the quiz covers the source material.

**Parameters:**
- `granularity`: "detailed", "balanced", or "broad"

**Scope:** Quiz-level

### 3. Clarity
Evaluates question and answer option clarity.

**Scope:** Question-level

## Adding Custom Metrics

1. Create a new metric class:

```python
# src/metrics/my_metric.py
from .base import BaseMetric, MetricScope

class MyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "my_metric"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    def get_prompt(self, question=None, quiz=None, source_text=None, **params):
        # Generate your prompt
        return f"Evaluate this question: {question.question_text}"

    def parse_response(self, llm_response: str) -> float:
        # Extract score from LLM response
        import re
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', llm_response)
        if match:
            return float(match.group(1))
        raise ValueError("Could not parse score")
```

2. Register in `main.py`:

```python
from src.metrics.my_metric import MyMetric

def register_metrics():
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(MyMetric)  # Add your metric
```

3. Use in configuration:

```yaml
metrics:
  - name: "my_metric"
    version: "1.0"
    evaluators: ["gpt4"]
    enabled: true
```

## Adding New LLM Providers

1. Create a provider class:

```python
# src/evaluators/my_provider.py
from .base import LLMProvider

class MyProvider(LLMProvider):
    def generate(self, prompt, temperature=None, max_tokens=None, **kwargs):
        # Implement your LLM API call
        response = my_api_call(prompt)
        return response
```

2. Register in factory:

```python
# In src/evaluators/factory.py
from .my_provider import MyProvider

_PROVIDER_MAP = {
    "my_provider": MyProvider,
    # ... existing providers
}
```

3. Use in configuration:

```yaml
evaluators:
  my_model:
    provider: "my_provider"
    model: "model-name"
    temperature: 0.0
```

## Output Files

After running a benchmark, you'll find:

- `results_<timestamp>.json`: Raw results from all runs
- `aggregated_<timestamp>.json`: Statistical aggregations
- `summary_<timestamp>.txt`: Human-readable summary

### Example Summary Output

```
======================================================================
BENCHMARK RESULTS SUMMARY
======================================================================
Configuration: example-benchmark
Version: 1.0.0
Total Runs: 3
Quizzes Evaluated: 2

DIFFICULTY
----------------------------------------------------------------------

  Evaluator: gpt-4
    Mean:   65.50
    Median: 67.00
    Std Dev: 8.23
    Min:    55.00
    Max:    74.00
    N:      12
```

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
ruff check src/
```

### Type Checking

```bash
mypy src/
```

## License

See LICENSE file for details.

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## Citation

If you use this benchmark in your research, please cite:

```bibtex
@software{quiz_benchmark,
  title={Quiz Generation Benchmark Framework},
  author={Your Name},
  year={2024},
  url={https://github.com/yourusername/quiz-benchmark}
}
```
