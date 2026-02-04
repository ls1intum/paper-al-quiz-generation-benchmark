---
sidebar_position: 1
slug: /
title: AI Quiz Generation Benchmark Documentation
hide_table_of_contents: false
---

# AI Quiz Generation Benchmark

**A Framework for Evaluating AI-Generated Quizzes Using LLMs as Judges**

---

## Overview

This benchmark framework provides a rigorous, extensible approach to evaluating AI-generated multiple-choice questions using multiple LLM-based quality metrics. The system is **stateless**, **modular**, and designed for **extensibility** and **reproducibility**.

### What This Framework Does

Systematically evaluate the quality of AI-generated quizzes using research-backed metrics:

- **Alignment with Learning Objectives**: Ensure questions assess intended outcomes
- **Cognitive Level Appropriateness**: Evaluate Bloom's taxonomy levels
- **Clarity and Precision**: Assess linguistic quality and unambiguity
- **Answer Key Correctness**: Verify single correct answer and clear distractors
- **Distractor Quality**: Evaluate plausibility based on common misconceptions
- **Homogeneous Options**: Check parallel structure across answer choices
- **Absence of Cueing**: Detect inadvertent clues to correct answers
- **Grammatical Correctness**: Ensure proper language usage throughout

### Key Features

✅ **Multiple LLM Support** — Azure OpenAI, OpenAI API, Anthropic Claude, and OpenAI-compatible local models  
✅ **Research-Based Metrics** — Implements quality criteria from assessment literature  
✅ **Flexible Configuration** — YAML-based configs for easy experimentation  
✅ **Statistical Rigor** — Multiple runs with aggregation (mean, median, standard deviation)  
✅ **Reproducible Results** — Versioned configs, deterministic evaluation (temperature=0.0)  
✅ **Clean Architecture** — Type-safe Python with clear interfaces  
✅ **Production-Oriented** — Complete with examples, tests, and comprehensive documentation

### Terminology

| Term | Definition |
|------|------------|
| **Metric** | A measurement of quiz quality (e.g., alignment, clarity, distractor quality) |
| **Evaluator** | An LLM provider that executes metric assessments |
| **Benchmark Run** | A complete evaluation cycle with specific configuration |
| **Quiz** | A collection of questions generated from source material |
| **Question** | Individual quiz item (multiple-choice, single-choice, true/false) |
| **Distractor** | An incorrect answer option designed to identify misconceptions |

---

## System Goals

