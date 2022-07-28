fastdaemon
================

<!-- WARNING: THIS FILE WAS AUTOGENERATED! DO NOT EDIT! -->

**NB: fastdaemon is experimental. Use it at your own risk!**

## Install

fastdaemon isn’t hosted on PyPI yet, but you can install it directly
from GitHub:

``` sh
pip install git+https://github.com/seem/fastdaemon.git
```

## How to use

**NB: fastdaemon is experimental. Use it at your own risk!**

Although fastdaemon is still under development, you can try using it to
run [`nbdev`](https://github.com/fastai/nbdev)’s git hooks.
First, serve `nbdev_clean`:

``` sh
fastdaemon_serve nbdev.clean:nbdev_clean 9998
```

Then update your `.gitconfig`:

``` ini
[filter "clean-nbs"]
        clean = fastdaemon_client 9998 -- --stdin
        smudge = cat
        required = true
[diff "ipynb"]
        textconv = fastdaemon_client 9998 -- --disp --fname
```
