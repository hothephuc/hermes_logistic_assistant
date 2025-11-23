# Backend

This folder contains the backend for the logistic assistant.

**Pre-commit**: This repository uses `pre-commit` to run formatters and linters before commits.

- **Install (pip / venv)**:

```bash
python -m pip install --user pre-commit
cd `pwd`
cd backend
pre-commit install
pre-commit run --all-files
```

- **Install (Poetry)**:

```bash
cd backend
poetry add --dev pre-commit
poetry run pre-commit install
poetry run pre-commit run --all-files
```

If you want to update hooks to their latest versions, run:

```bash
pre-commit autoupdate
```

The repository includes `.pre-commit-config.yaml` in the `backend/` folder. Adjust the project-specific instructions as needed.