1. **Evaluate quiz quality** using configurable, research-based metrics
2. **Support multiple LLM providers** (Azure OpenAI, OpenAI, Anthropic, open-source)
3. **Enable flexible configuration** for different benchmark runs and research questions
4. **Provide reproducible results** with versioning, statistical aggregation, and deterministic evaluation
5. **Maintain clean architecture** with clear interfaces, type safety, and extensibility

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
  - name: "alignment"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      learning_objectives: "auto_extract"
      
  - name: "cognitive_level"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      taxonomy: "bloom"
      target_level: "apply"
      
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
  - name: "alignment"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      learning_objectives: "auto_extract"
      
  - name: "distractor_quality"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      misconception_based: true

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
  # Test alignment with multiple evaluators
  - name: "alignment"
    version: "1.0"
    evaluators: ["gpt4", "gpt35", "claude_opus"]
    parameters:
      learning_objectives: "auto_extract"
    enabled: true
    
  # Test cognitive level with best model
  - name: "cognitive_level"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      taxonomy: "bloom"
      target_level: "apply"
    enabled: true
    
  # Test clarity across models
  - name: "clarity"
    version: "1.0"
    evaluators: ["gpt4", "claude_opus"]
    enabled: true
    
  # Test distractor quality
  - name: "distractor_quality"
    version: "1.0"
    evaluators: ["gpt4"]
    parameters:
      misconception_based: true
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
  "learning_objectives": [
    "Students will be able to...",
    "Students will understand..."
  ],
  "questions": [
    {
      "question_id": "unique_question_id",
      "question_type": "single_choice | multiple_choice | true_false",
      "question_text": "The question text",
      "options": ["Option 1", "Option 2", "..."],
      "correct_answer": "For SC/TF" || ["For", "MC"],
      "source_reference": "Optional reference to source",
      "bloom_level": "Optional: remember|understand|apply|analyze|evaluate|create",
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
   - Validates data schemas

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
   - Saves human-readable summary

#### Progress Monitoring

The framework prints progress information:

```
Registering metrics...
Available metrics: ['alignment', 'cognitive_level', 'clarity', 'distractor_quality']

Loading configuration from config/benchmark_example.yaml...
Configuration loaded: example-benchmark v1.0.0
  Runs: 3
  Evaluators: ['gpt4', 'gpt35']
  Metrics: ['alignment', 'clarity', 'distractor_quality']

Initializing benchmark runner...
  Initialized evaluator: gpt4 (gpt-4)
  Initialized evaluator: gpt35 (gpt-3.5-turbo)
  Initialized metric: alignment v1.0
  Initialized metric: clarity v1.0
  Initialized metric: distractor_quality v1.0

Starting benchmark execution...
Loading quizzes from data/quizzes...
  Loaded 1 quizzes

============================================================
Starting Run 1/3
============================================================
Evaluating quiz: Python Fundamentals Quiz (quiz_example_001)
  Running alignment with gpt4...
  Running alignment with gpt35...
  Running clarity with gpt4...
  Running clarity with gpt35...
  Running distractor_quality with gpt4...
...
```

### Understanding Results

#### Output Files

After execution, you'll find three files in `data/results/`:

1. **`results_<timestamp>.json`** — Raw results from all evaluations
2. **`aggregated_<timestamp>.json`** — Statistical aggregations
3. **`summary_<timestamp>.txt`** — Human-readable report

#### Reading the Summary

```
======================================================================
BENCHMARK RESULTS SUMMARY
======================================================================
Configuration: example-benchmark
Version: 1.0.0
Total Runs: 3
Quizzes Evaluated: 1

ALIGNMENT WITH LEARNING OBJECTIVES
----------------------------------------------------------------------
  Evaluator: gpt-4
    Mean:   82.50    # Average alignment score
    Median: 83.00    # Middle value (robust to outliers)
    Std Dev: 4.12    # Consistency (lower = more consistent)
    Min:    76.00    # Lowest score observed
    Max:    88.00    # Highest score observed
    N:      12       # Total number of evaluations
    
  Evaluator: gpt-3.5-turbo
    Mean:   79.25
    Median: 80.00
    Std Dev: 5.67
    Min:    71.00
    Max:    86.00
    N:      12

DISTRACTOR QUALITY
----------------------------------------------------------------------
  Evaluator: gpt-4
    Mean:   71.33
    Median: 72.00
    Std Dev: 6.89
    Min:    61.00
    Max:    81.00
    N:      12
```

#### Interpreting Results

**Mean vs Median**
- **Mean**: Average score, sensitive to outliers
- **Median**: Middle value, robust to outliers
- Large difference → check for outliers in raw data

**Standard Deviation**
- **Low (< 5)**: Consistent evaluations
- **Medium (5-10)**: Some variation (acceptable)
- **High (> 10)**: High variance, may need more runs or prompt refinement

**Comparing Evaluators**
- Similar scores → models agree on metric
- Different scores → models have different perspectives or capabilities
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
      "metric_name": "alignment",
      "metric_version": "1.0",
      "score": 82.0,
      "evaluator_model": "gpt-4",
      "quiz_id": "quiz_example_001",
      "question_id": "q1",
      "parameters": {
        "learning_objectives": "auto_extract"
      },
      "evaluated_at": "2024-01-15T10:30:00",
      "raw_response": "LLM's actual response..."
    }
  ],
  "started_at": "2024-01-15T10:29:00",
  "completed_at": "2024-01-15T10:35:00"
}
```

---

## Supported Quality Metrics

### 1. Alignment with Learning Objectives

**Purpose**: Verify questions accurately assess intended learning outcomes and match instructional goals.

**References**: Haladyna et al. [10], Sireci [17]

**Scope**: Question-level

**Parameters**:
- `learning_objectives`: Source of objectives ("auto_extract", "provided", or list)
- `alignment_threshold`: Minimum acceptable alignment score (default: 70)

**Evaluation Criteria**:
- Direct assessment of stated objectives
- Coverage of key concepts
- Appropriate depth and breadth

**Example Configuration**:
```yaml
- name: "alignment"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    learning_objectives: "auto_extract"
    alignment_threshold: 75
