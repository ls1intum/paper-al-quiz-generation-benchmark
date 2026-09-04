# Quality Criteria Coverage Report

This report assesses how well the benchmark's metrics cover the quality criteria
extracted from the literature in the paper
(`paper-al-quiz-generation/paper/sections/relatedwork.tex`, Table
`tab:quality-criteria`): **nine item-level criteria (C1-C9)** applied to individual
items and **three quiz-level criteria (Q1-Q3)** applied to intact quizzes. For each
criterion it states the coverage status, documents divergences from the definition,
and lists actionable improvements.

## Summary

The benchmark registers **14 metrics** (`src/metrics/__init__.py`):
`coverage`, `difficulty`, `accuracy`, `clarity`, `distractor_quality`,
`homogeneous_options`, `grammatical_correctness`, `answer_key_correctness`,
`objective_alignment`, `absence_of_cueing`, `cognitive_level`, `objective_balance`,
`difficulty_spread`, `cross_item_redundancy`.

`coverage` and `difficulty` map to no criterion: `coverage` measures how well a quiz
covers its *source material* (a content-coverage construct, not an objective one),
and `difficulty` was superseded by `cognitive_level`. Both remain available and are
not part of the instrument.

| # | Criterion (paper) | Metric | Status |
|---|---|---|---|
| 1 | Alignment with Learning Objectives | `objective_alignment` | ✅ Covered |
| 2 | Cognitive Level Appropriateness | `cognitive_level` | ✅ Covered — assigns a Bloom level blind, then compares it with the catalogue's intended level |
| 3 | Factual Accuracy | `accuracy` | ✅ Covered |
| 4 | Clarity and Precision | `clarity` | ⚠️ Partial — negative phrasing not checked |
| 5 | Answer Key Correctness | `answer_key_correctness` | ✅ Covered |
| 6 | Distractor Quality | `distractor_quality` | ✅ Covered |
| 7 | Homogeneous Options | `homogeneous_options` | ✅ Covered — now reported per item |
| 8 | Absence of Cueing | `absence_of_cueing` | ✅ Covered |
| 9 | Grammatical Correctness | `grammatical_correctness` | ✅ Covered — now reported per item |

Quiz-level criteria, each producing one result per quiz with `question_id` empty:

| # | Criterion (paper) | Metric | Status |
|---|---|---|---|
| Q1 | Learning-Objective Balance | `objective_balance` | ✅ Covered |
| Q2 | Difficulty Spread | `difficulty_spread` | ✅ Covered |
| Q3 | Redundancy and Cross-Item Cueing | `cross_item_redundancy` | ✅ Covered |

**Headline gaps:** Criterion 4 omits the explicit negative-phrasing check named
in its definition. Every other criterion, item-level and quiz-level, now has a
dedicated metric.

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

**Status: ✅ Covered** — by `cognitive_level`, which post-dates the assessment
below. It assigns a Bloom level blind to the intended one (an anti-anchoring
control), then compares the two as `below` / `matches` / `above`, so it scores
appropriateness against a target rather than absolute level. The reference value
is `question.metadata.bloom_intended`, and an item without one is reported
`applicable: false`. The rest of this section documents the earlier `difficulty`
proxy, which the instrument no longer uses.

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

**Status: ✅ Covered** by `absence_of_cueing` (`src/metrics/absence_of_cueing.py`),
question-level, one result per item with `question_id` populated.

- **Binary detection.** `100.0` when no cue is present, `0.0` when one is. Cueing is a detection
  construct rather than a matter of degree, and the primary analysis unit is present/absent.
  `severity` (`none` / `minor` / `strong`) is retained as a descriptive field so a three-level
  analysis remains possible later, without re-running any judge and without baking that decision
  into the score now.
- **Five cue types**, matching the human rating vocabulary exactly: `grammatical`, `semantic`,
  `length`, `convergence`, `other`. A judge label outside this set is dropped. The six seeded
  cueing items (2 grammatical · 2 length · 2 convergence) are all covered by named types, so
  per-type recall is computable.
- **All three cue directions** are checked explicitly: stem→key, key→distractors, and across the
  option set. This closes the gap noted previously — the incidental signal in
  `distractor_quality` (`distractor.py:182`) looks only at distractor→key hints, never at
  stem→key, which is the more common failure.
