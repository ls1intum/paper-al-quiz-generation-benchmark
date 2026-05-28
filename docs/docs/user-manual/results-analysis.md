---
title: Results Analysis & Aggregation
sidebar_position: 4.5
---

# Results Analysis & Aggregation

After running a benchmark, the framework automatically aggregates results across multiple runs using rigorous statistical methods. This guide explains how aggregation works, what statistics are computed, and how to interpret the results.

---

## Overview

### Why Aggregation Matters

Running a benchmark multiple times (configured via `runs` in your YAML) provides several benefits:

- **Variance Reduction**: Single LLM responses can be noisy. Multiple runs average out random variation.
- **Confidence Intervals**: With multiple data points, we can estimate the true underlying score with confidence bands.
- **Inter-Rater Reliability**: When using multiple evaluators (different LLM models), we can measure agreement/disagreement.
- **Statistical Rigor**: Mean, median, and standard deviation reveal the distribution of scores, not just point estimates.

### Aggregation Pipeline

```
Raw Results (Multiple Runs)
         │
         ├─ Run 1: Question A → Clarity Score: 75
         ├─ Run 2: Question A → Clarity Score: 78
         ├─ Run 3: Question A → Clarity Score: 76
         └─ ...
         │
         ▼
ResultsAggregator
         │
         ├─ Bootstrap Confidence Intervals
         ├─ Descriptive Statistics
         ├─ Inter-Rater Reliability (if multiple evaluators)
         └─ Per-Quiz Breakdowns
         │
         ▼
Aggregated Results (JSON + TXT Reports)
```

---

## Output Files

Each benchmark run produces the following files in `data/results/<run-bundle>/`:

### 1. `results.json` — Raw Results (All Runs)

Contains **every individual score** from every run, useful for detailed analysis:

```json
[
  {
    "benchmark_id": "benchmark-20250512-123456",
    "quiz_id": "python_quiz_1",
    "question_id": "q_001",
    "run_number": 1,
    "metrics": [
      {
        "metric_name": "clarity",
        "metric_version": "1.0",
        "score": 78.5,
        "evaluator_model": "gpt-4",
        "evaluated_at": "2025-05-12T12:34:56Z",
        "raw_response": "{...full LLM response...}"
      }
    ]
  },
  {
    "benchmark_id": "benchmark-20250512-123456",
    "quiz_id": "python_quiz_1",
    "question_id": "q_001",
    "run_number": 2,
    "metrics": [
      {
        "metric_name": "clarity",
        "metric_version": "1.0",
        "score": 81.2,
        "evaluator_model": "gpt-4",
        "evaluated_at": "2025-05-12T12:45:22Z",
        "raw_response": "{...full LLM response...}"
      }
    ]
  }
]
```

### 2. `aggregated.json` — Aggregated Statistics

Contains **summarized statistics** across all runs:

```json
{
  "benchmark_config_name": "comprehensive_eval",
  "benchmark_version": "1.0.0",
  "quiz_ids": ["python_quiz_1", "python_quiz_2", "advanced_python"],
  "total_runs": 5,
  "aggregations": {
    "clarity_gpt-4": {
      "metric_name": "clarity",
      "evaluator_model": "gpt-4",
      "mean": 77.8,
      "median": 78.5,
      "std_dev": 2.34,
      "min": 74.1,
      "max": 82.3,
      "ci_lower": 76.2,
      "ci_upper": 79.4,
      "per_run_scores": [75.5, 78.2, 77.1, 79.3, 78.8],
      "num_runs": 5
    },
    "clarity_claude-3": {
      "metric_name": "clarity",
      "evaluator_model": "claude-3-opus-20240229",
      "mean": 79.2,
      "median": 79.8,
      "std_dev": 1.89,
      "min": 76.9,
      "max": 81.5,
      "ci_lower": 77.8,
      "ci_upper": 80.6,
      "per_run_scores": [79.1, 80.5, 78.3, 79.4, 79.8],
      "num_runs": 5
    }
  },
  "inter_rater_reliability": {
    "clarity": {
      "icc": 0.851,
      "icc_ci_lower": 0.723,
      "icc_ci_upper": 0.931,
      "mad": 3.45,
      "spearman_rho": 0.876,
      "num_raters": 2
    }
  }
}
```

### 3. `summary.txt` — Human-Readable Report

Text summary ideal for quick review:

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