```

---

### 2. Cognitive Level Appropriateness

**Purpose**: Ensure questions target appropriate levels of Bloom's taxonomy.

**Bloom's Taxonomy Levels**:
1. **Remember**: Recall facts and basic concepts
2. **Understand**: Explain ideas or concepts
3. **Apply**: Use information in new situations
4. **Analyze**: Draw connections among ideas
5. **Evaluate**: Justify a decision or course of action
6. **Create**: Produce new or original work

**References**: Anderson & Krathwohl [2], Haladyna & Rodriguez [11]

**Scope**: Question-level

**Parameters**:
- `taxonomy`: "bloom" or "webb"
- `target_level`: Expected cognitive level
- `tolerance`: Allow ±1 level deviation

**Example Configuration**:
```yaml
- name: "cognitive_level"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    taxonomy: "bloom"
    target_level: "apply"
    tolerance: 1
```

---

### 3. Clarity and Precision

**Purpose**: Assess whether question stems and answer options use clear, unambiguous language without unnecessary complexity.

**References**: Downing [8], Haladyna et al. [10]

**Scope**: Question-level

**Evaluation Criteria**:
- Language complexity appropriate for audience
- Absence of ambiguous phrasing
- Clear, concise wording
- No unnecessary jargon
- Proper use of terminology

**Example Configuration**:
```yaml
- name: "clarity"
  version: "1.0"
  evaluators: ["gpt4", "claude_opus"]
  parameters:
    target_audience: "undergraduate"
    complexity_threshold: "moderate"
```

---

### 4. Answer Key Correctness

**Purpose**: Verify exactly one option is unambiguously correct (or clearly best) while all distractors are unambiguously incorrect.

**References**: Haladyna et al. [10], Haladyna & Rodriguez [11]

**Scope**: Question-level

**Evaluation Criteria**:
- One clearly correct answer
- All distractors are definitively incorrect
- No ambiguity in correctness
- Correct answer is verifiable from source material

**Example Configuration**:
```yaml
- name: "answer_correctness"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    verify_source: true
    require_unambiguous: true
```

---

### 5. Distractor Quality

**Purpose**: Evaluate whether incorrect options are plausible to students lacking mastery but clearly wrong to knowledgeable students; should be based on common misconceptions.

**References**: Gierl et al. [9], Haladyna & Rodriguez [11]

**Scope**: Question-level

**Evaluation Criteria**:
- Plausibility to novices
- Based on documented misconceptions
- Not obviously incorrect
- Discriminates between knowledge levels
- Avoids "all of the above" or "none of the above"

**Example Configuration**:
```yaml
- name: "distractor_quality"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    misconception_based: true
    plausibility_threshold: 60
    discrimination_required: true
```

---

### 6. Homogeneous Options

**Purpose**: Ensure all answer choices are parallel in grammatical structure and homogeneous in content type.

**References**: Downing [8], Haladyna et al. [10]

**Scope**: Question-level

**Evaluation Criteria**:
- Parallel grammatical structure
- Similar length and complexity
- Consistent content type
- Same level of specificity
- Uniform formatting

**Example Configuration**:
```yaml
- name: "homogeneity"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    check_grammar: true
    check_length: true
    check_specificity: true
```

---

### 7. Absence of Cueing

**Purpose**: Detect grammatical, semantic, or structural clues that inadvertently reveal the correct answer.

**References**: Downing [8], Haladyna et al. [10]

**Scope**: Question-level

**Common Cues to Detect**:
- Grammatical inconsistencies (e.g., "an" before consonant)
- Length differences (correct answer often longest)
- Specificity differences (correct answer more detailed)
- Absolute terms ("always", "never") in distractors
- Verbal associations between stem and correct answer
- Convergence cues (correct answer includes elements of all options)

**Example Configuration**:
```yaml
- name: "cueing_absence"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    check_grammar: true
    check_length: true
    check_specificity: true
    check_absolutes: true
    check_associations: true
```

---

### 8. Grammatical Correctness

**Purpose**: Ensure both stem and options are grammatically correct and properly punctuated.

**References**: Haladyna et al. [10], Haladyna & Rodriguez [11]

**Scope**: Question-level

**Evaluation Criteria**:
- Proper grammar in stem
- Proper grammar in all options
- Correct punctuation
- Subject-verb agreement
- Consistent tense usage

**Example Configuration**:
```yaml
- name: "grammar"
  version: "1.0"
  evaluators: ["gpt4"]
  parameters:
    strict_mode: true
    check_punctuation: true
