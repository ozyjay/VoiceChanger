import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QWidget, QVBoxLayout
import sounddevice as sd
import numpy as np

from audio_effects import EFFECT_NAMES, apply_effect
from audio_visualisation_widget import AudioVisualisationWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.audio_data = None
        self.audio_data_processed = None
        self.is_recording = False
        self.samplerate = 44100

        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Open Day Voice Effects Demo')

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        layout = QVBoxLayout()
        centralWidget.setLayout(layout)

        # Create buttons
        self.record_button = QPushButton('Record')
        self.record_button.setObjectName('recordButton')
        self.record_button.clicked.connect(self.start_recording)
        playOriginalButton = QPushButton('Play Original')
        playOriginalButton.clicked.connect(self.play_original)
        playFilteredButton = QPushButton('Play Filtered')
        playFilteredButton.clicked.connect(self.play_filtered)

        layout.addWidget(self.record_button)
        layout.addWidget(playOriginalButton)
        layout.addWidget(playFilteredButton)

        # Create effect dropdown
        self.effect_combo_box = QComboBox()
        for effect_name in EFFECT_NAMES:
            self.effect_combo_box.addItem(effect_name)
        self.effect_combo_box.currentIndexChanged.connect(self.effect_selected)

        layout.addWidget(self.effect_combo_box)

        self.visualisation_widget = AudioVisualisationWidget()
        self.waveformAndFftCanvas = self.visualisation_widget
        layout.addWidget(self.visualisation_widget)

    def start_recording(self):
        if self.is_recording:
            print("Stopping recording...")
            self.recording_stream.stop()
            self.recording_stream.close()
            self.is_recording = False
            self.record_button.setText("Record")
            if self.audio_data is not None:
                self.process_audio(self.effect_combo_box.currentText())
            return

        print("Starting recording...")
        self.is_recording = True
        self.audio_data = None
        self.audio_data_processed = None
        self.visualisation_widget.clear()
        
        # Set up the recording callback
        self.recording_callback = self._record_audio_callback
        self.recording_stream = sd.InputStream(samplerate=self.samplerate, channels=1, callback=self.recording_callback)
        self.recording_stream.start()
        
        self.record_button.setText("Stop Recording")

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
        if self.audio_data is not None:
            print("Playing original audio...")
            try:
                # Play the recorded data and wait for it to finish
                sd.play(self.audio_data, self.samplerate)
                sd.wait()
            except Exception as e:
                print(f"Error playing audio: {e}")
        else:
            print("No audio recorded.")

    def process_audio(self, effect_name):
        if self.audio_data is None:
            print("Cannot process: No original audio recorded.")
            return False

        print(f"Processing audio with effect: {effect_name}...")

        self.audio_data_processed = apply_effect(self.audio_data, effect_name, self.samplerate)
        self.visualisation_widget.set_audio(
            self.audio_data,
            self.audio_data_processed,
            effect_name,
            self.samplerate,
        )
        print("Processing complete.")
        return True

    def play_filtered(self):
        if self.audio_data_processed is None and self.audio_data is not None:
            self.process_audio(self.effect_combo_box.currentText())

        if self.audio_data_processed is not None:
            print("Playing filtered audio...")
            try:
                # Play the processed data and wait for it to finish
                sd.play(self.audio_data_processed, self.samplerate)
                sd.wait()
            except Exception as e:
                print(f"Error playing audio: {e}")
        else:
            print("No processed audio available.")

    def effect_selected(self, index):
        selected_effect = self.effect_combo_box.currentText()
        if self.audio_data is not None:
            self.process_audio(selected_effect)
        else:
            self.audio_data_processed = None
            self.visualisation_widget.clear()
            print("Please record audio first to apply effects.")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
