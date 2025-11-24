# Hermes Logistics Assistant

An AI-powered logistics assistant using LangGraph multi-agent system to analyze shipment data, provide insights, and predict delays.

## Features

- **Natural Language Query Interface**: Ask questions in plain English about your shipment data
- **Multi-Agent System**: Built with LangGraph, featuring:
  - **Master Agent**: Routes queries and coordinates sub-agents
  - **Analytics Agent**: Performs data analysis, aggregations, and filtering
  - **Prediction Agent**: Uses linear regression to forecast future delays
- **Interactive Visualizations**: Charts and tables powered by Chart.js
- **Real-time Communication**: WebSocket-based chat interface

## Architecture

```
┌─────────────────────────────────────┐
│         Master Agent                │
│  (Intent Classification & Routing)  │
└──────────┬──────────────────────────┘
           │
           ├─────────────┬──────────────────┐
           │             │                  │
    ┌──────▼──────┐ ┌───▼───────────┐ ┌────▼─────────┐
    │  Analytics  │ │  Prediction   │ │   Response   │
    │    Agent    │ │     Agent     │ │  Formatter   │
    └─────────────┘ └───────────────┘ └──────────────┘
```

## Setup

### Backend

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install dependencies (using uv):
```bash
uv sync
```

3. Run the FastAPI server:
```bash
uv run uvicorn main:app --reload --port 8000
```

### Frontend

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start the React development server:
```bash
npm start
```

The app will open at `http://localhost:3000`

## Example Queries

The system can handle various types of queries:

### 1. Route Performance
- "Which route had the most delays last week?"
- "Show me delays by route"
- "Compare route performance"

### 2. Warehouse Analysis
- "List warehouses with average delivery time above 5 days"
- "Which warehouse performs best?"
- "Show warehouse statistics"

### 3. Delay Reason Analysis
- "Show total delayed shipments by delay reason"
- "What are the main causes of delays?"
- "Break down delays by reason"

### 4. Time-based Statistics
- "What was the average delay in October?"
- "Show delay trends over time"
- "Average delay last month"

### 5. Predictions (Bonus Feature)
### 6. Conversational / Text-Only
- "Explain why delays increased last month (just text)"
- "Tell me about warehouse performance without a chart"
- "Why are Route A delays higher?"

If you explicitly ask for "no chart", "text only", or similar, the system returns a narrative summary with no visualization.

- "Predict the delay rate for next 14 days on Route B"
- "Forecast the next month of delays for WH2"
- "Roughly how long are delays if Weather issues hit Route C?"
- "Predict the delay rate for next week"
- "Forecast next week's delays"
- "What will delays look like next week?"

## Data Structure

The system processes shipment data from `backend/data/shipments.csv`:

```csv
id,route,warehouse,delivery_time,delay_minutes,delay_reason,date
1,Route A,WH1,5.2,30,Weather,2024-10-10
2,Route B,WH2,4.8,0,None,2024-10-11
...
```

### Fields:
- **id**: Unique shipment identifier
- **route**: Delivery route (Route A, Route B, Route C)
- **warehouse**: Warehouse location (WH1, WH2, WH3)
- **delivery_time**: Actual delivery time in days
- **delay_minutes**: Minutes of delay (0 = on time)
- **delay_reason**: Reason for delay (Weather, Traffic, Mechanical, Accident, None)
- **date**: Shipment date

## Response Format

Responses include:
- **Text Summary**: Human-readable analysis
- **Charts**: Visual representations (Bar, Line, Pie charts)
- **Tables**: Detailed data breakdowns

### Example Response Structure:
```json
{
  "query": "Which route had the most delays?",
  "intent": "route",
  "result": {
    "summary": "Route A experienced the most delays...",
    "chart": {
      "type": "bar",
      "title": "Delayed Shipments per Route",
      "data": [...]
    },
    "table": {
      "columns": [...],
      "rows": [...]
    }
  }
}
```

### Intent System
Hermes classifies each query into one of several intents which drive routing and response formatting:

| Intent | Purpose | Visualization |
|--------|---------|--------------|
| greeting | Salutations / welcome | None |
| gratitude | User thanks / appreciation | None |
| clarify | Ambiguous short query requiring clarification | None |
| prediction | Forecast future delays | Chart + Table |
| warehouse | Warehouse performance comparison | Chart + Table |
| route | Route delay performance | Chart + Table |
| delay_reason | Breakdown of delay reasons | Chart + Table |
| delay | Delay time statistics/trends | Chart + Table |
| analytics | General overview summary | Chart (line) |
| conversation | Explanatory qualitative insight (e.g. "why", "explain") | Suppressed |
| text_only | Explicit user request for no visualization | Suppressed |

Classifier rules:
- Picks the most specific analytic intent when keywords match.
- "conversation" chosen for explanatory, interpretive, narrative requests without explicit viz demand.
- "text_only" chosen when user explicitly requests no charts/visuals.
- Logs selected intent to the `hermes.intent` logger.

To extend: add new intent token, update the prompt in `backend/app/ai/master_agent/tools.py`, and handling logic in `agent.py`.

