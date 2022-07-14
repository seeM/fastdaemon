from nbprocess.clean import nbprocess_clean
from fastdaemon.core import fastdaemon_serve
fastdaemon_serve(nbprocess_clean, 9998)