```

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
│       ├── results_<timestamp>.json
│       ├── aggregated_<timestamp>.json
│       └── summary_<timestamp>.txt
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

## Best Practices

### 1. Configuration Management

✅ **DO**:
- Use descriptive names: `config/gpt4_vs_claude_alignment.yaml`
- Include version in benchmark config for tracking
- Add comments in YAML explaining parameter choices
- Keep separate configs for experiments vs. production

❌ **DON'T**:
- Overwrite configs without versioning
- Use generic names like `config1.yaml`
- Hard-code parameters in source code

### 2. Reproducibility

✅ **DO**:
- Set temperature to 0.0 for deterministic results
- Use at least 3-5 runs for reliable statistics
- Save all configurations in version control
- Specify exact model names (e.g., `gpt-4-0613`, not just `gpt-4`)
- Record timestamps and config hashes in results

❌ **DON'T**:
- Use temperature > 0 without documenting why
- Run benchmarks only once
- Delete old result files
- Use "latest" model versions without recording specifics

### 3. Cost Management

✅ **DO**:
- Start with 1-2 questions for testing
- Use cheaper models (gpt-3.5-turbo) for development
- Monitor API usage dashboards
- Cache results to avoid re-running
- Set `max_tokens` appropriately for each metric

❌ **DON'T**:
- Run full benchmarks during development
- Use GPT-4 for all testing
- Ignore rate limits
- Re-run unnecessarily

### 4. Data Quality

✅ **DO**:
- Validate JSON schemas before running
- Ensure source_material paths exist
- Review questions for well-formedness
- Test with small dataset first
- Include learning objectives when available

❌ **DON'T**:
- Skip validation steps
- Assume JSON is well-formed
- Run benchmarks on untested data

### 5. Metric Selection

✅ **DO**:
- Choose metrics relevant to your research question
- Start with core metrics (alignment, clarity, cognitive level)
- Create domain-specific metrics for specialized content
- Test metric prompts manually before automation
- Document metric rationale in config comments

❌ **DON'T**:
- Enable all metrics without purpose
- Use metrics inappropriate for question type
- Deploy untested custom metrics

### 6. Result Interpretation

✅ **DO**:
- Look at trends across multiple quizzes
- Check for consistency (low std dev = reliable)
- Cross-validate with multiple evaluators
- Review outliers and raw LLM responses
- Consider context (domain, audience, objectives)

❌ **DON'T**:
- Over-interpret single data points
- Ignore high variance warnings
- Trust one evaluator blindly
- Compare scores across different metrics

---

## Troubleshooting

### Common Issues

#### "Module not found" errors

```bash
# Ensure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

#### API Key errors

**Symptoms**: `AuthenticationError`, `Invalid API key`

**Solutions**:
1. Verify `.env` file is in project root
2. Check API keys are correct (no extra spaces)
3. Ensure provider in YAML matches `.env` configuration
4. Test API key manually with provider's playground

#### No quizzes found

**Symptoms**: `Loaded 0 quizzes`

**Solutions**:
1. Verify quiz JSON files are in correct directory
2. Check JSON format validity: `python -m json.tool data/quizzes/quiz.json`
3. Ensure `source_material` field references existing file
4. Review directory paths in config YAML

#### High variance in results

**Symptoms**: Std dev > 10

**Possible causes**:
- Ambiguous metric prompts
- Complex questions with multiple interpretations
- Insufficient runs

**Solutions**:
- Increase number of runs (5-10)
- Refine metric prompt for clarity
- Review raw LLM responses for patterns
- Try different evaluator models

#### Unexpected scores

**Symptoms**: Scores don't match manual assessment

**Diagnostic steps**:
1. Review raw LLM responses in `results_*.json`
2. Test metric prompt manually in LLM playground
3. Verify source material quality and completeness
4. Check if questions align with learning objectives
5. Compare across multiple evaluators

#### API rate limit errors

**Symptoms**: `RateLimitError`, `429 Too Many Requests`

**Solutions**:
- Add delays between API calls (implement in provider)
- Use batch processing with smaller batches
- Check your tier limits with provider
- Spread evaluation across longer time period

#### Memory issues

**Symptoms**: `MemoryError`, system slowdown

**Solutions**:
- Process quizzes in batches
- Reduce `max_tokens` in config
- Use lighter models (gpt-3.5-turbo vs gpt-4)
- Clear results between runs

---

## Example Workflows

### Workflow 1: Quick Single-Model Evaluation

**Use case**: Fast evaluation during development

```bash
# 1. Create minimal config
cat > config/quick_test.yaml << 'EOF'
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
  - name: "clarity"
    version: "1.0"
    evaluators: ["gpt35"]

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
EOF

# 2. Run benchmark
python main.py --config config/quick_test.yaml

# 3. View results
cat data/results/summary_*.txt | tail -20
```

---

### Workflow 2: Comprehensive Multi-Model Comparison

