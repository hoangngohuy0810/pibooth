# -*- coding: utf-8 -*-

"""Template discovery, preview generation and activation.

This module deliberately treats ``pibooth-picture-template`` as an optional
runtime dependency.  The core application keeps working when the plugin is not
installed or is disabled.
"""

import os
import os.path as osp
import base64
import math
from dataclasses import dataclass
from io import BytesIO
from xml.etree import ElementTree

from PIL import Image, ImageDraw, ImageFont
from PIL.Image import Resampling

from pibooth import pictures
from pibooth.utils import LOGGER


def is_overlay_template(path):
    """Return True for built-in templates whose transparent frame is on top."""
    return osp.basename(path or '').lower().startswith('kpop_frame_')


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
        folders = {self.cfg.join_path(), self.cfg.join_path('templates')}
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
        configured_key = osp.normcase(osp.abspath(configured)) if configured else ''

        def priority(path):
            basename = osp.basename(path).lower()
            if osp.normcase(path) == configured_key:
                return 0, basename
            if basename.startswith('kcute_'):
                return 2, basename
            if basename.startswith('kpop_frame_'):
                return 1, basename
            return 3, basename

        return sorted(paths, key=priority)

    def _ensure_builtin_templates(self):
        """Create a small starter library without overwriting user files."""
        folder = self.cfg.join_path('templates')
        definitions = {
            'pibooth_modern_grid.xml': 'grid',
            'pibooth_photo_strip.xml': 'strip',
            'genz_neon_pop.xml': 'genz_neon',
            'genz_y2k_dream.xml': 'genz_y2k',
            'genz_scrapbook.xml': 'genz_scrapbook',
            'genz_main_character.xml': 'genz_social',
            'kcute_milk_day.xml': 'kcute_milk',
            'kcute_ribbon_club.xml': 'kcute_ribbon',
            'kcute_cream_check.xml': 'kcute_check',
            'kcute_cloud_bunny.xml': 'kcute_cloud',
            'kcute_berry_date.xml': 'kcute_berry',
            'kcute_mint_diary.xml': 'kcute_mint',
            'kpop_frame_ribbon_diary.xml': 'kframe_ribbon',
            'kpop_frame_peach_party.xml': 'kframe_peach',
            'kpop_frame_bubble_pop.xml': 'kframe_bubble',
            'kpop_frame_idol_card.xml': 'kframe_idol',
        }
        try:
            os.makedirs(folder, exist_ok=True)
            for filename, style in definitions.items():
                path = osp.join(folder, filename)
                needs_migration = False
                if osp.isfile(path) and style.startswith('genz_'):
                    try:
                        with open(path, 'rb') as stream:
                            needs_migration = b'data:image/png;base64,' in stream.read()
                    except OSError:
                        pass
                if not osp.isfile(path) or needs_migration:
                    self._write_builtin(path, style)
        except OSError as exc:
            LOGGER.warning("Could not create built-in template library: %s", exc)

    @classmethod
    def _write_builtin(cls, path, style):
        mxfile = ElementTree.Element('mxfile')
        for orientation in (pictures.PORTRAIT, pictures.LANDSCAPE):
            page_w, page_h = ((400, 600) if orientation == pictures.PORTRAIT else (600, 400))
            background = cls._builtin_background(style, page_w, page_h)
            for count in range(1, 5):
                overlay = cls._builtin_overlay(style, orientation, count, page_w, page_h)
                diagram = ElementTree.SubElement(
                    mxfile, 'diagram', name='{} {} {}'.format(style, orientation, count))
                model = ElementTree.SubElement(
                    diagram, 'mxGraphModel', pageWidth=str(page_w), pageHeight=str(page_h))
                root = ElementTree.SubElement(model, 'root')
                ElementTree.SubElement(root, 'mxCell', id='0', dpi='300')
                ElementTree.SubElement(root, 'mxCell', id='1', parent='0')
                first_capture_id = 2
                if background:
                    cell = ElementTree.SubElement(
                        root, 'mxCell', id='2', value='', vertex='1', parent='1',
                        style='shape=image;image={};'.format(background))
                    ElementTree.SubElement(cell, 'mxGeometry', x='0', y='0',
                                           width=str(page_w), height=str(page_h), **{'as': 'geometry'})
                    first_capture_id = 3
                for index, (x, y, width, height) in enumerate(
                        cls._builtin_rects(style, orientation, count), start=1):
                    rotation = cls._builtin_rotation(style, index)
                    cell = ElementTree.SubElement(root, 'mxCell', id=str(first_capture_id + index - 1),
                                                  value=str(index), vertex='1', parent='1',
                                                  style='rounded=1;rotation={};'.format(rotation))
                    ElementTree.SubElement(cell, 'mxGeometry', x=str(x), y=str(y),
                                           width=str(width), height=str(height), **{'as': 'geometry'})
                if overlay:
                    overlay_id = str(first_capture_id + count)
                    cell = ElementTree.SubElement(
                        root, 'mxCell', id=overlay_id, value='', vertex='1', parent='1',
                        style='shape=image;image={};'.format(overlay))
                    ElementTree.SubElement(cell, 'mxGeometry', x='0', y='0',
                                           width=str(page_w), height=str(page_h), **{'as': 'geometry'})
        ElementTree.ElementTree(mxfile).write(path, encoding='utf-8', xml_declaration=True)

    @staticmethod
    def _builtin_rects(style, orientation, count):
        portrait = orientation == pictures.PORTRAIT
        if style.startswith('kframe_'):
            if portrait:
                layouts = {
                    1: ((52, 78, 296, 390),),
                    2: ((55, 70, 290, 182), (55, 278, 290, 182)),
                    3: ((55, 52, 290, 135), (55, 207, 290, 135), (55, 362, 290, 135)),
                    4: ((48, 62, 142, 190), (210, 62, 142, 190),
                        (48, 278, 142, 190), (210, 278, 142, 190)),
                }
            else:
                layouts = {
                    1: ((82, 50, 436, 275),),
                    2: ((70, 52, 215, 270), (315, 52, 215, 270)),
                    3: ((52, 55, 155, 260), (222, 55, 155, 260), (392, 55, 155, 260)),
                    4: ((66, 42, 215, 130), (319, 42, 215, 130),
                        (66, 192, 215, 130), (319, 192, 215, 130)),
                }
        elif style.startswith(('genz_', 'kcute_')):
            if portrait:
                layouts = {
                    1: ((45, 70, 310, 420),),
                    2: ((45, 62, 310, 200), (45, 282, 310, 200)),
                    3: ((45, 48, 310, 210), (45, 278, 145, 205), (210, 278, 145, 205)),
                    4: ((42, 62, 148, 200), (210, 62, 148, 200),
                        (42, 282, 148, 200), (210, 282, 148, 200)),
                }
            else:
                layouts = {
                    1: ((70, 48, 460, 285),),
                    2: ((62, 48, 225, 285), (313, 48, 225, 285)),
                    3: ((52, 48, 275, 285), (347, 48, 195, 133), (347, 201, 195, 132)),
                    4: ((62, 42, 225, 142), (313, 42, 225, 142),
                        (62, 204, 225, 142), (313, 204, 225, 142)),
                }
        elif style == 'grid':
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
    def _builtin_rotation(style, index):
        if style == 'genz_scrapbook':
            return (-3, 3, 2, -2)[(index - 1) % 4]
        if style == 'genz_y2k':
            return (2, -2, -1, 1)[(index - 1) % 4]
        if style in ('kcute_ribbon', 'kcute_berry', 'kcute_mint'):
            return (-1, 1, 0, -1)[(index - 1) % 4]
        return 0

    @staticmethod
    def _star_points(center, outer, inner, points=5):
        values = []
        for index in range(points * 2):
            angle = -math.pi / 2 + index * math.pi / points
            radius = outer if index % 2 == 0 else inner
            values.append((center[0] + math.cos(angle) * radius,
                           center[1] + math.sin(angle) * radius))
        return values

    @classmethod
    def _builtin_background(cls, style, width, height):
        """Return a small embedded PNG used by the Gen Z templates."""
        if style.startswith('kframe_'):
            return cls._kframe_background(style, width, height)
        if style.startswith('kcute_'):
            return cls._kcute_background(style, width, height)
        if not style.startswith('genz_'):
            return ''

        image = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(image)
        if style == 'genz_neon':
            top, bottom = (18, 10, 45), (91, 22, 126)
            accent, second, ink = (65, 255, 214), (255, 64, 180), (255, 255, 255)
            title = 'NO FILTER'
        elif style == 'genz_y2k':
            top, bottom = (220, 236, 255), (255, 204, 235)
            accent, second, ink = (120, 86, 255), (44, 196, 255), (55, 38, 90)
            title = 'ICON ENERGY'
        elif style == 'genz_scrapbook':
            top, bottom = (255, 246, 216), (244, 226, 184)
            accent, second, ink = (255, 92, 92), (72, 167, 124), (71, 55, 42)
            title = 'MEMORY DUMP'
        else:
            top, bottom = (255, 91, 140), (105, 68, 255)
            accent, second, ink = (255, 232, 92), (98, 255, 213), (255, 255, 255)
            title = 'MAIN CHARACTER'

        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
            draw.line((0, y, width, y), fill=color)

        scale = min(width, height)
        line = max(2, scale // 100)
        if style == 'genz_neon':
            draw.ellipse((-scale // 5, height // 10, scale // 2, height // 2),
                         outline=accent, width=line * 2)
            draw.ellipse((width - scale // 3, height // 2, width + scale // 4, height),
                         outline=second, width=line * 2)
            draw.line((0, height * 0.88, width, height * 0.72), fill=accent, width=line)
        elif style == 'genz_y2k':
            for center, radius in (((width * .12, height * .12), scale * .055),
                                   ((width * .88, height * .20), scale * .04),
                                   ((width * .82, height * .82), scale * .065)):
                draw.polygon(cls._star_points(center, radius, radius * .42),
                             fill=accent, outline=ink)
            draw.ellipse((width * .02, height * .65, width * .22, height * .85),
                         fill=second, outline=ink, width=line)
        elif style == 'genz_scrapbook':
            gap = max(16, scale // 14)
            for x in range(gap // 2, width, gap):
                for y in range(gap // 2, height, gap):
                    draw.ellipse((x, y, x + line, y + line), fill=(190, 166, 120))
            draw.rounded_rectangle((width * .04, height * .08, width * .24, height * .14),
                                   radius=4, fill=(255, 216, 96), outline=ink, width=line)
            draw.ellipse((width * .82, height * .12, width * .94, height * .24),
                         fill=accent, outline=ink, width=line)
            draw.arc((width * .85, height * .15, width * .91, height * .21), 10, 170,
                     fill=ink, width=line)
        else:
            draw.rounded_rectangle((width * .04, height * .05, width * .33, height * .13),
                                   radius=12, outline=ink, width=line)
            draw.ellipse((width * .82, height * .08, width * .94, height * .20),
                         fill=accent, outline=ink, width=line)
            draw.polygon(cls._star_points((width * .10, height * .84), scale * .07,
                                          scale * .03), fill=second, outline=ink)

        font = ImageFont.load_default(size=max(16, scale // 16))
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_y = height - max(30, scale // 10)
        draw.rounded_rectangle((width / 2 - text_width / 2 - 10, text_y - 5,
                                width / 2 + text_width / 2 + 10,
                                text_y + (bbox[3] - bbox[1]) + 5),
                               radius=8, fill=ink if style == 'genz_scrapbook' else (20, 14, 35))
        draw.text((width / 2 - text_width / 2, text_y), title,
                  fill=(255, 255, 255), font=font)

        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        # The plugin separates mxGraph style fields on semicolons, therefore
        # the usual ``;base64`` marker cannot be embedded in the style value.
        # Its image decoder only needs the comma and the base64 payload.
        return 'data:image/png,{}'.format(encoded)

    @staticmethod
    def _encode_png(image):
        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        return 'data:image/png,{}'.format(encoded)

    @classmethod
    def _kframe_background(cls, style, width, height):
        palettes = {
            'kframe_ribbon': ((255, 247, 241), (248, 206, 219)),
            'kframe_peach': ((255, 244, 220), (255, 213, 160)),
            'kframe_bubble': ((239, 242, 255), (207, 218, 255)),
            'kframe_idol': ((248, 248, 250), (222, 222, 232)),
        }
        top, bottom = palettes[style]
        image = Image.new('RGB', (width, height), top)
        draw = ImageDraw.Draw(image)
        for y in range(height):
            ratio = y / max(1, height - 1)
            color = tuple(int(top[i] * (1 - ratio) + bottom[i] * ratio) for i in range(3))
            draw.line((0, y, width, y), fill=color)

        # A subtle paper/grid texture stays below the photographs.
        grid = max(24, min(width, height) // 7)
        grid_color = tuple(max(0, channel - 10) for channel in bottom)
        for x in range(0, width, grid):
            draw.line((x, 0, x, height), fill=grid_color, width=1)
        for y in range(0, height, grid):
            draw.line((0, y, width, y), fill=grid_color, width=1)
        return cls._encode_png(image)

    @classmethod
    def _builtin_overlay(cls, style, orientation, count, width, height):
        """Create a transparent top layer that sits above the captured photos."""
        if not style.startswith('kframe_'):
            return ''

        palettes = {
            'kframe_ribbon': ((118, 75, 95), (244, 154, 190), (255, 234, 241), 'ribbon diary'),
            'kframe_peach': ((105, 69, 52), (255, 123, 91), (255, 205, 105), 'peach party'),
            'kframe_bubble': ((70, 70, 120), (138, 160, 255), (207, 246, 255), 'bubble pop'),
            'kframe_idol': ((34, 35, 43), (255, 116, 174), (230, 230, 238), 'idol mode'),
        }
        ink, accent, soft, title = palettes[style]
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        scale = min(width, height)
        line = max(2, scale // 90)
        rects = cls._builtin_rects(style, orientation, count)

        for index, (x, y, rect_w, rect_h) in enumerate(rects):
            pad = max(7, scale // 36)
            outer = (x - pad, y - pad, x + rect_w + pad, y + rect_h + pad)
            radius = max(10, scale // 24)
            draw.rounded_rectangle(outer, radius=radius, fill=(255, 253, 249, 245),
                                   outline=ink, width=line)
            # Punch a fully transparent window so the photo below remains visible.
            inner = (x + line, y + line, x + rect_w - line, y + rect_h - line)
            draw.rounded_rectangle(inner, radius=max(6, radius - pad), fill=(0, 0, 0, 0))

            if style in ('kframe_ribbon', 'kframe_peach'):
                # Small scallops overlap the photo edge and make the top layer obvious.
                dot_radius = max(3, scale // 85)
                step = max(dot_radius * 3, 12)
                for px in range(int(x + step), int(x + rect_w), step):
                    draw.ellipse((px - dot_radius, y - dot_radius, px + dot_radius,
                                  y + dot_radius), fill=(255, 253, 249, 255),
                                 outline=ink, width=max(1, line // 2))

            # Number badges sit over the lower photo edge.
            badge_r = max(9, scale // 27)
            badge_x = x + rect_w - badge_r * .55
            badge_y = y + rect_h - badge_r * .55
            draw.ellipse((badge_x - badge_r, badge_y - badge_r,
                          badge_x + badge_r, badge_y + badge_r), fill=accent,
                         outline=ink, width=line)
            number_font = ImageFont.load_default(size=max(10, badge_r))
            draw.text((badge_x, badge_y), str(index + 1), fill=(255, 255, 255),
                      font=number_font, anchor='mm')

        # Stickers are deliberately drawn after the holes so they overlap photos.
        if style == 'kframe_ribbon':
            cls._draw_ribbon(draw, (width * .13, height * .12), scale * .045,
                             ink, accent, soft, line)
            cls._draw_ribbon(draw, (width * .87, height * .80), scale * .04,
                             ink, soft, accent, line)
            for center in ((width * .88, height * .17), (width * .13, height * .74)):
                draw.polygon(cls._star_points(center, scale * .035, scale * .015, 4),
                             fill=soft, outline=ink)
        elif style == 'kframe_peach':
            for center in ((width * .12, height * .15), (width * .87, height * .78)):
                draw.polygon(cls._star_points(center, scale * .045, scale * .02),
                             fill=soft, outline=ink)
            # Minimal party hat and confetti.
            draw.polygon(((width * .84, height * .13), (width * .93, height * .22),
                          (width * .80, height * .24)), fill=accent, outline=ink)
            for cx, cy in ((.12, .30), (.90, .42), (.10, .88), (.86, .62)):
                draw.ellipse((width * cx - 3, height * cy - 3,
                              width * cx + 3, height * cy + 3), fill=accent)
        elif style == 'kframe_bubble':
            for cx, cy, radius in ((.10, .16, .045), (.88, .22, .035),
                                   (.12, .82, .03), (.90, .72, .05)):
                r = scale * radius
                draw.ellipse((width * cx - r, height * cy - r,
                              width * cx + r, height * cy + r),
                             fill=(soft[0], soft[1], soft[2], 190), outline=ink, width=line)
                draw.arc((width * cx - r * .65, height * cy - r * .65,
                          width * cx + r * .3, height * cy + r * .3), 190, 285,
                         fill=(255, 255, 255, 255), width=line)
        else:
            # Photocard-inspired corner brackets and tiny flash stars.
            bracket = max(12, scale // 18)
            for x, y, rect_w, rect_h in rects:
                draw.line((x - line, y + bracket, x - line, y - line,
                           x + bracket, y - line), fill=accent, width=line * 2)
                draw.line((x + rect_w - bracket, y + rect_h + line,
                           x + rect_w + line, y + rect_h + line,
                           x + rect_w + line, y + rect_h - bracket),
                          fill=accent, width=line * 2)
            for center in ((width * .10, height * .18), (width * .90, height * .78)):
                draw.polygon(cls._star_points(center, scale * .04, scale * .012, 4),
                             fill=accent, outline=ink)

        font = ImageFont.load_default(size=max(15, scale // 18))
        bbox = draw.textbbox((0, 0), title, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        label_y = height - max(26, scale // 12)
        draw.rounded_rectangle((width / 2 - text_w / 2 - 14, label_y - 6,
                                width / 2 + text_w / 2 + 14, label_y + text_h + 6),
                               radius=10, fill=(255, 253, 249, 245), outline=ink, width=line)
        draw.text((width / 2, label_y + text_h / 2), title, fill=ink,
                  font=font, anchor='mm')
        return cls._encode_png(image)

    @staticmethod
    def _draw_ribbon(draw, center, radius, ink, left, right, line):
        cx, cy = center
        draw.ellipse((cx - radius * 2, cy - radius, cx, cy + radius),
                     fill=left, outline=ink, width=line)
        draw.ellipse((cx, cy - radius, cx + radius * 2, cy + radius),
                     fill=right, outline=ink, width=line)
        draw.polygon(((cx - radius * .25, cy + radius * .3),
                      (cx - radius, cy + radius * 2.1), (cx, cy + radius * 1.35),
                      (cx + radius, cy + radius * 2.1),
                      (cx + radius * .25, cy + radius * .3)),
                     fill=left, outline=ink)
        draw.ellipse((cx - radius * .35, cy - radius * .35,
                      cx + radius * .35, cy + radius * .35),
                     fill=ink, outline=ink)

    @classmethod
    def _kcute_background(cls, style, width, height):
        """Create an original soft Korean photo-booth inspired background."""
        palettes = {
            'kcute_milk': ((250, 248, 241), (190, 215, 236), (70, 91, 116), 'soft day'),
            'kcute_ribbon': ((255, 238, 244), (244, 174, 201), (129, 72, 101), 'ribbon club'),
            'kcute_check': ((250, 242, 222), (186, 207, 226), (79, 91, 104), 'cream check'),
            'kcute_cloud': ((232, 232, 255), (183, 190, 239), (91, 83, 142), 'cloud nine'),
            'kcute_berry': ((255, 239, 235), (239, 132, 143), (117, 67, 71), 'berry date'),
            'kcute_mint': ((229, 247, 235), (142, 204, 174), (60, 102, 80), 'mint diary'),
        }
        base, accent, ink, title = palettes[style]
        image = Image.new('RGB', (width, height), base)
        draw = ImageDraw.Draw(image)
        scale = min(width, height)
        line = max(1, scale // 120)

        # Thin double border is common to the restrained basic-color frames.
        inset = max(8, scale // 30)
        draw.rounded_rectangle((inset, inset, width - inset, height - inset),
                               radius=max(8, scale // 28), outline=accent, width=line * 2)
        draw.rounded_rectangle((inset + 5, inset + 5, width - inset - 5, height - inset - 5),
                               radius=max(6, scale // 32), outline=(255, 255, 255), width=line)

        if style == 'kcute_milk':
            gap = max(28, scale // 7)
            for x in range(gap // 2, width, gap):
                for y in range(gap // 2, height, gap):
                    draw.ellipse((x - 2, y - 2, x + 2, y + 2), fill=accent)
            draw.ellipse((width * .08, height * .10, width * .19, height * .17),
                         fill=(255, 255, 255), outline=ink, width=line)
            draw.arc((width * .10, height * .12, width * .17, height * .17), 10, 170,
                     fill=ink, width=line)
        elif style == 'kcute_ribbon':
            for cx, cy in ((width * .12, height * .13), (width * .86, height * .23),
                           (width * .15, height * .80)):
                r = scale * .035
                draw.ellipse((cx - r * 2, cy - r, cx, cy + r), fill=(255, 255, 255),
                             outline=ink, width=line)
                draw.ellipse((cx, cy - r, cx + r * 2, cy + r), fill=(255, 255, 255),
                             outline=ink, width=line)
                draw.ellipse((cx - r * .35, cy - r * .35, cx + r * .35, cy + r * .35),
                             fill=accent, outline=ink, width=line)
                draw.polygon(((cx - r * .3, cy + r * .2), (cx - r, cy + r * 2),
                              (cx, cy + r * 1.3), (cx + r, cy + r * 2),
                              (cx + r * .3, cy + r * .2)), fill=accent, outline=ink)
        elif style == 'kcute_check':
            cell = max(22, scale // 8)
            pale = tuple(min(255, channel + 40) for channel in accent)
            for x in range(0, width, cell):
                draw.rectangle((x, 0, x + cell // 2, height), fill=pale)
            for y in range(0, height, cell):
                draw.rectangle((0, y, width, y + cell // 2), fill=pale)
            for x in range(0, width, cell):
                for y in range(0, height, cell):
                    draw.rectangle((x, y, x + cell // 2, y + cell // 2), fill=accent)
        elif style == 'kcute_cloud':
            for cx, cy, radius in ((width * .13, height * .14, scale * .045),
                                   (width * .84, height * .20, scale * .04),
                                   (width * .16, height * .82, scale * .035)):
                draw.ellipse((cx - radius * 1.8, cy, cx + radius * 1.8, cy + radius),
                             fill=(255, 255, 255))
                draw.ellipse((cx - radius, cy - radius * .7, cx + radius * .5,
                              cy + radius), fill=(255, 255, 255))
                draw.ellipse((cx, cy - radius * .45, cx + radius * 1.3,
                              cy + radius), fill=(255, 255, 255))
            for center in ((width * .12, height * .28), (width * .90, height * .40)):
                draw.polygon(cls._star_points(center, scale * .022, scale * .009, 4), fill=accent)
        elif style == 'kcute_berry':
            for cx, cy in ((width * .12, height * .14), (width * .87, height * .24),
                           (width * .15, height * .82)):
                radius = scale * .028
                draw.ellipse((cx - radius * 1.5, cy - radius, cx + radius * .2,
                              cy + radius), fill=accent, outline=ink, width=line)
                draw.ellipse((cx - radius * .2, cy - radius, cx + radius * 1.5,
                              cy + radius), fill=accent, outline=ink, width=line)
                draw.arc((cx - radius, cy - radius * 2.2, cx + radius,
                          cy - radius * .1), 180, 350, fill=ink, width=line)
        else:
            for cx, cy in ((width * .12, height * .14), (width * .88, height * .22),
                           (width * .14, height * .82)):
                radius = scale * .035
                draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius),
                             fill=(255, 255, 245), outline=ink, width=line)
                draw.ellipse((cx - radius * .25, cy - radius * .25,
                              cx + radius * .25, cy + radius * .25), fill=(255, 210, 90))
                for angle in range(0, 360, 45):
                    dx = math.cos(math.radians(angle)) * radius * 1.5
                    dy = math.sin(math.radians(angle)) * radius * 1.5
                    draw.ellipse((cx + dx - radius * .35, cy + dy - radius * .35,
                                  cx + dx + radius * .35, cy + dy + radius * .35), fill=accent)

        # Redraw the frame above patterns so the edge always remains crisp.
        draw.rounded_rectangle((inset, inset, width - inset, height - inset),
                               radius=max(8, scale // 28), outline=accent, width=line * 2)
        draw.rounded_rectangle((inset + 5, inset + 5, width - inset - 5, height - inset - 5),
                               radius=max(6, scale // 32), outline=(255, 255, 255), width=line)

        font = ImageFont.load_default(size=max(14, scale // 20))
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        text_y = height - max(28, scale // 11)
        draw.rounded_rectangle((width / 2 - text_width / 2 - 12, text_y - 5,
                                width / 2 + text_width / 2 + 12,
                                text_y + (bbox[3] - bbox[1]) + 5),
                               radius=10, fill=base, outline=ink, width=line)
        draw.text((width / 2 - text_width / 2, text_y), title, fill=ink, font=font)

        buffer = BytesIO()
        image.save(buffer, format='PNG', optimize=True)
        encoded = base64.b64encode(buffer.getvalue()).decode('ascii')
        return 'data:image/png,{}'.format(encoded)

    @staticmethod
    def _display_name(path):
        name = osp.splitext(osp.basename(path))[0]
        name = name.replace('_', ' ').replace('-', ' ').strip().title()
        return (name.replace('Genz ', 'Gen Z ', 1)
                .replace('Kcute ', 'K-Cute ', 1)
                .replace('Kpop ', 'K-Pop ', 1))

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
            crop = (is_overlay_template(path)
                    or self.cfg.getboolean('PICTURE', 'captures_cropping'))
            factory.set_cropping(crop)
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
