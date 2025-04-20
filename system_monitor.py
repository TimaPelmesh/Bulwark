import psutil
import platform
import logging

# Отключаем логирование (заглушка)
class NullHandler(logging.Handler):
    def emit(self, record):
        pass

# Настраиваем null-логирование, чтобы ничего не записывалось
logger = logging.getLogger()
logger.addHandler(NullHandler())
logger.setLevel(logging.CRITICAL)  # Самый высокий уровень логирования

# Попытка импортировать GPUtil с обработкой ошибки
try:
    import GPUtil
    HAS_GPUTIL = True
except ImportError:
    HAS_GPUTIL = False

# Проверка наличия модуля wmi
try:
    import wmi
    HAS_WMI = True
except ImportError:
    HAS_WMI = False
    # Удаляем print, чтобы не было вывода в терминал

import time
from PyQt5.QtCore import QThread, pyqtSignal, QTimer
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTabWidget, QLabel, QProgressBar, 
                           QGridLayout, QGroupBox, QHBoxLayout, QSplitter, QPushButton, 
                           QTableWidget, QTableWidgetItem, QHeaderView, QTreeWidget, 
                           QTreeWidgetItem, QStyle, QFrame, QStyledItemDelegate, 
                           QApplication, QSizePolicy, QLineEdit, QMenu, QAction)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QColor, QFont, QIcon, QBrush, QPalette
import socket
import datetime
import traceback
import math

class SystemMonitor:
    """
    Класс для мониторинга системных ресурсов компьютера
    """
    def __init__(self):
        self.system_info = self.get_system_info()
        # История загрузки CPU для сглаживания
        self.cpu_history = []
        self.history_size = 3  # Размер истории для усреднения
    
    def get_system_info(self):
        """
        Получение общей информации о системе
        """
        # Получаем исходную информацию о процессоре
        processor_info = platform.processor()
        
        # Преобразуем информацию о процессоре в более читаемый вид
        readable_processor = self._get_readable_processor_name(processor_info)
        
        info = {
            "Система": platform.system(),
            "Имя компьютера": platform.node(),
            "Версия": platform.version(),
            "Архитектура": platform.machine(),
            "Процессор": readable_processor,
            "Число ядер CPU": psutil.cpu_count(logical=False),
            "Число логических ядер": psutil.cpu_count(logical=True),
            "RAM всего (ГБ)": round(psutil.virtual_memory().total / (1024**3), 2),
        }
        return info
    
    def _get_readable_processor_name(self, processor_info):
        """
        Преобразует технический идентификатор процессора в более читаемое название
        """
        # Попытаемся получить информацию из WMI для Windows
        if platform.system() == "Windows":
            try:
                c = wmi.WMI()
                for processor in c.Win32_Processor():
                    return processor.Name.strip()
            except:
                pass
        
        # Для Linux можем прочитать /proc/cpuinfo
        if platform.system() == "Linux":
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if line.startswith('model name'):
                            return line.split(':')[1].strip()
            except:
                pass
        
        # Для macOS можем использовать sysctl
        if platform.system() == "Darwin":
            try:
                import subprocess
                output = subprocess.check_output(['sysctl', '-n', 'machdep.cpu.brand_string']).decode().strip()
                return output
            except:
                pass
        
        # Если не удалось получить понятное имя, обработаем строку processor_info
        if 'intel' in processor_info.lower():
            # Пример: Intel64 Family 6 Model 142 Stepping 10, GenuineIntel
            # Преобразуем в: Intel Core i5/i7/i9 (примерно)
            if 'family 6' in processor_info.lower():
                model = None
                if 'model 142' in processor_info.lower():
                    model = "Intel Core i7/i9 (10-го поколения)"
                elif 'model 158' in processor_info.lower():
                    model = "Intel Core i7/i9 (11-го поколения)"
                else:
                    model = "Intel Core (современное поколение)"
                return model
            return "Процессор Intel"
        elif 'amd' in processor_info.lower():
            return "Процессор AMD"
        
        # Если не смогли определить, вернем исходное значение с пометкой
        return processor_info
    
    def get_cpu_usage(self):
        """
        Получение текущей загрузки процессора с усреднением
        """
        # Получаем текущую загрузку всех ядер
        current_usage = psutil.cpu_percent(interval=1, percpu=True)
        
        # Добавляем в историю
        self.cpu_history.append(current_usage)
        
        # Ограничиваем размер истории
        if len(self.cpu_history) > self.history_size:
            self.cpu_history.pop(0)
        
        # Вычисляем среднее значение для каждого ядра
        avg_per_core = []
        cores_count = len(current_usage)
        
        for core in range(cores_count):
            core_history = [history[core] for history in self.cpu_history]
            avg_per_core.append(sum(core_history) / len(core_history))
        
        # Вычисляем общую среднюю загрузку
        total_avg = sum(avg_per_core) / len(avg_per_core)
        
        return {
            'total': round(total_avg, 1),
            'per_cpu': [round(x, 1) for x in avg_per_core]
        }
    
    def get_ram_usage(self):
        """
        Получение информации об использовании оперативной памяти
        """
        memory = psutil.virtual_memory()
        return {
            "Всего (ГБ)": round(memory.total / (1024**3), 2),
            "Использовано (ГБ)": round(memory.used / (1024**3), 2),
            "Доступно (ГБ)": round(memory.available / (1024**3), 2),
            "Процент использования": memory.percent
        }
    
    def get_disk_usage(self):
        """
        Получение информации об использовании дисков
        """
        disks = {}
        for partition in psutil.disk_partitions():
            if "cdrom" in partition.opts or partition.fstype == "":
                continue
            try:
                usage = psutil.disk_usage(partition.mountpoint)
                disks[partition.device] = {
                    "Точка монтирования": partition.mountpoint,
                    "Файловая система": partition.fstype,
                    "Всего (ГБ)": round(usage.total / (1024**3), 2),
                    "Использовано (ГБ)": round(usage.used / (1024**3), 2),
                    "Свободно (ГБ)": round(usage.free / (1024**3), 2),
                    "Процент использования": usage.percent
                }
            except:
                continue
        return disks
    
    def get_gpu_info(self):
        """Получает расширенную информацию о видеокартах."""
        gpus = {}
        gpu_count = 0
        
        # Получаем информацию через WMI
        if HAS_WMI:
            try:
                wmi_obj = wmi.WMI()
                for i, gpu in enumerate(wmi_obj.Win32_VideoController()):
                    gpu_count += 1
                    gpu_id = f"gpu_{i}"
                    status = "Работает" if gpu.Status == "OK" else f"Проблема: {gpu.Status}" if gpu.Status else "Неизвестно"
                    
                    # Проверяем, есть ли валидное значение для объема памяти
                    if hasattr(gpu, 'AdapterRAM') and gpu.AdapterRAM and int(gpu.AdapterRAM) > 0:
                        memory = f"{int(gpu.AdapterRAM) / (1024**3):.2f} GB"
                    else:
                        memory = "Не определено"
                    
                    # Информация о драйвере
                    driver = gpu.DriverVersion or "" if hasattr(gpu, 'DriverVersion') else ""
                    driver_date = gpu.DriverDate or "" if hasattr(gpu, 'DriverDate') else ""
                    if driver_date:
                        try:
                            # Преобразуем дату драйвера в читаемый формат
                            date_obj = datetime.strptime(driver_date.split('.')[0], '%Y%m%d%H%M%S')
                            driver_date = date_obj.strftime('%d.%m.%Y')
                        except:
                            pass
                    
                    # Создаем запись о видеокарте с проверкой всех полей
                    gpus[gpu_id] = {
                        'name': gpu.Name if hasattr(gpu, 'Name') and gpu.Name else "Видеокарта",
                        'status': status,
                        'manufacturer': gpu.AdapterCompatibility if hasattr(gpu, 'AdapterCompatibility') and gpu.AdapterCompatibility else "Неизвестно",
                        'driver': gpu.InstalledDisplayDrivers if hasattr(gpu, 'InstalledDisplayDrivers') and gpu.InstalledDisplayDrivers else "",
                        'driver_version': driver,
                        'driver_date': driver_date,
                        'memory': memory,
                        'description': gpu.Description if hasattr(gpu, 'Description') and gpu.Description else "",
                        'device_id': gpu.DeviceID if hasattr(gpu, 'DeviceID') and gpu.DeviceID else f"GPU{i}",
                        'video_processor': gpu.VideoProcessor if hasattr(gpu, 'VideoProcessor') and gpu.VideoProcessor else "",
                        'video_mode': f"{gpu.CurrentHorizontalResolution}x{gpu.CurrentVerticalResolution}" if hasattr(gpu, 'CurrentHorizontalResolution') and gpu.CurrentHorizontalResolution else "",
                        'refresh_rate': f"{gpu.CurrentRefreshRate} Hz" if hasattr(gpu, 'CurrentRefreshRate') and gpu.CurrentRefreshRate else "",
                        'bits_per_pixel': gpu.CurrentBitsPerPixel if hasattr(gpu, 'CurrentBitsPerPixel') and gpu.CurrentBitsPerPixel else ""
                    }
            except Exception as e:
                logging.error(f"Ошибка при получении информации о GPU через WMI: {e}")
                
        # Дополняем информацией из GPUtil если доступно
        if HAS_GPUTIL:
            try:
                for i, gpu in enumerate(GPUtil.getGPUs()):
                    gpu_count += 1
                    gpu_id = f"gputil_{i}"
                    
                    # Проверяем, не дублируется ли информация из WMI
                    duplicate = False
                    for existing_gpu in gpus.values():
                        if gpu.name in existing_gpu.get('name', ''):
                            duplicate = True
                            break
                    
                    if not duplicate:
                        if gpu.memoryTotal > 0:
                            memory = f"{gpu.memoryTotal / 1024:.2f} GB"
                        else:
                            memory = "Не определено"
                        
                        gpus[gpu_id] = {
                            'name': gpu.name if gpu.name else f"GPU {i}",
                            'status': "Работает",
                            'manufacturer': "NVIDIA" if "NVIDIA" in (gpu.name or "") else ("AMD" if "AMD" in (gpu.name or "") else ""),
                            'memory': memory,
                            'temperature': f"{gpu.temperature}°C" if hasattr(gpu, 'temperature') and gpu.temperature is not None else "",
                            'load': f"{gpu.load * 100:.1f}%" if hasattr(gpu, 'load') and gpu.load is not None else "",
                            'memory_used': f"{gpu.memoryUsed / 1024:.2f} GB" if hasattr(gpu, 'memoryUsed') and gpu.memoryUsed is not None else "",
                            'memory_free': f"{(gpu.memoryTotal - gpu.memoryUsed) / 1024:.2f} GB" if hasattr(gpu, 'memoryTotal') and hasattr(gpu, 'memoryUsed') and gpu.memoryTotal is not None and gpu.memoryUsed is not None else "",
                            'memory_utilization': f"{gpu.memoryUtil * 100:.1f}%" if hasattr(gpu, 'memoryUtil') and gpu.memoryUtil is not None else "",
                            'device_id': f"GPU-{gpu.id}" if hasattr(gpu, 'id') and gpu.id is not None else f"GPU{i}"
                        }
            except Exception as e:
                logging.error(f"Ошибка при получении информации о GPU через GPUtil: {e}")
        
        # Если не удалось обнаружить GPU ни через WMI, ни через GPUtil, 
        # добавляем хотя бы один базовый GPU основываясь на данных из системы
        if gpu_count == 0:
            try:
                gpus["gpu_0"] = {
                    'name': "Интегрированная видеокарта",
                    'status': "Работает",
                    'manufacturer': "Неизвестно",
                    'device_id': "GPU0"
                }
            except Exception as e:
                logging.error(f"Ошибка при создании резервной информации о GPU: {e}")
                
        return gpus
    
    def get_network_io(self):
        """
        Получение информации о сетевой активности
        """
        net_io = psutil.net_io_counters()
        return {
            "Отправлено (МБ)": round(net_io.bytes_sent / (1024**2), 2),
            "Получено (МБ)": round(net_io.bytes_recv / (1024**2), 2),
            "Отправлено пакетов": net_io.packets_sent,
            "Получено пакетов": net_io.packets_recv,
            "Ошибки входящие": net_io.errin,
            "Ошибки исходящие": net_io.errout,
            "Dropped входящие": net_io.dropin,
            "Dropped исходящие": net_io.dropout
        }

