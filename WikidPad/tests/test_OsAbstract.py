# coding: utf-8
"""
Test the file operations of OsAbstract (on Windows they are implemented
by WindowsHacks via SHFileOperationW).
"""

import os

import pytest


@pytest.fixture
def osAbstract(wx_app):
    from pwiki import OsAbstract

    return OsAbstract


@pytest.fixture
def srcFile(tmp_path):
    path = tmp_path / "src.txt"
    path.write_text("content")
    return str(path)


def test_copy_file(osAbstract, srcFile, tmp_path):
    dstPath = str(tmp_path / "newdir" / "dst.txt")

    osAbstract.copyFile(srcFile, dstPath)

    assert os.path.isfile(srcFile)
    with open(dstPath) as f:
        assert f.read() == "content"


def test_move_file(osAbstract, srcFile, tmp_path):
    dstPath = str(tmp_path / "newdir" / "dst.txt")

    osAbstract.moveFile(srcFile, dstPath)

    assert not os.path.exists(srcFile)
    with open(dstPath) as f:
        assert f.read() == "content"


def test_delete_file(osAbstract, srcFile):
    osAbstract.deleteFile(srcFile)

    assert not os.path.exists(srcFile)
