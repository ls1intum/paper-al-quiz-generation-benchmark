---
sidebar_position: 1
slug: /
title: AI Quiz Generation Benchmark Documentation
hide_table_of_contents: false
---

# AI Quiz Generation Benchmark

**Complete Documentation for Evaluating AI-Generated Quizzes Using LLMs as Judges**

---

## 📋 Table of Contents

- [Overview](#overview)
- [System Goals](#system-goals)
- [Quick Start](#quick-start)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running Your First Benchmark](#running-your-first-benchmark)
  - [Viewing Results](#viewing-results)
- [Complete Usage Guide](#complete-usage-guide)
  - [Environment Variables](#environment-variables)
  - [Benchmark Configuration](#benchmark-configuration)
  - [Data Preparation](#data-preparation)
  - [Running Benchmarks](#running-benchmarks)
  - [Understanding Results](#understanding-results)
  - [Command-Line Options](#command-line-options)
- [Customization](#customization)
  - [Adding Custom Metrics](#adding-custom-metrics)
  - [Adding Custom Evaluators](#adding-custom-evaluators)
  - [Customizing Analysis](#customizing-analysis)
- [Architecture](#architecture)
  - [System Overview](#system-overview)
  - [Component Design](#component-design)
  - [Project Structure](#project-structure)
  - [Workflow](#workflow)
- [Best Practices](#best-practices)
- [Project Status](#project-status)
- [Troubleshooting](#troubleshooting)

---

## Overview

This benchmark framework evaluates AI-generated quizzes using multiple LLM-based metrics. The system is **stateless**, **modular**, and designed for **extensibility**.

### What This Framework Does

Evaluate the quality of AI-generated quizzes using configurable metrics such as:
- **Difficulty**: Cognitive complexity assessment
- **Coverage**: Breadth and depth of content coverage
- **Clarity**: Question and answer clarity
- **Validity**: Alignment with learning objectives
- **And more**: Easily extensible with custom metrics

### Key Features

✅ **Multiple LLM Support** - Azure OpenAI, OpenAI API, Anthropic Claude, and OpenAI-compatible local models

✅ **Flexible Configuration** - YAML-based configs for easy experimentation

✅ **Statistical Rigor** - Multiple runs with aggregation (mean, median, std dev)

✅ **Reproducible Results** - Versioned configs, deterministic evaluation (temperature=0.0)

✅ **Clean Architecture** - Type-safe Python with clear interfaces

✅ **Production Ready** - Complete with examples, tests, and documentation

### Terminology

- **Metric**: A measurement of quiz quality (e.g., difficulty, coverage, clarity)
- **Evaluator**: An LLM provider that executes metric assessments
- **Benchmark Run**: A complete evaluation cycle with specific configuration
- **Quiz**: A collection of questions generated from source material
- **Question**: Individual quiz item (multiple-choice, single-choice, true/false)

---

## System Goals

1. **Evaluate quiz quality** using configurable metrics (difficulty, coverage, etc.)
2. **Support multiple LLM providers** (Azure OpenAI, OpenAI, Anthropic, open-source)
3. **Enable flexible configuration** for different benchmark runs
4. **Provide reproducible results** with versioning and aggregation
5. **Maintain clean architecture** with clear interfaces and type safety

---

## Quick Start

Get your quiz benchmark running in 5 minutes!

### Installation

#### Prerequisites

- Python 3.10 or higher
- pip package manager
- API keys for at least one LLM provider

#### Setup Steps

```bash
# Clone repository
git clone <repository-url>
cd paper-al-quiz-generation-benchmark

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

#### Step 1: Set Up Environment Variables

```bash
# Copy template
cp config/.env.example .env

# Edit with your API keys (at minimum, one provider)
nano .env
```

Example `.env` file:
```bash
# OpenAI (direct API)
OPENAI_API_KEY=sk-your-key-here

# Or Azure OpenAI (for enterprise deployments)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# Or Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**Security Note:** Never commit `.env` to version control. It's already listed in `.gitignore`.

#### Step 2: Configure Benchmark Settings

The repository includes an example configuration. If you only have OpenAI configured, edit `config/benchmark_example.yaml`:

```yaml
benchmark:
  name: "example-benchmark"
  version: "1.0.0"
  runs: 3

evaluators:
  gpt4:
    provider: "openai"  # or "azure_openai" or "anthropic"
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

  - name: "clarity"
    version: "1.0"
    evaluators: ["gpt4"]

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

### Running Your First Benchmark

The repository includes example quiz and source material. Just run:

```bash
python main.py --config config/benchmark_example.yaml
```

### Viewing Results

Results are saved to `data/results/`:

```bash
# View the human-readable summary
cat data/results/summary_*.txt

# View raw JSON results
cat data/results/results_*.json

# View aggregated statistics
cat data/results/aggregated_*.json
```

### What's Happening?

1. **Loading**: Reads `data/quizzes/example_quiz.json` and `data/inputs/python_intro.md`
2. **Evaluating**: Each configured metric runs with each configured evaluator
3. **Repeating**: The benchmark runs multiple times (configured via `runs` in YAML)
4. **Aggregating**: Statistics (mean, median, std dev) are calculated across runs
5. **Reporting**: Results are saved as JSON and human-readable text

---

## Complete Usage Guide

### Environment Variables

The `.env` file stores your API credentials:

```bash
# Azure OpenAI (for enterprise deployments)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# OpenAI (direct API)
OPENAI_API_KEY=sk-your-key-here

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Custom/Local models (optional)
CUSTOM_LLM_ENDPOINT=http://localhost:8000/v1
CUSTOM_LLM_API_KEY=optional-key
```

### Benchmark Configuration

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

For comparing multiple models:

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

### Data Preparation

#### Quiz JSON Format

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

#### Source Material Format

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

### Running Benchmarks

#### Basic Execution

```bash
python main.py --config config/benchmark_example.yaml
```

#### Command-Line Options

```bash
# Use custom .env file
python main.py --config config/my_benchmark.yaml --env .env.production

# Skip aggregation (save only raw results)
python main.py --config config/my_benchmark.yaml --no-aggregate

# Custom output filename prefix
python main.py --config config/my_benchmark.yaml --output-prefix experiment_001
```

#### What Happens During Execution

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

#### Progress Monitoring

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

### Understanding Results

#### Output Files

After execution, you'll find three files in `data/results/`:

1. **`results_<timestamp>.json`** - Raw results from all evaluations
2. **`aggregated_<timestamp>.json`** - Statistical aggregations
3. **`summary_<timestamp>.txt`** - Human-readable report

#### Reading the Summary

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

#### Interpreting Results

**Mean vs Median**
- **Mean**: Average score, sensitive to outliers
- **Median**: Middle value, robust to outliers
- Large difference → check for outliers in raw data

**Standard Deviation**
- **Low (< 5)**: Consistent evaluations
- **Medium (5-10)**: Some variation
- **High (> 10)**: High variance, may need more runs

**Comparing Evaluators**
- Similar scores → models agree on metric
- Different scores → models have different perspectives
- Check std dev to assess reliability

#### Raw Results Structure

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

---

## Customization

### Adding Custom Metrics

#### Step 1: Create Metric Class

Create a new file `src/metrics/validity.py`:

```python
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

#### Step 2: Register Metric

In `main.py`:

```python
from src.metrics.validity import ValidityMetric

def register_metrics():
    MetricRegistry.register(DifficultyMetric)
    MetricRegistry.register(CoverageMetric)
    MetricRegistry.register(ClarityMetric)
    MetricRegistry.register(ValidityMetric)  # Add this
```

#### Step 3: Use in Config

```yaml
metrics:
  - name: "validity"
    version: "1.0"
    evaluators: ["gpt4"]
```

### Adding Custom Evaluators

#### Step 1: Create Provider Class

Create `src/evaluators/custom_provider.py`:

```python
from .base import LLMProvider

class CustomProvider(LLMProvider):
    def __init__(self, api_key: str, endpoint: str, model: str):
        self.api_key = api_key
        self.endpoint = endpoint
        self.model = model

    def generate(self, prompt: str, temperature: float = 0.0, 
                 max_tokens: int = 1000, **kwargs) -> str:
        # Implement your API call here
        pass

    @property
    def model_name(self) -> str:
        return self.model
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
        # ... other providers
```

#### Step 3: Use in Config

```yaml
evaluators:
  my_custom:
    provider: "custom"
    model: "my-model-name"
    temperature: 0.0
    max_tokens: 500
```

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

---

## Architecture

### System Overview

```
┌─────────────────┐
│  Input Sources  │ (Markdown files: lectures, exercises, competencies)
└────────┬────────┘
         │
         │ (External Quiz Generation - not part of this system)
         │
         ▼
┌─────────────────┐
│Generated Quizzes│ (Standardized JSON format)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────┐
│            BENCHMARK SYSTEM                          │
│                                                      │
│  ┌──────────────┐      ┌─────────────────┐         │
│  │   Config     │──────▶│  Benchmark      │         │
│  │   Loader     │      │  Runner         │         │
│  └──────────────┘      └────────┬────────┘         │
│                                  │                   │
│                        ┌─────────▼────────┐         │
│                        │  Metric Engine   │         │
│                        └────────┬─────────┘         │
│                                 │                    │
│          ┌──────────────────────┼──────────┐        │
│          │                      │          │        │
│     ┌────▼─────┐          ┌────▼────┐ ┌───▼────┐  │
│     │ Metric A │          │Metric B │ │Metric C│  │
│     └────┬─────┘          └────┬────┘ └───┬────┘  │
│          │                     │           │        │
│          └──────────┬──────────┴───────────┘        │
│                     │                                │
│              ┌──────▼──────┐                        │
│              │  LLM        │                        │
│              │  Strategy   │                        │
│              └──────┬──────┘                        │
│                     │                                │
│       ┌─────────────┼─────────────┐                 │
│       │             │             │                 │
│  ┌────▼────┐  ┌────▼────┐  ┌────▼────┐            │
│  │ Azure   │  │ OpenAI  │  │Anthropic│            │
│  │ OpenAI  │  │   API   │  │  Claude │            │
│  └─────────┘  └─────────┘  └─────────┘            │
│                                                      │
│              ┌──────────────┐                       │
│              │   Results    │                       │
│              │  Aggregator  │                       │
│              └──────┬───────┘                       │
└─────────────────────┼────────────────────────────────┘
                      │
                      ▼
              ┌───────────────┐
              │ JSON Results  │ (Timestamped, versioned)
              └───────────────┘
```

### Component Design

#### 1. Data Models (`src/models/`)

**Quiz Schema**
```python
@dataclass
class QuizQuestion:
    question_id: str
    question_type: Literal["multiple_choice", "single_choice", "true_false"]
    question_text: str
    options: List[str]
    correct_answer: Union[str, List[str]]
    source_reference: Optional[str]
    metadata: Dict[str, Any]

@dataclass
class Quiz:
    quiz_id: str
    title: str
    source_material: str
    questions: List[QuizQuestion]
    metadata: Dict[str, Any]
    created_at: datetime
```

**Result Schema**
```python
@dataclass
class MetricResult:
    metric_name: str
    metric_version: str
    score: float  # 0-100
    evaluator_model: str
    question_id: Optional[str]
    quiz_id: str
    parameters: Dict[str, Any]
    evaluated_at: datetime
    raw_response: Optional[str]

@dataclass
class BenchmarkResult:
    benchmark_id: str
    benchmark_version: str
    config_hash: str
    quiz_id: str
    metrics: List[MetricResult]
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any]
```

#### 2. Metric Interface (`src/metrics/`)

```python
from abc import ABC, abstractmethod
from enum import Enum

class MetricScope(Enum):
    QUESTION_LEVEL = "question"
    QUIZ_LEVEL = "quiz"

class BaseMetric(ABC):
    """Abstract base class for all metrics"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Metric identifier"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Metric version for result tracking"""
        pass

    @property
    @abstractmethod
    def scope(self) -> MetricScope:
        """Whether metric operates on questions or entire quiz"""
        pass

    @abstractmethod
    def get_prompt(self,
                   question: Optional[QuizQuestion] = None,
                   quiz: Optional[Quiz] = None,
                   source_text: Optional[str] = None,
                   **params) -> str:
        """Generate LLM prompt for evaluation"""
        pass

    @abstractmethod
    def parse_response(self, llm_response: str) -> float:
        """Parse LLM response to extract 0-100 score"""
        pass
```

#### 3. LLM Provider Abstraction (`src/evaluators/`)

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """Abstract base class for LLM providers using Strategy pattern"""

    @abstractmethod
    def generate(self,
                 prompt: str,
                 temperature: float = 0.0,
                 max_tokens: int = 1000,
                 **kwargs) -> str:
        """Generate response from LLM"""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return model identifier"""
        pass
```

#### 4. Benchmark Runner (`src/runners/`)

```python
class BenchmarkRunner:
    """Orchestrates benchmark execution"""

    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.metrics: Dict[str, BaseMetric] = {}
        self.evaluators: Dict[str, LLMProvider] = {}

    def run(self, quizzes: List[Quiz]) -> List[BenchmarkResult]:
        """Execute benchmark for all quizzes"""
        pass

    def evaluate_quiz(self, quiz: Quiz, run_number: int) -> BenchmarkResult:
        """Evaluate single quiz with all configured metrics"""
        pass
```

### Project Structure

```
paper-al-quiz-generation-benchmark/
├── src/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── quiz.py           # Quiz and Question schemas
│   │   ├── result.py         # Result schemas
│   │   └── config.py         # Configuration models
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseMetric interface
│   │   ├── difficulty.py     # Difficulty metric implementation
│   │   ├── coverage.py       # Coverage metric implementation
│   │   ├── clarity.py        # Clarity metric implementation
│   │   └── registry.py       # Metric registration and discovery
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── base.py           # LLMProvider interface
│   │   ├── azure_openai.py
│   │   ├── openai.py
│   │   ├── anthropic.py
│   │   ├── openai_compatible.py
│   │   └── factory.py        # LLMProviderFactory
│   ├── runners/
│   │   ├── __init__.py
│   │   └── benchmark.py      # BenchmarkRunner
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── aggregator.py     # Results aggregation
│   │   └── reporter.py       # Report generation
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py  # YAML config loading
│       └── io.py             # File I/O utilities
├── data/
│   ├── inputs/               # Source markdown files
│   ├── quizzes/              # Generated quizzes (JSON)
│   └── results/              # Benchmark results
├── config/
│   ├── benchmark_example.yaml
│   └── .env.example
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_metrics.py
│   ├── test_evaluators.py
│   └── test_integration.py
├── .env
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── main.py                   # CLI entry point
```

### Workflow

1. **Setup**: Install dependencies, configure API keys
2. **Prepare Data**: Add markdown source files and quiz JSONs
3. **Run Benchmark**: Execute with YAML config
4. **View Results**: Analyze JSON results and text summaries

### Key Design Decisions

1. **Stateless Design**: No persistent state between runs; all context in config
2. **Strategy Pattern**: Easy swapping of LLM providers per metric
3. **Type Safety**: Full type hints with Python dataclasses
4. **Deterministic**: Fixed temperature=0.0, versioned configs, timestamped results
5. **Extensible**: Clear interfaces for metrics and evaluators
6. **Reproducible**: Config hashing, version tracking, complete result metadata

### Supported Metrics

#### Difficulty (Question-Level)
- Bloom's Taxonomy evaluation
- Webb's Depth of Knowledge
- Parameterizable rubric and target audience

#### Coverage (Quiz-Level)
- Breadth and depth analysis
- Source material alignment
- Configurable granularity

#### Clarity (Question-Level)
- Question wording assessment
- Answer option quality
- Ambiguity detection

---

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

---

## Project Status

### ✅ Implementation Complete

All planned components have been implemented and are ready to use.

#### Core Components

✅ **Data Models** (`src/models/`) - Quiz, Question, Result schemas with validation

✅ **LLM Evaluators** (`src/evaluators/`) - Azure OpenAI, OpenAI, Anthropic, OpenAI-compatible

✅ **Metrics** (`src/metrics/`) - Difficulty, Coverage, Clarity with extensible interface

✅ **Benchmark Runner** (`src/runners/`) - Complete orchestration of evaluation workflow

✅ **Analysis & Reporting** (`src/analysis/`) - Statistical aggregation and report generation

✅ **Utilities** (`src/utils/`) - Config loading, JSON I/O

✅ **Main Application** (`main.py`) - CLI entry point with full argument parsing

#### Documentation

✅ Comprehensive README
✅ Detailed architecture documentation
✅ Quick start guide
✅ Complete usage reference

#### Configuration & Examples

✅ Example configuration files
✅ Example quiz and source material
✅ Environment template

#### Testing

✅ Unit tests for data models
✅ Test infrastructure ready for expansion

### 📊 Key Features

- **Clean Architecture** - Strategy pattern, type-safe Python
- **Flexible Configuration** - YAML-based benchmark configs
- **Statistical Rigor** - Multiple runs with aggregation
- **Extensibility** - Easy to add metrics and providers
- **Production Ready** - Complete with examples and tests

### 🚀 Ready to Use

The framework is **production-ready** and can be used immediately:

```bash
# Install
pip install -r requirements.txt

# Configure
cp config/.env.example .env
# Add your API keys to .env

# Run
python main.py --config config/benchmark_example.yaml

# View results
cat data/results/summary_*.txt
```

### 📦 Dependencies

All managed via `requirements.txt`:
- LangChain (LLM abstraction)
- Pydantic (data validation)
- PyYAML (config loading)
- python-dotenv (environment management)
- OpenAI SDK
- Anthropic SDK
- pytest (testing)

---

## Troubleshooting

### "Module not found" errors

```bash
# Make sure you're in the virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### API Key errors

- Check that your `.env` file is in the root directory
- Verify your API keys are correct
- Make sure the provider in your YAML matches what's configured in `.env`

### No quizzes found

- Ensure quiz JSON files are in `data/quizzes/`
- Check that the JSON format is valid
- Verify `source_material` field points to an existing file in `data/inputs/`

### High variance in results?

- Increase number of runs
- Check prompt clarity
- Try different evaluators

### Unexpected scores?

- Review raw LLM responses in results JSON
- Test metric prompt manually
- Verify source material quality

### API errors?

- Check API key validity
- Verify rate limits
- Ensure sufficient credits

### Memory issues?

- Process quizzes in batches
- Reduce max_tokens
- Use lighter models

---

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

---

## Getting Help

### Documentation Resources

- This comprehensive guide covers all aspects of the framework
- Check example files in `config/`, `data/quizzes/`, `data/inputs/`
- Review configuration in `config/benchmark_example.yaml`
- Examine source code in `src/` for implementation details

### Common Questions

**Q: How do I add a new metric?**
A: See the [Adding Custom Metrics](#adding-custom-metrics) section above.

**Q: Can I use local/open-source models?**
A: Yes! Use the `openai_compatible` provider with any OpenAI-compatible API endpoint.

**Q: How many runs should I use?**
A: Start with 3-5 runs. Increase if you see high variance (std dev > 10).

**Q: Which model should I use as evaluator?**
A: GPT-4 provides most reliable results. GPT-3.5-turbo is cheaper for testing. Compare multiple models for validation.

**Q: How do I interpret the scores?**
A: Scores are 0-100. Higher is better (more difficult, better coverage, clearer). Compare relative scores, not absolute values.

---

## Future Enhancement Ideas

The framework is complete but can be extended with:

- Additional metrics (validity, discrimination, distractor quality)
- Caching layer for LLM responses
- Database backend option
- Web UI for result visualization
- Comparison reports between benchmark versions
- Export to CSV/Excel
- Integration with quiz generation systems
- Batch processing optimizations
- Support for more LLM providers
- Automated metric validation
- Statistical significance testing

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{quiz_benchmark_2024,
  title = {AI Quiz Generation Benchmark Framework},
  author = {[Your Name]},
  year = {2024},
  url = {[Your Repository URL]}
}
```

---

## License

[Specify your license here]

---

## Contact

For questions, issues, or contributions, please:

- Open an issue on GitLab: [Your Repository URL]
- Contact: [Your Email]

---

**Status**: ✅ **COMPLETE AND READY FOR USE**

All requirements have been implemented with clean architecture, full type safety, and comprehensive documentation.