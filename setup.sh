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

# Use a fresh TfNSW Open Data API key (NOT the one from your shell history)
read -rp "Paste your TfNSW API key: " TFNSW_API_KEY
export TFNSW_API_KEY

uvicorn app:app --host 0.0.0.0 --port 8000
# then open http://localhost:8000
