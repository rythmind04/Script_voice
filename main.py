import sys
import time
import numpy as np
import sounddevice as sd
import keyboard  # pip install keyboard
from PyQt5.QtWidgets import QApplication, QLineEdit, QLabel, QVBoxLayout, QWidget, QPushButton
from PyQt5.QtCore import QThread, pyqtSignal, QTimer, Qt
from PyQt5.QtGui import QGuiApplication, QFont
import win32gui
import win32con
import win32com.client

# Настройки аудио
RATE = 44100
CHANNELS = 1
CHUNK = 1024
VOLUME_THRESHOLD = 0.13223
COOLDOWN = 2
last_trigger_time = 0

# Код разблокировки
UNLOCK_CODE = "23654125"


class AudioStreamThread(QThread):
    show_warning_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.stream = None
        self.is_running = False

    def run(self):
        global last_trigger_time
        self.is_running = True
        try:
            self.stream = sd.InputStream(channels=CHANNELS, samplerate=RATE,
                                         blocksize=CHUNK, callback=self.audio_callback)
            self.stream.start()
            print("Прослушивание микрофона запущено")
            while self.is_running:
                time.sleep(0.1)
        except Exception as e:
            print(f"Ошибка в аудиопотоке: {e}")

    def audio_callback(self, indata, frames, time_info, status):
        global last_trigger_time
        if status:
            print(f"Статус ошибки: {status}")

        audio_data = np.abs(indata[:, 0])
        volume = audio_data.mean()

        if volume > VOLUME_THRESHOLD:
            current_time = time.time()
            if current_time - last_trigger_time > COOLDOWN:
                print(f"Громкость: {volume:.4f}")
                print("Крик!")
                self.show_warning_signal.emit()
                last_trigger_time = current_time

    def stop_stream(self):
        """Останавливает прослушивание микрофона"""
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                self.stream = None
                print("Прослушивание микрофона остановлено")
            except Exception as e:
                print(f"Ошибка при остановке потока: {e}")


