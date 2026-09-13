# -*- coding: utf-8 -*-

import pytest

from pibooth.plugins.camera_plugin import CameraPlugin
from pibooth.plugins.view_plugin import ViewPlugin


class ConfigMock(object):

    def __init__(self, preview_flip):
        self.preview_flip = preview_flip

    def getboolean(self, section, option, **kwargs):
        if (section, option) == ('CAMERA', 'preview_flip'):
            return self.preview_flip
        if (section, option) == ('WINDOW', 'always_preview'):
            return True
        raise AssertionError("Unexpected config option {}.{}".format(section, option))


class CameraMock(object):

    def __init__(self):
        self.preview_calls = []

    def preview(self, window, flip=True):
        self.preview_calls.append((window, flip))


class PrinterMock(object):

    @staticmethod
    def is_installed():
        return False


@pytest.mark.parametrize('preview_flip', [True, False])
def test_capture_preview_uses_configured_flip(preview_flip):
    camera = CameraMock()
    app = type('App', (), {'camera': camera, 'capture_date': None})()
    window = object()

    CameraPlugin(None).state_preview_enter(ConfigMock(preview_flip), app, window)

    assert camera.preview_calls == [(window, preview_flip)]


@pytest.mark.parametrize('preview_flip', [True, False])
def test_smart_mirror_preview_uses_configured_flip(preview_flip):
    camera = CameraMock()
    app = type('App', (), {'camera': camera, 'printer': PrinterMock()})()
    window = object()

    ViewPlugin(None).state_wait_enter(ConfigMock(preview_flip), app, window)

    assert camera.preview_calls == [(window, preview_flip)]
