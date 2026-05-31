import sys
import tomllib
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self._object_name = ""
        self.minimum_height = None
        self.update_count = 0

    def setObjectName(self, name):
        self._object_name = name

    def objectName(self):
        return self._object_name

    def setMinimumHeight(self, height):
        self.minimum_height = height

    def update(self):
        self.update_count += 1


class FakeButton(FakeWidget):
    def __init__(self, text=""):
        super().__init__()
        self._text = text
        self.clicked = FakeSignal()

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text


class FakeComboBox(FakeWidget):
    def __init__(self):
        super().__init__()
        self.items = []
        self.currentIndexChanged = FakeSignal()

    def addItem(self, text):
        self.items.append(text)

    def currentText(self):
        return self.items[0] if self.items else ""


class FakeLabel(FakeWidget):
    def __init__(self, text=""):
        super().__init__()
        self.text = text

    def setText(self, text):
        self.text = text


class FakeLayout:
    def __init__(self):
        self.widgets = []

    def addWidget(self, widget):
        self.widgets.append(widget)


class FakeContainer(FakeWidget):
    def __init__(self, *args, **kwargs):
        super().__init__()
        self.layout = None

    def setLayout(self, layout):
        self.layout = layout


class FakeMainWindow(FakeWidget):
    def __init__(self):
        super().__init__()
        self.central_widget = None

    def setGeometry(self, *args):
        self.geometry = args

    def setWindowTitle(self, title):
        self.title = title

    def setCentralWidget(self, widget):
        self.central_widget = widget

    def findChild(self, widget_type, object_name):
        return self._find_child(self.central_widget, widget_type, object_name)

    def _find_child(self, widget, widget_type, object_name):
        if isinstance(widget, widget_type) and widget.objectName() == object_name:
            return widget
        layout = getattr(widget, "layout", None)
        if layout:
            for child in layout.widgets:
                found = self._find_child(child, widget_type, object_name)
                if found is not None:
                    return found
        return None


class FakeInputStream:
    def __init__(self, *args, **kwargs):
        self.started = False
        self.stopped = False
        self.closed = False

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def close(self):
        self.closed = True


def install_fake_modules():
    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.QPointF = object
    qtcore.QRectF = object
    qtcore.Qt = types.SimpleNamespace(
        AlignmentFlag=types.SimpleNamespace(AlignCenter=0, AlignLeft=1, AlignRight=2, AlignTop=4, AlignBottom=8),
        PenStyle=types.SimpleNamespace(DotLine=1),
    )

    qtgui = types.ModuleType("PySide6.QtGui")
    qtgui.QColor = object
    qtgui.QFont = object
    qtgui.QPainter = object
    qtgui.QPen = object

    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtwidgets.QApplication = object
    qtwidgets.QComboBox = FakeComboBox
    qtwidgets.QLabel = FakeLabel
    qtwidgets.QMainWindow = FakeMainWindow
    qtwidgets.QPushButton = FakeButton
    qtwidgets.QVBoxLayout = FakeLayout
    qtwidgets.QWidget = FakeContainer

    pyside = types.ModuleType("PySide6")
    pyside.QtCore = qtcore
    pyside.QtGui = qtgui
    pyside.QtWidgets = qtwidgets

    sounddevice = types.ModuleType("sounddevice")
    sounddevice.InputStream = FakeInputStream
    sounddevice.play = lambda *args, **kwargs: None
    sounddevice.wait = lambda: None

    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtCore"] = qtcore
    sys.modules["PySide6.QtGui"] = qtgui
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules["sounddevice"] = sounddevice


