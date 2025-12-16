# Quick Start Guide

Get your quiz benchmark running in 5 minutes!

## Step 1: Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

## Step 2: Configure API Keys

```bash
# Copy template
cp config/.env.example .env

# Edit with your keys (at minimum, one provider)
nano .env
```

Example `.env`:
```bash
OPENAI_API_KEY=sk-your-key-here
```

## Step 3: Run the Example

The repository includes an example quiz and source material. Just run:

```bash
python main.py --config config/benchmark_example.yaml
```

**Note:** Edit `config/benchmark_example.yaml` to match your available API keys. For example, if you only have OpenAI configured, update the config to use only OpenAI evaluators:

```yaml
evaluators:
  gpt4:
    provider: "openai"  # Changed from azure_openai
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["gpt4"]  # Only use what you configured
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"
```

## Step 4: View Results

Results are saved to `data/results/`:

```bash
# View the summary
cat data/results/summary_*.txt

# View raw JSON
cat data/results/results_*.json
```

## What's Happening?

1. **Loading**: Reads `data/quizzes/example_quiz.json` and `data/inputs/python_intro.md`
2. **Evaluating**: Each configured metric runs with each configured evaluator
3. **Repeating**: The benchmark runs multiple times (configured via `runs` in YAML)
4. **Aggregating**: Statistics (mean, median, std dev) are calculated across runs
5. **Reporting**: Results are saved as JSON and human-readable text

## Next Steps

### Create Your Own Quiz

1. Create a markdown file in `data/inputs/my_topic.md` with your source material
2. Create a quiz JSON in `data/quizzes/my_quiz.json`:

```json
{
  "quiz_id": "my_quiz_001",
  "title": "My Custom Quiz",
  "source_material": "my_topic.md",
  "questions": [
    {
      "question_id": "q1",
      "question_type": "single_choice",
      "question_text": "Your question here?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "source_reference": "Section 1",
      "metadata": {}
    }
  ],
  "metadata": {},
  "created_at": "2024-01-15T10:00:00"
}
```

3. Run the benchmark again:

```bash
python main.py --config config/benchmark_example.yaml
```

### Customize Configuration

Create a new config file `config/my_benchmark.yaml`:

```yaml
benchmark:
  name: "my-custom-benchmark"
  version: "1.0.0"
  runs: 5  # Adjust number of runs

evaluators:
  my_evaluator:
    provider: "openai"
    model: "gpt-4"
    temperature: 0.0
    max_tokens: 500

metrics:
  - name: "difficulty"
    version: "1.0"
    evaluators: ["my_evaluator"]
    parameters:
      rubric: "bloom_taxonomy"
      target_audience: "undergraduate"
    enabled: true

  - name: "clarity"
    version: "1.0"
    evaluators: ["my_evaluator"]
    enabled: true

inputs:
  quiz_directory: "data/quizzes"
  source_directory: "data/inputs"

outputs:
  results_directory: "data/results"
```

Run with:
```bash
python main.py --config config/my_benchmark.yaml
```

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

## Understanding Output

### Summary File
Shows aggregated statistics:
```
DIFFICULTY
----------------------------------------------------------------------
  Evaluator: gpt-4
    Mean:   65.50  ← Average score across all evaluations
    Median: 67.00  ← Middle value
    Std Dev: 8.23  ← Variation between runs
    Min:    55.00  ← Lowest score
    Max:    74.00  ← Highest score
    N:      12     ← Number of evaluations
```

### Results File
Raw JSON with every individual evaluation, useful for detailed analysis.

### Aggregated File
JSON with statistics, useful for programmatic comparison between benchmarks.

## Need Help?

- See [README.md](README.md) for full documentation
- See [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Check example files in `data/` directory
- Review configuration in `config/benchmark_example.yaml`
