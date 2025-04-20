import silent_subprocess  # Импортируем модуль для скрытия командных окон
import sys
import os  # Добавляем для работы с файловой системой
from PyQt5.QtWidgets import QApplication
from ui import MainWindow
from PyQt5.QtCore import qInstallMessageHandler, QtMsgType

# Функция для удаления лог-файла, если он существует
def remove_log_file():
    log_file = "system_monitor.log"
    if os.path.exists(log_file):
        try:
            os.remove(log_file)
        except:
            pass  # Игнорируем ошибки при удалении файла

# Функция-обработчик, которая полностью игнорирует все сообщения Qt
def qt_message_handler(mode, context, message):
    pass  # Полностью игнорируем все сообщения Qt

# Устанавливаем обработчик сообщений
qInstallMessageHandler(qt_message_handler)

# Перенаправляем stdout и stderr в null
class NullIO:
    def write(self, *args, **kwargs):
        pass
    
    def flush(self, *args, **kwargs):
        pass

# Сохраняем оригинальные потоки вывода (если нужно будет вернуть их позже)
original_stdout = sys.stdout
original_stderr = sys.stderr

# Перенаправляем stdout и stderr
sys.stdout = NullIO()
sys.stderr = NullIO()

if __name__ == "__main__":
    # Удаляем лог-файл при запуске
    remove_log_file()
    
    # Создаем экземпляр QApplication
    app = QApplication(sys.argv)
    
    # Создаем главное окно приложения
    window = MainWindow()
    
    # Отображаем главное окно
    window.show()
    
    # Запускаем цикл обработки событий
    sys.exit(app.exec_())
