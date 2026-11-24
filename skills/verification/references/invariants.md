# Critical invariant verification

- State the user harm and invariant in observable terms (for example, retrying a request never creates a second accepted transaction with the same idempotency key). Identify allowed failures and recovery behavior.
- Inspect actual code, storage guarantees and concurrency boundaries. Prefer property-based or generated tests against real code when they cover the relevant domain; consider a state-machine model checker (such as TLA+), SMT solver or proof tool when the property needs stronger exploration. Do not introduce a new dependency or cost without authority.
- Define the model-to-code mapping, initial states, atomic operations, external assumptions, failure/retry behavior and bounds. Check that the modeled guarantees really exist in the implementation. Where practical, replay counterexamples against an isolated real implementation.
- Show that a deliberately broken variant violates the property; keep the original check intact. Do not weaken a property, change assumptions silently or edit product code just to obtain a pass.
- Record reproducible commands, tool versions, checked properties, bounds and counterexamples. Record the covered code and revision; revisit the mapping whenever relevant behavior changes. Preserve a repeatable check if its maintenance cost is justified.
- A bounded pass is evidence within its assumptions only. Explicitly separate the model, the implementation mapping and runtime tests. Report what could not be verified.
