# AUTOGENERATED! DO NOT EDIT! File to edit: ../00_core.ipynb.

# %% auto 0
__all__ = ['send_record', 'recv_record', 'start_client', 'transfer', 'fastdaemon_client']

# %% ../00_core.ipynb 3
import argparse,socket,struct,sys

# %% ../00_core.ipynb 7
def _S(fmt): return struct.Struct('!'+fmt) # use `struct` "network order"
_long_struct = _S('L')

# %% ../00_core.ipynb 8
def _recv_struct(r, fmt):
    if not isinstance(fmt,struct.Struct): fmt = _S(fmt)
    res = fmt.unpack(r(fmt.size))
    return res[0] if len(res)==1 else res

# %% ../00_core.ipynb 9
def _str_struct(s): return _long_struct.pack(len(s)) + (s.encode('utf-8') if isinstance(s,str) else s)

# %% ../00_core.ipynb 10
def send_record(w, c):
    "Send a sequence of length-prefixed utf-8-encoded strings"
    w(b''.join(_str_struct(s) for s in c))

# %% ../00_core.ipynb 12
def _recv_len(r): return _recv_struct(r, _long_struct)

# %% ../00_core.ipynb 14
def _recv_string(r):
    l = _recv_len(r)
    return struct.unpack(f'{l}s', r(l))[0].decode('utf-8')

# %% ../00_core.ipynb 15
def recv_record(r):
    "Receive two variable-length utf-8-encoded strings"
    return [_recv_string(r) for _ in range(2)]

# %% ../00_core.ipynb 17
def _socket_det(port,host,dgram):
    # Source: https://github.com/fastai/fastcore/blob/da9ca219c86190d22f4dbf2c3cad619c477d64a4/fastcore/net.py#L222-L225
    if isinstance(port,int): family,addr = socket.AF_INET,(host or socket.gethostname(),port) # TODO: default to localhost?
    else: family,addr = socket.AF_UNIX,port
    return family,addr,(socket.SOCK_STREAM,socket.SOCK_DGRAM)[dgram]

# %% ../00_core.ipynb 18
def start_client(port, host=None, dgram=False):
    "Create a `socket` client on `port`, with optional `host`, of type `dgram`"
    # Source: https://github.com/fastai/fastcore/blob/da9ca219c86190d22f4dbf2c3cad619c477d64a4/fastcore/net.py#L242-L247
    family,addr,typ = _socket_det(port,host,dgram)
    s = socket.socket(family, typ)
    s.connect(addr)
    return s

# %% ../00_core.ipynb 19
def transfer(data, port, host=None, dgram=False):
    "Send a request and receive a reply in one socket"
    with start_client(port, host, dgram) as client:
        with client.makefile('wb') as f: send_record(f.write, data)
        with client.makefile('rb') as f: return recv_record(f.read)

# %% ../00_core.ipynb 24
def _fastdaemon_client(port, host, dgram, args):
    args = ' '.join(args)
    stdin = sys.stdin.read() if not sys.stdin.isatty() else ''
    stdout,stderr = transfer((stdin,args), port, host)
    sys.stderr.write(stderr)
    sys.stdout.write(stdout)

# %% ../00_core.ipynb 25
def fastdaemon_client(argv=None):
    "Forward `sys.argv` and `sys.stdin` to server and write response to `sys.stdout` and `sys.stderr`"
    if argv is None: argv = sys.argv[1:]
    p = argparse.ArgumentParser(description=fastdaemon_client.__doc__)
    p.add_argument('port', type=str, help='Server port. Use int for TCP, and str for Unix socket')
    p.add_argument('--host', type=str, help='Server host (default: `socket.gethostname()`)', default=None)
    p.add_argument('--dgram', action='store_true', help='Use `SOCK_DGRAM`?', default=None)
    args,rest = p.parse_known_args(argv)
    try: args.port = int(args.port)
    except ValueError: pass
    args.args = rest
    _fastdaemon_client(**vars(args))
