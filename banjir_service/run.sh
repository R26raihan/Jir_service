#!/bin/bash

echo "🚀 Starting Banjir Service..."
echo "📍 Location: $(pwd)"
echo "🔧 Loading dependencies..."

# Kill any existing process on port 8001
lsof -ti:8001 | xargs kill -9 2>/dev/null || true

# Run the application
echo "🌐 Starting server on http://localhost:8001"
echo "📖 API Documentation: http://localhost:8001/docs"
echo "🔍 Test endpoint: http://localhost:8001/test"
echo "🌊 Pintu Air data: http://localhost:8001/pintu-air"
echo "🏘️  RT Terdampak: http://localhost:8001/rt-terdampak"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn Databanjir:app --host 0.0.0.0 --port 8001 --reload
