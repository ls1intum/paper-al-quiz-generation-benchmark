---
title: Statistical Methods & Paper Reporting
sidebar_position: 8
---

# Statistical Methods & Paper Reporting

This guide explains the statistical methods used in the framework and how to report results in academic papers.

---

## Statistical Foundations

### Terminology

|      Term       |                           Definition                          |               Application               |
|-----------------|---------------------------------------------------------------|-----------------------------------------|
|     **Run**     | One complete evaluation cycle of all quizzes with all metrics | Used to accumulate data for aggregation |
|    **Score**    |     Individual 0-100 rating from one evaluator in one run     |              Raw data point             |
| **Aggregation** |     Statistical combination of scores across multiple runs    |         Produces summary statistics     |
|  **Evaluator**  |  An LLM instance that produces scores (e.g., GPT-4, Claude)   |       Can compare evaluator agreement   |
|   **Metric**    |  A quality dimension being measured (e.g., clarity, accuracy) |   Can assess consistency within metrics |

### Why Multiple Runs?

Single evaluation runs are subject to **random variation**:
- LLM responses vary even with temperature=0.0 (due to internal stochasticity)
- A single score may not reflect true underlying quality
- Multiple runs enable statistical inference

**Example**:
- Run 1: Clarity = 75
- Run 2: Clarity = 78  
- Run 3: Clarity = 76
- **Aggregated**: Mean = 76.3, CI = [74.8, 77.8]

The confidence interval reflects our uncertainty about the true underlying score.

---

## Methods for Statistical Aggregation

### 1. Descriptive Statistics

Standard summary statistics computed across all runs for a given metric-evaluator pair:

```
Data: [75, 78, 76, 79, 77]

Mean (μ)       = (75+78+76+79+77)/5 = 77.0
Median (M)     = 76 (middle value when sorted)
Std Dev (σ)    = √[Σ(xi-μ)²/(n-1)] = 1.58
Min            = 75
Max            = 79
Range          = 4
```

**Interpretation**:
- **Mean**: Central tendency, use for comparisons
- **Median**: Robust alternative if outliers present
- **Std Dev**: Variability (higher = less consistent)
- **Range**: Spread from minimum to maximum

### 2. Bootstrap Confidence Intervals (95%)

A non-parametric method to estimate uncertainty without assuming normal distribution.

#### Algorithm

```
Input: data = [75, 78, 76, 79, 77]

1. Resample with replacement 10,000 times:
   Bootstrap sample 1: [79, 75, 78, 76, 75] → mean = 76.6
   Bootstrap sample 2: [77, 79, 76, 78, 77] → mean = 77.4
   Bootstrap sample 3: [76, 76, 77, 79, 78] → mean = 77.2
   ... (9,997 more samples)

2. Sort all 10,000 bootstrap means:
   [73.8, 74.1, 74.5, ..., 77.8, 78.1, 78.4]

3. Extract percentiles:
   2.5th percentile = 74.9  (lower bound)
   97.5th percentile = 79.1 (upper bound)

Result: 95% CI = [74.9, 79.1]
```

#### Why Bootstrap?

✅ **Advantages**:
- Works with any distribution (no normality assumption)
- Naturally handles skewed, bimodal, or heavy-tailed data
- Transparent: directly estimates from resampled empirical data
- Reproducible: seeded RNG (seed=42)

