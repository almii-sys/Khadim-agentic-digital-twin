# Contributing / Git Workflow

## Branches
```
main          -> always working, demo-ready. Protected — no direct pushes.
dev           -> integration branch. Feature branches merge here first.
feature/*     -> one branch per task/module, e.g. feature/thesis-module
```

Flow: `feature/*` → PR into `dev` → (after review) `dev` → `main` before
milestones/demos only.

## Starting new work
```bash
git checkout dev
git pull origin dev
git checkout -b feature/your-task-name
```

## Commit messages
Use a short prefix so history is scannable:
```
feat: add thesis milestone tracking model
fix: correct GPA calculation rounding
docs: update module ownership table
refactor: split enrollment logic out of student model
```
Small, frequent commits beat one giant commit. Avoid `update`, `fix stuff`, `wip`.

## Before you push
```bash
git pull origin dev --rebase   # always rebase onto latest dev before pushing
git push origin feature/your-task-name
```
Then open a PR into `dev` on GitHub. At least one teammate reviews before merge
— this is also your evidence of who did what for evaluation purposes.

## Avoiding merge conflicts
- Don't edit files outside your assigned module unless you've told the owner
- If you must touch a shared file (e.g. `mock_data/models.py`), open an issue
  or message the team first — schema changes there break everyone downstream
- Resolve conflicts locally; never force-push to `dev` or `main`

## Useful commands
```bash
git status                        # see what's changed before you commit
git add -p                        # stage changes selectively, review each hunk
git stash                         # shelve half-done work to switch tasks
git log --oneline --graph --all   # see the whole team's branch history at once
git rebase -i HEAD~3              # clean up your last few commits before a PR
git diff dev                      # see everything you'll be merging in
```

## .gitignore reminders
Never commit: `venv/`, `__pycache__/`, `*.db` (mock DBs are regenerated via
seed scripts, not committed), `.env`, `node_modules/`, IDE folders.