# ------------------------------
# Popup предупреждение Qt
# ------------------------------
class WarningPopup(QWidget):
    def __init__(self, text, duration=6000):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 250)

        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)

        label = QLabel(text)
        label.setStyleSheet(
            "font-size: 36px; color: red; background-color: rgba(0,0,0,180); padding: 20px; border-radius: 10px;")
        label.setAlignment(Qt.AlignCenter)

        layout.addWidget(label)
        self.setLayout(layout)

        self.center_on_active_screen()
        self.show()

        self.raise_()
        self.activateWindow()

        QTimer.singleShot(duration, self.close)

    def center_on_active_screen(self):
        try:
            screens = QGuiApplication.screens()

            game_window = win32gui.GetForegroundWindow()
            if game_window:
                rect = win32gui.GetWindowRect(game_window)
                window_center_x = (rect[0] + rect[2]) // 2
                window_center_y = (rect[1] + rect[3]) // 2

                for screen in screens:
                    screen_geometry = screen.geometry()
                    if (screen_geometry.left() <= window_center_x <= screen_geometry.right() and
                            screen_geometry.top() <= window_center_y <= screen_geometry.bottom()):
                        x = screen_geometry.left() + (screen_geometry.width() - self.width()) // 2
                        y = screen_geometry.top() + (screen_geometry.height() - self.height()) // 2
                        self.move(x, y)
                        return

            primary_screen = QGuiApplication.primaryScreen()
            screen_geometry = primary_screen.geometry()
            x = screen_geometry.left() + (screen_geometry.width() - self.width()) // 2
            y = screen_geometry.top() + (screen_geometry.height() - self.height()) // 2
            self.move(x, y)

        except Exception as e:
            print(f"Ошибка позиционирования: {e}")
            screen = QGuiApplication.primaryScreen().geometry()
            self.move((screen.width() - self.width()) // 2,
                      (screen.height() - self.height()) // 2)


# ------------------------------
# LockWindow блокировка
# ------------------------------
class LockWindow(QWidget):
    def __init__(self, parent_app):
        super().__init__()
        self.parent_app = parent_app
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)
        main_layout.setSpacing(30)
        main_layout.setContentsMargins(50, 50, 50, 50)

        title_label = QLabel("ЭКРАН ЗАБЛОКИРОВАН!")
        title_label.setStyleSheet("""
            font-size: 48px; 
            color: red; 
            font-weight: bold;
            padding: 20px;
        """)
        title_label.setAlignment(Qt.AlignCenter)

        subtitle_label = QLabel("Введите код для разблокировки:")
        subtitle_label.setStyleSheet("""
            font-size: 36px; 
            color: white;
            padding: 10px;
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)

        self.input_field = QLineEdit()
        self.input_field.setEchoMode(QLineEdit.Password)
        self.input_field.setFixedSize(500, 80)
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-size: 36px; 
                padding: 15px;
                background-color: white;
                color: black;
                border: 3px solid red;
                border-radius: 10px;
                selection-background-color: darkred;
            }
            QLineEdit:focus {
                border: 3px solid #ff4444;
                background-color: #f8f8f8;
            }
        """)
        self.input_field.setAlignment(Qt.AlignCenter)
        self.input_field.setPlaceholderText("Введите код...")

        font = QFont("Consolas", 24)
        font.setStyleStrategy(QFont.PreferAntialias)
        self.input_field.setFont(font)

        self.unlock_button = QPushButton("РАЗБЛОКИРОВАТЬ")
        self.unlock_button.setFixedSize(400, 70)
        self.unlock_button.setStyleSheet("""
            QPushButton {
                font-size: 28px; 
                padding: 15px;
                background-color: red;
                color: white;
                border: 2px solid darkred;
                border-radius: 10px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ff4444;
            }
            QPushButton:pressed {
                background-color: #cc0000;
            }
        """)
        self.unlock_button.clicked.connect(self.check_code)

        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addWidget(self.input_field)
        main_layout.addWidget(self.unlock_button)

        self.setLayout(main_layout)

        self.input_field.setFocus()
        self.block_system_keys()

        hwnd = int(self.winId())
        win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST,
                              0, 0, 0, 0,
                              win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

    def block_system_keys(self):
        try:
            keyboard.block_key("windows")
            keyboard.block_key("esc")
            keyboard.block_key("alt+f4")
            keyboard.block_key("f4")
            keyboard.block_key("alt+tab")
            keyboard.block_key("ctrl+esc")
            keyboard.block_key("ctrl+shift+esc")
        except Exception as e:
            print("Ошибка блокировки клавиш:", e)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self.check_code()
        elif event.key() == Qt.Key_Escape:
            event.ignore()
        elif event.key() == Qt.Key_Tab:
            event.ignore()
        else:
            super().keyPressEvent(event)

    def check_code(self):
        entered_code = self.input_field.text().strip()

        if entered_code == UNLOCK_CODE:
            self.unlock_screen()
        else:
            self.show_error()

    def show_error(self):
        self.input_field.clear()
        self.input_field.setPlaceholderText("НЕВЕРНЫЙ КОД!")

        self.input_field.setStyleSheet("""
            QLineEdit {
                font-size: 36px; 
                padding: 15px;
                background-color: #ffe6e6;
                color: black;
                border: 3px solid #ff0000;
                border-radius: 10px;
            }
        """)

        QTimer.singleShot(1000, self.restore_input_style)

    def restore_input_style(self):
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-size: 36px; 
                padding: 15px;
                background-color: white;
                color: black;
                border: 3px solid red;
                border-radius: 10px;
                selection-background-color: darkred;
            }
            QLineEdit:focus {
                border: 3px solid #ff4444;
                background-color: #f8f8f8;
            }
        """)
        self.input_field.setPlaceholderText("Введите код...")
        self.input_field.setFocus()

    def unlock_screen(self):
        try:
            keyboard.unhook_all()
        except:
            pass

        # Сообщаем родительскому приложению о разблокировке
        self.parent_app.on_screen_unlocked()
        self.close()

    def closeEvent(self, event):
        try:
            keyboard.unhook_all()
        except:
            pass
        super().closeEvent(event)


class WindowManager:
    @staticmethod
    def minimize_all_windows():
        """Сворачивает все окна и показывает рабочий стол"""
        try:
            # Используем Windows Shell для минимизации всех окон
            shell = win32com.client.Dispatch("Shell.Application")
            shell.MinimizeAll()
            print("Все окна свернуты")
        except Exception as e:
            print(f"Ошибка при сворачивании окон: {e}")

    @staticmethod
    def get_foreground_window_title():
        """Получает заголовок активного окна"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            return win32gui.GetWindowText(hwnd)
        except:
            return "Unknown"


