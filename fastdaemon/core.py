# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_core.ipynb.

# %% auto 0
__all__ = ['send_recv', 'DaemonHandler', 'DaemonServer', 'fastdaemon_serve']

# %% ../00_core.ipynb 2
import socket
from contextlib import redirect_stdout
from io import StringIO
from multiprocessing import get_context
from socketserver import TCPServer, StreamRequestHandler

from fastcore.meta import *
from fastcore.net import *
from fastcore.script import *
from fastcore.utils import *

# %% ../00_core.ipynb 5
def send_recv(s, port, host=None, dgram=False, encoding='utf-8'):
    "Wraps `start_client`; send string `s` in `encoding` and return its response"
    with start_client(port, host=host, dgram=dgram) as client:
        client.sendall((s+'\n').encode(encoding))
        with client.makefile('rb') as f: return f.read().decode('utf-8')

# %% ../00_core.ipynb 6
def _handle(cmd, data):
    "Execute `cmd` with args parsed from `data` and return `stdout`"
    argv = data.decode().strip()
    sys.argv = [cmd.__name__] + (argv.split(' ') if argv else [])
    with redirect_stdout(StringIO()) as s: cmd()
    return s.getvalue().encode()

# %% ../00_core.ipynb 7
class DaemonHandler(StreamRequestHandler):
    "Execute server's `cmd` with request args using server's process pool"
    def handle(self):
        data = self.rfile.readline().strip()
        future = self.server.pool.submit(_handle, self.server.cmd, data)
        result = future.result()
        self.wfile.write(result)

# %% ../00_core.ipynb 9
class DaemonServer(TCPServer): # TODO: could be a mixin to support other servers; `Pool(ed)Server`?
    "A `TCPServer` that executes `cmd` with request args using a process pool"
    @delegates(TCPServer)
    def __init__(self, server_address, cmd, RequestHandlerClass=DaemonHandler, timeout=None, **kwargs):
        self.cmd = cmd # TODO: is this the best place for `cmd`?
        if timeout is not None: self.timeout = timeout
        self.allow_reuse_address = True
        super().__init__(server_address, RequestHandlerClass)
        
    def server_activate(self):
        self.pool = ProcessPoolExecutor(mp_context=get_context('fork')) # TODO: make ctx configurable?
        super().server_activate()
        
    def server_close(self):
        if hasattr(self,'pool'): self.pool.shutdown()
        super().server_close()
        
    def handle_timeout(self): return True

# %% ../00_core.ipynb 16
def fastdaemon_serve(cmd, port, host=None, timeout=None):
    "Serve `cmd` on `port`, with optional `host` and `timeout`"
    host = host or socket.gethostname()
    with DaemonServer((host,port), cmd, timeout=timeout) as srv:
        while not srv.handle_request(): pass
