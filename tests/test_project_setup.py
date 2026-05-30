import sys
import tomllib
import types
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path


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

    def setObjectName(self, name):
        self._object_name = name

    def objectName(self):
        return self._object_name


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


class FakeLayout:
    def __init__(self):
        self.widgets = []

    def addWidget(self, widget):
        self.widgets.append(widget)


class FakeContainer(FakeWidget):
    def __init__(self):
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
    qtwidgets = types.ModuleType("PySide6.QtWidgets")
    qtwidgets.QApplication = object
    qtwidgets.QComboBox = FakeComboBox
    qtwidgets.QLabel = FakeLabel
    qtwidgets.QMainWindow = FakeMainWindow
    qtwidgets.QPushButton = FakeButton
    qtwidgets.QVBoxLayout = FakeLayout
    qtwidgets.QWidget = FakeContainer

    pyside = types.ModuleType("PySide6")
    pyside.QtWidgets = qtwidgets

    sounddevice = types.ModuleType("sounddevice")
    sounddevice.InputStream = FakeInputStream
    sounddevice.play = lambda *args, **kwargs: None
    sounddevice.wait = lambda: None

    sys.modules["PySide6"] = pyside
    sys.modules["PySide6.QtWidgets"] = qtwidgets
    sys.modules["sounddevice"] = sounddevice


class ProjectSetupTests(unittest.TestCase):
    def test_pyproject_uses_current_project_metadata(self):
        with (ROOT / "pyproject.toml").open("rb") as pyproject:
            metadata = tomllib.load(pyproject)

        self.assertIn("project", metadata)
        self.assertNotIn("poetry", metadata.get("tool", {}))

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


if __name__ == "__main__":
    unittest.main()
