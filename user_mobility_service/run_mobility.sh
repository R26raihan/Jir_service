#!/bin/bash

echo "🚶 Starting User Mobility Service..."
echo "📍 Location: $(pwd)"
echo "🔧 Loading dependencies..."

# Kill any existing process on port 8002
lsof -ti:8002 | xargs kill -9 2>/dev/null || true

# Run the application
echo "🌐 Starting server on http://localhost:8002"
echo "📖 API Documentation: http://localhost:8002/docs"
echo "🔍 Test endpoint: http://localhost:8002/test"
echo "💚 Health check: http://localhost:8002/health"
echo "🗄️  Database info: http://localhost:8002/db-info"
echo "👥 Users: http://localhost:8002/users"
echo "🚶 Mobility: http://localhost:8002/mobility"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn app:app --host 0.0.0.0 --port 8002 --reload
