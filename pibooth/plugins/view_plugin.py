import pygame
import pibooth
from pibooth.utils import LOGGER, get_crash_message, PoolingTimer
from pibooth import fonts


class ViewPlugin(object):

    """Plugin to manage the pibooth window dans transitions.
    """

    name = 'pibooth-core:view'

    def __init__(self, plugin_manager):
        self._pm = plugin_manager
        self.count = 0
        self.forgotten = False
        # Seconds to display the failed message
        self.failed_view_timer = PoolingTimer(2)
        # Seconds between each animated frame
        self.animated_frame_timer = PoolingTimer(0)
        # Seconds before going back to the start
        self.choose_timer = PoolingTimer(30)
        # Seconds to display the selected layout
        self.layout_timer = PoolingTimer(4)
        # Seconds to display the selected layout
        self.print_view_timer = PoolingTimer(0)
        # Seconds to display the selected layout
        self.finish_timer = PoolingTimer(1)
        self.reviewing = False

    @staticmethod
    def _next_after_layout(cfg, app):
        if getattr(app, 'template_preselected', False):
            app.template_preselected = False
            if cfg.getfloat('WINDOW', 'chosen_delay') > 0:
                return 'chosen'
            return 'preview'
        library = getattr(app, 'template_library', None)
        if library and library.refresh(app.capture_nbr):
            app.template_choices = library.items
            return 'template'
        if cfg.getfloat('WINDOW', 'chosen_delay') > 0:
            return 'chosen'
        return 'preview'

    @pibooth.hookimpl
    def state_failsafe_enter(self, win):
        win.show_oops()
        self.failed_view_timer.start()
        LOGGER.error(get_crash_message())

    @pibooth.hookimpl
    def state_failsafe_validate(self):
        if self.failed_view_timer.is_timeout():
            return 'wait'

    @pibooth.hookimpl
    def state_wait_enter(self, cfg, app, win):
        self.forgotten = False
        win.clear_review()
        if cfg.getboolean('WINDOW', 'always_preview', fallback=False) and hasattr(app, 'camera') and app.camera:
            LOGGER.info("Starting Smart Mirror live preview")
            app.camera.preview(win, flip=cfg.getboolean('CAMERA', 'preview_flip'))
        else:
            if app.previous_animated:
                previous_picture = next(app.previous_animated)
                # Reset timeout in case of settings changed
                self.animated_frame_timer.timeout = cfg.getfloat('WINDOW', 'animate_delay')
                self.animated_frame_timer.start()
            else:
                previous_picture = app.previous_picture

            win.show_intro(previous_picture, app.printer.is_ready()
                           and app.count.remaining_duplicates > 0)
        if app.printer.is_installed():
            win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

    @pibooth.hookimpl
    def state_wait_do(self, cfg, app, win, events):
        if cfg.getboolean('WINDOW', 'always_preview', fallback=False) and hasattr(app, 'camera') and app.camera:
            if hasattr(app.camera, '_get_preview_image'):
                image = app.camera._get_preview_image()
                if image:
                    win.show_image(image)
                    text = cfg.get('WINDOW', 'always_preview_text')
                    if text:
                        win_rect = win.surface.get_rect()
                        font_size = max(24, int(win_rect.height * 0.045))
                        try:
                            font = pygame.font.SysFont(['segoeui', 'arial'], font_size, bold=True)
                        except Exception:
                            font = pygame.font.Font(fonts.CURRENT, font_size)
                        label = font.render(text, True, (255, 255, 255))

                        padding_y = 12
                        padding_x = 24
                        banner_w = label.get_width() + padding_x * 2
                        banner_h = label.get_height() + padding_y * 2
                        banner = pygame.Surface((banner_w, banner_h), pygame.SRCALPHA)
                        banner.fill((0, 0, 0, 160))
                        banner_rect = banner.get_rect(centerx=win_rect.centerx, bottom=win_rect.bottom - 40)
                        label_rect = label.get_rect(center=banner_rect.center)
                        win.surface.blit(banner, banner_rect.topleft)
                        win.surface.blit(label, label_rect.topleft)
        else:
            if app.previous_animated and self.animated_frame_timer.is_timeout():
                previous_picture = next(app.previous_animated)
                win.show_intro(previous_picture, app.printer.is_ready()
                               and app.count.remaining_duplicates > 0)
                self.animated_frame_timer.start()
            else:
                previous_picture = app.previous_picture

            event = app.find_print_status_event(events)
            if event and app.printer.is_installed():
                tasks = app.printer.get_all_tasks()
                win.set_print_number(len(tasks), not app.printer.is_ready())

            if app.find_print_event(events) or (win.get_image() and not previous_picture):
                win.show_intro(previous_picture, app.printer.is_ready()
                               and app.count.remaining_duplicates > 0)

    @pibooth.hookimpl
    def state_wait_validate(self, cfg, app, events):
        if app.find_capture_event(events):
            if len(app.capture_choices) > 1:
                return 'choose'
            return self._next_after_layout(cfg, app)

    @pibooth.hookimpl
    def state_wait_exit(self, win):
        self.count = 0
        win.show_image(None)  # Clear currently displayed image

    @pibooth.hookimpl
    def state_choose_enter(self, app, win):
        LOGGER.info("Show picture choice (nothing selected)")
        win.set_print_number(0, False)  # Hide printer status
        win.show_choice(app.capture_choices)
        self.choose_timer.start()

    @pibooth.hookimpl
    def state_choose_validate(self, cfg, app):
        if app.capture_nbr:
            return self._next_after_layout(cfg, app)
        elif self.choose_timer.is_timeout():
            return 'wait'

    @pibooth.hookimpl
    def state_chosen_enter(self, cfg, app, win):
        LOGGER.info("Show picture choice (%s captures selected)", app.capture_nbr)
        win.show_choice(app.capture_choices, selected=app.capture_nbr)

        # Reset timeout in case of settings changed
        self.layout_timer.timeout = cfg.getfloat('WINDOW', 'chosen_delay')
        self.layout_timer.start()

    @pibooth.hookimpl
    def state_chosen_validate(self):
        if self.layout_timer.is_timeout():
            return 'preview'

    @pibooth.hookimpl
    def state_preview_enter(self, app, win):
        self.count += 1
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_preview_validate(self):
        return 'capture'

    @pibooth.hookimpl
    def state_capture_do(self, app, win):
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_capture_validate(self, app):
        if self.count >= app.capture_nbr:
            return 'processing'
        return 'preview'

    @pibooth.hookimpl
    def state_processing_enter(self, win):
        win.show_work_in_progress()

    @pibooth.hookimpl
    def state_processing_validate(self, cfg, app):
        if app.printer.is_ready() and cfg.getfloat('PRINTER', 'printer_delay') > 0\
                and app.count.remaining_duplicates > 0:
            return 'print'
        return 'finish'  # Can not print

    @pibooth.hookimpl
    def state_print_enter(self, cfg, app, win):
        LOGGER.info("Display the final picture")
        win.show_print(app.previous_picture)
        win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

        # Reset timeout in case of settings changed
        self.print_view_timer.timeout = cfg.getfloat('PRINTER', 'printer_delay')
        self.print_view_timer.start()

    @pibooth.hookimpl
    def state_print_validate(self, app, win, events):
        printed = app.find_print_event(events)
        self.forgotten = app.find_capture_event(events)
        if self.print_view_timer.is_timeout() or printed or self.forgotten:
            if printed:
                win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())
            return 'finish'

    @pibooth.hookimpl
    def state_finish_enter(self, cfg, app, win):
        self.reviewing = (cfg.getboolean('WINDOW', 'review_picture')
                          and not self.forgotten and app.previous_picture is not None)
        if self.reviewing:
            win.show_review(app.previous_picture, cfg.get('WINDOW', 'review_picture_text'))
            self.finish_timer.reset()
        elif cfg.getfloat('WINDOW', 'finish_picture_delay') > 0 and not self.forgotten:
            win.show_finished(app.previous_picture)
            timeout = cfg.getfloat('WINDOW', 'finish_picture_delay')
        else:
            win.show_finished()
            timeout = 1

        if not self.reviewing:
            # Reset timeout in case of settings changed
            self.finish_timer.timeout = timeout
            self.finish_timer.start()

    @pibooth.hookimpl
    def state_finish_validate(self, app, events):
        if self.reviewing:
            if app.find_review_event(events):
                self.reviewing = False
                return 'wait'
            return None
        if self.finish_timer.is_timeout():
            return 'wait'
