# Hermes Logistics Assistant Backend

## Description
This is the backend for the Hermes Logistics Assistant, built with FastAPI. It provides API endpoints for logistics operations and integrates with Gemini for AI capabilities.

## Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment (optional but recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    # OR if using uv (recommended)
    uv sync
    ```
    *Note: If `requirements.txt` is not present, ensure you have the necessary packages installed as specified in `pyproject.toml`.*

## Running the Application

You can run the application using `uvicorn`:

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.
Interactive documentation is available at `http://localhost:8000/docs`.

## Debugging with VS Code

A launch configuration is provided in `.vscode/launch.json`.
1.  Open the "Run and Debug" view in VS Code.
2.  Select "Python: FastAPI".
3.  Press F5 to start debugging.
