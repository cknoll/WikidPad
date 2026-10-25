# coding: utf-8
"""
Test that a ConfigureNotify with a huge size (e.g. sent by KWin during suspend)
doesn't break painting of a toplevel window permanently (wxGTK 3 on X11).
"""

import ctypes
import sys
import time

import pytest

pytestmark = pytest.mark.skipif(not sys.platform.startswith("linux"), reason="X11 only")

ConfigureNotify = 22
StructureNotifyMask = 1 << 17
CAIRO_STATUS_SUCCESS = 0


class XConfigureEvent(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_int),
        ("serial", ctypes.c_ulong),
        ("send_event", ctypes.c_int),
        ("display", ctypes.c_void_p),
        ("event", ctypes.c_ulong),
        ("window", ctypes.c_ulong),
        ("x", ctypes.c_int),
        ("y", ctypes.c_int),
        ("width", ctypes.c_int),
        ("height", ctypes.c_int),
        ("border_width", ctypes.c_int),
        ("above", ctypes.c_ulong),
        ("override_redirect", ctypes.c_int),
    ]


class XEvent(ctypes.Union):
    _fields_ = [("xconfigure", XConfigureEvent), ("pad", ctypes.c_long * 24)]


@pytest.fixture
def libs():
    gdk = ctypes.CDLL("libgdk-3.so.0")
    gtk = ctypes.CDLL("libgtk-3.so.0")
    cairo = ctypes.CDLL("libcairo.so.2")
    x11 = ctypes.CDLL("libX11.so.6")

    gtk.gtk_widget_get_window.restype = ctypes.c_void_p
    gtk.gtk_widget_get_window.argtypes = [ctypes.c_void_p]
    gdk.gdk_x11_window_get_xid.restype = ctypes.c_ulong
    gdk.gdk_x11_window_get_xid.argtypes = [ctypes.c_void_p]
    gdk.gdk_cairo_create.restype = ctypes.c_void_p
    gdk.gdk_cairo_create.argtypes = [ctypes.c_void_p]
    cairo.cairo_status.argtypes = [ctypes.c_void_p]
    cairo.cairo_destroy.argtypes = [ctypes.c_void_p]
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]
    x11.XSendEvent.argtypes = [ctypes.c_void_p, ctypes.c_ulong, ctypes.c_int, ctypes.c_long,
                               ctypes.POINTER(XEvent)]
    x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]

    return gdk, gtk, cairo, x11


@pytest.fixture
def frame(wx_app):
    import wx

    if "gtk3" not in wx.PlatformInfo:
        pytest.skip("wxGTK 3 only")

    frame = wx.Frame(None, size=(400, 300))
    frame.Show()
    _waitFor(lambda: frame.IsShown())
    yield frame
    frame.Destroy()


def _waitFor(condition, timeout=2.0):
    import wx

    end = time.time() + timeout
    while time.time() < end:
        wx.GetApp().Yield(True)
        if condition():
            return True
        time.sleep(0.01)
    return False


def _sendConfigureNotify(x11, xid, width, height):
    dpy = x11.XOpenDisplay(None)
    ev = XEvent()
    c = ev.xconfigure
    c.type = ConfigureNotify
    c.send_event = 1
    c.display = dpy
    c.event = c.window = xid
    c.width, c.height = width, height
    x11.XSendEvent(dpy, xid, 0, StructureNotifyMask, ctypes.byref(ev))
    x11.XSync(dpy, 0)
    x11.XCloseDisplay(dpy)


def _surfaceStatus(gdk, cairo, gdkWindow):
    cr = gdk.gdk_cairo_create(gdkWindow)
    status = cairo.cairo_status(cr)
    cairo.cairo_destroy(cr)
    return status


def test_huge_configure_size_does_not_break_painting(frame, libs):
    from pwiki import LinuxHacks

    gdk, gtk, cairo, x11 = libs
    if not LinuxHacks.installWindowSizeGuard(frame):
        pytest.skip("not running on X11")

    gdkWindow = gtk.gtk_widget_get_window(int(frame.GetGtkWidget()))
    xid = gdk.gdk_x11_window_get_xid(gdkWindow)
    width = frame.GetSize()[0]

    # A WM computing the height -29 sends 65507 (unsigned 16 bit)
    _sendConfigureNotify(x11, xid, width, 65507)
    assert _waitFor(lambda: frame.GetSize()[1] != 300)
    # Without the guard cairo reports CAIRO_STATUS_INVALID_SIZE (32) from now on
    assert _surfaceStatus(gdk, cairo, gdkWindow) == CAIRO_STATUS_SUCCESS
    assert frame.GetSize()[1] == 32767

    _sendConfigureNotify(x11, xid, width, 300)
    assert _waitFor(lambda: frame.GetSize()[1] == 300)
    assert _surfaceStatus(gdk, cairo, gdkWindow) == CAIRO_STATUS_SUCCESS
