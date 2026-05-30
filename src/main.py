import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QComboBox, QLabel, QWidget, QVBoxLayout

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()

    def initUI(self):
        self.setGeometry(100, 100, 800, 600)
        self.setWindowTitle('Open Day Voice Effects Demo')

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)

        layout = QVBoxLayout()
        centralWidget.setLayout(layout)

        # Create buttons
        recordButton = QPushButton('Record')
        playOriginalButton = QPushButton('Play Original')
        playFilteredButton = QPushButton('Play Filtered')

        layout.addWidget(recordButton)
        layout.addWidget(playOriginalButton)
        layout.addWidget(playFilteredButton)

        # Create effect dropdown
        effectComboBox = QComboBox()
        effectComboBox.addItem('Normal')
        effectComboBox.addItem('Chipmunk')
        effectComboBox.addItem('Giant')
        effectComboBox.addItem('Robot')
        effectComboBox.addItem('Radio')
        effectComboBox.addItem('Alien')
        effectComboBox.addItem('Echo')

        layout.addWidget(effectComboBox)

        # Create placeholder canvas area
        waveformAndFftCanvas = QLabel('Waveform and FFT visualisation will appear here.')
        layout.addWidget(waveformAndFftCanvas)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())