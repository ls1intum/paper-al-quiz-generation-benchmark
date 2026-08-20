# Quality Criteria Coverage Report

This report assesses how well the benchmark's metrics cover the nine quality
criteria extracted from the literature in the paper
(`paper-al-quiz-generation/paper/sections/relatedwork.tex`, Table
`tab:quality-criteria`). For each criterion it states the coverage status,
documents divergences from the definition, and lists actionable improvements.

## Summary

The benchmark registers **7 metrics** (`src/metrics/__init__.py`):
`coverage`, `difficulty`, `accuracy`, `clarity`, `distractor_quality`,
`homogeneous_options`, `grammatical_correctness`.

| # | Criterion (paper) | Metric | Status |
|---|---|---|---|
| 1 | Alignment with Learning Objectives | `coverage` | ⚠️ Partial — measures *source-topic* coverage, not stated learning objectives |
| 2 | Cognitive Level Appropriateness | `difficulty` (+ `coverage` depth) | ⚠️ Partial — scores *absolute* level, not appropriateness vs. a target |
| 3 | Factual Accuracy | `accuracy` | ✅ Covered |
| 4 | Clarity and Precision | `clarity` | ⚠️ Partial — negative phrasing not checked |
| 5 | Answer Key Correctness | — | ❌ Missing — no dedicated metric |
| 6 | Distractor Quality | `distractor_quality` | ✅ Covered |
| 7 | Homogeneous Options | `homogeneous_options` | ✅ Covered |
| 8 | Absence of Cueing | (partial in `distractor_quality`) | ❌ Largely missing — no dedicated metric |
| 9 | Grammatical Correctness | `grammatical_correctness` | ✅ Covered |

**Headline gaps:** Criterion 5 (Answer Key Correctness) and Criterion 8
(Absence of Cueing) have no dedicated metric. Criterion 1 conflates source
coverage with learning-objective alignment, and Criterion 4 omits the explicit
negative-phrasing check named in its definition.

---

## Criterion 1 — Alignment with Learning Objectives

**Definition:** *Questions accurately assess intended learning outcomes and match instructional goals.*

**Status: ⚠️ Partial / diverges.**

`CoverageMetric` (`src/metrics/coverage.py`) extracts topics and "critical
concepts" from the **source material** and scores breadth/depth/balance/critical
coverage against them. This is a content-coverage proxy, not alignment with
*stated learning objectives*. There is no learning-objectives input in the
pipeline: `QuizInstructions` (`src/models/instruction.py`) has no
`learning_objectives` field, and the only reference to learning objectives in
the codebase is read for display context in `grammatic.py:143-145` — never
scored against. The criterion's references (Sireci 1998 construct/content
validity, Moreno 2006) concern alignment to *intended outcomes*, which the
benchmark does not measure.

**Divergences:**
- Ground truth is auto-derived from source text, not from instructor-supplied learning objectives.
- "Match instructional goals" is unmeasured; an LLM-invented topic set stands in for the intended outcomes.

**Actionable improvements:**
1. Add a `learning_objectives: List[str]` field to `QuizInstructions` and thread it through `PhaseInput`.
2. Add an alignment sub-score (or a new `objective_alignment` metric) that maps each question to the supplied objectives and scores coverage/match against them, falling back to source-topic extraction only when no objectives are provided.
3. Document explicitly in the paper/metric docstring that `coverage` measures source-content coverage and is a *proxy* for, not a direct measure of, learning-objective alignment.

---

## Criterion 2 — Cognitive Level Appropriateness

**Definition:** *Questions target appropriate levels of Bloom's taxonomy (remembering, understanding, applying, analyzing, evaluating, creating).*

**Status: ⚠️ Partial.**

