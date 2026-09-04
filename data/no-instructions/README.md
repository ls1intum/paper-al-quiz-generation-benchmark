Deliberately empty.

A benchmark run whose quizzes come from more than one provenance points its
`instructions_directory` here. A generated quiz can ship the intent file it was
produced from and a human-authored quiz cannot, so loading intent for only some
quizzes hands the judge the generation brief -- which typically states the
quality requirements outright -- for one provenance only, and
`BaseMetric.evaluate` additionally interprets its `custom_prompt` and adjusts
the score by it. Any comparison across provenance would then be measuring that
asymmetry rather than the quizzes.

Supply intent for every quiz in a run or for none. This directory is the "for
none" half, kept as a real path so the choice is a visible line in the config
rather than a missing directory nobody notices.

See `config/form_b_quiz_level.yaml`.
