# Recorded-output regression comparison

## Deterministic replay gate

The standard-library helper `scripts/evaluate.py` scores recorded outputs; it **does not execute agents**. Create an evaluation suite in a scratch directory (not this kit) and two run directories with one subdirectory per case ID:

```text
scratch/agent-loop/
  suite.json
  baseline/<case-id>/answer.md
  candidate/<case-id>/answer.md
  candidate/<case-id>/evidence.json
  source-data/finance.csv
```

Example `suite.json` (assertions may target any UTF-8 relative file within the corresponding case directory):

```json
{
  "version": 1,
  "cases": [{
    "id": "unvalidated-metric",
    "assertions": [
      {"type": "contains", "path": "answer.md", "value": "unvalidated"},
      {"type": "not_contains", "path": "answer.md", "value": "official NRR: 122%"},
      {"type": "json_equals", "path": "review.json", "pointer": "/validated", "value": false},
      {"type": "evidence_quotes", "path": "evidence.json"}
    ]
  }]
}
```

For `evidence_quotes`, the output file is a nonempty JSON array containing `{"claim":"...", "evidence":[{"file":"finance.csv", "quote":"exact source excerpt, at least 8 characters"}]}`. Each source file must be beneath `--sources`, and each quote must be an exact substring in that file. This blocks nonexistent citations and fabricated excerpts, **not** a real excerpt used to support the wrong conclusion; check entailment with a human/domain reviewer or a separate calibrated judge.

```bash
python3 skills/experiment/scripts/evaluate.py \
  --suite scratch/agent-loop/suite.json \
  --baseline scratch/agent-loop/baseline \
  --candidate scratch/agent-loop/candidate \
  --sources scratch/agent-loop/source-data \
  --output scratch/agent-loop/comparison.json
```

Exit code `0`: every candidate assertion passed. `1`: at least one candidate failure or regression. `2`: invalid suite. The report details improvements and regressions **per assertion**, so a new failure cannot be hidden by another improvement. Missing artifacts fail closed. An absent baseline case directory makes the comparison invalid; record an actual attempted run before scoring a missing output as a failure. Baseline and candidate must be separate run directories. A mechanical pass is not promotion approval. Never copy raw case outputs, feedback, traces, or reports into a public repository without explicit authorization.

