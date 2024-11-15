from __future__ import annotations as _annotations

import sys
from types import CodeType, FrameType, TracebackType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .find_examples import CodeExample


def create_example_traceback(exc: Exception, module_path: str, example: CodeExample) -> TracebackType | None:
    """Create a new traceback with the filename and line numbers altered to match `example`.

    This involves lots of horrible hacking, but (somewhat miraculously) seems to work.

    Frames outside the example are not included in the new traceback.
    """
    frames = []
    tb = exc.__traceback__
    while tb is not None:
        frame = tb.tb_frame
        if frame.f_code.co_filename == module_path:
            frames.append((create_custom_frame(frame, example), tb.tb_lasti, tb.tb_lineno + example.start_line))
        tb = tb.tb_next

    frames.reverse()
    new_tb = None
    for altered_frame, lasti, lineno in frames:
        new_tb = TracebackType(tb_next=new_tb, tb_frame=altered_frame, tb_lasti=lasti, tb_lineno=lineno)
    return new_tb


def create_custom_frame(frame: FrameType, example: CodeExample) -> FrameType:
    """Create a new frame that mostly matches `frame` but with filename and line number faked.

    Create a new frame that mostly matches `frame` but with a code object that has
    a filename from `example` and adjusted first line number
    so that pytest shows the correct code context in the traceback.

    Taken mostly from https://naleraphael.github.io/blog/posts/devlog_create_a_builtin_frame_object/
    With the CodeType creation inspired by https://stackoverflow.com/a/16123158/949890.
    """
    import ctypes

    P_SIZE = ctypes.sizeof(ctypes.c_void_p)
    IS_X64 = P_SIZE == 8

    P_MEM_TYPE = ctypes.POINTER(ctypes.c_ulong if IS_X64 else ctypes.c_uint)

    ctypes.pythonapi.PyFrame_New.argtypes = (
        P_MEM_TYPE,  # PyThreadState *tstate
        P_MEM_TYPE,  # PyCodeObject *code
        ctypes.py_object,  # PyObject *globals
        ctypes.py_object,  # PyObject *locals
    )
    ctypes.pythonapi.PyFrame_New.restype = ctypes.py_object  # PyFrameObject*

    ctypes.pythonapi.PyThreadState_Get.argtypes = None  # type: ignore
    ctypes.pythonapi.PyThreadState_Get.restype = P_MEM_TYPE

    f_code = frame.f_code
    if sys.version_info >= (3, 12):
        code = CodeType(
            f_code.co_argcount,
            f_code.co_posonlyargcount,
            f_code.co_kwonlyargcount,
            f_code.co_nlocals,
            f_code.co_stacksize,
            f_code.co_flags,
            f_code.co_code,
            f_code.co_consts,
            f_code.co_names,
            f_code.co_varnames,
            str(example.path),
            f_code.co_name,
            f_code.co_qualname,
            f_code.co_firstlineno + example.start_line,
            f_code.co_linetable,
            f_code.co_exceptiontable,
        )
    elif sys.version_info >= (3, 11):
        code = CodeType(
            f_code.co_argcount,
            f_code.co_posonlyargcount,
            f_code.co_kwonlyargcount,
            f_code.co_nlocals,
            f_code.co_stacksize,
            f_code.co_flags,
            f_code.co_code,
            f_code.co_consts,
            f_code.co_names,
            f_code.co_varnames,
            str(example.path),
            f_code.co_name,
            f_code.co_qualname,
            f_code.co_firstlineno + example.start_line,
            f_code.co_lnotab,
            f_code.co_exceptiontable,
        )
    else:
        code = CodeType(
            f_code.co_argcount,
            f_code.co_posonlyargcount,
            f_code.co_kwonlyargcount,
            f_code.co_nlocals,
            f_code.co_stacksize,
            f_code.co_flags,
            f_code.co_code,
            f_code.co_consts,
            f_code.co_names,
            f_code.co_varnames,
            str(example.path),
            f_code.co_name,
            f_code.co_firstlineno + example.start_line,
            f_code.co_lnotab,
        )

    return ctypes.pythonapi.PyFrame_New(
        ctypes.pythonapi.PyThreadState_Get(),  # thread state
        ctypes.cast(id(code), P_MEM_TYPE),  # a code object
        frame.f_globals,  # a dict of globals
        frame.f_locals,  # a dict of locals
    )
