# Measurement validity

Before acting on a measured difference:

- Trace what is timed, counted and excluded. Check correctness, completion and errors; make sure caches, lazy execution, failed requests or skipped work did not produce a false gain.
- Compare representative data, release settings, versions, concurrency, warm/cold state and realistic tuning. Where different settings are the actual choice, make that difference explicit. Identify the bottleneck with independent profiling when useful; do not report instrumented latency as normal latency without qualification.
- Check physical and architectural limits, and whether the measured component is large enough to matter end to end.
- Repeat and alternate or randomize comparison order as practical; report dispersion and uncertainty, not only the best run. Choose sample size according to noise and consequence. A quick single-run estimate is not a reliable basis for a consequential choice.
- Freeze the comparison protocol while testing candidates. Changes to the harness or workload require rerunning the affected baseline and labeling the new comparison. Keep independent validation cases out of optimization.
- Compare the whole outcome (quality, correctness, latency, resources, and domain-specific risk as applicable). Report inconclusive differences as such.
