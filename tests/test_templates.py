# -*- coding: utf-8 -*-

from xml.etree import ElementTree

from PIL import Image

from pibooth import pictures
from pibooth.plugins.template_plugin import TemplatePlugin
from pibooth.templates import TemplateItem, TemplateLibrary, is_overlay_template


def test_builtin_templates_contain_every_capture_count(tmpdir):
    styles = ('grid', 'strip', 'genz_neon', 'genz_y2k', 'genz_scrapbook', 'genz_social',
              'kcute_milk', 'kcute_ribbon', 'kcute_check', 'kcute_cloud',
              'kcute_berry', 'kcute_mint', 'kframe_ribbon', 'kframe_peach',
              'kframe_bubble', 'kframe_idol')
    for style in styles:
        path = str(tmpdir.join(style + '.xml'))
        TemplateLibrary._write_builtin(path, style)
        root = ElementTree.parse(path).getroot()
        assert len(list(root.iter('diagram'))) == 8
        for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
            for count in range(1, 5):
                rects = TemplateLibrary._builtin_rects(style, orientation, count)
                assert len(rects) == count
                assert all(width > 0 and height > 0 for _, _, width, height in rects)


def test_kpop_frame_overlay_is_after_capture_cells(tmpdir):
    path = str(tmpdir.join('frame.xml'))
    TemplateLibrary._write_builtin(path, 'kframe_ribbon')
    diagram = next(ElementTree.parse(path).getroot().iter('diagram'))
    vertices = [cell for cell in diagram.iter('mxCell') if cell.get('vertex') == '1']

    assert vertices[0].get('style').startswith('shape=image')   # background
    assert not vertices[1].get('style').startswith('shape=image')  # capture
    assert vertices[-1].get('style').startswith('shape=image')  # transparent frame overlay


def test_only_overlay_frames_force_cover_crop():
    assert is_overlay_template('templates/kpop_frame_ribbon_diary.xml')
    assert is_overlay_template(r'C:\templates\KPOP_FRAME_IDOL_CARD.XML')
    assert not is_overlay_template('templates/kcute_ribbon_club.xml')


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
