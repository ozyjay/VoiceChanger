import sys
from pathlib import Path
from time import monotonic

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QMainWindow, QPushButton, QWidget, QVBoxLayout
import sounddevice as sd
import numpy as np

from audio_effects import EFFECT_NAMES, apply_effect, prepare_playback_audio
from audio_visualisation_widget import AudioVisualisationWidget


APP_ICON_PATH = Path(__file__).resolve().parents[1] / "assets" / "voice_changer_icon.png"
DESKTOP_FILE_NAME = "voicechanger"


def _load_app_icon():
    if APP_ICON_PATH.exists():
        return QIcon(str(APP_ICON_PATH))
    return None


EFFECT_CARD_NAMES = tuple(effect_name for effect_name in EFFECT_NAMES if effect_name != "Normal")
EFFECT_DECKS = {
    "Classic": ("Chipmunk", "Giant", "Robot", "Radio", "Alien", "Echo"),
    "Wild": ("Megaphone", "Underwater", "Vibrato", "Choir", "Monster", "Cave"),
}
EFFECT_COLORS = {
    "Chipmunk": "#f59e0b",
    "Giant": "#7c3aed",
    "Robot": "#06b6d4",
    "Radio": "#22c55e",
    "Alien": "#ec4899",
    "Echo": "#ef4444",
    "Megaphone": "#f97316",
    "Underwater": "#0ea5e9",
    "Vibrato": "#84cc16",
    "Choir": "#a78bfa",
    "Monster": "#16a34a",
    "Cave": "#94a3b8",
}
EFFECT_SUBTITLES = {
    "Chipmunk": "tiny and squeaky",
    "Giant": "deep and huge",
    "Robot": "metal voice",
    "Radio": "old speaker",
    "Alien": "space wobble",
    "Echo": "bouncy repeat",
    "Megaphone": "loud speaker",
    "Underwater": "muffled wobble",
    "Vibrato": "pitch wiggle",
    "Choir": "many voices",
    "Monster": "deep growl",
    "Cave": "big echoes",
}
EFFECT_EXPLANATIONS = {
    "Chipmunk": "Chipmunk raises the pitch so the voice sounds smaller and squeakier.",
    "Giant": "Giant lowers the pitch so the voice sounds deeper and bigger.",
    "Robot": "Robot adds fast modulation to make the voice sound mechanical.",
    "Radio": "Radio filters the voice band so it sounds like an old speaker.",
    "Alien": "Alien combines pitch, wobble, and echo for a strange space voice.",
    "Echo": "Echo adds a delayed copy of the voice so words bounce back.",
    "Megaphone": "Megaphone squeezes the voice into a loud speaker band with light distortion.",
    "Underwater": "Underwater muffles the voice and adds a slow wobble.",
    "Vibrato": "Vibrato wiggles the pitch smoothly up and down.",
    "Choir": "Choir layers slightly shifted copies so one voice sounds like several.",
    "Monster": "Monster drops the pitch and adds a low growl.",
    "Cave": "Cave adds long echoes so the voice sounds far away in a big space.",
}

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.audio_data_processed = None
        self.is_recording = False
        self.samplerate = 44100
        self.active_effect_deck = "Classic"
        self.selected_effect_names = []
        self.selected_effect_name = self._effect_chain_name()
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._advance_playback)
        self._playback_clock = monotonic
        self._playback_started_at = None
        self.playback_elapsed_seconds = 0.0
        self.playback_duration_seconds = 0.0
        self.playback_ready_status = "Ready"
        self.recording_limit_seconds = 5
        self.recording_limit_timer = QTimer(self)
        self.recording_limit_timer.timeout.connect(lambda: self._stop_recording(auto_stopped=True))
        self.recording_countdown_timer = QTimer(self)
        self.recording_countdown_timer.timeout.connect(self._update_recording_countdown)

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 1280, 820)
        self.setWindowTitle('Voice Changer Live')
        app_icon = _load_app_icon()
        if app_icon is not None:
            self.setWindowIcon(app_icon)
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
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)
        centralWidget.setLayout(layout)

        self.top_info_widget = QWidget()
        self.top_info_widget.setObjectName("topInfoBand")
        top_info_layout = QVBoxLayout()
        top_info_layout.setContentsMargins(0, 0, 0, 0)
        top_info_layout.setSpacing(6)
        self.top_info_widget.setLayout(top_info_layout)
        layout.addWidget(self.top_info_widget)

        info_labels_layout = QHBoxLayout()
        info_labels_layout.setSpacing(8)
        top_info_layout.addLayout(info_labels_layout)

        self.title_label = QLabel("Voice Changer Live")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 900; color: #f8fafc;")
        info_labels_layout.addWidget(self.title_label, 0)

        self.status_label = QLabel("Step 1: Record your voice")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet(
            "background: #0f172a; border: 2px solid #334155; border-radius: 8px; "
            "padding: 5px 10px; font-size: 15px; font-weight: 700; color: #cbd5e1;"
        )
        info_labels_layout.addWidget(self.status_label, 1)

        self.active_chain_label = QLabel(self._effect_chain_display())
        self.active_chain_label.setObjectName("activeChainLabel")
        self.active_chain_label.setStyleSheet(
            "background: #020617; border: 2px solid #38bdf8; border-radius: 8px; "
            "padding: 6px 10px; font-size: 16px; font-weight: 900; color: #e0f2fe;"
        )
        info_labels_layout.addWidget(self.active_chain_label, 1)

        self.explanation_label = QLabel(self._effect_explanation())
        self.explanation_label.setObjectName("explanationLabel")
        self.explanation_label.setStyleSheet(
            "background: #172033; border: 2px solid #475569; border-radius: 8px; "
            "padding: 6px 10px; font-size: 14px; font-weight: 700; color: #f8fafc;"
        )
        info_labels_layout.addWidget(self.explanation_label, 2)

        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(10)
        self.record_button = QPushButton('Record')
        self.record_button.setObjectName('recordButton')
        self.record_button.setStyleSheet(
            "background: #dc2626; border-color: #f87171; color: #ffffff; "
            "font-size: 18px; min-height: 40px;"
        )
        self.record_button.clicked.connect(self.start_recording)
        self.play_original_button = QPushButton('Play Original')
        self.play_original_button.setObjectName('playOriginalButton')
        self.play_original_button.clicked.connect(self.play_original)
        self.play_filtered_button = QPushButton(self._effect_play_label())
        self.play_filtered_button.setObjectName('playFilteredButton')
        self.play_filtered_button.clicked.connect(self.play_filtered)
        self.reset_button = QPushButton('Reset / Next Visitor')
        self.reset_button.setObjectName('resetButton')
        self.reset_button.clicked.connect(self._reset_for_next_visitor)

        controls_layout.addWidget(self.record_button)
        controls_layout.addWidget(self.play_original_button)
        controls_layout.addWidget(self.play_filtered_button)
        controls_layout.addWidget(self.reset_button)
        top_info_layout.addLayout(controls_layout)

        body_layout = QHBoxLayout()
        body_layout.setSpacing(12)
        layout.addLayout(body_layout, 1)

        self.pedal_rail_widget = QWidget()
        self.pedal_rail_widget.setObjectName("pedalRail")
        self.pedal_rail_widget.setFixedWidth(250)
        pedal_rail_layout = QVBoxLayout()
        pedal_rail_layout.setContentsMargins(0, 0, 0, 0)
        pedal_rail_layout.setSpacing(10)
        self.pedal_rail_widget.setLayout(pedal_rail_layout)
        deck_layout = QHBoxLayout()
        deck_layout.setSpacing(6)
        self.effect_deck_buttons = {}
        for deck_name in EFFECT_DECKS:
            deck_button = QPushButton(deck_name)
            deck_button.setObjectName(f"effectDeckButton{deck_name}")
            deck_button.setCheckable(True)
            deck_button.clicked.connect(lambda _checked=False, name=deck_name: self._set_active_effect_deck(name))
            self.effect_deck_buttons[deck_name] = deck_button
            deck_layout.addWidget(deck_button)
        pedal_rail_layout.addLayout(deck_layout)
        effects_layout = QVBoxLayout()
        effects_layout.setSpacing(10)
        pedal_rail_layout.addLayout(effects_layout)
        self.effect_buttons = {}
        self.effect_button_slots = []
        for index in range(len(EFFECT_DECKS["Classic"])):
            button = QPushButton()
            button.setCheckable(True)
            button.clicked.connect(lambda _checked=False, slot_index=index: self._effect_slot_selected(slot_index))
            self.effect_button_slots.append(button)
            effects_layout.addWidget(button)
        body_layout.addWidget(self.pedal_rail_widget, 0)

        self.visual_pane_widget = QWidget()
        self.visual_pane_widget.setObjectName("visualPane")
        visual_pane_layout = QVBoxLayout()
        visual_pane_layout.setContentsMargins(0, 0, 0, 0)
        visual_pane_layout.setSpacing(8)
        self.visual_pane_widget.setLayout(visual_pane_layout)
        body_layout.addWidget(self.visual_pane_widget, 1)

        self.visualisation_widget = AudioVisualisationWidget()
        self.visualisation_widget.on_waveform_follow_changed = self._set_waveform_follow_button_checked
        self.waveformAndFftCanvas = self.visualisation_widget

        zoom_layout = QHBoxLayout()
        zoom_layout.setSpacing(8)
        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.setObjectName("zoomInButton")
        self.zoom_in_button.clicked.connect(lambda _checked=False: self.visualisation_widget.zoom_in_waveform())
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.setObjectName("zoomOutButton")
        self.zoom_out_button.clicked.connect(lambda _checked=False: self.visualisation_widget.zoom_out_waveform())
        self.zoom_reset_button = QPushButton("Reset Zoom")
        self.zoom_reset_button.setObjectName("zoomResetButton")
        self.zoom_reset_button.clicked.connect(lambda _checked=False: self.visualisation_widget.reset_waveform_zoom())
        self.follow_button = QPushButton()
        self.follow_button.setObjectName("followButton")
        self.follow_button.setCheckable(True)
        self.follow_button.clicked.connect(lambda _checked=False: self._toggle_waveform_follow())
        for button in (self.zoom_in_button, self.zoom_out_button, self.zoom_reset_button):
            button.setStyleSheet(
                "background: #111827; border: 2px solid #475569; border-radius: 7px; "
                "font-size: 13px; font-weight: 800; min-height: 28px; padding: 4px 10px;"
            )
            zoom_layout.addWidget(button)
        self._set_waveform_follow_button_checked(True)
        zoom_layout.addWidget(self.follow_button)
        visual_pane_layout.addLayout(zoom_layout)
        visual_pane_layout.addWidget(self.visualisation_widget, 1)
        self._refresh_effect_cards()
        self._update_control_state()

    def start_recording(self):
        if self.is_recording:
            self._stop_recording(auto_stopped=False)
            return

        print("Starting recording...")
        try:
            sd.stop()
            self.playback_timer.stop()
            self._playback_started_at = None
            self.playback_elapsed_seconds = 0.0
            self.audio_data = None
            self.audio_data_processed = None
            self.visualisation_widget.clear()
            self._set_status(f"Recording... {self.recording_limit_seconds} seconds left")

            self.recording_callback = self._record_audio_callback
            self.recording_stream = sd.InputStream(samplerate=self.samplerate, channels=1, callback=self.recording_callback)
            self.recording_stream.start()

            self.is_recording = True
            self.record_button.setText("Stop")
            self._start_recording_timeout()
            self._update_control_state()
        except Exception as e:
            print(f"Error starting microphone input: {e}")
            self.is_recording = False
            self.record_button.setText("Record")
            self.recording_limit_timer.stop()
            self.recording_countdown_timer.stop()
            self.audio_data = None
            self.audio_data_processed = None
            self._set_status("Microphone unavailable. Check input device and try again")
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

    def _start_recording_timeout(self):
        self.recording_limit_timer.start(self.recording_limit_seconds * 1000)
        self.recording_countdown_timer.start(250)

    def _stop_recording(self, auto_stopped=False):
        if not self.is_recording:
            return

        print("Stopping recording...")
        self.recording_limit_timer.stop()
        self.recording_countdown_timer.stop()
        try:
            self.recording_stream.stop()
            self.recording_stream.close()
        except Exception as e:
            print(f"Error stopping microphone input: {e}")

        self.is_recording = False
        self.record_button.setText("Record")
        if self.audio_data is not None and len(self.audio_data) > 0:
            self.process_audio(self.selected_effect_names)
            if auto_stopped:
                self._set_status("Recording captured. Step 3: Play Original or hear the effect")
            else:
                self._set_status(f"Ready: {self.selected_effect_name} is selected")
        else:
            self._set_status("No sound captured. Tap Record to try again")
        self._update_control_state()

    def _update_recording_countdown(self):
        captured_seconds = 0.0
        if self.audio_data is not None:
            captured_seconds = len(self.audio_data) / float(self.samplerate)
        seconds_left = max(0.0, self.recording_limit_seconds - captured_seconds)
        self._set_status(f"Recording... {seconds_left:.1f} seconds left")

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
        if self._is_playing():
            self._set_status("Wait for playback to finish before changing effects")
            return

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
            self._set_status(f"Step 2: Choose effects. Step 1 is still to record your voice for {self.selected_effect_name}")
            print("Please record audio first to apply effects.")
        self._update_control_state()

    def _play_audio(self, audio_data, ready_status):
        try:
            sd.stop()
            playback_audio = prepare_playback_audio(audio_data, samplerate=self.samplerate)
            sd.play(playback_audio, self.samplerate)
            self._playback_started_at = self._playback_clock()
            self.playback_elapsed_seconds = 0.0
            self.playback_duration_seconds = max(len(playback_audio) / float(self.samplerate), 0.001)
            self.playback_ready_status = ready_status
            self.visualisation_widget.set_playback_progress(0.0)
            self.playback_timer.start(33)
            self._update_control_state()
        except Exception as e:
            print(f"Error playing audio: {e}")
            self._set_status("Audio playback failed")
            self.playback_timer.stop()
            self._playback_started_at = None
            self._update_control_state()

    def _advance_playback(self):
        if self._playback_started_at is None:
            return

        self.playback_elapsed_seconds = max(0.0, self._playback_clock() - self._playback_started_at)
        progress = min(1.0, self.playback_elapsed_seconds / self.playback_duration_seconds)
        self.visualisation_widget.set_playback_progress(progress)
        if progress >= 1.0:
            self.playback_timer.stop()
            self._playback_started_at = None
            self._set_status(self.playback_ready_status)
            self._update_control_state()

    def _set_status(self, text):
        self.status_label.setText(text)

    def _toggle_waveform_follow(self):
        enabled = not self.visualisation_widget.waveform_follow_enabled
        self.visualisation_widget.set_waveform_follow_enabled(enabled)
        self._set_waveform_follow_button_checked(enabled)

    def _set_waveform_follow_button_checked(self, enabled):
        self.follow_button.setChecked(enabled)
        self.follow_button.setText("Follow: On" if enabled else "Follow: Off")
        if enabled:
            self.follow_button.setStyleSheet(
                "background: #0f2a3a; border: 2px solid #38bdf8; border-radius: 7px; "
                "font-size: 13px; font-weight: 900; min-height: 28px; padding: 4px 10px;"
            )
        else:
            self.follow_button.setStyleSheet(
                "background: #111827; border: 2px solid #475569; border-radius: 7px; "
                "font-size: 13px; font-weight: 800; min-height: 28px; padding: 4px 10px;"
            )

    def _update_control_state(self):
        has_audio = self.audio_data is not None
        can_play = has_audio and not self.is_recording
        can_change_effects = not self.is_recording and not self._is_playing()
        self.play_original_button.setEnabled(can_play)
        self.play_filtered_button.setEnabled(can_play)
        self.record_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        for button in self.effect_buttons.values():
            button.setEnabled(can_change_effects)
        for button in self.effect_deck_buttons.values():
            button.setEnabled(can_change_effects)

    def _reset_for_next_visitor(self):
        sd.stop()
        self.playback_timer.stop()
        self._playback_started_at = None
        self.recording_limit_timer.stop()
        self.recording_countdown_timer.stop()
        if self.is_recording:
            try:
                self.recording_stream.stop()
                self.recording_stream.close()
            except Exception as e:
                print(f"Error stopping microphone input during reset: {e}")
        self.is_recording = False
        self.record_button.setText("Record")
        self.audio_data = None
        self.audio_data_processed = None
        self.visualisation_widget.clear()
        # Reset effects for public demos so each visitor starts from the same clear Normal voice state.
        self.selected_effect_names = []
        self.selected_effect_name = self._effect_chain_name()
        self.active_effect_deck = "Classic"
        self._refresh_effect_cards()
        self._set_status("Step 1: Record your voice")
        self._update_control_state()

    def _refresh_effect_cards(self):
        self.effect_buttons = {}
        for effect_name, button in zip(self._visible_effect_names(), self.effect_button_slots):
            self.effect_buttons[effect_name] = button
            button.setObjectName(f"effectButton{effect_name}")
            selected = effect_name in self.selected_effect_names
            button.setChecked(selected)
            color = EFFECT_COLORS[effect_name]
            indicator = "LED ● ON" if selected else "LED ○ OFF"
            button.setText(
                f"{effect_name.upper()}\n"
                f"{EFFECT_SUBTITLES[effect_name]}\n"
                f"{indicator}"
                f"{self._effect_pedal_flow_label(effect_name)}"
            )
            border_width = 4 if selected else 2
            background = color if selected else "#243044"
            text_color = "#0f172a" if selected else "#e5e7eb"
            accent_top = "#fef3c7" if selected else "#64748b"
            button.setStyleSheet(
                f"background: {background}; border: {border_width}px solid {color}; "
                f"border-top: 5px solid {accent_top}; border-radius: 14px; "
                f"color: {text_color}; font-size: 13px; font-weight: 900; "
                f"min-height: 72px; padding: 6px 8px;"
            )
        for deck_name, button in self.effect_deck_buttons.items():
            selected = deck_name == self.active_effect_deck
            button.setChecked(selected)
            if selected:
                button.setStyleSheet(
                    "background: #38bdf8; border: 2px solid #bae6fd; border-radius: 8px; "
                    "color: #082f49; font-size: 13px; font-weight: 900; min-height: 32px; padding: 4px 8px;"
                )
            else:
                button.setStyleSheet(
                    "background: #111827; border: 2px solid #475569; border-radius: 8px; "
                    "color: #cbd5e1; font-size: 13px; font-weight: 800; min-height: 32px; padding: 4px 8px;"
                )
        self.play_filtered_button.setText(self._effect_play_label())
        self.active_chain_label.setText(self._effect_chain_display())
        self.explanation_label.setText(self._effect_explanation())

    def _visible_effect_names(self):
        return EFFECT_DECKS[self.active_effect_deck]

    def _set_active_effect_deck(self, deck_name):
        if self._is_playing():
            self._set_status("Wait for playback to finish before changing effects")
            return

        if deck_name not in EFFECT_DECKS:
            return
        self.active_effect_deck = deck_name
        self._refresh_effect_cards()
        self._update_control_state()

    def _effect_slot_selected(self, slot_index):
        visible_effect_names = self._visible_effect_names()
        if 0 <= slot_index < len(visible_effect_names):
            self.effect_selected(visible_effect_names[slot_index])

    def _effect_pedal_flow_label(self, effect_name):
        if effect_name not in self.selected_effect_names:
            return ""

        chain_index = self.selected_effect_names.index(effect_name)
        input_name = "Normal" if chain_index == 0 else self.selected_effect_names[chain_index - 1]
        return f"\n{chain_index + 1}: {input_name} → {effect_name}"

    def _normalise_effect_names(self, effect_names):
        if isinstance(effect_names, str):
            return [] if effect_names == "Normal" else [effect_names]
        return [effect_name for effect_name in effect_names if effect_name in EFFECT_CARD_NAMES]

    def _effect_chain_name(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else effect_names
        if not names:
            return "Normal"
        return " + ".join(names)

    def _effect_chain_display(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else self._normalise_effect_names(effect_names)
        if not names:
            return "ACTIVE CHAIN: Normal voice"
        return f"ACTIVE CHAIN: {' → '.join(names)}"

    def _effect_explanation(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else self._normalise_effect_names(effect_names)
        if not names:
            return "What changed? Nothing yet: this is your plain voice, ready for comparison."
        if len(names) == 1:
            return f"What changed? {EFFECT_EXPLANATIONS[names[0]]}"
        return f"What changed? Effects are chained in order: {' → '.join(names)}. Each pedal changes the sound before the next one hears it."

    def _effect_play_label(self, effect_names=None):
        names = self.selected_effect_names if effect_names is None else self._normalise_effect_names(effect_names)
        if not names:
            return "Play Normal"
        if len(names) == 1:
            return f"Play {names[0]}"
        return "Play Chain"

    def _is_playing(self):
        return self.playback_timer.isActive()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("Voice Changer Live")
    app.setDesktopFileName(DESKTOP_FILE_NAME)
    app_icon = _load_app_icon()
    if app_icon is not None and hasattr(app, "setWindowIcon"):
        app.setWindowIcon(app_icon)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
