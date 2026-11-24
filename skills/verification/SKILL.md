---
name: verification
description: Create or improve reproducible project-local verification of real user behavior and critical invariants, including formal verification when warranted. Use only when explicitly selected.
disable-model-invocation: true
---

# Verification

Make the important behavior cheaply repeatable to verify. Use existing test and control tools first. Scope and action authority come from the user and applicable AGENTS.md.

## Real behavior

1. Inspect the project to identify user entry points, runtime prerequisites, launch/ready conditions, test data, authentication, existing drivers and observable effects. Establish a working baseline or report the exact blocker. Prioritize the most consequential behavior or recurring verification gap.
2. Drive the actual interface (browser, CLI, API, library public API, or device) using stable handles and representative inputs. Prefer existing harnesses; write a small reusable driver only for a demonstrated gap. Check the action, expected result and consequential side effects, not just a screenshot, status code or successful build.
3. Isolate ports, accounts, data and process ownership. Use fixtures, sandbox or authorized dry runs for money, messages, production mutations and other external effects. Verify what a dry run actually isolates; do not send real orders or change production to prove a check. Clean up only resources created by the run; keep sanitized evidence outside public source.
4. Demonstrate that the check distinguishes a working case from a broken one without damaging the real system. Record the exact command, environment, input and observed result. Expand coverage according to risk, not an arbitrary feature count.
5. If the path will be reused, leave a project-local command and, only if needed, a small project-local skill documenting setup/readiness, invocation, expected behavior, evidence and cleanup. Use the target harness's supported skill location. Maintain existing verification rather than adding parallel infrastructure; document what code or contract it covers and when it must be rechecked.

## Critical invariants

When ordinary cases cannot adequately cover interleavings, retries, state transitions, recovery or input domains, read `references/invariants.md`. Choose the least expensive method that can expose the relevant failure. Do not treat a model or bounded proof as verification of the whole implementation.

Report what ran and what was actually established, including missing runtime access, assumptions, bounds and residual risks. Implementation and review follow software-engineering when warranted.
