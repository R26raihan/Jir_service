#!/bin/bash

echo "🚀 Starting Crowd Monitoring Service..."
echo "📍 Location: $(pwd)"
echo "🔧 Loading model and dependencies..."

# Kill any existing process on port 8000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Run the application
echo "🌐 Starting server on http://localhost:8000"
echo "📖 API Documentation: http://localhost:8000/docs"
echo "🔍 Test endpoint: http://localhost:8000/test"
echo "👥 Crowd data: http://localhost:8000/crowd"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
