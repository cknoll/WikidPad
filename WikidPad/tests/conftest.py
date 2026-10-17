# coding: utf-8
"""Shared pytest fixtures for WikidPad tests."""

import importlib.util
import os
import sys

import pytest

WIKIDPAD_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _importStarter():
    """
    Import WikidPadStarter from its file (works whether or not WikidPad is
    installed as package). It sets up sys.path like the real application.
    """
    if "WikidPadStarter" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location(
        "WikidPadStarter", os.path.join(WIKIDPAD_DIR, "WikidPadStarter.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["WikidPadStarter"] = module
    spec.loader.exec_module(module)


@pytest.fixture(scope="session")
def wx_app():
    """
    Return a wx.App which provides the methods of WikidPad's MainApp that
    are needed by the tested code (with default settings).

    Tests using this fixture are skipped if no display is available.
    """
    if sys.platform.startswith("linux") and not (
        os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
    ):
        pytest.skip("no display available")

    _importStarter()
    import wx

    class _GlobalConfig:
        def get(self, section, key, default=None):
            return default

    app = wx.GetApp() or wx.App(False)
    if not hasattr(app, "getGlobalConfig"):
        app.getGlobalConfig = _GlobalConfig
        app.isInPortableMode = lambda: False

    return app