class ProjectSetupTests(unittest.TestCase):
    def test_pyproject_uses_current_project_metadata(self):
        with (ROOT / "pyproject.toml").open("rb") as pyproject:
            metadata = tomllib.load(pyproject)

        self.assertIn("project", metadata)
        self.assertEqual(metadata.get("tool", {}).get("poetry"), {"package-mode": False})

    def test_python_requirement_matches_pyenv_pin(self):
        with (ROOT / "pyproject.toml").open("rb") as pyproject:
            project = tomllib.load(pyproject)["project"]

        pinned_python = (ROOT / ".python-version").read_text().strip()
        major, minor, _patch = pinned_python.split(".")

        self.assertEqual(project["requires-python"], f">={major}.{minor},<{major}.{int(minor) + 1}")

    def test_runtime_dependencies_match_imports(self):
        with (ROOT / "pyproject.toml").open("rb") as pyproject:
            dependencies = tomllib.load(pyproject)["project"]["dependencies"]

        self.assertTrue(any(dep.startswith("PySide6") for dep in dependencies))
        self.assertTrue(any(dep.startswith("numpy") for dep in dependencies))
        self.assertTrue(any(dep.startswith("sounddevice") for dep in dependencies))
        self.assertFalse(any(dep.startswith("mpllib") for dep in dependencies))

    def test_record_button_toggles_recording_without_lookup_failure(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            with redirect_stdout(StringIO()):
                window.start_recording()

            self.assertTrue(window.is_recording)
            self.assertEqual(window.record_button.text(), "Stop Recording")
            self.assertTrue(window.recording_stream.started)

            with redirect_stdout(StringIO()):
                window.start_recording()

            self.assertFalse(window.is_recording)
            self.assertEqual(window.record_button.text(), "Record")
            self.assertTrue(window.recording_stream.stopped)
            self.assertTrue(window.recording_stream.closed)
        finally:
            sys.path.remove(str(SRC))

    def test_process_audio_uses_real_chipmunk_effect(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            samplerate = 8000
            t = np.arange(samplerate, dtype=np.float32) / samplerate
            window = MainWindow()
            window.samplerate = samplerate
            window.audio_data = (0.7 * np.sin(2 * np.pi * 220 * t)).reshape(-1, 1)

            with redirect_stdout(StringIO()):
                self.assertTrue(window.process_audio("Chipmunk"))

            freqs = np.fft.rfftfreq(len(window.audio_data_processed), d=1 / samplerate)
            magnitudes = np.abs(np.fft.rfft(window.audio_data_processed.reshape(-1)))
            magnitudes[0] = 0
            dominant_frequency = freqs[int(np.argmax(magnitudes))]
            self.assertGreater(dominant_frequency, 280)
        finally:
            sys.path.remove(str(SRC))

    def test_main_window_uses_audio_visualisation_widget(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            sys.modules.pop("audio_visualisation_widget", None)
            from main import MainWindow

            window = MainWindow()

            self.assertEqual(window.visualisation_widget.__class__.__name__, "AudioVisualisationWidget")
            self.assertIsNone(window.visualisation_widget.visualisation_data)
        finally:
            sys.path.remove(str(SRC))

    def test_process_audio_updates_visualisation_widget(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            sys.modules.pop("audio_visualisation_widget", None)
            from main import MainWindow

            samplerate = 8000
            t = np.arange(samplerate, dtype=np.float32) / samplerate
            window = MainWindow()
            window.samplerate = samplerate
            window.audio_data = (0.7 * np.sin(2 * np.pi * 220 * t)).reshape(-1, 1)

            with redirect_stdout(StringIO()):
                self.assertTrue(window.process_audio("Chipmunk"))

            data = window.visualisation_widget.visualisation_data
            self.assertEqual(data.effect_name, "Chipmunk")
            self.assertAlmostEqual(data.original.dominant_frequency, 220, delta=2)
            self.assertGreater(data.processed.dominant_frequency, 280)
            self.assertGreater(window.visualisation_widget.update_count, 0)
        finally:
            sys.path.remove(str(SRC))

    def test_starting_new_recording_clears_visualisation_widget(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            sys.modules.pop("audio_visualisation_widget", None)
            from main import MainWindow

            samplerate = 8000
            t = np.arange(samplerate, dtype=np.float32) / samplerate
            window = MainWindow()
            window.samplerate = samplerate
            window.audio_data = (0.7 * np.sin(2 * np.pi * 220 * t)).reshape(-1, 1)
            with redirect_stdout(StringIO()):
                window.process_audio("Chipmunk")
                window.start_recording()

            self.assertIsNone(window.visualisation_widget.visualisation_data)
        finally:
            sys.path.remove(str(SRC))


if __name__ == "__main__":
    unittest.main()