- **Deterministic length measurement** feeds the prompt: the key is flagged as an outlier only
  when it is both ≥1.5× the median distractor length and ≥20 characters longer. It is
  **advisory** — a key can be legitimately longer without cueing, so the judge weighs it rather
  than deferring to it. True/false items are skipped, and an item with no marked answer is
  handled without error.
- **Coherence is enforced after the judge**: a cue reported with severity `none` is raised to
  `minor`, and a no-cue verdict carries no cue types.

**Boundary with Criterion 7.** Non-parallel options are not automatically cueing: a homogeneity
break that does not point at the key belongs to `homogeneous_options`, while this metric reports
a cue only when something singles the key out. Grammatical cues necessarily break homogeneity
too and are reported by both — a known and expected overlap, not double-counting.

**Actionable improvements:**
1. ~~Add a dedicated `cueing` (or `absence_of_cueing`) metric…~~ **Done.**
2. ~~Length cueing can be partly deterministic…~~ **Done** — deterministic measurement feeding the prompt, advisory rather than decisive.
3. Surface a per-quiz cueing-violation rate. *(Still open — computable from the per-item rows, since each carries `cue_present`, `severity` and `cue_types`.)*

---

## Criterion 9 — Grammatical Correctness

**Definition:** *Question stems and answer options are free of grammatical, spelling, and punctuation errors.*

**Status: ✅ Covered**, and as of this change **reported per item**.

`GrammaticalCorrectnessMetric` (`src/metrics/grammatic.py`) is now
`MetricScope.QUESTION_LEVEL`: one result per question, `question_id` populated,
joinable by `(quiz_id, question_id)`.

**Why the conversion was needed.** The metric previously formatted every question into a single
prompt and returned one score for the whole quiz, so a single broken item among fifteen clean
ones was invisible in the average. Unlike Criterion 7, there was nothing to extract — the
per-question judgement was never made, so the prompt and schema had to be rewritten rather than
merely re-plumbed.

- **Four-level scale.** The judge picks `none` / `minor` / `major` / `critical` and the score is
  derived from it (`100 / 66.7 / 33.3 / 0`), so a verdict and its number cannot disagree. The
  stem and every option are judged together — one broken option makes the item worse however
  clean the rest reads.
- **Structured issue lists** (`grammar_issues`, `spelling_issues`, `punctuation_issues`) replace
  the bare numeric score the metric used to return, so a low score can be traced to specific
  problems.
- **`error_weights` was removed.** It existed to guide a continuous deduction; the four severity
  levels replace it. No config in this repo sets it, and `validate_params` now rejects it loudly
  rather than ignoring it silently.

**Language compliance moved out of the item score.** The `language` instruction is no longer
coupled to the metric via `_has_adjustable_instructions`. Leaving it coupled after the scope flip
would have fired one compliance LLM call *per question* to answer a question about the whole
quiz, and could have reached different language verdicts for items in the same quiz. It is now
checked once per quiz in `BenchmarkRunner._check_language_compliance`, beside the existing
`_check_difficulty_compliance`, which already solves the identical problem for the question-level
`difficulty` metric.

Following that precedent, **the per-question rows are never modified**: the compliance-adjusted
quiz mean is recorded in `BenchmarkResult.metadata["adjusted_grammar"]`, alongside
`adjusted_difficulty`. This is the stronger reading of the requirement that language mismatch
stay "an instruction compliance adjustment, not grammar quality itself" — folding it into every
item score would be exactly the contamination that rule guards against. Per-item scores therefore
hold pure grammar quality, which is also what a human rater judges. Cost is unchanged: the
adjustment fires once per (quiz, metric, evaluator), as before.

---

## Criterion Q1 — Learning-Objective Balance

**Definition:** *Given the objectives declared for the quiz, are they weighted sensibly across the item set — or does the quiz over-invest in one and barely touch another?*

**Status: ✅ Covered** by `objective_balance` (`src/metrics/objective_balance.py`), quiz-level, one result per quiz.

The judge receives `quiz.metadata.learning_objectives` and every item, attributes items to
objectives, and only then picks one of four evenly spaced levels. The reference set is what the
quiz declares for itself — not the per-item `learning_objective` that `objective_alignment` uses.

