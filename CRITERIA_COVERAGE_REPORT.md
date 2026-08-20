# Quality Criteria Coverage Report

This report assesses how well the benchmark's metrics cover the nine quality
criteria extracted from the literature in the paper
(`paper-al-quiz-generation/paper/sections/relatedwork.tex`, Table
`tab:quality-criteria`). For each criterion it states the coverage status,
documents divergences from the definition, and lists actionable improvements.

## Summary

The benchmark registers **9 metrics** (`src/metrics/__init__.py`):
`coverage`, `difficulty`, `accuracy`, `clarity`, `distractor_quality`,
`homogeneous_options`, `grammatical_correctness`, `answer_key_correctness`,
`objective_alignment`.

| # | Criterion (paper) | Metric | Status |
|---|---|---|---|
| 1 | Alignment with Learning Objectives | `objective_alignment` | ✅ Covered |
| 2 | Cognitive Level Appropriateness | `difficulty` (+ `coverage` depth) | ⚠️ Partial — scores *absolute* level, not appropriateness vs. a target |
| 3 | Factual Accuracy | `accuracy` | ✅ Covered |
| 4 | Clarity and Precision | `clarity` | ⚠️ Partial — negative phrasing not checked |
| 5 | Answer Key Correctness | `answer_key_correctness` | ✅ Covered |
| 6 | Distractor Quality | `distractor_quality` | ✅ Covered |
| 7 | Homogeneous Options | `homogeneous_options` | ✅ Covered — now reported per item |
| 8 | Absence of Cueing | (partial in `distractor_quality`) | ❌ Largely missing — no dedicated metric |
| 9 | Grammatical Correctness | `grammatical_correctness` | ✅ Covered |

**Headline gaps:** Criterion 8 (Absence of Cueing) has no dedicated metric, and
Criterion 4 omits the explicit negative-phrasing check named in its definition.

---

## Criterion 1 — Alignment with Learning Objectives

**Definition:** *Questions accurately assess intended learning outcomes and match instructional goals.*

**Status: ✅ Covered** by `objective_alignment` (`src/metrics/objective_alignment.py`),
question-level, one result per item with `question_id` populated.

The metric scores each item against the objective stated for it in
`question.metadata.learning_objective` — a reference value that pre-exists the item, so scoring
is classification against an independent catalogue rather than back-fitting an objective to an
item that already exists.

- **Four-level ordinal, no midpoint.** The judge picks `direct` / `partial` / `weak` / `none` and
  the score is derived from that level (`100 / 66.7 / 33.3 / 0`), so a verdict and its number
  cannot disagree. The distinction the metric is built around is direct assessment versus loose
  topical relatedness: an item testing a prerequisite, surface vocabulary, or an adjacent concept
  scores `weak`, not `direct`.
- **Per-item, not per-quiz.** The objective lives in question metadata because a question set can
  mix items drawn from several quizzes, where one quiz-level objective list would not apply.
- **Items with no stated objective** are returned `applicable=false` /
  `alignment_level="not_applicable"` and are never guessed at. They remain ratable on every other
  metric.

**Divergences / caveats:**
1. **Not-applicable items score `100.0`.** This follows the convention `homogeneous_options`
   already uses for excluded questions, but it means an unfiltered mean counts every
   objective-less item as perfect. **Analysis must filter on `applicable` before aggregating.**
2. `coverage` is retained and unchanged, but it is **not** the alignment metric — it measures
   how well a quiz covers its *source material* (breadth/depth/balance over extracted topics),
   which is a different construct. It should be reported as source-content coverage, never as
   learning-objective alignment.
3. Improvement 1 below is **superseded**: adding `learning_objectives` to `QuizInstructions` is
   the wrong home for the reference value, since it is a per-item property.