distractor_quality:
  ICC(2,1): 0.7940 [95% CI: 0.5820, 0.9060]
  MAD (Mean Absolute Deviation): 5.12 points
  Spearman rho: 0.7290
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

  Evaluator: claude-3-opus-20240229
    Mean:   79.20
    Median: 79.80
    Std Dev: 1.89
    95% CI: [77.80, 80.60]
    Min:    76.90
    Max:    81.50
    N:      5

DISTRACTOR_QUALITY
...
```

---

## Statistical Measures Explained

### Descriptive Statistics

|  Statistic  |          Definition           |                          Interpretation                              |
|-------------|-------------------------------|----------------------------------------------------------------------|
|  **Mean**   | Average score across all runs |           The "typical" score. Use for comparing evaluators.         |
| **Median**  |    Middle value when sorted   |       Robust to outliers. If median ≠ mean, check for outliers.      |
| **Std Dev** |      Standard deviation       | Spread of scores. Lower = more consistent. High (&gt;5) = high variance.|
| **Min/Max** |  Minimum and maximum scores   |         Range of observed values. Watch for extreme outliers.        |

### 95% Confidence Interval (CI)

**What it means**: If you re-ran the benchmark many times, 95% of the results would fall within [CI_lower, CI_upper].

**Calculation**: Bootstrap resampling with 10,000 iterations (seed=42 for reproducibility)

**Interpretation**:
- **Narrow CI** (e.g., [78.0, 79.5]): Consistent scores, high precision
- **Wide CI** (e.g., [70.0, 85.0]): Variable scores, low precision

**Example**:
```
Clarity (GPT-4): Mean=77.8, 95% CI=[76.2, 79.4]
→ You can be 95% confident the true mean is between 76.2 and 79.4
```

---

## Inter-Rater Reliability

When you use **multiple evaluators** (e.g., GPT-4 and Claude), the framework automatically measures **agreement** between them using three complementary metrics.

### Intraclass Correlation Coefficient (ICC)

**Type**: ICC(2,1) — two-way mixed effects, absolute agreement, single measurement

**What it measures**: Overall consistency in absolute scores across raters

**Scale**: 0 to 1 (higher is better)
- **ICC &lt; 0.5**: Poor
- **0.5 ≤ ICC &lt; 0.75**: Moderate
- **0.75 ≤ ICC &lt; 0.9**: Good
- **ICC ≥ 0.9**: Excellent

**With 95% CI**: [CI_lower, CI_upper] indicates confidence in the ICC estimate

**Example**:
```
Distractor Quality across GPT-4 and Claude:
ICC = 0.794 [95% CI: 0.582, 0.906]
→ Good agreement; CI is wide, suggesting moderate precision
```

### Mean Absolute Deviation (MAD)

**What it measures**: Average disagreement between raters, expressed on the original score scale (0–100)

**Scale**: 0–100 points
- **MAD &lt; 3**: Excellent agreement (very close ratings)
- **3 ≤ MAD &lt; 5**: Good agreement (minor differences)
- **5 ≤ MAD &lt; 10**: Moderate agreement (some systematic differences)
- **MAD ≥ 10**: Poor agreement (large systematic differences)

**Example**:
```
Clarity metric across GPT-4 and Claude:
MAD = 3.45 points
→ On average, raters differ by 3.45 points (on 0–100 scale)
```

**Advantages**: Directly interpretable — a MAD of 5 means raters disagree by 5 points on average.

### Spearman Rank Correlation (ρ)

**What it measures**: Whether raters rank quiz items in the same order (rank agreement)

**Scale**: −1 to 1
- **ρ &lt; 0**: Negative correlation (opposite ranking)
- **0 ≤ ρ ≤ 0.5**: Weak rank agreement
- **0.5 &lt; ρ ≤ 0.8**: Moderate to good rank agreement
- **ρ &gt; 0.8**: Excellent rank agreement

**Example**:
```
Clarity metric across GPT-4 and Claude:
Spearman ρ = 0.876
→ Strong rank agreement: both raters agree on which questions are clear/unclear
```

**Advantages**: Insensitive to systematic bias (e.g., one rater always scoring 10 points higher). Focuses on *relative* rather than absolute agreement.

---

## How to Interpret Results

### Scenario 1: High Consistency (Good)

```json
{
  "metric_name": "clarity",
  "evaluator_model": "gpt-4",
  "mean": 82.5,
  "std_dev": 1.2,
  "ci_lower": 81.8,
  "ci_upper": 83.2,
  "num_runs": 5
}
```

**Interpretation**:
- Scores are tightly clustered (std_dev = 1.2)
- Narrow confidence interval
- **Conclusion**: GPT-4's clarity assessment is reliable and repeatable

### Scenario 2: High Variance (Concerning)

```json
{
  "metric_name": "alignment",
  "evaluator_model": "gpt-4",
  "mean": 72.3,
  "std_dev": 8.9,
  "ci_lower": 62.1,
  "ci_upper": 82.5,
  "num_runs": 5
}
```

**Interpretation**:
- Scores vary widely (std_dev = 8.9)
- Wide confidence interval (20.4 points)
- **Possible causes**:
  - Ambiguous metric prompt
  - Complex questions with multiple interpretations
  - Stochasticity in LLM (try temperature=0.0)
- **Action**: Increase runs to 10+, refine metric prompt, or simplify questions

### Scenario 3: Evaluator Disagreement

```json
"inter_rater_reliability": {
  "clarity": {
    "icc": 0.51,
    "mad": 7.2,
    "spearman_rho": 0.42,
    "num_raters": 2
  }
}
```

**Interpretation**:
- GPT-4 and Claude show weak agreement (ICC = 0.51, rho = 0.42)
- Average disagreement is significant (MAD = 7.2 points)
- **Possible causes**:
  - Different evaluation styles/priorities
  - One model more lenient than other
  - Metric prompt is ambiguous
- **Action**: 
  - Review raw responses to understand disagreement
  - Refine metric prompt to be more specific
  - Use model-specific evaluation approaches

---

## Analyzing Raw Results Programmatically

### Load and Analyze Results

```python
import json
import statistics
from pathlib import Path