**Deliberate exclusions**, each stated in the prompt because a judge left to itself will
otherwise fold them in:
- **Coverage is not judged.** A declared objective with no item is not penalized here. Balance of
  emphasis and coverage are different constructs with different reference values.
- **The objectives themselves are not judged.** A badly scoped objective whose items are evenly
  spread scores at the top.
- **Whether an item assesses its objective well is not judged.** That is Criterion 1, per item.

**Divergences:**
- Item count is the evidence, so a longer or harder item counts once. A quiz that spends one
  demanding item on one objective and three trivial ones on another reads as unbalanced by count
  even where the effort is even.
- Objectives are weighed as equally important unless the quiz says otherwise; the format carries
  no per-objective weight.

**Not applicable:** a quiz declaring no objectives — `applicable: false`, score `100.0`, the
judge's answer discarded.

---

## Criterion Q2 — Difficulty Spread

**Definition:** *Does the quiz mix difficulty sensibly, rather than being uniformly trivial or uniformly hard?*

**Status: ✅ Covered** by `difficulty_spread` (`src/metrics/difficulty_spread.py`), quiz-level, one result per quiz.

The verdict is holistic and reached in one call over the whole quiz, which is the unit and the
judgement a human rater applies to the same material. The judge first names the least and most
demanding item, then picks a level from that range.

**Deliberate exclusions:**
- **Order is not judged.** A demanding item placed first is badly arranged, not badly spread.
- **This is not Criterion 2.** Cognitive level is assessed per item against a catalogue reference
  value; difficulty here is the effort an item demands of a prepared learner. Two items at one
  Bloom level can differ sharply in difficulty, and a quiz spread across Bloom levels can still
  be uniformly easy. The prompt says so outright.

**Divergences:**
- Difficulty is judged from the item text alone. No response data exists, so this is the judge's
  estimate of demand, not an empirical *p*-value — the same information a human rater has.
- Deriving the level from per-item difficulty labels would be more reproducible and would measure
  a different construct: a computed statistic over a scale with no reference value. Rejected for
  that reason, not for cost.

**Not applicable:** fewer than three items — `applicable: false`, score `100.0`. A pair has no
spread. The same floor governs which quizzes human raters are shown, so both arms abstain on the
same units.

---

## Criterion Q3 — Redundancy and Cross-Item Cueing

**Definition:** *Do items duplicate each other, or does one item reveal another's answer? If either, which item pairs?*

**Status: ✅ Covered** by `cross_item_redundancy` (`src/metrics/cross_item_redundancy.py`), quiz-level, one result per quiz.

Both halves of the criterion are cross-item relations, invisible to any per-item metric.
Distinct from Criterion 8 (`absence_of_cueing`), which asks whether an item's **own** options
give its key away.

The judge names the pairs first, with a kind (`redundancy` or `cueing`) and an explanation each,
and only then picks a level — the prompt requires at least one pair at the lower two levels, as
the rater instrument does. Naming the pair is what makes a depth-of-agreement comparison
possible: agreeing that a quiz is redundant is weaker evidence than agreeing which pair makes it so.

**Divergences:**
- A pair naming an item the quiz does not hold, or naming one item twice, is dropped, and the
  count is reported as `pairs_dropped` rather than absorbed. A judge that reaches `substantial`
  and then cannot name a real pair is a finding, not noise to smooth over.
- The verdict stays authoritative for the score even when every pair is dropped. Recomputing the
  level from the surviving pairs would silently rewrite the judge's answer.

**Not applicable:** fewer than three items — `applicable: false`, score `100.0`.

---

## Prioritized Action List

Ordered by impact on faithfulness to the literature-derived criteria.

