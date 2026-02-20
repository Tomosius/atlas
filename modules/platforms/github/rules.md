# GitHub

## Project

- Repo: {{github.owner}}/{{github.repo}}
- Default branch: {{github.default_branch}}
- CLI: `gh` (GitHub CLI)

## Issues

```bash
gh issue list                          # list open issues
gh issue list --label "bug"            # filter by label
gh issue view <number>                 # show issue detail
gh issue create --title "..." --body "..."
gh issue close <number> --comment "..."
gh issue edit <number> --add-label "status:in-progress"
```

## Pull Requests

```bash
gh pr list                             # list open PRs
gh pr view <number>                    # show PR detail
gh pr create --title "..." --body "..."
gh pr merge <number> --squash          # merge with squash
gh pr checkout <number>                # check out a PR locally
gh pr review <number> --approve
```

## Workflow Conventions

- One PR per feature/fix — keep PRs small and focused
- Link PR to issue: `Closes #<number>` in PR body
- Require passing CI before merge
- Use draft PRs for work-in-progress: `gh pr create --draft`
- Squash merge to keep `main` history linear

## Labels

Use labels consistently:
- `type:feat`, `type:fix`, `type:test`, `type:docs`, `type:build`
- `priority:critical`, `priority:high`, `priority:medium`, `priority:low`
- `status:in-progress` — currently being worked on

## Milestones

```bash
gh api repos/{owner}/{repo}/milestones       # list milestones
gh issue list --milestone "v1.0"             # filter by milestone
```

Group related issues into milestones for release tracking.

## Project Boards

```bash
gh project list --owner <owner>
gh project item-list <number> --owner <owner> --format json
```

Use project boards to track issue status across sprints.

## Commands

- List issues: `{{commands.issues}}`
- List PRs: `{{commands.prs}}`
- Repo status: `{{commands.status}}`
- Sync: `{{commands.sync}}`
