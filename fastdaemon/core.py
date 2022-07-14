# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_core.ipynb.

# %% auto 0
__all__ = ['pack_streams', 'send_streams', 'readlen', 'recv_streams', 'send_recv', 'DaemonHandler', 'DaemonServer',
           'fastdaemon_serve', 'fastdaemon_client']

# %% ../00_core.ipynb 2
import socket
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from multiprocessing import get_context
from socketserver import TCPServer, StreamRequestHandler

from fastcore.meta import *
from fastcore.net import *
from fastcore.script import *
from fastcore.utils import *

# %% ../00_core.ipynb 5
import struct
from io import BytesIO

# %% ../00_core.ipynb 6
def pack_streams(streams): # TODO: use chunked?
    "Pack a list of variable length utf-8 strings"
    streams = [o.encode('utf-8') if isinstance(o,str) else o for o in streams]
    ls = [len(o) for o in streams]
    fmt = '!'+''.join(f'L{l}s' for l,s in zip(ls,streams))
    vs = sum(list(zip(ls, streams)), ())
    return struct.pack(fmt, *vs)

# %% ../00_core.ipynb 8
def send_streams(w, streams): w(pack_streams(streams)) # TODO: needed?

# %% ../00_core.ipynb 9
def readlen(r):
    "Read the length of the next parameter"
    return struct.unpack('!L', r(4))[0]

# %% ../00_core.ipynb 11
def recv_streams(r):
    "Receive a 2-tuple of variable length utf-8 strings"
    res = []
    for _ in range(2):
        lv = readlen(r)
        v = struct.unpack(f'{lv}s', r(lv))[0].decode('utf-8')
        res.append(v)
    return res

# %% ../00_core.ipynb 13
def send_recv(streams, port, host=None, dgram=False):
    "Wraps `start_client`, `send_streams`, and `recv_streams`"
    with start_client(port, host=host, dgram=dgram) as client:
        with client.makefile('wb') as f: send_streams(f.write, streams)
        with client.makefile('rb') as f: return recv_streams(f.read)

# %% ../00_core.ipynb 14
def _handle(cmd, stdin, args):
    "Execute `cmd` with `stdin` and `args`, and return `stdout`"
    sys.argv = [cmd.__name__] + (args.split(' ') if args else [])
    sys.stdin,sys_stdin = StringIO(stdin),sys.stdin
    with redirect_stdout(StringIO()) as stdout, redirect_stderr(StringIO()) as stderr: cmd()
    sys.stdin = sys_stdin
    return tuple(o.getvalue().encode() for o in (stdout,stderr))

# %% ../00_core.ipynb 15
class DaemonHandler(StreamRequestHandler):
    "Execute server's `cmd` with request args using server's process pool"
    def handle(self):
        stdin,args = recv_streams(self.rfile.read)
        print(f'{stdin=} {args=}')
        future = self.server.pool.submit(_handle, self.server.cmd, stdin, args)
        stdout, stderr = future.result()
        print(f'{stdout=} {stderr=}')
        send_streams(self.wfile.write, (stdout,stderr))

# %% ../00_core.ipynb 17
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

# %% ../00_core.ipynb 24
def fastdaemon_serve(cmd, port, host=None, timeout=None):
    "Serve `cmd` on `port`, with optional `host` and `timeout`"
    host = host or socket.gethostname()
    with DaemonServer((host,port), cmd, timeout=timeout) as srv:
        while not srv.handle_request(): pass

# %% ../00_core.ipynb 28
from nbprocess.clean import wrapio

# %% ../00_core.ipynb 29
@call_parse(nested=True)
def fastdaemon_client(
    port:int, # Port to connect to
    host:str=None): # Host to connect to
    "Forward `sys.args` and `sys.stdin` to `fastdaemon_server` and write response `stdout` and `stderr`"
    args = ' '.join(sys.argv[1:])
    stdin = wrapio(sys.stdin).read() if not sys.stdin.isatty() else '' # TODO: wrapio needed?
    stdout,stderr = send_recv((stdin,args), port, host)
    sys.stderr.write(stderr)
    sys.stdout.write(stdout)
