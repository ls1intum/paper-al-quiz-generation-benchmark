---
title: Architecture
sidebar_position: 1
---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                           INPUT LAYER                            │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│      ┌──────────────────┐              ┌──────────────────┐      │
│      │  Source Material │              │ Learning         │      │
│      │  (Markdown)      │              │ Objectives       │      │
│      │                  │              │                  │      │
│      │  • Lectures      │              │ • Competencies   │      │
│      │  • Textbooks     │              │ • Goals          │      │
│      │  • Exercises     │              │ • Outcomes       │      │
│      └──────────────────┘              └──────────────────┘      │
│                                                                  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 │ (External Quiz Generation - not included)
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                          QUIZ ARTIFACTS                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│     ┌──────────────────────────────────────────────────────┐     │
│     │   Generated Quizzes (Standardized JSON Format)       │     │
│     │                                                      │     │
│     │  • Question ID, Type, Text                           │     │
│     │  • Options & Correct Answers                         │     │
│     │  • Source References                                 │     │
│     │  • Metadata (Bloom level, difficulty, etc.)          │     │
│     └──────────────────────────────────────────────────────┘     │
│                                                                  │
└───────────────────────────────┬──────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────┐
│                  BENCHMARK SYSTEM CORE                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐         ┌──────────────────────┐            │
│  │  Configuration  │────────▶│  Benchmark Runner    │            │
│  │  Loader (YAML)  │         │                      │            │
│  └─────────────────┘         │  • Orchestration     │            │
│                              │  • Multi-run Logic   │            │
│                              │  • Result Collection │            │
│                              └───────────┬──────────┘            │
│                                          │                       │
│                                          ▼                       │
│                               ┌──────────────────────┐           │
│                               │  Metric Engine       │           │
│                               │                      │           │
│                               │  • Metric Registry   │           │
│                               │  • Prompt Generation │           │
│                               │  • Response Parsing  │           │
│                               └──────────┬───────────┘           │
│                                          │                       │
│                         ┌────────────────┼────────────────┐      │
│                         │                │                │      │
│                    ┌────▼─────┐     ┌────▼────┐      ┌────▼────┐ │
│                    │Alignment │     │Clarity  │      │Distrac- │ │
│                    │          │     │         │      │tor Qual.│ │
│                    └────┬─────┘     └────┬────┘      └────┬────┘ │
│                         │                │                │      │
│                    ┌────▼─────┐     ┌────▼────┐      ┌────▼────┐ │
│                    │Cognitive │     │Answer   │      │Cueing   │ │
│                    │Level     │     │Correct. │      │Absence  │ │
│                    └────┬─────┘     └────┬────┘      └────┬────┘ │
│                         │                │                │      │
│                         └────────────────│────────────────┘      │
│                                          │                       │
│                                          ▼                       │
│                                  ┌─────────────────┐             │
│                                  │  LLM Strategy   │             │
│                                  │  (Provider      │             │
│                                  │   Abstraction)  │             │
│                                  └────────┬────────┘             │
│                                           │                      │
│                         ┌─────────────────┼─────────────────┐    │
│                         │                 │                 │    │
│                    ┌────▼────┐       ┌────▼────┐      ┌────▼────┐│                 
│                    │ OpenAI  │       │ Direct  │      │ Claude  ││
│                    └─────────┘       └─────────┘      └─────────┘│
│                                                                  │
│                         ┌─────────────────┐                      │
│                         │  Results        │                      │
│                         │  Aggregator     │                      │
│                         │                 │                      │
│                         │  • Statistics   │                      │
│                         │  • Reports      │                      │
│                         │  • Visualization│                      │
│                         └────────┬────────┘                      │
│                                  │                               │
└──────────────────────────────────┼───────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────┐
│                            OUTPUT LAYER                          │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│            ┌──────────────────┐    ┌──────────────────┐          │
│            │  Raw Results     │    │  Aggregated      │          │
│            │  (JSON)          │    │  Statistics      │          │
│            │                  │    │  (JSON)          │          │
│            │  • All runs      │    │                  │          │
│            │  • Timestamps    │    │  • Mean, Median  │          │
│            │  • Raw responses │    │  • Std Dev       │          │
│            └──────────────────┘    │  • Min, Max      │          │
│                                    └──────────────────┘          │
│                                                                  │
│             ┌─────────────────────────────────────────┐          │
│             │  Human-Readable Summary (TXT)           │          │
│             │                                         │          │
│             │  • Metric-by-metric breakdown           │          │
│             │  • Evaluator comparisons                │          │
│             │  • Statistical summaries                │          │
│             └─────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────v────────────────┘
```

### Component Design

#### 1. Data Models (`src/models/`)

**Quiz Schema**

```python
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Union, Literal
from datetime import datetime

