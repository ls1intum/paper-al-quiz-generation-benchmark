# Comprehensive Usage Guide

This guide covers all aspects of using the Quiz Generation Benchmark Framework.

## Table of Contents

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Data Preparation](#data-preparation)
4. [Running Benchmarks](#running-benchmarks)
5. [Understanding Results](#understanding-results)
6. [Customization](#customization)
7. [Best Practices](#best-practices)

## Installation

### Prerequisites

- Python 3.13 or higher
- pip package manager
- API keys for at least one LLM provider

### Setup Steps

```bash
# Clone repository
git clone <repository-url>
cd paper-al-quiz-generation-benchmark

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp config/.env.example .env
# Edit .env with your API keys
```

## Configuration

### Environment Variables (.env)

The `.env` file stores your API credentials:

```bash
# Azure OpenAI (for enterprise deployments, using v1 API)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key

# OpenAI (direct API)
OPENAI_API_KEY=sk-your-key-here

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Custom/Local models (optional)
CUSTOM_LLM_ENDPOINT=http://localhost:8000/v1
CUSTOM_LLM_API_KEY=optional-key
```

**Security Note:** Never commit `.env` to version control. It's listed in `.gitignore`.

### Benchmark Configuration (YAML)

Create YAML files in `config/` directory to define benchmark runs.

#### Basic Configuration

```yaml
benchmark:
  name: "basic-evaluation"
  version: "1.0.0"
  runs: 3

evaluators:
  gpt4:
    provider: "openai"
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

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

#### Advanced Configuration

```yaml
benchmark:
  name: "comprehensive-comparison"
  version: "2.0.0"
  runs: 5  # More runs for better statistics

evaluators:
  # Multiple models for comparison
  gpt4:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

  gpt35:
    provider: "openai"
    model: "gpt-3.5-turbo"
    temperature: 0.0
    max_tokens: 500

  claude_opus:
    provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.0
    max_tokens: 500

metrics:
  # Test difficulty with multiple evaluators
  - name: "difficulty"
    version: "1.0"
    evaluators: ["gpt4", "gpt35", "claude_opus"]
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"
    enabled: true

  # Test coverage with single best model
  - name: "coverage"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      granularity: "balanced"
    enabled: true

  # Test clarity across models
  - name: "clarity"
    version: "1.0"
    evaluators: ["gpt4", "claude_opus"]
    enabled: true

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

## Data Preparation

### Quiz JSON Format

Quizzes must be in JSON format with this schema:

```json
{
  "quiz_id": "unique_identifier",
  "title": "Human-readable title",
  "source_material": "filename.md",
  "questions": [
    {
      "question_id": "unique_question_id",
      "question_type": "single_choice | multiple_choice | true_false",
      "question_text": "The question text",
      "options": ["Option 1", "Option 2", "..."],
      "correct_answer": "For SC/TF" || ["For", "MC"],
      "source_reference": "Optional reference to source",
      "metadata": {}
    }
  ],
  "metadata": {
    "optional": "fields"
  },
  "created_at": "2024-01-15T10:00:00"
}
```

#### Question Types

**Single Choice** (one correct answer):
```json
{
  "question_type": "single_choice",
  "options": ["A", "B", "C", "D"],
  "correct_answer": "B"
}
```

**Multiple Choice** (multiple correct answers):
```json
{
  "question_type": "multiple_choice",
  "options": ["A", "B", "C", "D"],
  "correct_answer": ["B", "D"]
}
```

**True/False**:
```json
{
  "question_type": "true_false",
  "options": ["True", "False"],
  "correct_answer": "True"
}
```

### Source Material Format

Source materials should be Markdown files in `data/inputs/`:

```markdown
# Main Topic

## Section 1: Introduction

Content about the topic...

### Subsection 1.1

More detailed content...

## Section 2: Advanced Topics

Advanced content...
```

**Tips:**
- Use clear section headers
- Include all content that questions might reference
- Keep formatting simple (avoid complex tables/diagrams)
- Use the same structure as your educational materials

## Running Benchmarks

### Basic Execution

```bash
python main.py --config config/benchmark_example.yaml
```

### Command-Line Options

```bash
# Use custom .env file
python main.py --config config/my_benchmark.yaml --env .env.production

# Skip aggregation (save only raw results)
python main.py --config config/my_benchmark.yaml --no-aggregate

# Custom output filename prefix
python main.py --config config/my_benchmark.yaml --output-prefix experiment_001
```

### What Happens During Execution

1. **Initialization**
   - Loads configuration from YAML
   - Loads environment variables
   - Initializes LLM providers
   - Registers metrics

2. **Data Loading**
   - Loads all quizzes from `quiz_directory`
   - Loads corresponding source materials

3. **Evaluation Loop**
   - For each run (1 to `runs`)
     - For each quiz
       - For each metric
         - For each evaluator
           - Generates prompt
           - Calls LLM
           - Parses response
           - Records result

4. **Aggregation** (if enabled)
   - Groups results by metric and evaluator
   - Calculates statistics (mean, median, std dev, min, max)
   - Generates summary report

5. **Output**
   - Saves raw results JSON
   - Saves aggregated results JSON
   - Saves text summary

### Progress Monitoring

The framework prints progress information:

```
Registering metrics...
Available metrics: ['difficulty', 'coverage', 'clarity']

Loading configuration from config/benchmark_example.yaml...
Configuration loaded: example-benchmark v1.0.0
Runs: 3
Evaluators: ['gpt4', 'gpt35']
Metrics: ['difficulty', 'clarity']

Initializing benchmark runner...
Initialized evaluator: gpt4 (gpt-4)
Initialized evaluator: gpt35 (gpt-3.5-turbo)
Initialized metric: difficulty v1.0
Initialized metric: clarity v1.0

Starting benchmark execution...
Loading quizzes from data/quizzes...
Loaded 1 quizzes

============================================================
Starting Run 1/3
============================================================

Evaluating quiz: Python Fundamentals Quiz (quiz_example_001)
  Running difficulty with gpt4...
  Running difficulty with gpt35...
  Running clarity with gpt4...
  Running clarity with gpt35...
...
```

## Understanding Results

### Output Files

After execution, you'll find three files in `data/results/`:

1. **`results_<timestamp>.json`** - Raw results from all evaluations
2. **`aggregated_<timestamp>.json`** - Statistical aggregations
3. **`summary_<timestamp>.txt`** - Human-readable report

### Reading the Summary

```
======================================================================
BENCHMARK RESULTS SUMMARY
======================================================================
Configuration: example-benchmark
Version: 1.0.0
Total Runs: 3
Quizzes Evaluated: 1

DIFFICULTY
----------------------------------------------------------------------

  Evaluator: gpt-4
    Mean:   67.25    # Average difficulty score
    Median: 68.00    # Middle value (robust to outliers)
    Std Dev: 5.44    # Consistency (lower = more consistent)
    Min:    60.00    # Lowest score observed
    Max:    73.00    # Highest score observed
    N:      12       # Total number of evaluations

  Evaluator: gpt-3.5-turbo
    Mean:   64.50
    Median: 65.00
    Std Dev: 6.12
    Min:    55.00
    Max:    72.00
    N:      12
```

### Interpreting Results

#### Mean vs Median
- **Mean**: Average score, sensitive to outliers
- **Median**: Middle value, robust to outliers
- Large difference → check for outliers in raw data

#### Standard Deviation
- **Low (< 5)**: Consistent evaluations
- **Medium (5-10)**: Some variation
- **High (> 10)**: High variance, may need more runs

#### Comparing Evaluators
- Similar scores → models agree on metric
- Different scores → models have different perspectives
- Check std dev to assess reliability

### Raw Results Structure

```json
{
  "benchmark_id": "unique-run-id",
  "benchmark_version": "1.0.0",
  "config_hash": "abc123...",
  "quiz_id": "quiz_example_001",
  "run_number": 1,
  "metrics": [
    {
      "metric_name": "difficulty",
      "metric_version": "1.0",
      "score": 67.0,
      "evaluator_model": "gpt-4",
      "quiz_id": "quiz_example_001",
      "question_id": "q1",
      "parameters": {...},
      "evaluated_at": "2024-01-15T10:30:00",
      "raw_response": "LLM's actual response..."
    }
  ],
  "started_at": "2024-01-15T10:29:00",
  "completed_at": "2024-01-15T10:35:00"
}
```

## Customization

### Adding Custom Metrics

See [README.md#adding-custom-metrics](README.md#adding-custom-metrics) for detailed instructions.

Quick example:

```python
# src/metrics/validity.py
from .base import BaseMetric, MetricScope

class ValidityMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "validity"

    @property
    def version(self) -> str:
        return "1.0"

    @property
    def scope(self) -> MetricScope:
        return MetricScope.QUESTION_LEVEL

    def get_prompt(self, question=None, **params):
        return f"""Rate the validity of this question on a 0-100 scale.
Question: {question.question_text}
Answer options: {', '.join(question.options)}
Correct answer: {question.correct_answer}

Respond with only a number 0-100."""

    def parse_response(self, llm_response: str) -> float:
        import re
        match = re.search(r'\b(\d+(?:\.\d+)?)\b', llm_response)
        if match:
            return float(match.group(1))
        raise ValueError("Could not parse score")
```

Register in `main.py`:
```python
from src.metrics.validity import ValidityMetric

def register_metrics():
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)
    MetricRegistry.register(ValidityMetric)  # Add this
```

### Adding Custom Evaluators

See [README.md#adding-new-llm-providers](README.md#adding-new-llm-providers).

### Customizing Analysis

You can write custom analysis scripts:

```python
import json
from src.models.result import BenchmarkResult, MetricResult

# Load results
with open('data/results/results_20240115_103000.json') as f:
    results_data = json.load(f)

# Custom analysis
for result in results_data:
    quiz_id = result['quiz_id']
    for metric in result['metrics']:
        if metric['metric_name'] == 'difficulty':
            print(f"Quiz {quiz_id}, Q{metric['question_id']}: {metric['score']}")
```

## Best Practices

### 1. Configuration Management

- **Use descriptive names**: `config/gpt4_vs_claude_difficulty.yaml`
- **Version your configs**: Include version in benchmark config
- **Document parameters**: Add comments in YAML explaining choices

### 2. Reproducibility

- **Set temperature to 0.0**: For deterministic results
- **Use multiple runs**: At least 3-5 for reliable statistics
- **Save configurations**: Keep YAML files in version control
- **Record model versions**: Specify exact model names

### 3. Cost Management

- **Start small**: Test with 1-2 questions before full run
- **Use cheaper models first**: gpt-3.5-turbo for initial testing
- **Monitor API usage**: Check your provider dashboards
- **Cache results**: Save outputs to avoid re-running

### 4. Data Quality

- **Validate quizzes**: Ensure JSON format is correct
- **Check source alignment**: Verify source_material paths exist
- **Review questions**: Ensure questions are well-formed
- **Test incrementally**: Add quizzes gradually

### 5. Metric Selection

- **Choose relevant metrics**: Not all metrics apply to all quizzes
- **Start with core metrics**: Difficulty, coverage, clarity
- **Add domain-specific metrics**: Create custom metrics for your needs
- **Validate metric prompts**: Test prompts manually first

### 6. Result Interpretation

- **Look at trends**: Compare across multiple quizzes
- **Check consistency**: Low std dev indicates reliable metric
- **Cross-validate**: Use multiple evaluators for important metrics
- **Review outliers**: Examine questions with extreme scores
- **Context matters**: Scores depend on target audience and domain

### 7. Troubleshooting

**High variance in results?**
- Increase number of runs
- Check prompt clarity
- Try different evaluators

**Unexpected scores?**
- Review raw LLM responses in results JSON
- Test metric prompt manually
- Verify source material quality

**API errors?**
- Check API key validity
- Verify rate limits
- Ensure sufficient credits

**Memory issues?**
- Process quizzes in batches
- Reduce max_tokens
- Use lighter models

## Example Workflows

### Workflow 1: Quick Evaluation

```bash
# 1. Create minimal config
cat > config/quick_test.yaml << EOF
benchmark:
  name: "quick-test"
  version: "1.0.0"
  runs: 1

evaluators:
  gpt35:
    provider: "openai"
    model: "gpt-3.5-turbo"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["gpt35"]

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"
outputs:
  results_directory: "data/results"
EOF

# 2. Run
python main.py --config config/quick_test.yaml

# 3. View results
cat data/results/summary_*.txt
```

### Workflow 2: Comprehensive Comparison

```bash
# Use comprehensive config with multiple evaluators
python main.py --config config/comprehensive.yaml --output-prefix comparison_v1

# Analyze results
python -c "
import json
with open('data/results/aggregated_comparison_v1.json') as f:
    data = json.load(f)
    for metric, values in data['aggregations'].items():
        print(f'{metric}: {values[\"mean\"]:.2f} ± {values[\"std_dev\"]:.2f}')
"
```

### Workflow 3: Iterative Development

```bash
# 1. Test new metric with one evaluator
python main.py --config config/test_new_metric.yaml

# 2. Review results
cat data/results/summary_*.txt

# 3. Refine metric implementation
# Edit src/metrics/my_metric.py

# 4. Re-run
python main.py --config config/test_new_metric.yaml

# 5. Compare results
diff data/results/summary_*.txt
```

## Getting Help

- **Documentation**: See README.md and ARCHITECTURE.md
- **Examples**: Check files in config/, data/quizzes/, data/inputs/
- **Issues**: GitHub issues for bug reports
- **Community**: Discussions for questions and ideas
