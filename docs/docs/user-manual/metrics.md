---
title: Supported Quality Metrics
sidebar_position: 4
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

