---
title: Supported Quality Metrics
sidebar_position: 4
---

## Supported Quality Metrics

### 1. Alignment with Learning Objectives

**Metric name**: `objective_alignment`

**Purpose**: Measure how directly each item assesses the learning objective stated for it. The
stated objective is the reference value — an item can be well written, factually sound, and
on-topic for the course and still score low here, because the only thing being measured is
whether it assesses *that* objective.

**References**: Haladyna et al. [10], Sireci [17]

**Scope**: Question-level — one result per question, with `question_id` populated.

**Required input**: `question.metadata.learning_objective`. This is per-question, not per-quiz:
a quiz-level objective list cannot serve a question set drawn from several quizzes. The metric
never invents an objective when the field is missing.

**Scoring**: the judge picks one of four levels and the score follows from it, so a verdict and
its number can never disagree. There is deliberately no midpoint.

| Level | Score | Meaning |
|---|---|---|
| `direct` | `100.0` | Assesses the stated objective head-on, at the concept or skill level it describes. |
| `partial` | `66.7` | Assesses part of the objective, or assesses it at a shallower level than stated. |
| `weak` | `33.3` | Related only through a prerequisite, surface vocabulary, or a tangential concept. |
| `none` | `0.0` | Does not assess the stated objective at all. |

**Items without an objective**: reported as `applicable: false` with
`alignment_level: "not_applicable"` and a score of `100.0`. They are excluded from the measure,
not judged to be perfect.

:::warning
`applicable: false` items score `100.0`, so **filter on `applicable` before averaging**. A naive
mean over all items counts every objective-less item as a perfect score.
:::

**Relationship to `coverage`**: `coverage` is a quiz-level measure of how well a quiz covers its
*source material*. It is a content-coverage measure, not an objective-alignment one — the two
answer different questions and neither substitutes for the other.

**Output** (`raw_response`):
- `applicable`, `alignment_level`, `score`
- `learning_objective` — the objective the item was judged against
- `matched_objective_aspects` — which parts of the objective the item assesses
- `missing_or_misaligned_aspects` — what it leaves untested or tests in a different direction
- `rationale`

**Example Configuration**:
```yaml
- name: "objective_alignment"
  version: "1.0"
  evaluators: ["gpt4"]
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

**Metric name**: `answer_key_correctness`

**Purpose**: Verify the marked answer key is correct and unambiguous — exactly one option is
unambiguously correct (or, for multiple choice, the keyed set is exactly the correct set) while
all distractors are unambiguously incorrect, and no catch-all option is present.

**References**: Haladyna et al. [10], Haladyna & Rodriguez [11]

**Scope**: Question-level — one result per question, with `question_id` populated.

**Scoring**: **Binary** — `100.0` when the key is correct and unambiguous, `0.0` otherwise.
Unlike the other metrics this one is not an ordinal: a key is either defensible or it is not, and
there is no useful middle ground to score. Averaging the metric across a quiz therefore reads
directly as the share of items with a sound answer key, and the issue flags say why the rest
failed.

**Rules by question type**:
- `single_choice` / `true_false`: exactly one option is unambiguously correct, and it is the keyed one.
- `multiple_choice`: the keyed **set** must equal the unambiguously-correct **set** — every keyed
  option is correct **and** no unkeyed option is also defensible.

**Issue flags** (reported in `raw_response`, empty when the key is sound):

| Flag | Meaning |
|---|---|
| `multiple_defensible` | An unkeyed option is also defensible — the key omits a correct option. |
| `keyed_answer_wrong` | A keyed option is actually incorrect. |
| `no_correct_option` | None of the options is correct. |
| `catch_all_present` | An "all/none of the above" style option appears. |

**Deterministic checks** (applied after the judge, so they hold regardless of the judge model):
- **Catch-all detection** — options opening with an "all of the above" / "none of the above"
  phrase, in English or German, fail the criterion even when technically correct. Detection is
  pure Python, so the same items are flagged by every judge model.
- **Empty key** — an item with no marked answer (`correct_answer: []`) is evaluated normally and
  flagged `no_correct_option` rather than crashing the run.

**Source material**: optional. When a source is available it is supplied as supporting context;
when it is absent the judge reasons from general expert knowledge and the item wording.

**Output** (`raw_response`):
- `key_correct` — the Yes/No verdict
- `defensible_correct_options` — the full set the judge considers correct
- `misclassified_options` — which options are keyed wrongly
- `issue_flags`, `catch_all_options`, `rationale`, `score`

**Example Configuration**:
```yaml
- name: "answer_key_correctness"
  version: "1.0"
  evaluators: ["gpt4"]
