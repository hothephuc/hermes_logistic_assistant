# Developer Guide - Hermes Logistics Assistant

## 🛠️ Development Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- uv package manager (or pip)
- npm

### Clone and Install

```bash
# Backend
cd backend
uv sync  # or: pip install -e .

# Frontend
cd frontend
npm install
```

---

## 🏗️ Code Structure Deep Dive

### Backend Architecture

#### 1. Entry Point (`main.py`)
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Hermes Logistics Assistant")
app.add_middleware(CORSMiddleware, ...)
app.include_router(api_router)
```

#### 2. API Layer (`app/api/v1/endpoints/logistics.py`)
- **REST Endpoint**: `GET /api/data` - Returns all shipment data
- **WebSocket Endpoint**: `/api/ws/chat` - Real-time query processing

#### 3. AI Layer (`app/ai/`)

**Master Agent** (`master_agent/agent.py`):
```python
def build_master_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("classify_intent", _classify_intent)
    graph.add_node("augment_timeframe", _augment_timeframe)
    graph.add_node("run_intent", _run_intent)
    graph.add_node("format_response", _format_response)
    # ... edges ...
    return graph
```

**Analytics Agent** (`sub_agents/analytics_agent/agent.py`):
- `_route_performance()`: Analyzes delays by route
- `_warehouse_performance()`: Evaluates warehouse efficiency
- `_delay_reason_breakdown()`: Groups delays by cause
- `_delay_statistics()`: Time-series analysis
- `_quick_overview()`: General summary

**Prediction Agent** (`sub_agents/prediction_agent/agent.py`):
```python
# Linear regression forecast
x = np.array([date.toordinal() for date in dates])
y = daily_avg_delays.to_numpy()
slope, intercept = np.polyfit(x, y, 1)

# Project 7 days forward
for i in range(1, 8):
    next_day = last_date + timedelta(days=i)
    prediction = slope * next_day.toordinal() + intercept
```

#### 4. State Management (`master_agent/state.py`)
```python
class AgentState(TypedDict, total=False):
    query: str              # User input
    data: pd.DataFrame      # Shipment data
    intent: str             # Classified intent
    filters: Dict[str, Any] # Applied filters
    timeframe: Dict[str, Any]  # Date range
    result: Dict[str, Any]  # Agent output
    response: str           # JSON payload
    steps: List[str]        # Execution trace
```

---

### Frontend Architecture

#### 1. Main App (`App.js`)
- Fetches initial data from `/api/data`
- Renders header, chat section, and data table
- Manages app-level state

#### 2. Chat Interface (`components/ChatBox.js`)
```javascript
// WebSocket connection
ws.current = new WebSocket(getWebSocketUrl());

// Parse JSON responses
const parsed = JSON.parse(message);
if (parsed.result) {
    const { summary, chart, table } = parsed.result;
    // Render components
}
```

#### 3. Chart Renderer (`components/ChartRenderer.js`)
```javascript
// Register Chart.js components
ChartJS.register(CategoryScale, LinearScale, ...);

// Render based on type
{type === 'bar' && <Bar data={chartData} options={options} />}
{type === 'line' && <Line data={chartData} options={options} />}
{type === 'pie' && <Pie data={chartData} options={options} />}
```

#### 4. Table Renderer (`components/TableRenderer.js`)
- Displays main data table
- Separate forecast table (if present)
- Responsive design with overflow scroll

---

## 🔧 Customization Guide

### Adding a New Intent

#### Step 1: Update Intent Classifier
In `master_agent/agent.py`:
```python
def _classify_intent(state: AgentState) -> AgentState:
    query = state["query"].lower()

    # Add new intent keywords
    if "driver" in query or "personnel" in query:
        intent = "driver_analysis"
    # ... existing intents ...
```

#### Step 2: Create Handler Function
In `analytics_agent/agent.py`:
```python
def _driver_analysis(state: AgentState, df: pd.DataFrame) -> Dict[str, Any]:
    # Your analysis logic
    driver_stats = df.groupby("driver").agg(
        total_shipments=("id", "count"),
        delays=("delay_minutes", lambda x: (x > 0).sum())
    )

    return {
        "summary": "Driver analysis summary...",
        "chart": {
            "type": "bar",
            "title": "Shipments per Driver",
            "data": [...]
        },
        "table": {...}
    }
```

#### Step 3: Add Routing
In `analytics_agent/agent.py`:
```python
def run_analytics_intent(state: AgentState) -> Dict[str, Any]:
    intent = state.get("intent", "analytics")

    if intent == "driver_analysis":
        return _driver_analysis(state, df)
    # ... existing intents ...
```

---

### Adding a New Chart Type

#### Step 1: Install Chart.js Plugin (if needed)
```bash
cd frontend
npm install chartjs-plugin-datalabels
```

#### Step 2: Register Plugin
In `ChartRenderer.js`:
```javascript
import { Doughnut } from 'react-chartjs-2';
import ChartDataLabels from 'chartjs-plugin-datalabels';

ChartJS.register(...existing, ChartDataLabels);

