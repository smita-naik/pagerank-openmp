# Experimental evidence

Run directories contain `metadata.json`, `commands.jsonl` and `raw.jsonl`. Summaries and plots are derived from these measured records. Keep local exploratory data separate from ARC experiments. All run subdirectories are ignored by Git; explicitly archive the final selected evidence with the submission.

Use a new output path for every experiment. A `finished_utc` field in metadata identifies a completed run. Do not overwrite or edit raw measurements. Record any exclusions, incomplete blocks or reruns in the report. There are no precomputed or fabricated performance results in the source code.
