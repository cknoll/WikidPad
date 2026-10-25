"""
This is a Linux specific file for handling some operations not provided
by the OS-independent wxPython library.
"""

import ctypes, os, traceback, multiprocessing
from ctypes import c_int, c_uint, c_long, c_ulong, c_ushort, c_char, c_char_p, \
        c_wchar_p, c_byte, byref, create_string_buffer, create_unicode_buffer, \
        c_void_p, string_at, sizeof, Structure   # , WindowsError

from . import SystemInfo



libc = ctypes.CDLL('libc.so.6', use_errno=True)


# Based on "bits/sched.h", see e.g. http://code.woboq.org/gcc/include/bits/sched.h.html
# and http://linux.die.net/man/2/sched_setaffinity
try:
    sched_setaffinity = libc.sched_setaffinity
    sched_getaffinity = libc.sched_getaffinity
except:
    import ExceptionLogger
    ExceptionLogger.logOptionalComponentException(
            "Link to sched_setaffinity() in LinuxHacks.py")
    
    sched_setaffinity = None
    sched_getaffinity = None


# int sched_setaffinity(pid_t pid, size_t cpusetsize,
#                       cpu_set_t *mask);

# Naming is based on the C definitions, sometimes with less leading underscores
# than in original code

size_t = c_ulong
_cpu_mask = c_ulong
_CPU_SETSIZE = 1024
_NCPUBITS = 8 * sizeof (_cpu_mask)


