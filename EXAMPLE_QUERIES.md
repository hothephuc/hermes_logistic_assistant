# Example Queries for Hermes Logistics Assistant

This document provides comprehensive examples of queries you can ask the Hermes Logistics Assistant, organized by category.

## 📊 Route Performance Queries

### Most Delays
- "Which route had the most delays last week?"
- "Show me the route with the highest delay count"
- "Which route is performing worst?"
- "Compare routes by delay incidents"

### Route Statistics
- "Show me delay statistics for Route A"
- "How many shipments were delayed on Route B?"
- "Give me route performance summary"
- "Show total delay minutes per route"

### Expected Response
- **Summary**: Text describing which route had most delays
- **Chart**: Bar chart showing delayed shipments per route
- **Table**: Detailed breakdown with delay minutes and averages

---

## 🏭 Warehouse Performance Queries

### Delivery Time Analysis
- "List warehouses with average delivery time above 5 days"
- "Which warehouse has the longest delivery time?"
- "Show me warehouses with delivery time greater than 5 days"
- "Compare warehouse delivery performance"

### Warehouse Statistics
- "Which warehouse performs best?"
- "Show me warehouse efficiency stats"
- "List all warehouses by performance"
- "What's the average delivery time per warehouse?"

### Expected Response
- **Summary**: Text listing warehouses meeting criteria
- **Chart**: Bar chart of average delivery times
- **Table**: Warehouse stats with delayed vs total shipments

---

## 🚨 Delay Reason Analysis

### Breakdown by Cause
- "Show total delayed shipments by delay reason"
- "What are the main causes of delays?"
- "Break down delays by reason"
- "Which delay reason is most common?"

### Incident Counts
- "How many delays were caused by weather?"
- "Show traffic-related delays"
- "List all delay reasons with counts"
- "What percentage of delays are mechanical?"

### Expected Response
- **Summary**: Text breakdown of all delay reasons
- **Chart**: Pie chart showing distribution of delay causes
- **Table**: Delay reasons with incident counts and total minutes

---

## 📅 Time-Based Statistics

### Historical Analysis
- "What was the average delay in October?"
- "Show delay trends over time"
- "Average delay last month"
- "How have delays changed over time?"

### Date Range Queries
- "Show me delays from last week"
- "What were the delays in October 2024?"
- "Compare this month to last month"
- "Give me a daily breakdown of delays"

### Expected Response
- **Summary**: Average delay for the time period
- **Chart**: Line chart showing daily delay trends
- **Table**: Day-by-day breakdown with metrics

---

## 🔮 Prediction Queries (Bonus Feature)

### Forecasting
- "Predict the delay rate for next week"
- "Forecast next week's delays"
- "What will delays look like next week?"
- "Project delays for the coming week"

### Trend Analysis
- "Are delays increasing or decreasing?"
- "What's the delay trend?"
- "Predict future delay patterns"
- "Show me the forecast"

### Expected Response
- **Summary**: Predicted average delay for next week
- **Chart**: Line chart with historical data and forecast (dashed line)
- **Table**: Historical actuals + forecast table with predictions

---

## 📈 General Analytics Queries

### Overview
- "Give me an overview of shipments"
- "Show me general statistics"
- "What's the overall performance?"
- "Summarize shipment data"

### Combined Queries
- "Show delays by warehouse and route"
- "Which combination of route and warehouse has most delays?"
- "Compare everything"

### Expected Response
- **Summary**: High-level overview statistics
- **Chart**: Line chart of total delays over time
- **Table**: Various depending on query complexity

---

## 🎯 Tips for Best Results

### Be Specific
- ✅ "Which route had the most delays last week?"
- ❌ "delays"

### Use Natural Language
- ✅ "Show me warehouses with delivery time above 5 days"
- ✅ "List all delay reasons"
- ✅ "Predict next week"

### Timeframe Keywords
The system recognizes:
- "last week"
- "last month"
- "October" (or any month name)
- "next week" (for predictions)

### Intent Keywords
The system classifies queries based on keywords:
- **Route**: "route", "routes"
- **Warehouse**: "warehouse", "warehouses"
- **Delay Reason**: "reason", "cause", "why"
- **Delay Stats**: "average delay", "delay in", "delay last"
- **Prediction**: "predict", "forecast", "next week", "projection"

---

## 🎨 Understanding the Responses

### Text Summary
Every response includes a natural language summary of the findings.

### Charts
- **Bar Charts**: Used for comparing categories (routes, warehouses)
- **Line Charts**: Used for time-series data and trends
- **Pie Charts**: Used for showing proportions (delay reasons)
- **Forecast Charts**: Line charts with dashed lines for predictions

### Tables
Provide detailed numerical data supporting the summary and charts.
- Regular rows for historical data
- Highlighted rows for forecast data (yellow background)

---

## 🚀 Advanced Query Examples

### Complex Filters
While the system currently supports basic filters, you can combine concepts:
- "Show Route A delays in October"
- "Warehouse WH1 performance last month"

### Multi-part Questions
Ask follow-up questions based on results:
1. "Which route has most delays?"
2. (After seeing results) "What are the reasons for Route A delays?"
3. (Follow-up) "Predict Route A delays next week"

---

## 📝 Query Response Time

Most queries return results in **under 2 seconds**, including:
- Intent classification
- Data filtering and aggregation
- Chart and table generation
- Response formatting

Prediction queries may take slightly longer due to regression computation.

---

## 🔧 Troubleshooting

### No Results?
- Check if your timeframe has data (the dataset is from October 2024)
- Verify spelling of routes (Route A, Route B, Route C)
- Verify warehouse names (WH1, WH2, WH3)

### Unexpected Chart Type?
The system automatically chooses the best chart type:
- Routes/Warehouses → Bar chart
- Time series → Line chart
- Proportions → Pie chart

### Want Different Insights?
Try rephrasing your query with different keywords to trigger different intents.

---

## 📊 Sample Query Session

```
You: "Hello"
Bot: "Hello! I am Hermes. Ask me about shipments, delays, or predictions."

You: "Which route had the most delays?"
Bot: [Summary] "Route A experienced the most delays with 5 delayed shipments..."
     [Bar Chart] Showing delayed shipments per route
     [Table] Detailed route statistics

You: "What caused these delays?"
Bot: [Summary] "Total delayed shipments by reason: Weather (3), Traffic (4)..."
     [Pie Chart] Distribution of delay causes
     [Table] Delay reasons with counts

You: "Predict next week's delays"
Bot: [Summary] "Projected average delay for next week is 12.3 minutes..."
     [Line Chart] Historical data + forecast (dashed line)
     [Table] Actuals + 7-day forecast
```

---

## 🎓 Learning More

To understand how the system processes your queries, check:
- **Backend logs**: Shows intent classification and agent routing
- **Network tab**: Inspect WebSocket messages
- **Response payload**: Contains full JSON with steps taken

Happy querying! 🚀