❌ **Alternatives** (and why we don't use them):
- **Parametric CI** (t-distribution): Assumes normality; fails for skewed data
- **Standard Error**: Less robust; assumes symmetric distribution
- **No CI**: Insufficient uncertainty quantification

#### Interpretation

```
Clarity Score = 77.8, 95% CI = [76.2, 79.4]

Interpretation:
- Central estimate: 77.8
- Uncertainty range: 76.2 to 79.4
- Meaning: We're 95% confident the true mean lies in [76.2, 79.4]
- Narrowness: Narrow CI indicates precise, consistent estimates

Compare:
- Narrow CI [76.2, 79.4]:  Consistent scores, high precision
- Wide CI   [70.0, 85.0]:  Variable scores, low precision
```

### 3. Inter-Rater Reliability

When multiple evaluators (e.g., different LLM models) assess the same content, measure their **agreement**.

#### Krippendorff's Alpha (α)

**Type**: Ordinal (interval/ratio) scale agreement coefficient

**Formula**:
$$\alpha = 1 - \frac{D_o}{D_e}$$

where:
- $D_o$ = observed disagreement
- $D_e$ = expected disagreement by chance

**Scale & Interpretation**:
| α Value | Interpretation | Action |
|---------|----------------|--------|
| α < 0 | Worse than random | Models actively disagree |
| 0 ≤ α ≤ 0.40 | Poor | Cannot rely on models alone |
| 0.40 < α ≤ 0.60 | Fair | Use with caution; consider ensemble |
| 0.60 < α ≤ 0.75 | Moderate | Acceptable; note differences |
| 0.75 < α ≤ 0.85 | Substantial | Good agreement; reliable |
| α > 0.85 | Near-perfect | Excellent agreement |

**Example**:
```
Model A scores: [75, 78, 76, 79, 77]
Model B scores: [76, 79, 75, 80, 78]

Krippendorff's α = 0.82
→ Substantial agreement between models
```

#### Intraclass Correlation Coefficient (ICC)

**Type**: ICC(2,1) — two-way mixed, absolute agreement, single measurement

**Interpretation**: Correlation between raters' absolute scores

**Scale & Interpretation**:
| ICC | Interpretation |
|-----|----------------|
| < 0.50 | Poor agreement |
| 0.50–0.75 | Moderate agreement |
| 0.75–0.90 | Good agreement |
| > 0.90 | Excellent agreement |

**With Confidence Intervals**:
```
ICC = 0.82, 95% CI = [0.71, 0.91]

Interpretation:
- Point estimate: 0.82 (good agreement)
- Uncertainty: CI is relatively wide, suggesting moderate precision
- Meaning: We're 95% confident true ICC is between 0.71 and 0.91
```

#### Which to Use?

- **Krippendorff's α**: General-purpose, handles any scale type
- **ICC**: When you want correlation interpretation, symmetric case

Both are reported in aggregated results.

---

## Reporting in Academic Papers

### Section: Methods

```markdown
## Evaluation Methodology

### Quiz Evaluation Framework
We evaluated quiz quality using [framework name], a benchmark system 
that applies multiple LLM-based metrics to assess different dimensions 
of quiz quality.

### Metrics
We evaluated quizzes across [N] quality metrics:
- Clarity (language quality, unambiguous phrasing)
- Accuracy (factual correctness, evidence-based content)
- Distractor Quality (pedagogical effectiveness of incorrect options)
[... list others ...]

Each metric produces a score on a 0–100 scale, with detailed rubrics 
provided in [supplementary materials / appendix].

### Evaluators
We used [N] LLM-based evaluators:
- GPT-4 (OpenAI)
- Claude 3 Opus (Anthropic)
[... others ...]

All evaluators used temperature=0.0 for deterministic evaluation, and 
we prompted each evaluator with identical prompts (see Appendix A).

### Statistical Aggregation
To ensure reliable and reproducible results, we:

1. **Multiple Runs**: Each quiz was evaluated in [N] independent runs, 
   allowing us to estimate score stability and variance.

2. **Confidence Intervals**: We computed 95% confidence intervals using 
   bootstrap resampling (10,000 iterations, seed=42), which provides 
   robust uncertainty estimates without assuming normal distribution.

3. **Inter-Rater Reliability**: When multiple evaluators assessed the 
   same questions, we measured agreement using:
   - Krippendorff's alpha (α): General-purpose agreement coefficient
   - ICC(2,1): Intraclass correlation coefficient for symmetric agreement
   
   These metrics quantify whether different LLM evaluators converge on 
   similar assessments (α, ICC > 0.75 indicates substantial agreement).

4. **Descriptive Statistics**: For each metric-evaluator combination, 
   we report mean, median, standard deviation, min, and max across runs.
```

### Section: Results

```markdown
## Results

### Overall Evaluation Summary

Table 1 presents aggregated evaluation results across all quizzes 
and runs. GPT-4 rated clarity highest (M=82.5, SD=1.2), followed by 
Claude (M=81.2, SD=2.1). The narrow confidence intervals [81.8, 83.2] 
and [79.1, 83.3] suggest consistent and reproducible assessments.

| Metric | Evaluator | Mean | SD | 95% CI |
|--------|-----------|------|----|----|
| Clarity | GPT-4 | 82.5 | 1.2 | [81.8, 83.2] |
| Clarity | Claude | 81.2 | 2.1 | [79.1, 83.3] |
| Accuracy | GPT-4 | 78.3 | 3.4 | [75.2, 81.4] |
| ... | ... | ... | ... | ... |

### Inter-Rater Reliability

To assess evaluator agreement, we computed inter-rater reliability 
metrics (Table 2). For clarity, Krippendorff's α = 0.74 and ICC = 0.82, 
both indicating substantial agreement. This suggests GPT-4 and Claude 
converge on similar clarity assessments, strengthening confidence in 
the underlying construct.

| Metric | Krippendorff's α | ICC(2,1) | 95% CI |
|--------|---------|----------|--------|
| Clarity | 0.74 | 0.82 | [0.71, 0.91] |
| Accuracy | 0.68 | 0.75 | [0.61, 0.87] |
| ... | ... | ... | ... |

Higher α and ICC values indicate stronger consensus between evaluators. 
All metrics exceeded α > 0.60 (moderate agreement), suggesting the 
metrics reliably capture their intended constructs.

### Variance & Consistency

Standard deviation ranged from 1.2 to 5.8 across metrics. Lower 
variance (SD < 2) indicates evaluators consistently ranked quizzes; 
higher variance suggests greater sensitivity to quiz characteristics 
or ambiguity in the metric prompt. We discuss implications in Section X.
```

### Section: Discussion

```markdown
## Discussion

### Reliability of Automated Assessment

Our multi-run evaluation with bootstrap confidence intervals 
demonstrates that [Framework] provides reproducible, reliable assessment 
of quiz quality. The narrow confidence intervals (mean width: X) and 
high inter-rater agreement (mean α = Y) indicate both within-model 
consistency and cross-model agreement.

### Differences Between Evaluators

While GPT-4 and Claude showed substantial agreement overall (α = 0.74), 
we observed notable differences on [specific metrics]. This may reflect 
different training data, evaluation heuristics, or sensitivity to 
particular linguistic features. We recommend [assessment approach] 
when using multiple evaluators.

### Limitations

1. **LLM-Based Assessment**: Our metrics rely on LLM evaluations, 
   which may not perfectly align with expert human judgment. However, 
   high inter-rater agreement (ICC = 0.82) suggests the metrics capture 
   consistent, reproducible quality dimensions.

2. **Score Distribution**: Some metrics showed higher variance 
   (SD = 5.8 for [metric]). This may indicate genuine quiz variability 
   or metric prompt ambiguity. Future work should refine these prompts.

3. **Generalization**: This study used [N] quizzes on [topic]. 
   Generalization to other domains requires replication.
```

---

## Example Figures & Tables

### Figure 1: Confidence Intervals

```
         Clarity Scores with 95% Confidence Intervals

100  │
  85  │     ┌─────┐         ┌──────┐
  80  │ ═══██════xx═══     ═███════xx════
  75  │     └─────┘         └──────┘
  70  │
  65  │
     └─────────────────────────────────────
       GPT-4        Claude      LLaMA
```

**Caption**: Mean clarity scores (×) with 95% bootstrap confidence intervals (bars). 
Narrower intervals indicate more consistent evaluations. GPT-4 (CI = [81.8, 83.2]) 
shows higher consistency than Claude (CI = [79.1, 83.3]).

### Figure 2: Distribution of Scores Across Runs

```
Distribution of Clarity Scores (5 runs)

     Run 1  Run 2  Run 3  Run 4  Run 5
GPT-4:  82.5   81.8   82.1   83.2   82.9  → Mean = 82.5, SD = 0.53
Claude: 79.3   80.1   81.5   82.1   80.8  → Mean = 80.76, SD = 1.20
```

### Table 3: Comprehensive Results Template

```markdown
| Metric | Evaluator | Mean | SD | Min | Max | 95% CI | N |
|--------|-----------|------|----|----|-------|--------|---|
| Clarity | GPT-4 | 82.5 | 1.2 | 80.1 | 84.3 | [81.8, 83.2] | 50 |
| Clarity | Claude | 81.2 | 2.1 | 77.5 | 85.2 | [79.1, 83.3] | 50 |
| Accuracy | GPT-4 | 78.3 | 3.4 | 71.0 | 86.5 | [75.2, 81.4] | 50 |
| Accuracy | Claude | 76.8 | 4.2 | 68.3 | 87.1 | [73.1, 80.5] | 50 |
```

---

## Supplementary Materials Checklist

For full reproducibility, include:

- [ ] **Configuration Files**: All YAML configs used (benchmark_*.yaml)
- [ ] **Environment Details**: Python version, package versions (from requirements.txt or piproject.toml)
- [ ] **Raw Results**: aggregated.json (or summary statistics if space-limited)
- [ ] **Prompts**: LLM prompts used for each metric (in appendix or supplementary)
- [ ] **Data Description**: Number of quizzes, source materials, question types
- [ ] **Statistical Details**: 
  - [ ] Bootstrap methodology (n_iterations=10,000, seed=42)
  - [ ] Inter-rater reliability calculation details
  - [ ] Number of runs per evaluation
- [ ] **Code/Repository**: GitHub link or Zenodo DOI for code version

---

## Common Reporting Phrases

### Descriptive

- "Clarity ratings were consistent across runs (M=82.5, SD=1.2, 95% CI=[81.8, 83.2])"
- "GPT-4 rated accuracy lower than Claude (80.3 vs 82.1 respectively)"
- "High variance in distractor quality scores (SD=5.8) suggests sensitivity to content"

### Inter-Rater Reliability

- "Substantial agreement between evaluators (α=0.74, ICC=0.82)"
- "Evaluator agreement ranged from poor (α=0.42) to excellent (α=0.89)"
- "Inter-rater reliability exceeded the 0.75 threshold for [metric]"

### Confidence & Precision

- "Narrow confidence intervals indicate precise, reproducible estimates"
- "Wide confidence intervals [65.2, 91.3] reflect high score variability"
- "We can be 95% confident the true mean falls within [76.2, 79.4]"

### Reproducibility

- "Deterministic evaluation (temperature=0.0) and seeded randomness ensure reproducibility"
- "Multiple independent runs (N=5) reduced noise and enabled statistical inference"
- "Configuration hashing and versioning enable exact reproduction of results"

---

## References & Further Reading

- Krippendorff, K. (2004). *Reliability in content analysis*. Human Communication Research.
- Efron, B., & Tibshirani, R. (1993). *An introduction to the bootstrap*. Chapman and Hall.
- Koo, T. K., & Li, M. Y. (2016). A guideline of selecting and reporting intraclass correlation coefficients for reliability research. *Journal of Chiropractic Medicine*, 15(2), 155–163.