class cpu_set_t(Structure):
    _fields_ = [("bits", _cpu_mask*(_CPU_SETSIZE // _NCPUBITS))]



def _getCpuSetTByIndexes(cpuIndexSeq):
    """
    Convert sequence of cpus to a cpu_set_t object with appropriate bits set.
    cpuIndexSeq -- Sequence of integer index numbers of cpu cores (first is 0).
            
    """
    result = cpu_set_t()

    for idx in cpuIndexSeq:
        if idx < 0:
            raise ValueError()
        
        if idx >= _CPU_SETSIZE:
            continue
            
        result.bits[idx // _NCPUBITS] |= 1 << (idx % _NCPUBITS)
    
    return result


def setCpuAffinity(cpuIndexSeq):
    """
    Set affinity of current process to those CPUs listed as sequence of integers
    in the cpuIndexSeq. Numbers equal or higher than getCpuCount() are ignored.
    
    If no valid CPU number is in cpuIndexSeq, function returns False and
    affinity isn't set.
    
    cpuIndexSeq -- Sequence of integer index numbers of cpu cores (first is 0).
    """
    if sched_setaffinity is None:
        return False

    cpuSet = _getCpuSetTByIndexes(cpuIndexSeq)
    
    for v in cpuSet.bits:
        if v != 0:
            break
    else:
        # No processors set
        return False

    result = sched_setaffinity(os.getpid(), sizeof(cpuSet), byref(cpuSet))
    if result == 0:
        return True
    
    return False
    
    # return ctypes.get_errno()


def getCpuAffinity():
    """
    Get affinity of current process as a list of all CPU numbers to which
    the process is assigned.
    
    May return None if something went wrong.
    """
    if sched_getaffinity is None:
        return False
        
    cpuCount = getCpuCount()

    result = []
    cpuSet = cpu_set_t()
    retval = sched_getaffinity(os.getpid(), sizeof(cpuSet), byref(cpuSet))
    if retval != 0:
        # Something went wrong
        return None

    for outer, mask in enumerate(cpuSet.bits):
        for inner in range(_NCPUBITS):
            cpu = outer * _NCPUBITS + inner
            if cpu > cpuCount:
                break

            if (mask & (1 << inner)) != 0:
                result.append(cpu)

    return result


def getCpuCount():
    """
    Returns number of CPUs allowed for the sequence list for setCpuAffinity().
    Highest number in sequence list must be lower than getCpuCount()
    
    The value is system dependent and may be lower than
    the number of available CPUs.
    
    If setting CPU affinity is not supported, function returns 0
    """
    if sched_setaffinity is None:
        return 0

    try:
        return min(_CPU_SETSIZE, multiprocessing.cpu_count())
    except NotImplementedError:
        return 0



# Guard against huge window sizes (wxGTK 3 on X11)
#
# If the window manager sends a ConfigureNotify with a width or height above
# 32767 to a toplevel window (e.g. KWin computes a negative size for a maximized
# window while no monitor is connected during suspend, which wraps around to
# about 65500), GDK passes this size to the cairo-xlib surface it caches for the
# window. Cairo rejects the size and puts the surface permanently into the error
# state CAIRO_STATUS_INVALID_SIZE. From then on nothing is painted into the window
# anymore, it stays empty when shown again. GDK creates this surface only once
# per window, so the window can't be repaired afterwards, only a restart helps.
# Therefore such sizes are clamped before GDK processes the event.

_XLIB_COORD_MAX = 32767  # Largest surface size accepted by cairo-xlib
_X_CONFIGURE_NOTIFY = 22
_GDK_FILTER_CONTINUE = 0


class _XConfigureEvent(Structure):
    _fields_ = [
        ("type", c_int),
        ("serial", c_ulong),
        ("send_event", c_int),
        ("display", c_void_p),
        ("event", c_ulong),
        ("window", c_ulong),
        ("x", c_int),
        ("y", c_int),
        ("width", c_int),
        ("height", c_int),
        ("border_width", c_int),
        ("above", c_ulong),
        ("override_redirect", c_int),
        ]


# GdkFilterReturn (*GdkFilterFunc) (GdkXEvent *xevent, GdkEvent *event,
#         gpointer data);
_GdkFilterFunc = ctypes.CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)


def _clampConfigureSize(xevent, event, data):
    # Called for each X event of the window, so check the type cheaply first
    if c_int.from_address(xevent).value == _X_CONFIGURE_NOTIFY:
        configureEvent = _XConfigureEvent.from_address(xevent)
        if configureEvent.width > _XLIB_COORD_MAX:
            configureEvent.width = _XLIB_COORD_MAX
        if configureEvent.height > _XLIB_COORD_MAX:
            configureEvent.height = _XLIB_COORD_MAX

    return _GDK_FILTER_CONTINUE


# Must be referenced as long as filters using it are installed
_clampConfigureSizeFilter = _GdkFilterFunc(_clampConfigureSize)


def installWindowSizeGuard(window):
    """
    Protect the toplevel window against window sizes which would prevent it
    from being painted ever again (see above).

    Returns True if the guard was installed, False if it isn't needed or
    supported (not wxGTK 3 or not running on X11).
    """
    import wx

    if "gtk3" not in wx.PlatformInfo or not hasattr(window, "GetGtkWidget"):
        return False

    try:
        gobjectLib = ctypes.CDLL("libgobject-2.0.so.0")
        gdkLib = ctypes.CDLL("libgdk-3.so.0")
        gtkLib = ctypes.CDLL("libgtk-3.so.0")
    except OSError:
        return False

    gtkLib.gtk_widget_get_window.restype = c_void_p
    gtkLib.gtk_widget_get_window.argtypes = [c_void_p]
    gdkLib.gdk_x11_window_get_type.restype = ctypes.c_size_t
    gdkLib.gdk_x11_window_get_type.argtypes = []
    gobjectLib.g_type_check_instance_is_a.restype = c_int
    gobjectLib.g_type_check_instance_is_a.argtypes = [c_void_p, ctypes.c_size_t]
    gdkLib.gdk_window_add_filter.restype = None
    gdkLib.gdk_window_add_filter.argtypes = [c_void_p, _GdkFilterFunc, c_void_p]

    gdkWindow = gtkLib.gtk_widget_get_window(int(window.GetGtkWidget()))
    if not gdkWindow or not gobjectLib.g_type_check_instance_is_a(gdkWindow,
            gdkLib.gdk_x11_window_get_type()):
        # Not realized or not X11 (e.g. Wayland)
        return False

    gdkLib.gdk_window_add_filter(gdkWindow, _clampConfigureSizeFilter, None)
    return True