**Actionable improvements:**
1. ~~Add a `learning_objectives: List[str]` field to `QuizInstructions` and thread it through `PhaseInput`.~~ **Superseded** — the reference value is per-item and lives in `question.metadata.learning_objective`.
2. ~~Add an alignment sub-score (or a new `objective_alignment` metric)…~~ **Done.**
3. Document explicitly in the metric docstring that `coverage` measures source-content coverage and is a *proxy* for, not a direct measure of, learning-objective alignment. *(Still open — `coverage.py` itself is unchanged.)*

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

**Status: ✅ Covered** by `answer_key_correctness` (`src/metrics/answer_key_correctness.py`),
question-level, one result per item with `question_id` populated.

The metric mirrors Form A §3.2 of `human-validation-plan.md` so that the judge and the human
raters answer the same question on the same scale:

- **Binary verdict.** "Is the marked answer key correct and unambiguous?" → `score` is `100.0`
  or `0.0`, never an ordinal. C2 is an *objective* criterion validated by the judge's
  accuracy/precision/recall against an adjudicated gold standard; an ordinal judge score would
  need a post-hoc cut-point to compare against a binary human verdict.
- **Exactly the four Form A sub-flags:** `multiple_defensible`, `keyed_answer_wrong`,
  `no_correct_option`, `catch_all_present`. Flags the judge invents outside this set are dropped,
  so every judge flag maps 1:1 onto a rater checkbox.
- **Set comparison for multiple choice** — the keyed set must equal the unambiguously-correct
  set, closing the gap `accuracy` leaves open (it checks the keyed answer, never whether a
  distractor is *also* defensible).
- **Deterministic catch-all detection** (Python, no LLM) forces a failing verdict, so the two
  catch-all seeds among the 8 seeded C2 items are caught identically by every judge model.
- **Empty keys** (`correct_answer: []`, e.g. `1819ER_q3`) are flagged `no_correct_option` and
  scored `0.0` rather than aborting the run.

**Open items:**
1. Quiz-level aggregate rates — "multiple-correct rate" and "catch-all-option rate" — to mirror
   the figures cited in the related work (Doughty 2024, Di Battista 2014). Not implemented; the
   per-item flags are in `MetricResult.raw_response`, so these are computable from stored results
   without re-running any judge.
2. **Threat to validity — source asymmetry.** The metric passes `source_text` to the judge when a
   quiz has one, but §4 of the validation plan gives human raters no fixed source passage
   ("experts verify by knowledge / lookup"), and only some quizzes carry a source. That is an
   information asymmetry inside an objective-criterion comparison. It is inert for the planned
   run (`pool-run.yaml` executes source-free), but it must be stated in
   `threats-to-validity.tex` when the results are written up.
3. The metric is registered in `config/multi_judge_benchmark.yaml`. Adding it to the actual
   data-collection run requires editing `build_pools.py` in the paper repository and
   regenerating `pool-run.yaml` — see the note at the end of this report.

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

**Status: ✅ Covered**, and as of this change **reported per item**.

`HomogeneousOptionsMetric` (`src/metrics/homogeneous_options.py`) classifies
each option's grammatical form, content type, completeness, and length, then
scores grammatical parallelism, content-type homogeneity, and format
consistency. Matches the definition closely.

**Per-item extraction.** Both LLM phases are fan-out phases — every question
gets its own prompt and its own scored response carrying `question_id`,
`question_score`, `severity`, `issues` and `rationale`. Those judgements
previously survived only as nested JSON inside a single quiz-level
`MetricResult`. The metric now hands them back through a
`BaseMetric.expand_question_results` hook and the runner emits one row per
question, joinable by `(quiz_id, question_id)`. **No additional LLM calls** —
the data already existed and was being discarded at the boundary.

- The per-item rows **replace** the quiz-level aggregate row. `ResultsAggregator.aggregate`
  pools every score sharing a `metric_name` into one mean, and inter-rater reliability keys items
  by `(run, quiz_id, question_id)`; emitting both kinds under one name would mix N item scores
  with one penalized aggregate and add a spurious `question_id=None` item. Replacing is also a
  strict IRR improvement — N items per quiz instead of 1.
