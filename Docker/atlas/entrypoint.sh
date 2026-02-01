#!/bin/bash
set -e

echo "Starting Database migration..."
cd /app/models/db_schemas/atlas
alembic upgrade head
cd /app


# If a command is provided via CMD, exec it. Otherwise fall back to uvicorn.
if [ "$#" -gt 0 ]; then
	exec "$@"
else
	exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
fi