// Add to render
{type === 'doughnut' && <Doughnut data={chartData} options={options} />}
```

#### Step 3: Return from Agent
In agent code:
```python
return {
    "chart": {
        "type": "doughnut",
        "title": "My Doughnut Chart",
        "data": [{"label": "A", "value": 10}, ...]
    }
}
```

---

### Adding a New Data Source

#### Step 1: Add CSV/JSON File
```bash
backend/data/drivers.csv
```

#### Step 2: Update Data Service
In `data_service.py`:
```python
def load_drivers():
    df = pd.read_csv(DRIVERS_FILE)
    return df
```

#### Step 3: Merge Data in Agent
In `analytics_agent/agent.py`:
```python
from app.services.data_service import load_drivers

def run_analytics_intent(state: AgentState) -> Dict[str, Any]:
    shipments = state["data"]
    drivers = load_drivers()

    # Merge dataframes
    merged = shipments.merge(drivers, on="driver_id")
```

---

## 🐛 Debugging Tips

### Backend Debugging

#### 1. Enable Debug Logging
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

#### 2. Inspect State at Each Node
In `master_agent/agent.py`:
```python
def _classify_intent(state: AgentState) -> AgentState:
    print(f"DEBUG: Query = {state['query']}")
    # ... logic ...
    print(f"DEBUG: Classified as {intent}")
```

#### 3. Test Agents Directly
```python
from app.ai.master_agent.state import AgentState
from app.ai.sub_agents.analytics_agent.agent import run_analytics_intent

state: AgentState = {
    "query": "test",
    "data": df,
    "intent": "route",
    # ...
}
result = run_analytics_intent(state)
print(result)
```

### Frontend Debugging

#### 1. Console Logging
In `ChatBox.js`:
```javascript
ws.current.onmessage = (event) => {
    console.log('Received:', event.data);
    // ... parse and render ...
};
```

#### 2. React DevTools
- Install React Developer Tools extension
- Inspect component state and props
- View component hierarchy

#### 3. Network Tab
- Open DevTools → Network → WS (WebSocket)
- View messages sent/received
- Inspect JSON payloads

---

## 🧪 Testing

### Unit Tests

#### Backend Test Example
```python
# backend/tests/test_analytics.py
import pytest
from app.ai.sub_agents.analytics_agent.agent import run_analytics_intent

def test_route_performance():
    state = {
        "query": "route delays",
        "data": mock_df,
        "intent": "route",
    }
    result = run_analytics_intent(state)

    assert result["summary"]
    assert result["chart"]["type"] == "bar"
    assert len(result["chart"]["data"]) > 0
```

#### Frontend Test Example
```javascript
// frontend/src/components/ChatBox.test.js
import { render, screen } from '@testing-library/react';
import ChatBox from './ChatBox';

test('renders welcome message', () => {
    render(<ChatBox />);
    const linkElement = screen.getByText(/Hello! I am Hermes/i);
    expect(linkElement).toBeInTheDocument();
});
```

### Integration Tests

```bash
# Test full flow
cd backend
uv run python test_agents.py

# Expected output:
# ✅ All queries processed successfully
# ✅ Charts generated
# ✅ Tables formatted
```

---

## 📊 Performance Optimization

### Backend

#### 1. Cache Graph Compilation
```python
from functools import lru_cache

@lru_cache(maxsize=1)
def _graph():
    return build_master_graph().compile()
```

#### 2. Optimize Pandas Operations
```python
# Use vectorized operations
df["is_delayed"] = df["delay_minutes"] > 0

# Avoid loops
summary = df.groupby("route").agg({...})
```

#### 3. Profile Code
```python
import cProfile

cProfile.run('process_query(query, df)')
```

### Frontend

#### 1. Memoize Components
```javascript
import { memo } from 'react';

const ChartRenderer = memo(({ chartConfig }) => {
    // ... render logic ...
});
```

#### 2. Lazy Load Charts
```javascript
import { lazy, Suspense } from 'react';

const ChartRenderer = lazy(() => import('./ChartRenderer'));

<Suspense fallback={<div>Loading...</div>}>
    <ChartRenderer {...props} />
</Suspense>
```

#### 3. Debounce Input
```javascript
import { debounce } from 'lodash';

const debouncedSend = debounce((message) => {
    ws.current.send(message);
}, 300);
```

---

## 🚀 Deployment

### Docker Setup

#### Dockerfile (Backend)
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Dockerfile (Frontend)
```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=0 /app/build /usr/share/nginx/html
```

#### docker-compose.yml
```yaml
version: '3.8'
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
```

---

## 📚 Resources

### LangGraph
- [Official Docs](https://langchain-ai.github.io/langgraph/)
- [State Management](https://langchain-ai.github.io/langgraph/concepts/low_level/)
- [Multi-Agent Examples](https://github.com/langchain-ai/langgraph/tree/main/examples)

### Chart.js
- [Documentation](https://www.chartjs.org/docs/)
- [React Integration](https://react-chartjs-2.js.org/)
- [Chart Types](https://www.chartjs.org/docs/latest/charts/)

### FastAPI
- [WebSocket Guide](https://fastapi.tiangolo.com/advanced/websockets/)
- [CORS Setup](https://fastapi.tiangolo.com/tutorial/cors/)

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📧 Support

For questions or issues:
- Check existing documentation (README.md, EXAMPLE_QUERIES.md)
- Review test cases in `test_agents.py`
- Inspect browser console and network tab
- Check backend logs for errors

Happy coding! 🚀