# ------------------------------
# Основное приложение
# ------------------------------
class WarningApp(QApplication):
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        self.audio_thread = AudioStreamThread()
        self.audio_thread.show_warning_signal.connect(self.show_warning)

        self.is_window_open = False
        self.warning_count = 0
        self.active_popups = []
        self.is_locked = False

    def show_warning(self):
        if self.is_window_open or self.is_locked:
            return

        self.is_window_open = True
        self.warning_count += 1
        text = f"Превышен уровень громкости!\nПредупреждение {self.warning_count}/3"

        try:
            # Сначала сворачиваем все окна
            WindowManager.minimize_all_windows()

            # Ждем немного чтобы окна успели свернуться
            QTimer.singleShot(1000, lambda: self.show_popup(text))

        except Exception as e:
            print(f"Ошибка при показе предупреждения: {e}")
            # Если не удалось свернуть окна, все равно показываем popup
            self.show_popup(text)

    def show_popup(self, text):
        """Показывает popup окно с предупреждением"""
        try:
            popup = WarningPopup(text, duration=6000)
            self.active_popups.append(popup)
            QTimer.singleShot(6100, lambda: self.cleanup_popup(popup))

        except Exception as e:
            print(f"Ошибка показа popup: {e}")

        # Увеличиваем время до закрытия окна
        QTimer.singleShot(6000, self.on_window_closed)

        if self.warning_count >= 3:
            # Увеличиваем время до блокировки экрана
            QTimer.singleShot(6100, self.lock_screen)

    def cleanup_popup(self, popup):
        """Удаляет popup из списка активных"""
        if popup in self.active_popups:
            self.active_popups.remove(popup)

    def on_window_closed(self):
        self.is_window_open = False

    def restart_audio_capture(self):
        """Запускает прослушивание микрофона"""
        print("Запуск прослушивания...")
        if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
            self.audio_thread.stop_stream()
            self.audio_thread.wait()

        self.audio_thread = AudioStreamThread()
        self.audio_thread.show_warning_signal.connect(self.show_warning)
        self.audio_thread.start()

    def stop_audio_capture(self):
        """Останавливает прослушивание микрофона"""
        print("Остановка прослушивания...")
        if hasattr(self, 'audio_thread') and self.audio_thread.isRunning():
            self.audio_thread.stop_stream()
            self.audio_thread.wait()
            print("Прослушивание микрофона остановлено")

    def lock_screen(self):
        """Блокирует экран и останавливает прослушивание"""
        print("Экран заблокирован!")
        self.is_locked = True

        # Останавливаем прослушивание микрофона
        self.stop_audio_capture()

        # Создаем и показываем окно блокировки
        self.lock_window = LockWindow(self)
        self.lock_window.show()

    def on_screen_unlocked(self):
        """Вызывается при разблокировке экрана"""
        print("Экран разблокирован!")
        self.is_locked = False
        self.reset_warnings()

        # Перезапускаем прослушивание микрофона
        QTimer.singleShot(500, self.restart_audio_capture)

    def reset_warnings(self):
        self.warning_count = 0
        print("Счётчик предупреждений сброшен")

    def start(self):
        self.restart_audio_capture()
        self.setQuitOnLastWindowClosed(False)
        self.exec_()


if __name__ == "__main__":
    app = WarningApp(sys.argv)
    try:
        app.start()
    except Exception as e:
        print(f"Ошибка в приложении: {e}")