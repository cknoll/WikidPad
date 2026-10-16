# coding: utf-8
"""Test the full text search of the compact_sqlite database backend."""

import types

import pytest


class _FakeSarOp:
    """Minimal stand-in for SearchReplaceOperation: matches pages containing a word."""

    def __init__(self, needle, textNeeded=True):
        self.needle = needle
        self.textNeeded = textNeeded

    def isTextNeededForTest(self):
        return self.textNeeded

    def testWikiPage(self, word, text):
        return self.needle in (text if self.textNeeded else word)


@pytest.fixture
def wikiData(wx_app):
    import pwiki.sqlite3api as sqlite
    from pwiki.wikidata.compact_sqlite import DbStructure

    connwrap = DbStructure.ConnectWrapSyncCommit(sqlite.connect(":memory:"))
    DbStructure.registerSqliteFunctions(connwrap)
    connwrap.execSql("create table wikiwordcontent (word text, content blob)")
    for word, content in [("PageA", "apple pie"), ("PageB", "banana split"), ("AppleTree", "leaves")]:
        connwrap.execSql("insert into wikiwordcontent values (?, ?)", (word, content.encode("utf-8")))

    yield types.SimpleNamespace(connWrap=connwrap)
    connwrap.close()


def _search(wikiData, sarOp, exclusionSet=frozenset()):
    from pwiki.wikidata.compact_sqlite.WikiData import WikiData

    return WikiData.search(wikiData, sarOp, set(exclusionSet))


def test_search_content(wikiData):
    assert _search(wikiData, _FakeSarOp("apple")) == {"PageA"}


def test_search_word_only(wikiData):
    assert _search(wikiData, _FakeSarOp("Apple", textNeeded=False)) == {"AppleTree"}


def test_search_exclusion_set(wikiData):
    # "p" is contained in PageA and PageB
    assert _search(wikiData, _FakeSarOp("p"), {"PageB"}) == {"PageA"}


def test_search_releases_trans_object(wikiData):
    import pwiki.SqliteThin3 as SqliteThin3

    sarOp = _FakeSarOp("apple")
    _search(wikiData, sarOp)
    assert SqliteThin3.getTransObject(SqliteThin3.llId(sarOp)) is None
