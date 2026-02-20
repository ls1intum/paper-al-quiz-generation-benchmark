---
title: Quick Start
sidebar_position: 2
---

## Quick Start

Get your quiz benchmark running in 5 minutes!

### Installation

#### Prerequisites

- Python 3.13 or higher
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

# Or LM Studio / OpenAI-compatible local endpoint
CUSTOM_LLM_ENDPOINT=http://localhost:1234/v1
CUSTOM_LLM_API_KEY=not-required
```

**Security Note:** Never commit `.env` to version control. It's already listed in `.gitignore`.

#### Step 2: Set Up LM Studio with JIT (Optional, for local models)

If you want to run local evaluators with `provider: "openai_compatible"`, configure LM Studio:

1. Start the LM Studio local server.
2. Enable JIT model loading in LM Studio settings.
3. Keep Auto-Evict enabled so LM Studio can unload one JIT model when another is requested.
4. Confirm the OpenAI-compatible base URL is `http://localhost:1234/v1`.

Quick check:

```bash
curl http://localhost:1234/v1/models
```

If this returns a model list, your benchmark can call LM Studio using `base_url: "http://localhost:1234/v1"`.

#### Step 3: Configure Benchmark Settings

The repository includes an example configuration. To run a hybrid setup (Azure + LM Studio), use:

```yaml
benchmark:
  name: "hybrid-benchmark"
  version: "1.0.0"
  runs: 1

evaluators:
  azure_gpt4:
    provider: "azure_openai"
    model: "gpt-4"  # Azure deployment name
    temperature: 0.0
    max_tokens: 500

  lmstudio_fast:
    provider: "openai_compatible"
    model: "qwen2.5-7b-instruct"
    base_url: "http://localhost:1234/v1"
    temperature: 0.0
    max_tokens: 300

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["lmstudio_fast"]
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"

  - name: "clarity"
    version: "1.0"
    evaluators: ["lmstudio_fast", "azure_gpt4"]

  - name: "coverage"
    version: "1.1"
    evaluators: ["azure_gpt4"]
    parameters:
      granularity: "balanced"

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

To switch local models per metric, define multiple `openai_compatible` evaluators (different `model` values) and assign them in each metric's `evaluators` list.

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
