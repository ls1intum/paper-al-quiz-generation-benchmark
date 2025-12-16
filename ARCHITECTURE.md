# Quiz Generation Benchmark Architecture

## Overview

This benchmark framework evaluates AI-generated quizzes using multiple LLM-based metrics. The system is stateless, modular, and designed for extensibility.

## System Goals

1. **Evaluate quiz quality** using configurable metrics (difficulty, coverage, etc.)
2. **Support multiple LLM providers** (Azure OpenAI, OpenAI, Anthropic, open-source)
3. **Enable flexible configuration** for different benchmark runs
4. **Provide reproducible results** with versioning and aggregation
5. **Maintain clean architecture** with clear interfaces and type safety

## Terminology

### Core Concepts

- **Metric**: A measurement of quiz quality (e.g., difficulty, coverage, clarity)
- **Evaluator**: An LLM provider that executes metric assessments
- **Benchmark Run**: A complete evaluation cycle with specific configuration
- **Quiz**: A collection of questions generated from source material
- **Question**: Individual quiz item (multiple-choice, single-choice, true/false)

### Proposed Metrics (Initial Set)

Based on quiz evaluation literature, we'll support:

1. **Difficulty**: Cognitive complexity and expected difficulty level
2. **Coverage**: Breadth and depth of content coverage from source material
3. **Clarity**: Question and answer option clarity
4. **Validity**: Alignment with learning objectives
5. **Distractor Quality**: Quality of incorrect options (for MC questions)
6. **Discrimination**: Ability to distinguish knowledge levels

*Note: Metrics are pluggable and will be refined based on literature review*

## Architecture Overview

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

## Component Design

### 1. Data Models (`src/models/`)

#### Quiz Schema
```python
@dataclass
class QuizQuestion:
    question_id: str
    question_type: Literal["multiple_choice", "single_choice", "true_false"]
    question_text: str
    options: List[str]  # For MC/SC: list of options; For T/F: ["True", "False"]
    correct_answer: Union[str, List[str]]  # Single answer or list for MC
    source_reference: Optional[str]  # Reference to source material
    metadata: Dict[str, Any]  # Extensible metadata

@dataclass
class Quiz:
    quiz_id: str
    title: str
    source_material: str  # Reference to input markdown file
    questions: List[QuizQuestion]
    metadata: Dict[str, Any]
    created_at: datetime
```

#### Result Schema
```python
@dataclass
class MetricResult:
    metric_name: str
    metric_version: str
    score: float  # 0-100
    evaluator_model: str
    question_id: Optional[str]  # None if quiz-level metric
    quiz_id: str
    parameters: Dict[str, Any]  # Metric-specific parameters
    evaluated_at: datetime
    raw_response: Optional[str]  # LLM raw output for debugging

@dataclass
class BenchmarkResult:
    benchmark_id: str
    benchmark_version: str
    config_hash: str  # Hash of config for reproducibility
    quiz_id: str
    metrics: List[MetricResult]
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any]

@dataclass
class AggregatedResults:
    benchmark_config_name: str
    quiz_ids: List[str]
    num_runs: int
    aggregations: Dict[str, MetricAggregation]  # metric_name -> aggregation

@dataclass
class MetricAggregation:
    metric_name: str
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    per_run_scores: List[float]
```

### 2. Metric Interface (`src/metrics/`)

```python
from abc import ABC, abstractmethod
from enum import Enum

class MetricScope(Enum):
    QUESTION_LEVEL = "question"
    QUIZ_LEVEL = "quiz"

class MetricParameter:
    """Defines a configurable parameter for a metric"""
    name: str
    type: type
    default: Any
    description: str

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

    @property
    def parameters(self) -> List[MetricParameter]:
        """Configurable parameters for this metric"""
        return []

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

    def validate_params(self, **params) -> None:
        """Validate provided parameters"""
        pass
```

### 3. LLM Provider Abstraction (`src/evaluators/`)

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

class AzureOpenAIProvider(LLMProvider):
    """Azure OpenAI implementation"""
    pass

class OpenAIProvider(LLMProvider):
    """OpenAI API implementation"""
    pass

