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
│   │   ├── quiz.py               # Quiz and Question schemas
│   │   ├── result.py             # Result schemas
│   │   └── config.py             # Configuration models
│   │
│   ├── metrics/
│   │   ├── __init__.py
│   │   ├── base.py               # BaseMetric interface
│   │   ├── accuracy.py           # Factual accuracy assessment
│   │   ├── alignment.py          # Learning objective alignment
│   │   ├── cognitive_level.py    # Bloom's taxonomy evaluation
│   │   ├── clarity.py            # Language clarity assessment
│   │   ├── answer_correctness.py # Answer key validation
│   │   ├── distractor_quality.py # Distractor plausibility
│   │   ├── homogeneity.py        # Option parallelism check
│   │   ├── cueing_absence.py     # Inadvertent clue detection
│   │   ├── grammar.py            # Grammatical correctness
│   │   └── registry.py           # Metric registration/discovery
│   │
│   ├── evaluators/
│   │   ├── __init__.py
│   │   ├── base.py               # LLMProvider interface
│   │   ├── azure_openai.py       # Azure OpenAI implementation
│   │   ├── openai.py             # OpenAI direct API
│   │   ├── anthropic.py          # Anthropic Claude
│   │   ├── ollama.py             # Ollama local runtime
│   │   ├── openai_compatible.py  # Generic OpenAI-compatible
│   │   └── factory.py            # LLMProviderFactory
│   │
│   ├── runners/
│   │   ├── __init__.py
│   │   └── benchmark.py          # BenchmarkRunner orchestration
│   │
│   ├── analysis/
│   │   ├── __init__.py
│   │   ├── aggregator.py         # Statistical aggregation
│   │   ├── reporter.py           # Report generation
│   │   └── visualizer.py         # (Future) Result visualization
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config_loader.py      # YAML config loading
│       ├── io.py                 # File I/O utilities
│       └── validation.py         # Data validation helpers
│
├── data/
│   ├── inputs/                   # Source markdown files
│   │   └── example_lecture.md
│   │
│   ├── quizzes/                  # Generated quizzes (JSON)
│   │   └── example_quiz.json
│   │
│   └── results/                  # Benchmark results
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
│   ├── metrics/                  # Detailed metric documentation
│   │   ├── alignment.md
│   │   ├── cognitive_level.md
│   │   └── ...
│   │
│   ├── examples/                 # Usage examples
│   │   └── custom_metric.md
│   │
│   └── api/                      # API documentation
│       └── reference.md
│
├── .env                          # Local environment (not in git)
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── README.md                     # This file
└── main.py                       # CLI entry point
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

## Analysis & Aggregation Layer

### Results Aggregator (`src/analysis/aggregator.py`)

The **ResultsAggregator** class transforms raw evaluation results into statistically rigorous aggregations.

#### Responsibilities

1. **Grouping Results**: Organize scores by (metric_name, evaluator_model, quiz_id, question_id)
2. **Descriptive Statistics**: Compute mean, median, std dev, min, max across runs
3. **Bootstrap Confidence Intervals**: Estimate 95% CI for robust uncertainty quantification
4. **Inter-Rater Reliability**: Measure agreement between evaluators using:
   - **ICC(2,1)**: Intraclass correlation coefficient (two-way mixed, absolute agreement, single measurement)
   - **MAD**: Mean Absolute Deviation (interpretable on original score scale)
   - **Spearman ρ**: Rank-based correlation (insensitive to systematic bias)
5. **Per-Quiz Breakdowns**: Optional separate aggregation for each quiz

#### Bootstrap Confidence Interval Calculation

```python
def bootstrap_confidence_interval(
    data: List[float], 
    ci: float = 0.95, 
    n_bootstrap: int = 10000
) -> Tuple[float, float]:
    """
    Algorithm:
    1. Resample from data with replacement n_bootstrap times (e.g., 10,000)
    2. Calculate mean for each bootstrap sample
    3. Extract percentiles: lower = α/2, upper = 1 - α/2
    4. Return [lower_percentile, upper_percentile]
    
    Example:
    data = [75, 78, 76, 79, 77]
    - Bootstrap sample 1: mean([77, 78, 75, 76, 76]) = 76.4
    - Bootstrap sample 2: mean([78, 79, 77, 78, 79]) = 78.2
    - ... 9,998 more ...
    - 2.5th percentile of all means = 76.1
    - 97.5th percentile of all means = 79.2
    - Result: CI = [76.1, 79.2]
    """
    rng = np.random.default_rng(seed=42)  # Reproducible
    bootstrap_samples = rng.choice(data, size=(n_bootstrap, len(data)), replace=True)
    bootstrap_means = np.mean(bootstrap_samples, axis=1)
    
    alpha = 1 - ci
    lower = np.percentile(bootstrap_means, (alpha/2) * 100)
    upper = np.percentile(bootstrap_means, (1 - alpha/2) * 100)
    
    return (lower, upper)
```

**Why Bootstrap?**
- No parametric assumptions (works for any distribution)
- Robust to outliers and skewed data
- Reproducible (seeded RNG)
- Intuitive: measures actual variability in resampled means

#### Inter-Rater Reliability Calculation

When multiple evaluators assess the same questions, the framework computes three robust reliability metrics:

