# Git Branching & Contribution Governance Rules

This repository strictly enforces the following git workflow and contribution rules:

## 1. Zero Direct Commits to `main`
- Direct commits to `main` are strictly forbidden.
- All development, fixes, refactorings, and documentation updates must occur on semantic branches:
  - `feat/...` for new features and enhancements
  - `fix/...` for bug fixes and patches
  - `chore/...` for build, CI, dependency updates, and maintenance
  - `docs/...` for standalone documentation updates

## 2. Mandatory Identity Rule
- Every commit author and committer identity must strictly match:
  - **Name**: `Janusz Hatala`
  - **Email**: `janusz.hatala@gmail.com`
- Under no circumstances may corporate or other personal accounts (e.g. `januszhatala-tb` / `janusz.hatala@timebook.net`) appear in commit history, PRs, or repository configurations.
- Verify prior to committing:
  ```bash
  git config user.name "Janusz Hatala"
  git config user.email "janusz.hatala@gmail.com"
  ```

## 3. Local Testing Prior to Push
- All tests and compilation checks must pass locally before pushing to remote:
  ```bash
  pytest -v
  python -m compileall app.py db.py parser.py llm_manager.py web_search.py tests/
  ```

## 4. Pull Request Protocol
- Push semantic branch to remote:
  ```bash
  git push -u origin <branch-name>
  ```
- Open a Pull Request targeting `main`:
  ```bash
  gh pr create --fill
  ```
- Wait for all CI checks (GitHub Actions `CI / Test and Build Verification`) to pass.
- Merge into `main` using squash or rebase merge via GitHub CLI or PR UI:
  ```bash
  gh pr merge --merge --delete-branch
  ```
- Switch back to `main` and pull updates:
  ```bash
  git checkout main
  git pull origin main
  ```
