from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from visualisation_data import build_visualisation_data


VISUAL_EFFECT_COLORS = {
    "Chipmunk": "#f59e0b",
    "Giant": "#7c3aed",
    "Robot": "#06b6d4",
    "Radio": "#22c55e",
    "Alien": "#ec4899",
    "Echo": "#ef4444",
}


class AudioVisualisationWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.visualisation_data = None
        self.playback_progress = None
        self.waveform_zoom = 1.0
        self.waveform_follow_enabled = True
        self.comparison_panel_titles = ("Sound shape", "Pitch + brightness")
        self.setMinimumHeight(350)

    def set_audio(self, original_audio, processed_audio, effect_name, samplerate):
        self.visualisation_data = build_visualisation_data(
            original_audio,
            processed_audio,
            samplerate,
            effect_name,
            max_frequency=5000,
        )
        self.playback_progress = None
        self.update()

    def clear(self):
        self.visualisation_data = None
        self.playback_progress = None
        self.update()

    def zoom_in_waveform(self):
        self.waveform_zoom = min(8.0, self.waveform_zoom * 2.0)
        self.update()

    def zoom_out_waveform(self):
        self.waveform_zoom = max(1.0, self.waveform_zoom / 2.0)
        self.update()

    def reset_waveform_zoom(self):
        self.waveform_zoom = 1.0
        self.update()

    def set_waveform_follow_enabled(self, enabled):
        self.waveform_follow_enabled = bool(enabled)
        self.update()

    def set_playback_progress(self, progress):
        self.playback_progress = max(0.0, min(1.0, float(progress)))
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor("#111827"))

        if self.visualisation_data is None:
            self._draw_empty_state(painter)
            return

        data = self.visualisation_data
        painter.setPen(QColor("#f8fafc"))
        painter.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        painter.drawText(
            QRectF(16, 10, self.width() - 32, 28),
            Qt.AlignmentFlag.AlignCenter,
            f"Original vs {data.effect_name}",
        )

        left, top, gap = 16, 52, 14
        panel_width = self.width() - (left * 2)
        panel_height = (self.height() - top - 16 - gap) / 2

        panels = [
            QRectF(left, top, panel_width, panel_height),
            QRectF(left, top + panel_height + gap, panel_width, panel_height),
        ]

        processed = data.processed or data.original
        effect_color = QColor(_color_for_effect(data.effect_name))
        self._draw_waveform_comparison(painter, panels[0], data, processed, effect_color)
        self._draw_fft_comparison(painter, panels[1], data, processed, effect_color)

    def _draw_empty_state(self, painter):
        painter.setPen(QColor("#cbd5e1"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            "Record a clip, choose an effect, then compare what changed.",
        )

    def _draw_waveform_comparison(self, painter, rect, data, processed, color):
        x_min, x_max = self._waveform_time_window()
        self._draw_panel_frame(
            painter,
            rect,
            self.comparison_panel_titles[0],
            f"original peak {data.original.peak_amplitude:.2f}  effect peak {processed.peak_amplitude:.2f}  scale +/-{data.waveform_limit:.2f}",
        )
        plot_rect = rect.adjusted(54, 42, -18, -34)
        self._draw_axis_line(painter, plot_rect, 0.5)
        self._draw_series(
            painter,
            plot_rect,
            data.original.waveform_times,
            data.original.waveform_amplitudes,
            -data.waveform_limit,
            data.waveform_limit,
            _transparent("#64748b", 95),
            x_min=x_min,
            x_max=x_max,
            width=1,
        )
        self._draw_series(
            painter,
            plot_rect,
            processed.waveform_times,
            processed.waveform_amplitudes,
            -data.waveform_limit,
            data.waveform_limit,
            _with_alpha(color, 190),
            x_min=x_min,
            x_max=x_max,
            width=2,
        )
        if data.processed is not None:
            self._draw_series(
                painter,
                plot_rect,
                processed.waveform_times,
                data.difference_waveform_amplitudes,
                -data.waveform_limit,
                data.waveform_limit,
                _transparent("#f97316", 165),
                x_min=x_min,
                x_max=x_max,
                width=1,
            )
        self._draw_playhead(painter, plot_rect, x_min=x_min, x_max=x_max, duration_seconds=data.duration_seconds)
        if self.waveform_zoom > 1.0:
            time_label = f"{x_min:.2f}-{x_max:.2f}s  zoom x{self.waveform_zoom:.0f}"
        else:
            time_label = "full clip"
        self._draw_axis_labels(painter, rect, f"{time_label}  original grey  effect colour  change orange  gain x{data.display_gain:.1f}", "sound wave")

    def _draw_fft_comparison(self, painter, rect, data, processed, color):
        self._draw_panel_frame(
            painter,
            rect,
            self.comparison_panel_titles[1],
            f"peak {data.original.dominant_frequency:.0f} Hz -> {processed.dominant_frequency:.0f} Hz",
        )
        plot_rect = rect.adjusted(54, 42, -18, -34)
        self._draw_series(
            painter,
            plot_rect,
            data.original.fft_freqs,
            data.original.fft_display_magnitudes,
            0.0,
            1.0,
            _transparent("#64748b", 95),
            x_min=0.0,
            x_max=data.max_frequency,
            width=1,
        )
        self._draw_series(
            painter,
            plot_rect,
            processed.fft_freqs,
            processed.fft_display_magnitudes,
            0.0,
            1.0,
            _with_alpha(color, 190),
            x_min=0.0,
            x_max=data.max_frequency,
            width=2,
        )
        self._draw_playhead(painter, plot_rect)
        self._draw_axis_labels(painter, rect, "original grey  effect colour  voice band 0-5 kHz", "energy")

    def _draw_waveform(self, painter, rect, title, series, color, data, ghost_series=None, difference_amplitudes=None):
        self._draw_panel_frame(
            painter,
            rect,
            title,
            f"peak {series.peak_amplitude:.2f}  scale +/-{data.waveform_limit:.2f}",
        )
        plot_rect = rect.adjusted(42, 34, -12, -28)
        self._draw_axis_line(painter, plot_rect, 0.5)
        if ghost_series is not None:
            self._draw_series(
                painter,
                plot_rect,
                ghost_series.waveform_times,
                ghost_series.waveform_amplitudes,
                -data.waveform_limit,
                data.waveform_limit,
                _transparent("#64748b", 90),
                width=1,
            )
        self._draw_series(
            painter,
            plot_rect,
            series.waveform_times,
            series.waveform_amplitudes,
            -data.waveform_limit,
            data.waveform_limit,
            color,
            width=2,
        )
        if difference_amplitudes is not None:
            self._draw_series(
                painter,
                plot_rect,
                series.waveform_times,
                difference_amplitudes,
                -data.waveform_limit,
                data.waveform_limit,
                QColor("#f59e0b"),
                width=1,
            )
        self._draw_axis_labels(painter, rect, f"time  gain x{data.display_gain:.1f}", "amplitude")

    def _draw_fft(self, painter, rect, title, series, color, max_frequency, ghost_series=None):
        self._draw_panel_frame(painter, rect, title, f"peak {series.dominant_frequency:.0f} Hz")
        plot_rect = rect.adjusted(42, 34, -12, -28)
        if ghost_series is not None:
            self._draw_series(
                painter,
                plot_rect,
                ghost_series.fft_freqs,
                ghost_series.fft_display_magnitudes,
                0.0,
                1.0,
                _transparent("#64748b", 90),
                x_min=0.0,
                x_max=max_frequency,
                width=1,
            )
        self._draw_series(
            painter,
            plot_rect,
            series.fft_freqs,
            series.fft_display_magnitudes,
            0.0,
            1.0,
            color,
            x_min=0.0,
            x_max=max_frequency,
            width=2,
        )
        self._draw_axis_labels(painter, rect, "voice band 0-5 kHz", "relative dB")

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

    def _draw_playhead(self, painter, rect, x_min=0.0, x_max=1.0, duration_seconds=1.0):
        if self.playback_progress is None:
            return

        duration_seconds = max(float(duration_seconds), 0.001)
        playhead_seconds = self.playback_progress * duration_seconds
        if playhead_seconds < x_min or playhead_seconds > x_max:
            return
        x = rect.left() + ((playhead_seconds - x_min) / (x_max - x_min) * rect.width())
        painter.setPen(QPen(QColor("#ef4444"), 3))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))

    def _draw_axis_labels(self, painter, rect, x_label, y_label):
        painter.setPen(QColor("#64748b"))
        painter.setFont(QFont("Arial", 8))
        painter.drawText(rect.adjusted(42, 0, -12, -6), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom, x_label)
        painter.drawText(rect.adjusted(8, 34, -12, -28), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, y_label)

    def _draw_series(self, painter, rect, x_values, y_values, y_min, y_max, color, x_min=None, x_max=None, width=2):
        if len(x_values) < 2 or len(y_values) < 2:
            return

        x_min = float(x_values[0]) if x_min is None else float(x_min)
        x_max = float(x_values[-1]) if x_max is None else float(x_max)
        if x_max <= x_min:
            return

        painter.setPen(QPen(color, width))
        points = []
        for x_value, y_value in zip(x_values, y_values):
            if float(x_value) < x_min or float(x_value) > x_max:
                continue
            x_ratio = (float(x_value) - x_min) / (x_max - x_min)
            y_ratio = (float(y_value) - y_min) / (y_max - y_min)
            x = rect.left() + (x_ratio * rect.width())
            y = rect.bottom() - (y_ratio * rect.height())
            points.append(QPointF(x, y))

        for index in range(1, len(points)):
            painter.drawLine(points[index - 1], points[index])

    def _waveform_time_window(self):
        if self.visualisation_data is None:
            return 0.0, 1.0

        duration = max(float(self.visualisation_data.duration_seconds), 0.001)
        if self.waveform_zoom <= 1.0:
            return 0.0, duration

        window = duration / self.waveform_zoom
        if self.waveform_follow_enabled and self.playback_progress is not None:
            centre = self.playback_progress * duration
        else:
            centre = window / 2.0

        start = max(0.0, min(duration - window, centre - (window / 2.0)))
        end = min(duration, start + window)
        return round(start, 6), round(end, 6)


def _transparent(color_name, alpha):
    color = QColor(color_name)
    color.setAlpha(alpha)
    return color


def _with_alpha(source_color, alpha):
    color = QColor(source_color)
    color.setAlpha(alpha)
    return color


def _color_for_effect(effect_name):
    if effect_name in VISUAL_EFFECT_COLORS:
        return VISUAL_EFFECT_COLORS[effect_name]
    final_effect = effect_name.split(" + ")[-1]
    return VISUAL_EFFECT_COLORS.get(final_effect, "#ef4444")