```

---

### 5. Distractor Quality

**Purpose**: Evaluate whether incorrect options (distractors) are pedagogically effective—plausible to students lacking mastery but clearly wrong to knowledgeable students. Distractors should target specific misconceptions and discriminate between knowledge levels.

**References**: Gierl et al. [9], Haladyna & Rodriguez [11]

**Scope**: Question-level

**Supported Question Types**: Single-choice, Multiple-choice

**Implementation Overview**

The distractor quality metric uses a **two-phase pipeline** to ensure rigorous, consistent evaluation:

1. **Phase 1 (Analyze)**: Dimensional analysis across five pedagogical dimensions without assigning a score
2. **Phase 2 (Score)**: Calibrated scoring derived strictly from Phase 1 analysis, with explicit deduction triggers

This approach reduces variance and improves consistency across multiple runs.

**Five Analysis Dimensions**

1. **Plausibility & Source Alignment**
   - Does each distractor use specific vocabulary, values, or concepts from the source material?
   - Would a student who skimmed the material find it attractive?
   - Are distractors generic (not grounded in source) or transparently wrong?

2. **Misconception Targeting**
   - What specific cognitive error or knowledge gap does each distractor exploit?
   - Are these real, predictable student mistakes—or arbitrary wrong answers?
   - Can a teacher diagnose exactly what a student misunderstood from their answer selection?

3. **Discriminatory Power**
   - Can any distractor be eliminated by common sense alone (no domain knowledge required)?
   - Does eliminating it require genuine mastery, or just surface familiarity?
   - Is it a trap for students who partially understand the concept?

4. **Collective Quality**
   - Do distractors cover distinct misconceptions, or do multiple distractors exploit the same error?
   - Does the distractor set as a whole discriminate better or worse than individual distractors alone?
   - Does any distractor inadvertently hint at or narrow down the correct answer?

5. **Audience Calibration**
   - Are distractors appropriately difficult for the expected student level?
   - Would an expert find them trivially eliminable? Would a total novice find them indistinguishable?
   - Do they match the source material's complexity level?

**Scoring Rubric (0-100)**

|  Score  |    Level   |                                                      Characteristics                                                                   |
|---------|------------|----------------------------------------------------------------------------------------------------------------------------------------|
|  0–20   |    Poor    | Distractors are absurd, unrelated, or obviously wrong to any reader                                                                    |
|  21–40  |    Weak    | Easily eliminated by common sense; no domain knowledge needed                                                                          |
|  41–60  |    Fair    | Plausible but generic; not grounded in source material or real misconceptions                                                          |
|  61–80  |    Good    | Grounded in source material, requires real knowledge to eliminate                                                                      |
|  81–100 |  Excellent | Highly plausible, exploits specific student errors, covers distinct misconceptions, calibrated to audience, set is collectively strong |

**Deduction Triggers** (Applied additively from starting score of 100)

- Any distractor eliminable by common sense alone: **−10 to −20**
- Any distractor not tied to source material (generic): **−5 to −15**
- Two or more distractors exploit same misconception: **−5 to −10**
- Any distractor inadvertently hints at correct answer: **−10 to −15**
- Distractor set poorly calibrated for expected audience: **−5 to −10**
- Predictable, obvious student error missing as distractor: **−5**

**Output Format**

The metric produces structured analysis and scoring output:

```json
{
  "plausibility_analysis": "Per-distractor analysis of source alignment",
  "misconception_analysis": "Per-distractor analysis of cognitive errors targeted",
  "discrimination_analysis": "Per-distractor analysis of knowledge level discrimination",
  "collective_analysis": "Analysis of distractor set as a whole",
  "difficulty_calibration": "Audience-level fit analysis",
  "deduction_explanation": "List of deductions applied with point values",
  "score": 72.5
}
```

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

**References**: Haladyna et al. [10], Downing [8], Applegate et al. [18]

**Scope**: Registered quiz-level, but **reported per question** — the metric judges every
question separately and emits one result per question, each with `question_id` populated.
Scores are joinable by `(quiz_id, question_id)` without parsing nested JSON.

**Implementation Notes**:
- The metric runs in three phases: per-question option analysis, per-question scoring, and a quiz-level aggregation computed in Python with no extra model call.
- For each applicable question, answer choices are classified by grammatical form, content type, and formatting signals before being scored.
- Because each question is judged independently, prompt size does not grow with the number of questions in a quiz.
- The per-question rows replace the quiz-level aggregate in the results file. Emitting both under one metric name would pool item scores with a quiz-level summary in every downstream average. The quiz-level figures — mean question score, major-violation rate, issue distribution — are recomputable from the per-question rows, which carry score, severity and issues.
- True/false questions are treated as not applicable: they still produce a row, with `applicable: false`, a score of `100.0`, and `not_applicable` among the issues.

**Output** (`raw_response`, one object per question):
- `question_score`, `severity` (`none` / `minor` / `major`), `issues`, `rationale`
- `applicable`, plus the three sub-scores (grammatical parallelism, content-type homogeneity, format consistency)

:::warning
Not-applicable questions score `100.0`, so **filter on `applicable` before averaging** — otherwise
every true/false item counts as perfectly homogeneous.
:::

**Evaluation Criteria**:
- Parallel grammatical structure across answer choices
- Homogeneous content type across answer choices
- Consistent formatting, punctuation, and broad length patterns
- Detection of structural outliers such as one full sentence among short phrases or one code fragment among prose options
- Transparent issue reporting through per-question diagnostics retained in the metric output

**Example Configuration**:
```yaml
- name: "homogeneous_options"
  version: "1.0"
  evaluators: ["gpt4"]
  enabled: true
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

### 9. Factual Accuracy

**Purpose**: Verify questions and answers are factually correct, evidence-based, free from errors and biases, and aligned with provided source material.

**Scope**: Question-level

**Evaluation Dimensions**:
- **Factual Correctness**: Are all statements accurate? Are there outdated facts or clear errors?
- **Evidence-Based Content**: Is the answer verifiable fact rather than opinion or theory?
- **Bias and Distortion**: Is it free from political, cultural, or personal bias? Are all options presented fairly?
- **Source Alignment**: Does it align with the provided source material? Does it contradict it?
- **Objectivity**: Would reasonable experts agree with the factual claims?

**Scoring Scale**:
- **0-20**: Highly Inaccurate (major errors, built on false premises)
- **21-40**: Inaccurate (notable errors, partially opinion)
- **41-60**: Moderately Accurate (mostly factual but minor inaccuracies)
- **61-80**: Accurate (factually correct and evidence-based)
- **81-100**: Highly Accurate (objective, perfectly grounded in evidence)

**Output**:
- Detailed reasoning across all five dimensions
- List of specific major errors found (if any)
- Numerical score (0-100)

**Example Configuration**:
```yaml
- name: "accuracy"
  version: "1.1"
  evaluators: ["gpt4", "claude_opus"]
```

---
