#!/usr/bin/env bash
set -e
source .venv/bin/activate
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
