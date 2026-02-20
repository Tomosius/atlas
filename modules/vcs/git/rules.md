# Git

## Configuration

- User: {{git.user_name}} <{{git.user_email}}>
- Default branch: {{git.default_branch}}

## Branching

- `main` (or `master`) — production-ready code only; never commit directly
- Feature branches: `feature/<short-description>`
- Fix branches: `fix/<short-description>`
- Keep branches short-lived — merge or rebase frequently
- Delete branches after merging

## Commits

- Atomic commits — one logical change per commit
- Write commit messages in imperative mood: "Add feature" not "Added feature"
- Subject line: 50 chars or less; blank line before body
- Body: explain *why*, not *what* (the diff shows what)
- Reference issues: `Closes #42`, `Relates to #17`

{{#if commit_rules}}See commit-rules module for project-specific conventions.{{/if}}

## Workflow

```
git status          # check working tree state
git diff            # review unstaged changes
git diff --staged   # review staged changes
git add -p          # stage changes interactively (preferred over git add .)
git commit          # commit with editor
git log --oneline   # review recent history
```

- Stage with `git add -p` (patch mode) to review every hunk before committing
- Never use `git add .` blindly — it includes unintended files
- Never force-push to `main`/`master`

## Undoing Things

| Situation | Command |
|-----------|---------|
| Unstage a file | `git restore --staged <file>` |
| Discard working tree change | `git restore <file>` |
| Amend last commit (not pushed) | `git commit --amend` |
| Undo last commit, keep changes | `git reset HEAD~1` |
| Revert a pushed commit | `git revert <sha>` (creates new commit) |

Never rewrite history on shared branches.

## .gitignore

- Ignore build output, dependencies, secrets, and editor files
- Never commit `.env` files or credentials
- Use `git check-ignore -v <file>` to debug ignore rules

## Common Commands

- Status: `{{commands.status}}`
- Diff: `{{commands.diff}}`
- Log: `{{commands.log}}`
- Commit: `{{commands.commit}}`
