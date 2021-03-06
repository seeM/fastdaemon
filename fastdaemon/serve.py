# AUTOGENERATED! DO NOT EDIT! File to edit: ../01_serve.ipynb.

# %% auto 0
__all__ = ['CmdHandler', 'CmdMixin', 'CmdTCPServer', 'fastdaemon_serve']

# %% ../01_serve.ipynb 2
import importlib
import sys
from contextlib import contextmanager
from functools import partial
from io import StringIO
from multiprocessing import get_context
from socketserver import TCPServer, StreamRequestHandler, ThreadingTCPServer, ThreadingUnixStreamServer

from fastcore.parallel import ProcessPoolExecutor
from fastcore.script import *

from .core import *

from datetime import datetime # TODO: remove after optimising

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
        print(f'len(stdin)={len(self.stdin.getvalue())} argv={self.argv}')
    def finish(self):
        self.stdout,self.stderr = self.stdout.getvalue(),self.stderr.getvalue()
        send_record(self.wfile.write, (self.stdout,self.stderr))
        super().finish()
    def _handle(self, f):
        pool = getattr(self.server,'pool',None)
        if pool is not None: return pool.submit(f).result()
        return f()
    def handle(self):
        f = partial(_run, self.server.cmd, self.argv, self.stdin, self.stdout, self.stderr)
        self.stdout,self.stderr = self._handle(f)

# %% ../01_serve.ipynb 18
class CmdMixin:
    "Socket server with a `cmd` and optional `pool`"
    def __init__(self, server_address, cmd, pool=None, RequestHandlerClass=CmdHandler, timeout=None, **kwargs):
        self.cmd,self.pool = cmd,pool
        if timeout is not None: self.timeout = timeout
        super().__init__(server_address, RequestHandlerClass)

    def handle_timeout(self): return True

# %% ../01_serve.ipynb 22
class CmdTCPServer(CmdMixin, ThreadingTCPServer):
    allow_reuse_address = True

# %% ../01_serve.ipynb 23
def _fastdaemon_serve(cmd, port, host='localhost', timeout=None):
    "Serve `cmd` on `port`, with optional `host` and `timeout`"
    with ProcessPoolExecutor() as pool, CmdTCPServer((host,port), cmd, pool, timeout=timeout) as srv:
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
    _fastdaemon_serve(_cmd, port, host, timeout) # TODO: dont need two functions because of call_parse
