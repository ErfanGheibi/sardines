#!/usr/bin/env bash
# Rebuild + run the Sydney Metro live carriage app.
# Put app.py, index.html, tfnsw_metro.proto in the same folder as this script.
set -e

python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install requests protobuf grpcio-tools fastapi uvicorn

# Generate tfnsw_metro_pb2.py from the proto
python3 -m grpc_tools.protoc -I. --python_out=. tfnsw_metro.proto

# The app reads your API key from .tfnsw_api_key (next to app.py).
# If it's empty/missing or the key is rejected, the app will prompt you for one
# in this terminal and save it once it works.
uvicorn app:app --host 0.0.0.0 --port 8000
# then open http://localhost:8000