- Nothing is lost: mean question score, major-violation rate, perfect-homogeneity rate and issue
  distribution are all recomputable from the per-item rows.
- True/false items remain explicitly not applicable — they still produce a row, with
  `applicable: false` and a score of `100.0`. **Filter on `applicable` before averaging.**

**Open items:**
1. **Scale.** The metric emits a continuous 0-100 score plus a three-level severity
   (`none` / `minor` / `major`). The human rating scale for this criterion is a four-point
   ordinal. The judge was deliberately not rebuilt — the task here was the extraction path, and
   rewriting a working judge to change its scale is a separate decision. Binning the continuous
   score into four bands post hoc was rejected: the cut-points would be invented rather than
   chosen by the judge, which is not the same measurement.
2. The paper's definition explicitly flags that the evidence is **mixed** (Applegate 2019 found no consistent psychometric effect). Consider documenting that this metric encodes a contested guideline, and/or down-weighting it relative to better-supported criteria so it does not dominate aggregate scores.

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

1. ~~**[P0] Add an Answer Key Correctness metric (Criterion 5).**~~ **Done** — `answer_key_correctness`, binary per Form A §3.2, with a deterministic "none/all of the above" detector. Directly addresses the AI-specific failure mode (multiple defensible answers) emphasized in the related work.
2. **[P0] Add an Absence-of-Cueing metric (Criterion 8).** Currently only an incidental distractor sub-check; add stem→key grammatical/length/word-repetition/convergence cue detection.
3. **[P1] Score against stated learning objectives (Criterion 1).** Add a `learning_objectives` input and an alignment sub-score; stop equating source-topic coverage with objective alignment, or document the proxy explicitly.
4. **[P1] Add negative-phrasing detection to `clarity` (Criterion 4).** Named in the definition but absent from the prompt.
5. **[P2] Reconcile cognitive-level handling (Criterion 2).** Unify the Bloom taxonomy between `coverage` (3-level) and `difficulty` (6-level); separate Bloom level from the easy/medium/hard band; score appropriateness against a target when available.
6. **[P2] Reflect contested/AI-specific evidence in weighting & docs.** Flag `homogeneous_options` as a contested guideline (Applegate 2019); strengthen `accuracy`'s explicit source-grounded hallucination check.
7. **[P3] Cosmetic robustness.** Guard `accuracy` against `source_text=None`; document T/F exclusions for `distractor_quality`/`homogeneous_options`; add per-item breakdowns for quiz-level grammar.

---

## Follow-up in the paper repository

`answer_key_correctness` is registered in this repository and in
`config/multi_judge_benchmark.yaml`, but the actual data-collection run config lives in
`paper-al-quiz-generation` and is **generated**, so it must be regenerated rather than
hand-edited:

- `tools/corpus/build_pools.py` — add `("answer_key_correctness", "1.0")` and
  `("objective_alignment", "1.0")` to `METRICS`.
- `data-format-spec.md` §10 (the ❌ lines for C2 and C3) and §11 (the resolved metric-subset bullet).
- `roadmap-to-datacollection.md` task 2.3 (C2 and C3 both land here), and the 5.4 check.
- Re-run `build_pools.py` to regenerate `tools/corpus/out/pool-run.yaml`.
- `paper-benchmark/sections/threats-to-validity.tex` — the source-asymmetry threat above.
- `tools/corpus/build_pools.py` — the 15-item pool cap rests on a stale assumption. Its comment
  says `homogeneous_options` "formats the whole pool into one prompt and must return one summary
  per question", so a large pool would truncate. Both of that metric's LLM phases are fan-out
  phases: one prompt and one response **per question**, so response length does not scale with
  pool size. The cap is harmless but over-constrained, and the stated rationale is wrong.