@dataclass
class QuizQuestion:
    question_id: str
    question_type: Literal["multiple_choice", "single_choice", "true_false"]
    question_text: str
    options: List[str]
    correct_answer: Union[str, List[str]]
    source_reference: Optional[str] = None
    bloom_level: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class Quiz:
    quiz_id: str
    title: str
    source_material: str
    questions: List[QuizQuestion]
    learning_objectives: Optional[List[str]] = None
    metadata: Dict[str, Any] = None
    created_at: datetime = None
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
    raw_response: Optional[str] = None
    evaluation_details: Optional[Dict[str, Any]] = None

@dataclass
class BenchmarkResult:
    benchmark_id: str
    benchmark_version: str
    config_hash: str
    quiz_id: str
    run_number: int
    metrics: List[MetricResult]
    started_at: datetime
    completed_at: datetime
    metadata: Dict[str, Any] = None
```

#### 2. Metric Interface (`src/metrics/`)

```python
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional, Dict, Any

class MetricScope(Enum):
    QUESTION_LEVEL = "question"
    QUIZ_LEVEL = "quiz"

class BaseMetric(ABC):
    """Abstract base class for all quality metrics"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Metric identifier (e.g., 'alignment', 'clarity')"""
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
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this metric measures"""
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
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """Optional: Validate metric-specific parameters"""
        return True
```

#### 3. LLM Provider Abstraction (`src/evaluators/`)

```python
from abc import ABC, abstractmethod
from typing import Dict, Any

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
        """Return model identifier for result tracking"""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> str:
        """Return provider type (e.g., 'openai', 'anthropic')"""
        pass
```

#### 4. Benchmark Runner (`src/runners/`)

```python
from typing import List, Dict, Any

class BenchmarkRunner:
    """Orchestrates benchmark execution"""
    
    def __init__(self, config: BenchmarkConfig):
        self.config = config
        self.metrics: Dict[str, BaseMetric] = {}
        self.evaluators: Dict[str, LLMProvider] = {}
        
    def register_metric(self, metric: BaseMetric) -> None:
        """Register a metric for evaluation"""
        pass
        
    def register_evaluator(self, name: str, evaluator: LLMProvider) -> None:
        """Register an LLM evaluator"""
        pass
    
    def run(self, quizzes: List[Quiz]) -> List[BenchmarkResult]:
        """Execute benchmark for all quizzes across all runs"""
        pass
    
    def evaluate_quiz(self, 
                     quiz: Quiz, 
                     run_number: int) -> BenchmarkResult:
        """Evaluate single quiz with all configured metrics"""
        pass
```

### Project Structure

```
paper-al-quiz-generation-benchmark/
│
├── src/
│   ├── __init__.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── quiz.py              # Quiz and Question schemas
│   │   ├── result.py            # Result schemas
│   │   └── config.py            # Configuration models
│   │
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── base.py              # BaseMetric interface
│   │   ├── alignment.py         # Learning objective alignment
│   │   ├── cognitive_level.py   # Bloom's taxonomy evaluation
│   │   ├── clarity.py           # Language clarity assessment
│   │   ├── answer_correctness.py # Answer key validation
│   │   ├── distractor_quality.py # Distractor plausibility
│   │   ├── homogeneity.py       # Option parallelism check
│   │   ├── cueing_absence.py    # Inadvertent clue detection
│   │   ├── grammar.py           # Grammatical correctness
│   │   └── registry.py          # Metric registration/discovery
│   │
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── base.py              # LLMProvider interface
│   │   ├── azure_openai.py      # Azure OpenAI implementation
│   │   ├── openai.py            # OpenAI direct API
│   │   ├── anthropic.py         # Anthropic Claude
│   │   ├── ollama.py            # Ollama local runtime
│   │   ├── openai_compatible.py # Generic OpenAI-compatible
│   │   └── factory.py           # LLMProviderFactory
│   │
│   ├── runners/
│   │   ├── __init__.py
│   │   └── benchmark.py         # BenchmarkRunner orchestration
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── aggregator.py        # Statistical aggregation
│   │   ├── reporter.py          # Report generation
│   │   └── visualizer.py        # (Future) Result visualization
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py     # YAML config loading
│       ├── io.py                # File I/O utilities
│       └── validation.py        # Data validation helpers
│
├── data/
│   ├── inputs/                  # Source markdown files
│   │   └── example_lecture.md
│   │
│   ├── quizzes/                 # Generated quizzes (JSON)
│   │   └── example_quiz.json
│   │
│   └── results/                 # Benchmark results
│       └── <run-bundle>/
│           ├── results.json
│           ├── aggregated.json
│           ├── summary.txt
│           ├── metadata.json
│           └── run.log
│
├── config/
│   ├── benchmark_example.yaml
│   ├── comprehensive_eval.yaml
│   └── .env.example
│
├── tests/
│   ├── __init__.py
│   ├── test_models.py
│   ├── test_metrics.py
│   ├── test_evaluators.py
│   ├── test_integration.py
│   └── fixtures/
│       ├── sample_quizzes.json
│       └── sample_sources.md
│
├── docs/
│   ├── metrics/                 # Detailed metric documentation
│   │   ├── alignment.md
│   │   ├── cognitive_level.md
│   │   └── ...
│   │
│   ├── examples/                # Usage examples
│   │   └── custom_metric.md
│   │
│   └── api/                     # API documentation
│       └── reference.md
│
├── .env                         # Local environment (not in git)
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md                    # This file
└── main.py                      # CLI entry point
```

### Workflow Diagram

```
┌──────────────┐
│ Start        │
└──────┬───────┘
       │
       ▼
┌──────────────────────┐
│ Load Configuration   │
│ • YAML parsing       │
│ • Environment vars   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Initialize System    │
│ • Register metrics   │
│ • Create evaluators  │
│ • Validate config    │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Load Data            │
│ • Read quizzes       │
│ • Load sources       │
│ • Validate schemas   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ For each run (1..N)  │◄────────┐
└──────┬───────────────┘         │
       │                         │
       ▼                         │
┌──────────────────────┐         │
│ For each quiz        │◄────┐   │
└──────┬───────────────┘     │   │
       │                     │   │
       ▼                     │   │
┌──────────────────────┐     │   │
│ For each metric      │◄─┐  │   │
└──────┬───────────────┘  │  │   │
       │                  │  │   │
       ▼                  │  │   │
┌──────────────────────┐  │  │   │
│ For each evaluator   │  │  │   │
│                      │  │  │   │
│ • Generate prompt    │  │  │   │
│ • Call LLM           │  │  │   │
│ • Parse response     │  │  │   │
│ • Store result       │  │  │   │
└──────┬───────────────┘  │  │   │
       │                  │  │   │
       └──────────────────┘  │   │
       │                     │   │
       └─────────────────────┘   │
       │                         │
       └─────────────────────────┘
       │
       ▼
┌──────────────────────┐
│ Aggregate Results    │
│ • Group by metric    │
│ • Calculate stats    │
│ • Generate reports   │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ Save Outputs         │
│ • Raw JSON           │
│ • Aggregated JSON    │
│ • Text summary       │
└──────┬───────────────┘
       │
       ▼
┌──────────────┐
│ End          │
└──────────────┘
```

### Key Design Decisions

1. **Stateless Design**: No persistent state between runs; all context provided in configuration
2. **Strategy Pattern**: Easy swapping of LLM providers per metric without code changes
3. **Type Safety**: Full type hints with Python dataclasses for compile-time error detection
4. **Deterministic Evaluation**: Fixed temperature=0.0, versioned configs, timestamped results
5. **Extensibility**: Clear interfaces for metrics and evaluators; plugin architecture
6. **Reproducibility**: Config hashing, version tracking, complete result metadata
7. **Separation of Concerns**: Distinct layers for data, metrics, evaluation, and analysis
8. **Research-Based**: Metrics grounded in educational assessment literature

---
