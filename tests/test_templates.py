# -*- coding: utf-8 -*-

from xml.etree import ElementTree

from PIL import Image

from pibooth import pictures
from pibooth.plugins.template_plugin import TemplatePlugin
from pibooth.templates import TemplateItem, TemplateLibrary


def test_builtin_templates_contain_every_capture_count(tmpdir):
    for style in ('grid', 'strip'):
        path = str(tmpdir.join(style + '.xml'))
        TemplateLibrary._write_builtin(path, style)
        root = ElementTree.parse(path).getroot()
        assert len(list(root.iter('diagram'))) == 8
        for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
            for count in range(1, 5):
                rects = TemplateLibrary._builtin_rects(style, orientation, count)
                assert len(rects) == count
                assert all(width > 0 and height > 0 for _, _, width, height in rects)


def test_template_plugin_cycles_and_activates_selection():
    class Library(object):
        def __init__(self):
            self.selected = None

        def activate(self, index):
            self.selected = index

    class App(object):
        template_choices = [TemplateItem('one.xml', 'One', Image.new('RGB', (10, 10))),
                            TemplateItem('two.xml', 'Two', Image.new('RGB', (10, 10)))]
        template_index = 0
        template_confirmed = False
        template_library = Library()

        @staticmethod
        def find_template_event(events):
            return events[0]

    class Window(object):
        shown = []

        def show_template(self, preview, name, index, total):
            self.shown.append((name, index, total))

    app = App()
    win = Window()
    plugin = TemplatePlugin(None)

    plugin.state_template_do(app, win, ['next'])
    assert app.template_index == 1
    assert win.shown[-1] == ('Two', 2, 2)

    plugin.state_template_do(app, win, ['confirm'])
    assert app.template_library.selected == 1
    assert app.template_confirmed is True
