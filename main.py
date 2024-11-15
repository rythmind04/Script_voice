import sounddevice as sd
import numpy as np
import pygetwindow as gw
import pyautogui
import time

# Настройки захвата звука
RATE = 44100  # Частота дискретизации
CHANNELS = 1  # Количество каналов (моно)
CHUNK = 1024  # Размер блока
VOLUME_THRESHOLD = 0.35  # Порог уровня громкости (настройте по необходимости)

print("Запуск прослушивания...")

# Флаг для предотвращения частого сворачивания окон
cooldown = 2  # Время в секундах между сворачиваниями
last_trigger_time = 0  # Время последнего сворачивания


def minimize_active_window():
    # Получаем список всех окон
    windows = gw.getAllWindows()

    # Находим активное окно
    active_window = gw.getActiveWindow()

    if active_window is not None:
        # Сворачиваем окно
        active_window.minimize()

def audio_callback(indata, frames, time_info, status):
    global last_trigger_time
    if status:
        print(f"Статус ошибки: {status}")

    # Преобразуем данные в массив numpy и нормализуем
    audio_data = np.abs(indata[:, 0])
    volume = audio_data.mean()

    # Проверка уровня громкости
    if volume > VOLUME_THRESHOLD:
        current_time = time.time()  # Используем системное время
        # Проверяем, прошло ли достаточно времени с последнего сворачивания
        if current_time - last_trigger_time > cooldown:
            print(f"Текущий уровень громкости: {volume:.4f}")
            print("Крик!")
            # Сворачиваем все окна
            minimize_active_window()
            last_trigger_time = current_time  # Обновляем время последнего сворачивания

try:
    # Открытие потока для захвата звука
    with sd.InputStream(channels=CHANNELS, samplerate=RATE, blocksize=CHUNK, callback=audio_callback):
        while True:
            time.sleep(0.1)  # Небольшая задержка для снижения нагрузки на процессор
except KeyboardInterrupt:
    print("\nОстановка...")
except Exception as e:
    print(f"Ошибка: {e}")