# Load aggregated results
agg_path = "data/results/my_benchmark_20250512/aggregated.json"
with open(agg_path) as f:
    agg = json.load(f)

# Print all metric statistics
for agg_key, metric_stats in agg['aggregations'].items():
    print(f"\n{agg_key}:")
    print(f"  Mean:    {metric_stats['mean']:.2f}")
    print(f"  Median:  {metric_stats['median']:.2f}")
    print(f"  Std Dev: {metric_stats['std_dev']:.2f}")
    print(f"  95% CI:  [{metric_stats['ci_lower']:.2f}, {metric_stats['ci_upper']:.2f}]")
    print(f"  Runs:    {metric_stats['num_runs']}")

# Check inter-rater reliability
print("\nInter-Rater Reliability:")
for metric_name, irr_metrics in agg['inter_rater_reliability'].items():
    icc = irr_metrics.get('icc')
    mad = irr_metrics.get('mad')
    rho = irr_metrics.get('spearman_rho')
    print(f"\n{metric_name}:")
    if icc is not None:
        ci_lower = irr_metrics.get('icc_ci_lower')
        ci_upper = irr_metrics.get('icc_ci_upper')
        if ci_lower and ci_upper:
            print(f"  ICC(2,1): {icc:.4f} [95% CI: {ci_lower:.4f}, {ci_upper:.4f}]")
        else:
            print(f"  ICC(2,1): {icc:.4f}")
    if mad is not None:
        print(f"  MAD: {mad:.2f} points")
    if rho is not None:
        print(f"  Spearman rho: {rho:.4f}")
```

### Compare Evaluators

```python
# Extract all aggregations for a specific metric
metric_name = "clarity"
evaluator_stats = {}

for agg_key, stats in agg['aggregations'].items():
    if stats['metric_name'] == metric_name:
        evaluator_name = stats['evaluator_model']
        evaluator_stats[evaluator_name] = {
            'mean': stats['mean'],
            'std_dev': stats['std_dev'],
            'ci_lower': stats['ci_lower'],
            'ci_upper': stats['ci_upper'],
        }

# Print comparison
print(f"\n{metric_name} Comparison:")
print(f"{'Evaluator':<25} {'Mean':<10} {'Std Dev':<10} {'95% CI':<20}")
print("-" * 65)
for evaluator, stats in evaluator_stats.items():
    ci_str = f"[{stats['ci_lower']:.1f}, {stats['ci_upper']:.1f}]"
    print(f"{evaluator:<25} {stats['mean']:<10.2f} {stats['std_dev']:<10.2f} {ci_str:<20}")
```

### Identify High-Variance Metrics

```python
# Find metrics with high variance
print("Metrics with High Variance (Std Dev > 5):")
for agg_key, stats in agg['aggregations'].items():
    if stats['std_dev'] > 5:
        print(f"\n{stats['metric_name']} ({stats['evaluator_model']}):")
        print(f"  Mean: {stats['mean']:.2f}")
        print(f"  Std Dev: {stats['std_dev']:.2f}")
        print(f"  Recommendation: Increase runs or refine metric")
