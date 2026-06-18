import sys
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton, QWidget, QVBoxLayout
import sounddevice as sd
import numpy as np

from audio_effects import EFFECT_NAMES, apply_effect
from audio_visualisation_widget import AudioVisualisationWidget


EFFECT_CARD_NAMES = tuple(effect_name for effect_name in EFFECT_NAMES if effect_name != "Normal")
EFFECT_COLORS = {
    "Chipmunk": "#f59e0b",
    "Giant": "#7c3aed",
    "Robot": "#06b6d4",
    "Radio": "#22c55e",
    "Alien": "#ec4899",
    "Echo": "#ef4444",
}
EFFECT_SUBTITLES = {
    "Chipmunk": "tiny and squeaky",
    "Giant": "deep and huge",
    "Robot": "metal voice",
    "Radio": "old speaker",
    "Alien": "space wobble",
    "Echo": "bouncy repeat",
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.audio_data_processed = None
        self.is_recording = False
        self.samplerate = 44100
        self.selected_effect_names = []
        self.selected_effect_name = self._effect_chain_name()
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)
        self.playback_elapsed_seconds = 0.0
        self.playback_duration_seconds = 0.0
        self.playback_ready_status = "Ready"

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1100, 760)
        self.setWindowTitle('Open Day Voice Effects Demo')
        self.setStyleSheet(
            """
            QMainWindow { background: #111827; }
            QWidget { background: #111827; color: #f8fafc; font-family: Arial; }
            QPushButton {
                background: #1f2937;
                border: 2px solid #374151;
                border-radius: 8px;
                color: #f8fafc;
                font-size: 17px;
                font-weight: 700;
                min-height: 40px;
                padding: 8px 14px;
            }
            QPushButton:disabled {
                color: #6b7280;
                background: #171923;
                border-color: #1f2937;
            }
            QLabel { color: #f8fafc; }
            """
        )

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(9)
        centralWidget.setLayout(layout)

        self.title_label = QLabel("Voice Changer")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #f8fafc;")
        layout.addWidget(self.title_label)

        self.status_label = QLabel("Step 1: Record your voice")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet(
            "background: #0f172a; border: 2px solid #334155; border-radius: 8px; "
            "padding: 8px 12px; font-size: 16px; font-weight: 700; color: #cbd5e1;"
        )
        layout.addWidget(self.status_label)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        self.record_button = QPushButton('Record')
        self.record_button.setObjectName('recordButton')
        self.record_button.setStyleSheet(
            "background: #dc2626; border-color: #f87171; color: #ffffff; "
            "font-size: 20px; min-height: 46px;"
        )
        self.record_button.clicked.connect(self.start_recording)
        self.play_original_button = QPushButton('Play Original')
        self.play_original_button.setObjectName('playOriginalButton')
        self.play_original_button.clicked.connect(self.play_original)
        self.play_filtered_button = QPushButton(self._effect_play_label())
        self.play_filtered_button.setObjectName('playFilteredButton')
        self.play_filtered_button.clicked.connect(self.play_filtered)

        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.play_original_button)
        controls_layout.addWidget(self.play_filtered_button)
        layout.addLayout(controls_layout)

        effects_layout = QGridLayout()
        effects_layout.setSpacing(10)
        self.effect_buttons = {}
        for index, effect_name in enumerate(EFFECT_CARD_NAMES):
            button = QPushButton()
            button.setObjectName(f"effectButton{effect_name}")
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, name=effect_name: self.effect_selected(name))
            self.effect_buttons[effect_name] = button
            effects_layout.addWidget(button, index // 3, index % 3)
        layout.addLayout(effects_layout)

        self.visualisation_widget = AudioVisualisationWidget()
        self.waveformAndFftCanvas = self.visualisation_widget
        layout.addWidget(self.visualisation_widget, 1)
        self._refresh_effect_cards()
        self._update_control_state()

    def start_recording(self):
        if self.is_recording:
            print("Stopping recording...")
            self.recording_stream.stop()
            self.recording_stream.close()
            self.is_recording = False
            self.record_button.setText("Record")
            if self.audio_data is not None:
                self.process_audio(self.selected_effect_names)
                self._set_status(f"Ready: {self.selected_effect_name} is selected")
            else:
                self._set_status("No sound captured. Tap Record to try again")
            self._update_control_state()
            return

        print("Starting recording...")
        sd.stop()
        self.playback_timer.stop()
        self.playback_elapsed_seconds = 0.0
        self.is_recording = True
        self.audio_data = None
        self.audio_data_processed = None
        self.visualisation_widget.clear()
        self._set_status("Recording... tap Stop when you are done")
        
        # Set up the recording callback
        self.recording_callback = self._record_audio_callback
        self.recording_stream = sd.InputStream(samplerate=self.samplerate, channels=1, callback=self.recording_callback)
        self.recording_stream.start()
        
        self.record_button.setText("Stop")
        self._update_control_state()

    def _record_audio_callback(self, indata, frames, time, status):
        """This is called by sounddevice for each audio block."""
        if status:
            print(f"Recording status warning: {status}", file=sys.stderr)
        
        # Append the captured data to the audio_data list
        if self.audio_data is None:
            self.audio_data = np.copy(indata)
        else:
            self.audio_data = np.concatenate((self.audio_data, np.copy(indata)), axis=0)

    def play_original(self):
        if self.is_recording:
            print("Stop recording before playback.")
            self._set_status("Stop recording before playback")
            return

        if self.audio_data is not None:
            print("Playing original audio...")
            self._set_status("Playing original")
            self._play_audio(self.audio_data, f"Ready: {self.selected_effect_name} is selected")
        else:
            print("No audio recorded.")
            self._set_status("Tap Record first")

    def process_audio(self, effect_names):
        if self.audio_data is None:
            print("Cannot process: No original audio recorded.")
            return False

        effect_chain = self._normalise_effect_names(effect_names)
        effect_label = self._effect_chain_name(effect_chain)
        print(f"Processing audio with effect: {effect_label}...")

        processed_audio = np.copy(self.audio_data)
        for effect_name in effect_chain:
            processed_audio = apply_effect(processed_audio, effect_name, self.samplerate)

        self.audio_data_processed = processed_audio
        self.visualisation_widget.set_audio(
            self.audio_data,
            self.audio_data_processed,
            effect_label,
            self.samplerate,
        )
        print("Processing complete.")
        self._update_control_state()
        return True

    def play_filtered(self):
        if self.is_recording:
            print("Stop recording before playback.")
            self._set_status("Stop recording before playback")
            return

        if self.audio_data_processed is None and self.audio_data is not None:
            self.process_audio(self.selected_effect_names)

        if self.audio_data_processed is not None:
            print("Playing filtered audio...")
            self._set_status(f"Playing {self.selected_effect_name}")
            self._play_audio(self.audio_data_processed, f"Ready: {self.selected_effect_name} is selected")
        else:
            print("No processed audio available.")
            self._set_status("Tap Record first")

    def effect_selected(self, effect_name):
        if effect_name not in EFFECT_CARD_NAMES:
            return

        if effect_name in self.selected_effect_names:
            self.selected_effect_names.remove(effect_name)
        else:
            self.selected_effect_names.append(effect_name)
        self.selected_effect_name = self._effect_chain_name()
        self._refresh_effect_cards()
        if self.audio_data is not None:
            self.process_audio(self.selected_effect_names)
            self._set_status(f"Ready: {self.selected_effect_name} is selected")
        else:
            self.audio_data_processed = None
            self.visualisation_widget.clear()
            self._set_status(f"Record your voice, then try {self.selected_effect_name}")
            print("Please record audio first to apply effects.")
        self._update_control_state()

    def _play_audio(self, audio_data, ready_status):
        try:
            sd.stop()
            sd.play(audio_data, self.samplerate)
            self.playback_elapsed_seconds = 0.0
            self.playback_duration_seconds = max(len(audio_data) / float(self.samplerate), 0.001)
            self.playback_ready_status = ready_status
            self.visualisation_widget.set_playback_progress(0.0)
            self.playback_timer.start(33)
        except Exception as e:
            print(f"Error playing audio: {e}")
            self._set_status("Audio playback failed")

    def _advance_playback(self):
        self.playback_elapsed_seconds += 0.033
        progress = min(1.0, self.playback_elapsed_seconds / self.playback_duration_seconds)
        self.visualisation_widget.set_playback_progress(progress)
        if progress >= 1.0:
            self.playback_timer.stop()
            self._set_status(self.playback_ready_status)

    def _set_status(self, text):
        self.status_label.setText(text)

    def _update_control_state(self):
        has_audio = self.audio_data is not None
        can_play = has_audio and not self.is_recording
        self.play_original_button.setEnabled(can_play)
        self.play_filtered_button.setEnabled(can_play)
        for button in self.effect_buttons.values():
            button.setEnabled(not self.is_recording)

    def _refresh_effect_cards(self):
        for effect_name, button in self.effect_buttons.items():
            selected = effect_name in self.selected_effect_names
            button.setChecked(selected)
            color = EFFECT_COLORS[effect_name]
            indicator = "● ON" if selected else "○ OFF"
            button.setText(f"{effect_name}\n{EFFECT_SUBTITLES[effect_name]}\n{indicator}")
            border_width = 4 if selected else 2
            background = color if selected else "#1f2937"
            text_color = "#111827" if selected else "#f8fafc"
            button.setStyleSheet(
                f"background: {background}; border: {border_width}px solid {color}; "
                f"border-radius: 9px; color: {text_color}; font-size: 17px; "
                f"font-weight: 800; min-height: 58px; padding: 6px;"
            )
        self.play_filtered_button.setText(self._effect_play_label())

    def _normalise_effect_names(self, effect_names):
        if isinstance(effect_names, str):
            return [] if effect_names == "Normal" else [effect_names]
        return [effect_name for effect_name in effect_names if effect_name in EFFECT_CARD_NAMES]

    def _effect_chain_name(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else effect_names
        if not names:
            return "Normal"
        return " + ".join(names)

    def _effect_play_label(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else self._normalise_effect_names(effect_names)
        if not names:
            return "Play Normal"
        if len(names) == 1:
            return f"Play {names[0]}"
        return "Play Chain"

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
