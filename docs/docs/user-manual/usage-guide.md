---
title: Complete Usage Guide
sidebar_position: 3
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

# LM Studio models (optional, recommended with provider: "lm_studio")
LM_STUDIO_ENDPOINT=http://localhost:1234/v1
LM_STUDIO_API_KEY=not-required

# Generic OpenAI-compatible fallback
CUSTOM_LLM_ENDPOINT=http://localhost:1234/v1
CUSTOM_LLM_API_KEY=optional-key
```

### LM Studio JIT Setup (Local OpenAI-Compatible Endpoint)

To use LM Studio as a local evaluator backend:

1. Start LM Studio and launch the local server.
2. Enable JIT model loading.
3. Enable Auto-Evict so the server can switch models when different `model` IDs are requested.
4. Use `http://localhost:1234/v1` as your endpoint (or your configured port).

Recommended `.env` values:

```bash
LM_STUDIO_ENDPOINT=http://localhost:1234/v1
LM_STUDIO_API_KEY=not-required

# Optional fallback aliases
CUSTOM_LLM_ENDPOINT=http://localhost:1234/v1
CUSTOM_LLM_API_KEY=not-required
```

Sanity checks:

```bash
# OpenAI-compatible model list
curl http://localhost:1234/v1/models

# Optional LM Studio health check
curl http://localhost:1234/api/v1/models
```

Notes:
- Your benchmark does not manually load/unload models today; it relies on LM Studio JIT behavior.
- If multiple local evaluators use different `model` IDs, LM Studio handles switching between them.
- First request after a switch can be slower due to model load time.
- `lm_studio` resolves env vars in this order: `LM_STUDIO_ENDPOINT`/`LM_STUDIO_API_KEY`, then `CUSTOM_LLM_ENDPOINT`/`CUSTOM_LLM_API_KEY`.
- The runner performs fail-early validation for `lm_studio`: endpoint configured, server reachable, and configured model IDs present in `/v1/models`.

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

#### Hybrid Azure + LM Studio Configuration

Use larger hosted models for expensive metrics and local models for lower-cost checks:

```yaml
benchmark:
  name: "hybrid-azure-lmstudio"
  version: "1.0.0"
  runs: 3

evaluators:
  azure_gpt4:
    provider: "azure_openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 700

  lmstudio_fast:
    provider: "lm_studio"
    model: "qwen2.5-7b-instruct"
    base_url: "http://localhost:1234/v1"
    temperature: 0.0
    max_tokens: 300

  lmstudio_reasoning:
    provider: "lm_studio"
    model: "qwen2.5-14b-instruct"
    base_url: "http://localhost:1234/v1"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["lmstudio_fast"]
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"
    enabled: true

  - name: "grammatical_correctness"
    version: "1.0"
    evaluators: ["lmstudio_fast"]
    enabled: true

  - name: "clarity"
    version: "1.0"
    evaluators: ["lmstudio_reasoning", "azure_gpt4"]
    enabled: true

  - name: "coverage"
    version: "1.1"
    evaluators: ["azure_gpt4"]
    parameters:
      granularity: "balanced"
    enabled: true
```

Notes:
- `lm_studio` is the recommended provider for LM Studio endpoints.
- `openai_compatible` remains available for generic OpenAI-compatible backends (vLLM, local proxies, etc.).
- You can define multiple local evaluators with different `model` values and route metrics accordingly.
- If all local evaluators use the same LM Studio instance, keep `base_url` identical.

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
