#!/bin/bash
set -e

# Write Google Drive credentials from environment variable
if [ -n "$GOOGLE_CREDENTIALS_JSON" ]; then
    mkdir -p "$(dirname "${GOOGLE_CREDENTIALS_PATH:-/app/credentials/service_account.json}")"
    echo "$GOOGLE_CREDENTIALS_JSON" > "${GOOGLE_CREDENTIALS_PATH:-/app/credentials/service_account.json}"
    echo "✓ Google credentials written from environment variable"
fi

# Apply database migrations before serving traffic
alembic upgrade head

# Start the application (Railway provides $PORT)
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
