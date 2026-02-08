# Quiz Generation Benchmark Framework

A lightweight, reproducible benchmark for evaluating AI‑generated quizzes with LLM‑based metrics.

## Documentation

Full user and contributor documentation lives on the project site:

```
https://ls1intum.github.io/paper-al-quiz-generation-benchmark/
```

## Quick Start

### Requirements

- Python 3.13+
- At least one LLM provider API key

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd paper-al-quiz-generation-benchmark

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config/.env.example .env
# Edit .env with your API keys
```

### Run a Benchmark

```bash
python main.py --config config/benchmark_example.yaml
```

## Notes

- Tests and CI target Python 3.13.
- For detailed usage, metrics, and architecture, see the documentation site above.
