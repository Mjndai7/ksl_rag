#!/bin/bash
set -e

# Write Google Drive credentials from environment variable
if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
    echo "$GOOGLE_CREDENTIALS_JSON" > /app/credentials/qubo-426217-6ebaa2216a16.json
    echo "✓ Google credentials written from environment variable"
fi

# Start the application
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