```python
# ICC(2,1) - two-way mixed effects, absolute agreement
from pingouin import intraclass_corr
icc_result = intraclass_corr(
    data=rating_data,
    targets='item',
    raters='rater',
    ratings='score',
    icc_type='ICC2'
)
# Returns: icc value and 95% confidence interval
# Scale: 0-1, higher indicates better agreement

# MAD - Mean Absolute Deviation (pairwise)
mad_value = np.mean([np.abs(rater_i - rater_j) for each pair])
# Scale: 0-100 (same as original scores), interpretable as average disagreement

# Spearman rho - Rank correlation
from scipy.stats import spearmanr
rhos = [spearmanr(rater_i, rater_j)[0] for each pair]
rho_avg = np.mean(rhos)
# Scale: -1 to 1, answers: do raters rank items the same way?
# Insensitive to systematic bias (one rater consistently higher)
```

**Advantages of this three-metric approach:**
- **ICC**: Measures absolute agreement (two-way, mixed-effects)
- **MAD**: Interpretable on original scale (0-100); directly shows average disagreement in points
- **Spearman rho**: Insensitive to systematic bias; focuses on rank agreement across items

#### Output Format

```python
@dataclass
class MetricAggregation:
    metric_name: str
    evaluator_model: str
    mean: float
    median: float
    std_dev: float
    min: float
    max: float
    per_run_scores: List[float]
    ci_lower: float  # 95% CI lower bound
    ci_upper: float  # 95% CI upper bound
    num_runs: int

@dataclass
class AggregatedResults:
    benchmark_config_name: str
    benchmark_version: str
    quiz_ids: List[str]
    total_runs: int
    aggregations: Dict[str, MetricAggregation]
    inter_rater_reliability: Dict[str, Dict[str, float]]
```

### Results Reporter (`src/analysis/reporter.py`)

Generates human-readable reports from aggregated results.

#### Features

- **Summary Generation**: Overview of all metrics with statistics
- **Comparison Reports**: Per-metric comparison across evaluators
- **Inter-Rater Analysis**: Display reliability metrics with interpretation
- **JSON Export**: Machine-readable aggregated results
- **Markdown Tables**: Easy integration into documentation/papers

#### Example Output

```
================================================================================
BENCHMARK RESULTS SUMMARY
================================================================================
Configuration: comprehensive_eval
Version: 1.0.0
Total Runs: 5
Quizzes Evaluated: 3

INTER-RATER RELIABILITY
--------------------------------------------------------------------------------

clarity:
  ICC(2,1): 0.8510 [95% CI: 0.7230, 0.9310]
  MAD (Mean Absolute Deviation): 3.45 points
  Spearman rho: 0.8760
  Number of Raters: 2

CLARITY
--------------------------------------------------------------------------------

  Evaluator: gpt-4
    Mean:   77.80
    Median: 78.50
    Std Dev: 2.34
    95% CI: [76.20, 79.40]
    Min:    74.10
    Max:    82.30
    N:      5

  Evaluator: claude-3-opus
    Mean:   79.20
    Median: 79.80
    Std Dev: 1.89
    95% CI: [77.80, 80.60]
    Min:    76.90
    Max:    81.50
    N:      5
```

### Data Flow

```
BenchmarkRunner Output (Multiple Runs)
    │
    ├─ Run 1 → BenchmarkResult
    │    ├─ Quiz 1, Q1, Clarity, GPT-4: 75.5
    │    ├─ Quiz 1, Q1, Clarity, Claude: 77.2
    │    └─ ...
    │
    ├─ Run 2 → BenchmarkResult
    │    ├─ Quiz 1, Q1, Clarity, GPT-4: 78.2
    │    ├─ Quiz 1, Q1, Clarity, Claude: 76.9
    │    └─ ...
    │
    └─ Run 3 → BenchmarkResult
         └─ ...
         │
         ▼
    ResultsAggregator.aggregate()
         │
         ├─ Group by (clarity, gpt-4):
         │    Scores = [75.5, 78.2, 76.8]
         │    → Mean = 76.8, CI = [75.1, 78.5]
         │
         ├─ Group by (clarity, claude):
         │    Scores = [77.2, 76.9, 77.8]
         │    → Mean = 77.3, CI = [76.2, 78.4]
         │
         └─ Inter-Rater Reliability:
              Scores_GPT = [75.5, 78.2, 76.8, ...]
              Scores_Claude = [77.2, 76.9, 77.8, ...]
              → ICC = 0.85, MAD = 3.45, Spearman = 0.87
              │
              ▼
         AggregatedResults (JSON)
              │
              ▼
         ResultsReporter.generate_summary()
              │
              ▼
         summary.txt + aggregated.json
```

---

### Key Design Decisions

1. **Stateless Design**: No persistent state between runs; all context provided in configuration
2. **Strategy Pattern**: Easy swapping of LLM providers per metric without code changes
3. **Type Safety**: Full type hints with Python dataclasses for compile-time error detection
4. **Deterministic Evaluation**: Fixed temperature=0.0, versioned configs, timestamped results
5. **Extensibility**: Clear interfaces for metrics and evaluators; plugin architecture
6. **Reproducibility**: Config hashing, version tracking, complete result metadata
7. **Separation of Concerns**: Distinct layers for data, metrics, evaluation, and analysis
8. **Research-Based**: Metrics grounded in educational assessment literature
9. **Statistical Rigor**: Bootstrap CIs + inter-rater reliability for robust aggregation
10. **Multi-Run Support**: Automatic aggregation across N runs for variance reduction

---