## Technology Stack

### Backend
- **FastAPI**: Web framework
- **LangGraph**: Multi-agent orchestration
- **Pandas**: Data processing
- **NumPy**: Numerical computations
- **Uvicorn**: ASGI server

### Frontend
- **React**: UI framework
- **Chart.js**: Data visualization
- **react-chartjs-2**: React wrapper for Chart.js
- **WebSocket API**: Real-time communication

## Project Structure

```
logistic_assistant/
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   │   ├── master_agent/
│   │   │   │   ├── agent.py       # Master agent orchestration
│   │   │   │   ├── state.py       # Shared state definition
│   │   │   │   └── tools.py
│   │   │   └── sub_agents/
│   │   │       ├── analytics_agent/
│   │   │       │   └── agent.py   # Analytics computations
│   │   │       └── prediction_agent/
│   │   │           └── agent.py   # Prediction model
│   │   ├── api/
│   │   │   └── v1/endpoints/
│   │   │       └── logistics.py   # API routes
│   │   ├── services/
│   │   │   └── data_service.py    # Data loading
│   │   └── main.py
│   ├── data/
│   │   └── shipments.csv          # Mock shipment data
│   ├── pyproject.toml
│   └── main.py                    # Application entry point
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── ChatBox.js         # Chat interface
    │   │   ├── ChartRenderer.js   # Chart visualization
    │   │   └── TableRenderer.js   # Table display
    │   ├── App.js
    │   └── api.js
    └── package.json
```

## Prediction Model

Hermes combines time-series regression with an ensemble scenario model:
- Analyzes historical average daily delays and fits a linear trend with NumPy's `polyfit`
- Supports dynamic forecast horizons (e.g., next 5 days, 2 weeks, or 1 month)
- Builds ensemble estimates that blend a linear model with historical averages for route, warehouse, and delay reason combinations
- Surfaces the best-performing route/warehouse pairing and highlights dominant weather or operational risks
- Displays forecasts with dashed-line styling for projected values and shares recommendation bullet points in the chat

## LLM-Driven Processing (Updated)
Hermes now relies exclusively on Groq LLM outputs for:
- Intent classification (no keyword heuristics)
- Timeframe resolution (relative and absolute ranges)
- Entity filters (route / warehouse / delay_reason)
- Forecast horizon extraction
- Dynamic metric & ranking plans for routes, warehouses, and delay statistics
- Summary template generation

Planning helpers:
- llm_generate_delay_plan(query) → python_code + summary_template
- llm_generate_route_plan(query) → sort_field, sort_order, metric_label, summary_template
- llm_generate_warehouse_plan(query) → metric_field, sort_order, threshold, summary_template

## Safe Code Execution
Delay metric code returned by the LLM is executed inside a restricted sandbox:
- Allowed builtins: len, float, int, round, max, min, sum
- No imports except pandas as pd (pre-injected)
- Fallback metrics used if execution fails

### Environment Setup (Groq API Key)
Export your Groq API key before starting the backend:
```bash
export GROQ_API_KEY="sk_XXXXXXXXXXXXXXXX"
```
Without this key, the system falls back to clarification or minimal summaries.

### Updated Intent System
All intents are determined via the LLM classifier:
| Intent | Source | Notes |
|--------|--------|-------|
| greeting | LLM | Short salutations |
| gratitude | LLM | Thank-you messages |
| clarify | LLM | Ambiguous / insufficient context |
| prediction | LLM | Future delay forecasts |
| warehouse | LLM | Warehouse performance or ranking |
| route | LLM | Route performance or ranking |
| delay_reason | LLM | Cause distribution |
| delay | LLM | Delay metrics/time trends (LLM-generated code) |
| analytics | LLM | General overview fallback |
| conversation | LLM | Explanatory narrative (no charts) |
| text_only | LLM | User explicitly requests no visualization |

Removed: keyword heuristics.

## Dynamic Metric Generation
For delay/statistical queries:
1. LLM returns compute_metrics(df) definition.
2. Sandbox executes code → metrics dict.
3. Template formatting with placeholders (e.g. {period}, {total_delay_minutes}, {average_delay_minutes}).
4. Fallback summary used if code or template fails.

Route/Warehouse queries:
- LLM selects metric field & ordering (e.g. fewest delayed shipments for "best").
- Provides a summary_template; fallback textual summary if invalid.

## Failure & Fallback Behavior
- Missing Groq key → clarification or baseline summary.
- Invalid JSON plan → default metric/ordering.
- Code exec error → default metrics (total, average, count).
- Missing template placeholders → safe formatting ignore.

## Extending (LLM-Centric)
Add new analytic style:
1. Implement a new llm_generate_*_plan helper.
2. Consume plan in sub-agent, mirroring existing pattern.
3. No heuristic matching required.

## Security Notes
- Generated code never persisted.
- Restricted globals prevent filesystem/network access.
- Only dataframe transformations allowed.

## Development / Pre-Commit Hooks
Install hooks from project root (config is now at /.pre-commit-config.yaml):
```bash
pre-commit install
pre-commit run --all-files
```

## License

MIT
