# Voice lab - round 2 (less like AI)

Text: Okay, so here's something nobody tells you about packing for a beach trip. You don't need ten outfits. You need three, and one really good hat. We tried it last summer, and honestly? It changed everything. Less stuff, more time in the water. Would you try it? Let me know in the comments!

Every file: voice-over finishing: silence trimmed (0.25 s lead, 0.6 s tail), high-pass 70 Hz, a small dark room mixed 20 dB under the voice, a faint room tone 55 dB under it instead of digital silence, gentle compression (2.5:1), de-essing, loudness -16 LUFS, 44.1 kHz.

| letter | words wrong | seconds | pitch Hz | pitch moves (semitones) |
|---|---|---|---|---|
| G | 0 | 19.12 | 252.4 | 4.77 |
| H | 0 | 20.0 | 275.2 | 4.49 |
| I | 0 | 17.04 | 239.6 | 4.57 |
| J | 0 | 19.16 | 283.3 | 4.66 |

music_<letter>.mp3: the same voice over music - Flutey Funk (ISRC USUAN1100519).mp3 by Kevin MacLeod (incompetech.com), CC BY 3.0 (https://commons.wikimedia.org/wiki/File:Flutey_Funk_(ISRC_USUAN1100519).mp3).

Which letter is which: results.json -> blind.

Failed takes:
- voxcpm_locked_t1: RuntimeError: Failed to create AudioDecoder for /home/runner/work/_temp/r1/reference_locked_voice.wav: Could not load libtorchcodec. Likely causes:
          1. FFmpeg is not properly installed in your environment. We support
             versions 4, 5, 6, 7, 8, and 9, and we attempt to load libtorchcodec
             for each of those versions. Errors for versions not installed on
             your system are expected; only the error for your installed FFmpeg
             version is relevant. On Windows, ensure you've installed the
             "full-shared" version which ships DLLs.
          2. The PyTorch version (2.14.1+cpu) is not compatible with
             this version of TorchCodec. Refer to the version compatibility
             table:
             https://github.com/pytorch/torchcodec?tab=readme-ov-file#installing-torchcodec.
          3. Another runtime dependency; see exceptions below.

        The following exceptions were raised as we tried to load libtorchcodec:
        
[start of libtorchcodec loading traceback]
FFmpeg version 9:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.61: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core9.so

FFmpeg version 8:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.60: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core8.so

FFmpeg version 7:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.59: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core7.so

FFmpeg version 6:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.58: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core6.so

FFmpeg version 5:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.57: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core5.so

FFmpeg version 4:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.56: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core4.so
[end of libtorchcodec loading traceback].
- voxcpm_locked_t2: RuntimeError: Failed to create AudioDecoder for /home/runner/work/_temp/r1/reference_locked_voice.wav: Could not load libtorchcodec. Likely causes:
          1. FFmpeg is not properly installed in your environment. We support
             versions 4, 5, 6, 7, 8, and 9, and we attempt to load libtorchcodec
             for each of those versions. Errors for versions not installed on
             your system are expected; only the error for your installed FFmpeg
             version is relevant. On Windows, ensure you've installed the
             "full-shared" version which ships DLLs.
          2. The PyTorch version (2.14.1+cpu) is not compatible with
             this version of TorchCodec. Refer to the version compatibility
             table:
             https://github.com/pytorch/torchcodec?tab=readme-ov-file#installing-torchcodec.
          3. Another runtime dependency; see exceptions below.

        The following exceptions were raised as we tried to load libtorchcodec:
        
[start of libtorchcodec loading traceback]
FFmpeg version 9:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.61: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core9.so

FFmpeg version 8:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.60: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core8.so

FFmpeg version 7:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.59: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core7.so

FFmpeg version 6:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.58: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core6.so

FFmpeg version 5:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.57: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core5.so

FFmpeg version 4:
Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1587, in load_library
    ctypes.CDLL(path)
  File "/opt/hostedtoolcache/Python/3.11.17/x64/lib/python3.11/ctypes/__init__.py", line 376, in __init__
    self._handle = _dlopen(self._name, mode)
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
OSError: libavutil.so.56: cannot open shared object file: No such file or directory

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/_internally_replaced_utils.py", line 132, in load_core_libraries
    torch.ops.load_library(core_library_path)
  File "/home/runner/work/_temp/v/lib/python3.11/site-packages/torch/_ops.py", line 1589, in load_library
    raise OSError(f"Could not load this library: {path}") from e
OSError: Could not load this library: /home/runner/work/_temp/v/lib/python3.11/site-packages/torchcodec/libtorchcodec_core4.so
[end of libtorchcodec loading traceback].
