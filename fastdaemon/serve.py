# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_serve.ipynb.

# %% auto 0
__all__ = ['CmdHandler', 'PoolingMixin', 'PoolingTCPServer', 'fastdaemon_serve']

# %% ../01_serve.ipynb 2
import importlib
import sys
from contextlib import contextmanager
from functools import partial
from io import StringIO
from multiprocessing import get_context
from socketserver import TCPServer, StreamRequestHandler

from fastcore.parallel import ProcessPoolExecutor
from fastcore.script import *

from .core import *

# %% ../01_serve.ipynb 5
def _setattrs(o, d):
    for k,v in d.items(): setattr(o,k,v)

# %% ../01_serve.ipynb 6
@contextmanager
def _redirect_streams(argv, stdin, stdout, stderr):
    new = {k:v for k,v in locals().items()}
    old = {o:getattr(sys,o) for o in new.keys()}
    _setattrs(sys, new)
    try: yield new['stdout'],new['stderr']
    finally: _setattrs(sys, old)

# %% ../01_serve.ipynb 7
def _run(cmd, argv, stdin, stdout, stderr):
    with _redirect_streams(argv,stdin,stdout,stderr): cmd()
    return stdout,stderr

# %% ../01_serve.ipynb 8
class CmdHandler(StreamRequestHandler):
    "Run `self.server.cmd` with request's `argv` and `stdin`; return `stdout` and `stderr`"
    def setup(self):
        super().setup()
        stdin,argv = recv_record(self.rfile.read)
        self.argv = [self.server.cmd.__name__] + argv.split(' ') if argv else []
        self.stdin,self.stdout,self.stderr = StringIO(stdin),StringIO(),StringIO()
        print(f'stdin={self.stdin.getvalue()} argv={self.argv}')

    def finish(self):
        self.stdout,self.stderr = self.stdout.getvalue(),self.stderr.getvalue()
        print(f'stdout={self.stdout} stderr={self.stderr}')
        send_record(self.wfile.write, (self.stdout,self.stderr))
        super().finish()

    def _handle(self, f): return self.server.pool.submit(f).result() if hasattr(self.server,'pool') else f()
    def handle(self):
        f = partial(_run, self.server.cmd, self.argv, self.stdin, self.stdout, self.stderr)
        self.stdout,self.stderr = self._handle(f)

# %% ../01_serve.ipynb 15
class PoolingMixin:
    "Socket server with a `cmd` and `ProcessPoolExecutor`"
    def __init__(self, server_address, cmd, RequestHandlerClass=CmdHandler, timeout=None, **kwargs):
        self.cmd = cmd
        if timeout is not None: self.timeout = timeout
        super().__init__(server_address, RequestHandlerClass)

    def server_activate(self):
        self.pool = ProcessPoolExecutor(mp_context=get_context('fork')) # TODO: make ctx configurable?
        super().server_activate()
        
    def server_close(self):
        if hasattr(self,'pool'): self.pool.shutdown()
        super().server_close()
        
    def handle_timeout(self): return True

# %% ../01_serve.ipynb 22
class PoolingTCPServer(PoolingMixin, TCPServer):
    allow_reuse_address = True

# %% ../01_serve.ipynb 23
def _fastdaemon_serve(cmd, port, host=None, timeout=None):
    "Serve `cmd` on `port`, with optional `host` and `timeout`"
    host = host or 'localhost'
    with PoolingTCPServer((host,port), cmd, timeout=timeout) as srv:
        while not srv.handle_request(): pass

# %% ../01_serve.ipynb 27
def _import_cmd(cmd):
    mn, on = cmd.split(':')
    m = importlib.import_module(mn)
    return getattr(m,on)

# %% ../01_serve.ipynb 29
@call_parse
def fastdaemon_serve(
    cmd:str, # Module path to callable command (example: pkg.mod:obj)
    port:int, # Server port
    host:str='localhost', # Server host
    timeout:int=None): # Shutdown after `timeout` seconds without requests
    "Serve `cmd` on `port`, with optional `host` and `timeout`"
    _cmd = _import_cmd(cmd)
    with PoolingTCPServer((host,port), _cmd, timeout=timeout) as srv:
        while not srv.handle_request(): pass