**Use case**: Research paper evaluation, model selection

```bash
# 1. Use comprehensive config
python main.py \
  --config config/comprehensive_eval.yaml \
  --output-prefix experiment_comparison_v1

# 2. Analyze evaluator agreement
python << 'EOF'
import json
import pandas as pd
from pathlib import Path

# Load results
results = json.load(open('data/results/aggregated_experiment_comparison_v1.json'))

# Extract evaluator comparisons
for metric_name, metric_data in results['aggregations'].items():
    print(f"\n{metric_name}:")
    for evaluator, stats in metric_data.items():
        print(f"  {evaluator}: {stats['mean']:.2f} ± {stats['std_dev']:.2f}")
EOF

# 3. Generate comparison report
python scripts/generate_comparison_report.py \
  --input data/results/aggregated_experiment_comparison_v1.json \
  --output reports/model_comparison.pdf
```

---

### Workflow 3: Iterative Metric Development

**Use case**: Developing and refining a new custom metric

```bash
# 1. Create test config with new metric
cat > config/test_new_metric.yaml << 'EOF'
benchmark:
  name: "metric-development"
  version: "0.1.0"
  runs: 3

evaluators:
  gpt4:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "my_new_metric"
    version: "0.1"
    evaluators: ["gpt4"]
    parameters:
      custom_param: "value"

inputs:
  quiz_directory: "data/quizzes/test_subset"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
EOF

# 2. Run initial test
python main.py --config config/test_new_metric.yaml --output-prefix dev_v1

# 3. Review results and identify issues
cat data/results/summary_dev_v1.txt

# 4. Refine metric implementation
# Edit src/metrics/my_new_metric.py

# 5. Re-run with new version
# Update version in config to "0.2"
python main.py --config config/test_new_metric.yaml --output-prefix dev_v2

# 6. Compare versions
python << 'EOF'
import json

v1 = json.load(open('data/results/aggregated_dev_v1.json'))
v2 = json.load(open('data/results/aggregated_dev_v2.json'))

print("Version comparison:")
print(f"v0.1 mean: {v1['aggregations']['my_new_metric']['gpt4']['mean']:.2f}")
print(f"v0.2 mean: {v2['aggregations']['my_new_metric']['gpt4']['mean']:.2f}")
print(f"v0.1 std:  {v1['aggregations']['my_new_metric']['gpt4']['std_dev']:.2f}")
print(f"v0.2 std:  {v2['aggregations']['my_new_metric']['gpt4']['std_dev']:.2f}")
EOF
```

---

### Workflow 4: Large-Scale Production Evaluation

**Use case**: Evaluating production quiz generation system

```bash
# 1. Prepare environment
export BENCHMARK_ENV=production
source .env.production

# 2. Run production benchmark with full metrics
python main.py \
  --config config/production_full_eval.yaml \
  --output-prefix prod_eval_$(date +%Y%m%d) \
  --env .env.production

# 3. Generate comprehensive reports
python scripts/generate_report.py \
  --results data/results/aggregated_prod_eval_*.json \
  --format pdf \
  --include-visualizations \
  --output reports/production_evaluation_$(date +%Y%m%d).pdf

# 4. Upload results to storage
aws s3 cp \
  data/results/ \
  s3://quiz-benchmark-results/$(date +%Y/%m/%d)/ \
  --recursive

# 5. Send notification
python scripts/send_notification.py \
  --channel slack \
  --message "Production benchmark completed" \
  --attach reports/production_evaluation_$(date +%Y%m%d).pdf
```

---

## Project Status

### 🚧 Currently In Development

This benchmark framework is an **active research project** with ongoing development and refinement.

#### ✅ Completed Components

**Core Infrastructure**
- ✅ Data models with full type safety
- ✅ LLM provider abstraction (Azure OpenAI, OpenAI, Anthropic, OpenAI-compatible)
- ✅ Benchmark orchestration and runner
- ✅ Configuration management (YAML + environment variables)
- ✅ Result aggregation and statistical analysis
- ✅ CLI interface

**Documentation**
- ✅ Comprehensive usage guide
- ✅ Architecture documentation
- ✅ Quick start tutorial
- ✅ API reference

**Quality Assurance**
- ✅ Unit test infrastructure
- ✅ Example configurations
- ✅ Sample data for testing

#### 🏗️ In Progress