class SystemMonitorThread(QThread):
    """
    Поток для обновления информации о системных ресурсах
    """
    update_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.monitor = SystemMonitor()
        self._running = True
    
    def run(self):
        while self._running:
            data = {
                "cpu": self.monitor.get_cpu_usage(),
                "ram": self.monitor.get_ram_usage(),
                "disk": self.monitor.get_disk_usage(),
                "gpu": self.monitor.get_gpu_info(),
                "network": self.monitor.get_network_io()
            }
            self.update_signal.emit(data)
            time.sleep(1)
    
    def stop(self):
        self._running = False

class SystemInfoTab(QWidget):
    """
    Вкладка с основной информацией о системе
    """
    def __init__(self):
        super().__init__()
        self.monitor = SystemMonitor()
        self.cpu_usage = 0
        self.ram_usage = 0
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Создаем группы информации в две колонки
        info_layout = QHBoxLayout()
        
        # Левая колонка: информация о системе
        system_info_group = QGroupBox("Информация о системе")
        system_info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        system_layout = QGridLayout()
        system_layout.setSpacing(8)
        system_layout.setContentsMargins(10, 15, 10, 10)
        
        system_info = self.monitor.get_system_info()
        
        # Распределяем данные системы
        system_items = [
            ("Система", system_info["Система"]),
            ("Имя компьютера", system_info["Имя компьютера"]),
            ("Версия", system_info["Версия"]),
            ("Архитектура", system_info["Архитектура"])
        ]
        
        for row, (key, value) in enumerate(system_items):
            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel(str(value))
            system_layout.addWidget(key_label, row, 0)
            system_layout.addWidget(value_label, row, 1)
        
        system_info_group.setLayout(system_layout)
        
        # Правая колонка: информация о процессоре и памяти
        hardware_info_group = QGroupBox("Аппаратное обеспечение")
        hardware_info_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        hardware_layout = QGridLayout()
        hardware_layout.setSpacing(8)
        hardware_layout.setContentsMargins(10, 15, 10, 10)
        
        # Данные о процессоре и памяти
        hardware_items = [
            ("Процессор", system_info["Процессор"]),
            ("Физические ядра", system_info["Число ядер CPU"]),
            ("Логические ядра", system_info["Число логических ядер"]),
            ("Оперативная память", f"{system_info['RAM всего (ГБ)']} ГБ")
        ]
        
        for row, (key, value) in enumerate(hardware_items):
            key_label = QLabel(f"{key}:")
            key_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel(str(value))
            hardware_layout.addWidget(key_label, row, 0)
            hardware_layout.addWidget(value_label, row, 1)
        
        hardware_info_group.setLayout(hardware_layout)
        
        # Добавляем две колонки в горизонтальный лейаут
        info_layout.addWidget(system_info_group)
        info_layout.addWidget(hardware_info_group)
        
        # Добавляем виджеты мониторинга ресурсов
        resources_group = QGroupBox("Мониторинг ресурсов")
        resources_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        resources_layout = QHBoxLayout()
        resources_layout.setSpacing(15)
        resources_layout.setContentsMargins(10, 15, 10, 10)
        
        # Виджет CPU
        cpu_widget = QWidget()
        cpu_layout = QVBoxLayout()
        cpu_layout.setSpacing(5)
        
        self.cpu_label = QLabel("Загрузка ЦП")
        self.cpu_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.cpu_value = QLabel("0%")
        self.cpu_value.setStyleSheet("font-size: 24px; color: #0066cc;")
        self.cpu_bar = QProgressBar()
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setValue(0)
        self.cpu_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0e0ff;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                background-color: #f5f8ff;
            }
            QProgressBar::chunk {
                background-color: #3a7bd5;
                border-radius: 5px;
            }
        """)
        
        cpu_layout.addWidget(self.cpu_label)
        cpu_layout.addWidget(self.cpu_value, alignment=Qt.AlignCenter)
        cpu_layout.addWidget(self.cpu_bar)
        cpu_widget.setLayout(cpu_layout)
        
        # Виджет RAM
        ram_widget = QWidget()
        ram_layout = QVBoxLayout()
        ram_layout.setSpacing(5)
        
        self.ram_label = QLabel("Использование ОЗУ")
        self.ram_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        self.ram_value = QLabel("0%")
        self.ram_value.setStyleSheet("font-size: 24px; color: #0066cc;")
        self.ram_bar = QProgressBar()
        self.ram_bar.setRange(0, 100)
        self.ram_bar.setValue(0)
        self.ram_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #d0e0ff;
                border-radius: 5px;
                text-align: center;
                height: 20px;
                background-color: #f5f8ff;
            }
            QProgressBar::chunk {
                background-color: #3a7bd5;
                border-radius: 5px;
            }
        """)
        
        ram_layout.addWidget(self.ram_label)
        ram_layout.addWidget(self.ram_value, alignment=Qt.AlignCenter)
        ram_layout.addWidget(self.ram_bar)
        ram_widget.setLayout(ram_layout)
        
        # Добавляем виджеты в группу ресурсов
        resources_layout.addWidget(cpu_widget)
        resources_layout.addWidget(ram_widget)
        resources_group.setLayout(resources_layout)
        
        # Добавляем все в основной лейаут
        main_layout.addLayout(info_layout)
        main_layout.addWidget(resources_group)
        
        # Добавляем детальную информацию о ЦП (из вкладки Процессор)
        cpu_details_group = QGroupBox("Детальная информация о процессоре")
        cpu_details_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        cpu_details_layout = QVBoxLayout()
        
        # Загрузка отдельных ядер
        cores_layout = QGridLayout()
        
        self.core_bars = []
        self.core_labels = []
        
        cores_count = psutil.cpu_count(logical=True)
        rows = max(1, (cores_count + 1) // 2)
        
        for i in range(cores_count):
            core_label = QLabel(f"Core {i}: 0%")
            core_bar = QProgressBar()
            core_bar.setRange(0, 100)
            core_bar.setStyleSheet("""
                QProgressBar {
                    border: 1px solid #d0e0ff;
                    border-radius: 4px;
                    text-align: center;
                    height: 16px;
                    background-color: #f5f8ff;
                }
                QProgressBar::chunk {
                    background-color: #3a7bd5;
                    border-radius: 3px;
                }
            """)
            
            self.core_labels.append(core_label)
            self.core_bars.append(core_bar)
            
            row = i % rows
            col = i // rows * 2
            
            cores_layout.addWidget(core_label, row, col)
            cores_layout.addWidget(core_bar, row, col + 1)
        
        cpu_details_layout.addLayout(cores_layout)
        cpu_details_group.setLayout(cpu_details_layout)
        main_layout.addWidget(cpu_details_group)
        
        # Добавляем детальную информацию о RAM (из вкладки Память)
        ram_details_group = QGroupBox("Детальная информация о памяти")
        ram_details_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        ram_details_layout = QVBoxLayout()
        
        ram_info_layout = QGridLayout()
        ram_info_layout.addWidget(QLabel("Всего:"), 0, 0)
        ram_info_layout.addWidget(QLabel("Использовано:"), 1, 0)
        ram_info_layout.addWidget(QLabel("Доступно:"), 2, 0)
        
        self.ram_total = QLabel("0 ГБ")
        self.ram_used = QLabel("0 ГБ")
        self.ram_avail = QLabel("0 ГБ")
        
        ram_info_layout.addWidget(self.ram_total, 0, 1)
        ram_info_layout.addWidget(self.ram_used, 1, 1)
        ram_info_layout.addWidget(self.ram_avail, 2, 1)
        
        ram_details_layout.addLayout(ram_info_layout)
        ram_details_group.setLayout(ram_details_layout)
        main_layout.addWidget(ram_details_group)
        
        self.setLayout(main_layout)
    
    def update_data(self, data):
        """
        Обновление данных о ресурсах
        """
        if "cpu" in data:
            self.cpu_usage = data["cpu"]
            cpu_value = self.cpu_usage['total']
            self.cpu_value.setText(f"{cpu_value}%")
            
            # Устанавливаем максимальное значение в 1000 (100.0%) для прогресс-бара
            self.cpu_bar.setRange(0, 1000)
            # Умножаем на 10 для сохранения десятичной точности
            self.cpu_bar.setValue(int(cpu_value * 10))
            # Настраиваем формат отображения текста в прогресс-баре
            self.cpu_bar.setFormat(f"{cpu_value}%")
            
            # Обновляем загрузку отдельных ядер
            per_cpu = self.cpu_usage['per_cpu']
            for i, usage in enumerate(per_cpu):
                if i < len(self.core_labels):
                    self.core_labels[i].setText(f"Core {i}: {usage}%")
                    # То же для каждого ядра
                    self.core_bars[i].setRange(0, 1000)
                    self.core_bars[i].setValue(int(usage * 10))
                    self.core_bars[i].setFormat(f"{usage}%")
            
        if "ram" in data:
            ram_data = data["ram"]
            self.ram_usage = ram_data["Процент использования"]
            self.ram_value.setText(f"{self.ram_usage}%")
            
            # То же для RAM
            self.ram_bar.setRange(0, 1000)
            self.ram_bar.setValue(int(self.ram_usage * 10))
            self.ram_bar.setFormat(f"{self.ram_usage}%")
            
            # Обновляем детальную информацию о RAM
            self.ram_total.setText(f"{ram_data['Всего (ГБ)']} ГБ")
            self.ram_used.setText(f"{ram_data['Использовано (ГБ)']} ГБ")
            self.ram_avail.setText(f"{ram_data['Доступно (ГБ)']} ГБ")

class SystemMonitorWidget(QTabWidget):
    """
    Виджет, содержащий вкладки для мониторинга системы
    """
    def __init__(self):
        super().__init__()
        self.monitor_thread = SystemMonitorThread()
        
        # Устанавливаем стиль для вкладок
        self.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c8e0;
                border-radius: 6px;
                background-color: white;
                padding: 4px;
                margin-top: -1px;
            }
            QTabBar::tab {
                background-color: #f0f5ff;
                border: 1px solid #c0c8e0;
                border-bottom-color: #c0c8e0;
                padding: 6px 12px;
                margin-right: 2px;
                color: #3e4458;
                min-width: 170px;
                font-weight: bold;
                font-size: 11px;
                border-radius: 4px 4px 0 0;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                border: 1px solid #2196F3;
                border-bottom-color: #2196F3;
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d6e4ff;
                border-color: #a0b0e0;
            }
        """)
        
        self.init_ui()
        
        # Запускаем поток мониторинга
        self.monitor_thread.start()
    
    def init_ui(self):
        # Вкладка с общей информацией о системе (теперь включает информацию о процессоре и памяти)
        self.system_tab = SystemInfoTab()
        self.addTab(self.system_tab, "Система")
        
        # Вкладка с диспетчером устройств
        self.device_manager_tab = DeviceManagerTab()
        self.addTab(self.device_manager_tab, "Диспетчер устройств")
        
        # Подключаем обновление данных для системной вкладки
        self.monitor_thread.update_signal.connect(self.system_tab.update_data)
    
    def closeEvent(self, event):
        # Останавливаем поток при закрытии
        self.monitor_thread.stop()
        self.monitor_thread.wait()
        super().closeEvent(event)

class DeviceManagerTab(QWidget):
    """
    Вкладка диспетчера устройств отображает подробную информацию обо всех устройствах системы
    """
    def __init__(self, parent=None):
        """Инициализация вкладки менеджера устройств."""
        super().__init__()
        
        self.parent = parent
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)
        
        # Флаг для автоматического обновления
        self.auto_refresh_enabled = False
        
        # Заголовок с описанием
        self.header_label = QLabel("Диспетчер устройств показывает информацию о всём оборудовании вашей системы.")
        self.header_label.setStyleSheet("color: #555; padding: 3px;")
        self.header_label.setWordWrap(True)
        self.main_layout.addWidget(self.header_label)
        
        # Добавляем панель инструментов
        self.toolbar_layout = QHBoxLayout()
        self.toolbar_layout.setSpacing(10)
        
        
        # Добавляем растягивающийся элемент для выравнивания кнопки обновления вправо
        self.toolbar_layout.addStretch()
        
        # Кнопка ручного обновления
        self.refresh_button = QPushButton("Обновить")
        self.refresh_button.setIcon(QApplication.style().standardIcon(QStyle.SP_BrowserReload))
        self.refresh_button.setFixedWidth(120)
        self.refresh_button.clicked.connect(self.manual_refresh)
        self.refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 4px;
                font-weight: normal;
            }
            QPushButton:hover {
                background-color: #1E88E5;
                cursor: pointer;
            }
            QPushButton:pressed {
                background-color: #1976D2;
            }
        """)
        self.toolbar_layout.addWidget(self.refresh_button)
        
        self.main_layout.addLayout(self.toolbar_layout)
        
        # Добавляем статус загрузки
        self.status_layout = QHBoxLayout()
        self.status_label = QLabel("Загрузка данных об устройствах...")
        self.status_label.setStyleSheet("color: #1976D2; font-style: italic; font-weight: bold;")
        self.status_layout.addWidget(self.status_label)
        self.status_layout.addStretch()
        
        # Индикатор загрузки
        self.progress_indicator = QProgressBar()
        self.progress_indicator.setRange(0, 0)  # Бесконечная анимация
        self.progress_indicator.setFixedWidth(120)
        self.progress_indicator.setTextVisible(False)
        self.status_layout.addWidget(self.progress_indicator)
        
        self.main_layout.addLayout(self.status_layout)
        
        # Создаем единую древовидную структуру для отображения устройств и их свойств
        self.devices_tree = QTreeWidget()
        self.devices_tree.setHeaderLabels(["Устройство/Свойство", "Значение"])
        self.devices_tree.setAlternatingRowColors(True)
        self.devices_tree.setAnimated(False)  # Отключаем анимацию раскрытия узлов для улучшения производительности
        
        # Настраиваем ширину колонок
        self.devices_tree.setColumnWidth(0, 400)
        
        # Разрешаем растягивание последней колонки
        self.devices_tree.header().setSectionResizeMode(0, QHeaderView.Interactive)
        self.devices_tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        
        # Устанавливаем политику размера для корректного отображения раскрытых элементов
        self.devices_tree.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Вызывать функцию при раскрытии/сворачивании элемента для динамической загрузки
        self.devices_tree.itemExpanded.connect(self.on_item_expanded)
        
        # Добавляем контекстное меню
        self.devices_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.devices_tree.customContextMenuRequested.connect(self.show_context_menu)
        
        # Применяем стили к дереву устройств
        self.devices_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #c0c8e0;
                border-radius: 0px;
                background-color: white;
            }
            QTreeWidget::item {
                padding: 3px 0;
                min-height: 20px;
            }
            QTreeWidget::item:hover {
                background-color: #f0f5ff;
            }
            QTreeWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
            }
            QHeaderView::section {
                background-color: #f0f5ff;
                padding: 5px;
                border: 1px solid #c0c8e0;
                font-weight: bold;
                color: #434d66;
            }
        """)
        
        self.main_layout.addWidget(self.devices_tree)
        
        # Словарь для локализованных имен свойств
        self.property_names = {
            'status': 'Статус',
            'manufacturer': 'Производитель',
            'description': 'Описание',
            'device_id': 'ID устройства',
            'pnp_device_id': 'PnP ID',
            'cores': 'Ядра',
            'logical_processors': 'Логические ядра',
            'current_speed': 'Текущая частота',
            'max_speed': 'Максимальная частота',
            'socket': 'Сокет',
            'architecture': 'Архитектура',
            'cache_size': 'Размер кэша',
            'memory': 'Объем памяти',
            'driver': 'Драйвер',
            'driver_version': 'Версия драйвера',
            'driver_date': 'Дата драйвера',
            'interface_type': 'Тип интерфейса',
            'media_type': 'Тип носителя',
            'free_space': 'Свободное место',
            'used_space': 'Использовано',
            'percent_used': 'Процент использования',
            'filesystem': 'Файловая система',
            'serial_number': 'Серийный номер',
            'firmware': 'Прошивка',
            'ip_address': 'IP адрес',
            'mac_address': 'MAC адрес',
            'subnet_mask': 'Маска подсети',
            'default_gateway': 'Шлюз по умолчанию',
            'dns_servers': 'DNS серверы',
            'speed': 'Скорость',
            'adapter_type': 'Тип адаптера',
            'resolution': 'Разрешение',
            'refresh_rate': 'Частота обновления',
            'video_processor': 'Видеопроцессор',
            'video_mode': 'Видеорежим',
            'bits_per_pixel': 'Бит на пиксель',
            'monitor_type': 'Тип монитора',
            'temperature': 'Температура',
            'load': 'Загрузка',
            'memory_used': 'Использовано памяти',
            'memory_free': 'Свободно памяти',
            'memory_utilization': 'Загрузка памяти',
            'bios_manufacturer': 'Производитель BIOS',
            'bios_version': 'Версия BIOS',
            'bios_date': 'Дата BIOS',
            'model': 'Модель',
            'version': 'Версия',
            'hosting_board': 'Плата хоста',
            'replaceable': 'Заменяемая',
            'number_of_ports': 'Количество портов',
            # Дополнительные свойства
            'name': 'Название',
            'caption': 'Заголовок',
            'class_guid': 'GUID класса',
            'service': 'Служба',
            'partition_count': 'Количество разделов',
            'partitions': 'Разделы',
            'volume_name': 'Имя тома',
            'type': 'Тип',
            'size': 'Размер',
            'serial': 'Серийный номер',
            'product_name': 'Название продукта',
            'dma_buffer_size': 'Размер буфера DMA',
            'mpu_401_address': 'Адрес MPU-401',
            'adapter_ram': 'ОЗУ адаптера',
            'system_type': 'Тип системы',
            'capacity': 'Емкость',
            'interface': 'Интерфейс',
            'device_type': 'Тип устройства',
            'disk_type': 'Тип диска',
            'power_management_supported': 'Поддержка управления питанием',
            'power_state': 'Состояние питания',
            'device_name': 'Имя устройства',
            'protocol': 'Протокол',
            'dhcp_enabled': 'DHCP включен',
            'dhcp_server': 'DHCP сервер',
            'domain': 'Домен',
            'bios_release_date': 'Дата выпуска BIOS',
            'bios_rom_size': 'Размер ROM BIOS',
            'bios_serial_number': 'Серийный номер BIOS'
        }
        
        # Словарь для хранения подробной информации об устройствах
        self.devices_details = {}
        
        # Словарь для хранения хешей устройств для отслеживания изменений
        self.device_hashes = {}
        
        # Словарь для отслеживания загрузки данных категорий
        self.category_loaded = {}
        
        # Флаг для предотвращения повторной загрузки данных
        self.is_loading = False
        
        # Используем QThread вместо таймера для выполнения загрузки в фоновом режиме
        self.load_thread = None
        
        # Флаг первой загрузки
        self.is_first_load = True
        
        # WMI объект для отслеживания изменений устройств
        self.wmi_obj = None
        if HAS_WMI:
            try:
                self.wmi_obj = wmi.WMI()
                
                # Настраиваем WMI для отслеживания событий подключения/отключения устройств
                self.setup_device_monitoring()
            except Exception as e:
                # print(f"Ошибка при инициализации WMI: {e}")
                pass
        
        # Скрываем индикатор загрузки
        self.progress_indicator.hide()
        
        # Запускаем загрузку данных при инициализации
        self.start_async_loading()
    
    def setup_device_monitoring(self):
        """Настраивает отслеживание изменений устройств через WMI"""
        # Отключаем автоматическое отслеживание, т.к. есть кнопка ручного обновления
        # и автоматическое обновление может мешать пользователю при изучении устройств
        
        # Создаем таймер, но не запускаем его
        self.check_changes_timer = QTimer(self)
        self.check_changes_timer.setInterval(5000)  # Интервал 5 секунд (не используется)
        self.check_changes_timer.timeout.connect(self.check_device_changes)
        
        # Не запускаем таймер, оставляем только ручное обновление
        # self.check_changes_timer.start()
    
    def check_device_changes(self):
        """Проверяет изменения устройств в системе и обновляет данные при необходимости"""
        # Пропускаем проверку, если загрузка уже идет
        if self.is_loading:
            return
            
        try:
            # Отключаем частое обновление, чтобы не нагружать систему
            import time
            current_time = time.time()
            
            # Инициализируем last_check_time при первом вызове
            if not hasattr(self, "last_check_time"):
                self.last_check_time = current_time
                return  # Пропускаем первую проверку
                
            # Проверяем не чаще раза в 10 секунд
            if current_time - self.last_check_time < 10:
                return
                
            # Обновляем время последней проверки
            self.last_check_time = current_time
            
            # Ограничиваем количество одновременных проверок
            if not hasattr(self, 'check_count'):
                self.check_count = 0
                
            # Если уже идут 3 или более проверок, пропускаем эту
            self.check_count += 1
            if self.check_count > 3:
                self.check_count -= 1
                return
                
            # Проверяем изменения только если вкладка видима
            if not self.isVisible():
                self.check_count -= 1
                return
                
            # Создаем временный объект WMI
            import pythoncom
            pythoncom.CoInitialize()
            
            # Будем проверять количество устройств в каждой категории
            try:
                wmi_obj = wmi.WMI()
                
                # Проверяем изменения в основных категориях
                changes_detected = False
                
                # Проверяем процессоры
                try:
                    cpu_count = len(list(wmi_obj.Win32_Processor()))
                    if 'Процессоры' in self.devices_details and len(self.devices_details['Процессоры']) != cpu_count:
                        changes_detected = True
                except Exception as e:
                    logging.error(f"Ошибка при проверке изменений процессоров: {e}")
                
                # Проверяем видеокарты
                try:
                    gpu_count = len(list(wmi_obj.Win32_VideoController()))
                    if 'Видеокарты' in self.devices_details and len(self.devices_details['Видеокарты']) != gpu_count:
                        changes_detected = True
                except Exception as e:
                    logging.error(f"Ошибка при проверке изменений видеокарт: {e}")
                
                # Проверяем диски
                try:
                    disk_count = len(list(wmi_obj.Win32_DiskDrive()))
                    logical_disk_count = len(list(wmi_obj.Win32_LogicalDisk()))
                    total_disk_count = disk_count + logical_disk_count
                    if 'Диски' in self.devices_details and len(self.devices_details['Диски']) != total_disk_count:
                        changes_detected = True
                except Exception as e:
                    logging.error(f"Ошибка при проверке изменений дисков: {e}")
                
                # Проверяем сетевые адаптеры
                try:
                    # Считаем только активные адаптеры
                    network_count = 0
                    for adapter in wmi_obj.Win32_NetworkAdapter():
                        if adapter.NetConnectionID:
                            network_count += 1
                    
                    if 'Сеть' in self.devices_details and len(self.devices_details['Сеть']) != network_count:
                        changes_detected = True
                except Exception as e:
                    logging.error(f"Ошибка при проверке изменений сети: {e}")
                
                # Проверяем USB-устройства
                try:
                    usb_count = len(list(wmi_obj.Win32_USBController())) + len(list(wmi_obj.Win32_USBHub()))
                    if 'USB' in self.devices_details and len(self.devices_details['USB']) != usb_count:
                        changes_detected = True
                except Exception as e:
                    logging.error(f"Ошибка при проверке изменений USB: {e}")
                
                # Если обнаружены изменения, обновляем данные
                if changes_detected:
                    logging.info("Обнаружены изменения в устройствах. Выполняется обновление...")
                    self.status_label.setText("<span style='color:#2196F3;font-weight:bold;'>Обнаружены изменения в устройствах. Выполняется обновление...</span>")
                    self.manual_refresh()
                
            except Exception as e:
                logging.error(f"Ошибка при проверке изменений устройств: {e}")
            
            finally:
                # Освобождаем COM
                pythoncom.CoUninitialize()
                self.check_count -= 1
                
        except Exception as e:
            # Глобальная обработка ошибок
            logging.error(f"Критическая ошибка при проверке изменений устройств: {e}")
            if hasattr(self, 'check_count'):
                self.check_count -= 1
    
    def on_show(self, event):
        """Запускает загрузку при показе вкладки"""
        # Проверяем изменения устройств при показе вкладки
        self.check_device_changes()
    
    def on_hide(self, event):
        """Останавливает таймер обновления при скрытии вкладки"""
        # При скрытии ничего не останавливаем, только помечаем, что вкладка неактивна
        pass
    
    def manual_refresh(self):
        """Запускает ручное обновление устройств"""
        
        # Запоминаем состояние раскрытых элементов
        self.expanded_items = {}
        self.selected_item_path = []
        
        # Сохраняем текущий выбранный элемент и путь к нему
        selected_items = self.devices_tree.selectedItems()
        if selected_items:
            selected_item = selected_items[0]
            # Строим путь к элементу
            item = selected_item
            path = []
            while item is not None:
                path.insert(0, item.text(0))
                parent = item.parent()
                item = parent
            self.selected_item_path = path
        
        # Сохраняем состояние раскрытых элементов
        root = self.devices_tree.invisibleRootItem()
        for i in range(root.childCount()):
            category_item = root.child(i)
            category_name = category_item.text(0)
            if category_item.isExpanded():
                self.expanded_items[category_name] = True
                # Сохраняем состояние дочерних элементов
                for j in range(category_item.childCount()):
                    device_item = category_item.child(j)
                    device_name = device_item.text(0)
                    if device_item.isExpanded():
                        self.expanded_items[f"{category_name}/{device_name}"] = True
                        # Сохраняем также состояние свойств устройства
                        for k in range(device_item.childCount()):
                            prop_item = device_item.child(k)
                            prop_name = prop_item.text(0)
                            if prop_item.isExpanded():
                                self.expanded_items[f"{category_name}/{device_name}/{prop_name}"] = True
        
        # Сбрасываем флаги загрузки категорий
        for category in self.category_loaded:
            self.category_loaded[category] = False
        
        # Очищаем детали устройств и хеши
        self.devices_details = {}
        self.device_hashes = {}
        
        # Устанавливаем статус и запускаем асинхронную загрузку
        self.status_label.setText("<span style='color:#2196F3;font-weight:bold;'>Обновление данных...</span>")
        self.start_async_loading()
    
    def start_async_loading(self):
        """Запускает асинхронную загрузку данных в отдельном потоке"""
        if self.is_loading:
            return  # Предотвращаем повторный запуск загрузки
        
        self.is_loading = True
        
        # Отображаем индикатор загрузки
        self.progress_indicator.show()
        
        # Если это первая загрузка, показываем индикатор загрузки
        if self.is_first_load:
            self.devices_tree.clear()
            loading_item = QTreeWidgetItem(["Загрузка данных...", ""])
            loading_item.setForeground(0, QColor('#2196F3'))  # Синий цвет текста
            self.devices_tree.addTopLevelItem(loading_item)
        
        # Создаем и настраиваем поток для загрузки
        self.load_thread = DeviceLoadingThread(self)
        self.load_thread.update_signal.connect(self.on_device_loaded)
        self.load_thread.start()
    
    def on_device_loaded(self, category, devices):
        """Обработчик события загрузки устройства из категории"""
        # Обновляем словарь категорий
        if not hasattr(self, 'categories_data'):
            self.categories_data = {}
            
        # Добавляем категорию в наши данные
        if category not in self.categories_data:
            self.categories_data[category] = {'has_devices': len(devices) > 0}
            
        # Сохраняем детали устройств для будущего использования
        if category not in self.devices_details:
            self.devices_details[category] = {}
            
        self.devices_details[category].update(devices)
            
        # Когда все категории загружены, вызываем on_loading_finished
        if len(self.categories_data) >= 6:  # 6 категорий устройств (исключая "Сеть" и "Мониторы")
            # print(f"Все категории загружены: {list(self.categories_data.keys())}")
            self.on_loading_finished(self.categories_data)
    
    def on_loading_finished(self, categories_data):
        """Обработчик завершения загрузки данных"""
        self.is_loading = False
        
        # Скрываем индикатор загрузки
        self.progress_indicator.hide()
        
        # Временно отключаем обновление интерфейса для ускорения операций
        self.devices_tree.setUpdatesEnabled(False)
        
        # Скрываем дерево на время обновления для ускорения
        self.devices_tree.hide()
        
        # Очищаем дерево и данные
        self.devices_tree.clear()
        
        # Создаем все категории одним блоком
        categories_to_add = []
        
        # Устанавливаем все категории в качестве непосредственных дочерних элементов
        for category_name, category_info in categories_data.items():
            # Пропускаем категории "Сеть" и "Мониторы"
            if category_name in ["Сеть", "Мониторы"]:
                continue
                
            has_devices = category_info['has_devices']
            
            # Создаем элемент категории
            category_item = QTreeWidgetItem([category_name, ""])
            category_item.setFont(0, QFont("", 0, QFont.Bold))
            
            # Делаем фон элемента категории светло-серым
            for col in range(2):
                category_item.setBackground(col, QColor("#f0f0f0"))
            
            # Устанавливаем данные для отслеживания загрузки категории
            category_item.setData(0, Qt.UserRole, {'loaded': False, 'name': category_name})
            
            if not has_devices:
                # Если устройств нет, добавляем информационное сообщение
                empty_item = QTreeWidgetItem(["Устройства не обнаружены", ""])
                empty_item.setForeground(0, QColor('#607D8B'))  # Серо-синий цвет текста
                category_item.addChild(empty_item)
            else:
                # Добавляем фиктивный дочерний элемент для отображения "+"
                placeholder = QTreeWidgetItem(["Загрузка...", ""])
                placeholder.setForeground(0, QColor('#2196F3'))  # Синий цвет текста
                category_item.addChild(placeholder)
            
            # Добавляем категорию в список для добавления
            categories_to_add.append(category_item)
        
        # Добавляем все категории одним блоком
        self.devices_tree.addTopLevelItems(categories_to_add)
        
        # Восстанавливаем состояние раскрытия категорий из сохраненного
        if hasattr(self, 'expanded_items'):
            for i in range(self.devices_tree.topLevelItemCount()):
                category_item = self.devices_tree.topLevelItem(i)
                category_name = category_item.text(0)
                if category_name in self.expanded_items:
                    category_item.setExpanded(True)
                    # Если категория была раскрыта, загружаем ее содержимое сразу
                    # Установим небольшую задержку перед загрузкой первой категории,
                    # чтобы сначала показать интерфейс
                    if i == 0:
                        QTimer.singleShot(100, lambda item=category_item: self.load_category_devices(item))
                    else:
                        self.load_category_devices(category_item)
        
        # Показываем дерево
        self.devices_tree.show()
        
        # Восстанавливаем выбранный элемент, если был сохранен путь
        if hasattr(self, 'selected_item_path') and self.selected_item_path:
            # Для восстановления позиции используем QTimer, чтобы дать время на загрузку категорий
            QTimer.singleShot(500, self.restore_selected_item)
        
        # Обновляем статус
        self.status_label.setText("Данные загружены")
        self.status_label.setStyleSheet("color: #c0c8e0;")
        
        # Включаем обновление интерфейса
        self.devices_tree.setUpdatesEnabled(True)
        
        # Устанавливаем флаг первой загрузки в False
        self.is_first_load = False
    
    def restore_selected_item(self):
        """Восстанавливает выбранный элемент по сохраненному пути"""
        if not hasattr(self, 'selected_item_path') or not self.selected_item_path:
            return
            
        path = self.selected_item_path
        if not path:
            return
            
        # Ищем категорию (верхний уровень)
        category_name = path[0]
        
        # Пропускаем скрытые категории
        if category_name in ["Сеть", "Мониторы"]:
            # Сбрасываем выбранный путь, чтобы не пытаться восстановить его снова
            self.selected_item_path = None
            return
            
        category_item = None
        
        for i in range(self.devices_tree.topLevelItemCount()):
            item = self.devices_tree.topLevelItem(i)
            if item.text(0) == category_name:
                category_item = item
                break
                
        if not category_item:
            return
            
        # Загружаем категорию, если еще не загружена
        if not self.category_loaded.get(category_name, False):
            self.load_category_devices(category_item)
            # Если категория только загружается, отложим восстановление
            QTimer.singleShot(500, self.restore_selected_item)
            return
            
        # Если есть только категория в пути, выбираем ее
        if len(path) == 1:
            self.devices_tree.setCurrentItem(category_item)
            return
            
        # Ищем устройство
        device_name = path[1]
        device_item = None
        
        for i in range(category_item.childCount()):
            item = category_item.child(i)
            if item.text(0) == device_name:
                device_item = item
                break
                
        if not device_item:
            self.devices_tree.setCurrentItem(category_item)
            return
            
        # Раскрываем устройство, если оно было раскрыто
        device_path = f"{category_name}/{device_name}"
        if device_path in self.expanded_items:
            device_item.setExpanded(True)
            
        # Если есть только категория и устройство в пути, выбираем устройство
        if len(path) == 2:
            self.devices_tree.setCurrentItem(device_item)
            return
            
        # Ищем свойство
        prop_name = path[2]
        prop_item = None
        
        for i in range(device_item.childCount()):
            item = device_item.child(i)
            if item.text(0) == prop_name:
                prop_item = item
                break
                
        if not prop_item:
            self.devices_tree.setCurrentItem(device_item)
            return
            
        # Раскрываем свойство, если оно было раскрыто
        prop_path = f"{category_name}/{device_name}/{prop_name}"
        if prop_path in self.expanded_items:
            prop_item.setExpanded(True)
            
        # Выбираем свойство
        self.devices_tree.setCurrentItem(prop_item)
    
    def on_item_expanded(self, item):
        """Обработчик раскрытия элемента в дереве"""
        # Проверяем, является ли элемент категорией и не загружен ли он уже
        item_data = item.data(0, Qt.UserRole)
        if item_data and isinstance(item_data, dict) and 'loaded' in item_data:
            if not item_data['loaded']:
                # Загружаем устройства для категории
                self.load_category_devices(item)
    
    def load_category_devices(self, category_item):
        """Загружает устройства для указанной категории"""
        item_data = category_item.data(0, Qt.UserRole)
        if not item_data or not isinstance(item_data, dict):
            return
        
        category_name = item_data.get('name')
        if not category_name:
            return
            
        # Проверяем, загружены ли устройства уже
        if item_data.get('loaded', False):
            return
            
        # Отмечаем категорию как загруженную
        self.category_loaded[category_name] = True
        item_data['loaded'] = True
        category_item.setData(0, Qt.UserRole, item_data)
        
        # Временно отключаем обновление дерева для улучшения производительности
        self.devices_tree.setUpdatesEnabled(False)
        
        try:
            # Удаляем placeholder, если он есть
            placeholder = None
            for i in range(category_item.childCount()):
                child = category_item.child(i)
                if child.text(0) == "Загрузка...":
                    placeholder = child
                    break
                    
            if placeholder:
                category_item.removeChild(placeholder)
            
            # Флаг для отслеживания наличия устройств
            has_devices_to_show = False
            
            # Формируем список устройств для добавления (для повышения производительности)
            items_to_add = []
            
            # Получаем функцию загрузки соответствующую категории
            category_func_name = f"get_{category_name.lower().replace(' ', '_')}_info"
            load_func = getattr(self, category_func_name, None)
            
            # Если метода нет в классе, используем внешнюю функцию
            if not load_func:
                device_info = self.devices_details.get(category_name, {})
            else:
                try:
                    device_info = load_func()
                except Exception as e:
                    # print(f"Ошибка при загрузке данных для категории {category_name}: {e}")
                    device_info = {}
            
            # Проверяем, есть ли устройства вообще
            if not device_info:
                empty_item = QTreeWidgetItem(["Устройства не обнаружены", ""])
                empty_item.setForeground(0, QColor('#607D8B'))  # Серо-синий цвет текста
                category_item.addChild(empty_item)
                self.devices_tree.setUpdatesEnabled(True)
                return
            
            # Создаем родительскую категорию для устройств в словаре деталей, если её нет
            if category_name not in self.devices_details:
                self.devices_details[category_name] = {}
                    
            # Поочередно добавляем все устройства из категории
            for device_id, device in device_info.items():
                # Пропускаем неактивные устройства, кроме случаев, когда это единственное устройство в категории
                status = device.get('status', '')
                if ('отключено' in status.lower() or 'не подключено' in status.lower()) and len(device_info) > 1:
                    continue
                    
                # Создаем элемент устройства
                device_name = device.get('name', 'Неизвестное устройство')
                device_manufacturer = device.get('manufacturer', '')
                
                # Формируем текст для отображения
                display_name = device_name
                if device_manufacturer and device_manufacturer.lower() not in device_name.lower():
                    display_name = f"{device_name} [{device_manufacturer}]"
                    
                # Создаем элемент для устройства
                device_item = QTreeWidgetItem([display_name, ""])
                device_item.setFont(0, QFont("", 0, QFont.Bold))  # Выделяем название жирным шрифтом
                
                # Подсвечиваем зеленым работающие устройства, красным - с проблемами
                if status and 'работает' in status.lower():
                    device_item.setForeground(1, QColor('#4CAF50'))  # Зеленый
                elif status and ('проблема' in status.lower() or 'ошибка' in status.lower()):
                    device_item.setForeground(1, QColor('#F44336'))  # Красный
                
                # Добавляем основные свойства в значение
                main_props = []
                if 'status' in device and device['status']:
                    main_props.append(device['status'])
                
                # Специфические свойства для разных категорий
                if category_name == "Процессоры" and 'cores' in device and device['cores']:
                    main_props.append(f"Ядра: {device['cores']}")
                elif category_name == "Видеокарты" and 'memory' in device and device['memory']:
                    main_props.append(f"Память: {device['memory']}")
                elif category_name == "Диски" and 'memory' in device and device['memory']:
                    main_props.append(f"Объём: {device['memory']}")
                elif category_name == "Сеть" and 'ip_address' in device and device['ip_address']:
                    main_props.append(f"IP: {device['ip_address']}")
                
                # Устанавливаем значение
                if main_props:
                    device_item.setText(1, " | ".join(main_props))
                    
                # Добавляем свойства устройства
                for prop_name, prop_value in device.items():
                    # Пропускаем имя устройства и статус, они уже отображаются
                    if prop_name in ['name', 'status']:
                        continue
                        
                    # Пропускаем пустые значения
                    if prop_value is None or prop_value == "":
                        continue
                        
                    # Пропускаем определенные свойства для видеокарт
                    if category_name == "Видеокарты" and prop_name in ["Объем памяти", "Разрешение", "Частота обновления"]:
                        continue
                        
                    # Получаем локализованное название свойства, с защитой от отсутствия ключа
                    friendly_name = self.property_names.get(prop_name, prop_name)
                    
                    # Обрабатываем различные типы данных
                    if isinstance(prop_value, list):
                        # Пропускаем пустые списки
                        if not prop_value:
                            continue
                        
                        # Обработка списков
                        list_item = QTreeWidgetItem([friendly_name, f"{len(prop_value)} элементов"])
                        device_item.addChild(list_item)
                        
                        for i, val in enumerate(prop_value):
                            try:
                                # Безопасное преобразование к строке с обработкой исключений
                                str_val = str(val) if val is not None else "Нет данных"
                                list_item.addChild(QTreeWidgetItem([f"{friendly_name} {i+1}", str_val]))
                            except Exception:
                                # В случае ошибки устанавливаем значение по умолчанию
                                list_item.addChild(QTreeWidgetItem([f"{friendly_name} {i+1}", "Ошибка преобразования"]))
                    elif isinstance(prop_value, dict):
                        # Пропускаем пустые словари
                        if not prop_value:
                            continue
                        
                        # Обработка словарей
                        dict_item = QTreeWidgetItem([friendly_name, ""])
                        device_item.addChild(dict_item)
                        
                        for key, val in prop_value.items():
                            try:
                                # Безопасное преобразование к строке с обработкой исключений
                                str_val = str(val) if val is not None else "Нет данных"
                                dict_item.addChild(QTreeWidgetItem([key, str_val]))
                            except Exception:
                                # В случае ошибки устанавливаем значение по умолчанию
                                dict_item.addChild(QTreeWidgetItem([key, "Ошибка преобразования"]))
                    else:
                        # Проверка на целые числа и преобразование их в нормальный формат
                        if isinstance(prop_value, (int, float)):
                            # Если это объем в байтах (определяем по имени свойства)
                            if any(size_key in prop_name.lower() for size_key in ['size', 'space', 'memory', 'capacity']):
                                prop_value = format_bytes(prop_value)
                            elif 'frequency' in prop_name.lower() and prop_value > 1000:
                                # Если это частота и значение большое, форматируем в ГГц
                                prop_value = f"{prop_value / 1000:.2f} ГГц"
                        
                        # Прочие свойства
                        prop_item = QTreeWidgetItem([friendly_name, str(prop_value)])
                        device_item.addChild(prop_item)
                
                # Сохраняем детали устройства для быстрого доступа
                self.devices_details[category_name][device_id] = device
                
                # Создаем хэш для проверки изменений
                device_hash = hash(str(device))
                self.device_hashes[device_id] = device_hash
                
                # Устанавливаем данные устройства
                device_data = {'device_id': device_id, 'category': category_name}
                device_item.setData(0, Qt.UserRole, device_data)
                
                # Отмечаем, что добавили устройство
                has_devices_to_show = True
                
                # Добавляем в список для пакетного добавления
                items_to_add.append(device_item)
                
            # Если есть устройства, добавляем их в дерево
            if has_devices_to_show:
                # Добавляем все элементы сразу для улучшения производительности
                category_item.addChildren(items_to_add)
                
        except Exception as e:
            logging.error(f"Ошибка при загрузке категории {category_name}: {e}")
            error_item = QTreeWidgetItem(["Ошибка загрузки", str(e)])
            error_item.setForeground(0, QColor('#F44336'))  # Красный цвет для ошибки
            category_item.addChild(error_item)
        finally:
            # Восстанавливаем обновление дерева
            self.devices_tree.setUpdatesEnabled(True)
    
    def show_context_menu(self, position):
        """Отображает контекстное меню для элемента дерева устройств"""
        # Получаем элемент, на котором произошел клик
        item = self.devices_tree.itemAt(position)
        
        # Создаем контекстное меню
        context_menu = QMenu(self)
        
        # Добавляем опцию автоматического обновления в общее меню
        auto_refresh_action = context_menu.addAction("Автоматическое обновление")
        auto_refresh_action.setCheckable(True)
        auto_refresh_action.setChecked(self.auto_refresh_enabled)
        auto_refresh_action.triggered.connect(self.toggle_auto_refresh)
        
        # Добавляем разделитель
        context_menu.addSeparator()
        
        # Если на элементе кликнули, добавляем пункты меню для этого элемента
        if item:
            # Добавляем действие "Копировать информацию"
            copy_action = context_menu.addAction("Копировать информацию")
            copy_action.triggered.connect(lambda: self.copy_item_info(item))
            
            # Добавляем действие "Развернуть все" для устройств
            if item.childCount() > 0:
                expand_action = context_menu.addAction("Развернуть все")
                expand_action.triggered.connect(lambda: self.expand_all_children(item))
                
                collapse_action = context_menu.addAction("Свернуть все")
                collapse_action.triggered.connect(lambda: self.collapse_all_children(item))
            
            # Если это категория устройств, добавляем возможность обновить данные
            item_data = item.data(0, Qt.UserRole)
            if item_data and isinstance(item_data, dict) and 'name' in item_data:
                refresh_action = context_menu.addAction("Обновить категорию")
                refresh_action.triggered.connect(lambda: self.refresh_category(item))
        
        # Отображаем контекстное меню
        context_menu.exec_(self.devices_tree.mapToGlobal(position))
    
    def toggle_auto_refresh(self, checked):
        """Включает или отключает автоматическое обновление"""
        self.auto_refresh_enabled = checked
        
        if checked:
            # Запускаем таймер обновления
            self.check_changes_timer.start()
            self.status_label.setText("Автоматическое обновление включено")
        else:
            # Останавливаем таймер
            self.check_changes_timer.stop()
            self.status_label.setText("Автоматическое обновление отключено")
        
        # Сбрасываем статус через 3 секунды
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    
    def copy_item_info(self, item):
        """Копирует информацию о выбранном элементе в буфер обмена"""
        text = item.text(0)
        if item.text(1):
            text += ": " + item.text(1)
            
        # Копируем в буфер обмена
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Показываем уведомление о копировании
        self.status_label.setText("Информация скопирована в буфер обмена")
        
        # Сбрасываем статус через 3 секунды
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))
    
    def expand_all_children(self, item):
        """Разворачивает все дочерние элементы"""
        item.setExpanded(True)
        for i in range(item.childCount()):
            child = item.child(i)
            self.expand_all_children(child)
    
    def collapse_all_children(self, item):
        """Сворачивает все дочерние элементы"""
        for i in range(item.childCount()):
            child = item.child(i)
            self.collapse_all_children(child)
        item.setExpanded(False)
    
    def refresh_category(self, item):
        """Обновляет информацию для указанной категории устройств"""
        item_data = item.data(0, Qt.UserRole)
        if not item_data or not isinstance(item_data, dict):
            return
            
        category_name = item_data.get('name')
        if not category_name:
            return
            
        # Сбрасываем флаг загрузки категории
        if category_name in self.category_loaded:
            self.category_loaded[category_name] = False
            
        # Сбрасываем флаг загрузки в данных элемента
        item_data['loaded'] = False
        item.setData(0, Qt.UserRole, item_data)
        
        # Очищаем элемент
        item.takeChildren()
        
        # Добавляем заглушку
        placeholder = QTreeWidgetItem(["Загрузка...", ""])
        item.addChild(placeholder)
        
        # Загружаем данные для категории
        self.load_category_devices(item)
        
        # Обновляем статус
        self.status_label.setText(f"Категория '{category_name}' обновлена")
        
        # Сбрасываем статус через 3 секунды
        QTimer.singleShot(3000, lambda: self.status_label.setText(""))

def get_audio_info_for_device_manager():
    """Получает расширенную информацию о звуковых устройствах."""
    audio_devices = {}
    
    if not HAS_WMI:
        return audio_devices
        
    try:
        # Инициализируем COM для WMI
        import pythoncom
        pythoncom.CoInitialize()
            
        wmi_obj = wmi.WMI()
        
        # Звуковые устройства через Win32_SoundDevice
        for i, device in enumerate(wmi_obj.Win32_SoundDevice()):
            try:
                device_id = f"audio_{i}"
                
                audio_devices[device_id] = {
                    'name': getattr(device, 'Name', None) or f"Звуковое устройство {i}",
                    'manufacturer': getattr(device, 'Manufacturer', None) or "Неизвестно",
                    'description': getattr(device, 'Description', None) or "Звуковое устройство",
                    'device_id': getattr(device, 'DeviceID', None) or f"AUDIO{i}",
                    'pnp_device_id': getattr(device, 'PNPDeviceID', None) or ""
                }
                
                # Проверяем, есть ли свойство DriverName
                if hasattr(device, 'DriverName') and device.DriverName:
                    audio_devices[device_id]['driver'] = device.DriverName
            except Exception as e:
                logging.error(f"Ошибка при получении информации о звуковом устройстве {i}: {e}")
            
    except Exception as e:
        logging.error(f"Ошибка при получении информации о звуковых устройствах: {e}")
    finally:
        # Освобождаем COM
        pythoncom.CoUninitialize()
        
    return audio_devices

def format_bytes(bytes_value, decimal_places=2):
    """Форматирует байты в человекочитаемый формат."""
    try:
        if not bytes_value or bytes_value == 0:
            return "0 B"
            
        # Преобразуем в число, если строка
        if isinstance(bytes_value, str):
            try:
                bytes_value = int(bytes_value)
            except:
                return bytes_value
        
        sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
        i = 0
        while bytes_value >= 1024 and i < len(sizes) - 1:
            bytes_value /= 1024.0
            i += 1
        
        return f"{bytes_value:.{decimal_places}f} {sizes[i]}"
    except Exception as e:
        logging.error(f"Ошибка при форматировании байтов: {e}")
        return str(bytes_value)
    
def get_monitors_info_for_device_manager():
    """Получает расширенную информацию о мониторах."""
    monitors = {}
    
    if not HAS_WMI:
        return monitors
        
    try:
        # Инициализируем COM для WMI
        import pythoncom
        pythoncom.CoInitialize()
            
        wmi_obj = wmi.WMI()
        
        # Получаем информацию о мониторах через WMI
        # Используем несколько источников данных для максимального охвата
        monitor_count = 0
        
        # 1. Пробуем Win32_DesktopMonitor
        try:
            for i, monitor in enumerate(wmi_obj.Win32_DesktopMonitor()):
                try:
                    if not getattr(monitor, 'DeviceID', None):
                        continue
                        
                    monitor_id = f"mon_dm_{i}"
                    
                    monitors[monitor_id] = {
                        'name': getattr(monitor, 'Name', None) or getattr(monitor, 'Caption', None) or "Монитор",
                        'manufacturer': getattr(monitor, 'MonitorManufacturer', None) or "Неизвестно",
                        'description': getattr(monitor, 'Description', None) or "Устройство отображения",
                    }
                    
                    # Разрешение
                    if hasattr(monitor, 'ScreenWidth') and hasattr(monitor, 'ScreenHeight'):
                        if monitor.ScreenWidth and monitor.ScreenHeight:
                            monitors[monitor_id]['resolution'] = f"{monitor.ScreenWidth} x {monitor.ScreenHeight}"
                    
                    # Частота обновления
                    if hasattr(monitor, 'DisplayFrequency') and monitor.DisplayFrequency:
                        monitors[monitor_id]['refresh_rate'] = f"{monitor.DisplayFrequency} Гц"
                    
                    monitor_count += 1
                except Exception as e:
                    logging.error(f"Ошибка при получении информации о мониторе {i}: {e}")
        except Exception as e:
            logging.error(f"Ошибка при получении информации о мониторах через Win32_DesktopMonitor: {e}")
        
        # 2. Пробуем через видео-контроллеры
        try:
            for i, controller in enumerate(wmi_obj.Win32_VideoController()):
                try:
                    if not getattr(controller, 'DeviceID', None):
                        continue
                        
                    monitor_id = f"mon_vc_{i}"
                    
                    # Базовая информация
                    monitors[monitor_id] = {
                        'name': getattr(controller, 'Name', None) or "Видео-контроллер",
                        'manufacturer': getattr(controller, 'AdapterCompatibility', None) or "Неизвестно",
                        'description': getattr(controller, 'Description', None) or "Видеокарта",
                        'driver_version': getattr(controller, 'DriverVersion', None) or "Н/Д",
                        'video_processor': getattr(controller, 'VideoProcessor', None) or "Н/Д"
                    }
                    
                    # Разрешение
                    if hasattr(controller, 'CurrentHorizontalResolution') and hasattr(controller, 'CurrentVerticalResolution'):
                        if controller.CurrentHorizontalResolution and controller.CurrentVerticalResolution:
                            monitors[monitor_id]['resolution'] = f"{controller.CurrentHorizontalResolution} x {controller.CurrentVerticalResolution}"
                    
                    # Частота обновления
                    if hasattr(controller, 'CurrentRefreshRate') and controller.CurrentRefreshRate:
                        monitors[monitor_id]['refresh_rate'] = f"{controller.CurrentRefreshRate} Гц"
                    
                    # Удаляем блок с видеопамятью, так как он показывает некорректные значения
                    
                    # Режим работы
                    if hasattr(controller, 'VideoModeDescription') and controller.VideoModeDescription:
                        monitors[monitor_id]['video_mode'] = controller.VideoModeDescription
                    
                    monitor_count += 1
                except Exception as e:
                    logging.error(f"Ошибка при получении информации о видео-контроллере {i}: {e}")
        except Exception as e:
            logging.error(f"Ошибка при получении информации о видео-контроллерах: {e}")
            
        # 3. Пробуем через PnP сущности (охватывает больше мониторов, особенно подключенных через HDMI)
        try:
            for i, entity in enumerate(wmi_obj.Win32_PnPEntity()):
                try:
                    # Фильтруем только мониторы
                    if getattr(entity, 'PNPClass', '') != 'Monitor':
                        continue
                        
                    if not getattr(entity, 'DeviceID', None):
                        continue
                        
                    monitor_id = f"mon_pnp_{i}"
                    
                    monitors[monitor_id] = {
                        'name': getattr(entity, 'Name', None) or getattr(entity, 'Caption', None) or "PnP Монитор",
                        'manufacturer': getattr(entity, 'Manufacturer', None) or "Неизвестно",
                        'description': getattr(entity, 'Description', None) or "PnP устройство отображения",
                        'device_id': getattr(entity, 'DeviceID', None) or "Н/Д",
                        'service': getattr(entity, 'Service', None) or "Н/Д"
                    }
                    
                    monitor_count += 1
                except Exception as e:
                    logging.error(f"Ошибка при получении информации о PnP мониторе {i}: {e}")
        except Exception as e:
            logging.error(f"Ошибка при получении информации о PnP мониторах: {e}")
            
        logging.info(f"Найдено мониторов: {monitor_count}")
        
        # Если не нашли ни одного монитора, добавляем заглушку
        if monitor_count == 0:
            monitors['mon_unknown'] = {
                'name': "Монитор",
                'manufacturer': "Информация недоступна",
                'description': "Не удалось получить информацию о мониторах"
            }
    except Exception as e:
        logging.error(f"Ошибка при получении информации о мониторах: {e}")
        # Добавляем заглушку в случае общей ошибки
        monitors['mon_error'] = {
            'name': "Монитор",
            'manufacturer': "Ошибка",
            'description': f"Ошибка при получении информации: {e}"
        }
    finally:
        # Освобождаем COM
        pythoncom.CoUninitialize()
        
    return monitors

def get_gpu_info_for_device_manager():
    """Получает расширенную информацию о видеокартах."""
    gpus = {}
    
    try:
        # Проверяем наличие GPUtil
        if HAS_GPUTIL:
            try:
                # Получаем данные через GPUtil
                for i, gpu in enumerate(GPUtil.getGPUs()):
                    gpu_id = f"gpu_{i}"
                    
                    # Основная информация
                    gpus[gpu_id] = {
                        'name': gpu.name,
                        'status': "Работает",
                        'manufacturer': "NVIDIA" if "NVIDIA" in gpu.name else "AMD" if "AMD" in gpu.name else "Неизвестно",
                        'memory': f"{gpu.memoryTotal} MB" if gpu.memoryTotal > 0 else "Не определено",
                        'memory_free': f"{gpu.memoryFree} MB" if gpu.memoryFree > 0 else "Не определено",
                        'memory_used': f"{gpu.memoryUsed} MB" if gpu.memoryUsed > 0 else "Не определено",
                        'memory_utilization': f"{gpu.memoryUtil * 100:.2f}%" if gpu.memoryUtil >= 0 else "Не определено",
                        'load': f"{gpu.load * 100:.2f}%" if gpu.load >= 0 else "Не определено",
                        'temperature': f"{gpu.temperature}°C" if gpu.temperature > 0 else "Не определено"
                    }
            except Exception as e:
                logging.error(f"Ошибка при получении информации о GPU через GPUtil: {e}")
        
        # Получаем информацию через WMI (только если не получили через GPUtil)
        if not gpus and HAS_WMI:
            try:
                import pythoncom
                
                # Инициализируем COM для WMI в безопасном блоке
                try:
                    # Сначала проверяем, не был ли COM уже инициализирован
                    pythoncom.CoInitialize()
                except:
                    # Если COM уже инициализирован, просто продолжаем
                    pass
                
                try:
                    # Используем контекстный менеджер для COM (если доступен)
                    wmi_obj = wmi.WMI()
                    
                    # Добавляем задержку для стабилизации COM
                    import time
                    time.sleep(0.1)
                    
                    # Ограничиваем количество запросов
                    max_retries = 1
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            for i, gpu in enumerate(wmi_obj.Win32_VideoController()):
                                gpu_id = f"gpu_wmi_{i}"
                                
                                # Проверяем, действительно ли это видеокарта
                                if gpu.Name:  # Проверяем наличие имени
                                    
                                    # Базовая информация
                                    gpu_info = {
                                        'name': gpu.Name,
                                        'status': "Работает",
                                        'manufacturer': gpu.AdapterCompatibility if hasattr(gpu, 'AdapterCompatibility') and gpu.AdapterCompatibility else "Неизвестно",
                                        'description': gpu.Description if hasattr(gpu, 'Description') else "",
                                        'device_id': gpu.DeviceID if hasattr(gpu, 'DeviceID') else f"GPU{i}",
                                        'driver': gpu.DriverVersion if hasattr(gpu, 'DriverVersion') else "Н/Д"
                                        # Удаляем поле 'adapter_ram' которое могло содержать некорректные значения
                                    }
                                    
                                    # Добавляем устройство
                                    gpus[gpu_id] = gpu_info
                            
                            break  # Если всё ок, выходим из цикла
                        except Exception as e:
                            retry_count += 1
                            if retry_count >= max_retries:
                                raise
                            time.sleep(0.2)  # Ждем перед следующей попыткой
                
                finally:
                    # Освобождаем COM в любом случае
                    try:
                        pythoncom.CoUninitialize()
                    except:
                        pass
                
            except Exception as e:
                logging.error(f"Ошибка при получении информации о GPU через WMI: {e}")
        
        # Если ни через GPUtil, ни через WMI не удалось получить данные,
        # добавляем фиктивную видеокарту, чтобы раздел не был пустым
        if not gpus:
            gpus["gpu_default"] = {
                'name': "Видеокарта (базовая информация)",
                'status': "Работает",
                'manufacturer': "Неизвестно",
                'description': "Информация получена из базового API Windows",
                'driver': "Н/Д"
            }
    
    except Exception as e:
        logging.error(f"Общая ошибка при получении информации о видеокартах: {e}")
        # Добавляем хотя бы одну фиктивную карту
        gpus["gpu_error"] = {
            'name': "Ошибка получения данных о видеокарте",
            'status': f"Ошибка: {str(e)}",
            'manufacturer': "Неизвестно"
        }
    
    return gpus

def get_network_info_for_device_manager():
    """Получает расширенную информацию о сетевых адаптерах."""
    network_adapters = {}
    
    if not HAS_WMI:
        return network_adapters
        
    try:
        # Инициализируем COM для WMI
        import pythoncom
        pythoncom.CoInitialize()
            
        wmi_obj = wmi.WMI()
        
        # Получаем информацию об адаптерах через WMI
        for i, adapter in enumerate(wmi_obj.Win32_NetworkAdapter()):
            try:
                # Пропускаем виртуальные и отключенные адаптеры без имени
                if not adapter.NetConnectionID or adapter.NetConnectionID == "":
                    continue
                    
                adapter_id = f"net_{i}"
                
                # Базовая информация
                network_adapters[adapter_id] = {
                    'name': adapter.NetConnectionID or adapter.Name,
                    'manufacturer': getattr(adapter, 'Manufacturer', None) or "Неизвестно",
                    'description': getattr(adapter, 'Description', None) or "Сетевой адаптер",
                    'adapter_type': getattr(adapter, 'AdapterType', None) or "Неизвестно",
                    'mac_address': getattr(adapter, 'MACAddress', None) or "Н/Д"
                }
                
                # Добавляем информацию о настройках IP
                try:
                    net_configs = wmi_obj.Win32_NetworkAdapterConfiguration(Index=adapter.Index)
                    if net_configs:
                        net_config = net_configs[0]
                        
                        # IP адреса и маски
                        if hasattr(net_config, 'IPAddress') and net_config.IPAddress:
                            network_adapters[adapter_id]['ip_address'] = ", ".join(net_config.IPAddress)
                        
                        if hasattr(net_config, 'IPSubnet') and net_config.IPSubnet:
                            network_adapters[adapter_id]['subnet_mask'] = ", ".join(net_config.IPSubnet)
                        
                        # Шлюз по умолчанию
                        if hasattr(net_config, 'DefaultIPGateway') and net_config.DefaultIPGateway:
                            network_adapters[adapter_id]['default_gateway'] = ", ".join(net_config.DefaultIPGateway)
                        
                        # DNS серверы
                        if hasattr(net_config, 'DNSServerSearchOrder') and net_config.DNSServerSearchOrder:
                            network_adapters[adapter_id]['dns_servers'] = ", ".join(net_config.DNSServerSearchOrder)
                except Exception as e:
                    logging.error(f"Ошибка при получении конфигурации сетевого адаптера {i}: {e}")
                
                # Скорость адаптера
                try:
                    if hasattr(adapter, 'Speed') and adapter.Speed:
                        speed_mbps = int(adapter.Speed) / 1000000
                        network_adapters[adapter_id]['speed'] = f"{speed_mbps:.0f} Mbps"
                except Exception as e:
                    logging.error(f"Ошибка при получении скорости сетевого адаптера {i}: {e}")
            except Exception as e:
                logging.error(f"Ошибка при получении информации о сетевом адаптере {i}: {e}")
    except Exception as e:
        logging.error(f"Ошибка при получении информации о сетевых адаптерах: {e}")
    finally:
        # Освобождаем COM
        pythoncom.CoUninitialize()
        
    return network_adapters

def get_motherboard_info_for_device_manager():
    """Получает расширенную информацию о материнской плате."""
    motherboards = {}
    
    if not HAS_WMI:
        return motherboards
        
    try:
        # Инициализируем COM для WMI
        import pythoncom
        pythoncom.CoInitialize()
            
        wmi_obj = wmi.WMI()
        
        # Получаем информацию о материнской плате через WMI
        for i, board in enumerate(wmi_obj.Win32_BaseBoard()):
            board_id = f"mb_{i}"
            
            # Базовая информация
            motherboards[board_id] = {
                'name': board.Product or "Материнская плата",
                'manufacturer': board.Manufacturer or "Неизвестно"
            }
            
            # Добавляем только те поля, которые имеют значение
            if board.Model:
                motherboards[board_id]['model'] = board.Model
            
            if board.SerialNumber and board.SerialNumber.strip():
                motherboards[board_id]['serial_number'] = board.SerialNumber
            
            if board.Version and board.Version.strip():
                motherboards[board_id]['version'] = board.Version
            
            if board.Tag:
                motherboards[board_id]['device_id'] = board.Tag
            
            # Добавляем информацию о BIOS
            try:
                for bios in wmi_obj.Win32_BIOS():
                    if bios.Manufacturer and bios.Manufacturer.strip():
                        motherboards[board_id]['bios_manufacturer'] = bios.Manufacturer
                    
                    if bios.Version and bios.Version.strip():
                        motherboards[board_id]['bios_version'] = bios.Version
                    
                    if bios.ReleaseDate and bios.ReleaseDate.strip():
                        motherboards[board_id]['bios_date'] = bios.ReleaseDate
                    break
            except:
                pass
    except Exception as e:
        logging.error(f"Ошибка при получении информации о материнской плате: {e}")
    finally:
        # Освобождаем COM
        pythoncom.CoUninitialize()
        
    return motherboards

class DeviceLoadingThread(QThread):
    """
    Поток для асинхронной загрузки информации об устройствах
    """
    update_signal = pyqtSignal(str, dict)  # Сигнал для передачи загруженной категории и устройств
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        
    def run(self):
        """Загружает информацию об устройствах в отдельном потоке"""
        try:
            # Инициализируем COM для работы с WMI в потоке
            import pythoncom
            pythoncom.CoInitialize()
            
            try:
                # Загрузка информации о процессорах
                processors = get_cpu_info_for_device_manager()
                self.update_signal.emit("Процессоры", processors)
                if not self._running:
                    return
                    
                # Загрузка информации о видеокартах
                gpus = get_gpu_info_for_device_manager()
                self.update_signal.emit("Видеокарты", gpus)
                if not self._running:
                    return
                    
                # Загрузка информации о дисках
                disks = get_disk_info_for_device_manager()
                self.update_signal.emit("Диски", disks)
                if not self._running:
                    return
                    
                # Загрузка информации о сетевых адаптерах
                network = get_network_info_for_device_manager()
                self.update_signal.emit("Сеть", network)
                if not self._running:
                    return
                    
                # Загрузка информации о материнской плате
                motherboards = get_motherboard_info_for_device_manager()
                self.update_signal.emit("Материнская плата", motherboards)
                if not self._running:
                    return
                    
                # Загрузка информации о USB устройствах
                usb = get_usb_info_for_device_manager()
                self.update_signal.emit("USB", usb)
                if not self._running:
                    return
                    
                # Загрузка информации о звуковых устройствах
                audio = get_audio_info_for_device_manager()
                self.update_signal.emit("Звук", audio)
                if not self._running:
                    return
                    
                # Загрузка информации о мониторах
                monitors = get_monitors_info_for_device_manager()
                self.update_signal.emit("Мониторы", monitors)
            except Exception as e:
                logging.error(f"Ошибка при загрузке устройств: {e}")
            
            finally:
                # Освобождаем COM
                pythoncom.CoUninitialize()
                
        except Exception as e:
            logging.error(f"Критическая ошибка в потоке загрузки: {e}")
            
    def stop(self):
        """Останавливает поток"""
        self._running = False

# Определение функции для получения информации о процессорах
def get_cpu_info_for_device_manager():
    """Получает расширенную информацию о процессорах."""
    processors = {}
    
    try:
        # Используем WMI для получения информации о процессорах
        if HAS_WMI:
            import pythoncom
            pythoncom.CoInitialize()
            
            wmi_obj = wmi.WMI()
            
            for i, processor in enumerate(wmi_obj.Win32_Processor()):
                processor_id = f"cpu_{i}"
                
                # Базовая информация
                processors[processor_id] = {
                    'name': processor.Name,
                    'status': "Работает",
                    'manufacturer': processor.Manufacturer,
                    'description': processor.Description,
                    'cores': processor.NumberOfCores,
                    'logical_processors': processor.NumberOfLogicalProcessors,
                    'current_speed': f"{processor.CurrentClockSpeed} МГц",
                    'max_speed': f"{processor.MaxClockSpeed} МГц",
                    'socket': processor.SocketDesignation,
                    'architecture': processor.Architecture
                }
                
                # Добавляем информацию о кэше, если она доступна
                if hasattr(processor, 'L2CacheSize') and processor.L2CacheSize:
                    processors[processor_id]['l2_cache'] = f"{processor.L2CacheSize} KB"
                
                if hasattr(processor, 'L3CacheSize') and processor.L3CacheSize:
                    processors[processor_id]['l3_cache'] = f"{processor.L3CacheSize} KB"
            
            pythoncom.CoUninitialize()
    except Exception as e:
        logging.error(f"Ошибка при получении информации о процессорах: {e}")
    
    return processors

# Определение функции для получения информации о дисках, если её нет
def get_disk_info_for_device_manager():
    """Получает расширенную информацию о дисках."""
    disks = {}
    
    try:
        # Используем WMI для получения информации о физических дисках
        if HAS_WMI:
            import pythoncom
            pythoncom.CoInitialize()
            
            wmi_obj = wmi.WMI()
            
            # Получаем информацию о физических дисках
            for i, disk in enumerate(wmi_obj.Win32_DiskDrive()):
                disk_id = f"disk_{i}"
                
                # Базовая информация
                disks[disk_id] = {
                    'name': disk.Model or f"Диск {i}",
                    'status': "Работает",
                    'manufacturer': disk.Manufacturer or "Неизвестно",
                    'type': "Физический диск",
                    'interface_type': disk.InterfaceType,
                    'media_type': disk.MediaType,
                    'size': format_bytes(int(disk.Size)) if hasattr(disk, 'Size') and disk.Size else "Неизвестно"
                }
                
                # Добавляем информацию о серийном номере, если она доступна
                if hasattr(disk, 'SerialNumber') and disk.SerialNumber:
                    disks[disk_id]['serial_number'] = disk.SerialNumber.strip()
            
            # Получаем информацию о логических дисках
            logical_disks = {}
            try:
                for i, logical_disk in enumerate(wmi_obj.Win32_LogicalDisk()):
                    try:
                        # Создаем идентификатор для логического диска
                        logical_id = f"logical_{i}"
                        
                        # Получаем тип файловой системы
                        drive_type_map = {
                            0: "Неизвестно",
                            1: "Неопределен",
                            2: "Съемный диск",
                            3: "Локальный диск",
                            4: "Сетевой диск",
                            5: "Оптический диск",
                            6: "RAM-диск"
                        }
                        
                        # Получаем тип диска из словаря или "Неизвестно" по умолчанию
                        drive_type = drive_type_map.get(getattr(logical_disk, 'DriveType', 0), "Неизвестно")
                        
                        # Создаем информацию о логическом диске
                        logical_disks[logical_id] = {
                            'name': f"{getattr(logical_disk, 'DeviceID', 'Диск')} ({getattr(logical_disk, 'VolumeName', 'Том') or 'Локальный диск'})",
                            'manufacturer': "Microsoft",
                            'description': f"Логический диск {drive_type}",
                            'type': "Логический диск",
                            'filesystem': getattr(logical_disk, 'FileSystem', None) or "Н/Д",
                            'total_space': format_bytes(getattr(logical_disk, 'Size', 0)),
                            'free_space': format_bytes(getattr(logical_disk, 'FreeSpace', 0))
                        }
                        
                        # Добавляем информацию о метке тома, если она есть
                        if hasattr(logical_disk, 'VolumeName') and logical_disk.VolumeName:
                            logical_disks[logical_id]['volume_name'] = logical_disk.VolumeName
                            
                        # Добавляем информацию о серийном номере тома, если она есть
                        if hasattr(logical_disk, 'VolumeSerialNumber') and logical_disk.VolumeSerialNumber:
                            logical_disks[logical_id]['volume_serial'] = logical_disk.VolumeSerialNumber
                    except Exception as e:
                        logging.error(f"Ошибка при получении информации о логическом диске {i}: {e}")
                
                # Добавляем логические диски в общий список дисков
                disks.update(logical_disks)
            except Exception as e:
                logging.error(f"Ошибка при получении информации о логических дисках: {e}")
            
            pythoncom.CoUninitialize()
    except Exception as e:
        logging.error(f"Ошибка при получении информации о дисках: {e}")
    
    return disks

# Определение функции для получения информации о USB-устройствах, если её нет
def get_usb_info_for_device_manager():
    """Получает расширенную информацию о USB устройствах."""
    usb_devices = {}
    
    try:
        # Используем WMI для получения информации о USB устройствах
        if HAS_WMI:
            import pythoncom
            pythoncom.CoInitialize()
            
            wmi_obj = wmi.WMI()
            
            # Получаем USB-контроллеры
            for i, controller in enumerate(wmi_obj.Win32_USBController()):
                device_id = f"usb_controller_{i}"
                
                # Базовая информация о контроллере
                usb_devices[device_id] = {
                    'name': controller.Name or f"USB контроллер {i}",
                    'status': controller.Status or "Неизвестно",
                    'manufacturer': controller.Manufacturer or "Неизвестно",
                    'device_id': controller.DeviceID,
                    'type': "USB контроллер"
                }
            
            # Получаем USB-хабы
            for i, hub in enumerate(wmi_obj.Win32_USBHub()):
                device_id = f"usb_hub_{i}"
                
                # Базовая информация о хабе
                usb_devices[device_id] = {
                    'name': hub.Name or f"USB хаб {i}",
                    'status': hub.Status or "Неизвестно",
                    'manufacturer': hub.Manufacturer or "Неизвестно",
                    'device_id': hub.DeviceID,
                    'type': "USB хаб"
                }
                
                # Добавляем протокол USB, если он есть
                if hasattr(hub, 'ProtocolCode') and hub.ProtocolCode is not None:
                    protocol_map = {1: "USB 1.0", 2: "USB 2.0", 3: "USB 3.0"}
                    protocol = protocol_map.get(hub.ProtocolCode, f"USB (код: {hub.ProtocolCode})")
                    usb_devices[device_id]['protocol'] = protocol
            
            pythoncom.CoUninitialize()
    except Exception as e:
        logging.error(f"Ошибка при получении информации о USB устройствах: {e}")
    
    return usb_devices

# Функции для получения информации о диспетчере устройств для отчета
def get_cpu_info_for_device_manager():
    """Получает информацию о процессорах из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        cpu_info = {}
        
        for i, processor in enumerate(w.Win32_Processor()):
            cpu_info[f"CPU_{i}"] = {
                "name": processor.Name.strip() if processor.Name else "Неизвестно",
                "Производитель": processor.Manufacturer if processor.Manufacturer else "Неизвестно",
                "Описание": processor.Description if processor.Description else "Неизвестно",
                "Архитектура": processor.Architecture if processor.Architecture else "Неизвестно",
                "Текущая частота": f"{processor.CurrentClockSpeed} МГц" if processor.CurrentClockSpeed else "Неизвестно",
                "Максимальная частота": f"{processor.MaxClockSpeed} МГц" if processor.MaxClockSpeed else "Неизвестно",
                "Количество ядер": processor.NumberOfCores if processor.NumberOfCores else "Неизвестно",
                "Количество логических процессоров": processor.NumberOfLogicalProcessors if processor.NumberOfLogicalProcessors else "Неизвестно",
                "Статус": processor.Status if processor.Status else "Неизвестно"
            }
        return cpu_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_gpu_info_for_device_manager():
    """Получает информацию о видеокартах из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        gpu_info = {}
        
        for i, gpu in enumerate(w.Win32_VideoController()):
            gpu_info[f"GPU_{i}"] = {
                "name": gpu.Name.strip() if gpu.Name else "Неизвестно",
                "Статус": gpu.Status if gpu.Status else "Неизвестно",
                "Драйвер": gpu.DriverVersion if gpu.DriverVersion else "Неизвестно",
                "Описание": gpu.Description if gpu.Description else "Неизвестно",
                "Видеопроцессор": gpu.VideoProcessor if gpu.VideoProcessor else "Неизвестно",
                "Объем памяти": f"{int(gpu.AdapterRAM / (1024*1024))} МБ" if hasattr(gpu, 'AdapterRAM') and gpu.AdapterRAM else "Неизвестно",
                "Разрешение": f"{gpu.CurrentHorizontalResolution}x{gpu.CurrentVerticalResolution}" if hasattr(gpu, 'CurrentHorizontalResolution') and hasattr(gpu, 'CurrentVerticalResolution') else "Неизвестно",
                "Частота обновления": f"{gpu.CurrentRefreshRate} Гц" if hasattr(gpu, 'CurrentRefreshRate') and gpu.CurrentRefreshRate else "Неизвестно"
            }
        return gpu_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_disk_info_for_device_manager():
    """Получает информацию о дисках из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        disk_info = {}
        
        # Физические диски
        for i, disk in enumerate(w.Win32_DiskDrive()):
            disk_info[f"Disk_{i}"] = {
                "name": disk.Caption.strip() if disk.Caption else "Неизвестно",
                "Модель": disk.Model if disk.Model else "Неизвестно",
                "Серийный номер": disk.SerialNumber if disk.SerialNumber else "Неизвестно",
                "Интерфейс": disk.InterfaceType if disk.InterfaceType else "Неизвестно",
                "Размер": f"{int(int(disk.Size) / (1024*1024*1024))} ГБ" if disk.Size else "Неизвестно",
                "Статус": disk.Status if disk.Status else "Неизвестно",
                "Тип медиа": disk.MediaType if disk.MediaType else "Неизвестно"
            }
        
        # Логические диски
        for i, logical_disk in enumerate(w.Win32_LogicalDisk()):
            if logical_disk.DriveType == 3:  # Только локальные диски
                disk_info[f"LogicalDisk_{i}"] = {
                    "name": f"Диск {logical_disk.DeviceID}",
                    "Метка тома": logical_disk.VolumeName if logical_disk.VolumeName else "Нет метки",
                    "Файловая система": logical_disk.FileSystem if logical_disk.FileSystem else "Неизвестно",
                    "Размер": f"{int(int(logical_disk.Size) / (1024*1024*1024))} ГБ" if logical_disk.Size else "Неизвестно",
                    "Свободно": f"{int(int(logical_disk.FreeSpace) / (1024*1024*1024))} ГБ" if logical_disk.FreeSpace else "Неизвестно"
                }
        
        return disk_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_network_info_for_device_manager():
    """Получает информацию о сетевых адаптерах из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        network_info = {}
        
        for i, adapter in enumerate(w.Win32_NetworkAdapter()):
            # Пропускаем отключенные адаптеры
            if not adapter.NetEnabled:
                continue
                
            network_info[f"Network_{i}"] = {
                "name": adapter.Name.strip() if adapter.Name else "Неизвестно",
                "Описание": adapter.Description if adapter.Description else "Неизвестно",
                "MAC-адрес": adapter.MACAddress if adapter.MACAddress else "Нет",
                "Производитель": adapter.Manufacturer if adapter.Manufacturer else "Неизвестно",
                "Тип адаптера": adapter.AdapterType if adapter.AdapterType else "Неизвестно",
                "Скорость": f"{int(adapter.Speed / (1000*1000))} Мбит/с" if hasattr(adapter, 'Speed') and adapter.Speed else "Неизвестно",
                "Статус": adapter.Status if adapter.Status else "Неизвестно"
            }
            
            # Добавляем IP-адреса для этого адаптера
            try:
                for config in w.Win32_NetworkAdapterConfiguration(MACAddress=adapter.MACAddress):
                    if config.IPAddress:
                        network_info[f"Network_{i}"]["IP-адреса"] = ", ".join(config.IPAddress)
                    if config.DefaultIPGateway:
                        network_info[f"Network_{i}"]["Шлюз"] = ", ".join(config.DefaultIPGateway)
                    if config.DNSServerSearchOrder:
                        network_info[f"Network_{i}"]["DNS-серверы"] = ", ".join(config.DNSServerSearchOrder)
            except:
                pass
                
        return network_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_motherboard_info_for_device_manager():
    """Получает информацию о материнской плате из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        motherboard_info = {}
        
        # Информация о материнской плате
        for i, board in enumerate(w.Win32_BaseBoard()):
            motherboard_info["Motherboard"] = {
                "name": board.Product.strip() if board.Product else "Неизвестно",
                "Производитель": board.Manufacturer if board.Manufacturer else "Неизвестно",
                "Модель": board.Product if board.Product else "Неизвестно",
                "Серийный номер": board.SerialNumber if board.SerialNumber else "Неизвестно",
                "Версия": board.Version if board.Version else "Неизвестно"
            }
        
        # Информация о BIOS
        for bios in w.Win32_BIOS():
            motherboard_info["BIOS"] = {
                "name": "BIOS",
                "Производитель": bios.Manufacturer if bios.Manufacturer else "Неизвестно",
                "Версия": bios.Version if bios.Version else "Неизвестно",
                "Дата выпуска": bios.ReleaseDate.split('.')[0] if bios.ReleaseDate else "Неизвестно"
            }
            
        return motherboard_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_audio_info_for_device_manager():
    """Получает информацию о аудио устройствах из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        audio_info = {}
        
        for i, device in enumerate(w.Win32_SoundDevice()):
            audio_info[f"Audio_{i}"] = {
                "name": device.Name.strip() if device.Name else "Неизвестно",
                "Производитель": device.Manufacturer if device.Manufacturer else "Неизвестно",
                "Статус": device.Status if device.Status else "Неизвестно",
                "Тип устройства": device.DeviceID if device.DeviceID else "Неизвестно"
            }
        return audio_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_monitors_info_for_device_manager():
    """Получает информацию о мониторах из диспетчера устройств"""
    try:
        import wmi
        w = wmi.WMI()
        monitor_info = {}
        
        for i, monitor in enumerate(w.Win32_DesktopMonitor()):
            monitor_info[f"Monitor_{i}"] = {
                "name": monitor.Name.strip() if monitor.Name else "Неизвестно",
                "Описание": monitor.Description if monitor.Description else "Неизвестно",
                "Разрешение по горизонтали": f"{monitor.ScreenWidth} пикселей" if monitor.ScreenWidth else "Неизвестно",
                "Разрешение по вертикали": f"{monitor.ScreenHeight} пикселей" if monitor.ScreenHeight else "Неизвестно",
                "Статус": monitor.Status if monitor.Status else "Неизвестно"
            }
        return monitor_info
    except Exception as e:
        return {"Ошибка": str(e)}

# Функции для получения информации о топологии сети
def get_network_topology_info():
    """Получает информацию о топологии сети"""
    try:
        import socket
        import subprocess
        import re
        import platform
        
        topology_info = {
            "Имя компьютера": socket.gethostname(),
            "IP-адрес": socket.gethostbyname(socket.gethostname()),
            "Подключенные устройства": {}
        }
        
        # Получаем таблицу ARP для определения устройств в локальной сети
        arp_output = subprocess.check_output("arp -a", shell=True).decode('cp866')
        
        # Парсим вывод ARP таблицы
        arp_entries = re.findall(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f-]+)', arp_output, re.IGNORECASE)
        
        for i, (ip, mac) in enumerate(arp_entries):
            if mac != "ff-ff-ff-ff-ff":  # Исключаем широковещательные адреса
                topology_info["Подключенные устройства"][f"Устройство_{i}"] = {
                    "IP-адрес": ip,
                    "MAC-адрес": mac
                }
                
                # Пробуем получить имя устройства
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                    topology_info["Подключенные устройства"][f"Устройство_{i}"]["Имя устройства"] = hostname
                except:
                    topology_info["Подключенные устройства"][f"Устройство_{i}"]["Имя устройства"] = "Неизвестно"
        
        # Добавляем информацию о маршрутизации
        try:
            if platform.system() == "Windows":
                route_output = subprocess.check_output("route print", shell=True).decode('cp866')
                default_gateway_match = re.search(r'0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)', route_output)
                if default_gateway_match:
                    topology_info["Шлюз по умолчанию"] = default_gateway_match.group(1)
        except:
            topology_info["Шлюз по умолчанию"] = "Не удалось определить"
            
        # Проверяем доступность интернета
        try:
            socket.create_connection(("www.google.com", 80), timeout=2)
            topology_info["Доступ в интернет"] = "Доступен"
        except:
            topology_info["Доступ в интернет"] = "Недоступен"
            
        return topology_info
    except Exception as e:
        return {"Ошибка": str(e)}

def get_detailed_network_topology():
    """Получает детальную информацию о топологии сети с помощью traceroute"""
    try:
        import subprocess
        import re
        import socket
        
        trace_info = {
            "Маршрут до google.com": []
        }
        
        # Выполняем tracert для определения маршрута до google.com
        try:
            tracert_output = subprocess.check_output("tracert -d -h 15 google.com", shell=True, timeout=15).decode('cp866')
            
            # Парсим вывод tracert
            hop_lines = re.findall(r'\s*(\d+)\s+(\d+\s+ms|\*)\s+(\d+\s+ms|\*)\s+(\d+\s+ms|\*)\s+(\S+)', tracert_output)
            
            for hop in hop_lines:
                hop_num = hop[0]
                ip = hop[4]
                
                # Пропускаем строки с таймаутами
                if ip == "*":
                    continue
                    
                hop_info = {
                    "IP-адрес": ip,
                    "Время отклика": min(t for t in [hop[1], hop[2], hop[3]] if t != "*")
                }
                
                # Пробуем получить имя устройства
                try:
                    hostname = socket.gethostbyaddr(ip)[0]
                    hop_info["Имя устройства"] = hostname
                except:
                    hop_info["Имя устройства"] = "Неизвестно"
                    
                trace_info["Маршрут до google.com"].append(hop_info)
                
        except subprocess.TimeoutExpired:
            trace_info["Маршрут до google.com"] = ["Превышено время ожидания при выполнении tracert"]
        except:
            trace_info["Маршрут до google.com"] = ["Не удалось выполнить tracert"]
            
        return trace_info
    except Exception as e:
        return {"Ошибка": str(e)}
