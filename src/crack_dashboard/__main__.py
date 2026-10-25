import os
import sys
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Distributed Password Cracker - Real-Time Dashboard")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host interface (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--workers", type=int, default=1, help="Uvicorn worker count")
    args = parser.parse_args()

    print(f"[*] Starting Distributed Password Cracker Dashboard on http://{args.host}:{args.port}")
    uvicorn.run("crack_dashboard.app:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
