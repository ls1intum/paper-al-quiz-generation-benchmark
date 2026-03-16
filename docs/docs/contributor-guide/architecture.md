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

#### 5. Quiz Instructions and Intent-Aware Scoring (`src/models/instruction.py`)

The benchmark system supports optional **quiz instructions**—user-supplied intent that informs how quizzes are evaluated. This enables **intent-aware scoring** where metrics understand not just what a quiz *is*, but what it was *supposed to be*.

**Instructions Schema**

```python
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class QuizInstructions(BaseModel):
    """User-supplied intent for what the quiz should be."""
    
    language: Optional[str] = None
    # Language the quiz should be written in (e.g., "English", "Spanish")
    # Couple: grammatical_correctness metric only
    
    num_questions: Optional[int] = None
    # Ideal number of questions; drives breadth penalty in coverage metric
    # Couple: coverage metric only
    
    question_types: List[str] = Field(default_factory=list)
    # Only these question types permitted (e.g., ["multiple_choice", "true_false"])
    # Validated against QuestionType enum at load time
    # Couple: clarity metric only
    
    difficulty: Optional[Literal["easy", "medium", "hard"]] = None
    # Difficulty band questions should fall into
    # Couple: difficulty metric only
    
    custom_prompt: Optional[str] = None
    # Free-form topic/content directive (e.g., "focus on recursion only")
    # Couple: all metrics decide relevance individually
```

**Two-Stage Adjustment Mechanism**

Instructions are processed in two stages during metric evaluation:

1. **Interpretation** (before any metric phase runs):
   - `interpret_custom_prompt()` normalizes free-text `custom_prompt` into a clear directive
   - Result stored in `accumulated["custom_prompt_context"]` for all phases to access
   - One LLM call per quiz, reused across all metrics

2. **Compliance Adjustment** (after all metric phases complete):
   - `adjust_score_for_custom_prompt()` runs once per metric
   - Assesses whether instructions are relevant to *this specific metric*
   - Computes compliance adjustment (positive, negative, or zero)
   - Adjustment applied in Python and clamped to [0, 100]

**Field-to-Metric Coupling**

Each structured instruction field is coupled to specific metrics to prevent logical conflicts:

| Instruction Field | Target Metrics | Reasoning |
|---|---|---|
| `language` | `grammatical_correctness` only | Language mismatch is a compliance issue, not a quality issue; grammar is scored on actual language |
| `difficulty` | `difficulty` only | Difficulty band compliance is separate from other quality metrics |
| `question_types` | `clarity` only | Question type mismatch affects clarity (type expectations), not other metrics |
| `custom_prompt` | All metrics | Content/topic directives are open-ended; each metric decides whether relevant |

**Loading Instructions**

Instructions are loaded from JSON files and linked via the `Quiz.instructions` field:

```python
# src/utils/io.py
@staticmethod
def load_instructions(quiz: Quiz, instructions_dir: str) -> Optional[QuizInstructions]:
    """Load instructions for a quiz.
    
    Returns None (with warning) if:
    - No instructions linked (quiz.instructions is None)
    - Instructions file not found
    - JSON parsing fails
    
    Never crashes the benchmark — allows graceful degradation.
    """
```

**Example Instructions File**

```json
{
  "language": "English",
  "num_questions": 10,
  "question_types": ["multiple_choice", "true_false"],
  "difficulty": "medium",
  "custom_prompt": "Focus exclusively on recursion, lists, and I/O operations. Do not include questions on object-oriented programming."
}
```

**Validation**

All instruction values are validated at deserialization:
- `question_types` are validated against `QuestionType` enum; invalid types raise `ValueError` with helpful guidance
- `difficulty` is limited to `"easy" | "medium" | "hard"` by Pydantic
- Invalid instructions fail early during loading, not during evaluation

**Difficulty Compliance Bands**

The difficulty metric applies scoring bands to assess compliance:

| Band | Score Range | Penalty Cap |
|---|---|---|
| Easy | 0–40 | 30 pts |
| Medium | 35–65 | 30 pts |
| Hard | 60–100 | 30 pts |

When a difficulty score falls outside the target band, a penalty is applied proportional to the distance:
- Distance = absolute gap from nearest band edge
- Penalty = min(distance × 0.5, 30 pts)
- Adjustment = raw_score − penalty

Example: If difficulty is requested as "hard" (60–100) but the quiz scores 45, the distance is 15 pts → penalty = 7.5 pts → adjusted score = 37.5.

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
