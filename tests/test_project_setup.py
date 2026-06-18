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

    def emit(self, *args, **kwargs):
        if self.callback is not None:
            self.callback(*args, **kwargs)


class FakeWidget:
    def __init__(self, *args, **kwargs):
        self._object_name = ""
        self.minimum_height = None
        self.update_count = 0
        self.enabled = True
        self.style_sheet = ""

    def setObjectName(self, name):
        self._object_name = name

    def objectName(self):
        return self._object_name

    def setMinimumHeight(self, height):
        self.minimum_height = height

    def setStyleSheet(self, style_sheet):
        self.style_sheet = style_sheet

    def setEnabled(self, enabled):
        self.enabled = bool(enabled)

    def isEnabled(self):
        return self.enabled

    def update(self):
        self.update_count += 1


class FakeButton(FakeWidget):
    def __init__(self, text=""):
        super().__init__()
        self._text = text
        self.clicked = FakeSignal()
        self.checkable = False
        self.checked = False

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setCheckable(self, checkable):
        self.checkable = bool(checkable)

    def setChecked(self, checked):
        self.checked = bool(checked)

    def isChecked(self):
        return self.checked


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
        self.layouts = []

    def addWidget(self, widget, *args):
        widget.layout_args = args
        self.widgets.append(widget)

    def addLayout(self, layout):
        self.layouts.append(layout)

    def setSpacing(self, spacing):
        self.spacing = spacing

    def setContentsMargins(self, *margins):
        self.margins = margins


class FakeGridLayout(FakeLayout):
    def addWidget(self, widget, *args):
        widget.grid_position = args
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


class FakeTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = FakeSignal()
        self.active = False
        self.interval = None

    def start(self, interval=None):
        self.active = True
        self.interval = interval

    def stop(self):
        self.active = False

    def isActive(self):
        return self.active


