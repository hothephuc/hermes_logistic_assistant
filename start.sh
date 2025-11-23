#!/bin/bash

# Hermes Logistics Assistant - Startup Script

echo "🚀 Starting Hermes Logistics Assistant..."

# Check if we're in the correct directory
if [ ! -d "backend" ] || [ ! -d "frontend" ]; then
    echo "❌ Error: Please run this script from the root directory (logistic_assistant/)"
    exit 1
fi

# Start backend
echo "📦 Starting backend server..."
cd backend
uv run uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend to start
echo "⏳ Waiting for backend to initialize..."
sleep 3

# Start frontend
echo "🎨 Starting frontend..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ Both servers are starting!"
echo ""
echo "📍 Backend API: http://localhost:8000"
echo "📍 Frontend UI: http://localhost:3000"
echo ""
echo "💡 Try these example queries:"
echo "   - Which route had the most delays last week?"
echo "   - Show total delayed shipments by delay reason"
echo "   - List warehouses with average delivery time above 5 days"
echo "   - Predict the delay rate for next week"
echo ""
echo "🛑 To stop both servers, press CTRL+C"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "🛑 Stopping servers..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup INT TERM

# Wait for both processes
wait
