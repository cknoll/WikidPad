# coding: utf-8
"""Test saving an image pasted from the clipboard into the file storage."""

import os

import pytest


@pytest.fixture
def saver_and_storage(wx_app, tmp_path):
    from pwiki.WikiTxtDialogs import ImagePasteSaver
    from pwiki.wikidata.FileStorage import FileStorage

    saver = ImagePasteSaver()
    saver.prefix = "pasted_"
    return saver, FileStorage(None, str(tmp_path))


@pytest.fixture
def image(wx_app):
    import wx

    img = wx.Image(20, 10)
    img.SetRGB(wx.Rect(0, 0, 20, 10), 200, 30, 30)
    return img


@pytest.mark.parametrize("formatNo, suffix", [(1, ".png"), (2, ".jpg")])
def test_save_image(saver_and_storage, image, tmp_path, formatNo, suffix):
    saver, fs = saver_and_storage
    saver.formatNo = formatNo

    path = saver.saveFile(fs, image)

    assert isinstance(path, str)
    assert os.path.isfile(path)
    assert os.path.dirname(path) == str(tmp_path)
    assert path.endswith(suffix)


def test_save_same_image_twice_reuses_file(saver_and_storage, image, tmp_path):
    saver, fs = saver_and_storage
    saver.formatNo = 1

    path1 = saver.saveFile(fs, image)
    path2 = saver.saveFile(fs, image)

    assert path1 == path2
    assert len(os.listdir(tmp_path)) == 1


def test_no_format_saves_nothing(saver_and_storage, image, tmp_path):
    saver, fs = saver_and_storage
    saver.formatNo = 0

    assert saver.saveFile(fs, image) is None
    assert os.listdir(tmp_path) == []
