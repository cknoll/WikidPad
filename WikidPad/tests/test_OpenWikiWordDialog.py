# coding: utf-8
"""Test closing logic of OpenWikiWordDialog (without creating a real dialog)."""

import pytest


class _FakeDialog:
    """Provides what OpenWikiWordDialog._activateAndClose() needs."""

    def __init__(self, reenter=False):
        from pwiki.AdditionalDialogs import OpenWikiWordDialog

        self._impl = OpenWikiWordDialog._activateAndClose
        self.activating = False
        self.modal = True
        self.reenter = reenter
        self.activated = 0
        self.endModalCalls = 0

    def _activateAndClose(self, tabMode):
        return self._impl(self, tabMode)

    def IsModal(self):
        return self.modal

    def EndModal(self, retCode):
        if not self.modal:
            raise AssertionError("EndModal called twice")
        self.modal = False
        self.endModalCalls += 1

    def activateSelectedWikiWords(self, tabMode):
        self.activated += 1
        if self.reenter:
            # a second OK event processed while the page is activated
            self._activateAndClose(tabMode)
        return True


def test_ok_closes_dialog(wx_app):
    dlg = _FakeDialog()
    dlg._activateAndClose(0)
    assert (dlg.activated, dlg.endModalCalls) == (1, 1)


def test_reentrant_ok_ends_modal_once(wx_app):
    dlg = _FakeDialog(reenter=True)
    dlg._activateAndClose(0)
    assert (dlg.activated, dlg.endModalCalls) == (1, 1)
    assert not dlg.activating


def test_ok_after_close_is_ignored(wx_app):
    dlg = _FakeDialog()
    dlg._activateAndClose(0)
    dlg._activateAndClose(0)
    assert (dlg.activated, dlg.endModalCalls) == (1, 1)
