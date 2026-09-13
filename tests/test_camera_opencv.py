# -*- coding: utf-8 -*-

from types import SimpleNamespace

from pibooth.camera import opencv


def test_camera_choices_use_device_names_and_local_ports(monkeypatch):
    cv2 = SimpleNamespace(CAP_DSHOW=700, CAP_AVFOUNDATION=1200, CAP_V4L2=200)
    cameras = [SimpleNamespace(name='Integrated Camera', index=0, backend=700),
               SimpleNamespace(name='USB Camera', index=1, backend=700)]
    monkeypatch.setattr(opencv, 'cv2', cv2)
    monkeypatch.setattr(opencv, 'enumerate_cameras', lambda backend: cameras)
    monkeypatch.setattr(opencv.sys, 'platform', 'win32')

    assert opencv.get_cv_camera_choices() == [('Integrated Camera', 0),
                                              ('USB Camera', 1)]


def test_duplicate_camera_names_are_distinguishable(monkeypatch):
    cv2 = SimpleNamespace(CAP_DSHOW=700, CAP_AVFOUNDATION=1200, CAP_V4L2=200)
    cameras = [SimpleNamespace(name='USB Camera', index=0, backend=700),
               SimpleNamespace(name='USB Camera', index=1, backend=700)]
    monkeypatch.setattr(opencv, 'cv2', cv2)
    monkeypatch.setattr(opencv, 'enumerate_cameras', lambda backend: cameras)
    monkeypatch.setattr(opencv.sys, 'platform', 'win32')

    assert opencv.get_cv_camera_choices() == [('USB Camera (1)', 0),
                                              ('USB Camera (2)', 1)]


def test_camera_choices_fall_back_when_enumeration_fails(monkeypatch):
    cv2 = SimpleNamespace(CAP_DSHOW=700, CAP_AVFOUNDATION=1200, CAP_V4L2=200)
    monkeypatch.setattr(opencv, 'cv2', cv2)
    monkeypatch.setattr(opencv, 'enumerate_cameras', lambda backend: 1 / 0)

    assert opencv.get_cv_camera_choices(2) == [('Camera 0', 0), ('Camera 1', 1)]


def test_selected_camera_uses_the_same_native_backend(monkeypatch):
    calls = []

    class CaptureMock(object):
        @staticmethod
        def isOpened():
            return True

    def video_capture(port, backend):
        calls.append((port, backend))
        return CaptureMock()

    cv2 = SimpleNamespace(CAP_DSHOW=700, CAP_AVFOUNDATION=1200, CAP_V4L2=200,
                          VideoCapture=video_capture)
    monkeypatch.setattr(opencv, 'cv2', cv2)
    monkeypatch.setattr(opencv.sys, 'platform', 'win32')

    assert opencv.get_cv_camera_proxy(3).isOpened()
    assert calls == [(3, 700)]
