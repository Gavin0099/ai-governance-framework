# Commands

## Proposal-time summary

```bash
python governance_tools/change_proposal_builder.py --project-root . --task-text "Describe the requested change here" --rules common --format human
```

## Proposal-time summary with impact preview

```bash
python governance_tools/change_proposal_builder.py --project-root . --task-text "Refactor runtime boundary" --rules common,refactor --impact-before runtime_hooks/core/post_task_check.py --impact-after runtime_hooks/core/post_task_check.py --format human
```

## Direct architecture impact preview

```bash
python governance_tools/architecture_impact_estimator.py --before runtime_hooks/core/post_task_check.py --after runtime_hooks/core/post_task_check.py --scope refactor --rules common,refactor --format human
```

## Supporting repository context

```bash
python runtime_hooks/core/session_start.py --project-root . --plan PLAN.md --rules common --task-text "Describe the requested change here"
```