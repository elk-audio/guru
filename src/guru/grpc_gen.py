"""
This module is DEPRECATED
"""
import __main__
import os
import sys
import importlib
from types import ModuleType
from typing import Tuple


def modules_from_proto(proto_filename: str) -> Tuple[ModuleType, ModuleType]:
    """
    Run protoc compiler and get generated modules.

    Parameters:
        proto_filename : path to .proto file with service definition

    Returns:
        (protobuf_module, grpc_module)
    """
    full_path = os.path.abspath(proto_filename)
    [inc_path, rel_proto_filename] = os.path.split(full_path)
    out_dir = "."
    if hasattr(__main__, "__file__"):
        file_path = os.path.dirname(os.path.abspath(__main__.__file__))
        if sys.path[0] == file_path:
            out_dir = file_path

    proto_base_name = os.path.splitext(rel_proto_filename)[0]
    proto_module_name = "%s_pb2" % proto_base_name
    grpc_module_name = "%s_pb2_grpc" % proto_base_name

    if not os.path.exists(out_dir + "/" + proto_module_name + ".py"):
        import grpc_tools.protoc as gprotoc
        protoc_args = [
            "dummy",
            "-I%s" % inc_path,
            f"--python_out={out_dir}",
            f"--grpc_python_out={out_dir}",
            rel_proto_filename,
        ]
        gprotoc.main(protoc_args)
        print("PROTO: Compiled proto file!")
    else:
        print("PROTO: Compiled proto found!")

    proto_module = importlib.import_module(proto_module_name)
    grpc_module = importlib.import_module(grpc_module_name)
    return (proto_module, grpc_module)
