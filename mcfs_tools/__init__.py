"""
This module is a package that contains the tools for the firmware update of the MyActuator device.

Author: Hank Wu
Organization: Seedspider Ltd, New Zealand
"""

from .ymodem import Ymodem
from .stream import StreamAbstract, make_stream, get_stream_names
import glob

# load all the stream classes
import importlib
import os
for file in glob.glob(os.path.dirname(__file__)+"/*stream.py"):
    print(file)
    module_name = file.split("/")[-1].split(".")[0]
    try:
        importlib.import_module(f"mcfs_tools.{module_name}")
    except Exception as e:
        pass
