#!/usr/bin/env python3
"""
Charity Intelligence Map — Application Runner
===============================================
Starts the FastAPI server which serves both the REST API
and the frontend dashboard.

Usage:
    python run.py                    # Default: http://localhost:8000
    python run.py --port 3000        # Custom port
    python run.py --host 127.0.0.1   # Bind to localhost only
"""

import os
import sys
import argparse

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()
app.mount("/static", StaticFiles(directory="frontend"), name="static")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.config import API_HOST, API_PORT

def main():
    parser = argparse.ArgumentParser(description="Charity Intelligence Map — Server")
    parser.add_argument("--host", type=str, default=API_HOST, help="Bind host")
    parser.add_argument("--port", type=int, default=API_PORT, help="Bind port")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("✗ uvicorn is required. Install with:")
        print("  pip install fastapi uvicorn")
        print("\nAlternatively, just open frontend/index.html directly in a browser.")
        sys.exit(1)

    print("╔══════════════════════════════════════════════════╗")
    print("║  Charity Intelligence Map                        ║")
    print(f"║  http://{args.host}:{args.port}                          ║")
    print("╚══════════════════════════════════════════════════╝")
    print()
    print("  API docs:  http://localhost:{}/docs".format(args.port))
    print("  Dashboard: http://localhost:{}".format(args.port))
    print()

    uvicorn.run(
        "backend.api:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()