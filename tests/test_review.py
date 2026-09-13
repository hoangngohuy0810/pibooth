# -*- coding: utf-8 -*-

from PIL import Image

from pibooth.plugins.view_plugin import ViewPlugin


class ConfigMock(object):

    def getboolean(self, section, option):
        assert (section, option) == ('WINDOW', 'review_picture')
        return True

    def get(self, section, option):
        assert (section, option) == ('WINDOW', 'review_picture_text')
        return 'Review'


class WindowMock(object):

    review = None

    def show_review(self, image, text):
        self.review = (image, text)


class AppMock(object):

    previous_picture = Image.new('RGB', (20, 20))
    leave_review = False

    def find_review_event(self, events):
        return events[0] if self.leave_review and events else None


def test_review_waits_for_explicit_continue():
    plugin = ViewPlugin(None)
    app = AppMock()
    window = WindowMock()

    plugin.state_finish_enter(ConfigMock(), app, window)
    assert window.review == (app.previous_picture, 'Review')
    assert plugin.state_finish_validate(app, ['click']) is None

    app.leave_review = True
    assert plugin.state_finish_validate(app, ['click']) == 'wait'