1. ~~**[P0] Add an Answer Key Correctness metric (Criterion 5).**~~ **Done** — `answer_key_correctness`, binary per Form A §3.2, with a deterministic "none/all of the above" detector. Directly addresses the AI-specific failure mode (multiple defensible answers) emphasized in the related work.
2. ~~**[P0] Add an Absence-of-Cueing metric (Criterion 8).**~~ **Done** — `absence_of_cueing`, binary detection over five cue types, checking stem→key, key→distractors and option-set convergence, with a deterministic length signal feeding the prompt.
3. ~~**[P1] Score against stated learning objectives (Criterion 1).**~~ **Done** — `objective_alignment` judges each item against its own stated objective, and `objective_balance` (Q1) judges how the quiz weights the objectives it declares. Neither uses source-topic coverage as a proxy.
4. **[P1] Add negative-phrasing detection to `clarity` (Criterion 4).** Named in the definition but absent from the prompt.
5. **[P2] Reconcile cognitive-level handling (Criterion 2).** ~~Score appropriateness against a target when available~~ **done** — `cognitive_level` compares the assigned level against `bloom_intended`, and `difficulty_spread` (Q2) keeps difficulty separate from Bloom level at the quiz level. Still open: `coverage` uses its own 3-level depth scale (`coverage.py:168-172`) where every other metric uses 6-level Bloom.
6. **[P2] Add the three quiz-level criteria (Q1-Q3).** ~~The judge implemented nine of the instrument's twelve criteria: nothing scored objective balance, difficulty spread or cross-item redundancy, so no quiz-level criterion could be compared against a human rating.~~ **Done** — `objective_balance`, `difficulty_spread`, `cross_item_redundancy`, with `config/form_b_quiz_level.yaml` as a runnable example.
7. **[P2] Reflect contested/AI-specific evidence in weighting & docs.** Flag `homogeneous_options` as a contested guideline (Applegate 2019); strengthen `accuracy`'s explicit source-grounded hallucination check.
8. **[P3] Cosmetic robustness.** Guard `accuracy` against `source_text=None`; document T/F exclusions for `distractor_quality`/`homogeneous_options`; add per-item breakdowns for quiz-level grammar.

---

## Follow-up in the paper repository

The actual data-collection run config lives in `paper-al-quiz-generation` and is **generated**,
so it must be regenerated rather than hand-edited.

For the quiz-level criteria specifically:

- `tools/corpus/build_pools.py` — the pool configs must **not** gain `objective_balance`,
  `difficulty_spread` or `cross_item_redundancy`: pool files are containers for standalone
  items, and all three criteria are meaningless on them. Q1-Q3 need their own config over the
  intact Form B quizzes, modelled on `config/form_b_quiz_level.yaml`.
- **Build the Form B judge inputs with `instructions` stripped.** Only the generated quizzes
  carry an intent file; the human-authored ones cannot. Supplying it for one provenance only
  hands the judge the generation brief — which states the quality requirements outright — and
  `BaseMetric.evaluate` would additionally interpret its `custom_prompt` and adjust the score by
  it. Any provenance comparison would then measure that asymmetry. Pointing the config's
  `instructions_directory` at `data/no-instructions` has the same effect; note that a quiz
  declaring no intent file at all is dropped by `IOUtils.load_instructions` before the directory
  is consulted, so the config line is the record of this decision, not the log.
- `analysis-benchmark/harmonise.py` — `METRIC_TO_CRITERION` needs the three new entries, and the
  join needs a quiz-level path: these rows carry `question_id: null`.

For the item-level metrics:

- `tools/corpus/build_pools.py` — add `("answer_key_correctness", "1.0")`,
  `("objective_alignment", "1.0")` and `("absence_of_cueing", "1.0")` to `METRICS`, and bump
  `grammatical_correctness` to `"2.0"`. That metric was excluded from the pool subset because it
  was "quiz-level, one score per whole quiz with no per-question breakdown" — that reason no
  longer holds, so it can now be added.
- `data-format-spec.md` §10 (the ❌ lines for C2, C3 and C8) and §11 (the resolved metric-subset bullet).
- `roadmap-to-datacollection.md` task 2.3 (C2, C3 and C8 all land here), and the 5.4 check
  "Confirm C2/C8 metrics landed" — both now have metrics, so RQ2 reaches all 30 seeds.
- Re-run `build_pools.py` to regenerate `tools/corpus/out/pool-run.yaml`.
- `paper-benchmark/sections/threats-to-validity.tex` — the source-asymmetry threat above.
- `tools/corpus/build_pools.py` — the 15-item pool cap rests on a stale assumption. Its comment
  says `homogeneous_options` "formats the whole pool into one prompt and must return one summary
  per question", so a large pool would truncate. Both of that metric's LLM phases are fan-out
  phases: one prompt and one response **per question**, so response length does not scale with
  pool size. The cap is harmless but over-constrained, and the stated rationale is wrong.