class AnthropicProvider(LLMProvider):
    """Anthropic Claude implementation"""
    pass

class OpenAICompatibleProvider(LLMProvider):
    """Generic provider for OpenAI-compatible APIs (local models)"""
    pass

class LLMProviderFactory:
    """Factory to create LLM providers from config"""

    @staticmethod
    def create(provider_config: Dict[str, Any]) -> LLMProvider:
        pass
```

### 4. Benchmark Runner (`src/runners/`)

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

### 5. Configuration (`config/`)

#### Benchmark Config (YAML)
```yaml
benchmark:
  name: "gpt4-vs-gpt35-difficulty"
  version: "1.0.0"
  runs: 5  # Number of times to repeat evaluation

evaluators:
  gpt4:
    provider: "azure_openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

  gpt35:
    provider: "azure_openai"
    model: "gpt-3.5-turbo"
    temperature: 0.0
    max_tokens: 500

  claude:
    provider: "anthropic"
    model: "claude-3-opus-20240229"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["gpt4", "gpt35"]  # Run with both models
    parameters:
      rubric: "bloom_taxonomy"

  - name: "coverage"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      granularity: "detailed"

  - name: "clarity"
    version: "1.0"
    evaluators: ["claude"]

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
  aggregate: true
```

#### Environment Variables (`.env`)
```bash
# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview

# OpenAI
OPENAI_API_KEY=your-api-key

# Anthropic
ANTHROPIC_API_KEY=your-api-key

# Custom endpoints
CUSTOM_LLM_ENDPOINT=http://localhost:8000/v1
CUSTOM_LLM_API_KEY=optional-key
```

## Project Structure

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
│   │   └── .gitkeep
│   ├── quizzes/              # Generated quizzes (JSON)
│   │   └── .gitkeep
│   └── results/              # Benchmark results
│       └── .gitkeep
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
├── README.md
├── ARCHITECTURE.md
└── main.py                   # CLI entry point
```

## Workflow

### 1. Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp config/.env.example .env
# Edit .env with your API keys

# Prepare data
mkdir -p data/inputs data/quizzes data/results
# Add markdown source files to data/inputs/
# Add generated quizzes to data/quizzes/
```

### 2. Run Benchmark
```bash
python main.py --config config/benchmark_example.yaml
```

### 3. View Results
```bash
# Results stored in data/results/ with timestamp
# - individual_results_{timestamp}.json (all raw results)
# - aggregated_results_{timestamp}.json (statistics)
# - report_{timestamp}.json (human-readable summary)
```

## Extensibility Points

### Adding New Metrics
1. Create new class inheriting from `BaseMetric`
2. Implement required methods (name, version, scope, get_prompt, parse_response)
3. Register in `src/metrics/registry.py`
4. Add to benchmark config YAML

### Adding New LLM Providers
1. Create new class inheriting from `LLMProvider`
2. Implement `generate()` and `model_name` methods
3. Register in `LLMProviderFactory`
4. Add credentials to `.env`

### Adding New Aggregations
1. Extend `MetricAggregation` dataclass
2. Update `Aggregator` class in `src/analysis/aggregator.py`

## Key Design Decisions

1. **Stateless Design**: No persistent state between runs; all context in config
2. **Strategy Pattern**: Easy swapping of LLM providers per metric
3. **Type Safety**: Full type hints with Python dataclasses
4. **Deterministic**: Fixed temperature=0.0, versioned configs, timestamped results
5. **Extensible**: Clear interfaces for metrics and evaluators
6. **Reproducible**: Config hashing, version tracking, complete result metadata

## Dependencies

- **langchain**: LLM provider abstraction
- **pydantic**: Data validation and settings
- **pyyaml**: Configuration loading
- **python-dotenv**: Environment variable management
- **pandas**: Results analysis (optional)
- **pytest**: Testing

## Next Steps

1. Implement core data models
2. Create LLM provider abstractions
3. Build metric interface and 2-3 initial metrics
4. Implement benchmark runner
5. Add results aggregation
6. Write tests
7. Create documentation and examples
