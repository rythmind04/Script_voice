import sounddevice as sd
import numpy as np
import sys
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QTimer

# Настройки захвата звука
RATE = 44100  # Частота дискретизации
CHANNELS = 1  # Количество каналов (моно)
CHUNK = 1024  # Размер блока
VOLUME_THRESHOLD = 0.03  # Порог уровня громкости (настройте по необходимости)

print("Запуск прослушивания...")

# Флаг для предотвращения частого появления окон
COOLDOWN = 2  # Время в секундах между предупреждениями
last_trigger_time = 0  # Время последнего предупреждения


class AudioStreamThread(QThread):
    """Поток для захвата аудио."""
    show_warning_signal = pyqtSignal()  # Сигнал для отображения предупреждения

    def run(self):
        """Основной метод работы потока."""
        global last_trigger_time
        try:
            with sd.InputStream(channels=CHANNELS, samplerate=RATE, blocksize=CHUNK, callback=self.audio_callback):
                while True:
                    time.sleep(0.1)  # Задержка, чтобы поток не использовал 100% CPU
        except Exception as e:
            print(f"Ошибка в аудиопотоке: {e}")

    def audio_callback(self, indata, frames, time_info, status):
        """Обработчик аудиопотока."""
        global last_trigger_time

        if status:
            print(f"Статус ошибки: {status}")

        # Преобразуем данные в массив numpy и нормализуем
        audio_data = np.abs(indata[:, 0])
        volume = audio_data.mean()

        # Проверка уровня громкости
        if volume > VOLUME_THRESHOLD:
            current_time = time.time()

            # Проверяем, прошло ли достаточно времени с последнего предупреждения
            if current_time - last_trigger_time > COOLDOWN:
                print(f"Текущий уровень громкости: {volume:.4f}")
                print("Крик!")
                self.show_warning_signal.emit()  # Передаем сигнал для отображения окна
                last_trigger_time = current_time  # Обновляем время последнего предупреждения


class WarningApp(QApplication):
    """Основное приложение для обработки предупреждений."""
    def __init__(self, sys_argv):
        super().__init__(sys_argv)

        self.audio_thread = AudioStreamThread()
        self.audio_thread.show_warning_signal.connect(self.show_warning)

        self.is_window_open = False  # Флаг для предотвращения открытия нескольких окон

    def show_warning(self):
        """Отображает предупреждающее окно."""
        if self.is_window_open:
            return  # Если окно уже открыто, не открываем новое

        self.is_window_open = True  # Устанавливаем флаг, что окно открыто

        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Предупреждение")
        msg_box.setText("Превышен уровень громкости!")
        msg_box.setStandardButtons(QMessageBox.Ok)

        # Закрываем окно автоматически через 3 секунды, если пользователь не закрыл его
        QTimer.singleShot(3000, lambda: self.close_warning(msg_box))

        # Сбрасываем флаг, когда окно закрывается вручную
        msg_box.finished.connect(lambda: self.on_window_closed())
        msg_box.show()

    def close_warning(self, msg_box):
        """Закрывает предупреждающее окно."""
        if msg_box.isVisible():
            msg_box.close()
        self.is_window_open = False  # Сбрасываем флаг

    def on_window_closed(self):
        """Когда окно закрывается, продолжает захват аудио."""
        self.is_window_open = False
        self.restart_audio_capture()

    def restart_audio_capture(self):
        """Перезапускает поток аудиозахвата."""
        print("Запуск прослушивания...")
        self.audio_thread = AudioStreamThread()
        self.audio_thread.show_warning_signal.connect(self.show_warning)
        self.audio_thread.start()

    def start(self):
        """Запускает аудиопоток и приложение."""
        self.audio_thread.start()  # Запускаем поток захвата аудио
        self.exec_()  # Запускаем цикл событий PyQt


if __name__ == "__main__":
    app = WarningApp(sys.argv)
    try:
        app.start()
    except Exception as e:
        print(f"Ошибка в приложении: {e}")
