# Repo-Local Handoff Agent Package Template

Use this when creating the project-specific handoff agent inside a repository.

## Recommended File Layout

```text
agents/<project>-handoff/
  SKILL.md
  references/
    first-session.md
    handoff-completion.md
    maintainer-roadmap.md
    project-source-map.md
  agents/
    openai.yaml        # optional UI metadata when the environment supports it
docs/
  handoff_agent.md     # human-facing routing page, if the repo has docs/
README.md             # link to the handoff route, if public docs should expose it
```

Adjust the layout to repo conventions. If the repo has no `agents/` folder, use the nearest local convention, but keep the package easy to copy into Codex skills.

## SKILL.md Contents

The repo-local `SKILL.md` should include:

1. Frontmatter with a specific `name` and trigger-rich `description`.
2. Role: the agent is the handoff guide, not a passive Q&A bot.
3. First-session behavior and hard boundaries.
4. Safe execution rules for the repo.
5. Artifact walkthrough rules.
6. Code walkthrough depth.
7. Source map and settings map.
8. Data primer and trust rules.
9. Evaluation and verification commands.
10. Forward-test expectations.

Keep detailed examples and long roadmaps in `references/`.

## first-session.md

This reference should contain a script-like first response that a user can test. It should include project purpose, first route, exact first command or inspection action, working directory, output directory or first artifact, short term decode, direct-run vs agent-run choice when commands are involved, and an explicit stop point before run status is known.

Also include first-response anti-patterns:

- "What do you want to know?"
- Long glossary first.
- Policy dump first.
- Test matrix first.
- File list without action.
- Direct-run-only wording when agent-run is possible.

## handoff-completion.md

This reference should define the loop:

1. Teach one concept.
2. Inspect one concrete source.
3. Summarize in more than one sentence when needed.
4. Check understanding.
5. Repair confusion with a smaller example.
6. Continue to the next planned source after confirmation.

It should define completion criteria and require a detailed final recap.

## maintainer-roadmap.md

This reference should be project-specific. Include domain stages, data stages, first run/artifact stages, code stages with real paths and functions, settings stages, evaluation stages, execution variants, optimization/future-work stages, and safe first tasks.

For each stage, write:

- Goal.
- What to teach proactively.
- What file/artifact/command to inspect.
- Stage summary example.
- Understanding check.
- Progress criteria.

## project-source-map.md

This reference should route common questions:

- "Where is the CLI?"
- "Where is the first UI?"
- "Where are settings?"
- "Where is parsing?"
- "Where is validation?"
- "Where are generated artifacts?"
- "Which test should I run?"
- "Which file owns this domain rule?"

Use real paths and function names.

## Human Docs Link

If the repo has a docs system, add a short page explaining what the handoff agent is for, where the package lives, how to invoke it, what the handoff covers, and what it does not replace.

Do not duplicate the entire skill in docs; point to the source package.
