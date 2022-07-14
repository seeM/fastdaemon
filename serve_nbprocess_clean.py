from nbprocess.clean import nbprocess_clean
from fastdaemon.server import fastdaemon_serve
fastdaemon_serve(nbprocess_clean, 9998)
