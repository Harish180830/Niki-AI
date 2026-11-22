#!/usr/bin/env bash
# Starts the FastAPI backend (port 8000) and the Streamlit frontend (port 8501).
# Paste your Groq key in the app sidebar when it opens - nothing to export.
set -e
uvicorn main:api --host 127.0.0.1 --port 8000 &
API_PID=$!
trap "kill $API_PID" EXIT
BACKEND_URL=http://127.0.0.1:8000 streamlit run app.py