`DifficultyMetric` (`src/metrics/difficulty.py`) scores cognitive complexity
using a full 6-level Bloom rubric (or Webb's DoK). `CoverageMetric` also assigns
a Bloom level per question for its depth sub-score. So Bloom level *is*
estimated. However:

**Divergences:**
- The metric scores **absolute** difficulty, not **appropriateness** — i.e. whether the level matches the level the objective/audience requires. "Appropriate" presupposes a target; without one, the metric only reports where on the scale a question lands.
- A target only exists when `instructions.difficulty` is set, and that field is `easy/medium/hard` (`src/models/instruction.py:19`) — a difficulty band, **not** a Bloom level. The two are conflated.
- Inconsistent taxonomies across metrics: `coverage` uses a 3-level scale (recall/understanding/application, `coverage.py:168-172`) while `difficulty` uses the full 6-level Bloom (`difficulty.py:76-82`). The same construct is operationalized two different ways.

**Actionable improvements:**
1. Allow a target cognitive level (per quiz or per objective) as input, and score the *distance* from that target rather than the absolute level.
2. Reconcile the taxonomy: have `coverage` and `difficulty` share one Bloom-level definition (either both 6-level or both 3-level) to avoid divergent depth signals.
3. Decouple Bloom level from the `easy/medium/hard` difficulty band, or document that they are intentionally distinct constructs.

---

## Criterion 3 — Factual Accuracy

**Definition:** *Question content and the designated correct answer are factually correct and free of hallucinated information.*

**Status: ✅ Covered.**

`FactualAccuracyMetric` (`src/metrics/accuracy.py`) evaluates factual
correctness, evidence-basis, bias/distortion, source alignment, and objectivity,
and surfaces `major_errors_found`. Source-material grounding is passed in. This
matches the definition well.

**Minor notes / improvements:**
1. The prompt does not strongly distinguish *hallucination relative to the source* from general world-knowledge correctness; consider an explicit "is this supported by the provided source?" sub-judgment to directly target hallucination (the word in the definition).
2. `source_context` is injected even when `source_text` is `None` (becomes `"Source Material: None"`); guard this so the prompt reads cleanly without a source.

---

## Criterion 4 — Clarity and Precision

**Definition:** *Question stems and answer options use clear, unambiguous language without unnecessary complexity or **negative phrasing**.*

**Status: ⚠️ Partial.**

`ClarityMetric` (`src/metrics/clarity.py`) scores ambiguity, option
distinctness, overlap, "trick" wordings, and overall readability — covering the
"clear, unambiguous language without unnecessary complexity" portion.

**Divergences:**
- **Negative phrasing is not checked.** The definition explicitly names it (Haladyna guideline: avoid/emphasize negatives such as "Which is NOT…"), but the clarity prompt never mentions negation. This is a named sub-requirement that is forgotten.

**Actionable improvements:**
1. Add an explicit instruction to the clarity prompt to detect and penalize unmarked negative phrasing in stems (e.g. NOT/EXCEPT), per Haladyna 2002 / Downing 2005.
2. Optionally report a structured flag (`contains_negation`) so negative-phrasing prevalence can be aggregated across a quiz.

---

## Criterion 5 — Answer Key Correctness

**Definition:** *Exactly one option is unambiguously correct (or clearly best) while all distractors are unambiguously incorrect; "none/all of the above" options are excluded.*

**Status: ❌ Missing.**

No metric covers this criterion. Specifically:
- **"Exactly one correct"** is not checked. `accuracy` verifies the *designated* answer is factually correct but never tests whether a distractor is *also* defensibly correct — the exact failure mode the related-work section highlights (Doughty 2024: AI items show 4.9% multiple-correct rate vs. 1.1% human).
- **"All distractors unambiguously incorrect"** is not verified; `distractor_quality` measures plausibility/discrimination, not correctness.
- **"none/all of the above" exclusion** is never checked anywhere in `src/` (confirmed by search).
- `clarity` lists "Is there a single, clearly correct answer?" as one incidental consideration (`clarity.py:100`), but it is folded into a clarity score and does not test distractor incorrectness or catch-all options.

**Actionable improvements (high priority):**
1. Add a dedicated `answer_key_correctness` metric that, given source material: (a) verifies the keyed answer is correct, (b) checks each distractor is unambiguously incorrect / not also defensible, and (c) flags multiple-defensible-answer items.
2. Add a deterministic check (Python, no LLM) that detects "none of the above" / "all of the above" style options and penalizes/flags them per Di Battista 2014 / Dochy 2001.
3. Report a quiz-level "multiple-correct rate" and "catch-all-option rate" to mirror the metrics cited in the related work.

---

## Criterion 6 — Distractor Quality

**Definition:** *Incorrect options are plausible to students lacking mastery but clearly wrong to knowledgeable students; distractors reflect common misconceptions rather than implausible or random alternatives.*

**Status: ✅ Covered.**

`DistractorQualityMetric` (`src/metrics/distractor.py`) runs an analyze→score
pipeline across plausibility/source-alignment, misconception targeting,
discriminatory power, collective quality, and audience calibration, with
explicit deduction triggers. This is a strong, definition-aligned implementation.

**Minor notes / improvements:**
1. Only `single_choice`/`multiple_choice` are supported (`distractor.py:96-100`); true/false is rejected (acceptable, since T/F has no distractors — but document the exclusion).
2. Requires `source_text` (raises if `None`); fine, but note this dependency in metric docs since other metrics tolerate a missing source.

---

## Criterion 7 — Homogeneous Options

**Definition:** *All answer choices are parallel in grammatical structure and homogeneous in content type; empirical evidence on the effect of homogeneity on psychometric properties is mixed.*

**Status: ✅ Covered.**

`HomogeneousOptionsMetric` (`src/metrics/homogeneous_options.py`) classifies
each option's grammatical form, content type, completeness, and length, then
scores grammatical parallelism, content-type homogeneity, and format
consistency, aggregating with a major-violation penalty. Matches the definition
closely.

**Minor notes / improvements:**
1. The paper's definition explicitly flags that the evidence is **mixed** (Applegate 2019 found no consistent psychometric effect). Consider documenting that this metric encodes a contested guideline, and/or down-weighting it relative to better-supported criteria so it does not dominate aggregate scores.

---

## Criterion 8 — Absence of Cueing

**Definition:** *Items do not contain grammatical, semantic, or structural clues that reveal the correct answer.*

**Status: ❌ Largely missing.**

The only related signal is one deduction trigger inside `distractor_quality`
("Any distractor inadvertently hints at the correct answer", `distractor.py:182`)
and the collective "cannibalization" check. There is **no dedicated cueing
metric**, and the classic cueing flaws named in the literature are not
systematically detected:
- **Grammatical cueing** — stem agreeing (a/an, singular/plural) with only the keyed option.
- **Length cueing** — the correct option being conspicuously longer/more qualified.
- **Word-repetition / clang cueing** — terms from the stem echoed only in the key.
- **Convergence / logical cueing** across the option set.

Critically, the existing signal looks at distractor→key hints, not at
**stem→key** cues, which is the more common cueing failure.

**Actionable improvements (high priority):**
1. Add a dedicated `cueing` (or `absence_of_cueing`) metric covering grammatical, length, word-repetition, and convergence cues between stem and key. References: Haladyna 2002, Downing 2005, Moore 2024.
2. Length cueing can be partly deterministic (compare key length vs. mean distractor length) to reduce LLM variance.
3. Surface a per-quiz cueing-violation rate.

---

## Criterion 9 — Grammatical Correctness

**Definition:** *Both stem and options are grammatically correct and properly punctuated.*

**Status: ✅ Covered.**

`GrammaticalCorrectnessMetric` (`src/metrics/grammatic.py`) evaluates grammar,
spelling, punctuation, sentence structure, and technical-writing standards
across both stems and options, with severity-weighted deductions. Language
mismatch is handled separately to avoid double-penalization. Matches the
definition.

**Minor notes / improvements:**
1. Quiz-level single score may mask a single badly-broken item among many clean ones; consider reporting a per-item breakdown or a worst-item flag (the definition is item-scoped).

---

## Prioritized Action List

Ordered by impact on faithfulness to the literature-derived criteria.

1. **[P0] Add an Answer Key Correctness metric (Criterion 5).** No coverage today; directly addresses the AI-specific failure mode (multiple defensible answers) emphasized in the related work. Include a deterministic "none/all of the above" detector.
2. **[P0] Add an Absence-of-Cueing metric (Criterion 8).** Currently only an incidental distractor sub-check; add stem→key grammatical/length/word-repetition/convergence cue detection.
3. **[P1] Score against stated learning objectives (Criterion 1).** Add a `learning_objectives` input and an alignment sub-score; stop equating source-topic coverage with objective alignment, or document the proxy explicitly.
4. **[P1] Add negative-phrasing detection to `clarity` (Criterion 4).** Named in the definition but absent from the prompt.
5. **[P2] Reconcile cognitive-level handling (Criterion 2).** Unify the Bloom taxonomy between `coverage` (3-level) and `difficulty` (6-level); separate Bloom level from the easy/medium/hard band; score appropriateness against a target when available.
6. **[P2] Reflect contested/AI-specific evidence in weighting & docs.** Flag `homogeneous_options` as a contested guideline (Applegate 2019); strengthen `accuracy`'s explicit source-grounded hallucination check.
7. **[P3] Cosmetic robustness.** Guard `accuracy` against `source_text=None`; document T/F exclusions for `distractor_quality`/`homogeneous_options`; add per-item breakdowns for quiz-level grammar.
