# coding: utf-8
"""Test focus handling of DocPagePresenter (without creating a real presenter)."""

import sys
import types

import pytest


def _processPendingCalls(app):
    import wx

    # run the wx.CallAfter() calls
    app.ProcessPendingEvents()
    wx.SafeYield()


@pytest.fixture
def frame(wx_app):
    import wx

    frame = wx.Frame(None)
    yield frame
    frame.Destroy()


@pytest.fixture
def exceptions(monkeypatch):
    """Collect exceptions raised in wx event handlers (incl. wx.CallAfter calls)."""
    collected = []
    monkeypatch.setattr(sys, "excepthook", lambda typ, value, tb: collected.append(value))
    return collected


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SetFocus uses wx.CallAfter on Linux only")
def test_setfocus_on_control_destroyed_meanwhile(wx_app, frame, exceptions):
    import wx
    from pwiki.DocPagePresenter import DocPagePresenter

    ctrl = wx.TextCtrl(frame)
    presenter = types.SimpleNamespace(subControls={"textedit": ctrl}, lastVisibleCtrlName="textedit")

    DocPagePresenter.SetFocus(presenter)
    ctrl.Destroy()
    _processPendingCalls(wx_app)

    assert exceptions == []


@pytest.mark.skipif(not sys.platform.startswith("linux"), reason="SetFocus uses wx.CallAfter on Linux only")
def test_setfocus_sets_focus(wx_app, frame, exceptions, monkeypatch):
    import wx
    from pwiki.DocPagePresenter import DocPagePresenter

    ctrl = wx.TextCtrl(frame)
    focused = []
    monkeypatch.setattr(wx.TextCtrl, "SetFocus", lambda self: focused.append(self))
    presenter = types.SimpleNamespace(subControls={"textedit": ctrl}, lastVisibleCtrlName="textedit")

    DocPagePresenter.SetFocus(presenter)
    _processPendingCalls(wx_app)

    assert focused == [ctrl]
    assert exceptions == []