```

---

## Best Practices for Result Interpretation

### ✅ DO

- **Report confidence intervals** alongside means: "Clarity: 78.5 ± [76.2, 80.8]"
- **Note standard deviation**: "Results were consistent (σ = 1.2)"
- **Check inter-rater reliability**: "Two models showed good agreement (ICC = 0.82)"
- **Use medians for skewed data**: "Median clarity score was 79 (less affected by outliers)"
- **Compare across multiple runs**: "Metric became more consistent after 10 runs"
- **Document model versions**: "Using GPT-4-0613, not just 'gpt-4'"

### ❌ DON'T

- Report single scores without context: "Clarity: 78.5" (no confidence band)
- Ignore high variance: "Std Dev = 12, but we'll ignore it"
- Over-interpret single data points: "One score was 95, so clarity is perfect"
- Compare metrics across different evaluators without noting differences
- Trust only one evaluator without checking inter-rater reliability
- Use results from single run (no averaging)

---

## Exporting Results for Papers

### JSON for Data Analysis

```bash
# Copy aggregated results for analysis
cp data/results/my_benchmark_20250512/aggregated.json results/my_study.json

# Load in R, Python, or Excel
# See code examples above
```

### Summary Tables in Markdown

```python
import json
import pandas as pd

with open('data/results/my_benchmark_20250512/aggregated.json') as f:
    agg = json.load(f)

# Create DataFrame
rows = []
for agg_key, stats in agg['aggregations'].items():
    rows.append({
        'Metric': stats['metric_name'],
        'Evaluator': stats['evaluator_model'],
        'Mean': f"{stats['mean']:.2f}",
        'Std Dev': f"{stats['std_dev']:.2f}",
        '95% CI': f"[{stats['ci_lower']:.2f}, {stats['ci_upper']:.2f}]",
    })

df = pd.DataFrame(rows)
print(df.to_markdown(index=False))
```

### Visualizing Confidence Intervals

```python
import matplotlib.pyplot as plt
import numpy as np

# Extract data
metrics = []
means = []
cis_lower = []
cis_upper = []

for agg_key, stats in agg['aggregations'].items():
    metrics.append(f"{stats['metric_name']}\n({stats['evaluator_model'][:8]})")
    means.append(stats['mean'])
    cis_lower.append(stats['ci_lower'])
    cis_upper.append(stats['ci_upper'])

# Plot
fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(metrics))
yerr = [
    [means[i] - cis_lower[i] for i in range(len(means))],
    [cis_upper[i] - means[i] for i in range(len(means))]
]

ax.bar(x, means, yerr=yerr, capsize=5, alpha=0.7)
ax.set_ylabel('Score (0-100)')
ax.set_title('Metric Scores with 95% Confidence Intervals')
ax.set_xticks(x)
ax.set_xticklabels(metrics, rotation=45, ha='right')
ax.set_ylim([0, 100])
plt.tight_layout()
plt.savefig('results/confidence_intervals.png', dpi=300)
```

---

## Advanced: Understanding Bootstrap Confidence Intervals

The framework uses **bootstrap resampling** to compute confidence intervals without assuming a particular distribution.

### How It Works

```python
def bootstrap_confidence_interval(data, ci=0.95, n_bootstrap=10000):
    """
    1. Original data: [75, 78, 76, 79, 77]
    2. Resample 10,000 times with replacement:
       - Bootstrap sample 1: [75, 79, 78, 75, 76] → mean = 76.6
       - Bootstrap sample 2: [77, 78, 76, 79, 78] → mean = 77.6
       - Bootstrap sample 3: [75, 75, 78, 77, 79] → mean = 76.8
       - ... (9,997 more)
    
    3. Calculate percentiles:
       - 2.5th percentile = 76.2
       - 97.5th percentile = 79.4
    
    4. Result: 95% CI = [76.2, 79.4]
    """
```

### Why Bootstrap?

- **No distribution assumptions** (works with any data distribution)
- **Reproducible** (seed=42 ensures same results)
- **Robust to skewed data** (doesn't assume normality)

---

## Summary

|         Aspect          | Key Takeaway                                                     |
|-------------------------|------------------------------------------------------------------|
|   **Why aggregate?**    | Reduce noise, estimate confidence, detect agreement/disagreement |
|   **Key statistics**    | Mean, median, std dev, confidence intervals                      |
| **Reliability metrics** | ICC, MAD, and Spearman ρ measure evaluator agreement             |
|   **Interpretation**    | Report with confidence intervals; watch for high variance        |
|     **For papers**      | Export JSON for analysis, create visualizations from CI data     |