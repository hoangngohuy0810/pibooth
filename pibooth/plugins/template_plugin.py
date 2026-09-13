# -*- coding: utf-8 -*-

"""Core UI integration for the optional picture-template plugin."""

import pibooth
from pibooth.templates import TemplateLibrary
from pibooth.utils import LOGGER, PoolingTimer


class TemplatePlugin(object):

    name = 'pibooth-core:template'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.choose_timer = PoolingTimer(60)

    @pibooth.hookimpl
    def pibooth_startup(self, cfg, app):
        app.template_library = TemplateLibrary(cfg)
        # A capture count is needed to render the initial thumbnail. The user
        # can still choose another count immediately after choosing a template.
        app.capture_nbr = app.capture_choices[0]
        app.template_choices = app.template_library.refresh(app.capture_nbr)
        app.template_index = app.template_library.current_index() if app.template_choices else 0
        app.template_confirmed = False
        app.template_startup = bool(app.template_choices)
        app.template_preselected = False

    @pibooth.hookimpl
    def state_wait_enter(self, app):
        if not getattr(app, 'template_library', None):
            return
        app.template_choices = app.template_library.refresh(app.capture_nbr)
        app.template_index = app.template_library.current_index() if app.template_choices else 0
        app.template_confirmed = False
        app.template_preselected = False

    @pibooth.hookimpl
    def state_template_enter(self, app, win):
        app.template_choices = app.template_library.refresh(app.capture_nbr)
        app.template_index = app.template_library.current_index() if app.template_choices else 0
        app.template_confirmed = False
        self.choose_timer.start()
        if app.template_choices:
            LOGGER.info("Choose a picture template (%s available)", len(app.template_choices))
            self._show(app, win)

    @staticmethod
    def _show(app, win):
        item = app.template_choices[app.template_index]
        win.show_template(item.preview, item.name, app.template_index + 1,
                          len(app.template_choices))

    @pibooth.hookimpl
    def state_template_do(self, app, win, events):
        if not app.template_choices:
            return
        action = app.find_template_event(events)
        if action == 'previous':
            app.template_index = (app.template_index - 1) % len(app.template_choices)
            self._show(app, win)
        elif action == 'next':
            app.template_index = (app.template_index + 1) % len(app.template_choices)
            self._show(app, win)
        elif action == 'confirm':
            app.template_library.activate(app.template_index)
            app.template_confirmed = True

    @pibooth.hookimpl
    def state_template_validate(self, cfg, app):
        if not app.template_choices:
            app.template_startup = False
            return 'wait'
        if app.template_confirmed:
            if app.template_startup:
                app.template_startup = False
                app.template_preselected = True
                if len(app.capture_choices) > 1:
                    app.capture_nbr = None
                    return 'choose'
            return self._next_state(cfg)
        if self.choose_timer.is_timeout():
            app.template_startup = False
            return 'wait'

    @staticmethod
    def _next_state(cfg):
        if cfg.getfloat('WINDOW', 'chosen_delay') > 0:
            return 'chosen'
        return 'preview'
