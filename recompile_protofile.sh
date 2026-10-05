#!/usr/bin/env bash

uv run python -m grpc_tools.protoc -I src/guru/rpc --python_out=src/guru/rpc --grpc_python_out=src/guru/rpc src/guru/rpc/sensei_rpc.proto

sed -i 's/import sensei_rpc_pb2 as sensei__rpc__pb2/from . import sensei_rpc_pb2 as sensei__rpc__pb2/' src/guru/rpc/sensei_rpc_pb2_grpc.py