**Metrics Implementation**
- 🏗️ Alignment with Learning Objectives
- 🏗️ Cognitive Level Appropriateness
- 🏗️ Clarity and Precision
- 🏗️ Answer Key Correctness
- 🏗️ Distractor Quality
- 🏗️ Homogeneous Options
- 🏗️ Absence of Cueing
- 🏗️ Grammatical Correctness

**Validation & Testing**
- 🏗️ Metric prompt optimization
- 🏗️ Inter-rater reliability studies
- 🏗️ Comparison with human expert ratings
- 🏗️ Statistical validation of metrics

#### 📋 Planned Enhancements

**Short Term**
- Batch processing optimization
- Caching layer for LLM responses
- Enhanced error handling and recovery
- Progress bar for long-running benchmarks

**Medium Term**
- Web UI for result visualization
- Database backend (optional)
- Export to CSV/Excel formats
- Statistical significance testing
- Comparison reports between benchmark versions

**Long Term**
- Integration with quiz generation pipelines
- Real-time evaluation API
- Additional metric library
- Multi-language support
- Automated metric calibration

### 📊 Current Capabilities

**What Works Now**:
- Running benchmarks with any LLM provider
- Custom metric development and integration
- Multi-run statistical aggregation
- Result export (JSON, TXT)
- Reproducible evaluation workflows

**What's Being Refined**:
- Metric prompt engineering for optimal accuracy
- Evaluation consistency across different LLM providers
- Correlation with human expert judgments
- Statistical methodologies for aggregation

### 🎯 Research Goals

This framework supports several ongoing research objectives:

1. **Automated Quality Assessment**: Developing reliable LLM-based metrics for quiz quality
2. **Evaluator Comparison**: Understanding strengths/weaknesses of different LLMs as judges
3. **Metric Validation**: Correlating automated metrics with expert human assessment
4. **Best Practices**: Identifying optimal prompting strategies for educational assessment

### 🤝 Contributing

This is a research project and we welcome contributions:

- **Metric Development**: Propose new quality metrics based on assessment literature
- **Prompt Engineering**: Improve metric prompts for better accuracy
- **Validation Studies**: Compare automated scores with human expert ratings
- **Use Cases**: Share your benchmark configurations and findings

### 📬 Feedback & Contact

We value feedback from researchers and practitioners:

- **Issues**: Report bugs or suggest features via GitLab issues
- **Discussions**: Share findings or ask questions in GitLab discussions
- **Collaboration**: Contact [your-email] for research collaboration

---

## References

### Educational Assessment Literature

[2] Anderson, L. W., & Krathwohl, D. R. (2001). *A taxonomy for learning, teaching, and assessing: A revision of Bloom's taxonomy of educational objectives*. Addison Wesley Longman, Inc.

[8] Downing, S. M. (2005). The effects of violating standard item writing principles on tests and students: The consequences of using flawed test items on achievement examinations in medical education. *Advances in Health Sciences Education*, 10(2), 133–143. https://doi.org/10.1007/s10459-004-4019-5

[9] Gierl, M. J., Bulut, O., Guo, Q., & Zhang, X. (2017). Developing, analyzing, and using distractors for multiple-choice tests in education: A comprehensive review. *Review of Educational Research*, 87(6), 1082–1116. https://doi.org/10.3102/0034654317726529

[10] Haladyna, T. M., Downing, S. M., & Rodriguez, M. C. (2002). A review of multiple-choice item-writing guidelines for classroom assessment. *Applied Measurement in Education*, 15(3), 309–333. https://doi.org/10.1207/S15324818AME1503_5

[11] Haladyna, T. M., & Rodriguez, M. C. (2013). *Developing and validating test items*. Routledge. https://doi.org/10.4324/9780203850381

[17] Sireci, S. G. (1998). The construct of content validity. *Social Indicators Research*, 45(1-3), 83–117.

---

## Citation

If you use this framework in your research, please cite:

```bibtex
@software{quiz_benchmark_2024,
  title = {AI Quiz Generation Benchmark: A Framework for Evaluating AI-Generated Educational Assessments},
  author = {[Your Name/Team]},
  year = {2024},
  version = {1.0.0-beta},
  url = {[Your Repository URL]},
  note = {Research software under active development}
}
```

---

## License

[Specify your license here]

---

## Acknowledgments

This framework builds on established principles from educational measurement and leverages modern LLM capabilities for automated assessment. We acknowledge the foundational work in educational assessment literature that informs our quality metrics.

---

**Status**: 🚧 **ACTIVE DEVELOPMENT** — Framework operational, metrics under validation

**Version**: 1.0.0-beta

**Last Updated**: February 2024
