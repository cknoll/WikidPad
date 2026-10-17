# coding: utf-8
"""
Load every top-level object of WikidPad.xrc and check that wxWidgets
reports no errors (they would be shown to the user in an error box when
the dialog is opened for the first time).
"""

import os
import re

import pytest

XRC_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "WikidPad.xrc")


def _topLevelObjects():
    with open(XRC_PATH, encoding="utf-8") as f:
        # top-level objects are indented by exactly two spaces
        return re.findall(r'^  <object class="(\w+)" name="(\w+)"', f.read(), re.M)


@pytest.fixture(scope="module")
def xrcLoader(wx_app):
    import wx
    import wx.xrc

    class CollectLog(wx.Log):
        def __init__(self):
            super().__init__()
            self.msgs = []

        def DoLogTextAtLevel(self, level, msg):
            if level <= wx.LOG_Warning:
                self.msgs.append(msg)

    log = CollectLog()
    oldLog = wx.Log.SetActiveTarget(log)
    res = wx.xrc.XmlResource(XRC_PATH)
    parent = wx.Frame(None)

    loaders = {
        "wxDialog": lambda name: res.LoadDialog(parent, name),
        "wxFrame": lambda name: res.LoadFrame(parent, name),
        "wxPanel": lambda name: res.LoadPanel(parent, name),
        "wxMenuBar": lambda name: res.LoadMenuBar(name),
        "wxMenu": lambda name: res.LoadMenu(name),
    }

    yield loaders, log

    parent.Destroy()
    wx.Log.SetActiveTarget(oldLog)


@pytest.mark.parametrize("cls, name", _topLevelObjects())
def test_load_without_errors(xrcLoader, cls, name):
    loaders, log = xrcLoader
    if cls not in loaders:
        pytest.skip("no loader for " + cls)

    del log.msgs[:]
    obj = loaders[cls](name)

    assert obj is not None
    if hasattr(obj, "Destroy"):
        obj.Destroy()
    assert log.msgs == []
