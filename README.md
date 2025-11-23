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

The system uses simple linear regression for delay prediction:
- Analyzes historical average daily delays
- Computes trend line using NumPy's `polyfit`
- Projects delays for the next 7 days
- Displays forecast with distinct visual styling

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
