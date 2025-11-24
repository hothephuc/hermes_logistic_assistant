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

**NOTE:** Please create `.env` file in backend folder and add GROQ_API_KEY= 

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

## Extending the System

### Adding New Intents
1. Update `_classify_intent` in `backend/app/ai/master_agent/agent.py`
2. Create new handler function in analytics or prediction agent
3. Add routing logic in `run_analytics_intent` or `run_prediction_intent`

### Adding New Chart Types
1. Register new Chart.js chart type in `frontend/src/components/ChartRenderer.js`
2. Add chart configuration in agent response
3. Update rendering logic in `ChartRenderer`

## Development Notes

- The LangGraph state is passed between agents using TypedDict
- Each agent updates the state and returns it for the next node
- The master agent compiles the graph once and caches it
- Charts support forecast vs. actual data with different styling

## License

MIT
