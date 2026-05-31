from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from visualisation_data import build_visualisation_data


class AudioVisualisationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.visualisation_data = None
        self.setMinimumHeight(420)

    def set_audio(self, original_audio, processed_audio, effect_name, samplerate):
        self.visualisation_data = build_visualisation_data(
            original_audio,
            processed_audio,
            samplerate,
            effect_name,
            max_frequency=5000,
        )
        self.update()

    def clear(self):
        self.visualisation_data = None
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#f8fafc"))

        if self.visualisation_data is None:
            self._draw_empty_state(painter)
            return

        data = self.visualisation_data
        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(
            QRectF(16, 10, self.width() - 32, 28),
            Qt.AlignmentFlag.AlignCenter,
            f"Original vs {data.effect_name}",
        )

        left, top, gap = 16, 52, 14
        panel_width = (self.width() - (left * 2) - gap) / 2
        panel_height = (self.height() - top - 16 - gap) / 2

        panels = [
            QRectF(left, top, panel_width, panel_height),
            QRectF(left + panel_width + gap, top, panel_width, panel_height),
            QRectF(left, top + panel_height + gap, panel_width, panel_height),
            QRectF(left + panel_width + gap, top + panel_height + gap, panel_width, panel_height),
        ]

        processed = data.processed or data.original
        self._draw_waveform(painter, panels[0], "Original waveform", data.original, QColor("#2563eb"))
        self._draw_fft(painter, panels[1], "Original FFT", data.original, QColor("#2563eb"), data.max_frequency)
        self._draw_waveform(painter, panels[2], f"{data.effect_name} waveform", processed, QColor("#dc2626"))
        self._draw_fft(painter, panels[3], f"{data.effect_name} FFT", processed, QColor("#dc2626"), data.max_frequency)

    def _draw_empty_state(self, painter):
        painter.setPen(QColor("#475569"))
        painter.setFont(QFont("Arial", 13))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Record a clip to compare the original and selected voice effect.",
        )

    def _draw_waveform(self, painter, rect, title, series, color):
        self._draw_panel_frame(painter, rect, title, f"peak {series.peak_amplitude:.2f}")
        plot_rect = rect.adjusted(42, 34, -12, -28)
        self._draw_axis_line(painter, plot_rect, 0.5)
        self._draw_series(
            painter,
            plot_rect,
            series.waveform_times,
            series.waveform_amplitudes,
            -1.0,
            1.0,
            color,
        )
        self._draw_axis_labels(painter, rect, "time", "amplitude")

    def _draw_fft(self, painter, rect, title, series, color, max_frequency):
        self._draw_panel_frame(painter, rect, title, f"peak {series.dominant_frequency:.0f} Hz")
        plot_rect = rect.adjusted(42, 34, -12, -28)
        self._draw_series(
            painter,
            plot_rect,
            series.fft_freqs,
            series.fft_magnitudes,
            0.0,
            1.0,
            color,
            x_min=0.0,
            x_max=max_frequency,
        )
        self._draw_axis_labels(painter, rect, "0-5 kHz", "energy")

    def _draw_panel_frame(self, painter, rect, title, summary):
        painter.setPen(QPen(QColor("#cbd5e1"), 1))
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 6, 6)

        painter.setPen(QColor("#0f172a"))
        painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        painter.drawText(rect.adjusted(10, 6, -10, -6), Qt.AlignmentFlag.AlignLeft, title)

        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Arial", 9))
        painter.drawText(rect.adjusted(10, 6, -10, -6), Qt.AlignmentFlag.AlignRight, summary)

    def _draw_axis_line(self, painter, rect, y_ratio):
        y = rect.top() + (rect.height() * y_ratio)
        painter.setPen(QPen(QColor("#e2e8f0"), 1, Qt.PenStyle.DotLine))
        painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))

    def _draw_axis_labels(self, painter, rect, x_label, y_label):
        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(rect.adjusted(42, 0, -12, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, x_label)
        painter.drawText(rect.adjusted(8, 34, -12, -28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, y_label)

    def _draw_series(self, painter, rect, x_values, y_values, y_min, y_max, color, x_min=None, x_max=None):
        if len(x_values) < 2 or len(y_values) < 2:
            return

        x_min = float(x_values[0]) if x_min is None else float(x_min)
        x_max = float(x_values[-1]) if x_max is None else float(x_max)
        if x_max <= x_min:
            return

        painter.setPen(QPen(color, 2))
        points = []
        for x_value, y_value in zip(x_values, y_values):
            x_ratio = (float(x_value) - x_min) / (x_max - x_min)
            y_ratio = (float(y_value) - y_min) / (y_max - y_min)
            x = rect.left() + (x_ratio * rect.width())
            y = rect.bottom() - (y_ratio * rect.height())
            points.append(QPointF(x, y))

        for index in range(1, len(points)):
            painter.drawLine(points[index - 1], points[index])
