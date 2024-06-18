from .stream import StreamAbstract, make_stream, get_stream_names

# load all the stream classes

import glob
import importlib
import os
for file in glob.glob(os.path.dirname(__file__)+"/*stream.py"):
    module_name = file.split("/")[-1].split(".")[0]
    try:
        importlib.import_module(f"mcfs_tools.streams.{module_name}")
    except Exception as e:
        pass
