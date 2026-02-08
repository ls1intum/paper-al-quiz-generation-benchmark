---
title: Example Workflows
sidebar_position: 7
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