def install_fake_modules():
    qtcore = types.ModuleType("PySide6.QtCore")
    qtcore.QPointF = object
    qtcore.QRectF = object
    qtcore.QTimer = FakeTimer
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
    qtwidgets.QGridLayout = FakeGridLayout
    qtwidgets.QHBoxLayout = FakeLayout
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
    sounddevice.play_calls = []
    sounddevice.stop_calls = 0
    sounddevice.wait_calls = 0

    def play(*args, **kwargs):
        sounddevice.play_calls.append((args, kwargs))

    def stop():
        sounddevice.stop_calls += 1

    def wait():
        sounddevice.wait_calls += 1

    sounddevice.play = play
    sounddevice.stop = stop
    sounddevice.wait = wait

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
            self.assertEqual(window.record_button.text(), "Stop")
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

    def test_audio_visualisation_widget_uses_two_teaching_comparison_panels(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("audio_visualisation_widget", None)
            from audio_visualisation_widget import AudioVisualisationWidget

            widget = AudioVisualisationWidget()

            self.assertEqual(widget.comparison_panel_titles, ("Sound shape", "Pitch + brightness"))
        finally:
            sys.path.remove(str(SRC))

    def test_audio_visualisation_widget_zoom_window_follows_playback(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("audio_visualisation_widget", None)
            from audio_visualisation_widget import AudioVisualisationWidget

            widget = AudioVisualisationWidget()
            samplerate = 8000
            audio = np.ones((samplerate * 2, 1), dtype=np.float32) * 0.2
            widget.set_audio(audio, audio, "Normal", samplerate)

            self.assertEqual(widget.waveform_zoom, 1.0)
            self.assertEqual(widget._waveform_time_window(), (0.0, 2.0))

            widget.zoom_in_waveform()
            self.assertEqual(widget.waveform_zoom, 2.0)
            self.assertEqual(widget._waveform_time_window(), (0.0, 1.0))

            widget.set_playback_progress(0.75)
            self.assertEqual(widget._waveform_time_window(), (1.0, 2.0))

            widget.reset_waveform_zoom()
            self.assertEqual(widget.waveform_zoom, 1.0)
            self.assertEqual(widget._waveform_time_window(), (0.0, 2.0))
        finally:
            sys.path.remove(str(SRC))

    def test_audio_visualisation_widget_follow_can_be_disabled_for_manual_inspection(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("audio_visualisation_widget", None)
            from audio_visualisation_widget import AudioVisualisationWidget

            widget = AudioVisualisationWidget()
            samplerate = 8000
            audio = np.ones((samplerate * 2, 1), dtype=np.float32) * 0.2
            widget.set_audio(audio, audio, "Normal", samplerate)
            widget.zoom_in_waveform()
            widget.set_waveform_follow_enabled(False)
            widget.set_playback_progress(0.75)

            self.assertFalse(widget.waveform_follow_enabled)
            self.assertEqual(widget._waveform_time_window(), (0.0, 1.0))
        finally:
            sys.path.remove(str(SRC))

    def test_main_window_creates_large_effect_cards_without_dropdown(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            self.assertFalse(hasattr(window, "effect_combo_box"))
            self.assertEqual(
                set(window.effect_buttons),
                {"Chipmunk", "Giant", "Robot", "Radio", "Alien", "Echo"},
            )
            self.assertEqual(window.selected_effect_names, [])
            self.assertEqual(window.selected_effect_name, "Normal")
            self.assertFalse(window.effect_buttons["Chipmunk"].isChecked())
            self.assertEqual(window.play_filtered_button.text(), "Play Normal")
            self.assertIn("○ OFF", window.effect_buttons["Chipmunk"].text())
            self.assertNotIn("INPUT", window.effect_buttons["Chipmunk"].text())
            self.assertNotIn("OUTPUT", window.effect_buttons["Chipmunk"].text())
        finally:
            sys.path.remove(str(SRC))

    def test_effect_pedals_show_strong_on_state_and_dynamic_play_label(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            with redirect_stdout(StringIO()):
                window.effect_selected("Echo")

            self.assertEqual(window.selected_effect_names, ["Echo"])
            self.assertEqual(window.selected_effect_name, "Echo")
            self.assertTrue(window.effect_buttons["Echo"].isChecked())
            self.assertIn("● ON", window.effect_buttons["Echo"].text())
            self.assertIn("background: #ef4444", window.effect_buttons["Echo"].style_sheet)
            self.assertEqual(window.play_filtered_button.text(), "Play Echo")

            with redirect_stdout(StringIO()):
                window.effect_selected("Robot")

            self.assertEqual(window.selected_effect_names, ["Echo", "Robot"])
            self.assertEqual(window.selected_effect_name, "Echo + Robot")
            self.assertIn("● ON", window.effect_buttons["Robot"].text())
            self.assertEqual(window.play_filtered_button.text(), "Play Chain")
        finally:
            sys.path.remove(str(SRC))

    def test_effect_pedals_use_guitar_stompbox_visual_cues(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            echo_button = window.effect_buttons["Echo"]

            self.assertIn("ECHO", echo_button.text())
            self.assertIn("bouncy repeat", echo_button.text())
            self.assertIn("LED ○ OFF", echo_button.text())
            self.assertIn("○ OFF", echo_button.text())
            self.assertNotIn("LEVEL", echo_button.text())
            self.assertNotIn("TONE", echo_button.text())
            self.assertNotIn("MIX", echo_button.text())
            self.assertNotIn("FOOTSWITCH", echo_button.text())
            self.assertIn("min-height: 72px", echo_button.style_sheet)
            self.assertIn("border-radius: 14px", echo_button.style_sheet)

            with redirect_stdout(StringIO()):
                window.effect_selected("Echo")

            self.assertIn("LED ● ON", echo_button.text())
            self.assertIn("● ON", echo_button.text())
            self.assertIn("border-top: 5px solid #fef3c7", echo_button.style_sheet)
        finally:
            sys.path.remove(str(SRC))

    def test_stage_layout_keeps_fixed_minimum_heights_inside_demo_window(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            sys.modules.pop("audio_visualisation_widget", None)
            from main import MainWindow

            window = MainWindow()

            self.assertEqual(window.geometry, (100, 100, 1100, 760))
            self.assertGreaterEqual(window.visualisation_widget.minimum_height, 340)
            self.assertLessEqual(window.visualisation_widget.minimum_height, 380)
            for button in window.effect_buttons.values():
                self.assertIn("min-height: 72px", button.style_sheet)
        finally:
            sys.path.remove(str(SRC))

    def test_open_day_stage_layout_shows_header_chain_and_reset_controls(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            self.assertEqual(window.title_label.text, "Voice Changer Live")
            self.assertEqual(window.active_chain_label.text, "ACTIVE CHAIN: Normal voice")
            self.assertEqual(window.reset_button.text(), "Reset / Next Visitor")
            self.assertIn("Record your voice", window.status_label.text)

            with redirect_stdout(StringIO()):
                window.effect_selected("Echo")
                window.effect_selected("Robot")

            self.assertEqual(window.active_chain_label.text, "ACTIVE CHAIN: Echo → Robot")
            self.assertIn("Choose effects", window.status_label.text)
        finally:
            sys.path.remove(str(SRC))

    def test_main_window_exposes_waveform_zoom_and_follow_controls(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            self.assertEqual(window.zoom_in_button.text(), "Zoom In")
            self.assertEqual(window.zoom_out_button.text(), "Zoom Out")
            self.assertEqual(window.zoom_reset_button.text(), "Reset Zoom")
            self.assertEqual(window.follow_button.text(), "Follow")
            self.assertTrue(window.follow_button.isChecked())

            window.zoom_in_button.clicked.emit()
            self.assertEqual(window.visualisation_widget.waveform_zoom, 2.0)

            window.zoom_out_button.clicked.emit()
            self.assertEqual(window.visualisation_widget.waveform_zoom, 1.0)

            window.zoom_in_button.clicked.emit()
            window.zoom_reset_button.clicked.emit()
            self.assertEqual(window.visualisation_widget.waveform_zoom, 1.0)

            window.follow_button.clicked.emit()
            self.assertFalse(window.visualisation_widget.waveform_follow_enabled)
            self.assertFalse(window.follow_button.isChecked())
        finally:
            sys.path.remove(str(SRC))

    def test_teaching_explanation_panel_tracks_active_effect_chain(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            self.assertIn("What changed?", window.explanation_label.text)
            self.assertIn("plain voice", window.explanation_label.text)

            with redirect_stdout(StringIO()):
                window.effect_selected("Chipmunk")

            self.assertIn("raises the pitch", window.explanation_label.text)
            self.assertIn("squeakier", window.explanation_label.text)

            with redirect_stdout(StringIO()):
                window.effect_selected("Echo")

            self.assertIn("chained in order", window.explanation_label.text)
            self.assertIn("Chipmunk → Echo", window.explanation_label.text)
        finally:
            sys.path.remove(str(SRC))

    def test_effect_cards_toggle_multiple_effects_and_reprocess_audio(self):
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
                window.effect_selected("Robot")

            self.assertEqual(window.selected_effect_names, ["Robot"])
            self.assertEqual(window.selected_effect_name, "Robot")
            self.assertTrue(window.effect_buttons["Robot"].isChecked())
            self.assertFalse(window.effect_buttons["Chipmunk"].isChecked())
            self.assertEqual(window.visualisation_widget.visualisation_data.effect_name, "Robot")
            self.assertIn("Robot", window.status_label.text)

            with redirect_stdout(StringIO()):
                window.effect_selected("Echo")

            self.assertEqual(window.selected_effect_names, ["Robot", "Echo"])
            self.assertFalse(window.effect_buttons["Chipmunk"].isChecked())
            self.assertTrue(window.effect_buttons["Robot"].isChecked())
            self.assertTrue(window.effect_buttons["Echo"].isChecked())
            self.assertEqual(window.visualisation_widget.visualisation_data.effect_name, "Robot + Echo")
            self.assertEqual(window.play_filtered_button.text(), "Play Chain")
        finally:
            sys.path.remove(str(SRC))

    def test_controls_are_disabled_until_recording_is_available_and_while_recording(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()

            self.assertFalse(window.play_original_button.isEnabled())
            self.assertFalse(window.play_filtered_button.isEnabled())

            with redirect_stdout(StringIO()):
                window.start_recording()

            self.assertFalse(window.play_original_button.isEnabled())
            self.assertFalse(window.play_filtered_button.isEnabled())
            self.assertTrue(window.recording_limit_timer.isActive())
            self.assertEqual(window.recording_limit_timer.interval, window.recording_limit_seconds * 1000)

            window.audio_data = np.ones((8, 1), dtype=np.float32)
            with redirect_stdout(StringIO()):
                window._stop_recording(auto_stopped=True)

            self.assertTrue(window.play_original_button.isEnabled())
            self.assertTrue(window.play_filtered_button.isEnabled())
            self.assertFalse(window.recording_limit_timer.isActive())
            self.assertFalse(window.recording_countdown_timer.isActive())
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
            self.assertLess(data.waveform_limit, 1.0)
            self.assertGreater(float(np.max(np.abs(data.difference_waveform_amplitudes))), 0.02)
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

    def test_playback_stops_current_output_before_playing_original(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            window.audio_data = np.ones((8, 1), dtype=np.float32)

            with redirect_stdout(StringIO()):
                window.play_original()

            sounddevice = sys.modules["sounddevice"]
            self.assertEqual(sounddevice.stop_calls, 1)
            self.assertEqual(len(sounddevice.play_calls), 1)
            self.assertEqual(sounddevice.wait_calls, 0)
            self.assertTrue(window.playback_timer.isActive())
            self.assertEqual(window.visualisation_widget.playback_progress, 0.0)
        finally:
            sys.path.remove(str(SRC))

    def test_playback_sends_limited_audio_to_output_device(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            window.audio_data = np.array([[-1.4], [0.0], [1.6]], dtype=np.float32)

            with redirect_stdout(StringIO()):
                window.play_original()

            sounddevice = sys.modules["sounddevice"]
            played_audio = sounddevice.play_calls[0][0][0]
            self.assertLessEqual(float(np.max(np.abs(played_audio))), 0.95)
            self.assertEqual(played_audio.dtype, np.float32)
        finally:
            sys.path.remove(str(SRC))

    def test_playback_timer_advances_visualisation_playhead_and_finishes(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            window.samplerate = 4
            window.audio_data = np.ones((4, 1), dtype=np.float32)

            with redirect_stdout(StringIO()):
                window.play_original()
                window._advance_playback()

            self.assertGreater(window.visualisation_widget.playback_progress, 0.0)

            with redirect_stdout(StringIO()):
                for _ in range(40):
                    window._advance_playback()

            self.assertEqual(window.visualisation_widget.playback_progress, 1.0)
            self.assertFalse(window.playback_timer.isActive())
            self.assertIn("Ready", window.status_label.text)
        finally:
            sys.path.remove(str(SRC))

    def test_playback_is_ignored_while_recording(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            window.audio_data = np.ones((8, 1), dtype=np.float32)
            window.audio_data_processed = np.ones((8, 1), dtype=np.float32)
            window.is_recording = True

            with redirect_stdout(StringIO()):
                window.play_original()
                window.play_filtered()

            sounddevice = sys.modules["sounddevice"]
            self.assertEqual(sounddevice.stop_calls, 0)
            self.assertEqual(sounddevice.play_calls, [])
            self.assertEqual(sounddevice.wait_calls, 0)
        finally:
            sys.path.remove(str(SRC))

    def test_reset_for_next_visitor_stops_audio_and_returns_to_clean_start(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            window = MainWindow()
            with redirect_stdout(StringIO()):
                window.start_recording()
            window.audio_data = np.ones((8, 1), dtype=np.float32)
            window.audio_data_processed = np.ones((8, 1), dtype=np.float32)
            window.selected_effect_names = ["Robot", "Echo"]
            window._refresh_effect_cards()

            with redirect_stdout(StringIO()):
                window._reset_for_next_visitor()

            sounddevice = sys.modules["sounddevice"]
            self.assertEqual(sounddevice.stop_calls, 2)
            self.assertFalse(window.is_recording)
            self.assertIsNone(window.audio_data)
            self.assertIsNone(window.audio_data_processed)
            self.assertIsNone(window.visualisation_widget.visualisation_data)
            self.assertEqual(window.selected_effect_names, [])
            self.assertEqual(window.active_chain_label.text, "ACTIVE CHAIN: Normal voice")
            self.assertEqual(window.play_filtered_button.text(), "Play Normal")
            self.assertIn("Step 1", window.status_label.text)
        finally:
            sys.path.remove(str(SRC))

    def test_recording_stream_failure_recovers_buttons_and_status(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            class BrokenInputStream:
                def __init__(self, *args, **kwargs):
                    raise RuntimeError("no microphone")

            sys.modules["sounddevice"].InputStream = BrokenInputStream
            window = MainWindow()

            with redirect_stdout(StringIO()):
                window.start_recording()

            self.assertFalse(window.is_recording)
            self.assertEqual(window.record_button.text(), "Record")
            self.assertFalse(window.recording_limit_timer.isActive())
            self.assertIn("Microphone unavailable", window.status_label.text)
        finally:
            sys.path.remove(str(SRC))

    def test_playback_failure_recovers_status_without_starting_timer(self):
        install_fake_modules()
        sys.path.insert(0, str(SRC))
        try:
            sys.modules.pop("main", None)
            from main import MainWindow

            def broken_play(*args, **kwargs):
                raise RuntimeError("no speaker")

            sys.modules["sounddevice"].play = broken_play
            window = MainWindow()
            window.audio_data = np.ones((8, 1), dtype=np.float32)

            with redirect_stdout(StringIO()):
                window.play_original()

            self.assertFalse(window.playback_timer.isActive())
            self.assertIn("Audio playback failed", window.status_label.text)
            self.assertTrue(window.play_original_button.isEnabled())
        finally:
            sys.path.remove(str(SRC))


if __name__ == "__main__":
    unittest.main()
