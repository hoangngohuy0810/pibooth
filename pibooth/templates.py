# -*- coding: utf-8 -*-

"""Template discovery, preview generation and activation.

This module deliberately treats ``pibooth-picture-template`` as an optional
runtime dependency.  The core application keeps working when the plugin is not
installed or is disabled.
"""

import os
import os.path as osp
from dataclasses import dataclass
from xml.etree import ElementTree

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from pibooth import pictures
from pibooth.utils import LOGGER


@dataclass(frozen=True)
class TemplateItem(object):
    """A template ready to be displayed in the chooser."""

    path: str
    name: str
    preview: Image.Image


class TemplateLibrary(object):
    """Discover and preview XML templates handled by the optional plugin."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.items = []
        self._cache = {}
        self._api = self._load_plugin_api()

    @staticmethod
    def _load_plugin_api():
        try:
            from pibooth_picture_template import TemplateParser, TemplatePictureFactory
            return TemplateParser, TemplatePictureFactory
        except (ImportError, ModuleNotFoundError):
            return None

    @property
    def available(self):
        """Whether the picture-template plugin and its option are available."""
        if not self._api:
            return False
        try:
            self.cfg.get('PICTURE', 'template')
        except (KeyError, ValueError):
            return False
        return True

    def _configured_path(self):
        try:
            return self.cfg.getpath('PICTURE', 'template')
        except (KeyError, ValueError):
            return ''

    def _candidate_paths(self):
        self._ensure_builtin_templates()
        configured = self._configured_path()
        folders = {self.cfg.join_path('templates')}
        if configured:
            folders.add(osp.dirname(configured))

        paths = []
        if configured and osp.isfile(configured):
            paths.append(osp.abspath(configured))

        for folder in sorted(folders):
            if not osp.isdir(folder):
                continue
            for filename in sorted(os.listdir(folder), key=str.casefold):
                path = osp.abspath(osp.join(folder, filename))
                if filename.lower().endswith('.xml') and osp.isfile(path) and path not in paths:
                    paths.append(path)
        return paths

    def _ensure_builtin_templates(self):
        """Create a small starter library without overwriting user files."""
        folder = self.cfg.join_path('templates')
        definitions = {
            'pibooth_modern_grid.xml': 'grid',
            'pibooth_photo_strip.xml': 'strip',
        }
        try:
            os.makedirs(folder, exist_ok=True)
            for filename, style in definitions.items():
                path = osp.join(folder, filename)
                if not osp.isfile(path):
                    self._write_builtin(path, style)
        except OSError as exc:
            LOGGER.warning("Could not create built-in template library: %s", exc)

    @classmethod
    def _write_builtin(cls, path, style):
        mxfile = ElementTree.Element('mxfile')
        for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
            page_w, page_h = ((400, 600) if orientation == pictures.PORTRAIT else (600, 400))
            for count in range(1, 5):
                diagram = ElementTree.SubElement(
                    mxfile, 'diagram', name='{} {} {}'.format(style, orientation, count))
                model = ElementTree.SubElement(
                    diagram, 'mxGraphModel', pageWidth=str(page_w), pageHeight=str(page_h))
                root = ElementTree.SubElement(model, 'root')
                ElementTree.SubElement(root, 'mxCell', id='0', dpi='300')
                ElementTree.SubElement(root, 'mxCell', id='1', parent='0')
                for index, (x, y, width, height) in enumerate(
                        cls._builtin_rects(style, orientation, count), start=1):
                    cell = ElementTree.SubElement(root, 'mxCell', id=str(index + 1),
                                                  value=str(index), vertex='1', parent='1',
                                                  style='rounded=1;')
                    ElementTree.SubElement(cell, 'mxGeometry', x=str(x), y=str(y),
                                           width=str(width), height=str(height), **{'as': 'geometry'})
        ElementTree.ElementTree(mxfile).write(path, encoding='utf-8', xml_declaration=True)

    @staticmethod
    def _builtin_rects(style, orientation, count):
        portrait = orientation == pictures.PORTRAIT
        if style == 'grid':
            if portrait:
                layouts = {
                    1: ((30, 40, 340, 500),),
                    2: ((30, 35, 340, 245), (30, 300, 340, 245)),
                    3: ((30, 25, 340, 165), (30, 210, 340, 165), (30, 395, 340, 165)),
                    4: ((25, 45, 165, 235), (210, 45, 165, 235),
                        (25, 310, 165, 235), (210, 310, 165, 235)),
                }
            else:
                layouts = {
                    1: ((45, 30, 510, 340),),
                    2: ((35, 35, 255, 330), (310, 35, 255, 330)),
                    3: ((25, 45, 170, 310), (215, 45, 170, 310), (405, 45, 170, 310)),
                    4: ((45, 25, 235, 165), (320, 25, 235, 165),
                        (45, 210, 235, 165), (320, 210, 235, 165)),
                }
        else:
            if portrait:
                height = (520 - (count - 1) * 14) // count
                layouts = {count: tuple((75, 35 + i * (height + 14), 250, height)
                                         for i in range(count))}
            else:
                width = (520 - (count - 1) * 14) // count
                layouts = {count: tuple((35 + i * (width + 14), 70, width, 260)
                                         for i in range(count))}
        return layouts[count]

    @staticmethod
    def _display_name(path):
        name = osp.splitext(osp.basename(path))[0]
        return name.replace('_', ' ').replace('-', ' ').strip().title()

    @staticmethod
    def _placeholder(index, portrait):
        size = (900, 1200) if portrait else (1200, 900)
        colors = ((54, 138, 230), (238, 107, 95), (66, 184, 131), (245, 174, 66))
        image = Image.new('RGB', size, colors[index % len(colors)])
        draw = ImageDraw.Draw(image)
        step = max(20, min(size) // 10)
        for offset in range(-size[1], size[0], step * 2):
            draw.line((offset, 0, offset + size[1], size[1]), fill=(255, 255, 255), width=step // 2)
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        radius = min(size) // 7
        center = (size[0] // 2, size[1] // 2)
        overlay_draw.ellipse((center[0] - radius, center[1] - radius,
                              center[0] + radius, center[1] + radius), fill=(0, 0, 0, 150))
        font = ImageFont.load_default(size=max(36, radius))
        label = str(index + 1)
        bbox = overlay_draw.textbbox((0, 0), label, font=font)
        overlay_draw.text((center[0] - (bbox[2] - bbox[0]) // 2,
                           center[1] - (bbox[3] - bbox[1]) // 2),
                          label, fill='white', font=font)
        return Image.alpha_composite(image.convert('RGBA'), overlay).convert('RGB')

    def _select_orientation(self, parser, capture_number):
        configured = self.cfg.get('PICTURE', 'orientation')
        if configured in parser.data and capture_number in parser.data[configured]:
            return configured
        if configured != pictures.AUTO:
            return None
        capture_orientation = self._capture_orientation(capture_number)
        if capture_orientation:
            for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
                if orientation in parser.data and capture_number in parser.data[orientation]:
                    data = parser.data[orientation][capture_number]
                    if data.get('captures_orientation') == capture_orientation:
                        return orientation
        for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
            if orientation in parser.data and capture_number in parser.data[orientation]:
                return orientation
        return None

    def _capture_orientation(self, capture_number):
        """Estimate the captured image orientation for an accurate auto preview."""
        try:
            width, height = self.cfg.gettyped('CAMERA', 'resolution')
            choices = self.cfg.gettuple('PICTURE', 'captures', int)
            rotations = self.cfg.gettuple('CAMERA', 'rotation', int, 2)
            rotation = rotations[choices.index(capture_number)] % 180
            if rotation == 90:
                width, height = height, width
            return pictures.PORTRAIT if width < height else pictures.LANDSCAPE
        except (IndexError, TypeError, ValueError, KeyError):
            return None

    def _get_background(self, capture_number):
        try:
            choices = self.cfg.gettuple('PICTURE', 'captures', int)
            index = choices.index(capture_number)
            return self.cfg.gettuple('PICTURE', 'backgrounds', ('color', 'path'), 2)[index]
        except (IndexError, ValueError, KeyError):
            return (255, 255, 255)

    def _get_overlay(self, capture_number):
        try:
            choices = self.cfg.gettuple('PICTURE', 'captures', int)
            index = choices.index(capture_number)
            return self.cfg.gettuple('PICTURE', 'overlays', 'path', 2)[index]
        except (IndexError, ValueError, KeyError):
            return ''

    def _build_preview(self, path, capture_number):
        parser_class, factory_class = self._api
        parser = parser_class(path)
        for choice in self.cfg.gettuple('PICTURE', 'captures', int):
            if not self._select_orientation(parser, choice):
                raise ValueError("no layout for configured capture count {}".format(choice))
        orientation = self._select_orientation(parser, capture_number)
        if not orientation:
            raise ValueError("no layout for {} captures".format(capture_number))

        data = parser.data[orientation][capture_number]
        portrait = data.get('captures_orientation') == pictures.PORTRAIT
        captures = [self._placeholder(i, portrait) for i in range(capture_number)]
        factory = factory_class(parser, orientation, *captures)
        factory.set_background(self._get_background(capture_number))
        overlay = self._get_overlay(capture_number)
        if overlay and osp.isfile(overlay):
            factory.set_overlay(overlay)
        try:
            factory.set_cropping(self.cfg.getboolean('PICTURE', 'captures_cropping'))
        except (KeyError, ValueError):
            pass
        preview = factory.build().convert('RGB')
        preview.thumbnail((900, 650), Resampling.LANCZOS)
        return preview

    def refresh(self, capture_number):
        """Refresh compatible templates for the selected capture count."""
        self.items = []
        if not self.available or not capture_number:
            return self.items

        orientation = self.cfg.get('PICTURE', 'orientation')
        for path in self._candidate_paths():
            try:
                cache_key = (path, os.path.getmtime(path), capture_number, orientation,
                             self._capture_orientation(capture_number),
                             repr(self._get_background(capture_number)), self._get_overlay(capture_number))
                preview = self._cache.get(cache_key)
                if preview is None:
                    preview = self._build_preview(path, capture_number)
                    self._cache[cache_key] = preview
                self.items.append(TemplateItem(path, self._display_name(path), preview))
            except Exception as exc:  # A malformed template must not crash the booth
                LOGGER.warning("Ignore template '%s': %s", path, exc)
        return self.items

    def current_index(self):
        configured = osp.normcase(osp.abspath(self._configured_path())) if self._configured_path() else ''
        for index, item in enumerate(self.items):
            if osp.normcase(item.path) == configured:
                return index
        return 0

    def activate(self, index):
        """Use and persist the selected template for the next picture factory."""
        item = self.items[index]
        old_path = self._configured_path()
        self.cfg.set('PICTURE', 'template', item.path)

        # pibooth-picture-template caches its parser directly on the config object.
        # It must be cleared so the next capture uses the newly selected XML file.
        if hasattr(self.cfg, 'template'):
            delattr(self.cfg, 'template')

        if osp.normcase(osp.abspath(old_path)) != osp.normcase(item.path):
            try:
                self.cfg.save()
            except OSError as exc:
                LOGGER.warning("Template selection could not be saved: %s", exc)
        LOGGER.info("Selected picture template '%s'", item.path)
        return item
