# Naming, Docs, And Contract Consistency

Use this reference when a change shifts responsibility, public behavior, configuration, generated artifacts, tests, or operational meaning.

The goal is not to rename everything. The goal is to avoid a finished change where the code works but the names, docs, tests, settings, logs, or generated contracts still describe the old world.

## Principle

Names are maintenance interfaces. A maintainer uses a function name, file name, module name, type name, test name, setting key, log message, metric, command, document title, or generated-contract label to predict what the system currently does.

When the name and behavior disagree, either align them or record why compatibility, migration cost, or external contract requires the mismatch to remain.

## Required Checkpoints

Run this consistency pass when:

1. a function or module gains or loses responsibility
2. a file starts representing multiple responsibilities
3. data shape, domain type, or accepted input expands beyond the original name
4. exception handling, validation, caching, fallback, transformation, or external calls are added
5. public behavior, CLI options, config keys, generated contracts, examples, or docs change
6. a review finding points out a name or docs mismatch
7. a test name no longer describes what the test proves

## Consistency Surface

Check the directly connected surface before finishing:

1. function, method, class, type, module, package, and file names
2. tests, fixtures, helper names, snapshots, and test data labels
3. docs, README sections, examples, command snippets, and generated-contract descriptions
4. config keys, environment variable names, CLI flags, API fields, and schema names
5. log messages, metric names, alert names, dashboard labels, and report titles
6. import paths, wrappers, compatibility aliases, deprecation notices, and migration notes

Do not broaden into unrelated cleanup. Follow references only far enough to keep the changed contract understandable and safe.

## Decision Rules

Prefer renaming or moving when:

1. the new name better predicts current behavior
2. callers are internal or mechanically updateable
3. the old name would mislead future maintenance
4. docs and tests can be updated in the same coherent task unit

Prefer a compatibility wrapper, alias, deprecation note, or explicit documentation when:

1. the name is public API
2. persisted records, old payloads, or external clients still depend on it
3. a rename would require migration or release coordination outside the current task
4. the user requested a narrower change and the mismatch is not a current safety risk

If the mismatch remains, record the reason near the durable interface: wrapper comment, docs note, test name, deprecation notice, migration plan, or final report.

## Review And Finish Questions

Before final response or commit, ask:

1. Would a maintainer infer the current responsibility from the visible names?
2. Do docs and examples describe the behavior that now ships?
3. Do tests prove the public contract rather than incidental implementation shape?
4. Do logs, metrics, and settings still mean what their names claim?
5. Did a generated artifact, schema, or contract need regeneration or a note explaining why not?
6. Are any remaining mismatches intentional, documented, and bounded?
