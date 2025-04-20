import psutil
import socket
import subprocess
import re
import platform
import time
import ipaddress
import math  # Добавляем импорт модуля math
import threading  # Добавляем импорт модуля threading
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLabel, 
                           QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
                           QPushButton, QComboBox, QSplitter, QApplication,
                           QProgressBar, QToolButton, QMenu, QAction, QGridLayout,
                           QToolTip, QCheckBox, QLineEdit)  # Добавляем QCheckBox и QLineEdit
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QRectF, QPointF, QRect, QSize, QEvent
from PyQt5.QtGui import (QPainter, QColor, QPen, QBrush, QFont, QPixmap, QPainterPath, 
                       QPolygonF, QLinearGradient, QRadialGradient, QIcon)  # Добавляем QIcon
import logging
import concurrent.futures


# Добавляем новый класс AnimatedProgressBar
class AnimatedProgressBar(QWidget):
    """
    Кастомный анимированный индикатор прогресса в виде бегущей полоски
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20)
        self.setMinimumWidth(200)
        
        # Настройки анимации
        self.position = 0
        self.direction = 1  # 1 - вправо, -1 - влево
        self.bar_width = 100  # Ширина бегущей полоски
        self.animation_step = 5  # Шаг смещения за одну итерацию
        self.visible = False
        self.is_completed = False
        
        # Цвета
        self.background_color = QColor(245, 248, 255)
        self.border_color = QColor(208, 224, 255)
        self.bar_color = QColor(58, 123, 213)
        
        # Таймер для анимации
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        
    def setVisible(self, visible):
        self.visible = visible
        if visible and not self.is_completed:
            self.timer.start(30)  # Запускаем анимацию при показе
        else:
            self.timer.stop()
        super().setVisible(visible)
    
    def update_animation(self):
        """Обновляет позицию бегущей полоски"""
        if not self.visible or self.is_completed:
            return
            
        # Обновляем позицию полоски
        self.position += self.animation_step * self.direction
        
        # Меняем направление, если достигли края
        if self.position >= self.width() - self.bar_width:
            self.direction = -1
        elif self.position <= 0:
            self.direction = 1
            
        # Обновляем отрисовку
        self.update()
    
    def paintEvent(self, event):
        if not self.visible:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Рисуем фон
        painter.setPen(QPen(self.border_color, 1))
        painter.setBrush(QBrush(self.background_color))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        
        if self.is_completed:
            # Если сканирование завершено, показываем полностью заполненный индикатор
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.bar_color))
            painter.drawRoundedRect(0, 0, self.width(), self.height(), 4, 4)
        else:
            # Рисуем бегущую полоску
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self.bar_color))
            painter.drawRoundedRect(self.position, 0, self.bar_width, self.height(), 4, 4)
    
    def setCompleted(self, completed=True):
        """Устанавливает состояние завершения"""
        self.is_completed = completed
        if completed:
            self.timer.stop()
        self.update()
    
    def reset(self):
        """Сбрасывает состояние прогресс-бара в исходное"""
        self.is_completed = False
        self.position = 0
        self.direction = 1
        # Запускаем таймер анимации, если виджет видимый
        if self.visible:
            self.timer.start(30)
        self.update()


class NetworkMonitor:
    """
    Класс для мониторинга сетевых интерфейсов и трафика
    """
    def __init__(self):
        """
        Инициализация монитора сети
        """
        # Информация о локальной сети
        self.local_ip = "Не определен"
        self.gateway = "Не определен"
        self.discovered_devices = {}
        
        self.interfaces = self.get_network_interfaces()
        # История трафика для плавности графиков
        self.traffic_history = {}
    
    def get_network_interfaces(self):
        """
        Получение информации о сетевых интерфейсах с фильтрацией виртуальных адаптеров
        """
        interfaces = {}
        net_if_stats = psutil.net_if_stats()
        net_if_addrs = psutil.net_if_addrs()
        
        # Возможные префиксы названий виртуальных интерфейсов
        vmware_patterns = [
            'vmware', 'vm ', 'virtual', 'vmnet', 'vethernet', 'vnet', 
            'vboxnet', 'virtualbox'
        ]
        
        for interface_name, stats in net_if_stats.items():
            # Проверяем, не является ли интерфейс виртуальным адаптером VMware
            is_vmware_interface = False
            interface_name_lower = interface_name.lower()
            
            for pattern in vmware_patterns:
                if pattern in interface_name_lower:
                    is_vmware_interface = True
                    break
            
            # Пропускаем виртуальные интерфейсы
            if is_vmware_interface:
                continue
                
            # Получаем адреса для интерфейса
            if interface_name in net_if_addrs:
                addrs = net_if_addrs[interface_name]
                ipv4_addresses = []
                mac_address = None
                netmask = None
                
                # Ищем IPv4 и MAC адреса
                for addr in addrs:
                    if addr.family == socket.AF_INET:
                        ipv4_addresses.append({
                            "address": addr.address,
                            "netmask": addr.netmask
                        })
                    elif addr.family == psutil.AF_LINK:
                        mac_address = addr.address
                
                # Добавляем только если есть хотя бы один IPv4 адрес
                if ipv4_addresses:
                    interfaces[interface_name] = {
                        "IP": [ip["address"] for ip in ipv4_addresses],
                        "Маска сети": [ip["netmask"] for ip in ipv4_addresses],
                        "MAC": mac_address if mac_address else "N/A",
                        "Активен": stats.isup,
                        "MTU": stats.mtu,
                        "Скорость": f"{stats.speed} Mbit/s" if stats.speed > 0 else "N/A"
                    }
        
        return interfaces
    
    def get_network_stats(self):
        """
        Получение статистики по сетевым интерфейсам
        """
        stats = {}
        io_counters = psutil.net_io_counters(pernic=True)
        
        for interface, io_counter in io_counters.items():
            if interface in self.interfaces:
                stats[interface] = {
                    "Отправлено (МБ)": round(io_counter.bytes_sent / (1024**2), 2),
                    "Получено (МБ)": round(io_counter.bytes_recv / (1024**2), 2),
                    "Отправлено пакетов": io_counter.packets_sent,
                    "Получено пакетов": io_counter.packets_recv,
                    "Ошибки входящие": io_counter.errin,
                    "Ошибки исходящие": io_counter.errout,
                    "Dropped входящие": io_counter.dropin,
                    "Dropped исходящие": io_counter.dropout
                }
        
        return stats
    
    def get_arp_table(self):
        """
        Получение ARP таблицы с улучшенной фильтрацией и классификацией устройств
        """
        arp_table = []
        
        def determine_device_type(ip, mac, is_static=False):
            """Определяет тип устройства для ARP таблицы"""
            # По умолчанию все записи считаются динамическими
            device_type = "динамический"
            
            # Если запись явно указана как статическая или
            # если это специальный IP-адрес или MAC-адрес, то это статическая запись
            if is_static or self.is_special_ip(ip) or self.is_special_mac(mac):
                device_type = "статический"
                
            # Проверяем, является ли IP-адрес мультикастовым или широковещательным
            octets = list(map(int, ip.split('.')))
            if 224 <= octets[0] <= 239 or octets[0] == 255:
                device_type = "статический"
            
            # Проверяем мультикастовый MAC-адрес (начинается с 01:00:5e)
            mac_lower = mac.lower().replace('-', ':')
            if mac_lower.startswith('01:00:5e') or mac_lower == 'ff:ff:ff:ff:ff:ff':
                device_type = "статический"
                
            return device_type
        
        try:
            if hasattr(psutil, 'WINDOWS') and psutil.WINDOWS:
                # Windows-специфичный код
                arp_output = subprocess.check_output("arp -a", shell=True).decode('cp1251', errors='ignore')
                lines = arp_output.split('\n')
                current_interface = None
                
                for line in lines:
                    if "Интерфейс" in line or "Interface" in line:
                        interface_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                        if interface_match:
                            current_interface = interface_match.group(1)
                    elif re.match(r'\s+\d+\.\d+\.\d+\.\d+', line):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1].replace('-', ':')
                            
                            # Определяем тип записи
                            is_static = False
                            if len(parts) > 2:
                                type_code = parts[2].lower()
                                is_static = "стат" in type_code or "stat" in type_code
                            
                            device_type = determine_device_type(ip, mac, is_static)
                            
                            arp_table.append({
                                "IP": ip,
                                "MAC": mac,
                                "Тип": device_type,
                                "Интерфейс": current_interface if current_interface else "Не определен"
                            })
            else:
                # Linux/Unix-специфичный код
                arp_output = subprocess.check_output("arp -n", shell=True).decode('utf-8')
                lines = arp_output.split('\n')
                
                for line in lines[1:]:  # Пропускаем заголовок
                    parts = line.split()
                    if len(parts) >= 3:
                        ip = parts[0]
                        mac = parts[2]
                        
                        # Определяем тип записи
                        is_static = len(parts) > 3 and parts[3].lower() == "static"
                        device_type = determine_device_type(ip, mac, is_static)
                        
                        arp_table.append({
                            "IP": ip,
                            "MAC": mac,
                            "Тип": device_type,
                            "Интерфейс": parts[5] if len(parts) > 5 else "Не определен"
                        })
        except Exception as e:
            # print(f"Ошибка при получении ARP таблицы: {e}")  # Удаляем вывод в терминал
            pass
        
        return arp_table
    
    def get_gateway_info(self):
        """
        Получение информации о шлюзе с улучшенным алгоритмом выбора
        """
        try:
            # Получаем все шлюзы, отсортированные по приоритету
            all_gateways = self.get_all_gateways()
            
            if not all_gateways:
                return None
            
            # Берем шлюз с наивысшим приоритетом
            primary_gateway = all_gateways[0]
            gateway_ip = primary_gateway["gateway"]
            
            # Пингуем шлюз для обновления ARP-записи
            try:
                subprocess.call(f"ping -n 1 {gateway_ip}", shell=True, 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
                
            # Получаем MAC-адрес шлюза из ARP-таблицы
            arp_table = self.get_arp_table()
            for entry in arp_table:
                if entry["IP"] == gateway_ip:
                    # Определяем производителя по MAC
                    vendor = self._get_mac_vendor(entry["MAC"])
                    
                    # Определяем тип устройства с помощью улучшенного метода
                    device_type = self._determine_device_type(gateway_ip, entry["MAC"], True)
                    
                    return {
                        "IP": gateway_ip,
                        "MAC": entry["MAC"],
                        "Интерфейс": entry["Интерфейс"] if "Интерфейс" in entry else primary_gateway["name"],
                        "Производитель": vendor if vendor else "Неизвестно",
                        "Тип": device_type,
                        "Виртуальный": primary_gateway["is_virtual"]
                    }
                    
            # Если MAC-адрес не найден в ARP-таблице, возвращаем информацию без MAC
            return {
                "IP": gateway_ip,
                "MAC": "Не определен",
                "Интерфейс": primary_gateway["name"],
                "Производитель": "Неизвестно",
                "Тип": "Маршрутизатор",  # Значение по умолчанию, если не удалось определить MAC
                "Виртуальный": primary_gateway["is_virtual"]
            }
        except Exception as e:
            logging.error(f"Ошибка при получении информации о шлюзе: {str(e)}")
        
        return None

    def _get_mac_vendor(self, mac):
        """
        Определяет производителя по MAC-адресу
        """
        if not mac or mac == "Не определен":
            return None
        
        # Преобразуем MAC в стандартный формат без разделителей
        mac = mac.replace('-', '').replace(':', '').replace('.', '').upper()
        if len(mac) < 6:
            return None
        
        # Берем первые 6 символов (OUI - Organizationally Unique Identifier)
        oui = mac[0:6]
        
        # Базовый список известных производителей сетевого оборудования
        vendors = {
            # Cisco
            "00000C": "Cisco", "000142": "Cisco", "000143": "Cisco", "000163": "Cisco", 
            "000164": "Cisco", "000196": "Cisco", "000197": "Cisco", "0001C7": "Cisco",
            "0001C9": "Cisco", "000216": "Cisco", "000217": "Cisco", "00022D": "Cisco",
            "000F8F": "Cisco", "001007": "Cisco", "001111": "Cisco", "0016C7": "Cisco",
            "001A2F": "Cisco", "001C7E": "Cisco", "001DA1": "Cisco", "001EBD": "Cisco",
            "001F6C": "Cisco", "00223A": "Cisco", "002413": "Cisco", "002584": "Cisco",
            # TP-Link
            "000AEB": "TP-Link", "001018": "TP-Link", "0019E0": "TP-Link", "001D0F": "TP-Link",
            "002127": "TP-Link", "5C63BF": "TP-Link", "645601": "TP-Link", "78C3E9": "TP-Link",
            "8CFABA": "TP-Link", "94D9B3": "TP-Link", "A0F3C1": "TP-Link", "C4E984": "TP-Link",
            "D8150D": "TP-Link", "EC172F": "TP-Link", "EC888F": "TP-Link", "F4EC38": "TP-Link",
            # D-Link
            "00055D": "D-Link", "000D88": "D-Link", "000F3D": "D-Link", "001195": "D-Link",
            "0015E9": "D-Link", "00179A": "D-Link", "0019D1": "D-Link", "001B11": "D-Link",
            "001CF0": "D-Link", "001E58": "D-Link", "002191": "D-Link", "0022B0": "D-Link",
            "14D64D": "D-Link", "1C7EE5": "D-Link", "28107B": "D-Link", "3CBDD8": "D-Link",
            # Huawei
            "00259E": "Huawei", "001882": "Huawei", "00464B": "Huawei", "0C2C54": "Huawei",
            "105172": "Huawei", "283152": "Huawei", "2CAB00": "Huawei", "3CDFBD": "Huawei",
            "48AD08": "Huawei", "4C5499": "Huawei", "4CB16C": "Huawei", "547595": "Huawei",
            "585F5A": "Huawei", "5CB395": "Huawei", "70725C": "Huawei", "78D752": "Huawei",
            # ASUS
            "001BFC": "ASUS", "001E8C": "ASUS", "002354": "ASUS", "00248C": "ASUS",
            "0026ED": "ASUS", "00E018": "ASUS", "08606E": "ASUS", "107B44": "ASUS",
            "149EDC": "ASUS", "1C872C": "ASUS", "305A3A": "ASUS", "38D547": "ASUS",
            "485B39": "ASUS", "50465D": "ASUS", "54A050": "ASUS", "60A44C": "ASUS",
            # Netgear
            "00095B": "Netgear", "000FB5": "Netgear", "00146C": "Netgear", "001882": "Netgear",
            "001E2A": "Netgear", "00224E": "Netgear", "002611": "Netgear", "008EF2": "Netgear",
            "04A151": "Netgear", "08028E": "Netgear", "0826B9": "Netgear", "0C5415": "Netgear",
            "100C6B": "Netgear", "10DA43": "Netgear", "205D47": "Netgear", "28C68E": "Netgear",
            # Mikrotik
            "001107": "MikroTik", "001149": "MikroTik", "00126E": "MikroTik", "001313": "MikroTik",
            "0014D1": "MikroTik", "0015D5": "MikroTik", "0016C9": "MikroTik", "0017D1": "MikroTik",
            "0021A5": "MikroTik", "002326": "MikroTik", "002401": "MikroTik", "0025B3": "MikroTik",
            "002700": "MikroTik", "002728": "MikroTik", "00273F": "MikroTik", "002755": "MikroTik",
            # ZyXEL
            "001349": "ZyXEL", "00617C": "ZyXEL", "009C02": "ZyXEL", "105F06": "ZyXEL",
            "18E225": "ZyXEL", "2C6BF5": "ZyXEL", "40B620": "ZyXEL", "547975": "ZyXEL",
            "58863B": "ZyXEL", "5CA39D": "ZyXEL", "94638C": "ZyXEL", "A0E4CB": "ZyXEL",
            "B0B20F": "ZyXEL", "B4C6F8": "ZyXEL", "BCEC23": "ZyXEL", "CC5D4E": "ZyXEL"
        }
        
        if oui in vendors:
            return vendors[oui]
        
        return None
    
    def get_disk_io(self):
        """
        Получение статистики ввода-вывода дисков
        """
        current_time = time.time()
        current_disk_io = psutil.disk_io_counters(perdisk=True)
        result = {}
        
        if self.prev_disk_io is not None:
            time_delta = current_time - self.prev_disk_time
            
            for disk, counters in current_disk_io.items():
                if disk in self.prev_disk_io:
                    prev_counters = self.prev_disk_io[disk]
                    
                    # Рассчитываем скорость в МБ/с
                    read_speed = (counters.read_bytes - prev_counters.read_bytes) / (time_delta * 1024 * 1024)
                    write_speed = (counters.write_bytes - prev_counters.write_bytes) / (time_delta * 1024 * 1024)
                    
                    # Рассчитываем IOPS (операций в секунду)
                    read_iops = (counters.read_count - prev_counters.read_count) / time_delta
                    write_iops = (counters.write_count - prev_counters.write_count) / time_delta
                    
                    result[disk] = {
                        "Чтение (МБ/с)": round(read_speed, 2),
                        "Запись (МБ/с)": round(write_speed, 2),
                        "Чтение (IOPS)": round(read_iops, 2),
                        "Запись (IOPS)": round(write_iops, 2),
                        "Всего прочитано (ГБ)": round(counters.read_bytes / (1024**3), 2),
                        "Всего записано (ГБ)": round(counters.write_bytes / (1024**3), 2),
                        "Время чтения (мс)": counters.read_time if hasattr(counters, 'read_time') else 0,
                        "Время записи (мс)": counters.write_time if hasattr(counters, 'write_time') else 0,
                    }
        
        # Сохраняем текущие значения для следующего вызова
        self.prev_disk_io = current_disk_io
        self.prev_disk_time = current_time
        
        return result
    
    def get_detailed_net_stats(self):
        """
        Получение детальной сетевой статистики с расчетом скорости
        """
        current_time = time.time()
        current_net_io = psutil.net_io_counters(pernic=True)
        result = {}
        
        if self.prev_net_io is not None:
            time_delta = current_time - self.prev_net_time
            
            for interface, counters in current_net_io.items():
                if interface in self.prev_net_io:
                    prev_counters = self.prev_net_io[interface]
                    
                    # Рассчитываем скорость в Мбит/с (1 Байт = 8 бит)
                    recv_speed = (counters.bytes_recv - prev_counters.bytes_recv) * 8 / (time_delta * 1024 * 1024)
                    sent_speed = (counters.bytes_sent - prev_counters.bytes_sent) * 8 / (time_delta * 1024 * 1024)
                    
                    # Рассчитываем пакеты в секунду
                    recv_pps = (counters.packets_recv - prev_counters.packets_recv) / time_delta
                    sent_pps = (counters.packets_sent - prev_counters.packets_sent) / time_delta
                    
                    result[interface] = {
                        "Входящая скорость (Мбит/с)": round(recv_speed, 2),
                        "Исходящая скорость (Мбит/с)": round(sent_speed, 2),
                        "Входящие пакеты/с": round(recv_pps, 2),
                        "Исходящие пакеты/с": round(sent_pps, 2),
                        "Всего получено (МБ)": round(counters.bytes_recv / (1024*1024), 2),
                        "Всего отправлено (МБ)": round(counters.bytes_sent / (1024*1024), 2),
                        "Ошибок входящих": counters.errin,
                        "Ошибок исходящих": counters.errout,
                        "Пакетов отброшено (вх)": counters.dropin,
                        "Пакетов отброшено (исх)": counters.dropout
                    }
        
        # Сохраняем текущие значения для следующего вызова
        self.prev_net_io = current_net_io
        self.prev_net_time = current_time
        
        return result
    
    def get_top_processes(self, limit=10):
        """
        Получение списка наиболее ресурсоемких процессов
        """
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'create_time']):
            try:
                # Получаем информацию о процессе
                proc_info = proc.info
                
                # Добавляем дополнительную информацию
                proc_info['memory_mb'] = round(proc.memory_info().rss / (1024 * 1024), 2)
                
                # Пытаемся получить количество потоков и дескрипторов
                try:
                    proc_info['threads'] = proc.num_threads()
                except:
                    proc_info['threads'] = 0
                
                try:
                    proc_info['connections'] = len(proc.connections())
                except:
                    proc_info['connections'] = 0
                
                # Добавляем информацию о времени работы
                try:
                    proc_info['runtime'] = time.time() - proc_info['create_time']
                    hours, remainder = divmod(proc_info['runtime'], 3600)
                    minutes, seconds = divmod(remainder, 60)
                    proc_info['runtime_str'] = f"{int(hours)}ч {int(minutes)}м {int(seconds)}с"
                except:
                    proc_info['runtime_str'] = "Н/Д"
                
                processes.append(proc_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Сортируем по загрузке CPU (можно изменить на другой параметр)
        processes.sort(key=lambda p: p['cpu_percent'], reverse=True)
        
        return processes[:limit]
    
    def get_system_temperatures(self):
        """
        Получение информации о температуре системы (если доступно)
        """
        try:
            temps = psutil.sensors_temperatures()
            result = {}
            
            for chip, sensors in temps.items():
                chip_temps = []
                for sensor in sensors:
                    chip_temps.append({
                        "Название": sensor.label or "Н/Д",
                        "Температура": round(sensor.current, 1),
                        "Высокая": round(sensor.high, 1) if sensor.high else None,
                        "Критическая": round(sensor.critical, 1) if sensor.critical else None
                    })
                result[chip] = chip_temps
            
            return result
        except:
            return None
    
    def get_system_fans(self):
        """
        Получение информации о вентиляторах (если доступно)
        """
        try:
            fans = psutil.sensors_fans()
            result = {}
            
            for chip, sensors in fans.items():
                chip_fans = []
                for sensor in sensors:
                    chip_fans.append({
                        "Название": sensor.label or "Н/Д",
                        "Скорость (RPM)": sensor.current
                    })
                result[chip] = chip_fans
            
            return result
        except:
            return None
    
    def get_system_battery(self):
        """
        Получение информации о батарее (если доступно)
        """
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    "Заряд (%)": round(battery.percent, 1),
                    "Подключено к сети": battery.power_plugged,
                    "Осталось времени (ч)": round(battery.secsleft / 3600, 2) if battery.secsleft != -1 else "Н/Д"
                }
            return None
        except:
            return None
            
    def get_memory_detailed(self):
        """
        Получение детальной информации о памяти
        """
        virtual = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        return {
            "Виртуальная память": {
                "Всего (ГБ)": round(virtual.total / (1024**3), 2),
                "Доступно (ГБ)": round(virtual.available / (1024**3), 2),
                "Использовано (ГБ)": round(virtual.used / (1024**3), 2),
                "Свободно (ГБ)": round(virtual.free / (1024**3), 2),
                "Процент использования": virtual.percent,
                "Активно (ГБ)": round(getattr(virtual, 'active', 0) / (1024**3), 2),
                "Буферы (ГБ)": round(getattr(virtual, 'buffers', 0) / (1024**3), 2),
                "Кэш (ГБ)": round(getattr(virtual, 'cached', 0) / (1024**3), 2)
            },
            "Своп": {
                "Всего (ГБ)": round(swap.total / (1024**3), 2),
                "Использовано (ГБ)": round(swap.used / (1024**3), 2),
                "Свободно (ГБ)": round(swap.free / (1024**3), 2),
                "Процент использования": swap.percent,
                "Загружено (ГБ)": round(getattr(swap, 'sin', 0) / (1024**3), 2),
                "Выгружено (ГБ)": round(getattr(swap, 'sout', 0) / (1024**3), 2)
            }
        }
    
    def is_special_ip(self, ip):
        """Проверяет, является ли IP-адрес служебным"""
        try:
            # Проверка с помощью библиотеки ipaddress
            ip_obj = ipaddress.ip_address(ip)
            
            # Широковещательный адрес (255.255.255.255)
            if ip == "255.255.255.255":
                return True
            
            # Localhost (127.x.x.x)
            if ip_obj.is_loopback:
                return True
            
            # Multicast (224-239.x.x.x)
            if ip_obj.is_multicast:
                return True
            
            # Link-local (169.254.x.x)
            if ip_obj.is_link_local:
                return True
            
            # Reserved
            if ip_obj.is_reserved:
                return True
            
            # Unspecified (0.0.0.0)
            if ip_obj.is_unspecified:
                return True
            
            # Проверяем на VMware, VirtualBox и WSL
            octets = list(map(int, ip.split('.')))
            
            # Типичные подсети виртуальных машин
            vmware_subnets = [
                (192, 168, 56),  # VirtualBox Host-only
                (192, 168, 99),  # VMware
                (192, 168, 152), # VMware
                (192, 168, 232)  # VMware
            ]
            
            # WSL2 обычно использует IP-адреса в подсетях 172.16-31.x.x
            if len(octets) >= 2 and octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            
            if len(octets) >= 3:
                prefix = tuple(octets[:3])
                if prefix in vmware_subnets:
                    return True
            
            return False
        except:
            # При ошибке разбора IP-адреса (например, если это IPv6)
            # проверяем по более простому алгоритму
            
            # Обработка IPv6
            if ":" in ip:
                if ip == "::1" or ip.startswith("fe80:"):
                    return True
                return False
            
            # Разбираем IP на октеты
            octets = list(map(int, ip.split('.')))
            
            # Localhost (127.x.x.x)
            if octets[0] == 127:
                return True
            
            # Multicast (224-239.x.x.x)
            if 224 <= octets[0] <= 239:
                return True
            
            # Broadcast (255.x.x.x)
            if octets[0] == 255:
                return True
            
            # Link-local (169.254.x.x)
            if octets[0] == 169 and octets[1] == 254:
                return True
            
            # WSL2 обычно использует IP-адреса в подсетях 172.16-31.x.x
            if octets[0] == 172 and 16 <= octets[1] <= 31:
                return True
            
            # Reserved for future use (240-255.x.x.x)
            if 240 <= octets[0] <= 255:
                return True
            
            return False
    
    def is_special_mac(self, mac):
        """
        Проверяет, является ли MAC-адрес специальным (не физическим)
        """
        if not mac:
            return True
        
        # Нормализуем MAC-адрес
        mac = mac.upper().replace(':', '-').replace('.', '-')
        
        # Проверяем на специальные MAC-адреса
        special_macs = [
            '00-00-00-00-00-00',  # Нулевой MAC
            'FF-FF-FF-FF-FF-FF',  # Broadcast MAC
            '33-33'               # Мультикаст IPv6 (начинается с 33-33)
        ]
        
        # Проверяем на совпадение со специальными MAC
        for special_mac in special_macs:
            if mac.startswith(special_mac):
                return True
        
        return False
    
    def get_subnet(self, ip_address):
        """
        Определяет подсеть IP-адреса и возвращает её
        
        Args:
            ip_address (str): IP-адрес для проверки
            
        Returns:
            str: Подсеть в формате "A.B.C.0", где A.B.C - первые три октета IP-адреса
        """
        if not ip_address or self.is_special_ip(ip_address):
            return None
            
        # Разбиваем IP-адрес на октеты
        octets = ip_address.split('.')
        if len(octets) != 4:
            return None
            
        # Возвращаем подсеть (первые три октета + ".0")
        return f"{octets[0]}.{octets[1]}.{octets[2]}.0"
    
    def is_same_subnet(self, ip1, ip2):
        """
        Проверяет, находятся ли два IP-адреса в одной подсети
        
        Args:
            ip1 (str): Первый IP-адрес
            ip2 (str): Второй IP-адрес
            
        Returns:
            bool: True если IP-адреса находятся в одной подсети, False в противном случае
        """
        subnet1 = self.get_subnet(ip1)
        subnet2 = self.get_subnet(ip2)
        
        if subnet1 is None or subnet2 is None:
            return False
            
        # Сравниваем первые три октета
        return subnet1 == subnet2
    
    def scan_network(self, start_subnet_index=0, start_batch=1):
        """
        Активное сканирование сети для обнаружения всех устройств
        :param start_subnet_index: Индекс для начала сканирования при возобновлении
        :param start_batch: Номер батча для начала сканирования
        :return: Словарь с обнаруженными устройствами и флагом завершения
        """
        try:
            # Получаем список всех IP-адресов интерфейсов
            interfaces = self.get_network_interfaces()
            subnets = []
            
            discovered_devices = {}
            completed = True  # Флаг завершения сканирования
            
            # Получаем все подсети для сканирования
            for interface in interfaces:
                # Пропускаем неактивные интерфейсы
                if not interface['Активен']:
                        continue
                        
                # Пропускаем VPN и виртуальные интерфейсы
                if self._is_virtual_adapter(interface['Имя'], interface.get('Описание', '')):
                    continue
                
                # Определяем подсеть для каждого интерфейса
                ip = interface['IP']
                if ip and not self.is_special_ip(ip):
                    subnet = self.get_subnet(ip)
                    if subnet and subnet not in subnets:
                        subnets.append(subnet)
            
            # Если подсетей не найдено, используем стандартную
            if not subnets:
                subnets = ["192.168.1.0/24"]
            
            # Устанавливаем максимальное время сканирования (в секундах)
            max_scan_time = 120
            start_time = time.time()
            
            # Перебираем все подсети
            for subnet_index, subnet in enumerate(subnets[start_subnet_index:], start_subnet_index):
                # Пропускаем, если время сканирования превышено
                current_time = time.time()
                if current_time - start_time > max_scan_time:
                    completed = False
                    break
                
                # Разбиваем диапазон IP-адресов на пакеты для более быстрого сканирования
                ip_batches = []
                batch_size = 30  # Размер пакета IP-адресов
                
                # Создаем пакеты по batch_size IP-адресов каждый
                network = ipaddress.ip_network(subnet, strict=False)
                hosts = list(network.hosts())
                
                for i in range(0, len(hosts), batch_size):
                    batch = hosts[i:i+batch_size]
                    ip_batches.append(batch)
                
                # Сканируем каждый пакет IP-адресов
                for batch_index, batch in enumerate(ip_batches[start_batch-1:], start_batch):
                    # Проверяем, не истекло ли время сканирования
                    current_time = time.time()
                    if current_time - start_time > max_scan_time:
                        completed = False
                        break
                    
                    # Запускаем асинхронное сканирование пакета IP-адресов
                    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                        future_to_ip = {executor.submit(self._ping_ip, str(ip)): str(ip) for ip in batch}
                        
                        for future in concurrent.futures.as_completed(future_to_ip):
                            ip = future_to_ip[future]
                            try:
                                is_alive = future.result()
                                if is_alive:
                                    # Если устройство отвечает на пинг, добавляем его в список обнаруженных
                                    discovered_devices[ip] = {
                                        "IP": ip,
                                        "MAC": "",
                                        "Интерфейс": "",
                                        "Тип": "Неизвестно"
                                    }
                            except Exception:
                                # Игнорируем ошибки отдельных пингов
                                pass
                    
                    # Обновляем ARP таблицу после каждого батча
                    arp_table = self.get_arp_table()
                    
                    # Обновляем MAC-адреса и типы у найденных устройств
                    for ip, device in discovered_devices.items():
                        for entry in arp_table:
                            if entry["IP"] == ip:
                                device["MAC"] = entry["MAC"]
                                device["Интерфейс"] = entry["Интерфейс"]
                                device["Тип"] = self._determine_device_type(ip, entry["MAC"])
                
                # Если превышено максимальное время, прерываем цикл по подсетям
                if not completed:
                    break
            
            # Если сканирование не было завершено полностью
            if not completed:
                # Запоминаем индекс последней сканированной подсети и батча для возможности продолжения
                return {
                    "devices": discovered_devices,
                    "completed": completed,
                    "subnet_index": subnet_index,
                    "batch_index": batch_index
                }
            
            return {
                "devices": discovered_devices,
                "completed": completed
            }
        
        except Exception as e:
            logging.error(f"Ошибка при сканировании сети: {e}")
            return {
                "devices": {},
                "completed": False,
                "error": str(e)
            }

    def _ping_ip(self, ip):
        """
        Проверяет доступность IP-адреса с помощью ping
        
        Args:
            ip (str): IP-адрес для проверки
            
        Returns:
            bool: True если хост ответил, False в противном случае
        """
        try:
            # Используем разные команды в зависимости от ОС
            cmd = f"ping -n 1 -w 200 {ip}" if hasattr(psutil, 'WINDOWS') and psutil.WINDOWS else f"ping -c 1 -W 0.5 {ip}"
            result = subprocess.run(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return result.returncode == 0
        except Exception:
            return False

    def get_all_gateways(self):
        """
        Получает информацию о всех шлюзах из всех сетевых адаптеров
        Возвращает список словарей с информацией о шлюзах, отсортированный по приоритету
        """
        gateways = []
        
        # Получаем информацию о сетевых адаптерах
        try:
            if hasattr(psutil, 'WINDOWS') and psutil.WINDOWS:
                # Получаем информацию через ipconfig
                ipconfig_output = subprocess.check_output("ipconfig /all", shell=True).decode('cp1251', errors='ignore')
                
                # Парсим вывод ipconfig для получения данных по каждому адаптеру
                adapter_sections = re.split(r'\r?\n\r?\n', ipconfig_output)
                current_adapter = None
                adapter_type = None
                adapter_gateway = None
                adapter_description = None
                adapter_ip = None
                
                for section in adapter_sections:
                    # Определяем начало нового адаптера
                    adapter_match = re.search(r'(Ethernet|Беспроводная|Wi-Fi|VPN|Tunnel|Virtual|Виртуальный|Hamachi|Radmin|TAP)', section, re.IGNORECASE)
                    if adapter_match:
                        # Сохраняем предыдущий адаптер если у него был шлюз
                        if current_adapter and adapter_gateway:
                            is_virtual = self._is_virtual_adapter(current_adapter, adapter_description)
                            gateway_info = {
                                "name": current_adapter,
                                "description": adapter_description,
                                "IP": adapter_ip,
                                "gateway": adapter_gateway,
                                "is_virtual": is_virtual,
                                "priority": self._calculate_gateway_priority(adapter_gateway, is_virtual)
                            }
                            gateways.append(gateway_info)
                        
                        # Начинаем новый адаптер
                        current_adapter = adapter_match.group(0)
                        adapter_description = section.split('\n')[0].strip()
                        adapter_gateway = None
                        adapter_ip = None
                        
                        # Ищем IP-адрес и шлюз адаптера
                        ip_match = re.search(r'IPv4.*?:\s+(\d+\.\d+\.\d+\.\d+)', section)
                        if ip_match:
                            adapter_ip = ip_match.group(1)
                            
                        gateway_match = re.search(r'Основной шлюз.*?:\s+(\d+\.\d+\.\d+\.\d+)', section) or \
                                       re.search(r'Default Gateway.*?:\s+(\d+\.\d+\.\d+\.\d+)', section)
                        if gateway_match:
                            adapter_gateway = gateway_match.group(1)
                
                # Добавляем последний адаптер
                if current_adapter and adapter_gateway:
                    is_virtual = self._is_virtual_adapter(current_adapter, adapter_description)
                    gateway_info = {
                        "name": current_adapter,
                        "description": adapter_description,
                        "IP": adapter_ip,
                        "gateway": adapter_gateway,
                        "is_virtual": is_virtual,
                        "priority": self._calculate_gateway_priority(adapter_gateway, is_virtual)
                    }
                    gateways.append(gateway_info)
                
                # Также получаем информацию из таблицы маршрутизации
                route_output = subprocess.check_output("route print 0.0.0.0", shell=True).decode('cp1251', errors='ignore')
                route_matches = re.findall(r'0\.0\.0\.0\s+0\.0\.0\.0\s+(\d+\.\d+\.\d+\.\d+)', route_output)
                
                # Добавляем маршруты, которых нет в списке шлюзов
                for route in route_matches:
                    if not any(g["gateway"] == route for g in gateways):
                        # Пытаемся определить тип адаптера по другим данным
                        is_virtual = self._is_virtual_ip(route)
                        gateway_info = {
                            "name": "Неизвестный адаптер",
                            "description": "Маршрут из таблицы маршрутизации",
                            "IP": None,
                            "gateway": route,
                            "is_virtual": is_virtual,
                            "priority": self._calculate_gateway_priority(route, is_virtual)
                        }
                        gateways.append(gateway_info)
        except Exception as e:
            logging.error(f"Ошибка при получении информации о шлюзах: {str(e)}")
        
        # Сортируем шлюзы по приоритету (чем меньше, тем выше приоритет)
        gateways.sort(key=lambda x: x["priority"])
        
        return gateways

    def _is_virtual_adapter(self, adapter_name, adapter_description):
        """
        Определяет, является ли адаптер виртуальным
        """
        virtual_keywords = ['vpn', 'virtual', 'виртуальный', 'tunnel', 'tap', 'hamachi', 'radmin', 
                           'vethernet', 'vmware', 'virtualbox', 'hyper-v', 'docker']
        
        adapter_text = (adapter_name + ' ' + adapter_description).lower()
        
        for keyword in virtual_keywords:
            if keyword in adapter_text:
                return True
        
        return False

    def _is_virtual_ip(self, ip):
        """
        Определяет, принадлежит ли IP-адрес к диапазонам виртуальных сетей
        """
        # Типичные диапазоны виртуальных сетей и VPN
        virtual_ranges = [
            ('10.', False),       # Может быть как реальным, так и виртуальным
            ('172.16.', True),    # Чаще виртуальный
            ('172.17.', True),    # Docker и другие контейнеры
            ('192.168.56.', True),  # VirtualBox по умолчанию
            ('192.168.122.', True), # libvirt/KVM по умолчанию
            ('25.', True),        # Hamachi
            ('26.', True)         # Radmin VPN
        ]
        
        for prefix, is_virtual in virtual_ranges:
            if ip.startswith(prefix):
                return is_virtual
        
        # Для типичных домашних сетей считаем не виртуальными
        if ip.startswith('192.168.0.') or ip.startswith('192.168.1.'):
            return False
        
        # По умолчанию неизвестные сети считаем не виртуальными
        return False

    def _calculate_gateway_priority(self, gateway_ip, is_virtual):
        """
        Рассчитывает приоритет шлюза (меньше = выше приоритет)
        """
        priority = 100  # Начальное значение
        
        # Виртуальные адаптеры имеют более низкий приоритет
        if is_virtual:
            priority += 100
        
        # Приоритет для домашних маршрутизаторов
        if gateway_ip.startswith('192.168.0.') or gateway_ip.startswith('192.168.1.'):
            # Самый высокий приоритет для типичных домашних шлюзов
            if gateway_ip in ['192.168.0.1', '192.168.1.1', '192.168.0.254', '192.168.1.254']:
                priority -= 50
            else:
                priority -= 25
        elif gateway_ip.startswith('10.0.0.'):
            # Средний приоритет для сетей 10.0.0.x
            if gateway_ip in ['10.0.0.1', '10.0.0.138']:
                priority -= 20
        elif gateway_ip.startswith('26.') or gateway_ip.startswith('25.'):
            # Низкий приоритет для Radmin VPN и Hamachi
            priority += 30
        
        return priority

    def _determine_device_type(self, ip, mac, is_gateway=False):
        """
        Улучшенное определение типа устройства с учетом особенностей корпоративных сетей.
        Определяет тип устройства: маршрутизатор, коммутатор или другое.
        
        Args:
            ip (str): IP-адрес устройства
            mac (str): MAC-адрес устройства
            is_gateway (bool): Флаг, указывающий, является ли устройство шлюзом
            
        Returns:
            str: Тип устройства ("Маршрутизатор", "Коммутатор", "Компьютер" и т.д.)
        """
        # Если MAC отсутствует или не определен
        if not mac or mac == "Не определен":
            if is_gateway:
                return "Маршрутизатор"
            return "Неизвестное устройство"
        
        # Нормализуем MAC-адрес для проверки
        mac_lower = mac.lower().replace('-', ':').replace('.', ':')
        
        # Получаем название производителя
        vendor = self._get_mac_vendor(mac)
        vendor_lower = vendor.lower() if vendor else ""
        
        # Префиксы MAC-адресов известных производителей коммутаторов
        switch_prefixes = [
            # Cisco Catalyst коммутаторы
            "00:1a:a1", "00:1b:54", "00:21:1b", "00:23:5e", "00:25:45", 
            # HP/Aruba коммутаторы
            "00:0e:b3", "00:14:c2", "00:16:b9", "00:1f:fe", "24:be:05", 
            # Dell коммутаторы
            "00:1e:c9", "14:fe:b5", "24:b6:fd", "f8:ca:b8", "f8:db:88",
            # Juniper коммутаторы
            "00:05:85", "00:10:db", "2c:6b:f5", "28:8a:1c", "54:1e:56"
        ]
        
        # Определение на основе префикса MAC
        for prefix in switch_prefixes:
            if mac_lower.startswith(prefix.lower()):
                return "Коммутатор"
        
        # Определение на основе имени производителя
        switch_vendors = ["cisco systems", "cisco switch", "d-link switch", "hp procurve", 
                          "hp enterprise", "juniper networks", "aruba", "allied telesis", 
                          "netgear switch", "dell switch", "brocade", "extreme networks"]
        
        for switch_vendor in switch_vendors:
            if switch_vendor in vendor_lower:
                return "Коммутатор"
                
        # Проверка на маршрутизатор по производителю
        router_vendors = ["tp-link technologies", "mikrotik", "asus router", "d-link router", 
                          "netgear router", "cisco router", "huawei router", "zyxel", "edge router", 
                          "ubiquiti", "sagemcom", "actiontec", "arris", "technicolor"]
        
        for router_vendor in router_vendors:
            if router_vendor in vendor_lower:
                return "Маршрутизатор"
        
        # Если устройство является шлюзом, проверяем дополнительные признаки коммутатора
        if is_gateway:
            # Если есть признаки коммутатора в имени производителя
            switch_keywords = ["switch", "коммутатор", "dell powerconnect", "juniper ex", 
                              "cisco catalyst", "hp procurve", "hp switch", "aruba switch"]
            
            for keyword in switch_keywords:
                if vendor_lower and keyword in vendor_lower:
                    return "Коммутатор"
                
            # По умолчанию считаем шлюз маршрутизатором, если нет явных признаков коммутатора
            return "Маршрутизатор"
        
        # По умолчанию считаем устройство компьютером
        return "Компьютер"

    def _check_common_ports(self, ip, timeout=0.5):
        """
        Проверяет наличие открытых портов на устройстве.
        Это альтернативный метод обнаружения устройств, когда ICMP блокируется.
        
        Args:
            ip (str): IP-адрес для проверки
            timeout (float): Таймаут для проверки порта в секундах
            
        Returns:
            bool: True если хотя бы один порт открыт, False в противном случае
        """
        # Добавляем порты, часто используемые мобильными устройствами
        # HTTP, HTTPS, SSH, Telnet, FTP, mDNS, DLNA/UPnP, SNMP, AirPlay, Chromecast
        common_ports = [80, 443, 22, 23, 21, 5353, 1900, 161, 7000, 8008, 8009, 32768, 32769, 49152, 62078]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(timeout)
                result = sock.connect_ex((ip, port))
                sock.close()
                if result == 0:  # Порт открыт
                    return True
            except:
                pass
        
        return False

    def _scan_network_alternative(self, subnet=None, max_devices=20):
        """
        Альтернативный метод сканирования сети, когда ICMP блокируется.
        Использует комбинацию методов обнаружения и проверяет актуальность устройств.
        
        Args:
            subnet (str): Подсеть для сканирования (если None, используется текущая подсеть)
            max_devices (int): Максимальное количество устройств для проверки
            
        Returns:
            dict: Словарь обнаруженных устройств
        """
        discovered_devices = {}
        current_time = time.time()
        
        # Проверяем, существует ли словарь для хранения истории устройств
        if not hasattr(self, '_devices_history'):
            self._devices_history = {}
        
        # 1. Сначала собираем устройства из ARP-таблицы
        arp_entries = self.get_arp_table()
        for entry in arp_entries:
            ip = entry.get("IP")
            if ip and not self.is_special_ip(ip):
                mac = entry.get("MAC", "Не определен")
                if not self.is_special_mac(mac):
                    # Проверяем, активно ли устройство в данный момент
                    is_active = False
                    ping_success = self._ping_ip(ip)
                    port_success = self._check_common_ports(ip)
                    
                    # Устройство считается активным, если оно отвечает на ping или на проверку портов
                    if ping_success or port_success:
                        is_active = True
                        
                    # Сохраняем статус и время последней активности
                    if ip in self._devices_history:
                        # Обновляем существующую запись
                        if is_active:
                            self._devices_history[ip]["last_active"] = current_time
                            self._devices_history[ip]["active"] = True
                        else:
                            # Если устройство не активно сейчас, но было активно недавно (в течение 3 минут),
                            # оставляем его в списке, но помечаем как неактивное
                            if current_time - self._devices_history[ip]["last_active"] < 180:  # 3 минуты
                                is_active = True  # Считаем его всё ещё присутствующим, но неактивным
                                self._devices_history[ip]["active"] = False
                            else:
                                # Если устройство было неактивно больше 3 минут, удаляем его
                                continue
                    else:
                        # Создаем новую запись в истории
                        self._devices_history[ip] = {
                            "last_active": current_time if is_active else 0,
                            "active": is_active,
                            "first_seen": current_time
                        }
                    
                    # Если устройство активно или было активно недавно, добавляем его в список
                    if is_active:
                        active_status = "Активно" if self._devices_history[ip]["active"] else "Неактивно"
                        discovered_devices[ip] = {
                            "IP": ip,
                            "MAC": mac,
                            "Тип": "Неизвестно",  # Тип будет определен позже
                            "Метод": "ARP",
                            "Статус": active_status
                        }
        
        # 2. Получаем текущую подсеть
        if not subnet:
            if hasattr(self, 'local_ip') and self.local_ip:
                subnet = self.get_subnet(self.local_ip)
            else:
                # Если не можем определить подсеть, используем стандартную
                return discovered_devices
        
        # Удаляем ".0" из конца подсети, если она есть
        if subnet.endswith('.0'):
            subnet = subnet[:-2]
        
        # 3. Пытаемся просканировать общие порты для устройств в подсети
        # Сначала пробуем наиболее вероятные адреса
        common_last_octets = [1, 2, 3, 254, 100, 101, 10, 20, 30, 40, 50, 60, 70, 80, 90, 110, 120, 130, 140, 150]
        
        for last_octet in common_last_octets:
            ip = f"{subnet}.{last_octet}"
            if ip not in discovered_devices and not self.is_special_ip(ip):
                ping_success = self._ping_ip(ip)
                port_success = self._check_common_ports(ip)
                
                # Устройство считается активным, если оно отвечает на ping или на проверку портов
                if ping_success or port_success:
                    method = "ICMP" if ping_success else "PORT"
                    
                    # Сохраняем статус и время последней активности
                    if ip in self._devices_history:
                        self._devices_history[ip]["last_active"] = current_time
                        self._devices_history[ip]["active"] = True
                    else:
                        self._devices_history[ip] = {
                            "last_active": current_time,
                            "active": True,
                            "first_seen": current_time
                        }
                    
                    discovered_devices[ip] = {
                        "IP": ip,
                        "MAC": "Не определен",  # MAC будет определен позже
                        "Тип": "Неизвестно",
                        "Метод": method,
                        "Статус": "Активно"
                    }
        
        # 4. Если обнаружено слишком мало устройств, сканируем дополнительные адреса
        if len(discovered_devices) < max_devices:
            # Ограничиваем диапазон сканирования
            max_additional = max_devices - len(discovered_devices)
            step = max(1, 254 // max_additional)
            
            for last_octet in range(1, 255, step):
                if len(discovered_devices) >= max_devices:
                    break
                    
                ip = f"{subnet}.{last_octet}"
                if ip not in discovered_devices and not self.is_special_ip(ip):
                    # Проверяем сначала порты, затем при необходимости пинг
                    port_success = self._check_common_ports(ip)
                    if port_success:
                        ping_success = self._ping_ip(ip)
                        method = "ICMP" if ping_success else "PORT"
                        
                        # Сохраняем статус и время последней активности
                        if ip in self._devices_history:
                            self._devices_history[ip]["last_active"] = current_time
                            self._devices_history[ip]["active"] = True
                        else:
                            self._devices_history[ip] = {
                                "last_active": current_time,
                                "active": True,
                                "first_seen": current_time
                            }
                        
                        discovered_devices[ip] = {
                            "IP": ip,
                            "MAC": "Не определен",
                            "Тип": "Неизвестно",
                            "Метод": method,
                            "Статус": "Активно"
                        }
        
        # 5. Пингуем все обнаруженные устройства для обновления ARP-таблицы
        for ip in list(discovered_devices.keys()):
            try:
                subprocess.call(f"ping -n 1 {ip}", shell=True, 
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except:
                pass
        
        # 6. Обновляем MAC-адреса для всех обнаруженных устройств
        updated_arp = self.get_arp_table()
        for entry in updated_arp:
            ip = entry.get("IP")
            if ip in discovered_devices and discovered_devices[ip].get("MAC") == "Не определен":
                discovered_devices[ip]["MAC"] = entry.get("MAC", "Не определен")
        
        # 7. Очистка истории устройств (удаляем устройства, не видимые более 1 часа)
        cleanup_time = current_time - 3600  # 1 час
        ips_to_remove = [ip for ip, data in self._devices_history.items() 
                         if data["last_active"] < cleanup_time]
        for ip in ips_to_remove:
            del self._devices_history[ip]
        
        return discovered_devices

class NetworkMonitorThread(QThread):
    """
    Поток для обновления информации о сетевой активности
    """
    update_signal = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        self.monitor = NetworkMonitor()
        self._running = True
    
    def run(self):
        while self._running:
            data = {
                "interfaces": self.monitor.get_network_interfaces(),
                "stats": self.monitor.get_network_stats(),
                "arp_table": self.monitor.get_arp_table(),
                "gateway": self.monitor.get_gateway_info()
            }
            self.update_signal.emit(data)
            time.sleep(2)
    
    def stop(self):
        self._running = False

class NetworkInfoTab(QWidget):
    """
    Вкладка с информацией о сетевых интерфейсах
    """
    def __init__(self, monitor_thread):
        super().__init__()
        self.monitor = NetworkMonitor()
        self.monitor_thread = monitor_thread
        self.init_ui()
        
        # Подключаем обновление данных
        self.monitor_thread.update_signal.connect(self.update_data)
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Группа с информацией о сетевых интерфейсах
        interfaces_group = QGroupBox("Сетевые интерфейсы")
        interfaces_layout = QVBoxLayout()
        
        # Таблица интерфейсов
        self.interfaces_table = QTableWidget()
        self.interfaces_table.setColumnCount(7)
        self.interfaces_table.setHorizontalHeaderLabels([
            "Интерфейс", "IP адрес", "Маска сети", "MAC адрес", 
            "Статус", "MTU", "Скорость"
        ])
        self.interfaces_table.setColumnWidth(0, 150)
        self.interfaces_table.setColumnWidth(1, 120)
        self.interfaces_table.setColumnWidth(2, 120)
        self.interfaces_table.setColumnWidth(3, 150)
        
        # Применяем стили к таблицам
        table_style = """
            QTableWidget {
                border: 1px solid #c0c8e0;
                border-radius: 0px;
                background-color: white;
                selection-background-color: #e3f2fd;
                selection-color: #1976D2;
                gridline-color: #e0e6f0;
            }
            QTableWidget::item {
                padding: 3px;
                border-bottom: 1px solid #f0f5ff;
            }
            QTableWidget::item:selected {
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
        """
        self.interfaces_table.setStyleSheet(table_style)
        
        interfaces_layout.addWidget(self.interfaces_table)
        interfaces_group.setLayout(interfaces_layout)
        layout.addWidget(interfaces_group)
        
        # Группа с информацией о шлюзе
        gateway_group = QGroupBox("Информация о шлюзе")
        gateway_layout = QVBoxLayout()
        
        self.gateway_info = QLabel("Нет информации о шлюзе")
        gateway_layout.addWidget(self.gateway_info)
        
        gateway_group.setLayout(gateway_layout)
        layout.addWidget(gateway_group)
        
        # Группа с сетевой статистикой
        stats_group = QGroupBox("Статистика сетевого трафика")
        stats_layout = QVBoxLayout()
        
        # Таблица статистики
        self.stats_table = QTableWidget()
        self.stats_table.setColumnCount(5)
        self.stats_table.setHorizontalHeaderLabels([
            "Интерфейс", "Отправлено (МБ)", "Получено (МБ)", 
            "Отправлено пакетов", "Получено пакетов"
        ])
        self.stats_table.setStyleSheet(table_style)
        
        stats_layout.addWidget(self.stats_table)
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)
        
        self.setLayout(layout)
        
        # Обновляем данные при инициализации
        self.update_interface_table()
        self.update_gateway_info()
        self.update_stats_table()
    
    def update_interface_table(self):
        interfaces = self.monitor.get_network_interfaces()
        
        self.interfaces_table.setRowCount(len(interfaces))
        
        for row, (interface, info) in enumerate(interfaces.items()):
            self.interfaces_table.setItem(row, 0, QTableWidgetItem(interface))
            # Преобразуем список IP-адресов в строку
            ip_text = ", ".join(info["IP"]) if isinstance(info["IP"], list) else str(info["IP"])
            netmask_text = ", ".join(info["Маска сети"]) if isinstance(info["Маска сети"], list) else str(info["Маска сети"])
            
            self.interfaces_table.setItem(row, 1, QTableWidgetItem(ip_text))
            self.interfaces_table.setItem(row, 2, QTableWidgetItem(netmask_text))
            self.interfaces_table.setItem(row, 3, QTableWidgetItem(info["MAC"]))
            self.interfaces_table.setItem(row, 4, QTableWidgetItem("Активен" if info["Активен"] else "Неактивен"))
            self.interfaces_table.setItem(row, 5, QTableWidgetItem(str(info["MTU"])))
            self.interfaces_table.setItem(row, 6, QTableWidgetItem(info["Скорость"]))
    
    def update_gateway_info(self):
        gateway = self.monitor.get_gateway_info()
        
        if gateway:
            self.gateway_info.setText(
                f"<span style='color: #2196F3; font-weight: bold;'>IP адрес:</span> {gateway['IP']}\n"
                f"<span style='color: #2196F3; font-weight: bold;'>MAC адрес:</span> {gateway['MAC']}"
            )
        else:
            self.gateway_info.setText("<span style='color: #607D8B; font-style: italic;'>Нет информации о шлюзе</span>")
    
    def update_stats_table(self):
        stats = self.monitor.get_network_stats()
        
        self.stats_table.setRowCount(len(stats))
        
        for row, (interface, info) in enumerate(stats.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(interface))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(info["Отправлено (МБ)"])))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(info["Получено (МБ)"])))
            self.stats_table.setItem(row, 3, QTableWidgetItem(str(info["Отправлено пакетов"])))
            self.stats_table.setItem(row, 4, QTableWidgetItem(str(info["Получено пакетов"])))
    
    def update_data(self, data):
        interfaces = data["interfaces"]
        
        self.interfaces_table.setRowCount(len(interfaces))
        
        for row, (interface, info) in enumerate(interfaces.items()):
            self.interfaces_table.setItem(row, 0, QTableWidgetItem(interface))
            # Преобразуем список IP-адресов в строку
            ip_text = ", ".join(info["IP"]) if isinstance(info["IP"], list) else str(info["IP"])
            netmask_text = ", ".join(info["Маска сети"]) if isinstance(info["Маска сети"], list) else str(info["Маска сети"])
            
            self.interfaces_table.setItem(row, 1, QTableWidgetItem(ip_text))
            self.interfaces_table.setItem(row, 2, QTableWidgetItem(netmask_text))
            self.interfaces_table.setItem(row, 3, QTableWidgetItem(info["MAC"]))
            self.interfaces_table.setItem(row, 4, QTableWidgetItem("Активен" if info["Активен"] else "Неактивен"))
            self.interfaces_table.setItem(row, 5, QTableWidgetItem(str(info["MTU"])))
            self.interfaces_table.setItem(row, 6, QTableWidgetItem(info["Скорость"]))
        
        gateway = data["gateway"]
        if gateway:
            self.gateway_info.setText(
                f"<span style='color: #2196F3; font-weight: bold;'>IP адрес:</span> {gateway['IP']}\n"
                f"<span style='color: #2196F3; font-weight: bold;'>MAC адрес:</span> {gateway['MAC']}"
            )
        else:
            self.gateway_info.setText("<span style='color: #607D8B; font-style: italic;'>Нет информации о шлюзе</span>")
        
        stats = data["stats"]
        self.stats_table.setRowCount(len(stats))
        
        for row, (interface, info) in enumerate(stats.items()):
            self.stats_table.setItem(row, 0, QTableWidgetItem(interface))
            self.stats_table.setItem(row, 1, QTableWidgetItem(str(info["Отправлено (МБ)"])))
            self.stats_table.setItem(row, 2, QTableWidgetItem(str(info["Получено (МБ)"])))
            self.stats_table.setItem(row, 3, QTableWidgetItem(str(info["Отправлено пакетов"])))
            self.stats_table.setItem(row, 4, QTableWidgetItem(str(info["Получено пакетов"])))

class ARPTableTab(QWidget):
    """
    Вкладка с ARP таблицей
    """
    def __init__(self, monitor_thread):
        super().__init__()
        self.monitor_thread = monitor_thread
        self.init_ui()
    
    def init_ui(self):
        # Основной лейаут
        main_layout = QVBoxLayout()
        
        # Добавляем заголовок
        header_layout = QHBoxLayout()
        title_label = QLabel("ARP таблица")
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Создаем таблицу для отображения ARP записей
        self.arp_table = QTableWidget()
        self.arp_table.setColumnCount(3)
        self.arp_table.setHorizontalHeaderLabels([
            "IP адрес", 
            "MAC адрес", 
            "Тип устройства"
        ])
        
        # Устанавливаем свойства таблицы
        self.arp_table.setAlternatingRowColors(True)
        self.arp_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e6f2ff;
                color: #2196F3;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: 1px solid #d0d0d0;
                border-left: none;
                border-top: none;
                font-weight: bold;
                color: #424242;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        # Растягиваем заголовки на всю ширину таблицы
        self.arp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Добавляем компоненты в лейаут
        main_layout.addLayout(header_layout)
        main_layout.addWidget(self.arp_table)
        
        # Устанавливаем основной лейаут
        self.setLayout(main_layout)
        
        # Обновляем данные при инициализации
        self.update_arp_table()
        
        # Подключаем сигнал обновления данных
        self.monitor_thread.update_signal.connect(self.update_data)
    
    def update_arp_table(self):
        """
        Обновляет таблицу ARP записей
        """
        # Получаем данные ARP таблицы
        arp_data = self.monitor_thread.monitor.get_arp_table()
        
        # Очищаем таблицу
        self.arp_table.setRowCount(0)
        
        # Заполняем таблицу данными
        for i, record in enumerate(arp_data):
            self.arp_table.insertRow(i)
            self.arp_table.setItem(i, 0, QTableWidgetItem(record.get("IP", "N/A")))
            self.arp_table.setItem(i, 1, QTableWidgetItem(record.get("MAC", "N/A")))
            self.arp_table.setItem(i, 2, QTableWidgetItem(record.get("Тип", "N/A")))
    
    def update_data(self, data):
        """
        Обновляет данные от потока мониторинга
        """
        if "arp_table" in data:
            # Очищаем таблицу
            self.arp_table.setRowCount(0)
            
            # Заполняем таблицу данными
            for i, record in enumerate(data["arp_table"]):
                self.arp_table.insertRow(i)
                self.arp_table.setItem(i, 0, QTableWidgetItem(record.get("IP", "N/A")))
                self.arp_table.setItem(i, 1, QTableWidgetItem(record.get("MAC", "N/A")))
                self.arp_table.setItem(i, 2, QTableWidgetItem(record.get("Тип", "N/A")))

class NetworkTopologyCanvas(QWidget):
    """
    Виджет для рисования топологии сети в стиле логического представления Cisco Packet Tracer
    с возможностью масштабирования и перемещения
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.devices = []
        self.connections = []
        self.selected_device = None
        self.setMinimumHeight(450)
        self.setMinimumWidth(600)
        self.setStyleSheet("background-color: #FFFFFF; border: 2px solid #cccccc; border-radius: 4px;")
        self.setMouseTracking(True)  # Отслеживание движения мыши
        
        # Переменные для перемещения и масштабирования
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.last_mouse_pos = None
        self.dragging = False
        
        # Информация для всплывающей подсказки
        self.hover_device = None
        
        # Базовый размер иконок (не меняется при масштабировании)
        self.base_icon_size = 45
        
        # Цвета для лучшего восприятия
        self.colors = {
            "router_fill": QColor(231, 76, 60),  # Красный из Flat UI Colors
            "router_border": QColor(192, 57, 43),
            "router_accent": QColor(255, 110, 110),
            "switch_fill": QColor(52, 152, 219),  # Синий из Flat UI Colors
            "switch_border": QColor(41, 128, 185),
            "computer_fill": QColor(41, 128, 185),  # Темно-синий из Flat UI Colors
            "computer_border": QColor(22, 96, 148),
            "computer_screen": QColor(214, 234, 248),
            "other_fill": QColor(80, 180, 240),  # Светло-синий вместо зеленого
            "other_border": QColor(60, 150, 220),
            "connection": QColor(84, 84, 84),
            "selected": QColor(41, 128, 185),  # Синий из Flat UI Colors
            "hovered": QColor(189, 195, 199, 180),  # Серый из Flat UI Colors
            "text": QColor(44, 62, 80),  # Темно-синий (почти черный) из Flat UI Colors
            "highlight": QColor(241, 196, 15, 100),  # Желтый из Flat UI Colors с прозрачностью
            "grid": QColor(240, 240, 240)  # Очень светлый серый для сетки
        }

    def paintEvent(self, event):
        """
        Улучшенный метод для отрисовки элементов топологии с корректным масштабированием
        """
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setRenderHint(QPainter.TextAntialiasing)
            painter.setRenderHint(QPainter.SmoothPixmapTransform)
            
            # Заливаем фон белым цветом
            painter.fillRect(self.rect(), QColor("#FFFFFF"))
            
            # Рисуем сетку, не зависящую от масштаба
            self._draw_grid(painter)
            
            # Проверяем наличие данных перед отрисовкой
            if not hasattr(self, 'devices') or not self.devices:
                # Если нет данных, просто заканчиваем отрисовку
                painter.end()
                return
            
            # Сохраняем текущую трансформацию для восстановления
            painter.save()
            
            # Применяем масштабирование и смещение
            painter.translate(self.offset_x, self.offset_y)
            painter.scale(self.scale, self.scale)
            
            # Рассчитываем позиции устройств
            width = self.width() / self.scale
            height = self.height() / self.scale
            positions = self._calculate_positions(width, height)
            
            # Рисуем соединения между устройствами
            self._draw_connections(painter, positions)
            
            # Восстанавливаем трансформацию перед рисованием устройств
            painter.restore()
            
            # Рисуем устройства с фиксированным размером независимо от масштаба
            self._draw_scaled_devices(painter, positions)
            
        except Exception as e:
            # В случае ошибки, логируем её и продолжаем работу
            print(f"Ошибка при отрисовке топологии сети: {str(e)}")
    
    def _draw_grid(self, painter):
        """
        Рисует фоновую сетку, независимую от масштаба
        """
        grid_size = 50  # Размер ячейки сетки
        
        # Используем цвет сетки из палитры цветов
        painter.setPen(QPen(self.colors["grid"], 0.5, Qt.DotLine))
        
        # Смещение сетки с учетом панорамирования (чтобы сетка двигалась вместе с содержимым)
        offset_x = self.offset_x % grid_size
        offset_y = self.offset_y % grid_size
        
        # Рисуем вертикальные линии
        for x in range(int(offset_x), self.width() + grid_size, grid_size):
            painter.drawLine(x, 0, x, self.height())
        
        # Рисуем горизонтальные линии
        for y in range(int(offset_y), self.height() + grid_size, grid_size):
            painter.drawLine(0, y, self.width(), y)
    
    def _calculate_positions(self, width, height):
        """
        Размещение устройств с маршрутизатором в центре
        """
        positions = {}
        
        # Находим шлюз и классифицируем устройства
        gateway = None
        for device in self.devices:
            if device.get("Тип") == "Маршрутизатор":
                gateway = device
                break
            
        other_devices = [d for d in self.devices if d != gateway]
        
        # Определяем центр области отображения
        center_x = width / 2
        center_y = height / 2
        
        # Увеличиваем радиус для большего расстояния между устройствами
        radius = min(width, height) * 0.4
        
        # Шлюз размещаем в центре
        if gateway:
            gateway_ip = gateway["IP"]
            if isinstance(gateway_ip, list):
                gateway_ip = gateway_ip[0]
            positions[gateway_ip] = QPointF(center_x, center_y)
        
        # Равномерно распределяем остальные устройства по окружности
        if other_devices:
            # Вычисляем угол между устройствами
            angle_step = 2 * math.pi / len(other_devices)
            
            # Начинаем с верхней точки окружности
            start_angle = -math.pi / 2
            
            for i, device in enumerate(other_devices):
                # Вычисляем угол для текущего устройства
                angle = start_angle + i * angle_step
                
                # Вычисляем координаты
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                # Получаем IP для позиционирования
                device_ip = device["IP"]
                if isinstance(device_ip, list):
                    device_ip = device_ip[0]
                
                positions[device_ip] = QPointF(x, y)
        
        return positions
    
    def _draw_scaled_devices(self, painter, positions):
        """
        Рисует устройства с учетом масштаба, но с фиксированным размером иконок
        """
        for device in self.devices:
            device_ips = device["IP"] if isinstance(device["IP"], list) else [device["IP"]]
            # Используем первый IP-адрес для позиционирования
            ip = device_ips[0]
            if ip in positions:
                # Преобразуем координаты с учетом масштаба и смещения
                scaled_pos = QPointF(
                    positions[ip].x() * self.scale + self.offset_x,
                    positions[ip].y() * self.scale + self.offset_y
                )
                
                is_selected = False
                if self.selected_device is not None:
                    selected_ips = self.selected_device["IP"] if isinstance(self.selected_device["IP"], list) else [self.selected_device["IP"]]
                    is_selected = any(ip in device_ips for ip in selected_ips)
                
                is_hovered = False
                if self.hover_device is not None:
                    hover_ips = self.hover_device["IP"] if isinstance(self.hover_device["IP"], list) else [self.hover_device["IP"]]
                    is_hovered = any(ip in device_ips for ip in hover_ips)
                
                # Рисуем устройство с фиксированным размером
                self._draw_device_fixed_size(painter, scaled_pos, device, is_selected, is_hovered)
    
    def _draw_device_fixed_size(self, painter, position, device, is_selected=False, is_hovered=False):
        """
        Рисует устройство фиксированного размера с улучшенным определением типа
        """
        # Сохраняем текущее состояние художника
        painter.save()
        
        # Получаем тип устройства, статус и дополнительные атрибуты
        device_type = device.get("Тип", "Неизвестное устройство")
        is_virtual_interface = False  # По умолчанию не виртуальный интерфейс
        
        # Проверяем статус устройства (активно/неактивно)
        device_status = device.get("Статус", "Активно")
        is_active = device_status == "Активно"
        
        # Проверяем IP адреса виртуальных интерфейсов
        if isinstance(device.get("IP", ""), str):
            known_virtual_interfaces = ["192.168.204.254", "192.168.10.254"]
            is_virtual_interface = device.get("IP", "") in known_virtual_interfaces
        
        # Размер устройства
        device_size = QSize(40, 40)
        if is_selected:
            device_size = QSize(45, 45)  # Увеличиваем размер выделенного устройства
        
        # Создаем прямоугольник для отрисовки устройства
        rect = QRectF(position.x() - device_size.width() / 2, 
                     position.y() - device_size.height() / 2,
                     device_size.width(), device_size.height())
        
        # Обрабатываем эффект подсветки при наведении или выделении
        if is_hovered or is_selected:
            try:
                # Создаем эффект сияния вокруг устройства
                glow_radius = 10
                glow_rect = rect.adjusted(-glow_radius, -glow_radius, glow_radius, glow_radius)
                
                # Создаем радиальный градиент для эффекта сияния
                gradient = QRadialGradient(rect.center(), glow_radius + rect.width() / 2)
                
                if is_selected:
                    # Яркое свечение для выделенного устройства
                    gradient.setColorAt(0, QColor(52, 152, 219, 150))
                    gradient.setColorAt(0.7, QColor(52, 152, 219, 80))
                    gradient.setColorAt(1, QColor(52, 152, 219, 0))
                else:
                    # Более мягкое свечение для наведения
                    gradient.setColorAt(0, QColor(52, 152, 219, 100))
                    gradient.setColorAt(0.8, QColor(52, 152, 219, 40))
                    gradient.setColorAt(1, QColor(52, 152, 219, 0))
                
                painter.setBrush(gradient)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(glow_rect.center(), glow_radius + rect.width() / 2, glow_radius + rect.width() / 2)
            except Exception as e:
                # В случае ошибки с градиентом, просто пропускаем его отрисовку
                print(f"Ошибка при создании градиента: {str(e)}")
        
        # Если устройство неактивно, рисуем вокруг него серую полупрозрачную рамку
        if not is_active:
            # Создаем эффект "отключения" для неактивных устройств
            inactive_rect = rect.adjusted(-5, -5, 5, 5)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(100, 100, 100, 120), 2, Qt.DashLine))
            painter.drawEllipse(inactive_rect)
        
        # Определяем, какое устройство рисовать
        if device.get("Локальный", False):
            self._draw_local_computer(painter, rect)
        elif "Маршрутизатор" in device_type:
            # Получаем дополнительные атрибуты маршрутизатора
            is_primary = device.get("Основной", False)
            is_virtual = device.get("Виртуальный", False)
            
            # Выбираем метод отрисовки в зависимости от типа маршрутизатора
            if is_primary and not is_virtual:
                # Основной физический маршрутизатор
                self._draw_router_primary(painter, rect)
            elif is_virtual:
                # Виртуальный маршрутизатор
                self._draw_router_virtual(painter, rect)
            else:
                # Обычный маршрутизатор
                self._draw_router(painter, rect)
        elif "Коммутатор" in device_type:
            self._draw_switch(painter, rect)
        elif "Компьютер" in device_type or is_virtual_interface:
            # Проверяем подсеть устройства
            is_same_subnet = device.get("СамаяПодсеть", True)  # По умолчанию считаем из той же подсети
            
            # Если это виртуальный интерфейс, используем специальный метод отрисовки
            if is_virtual_interface:
                self._draw_virtual_interface(painter, rect)
            else:
                self._draw_computer(painter, rect, is_same_subnet)
        else:
            # Для всех других устройств используем прежний метод отрисовки
            self._draw_other_device(painter, rect)
        
        # Получаем IP-адрес для отображения
        ip_address = ""
        if "IP" in device:
            device_ip = device["IP"]
            if isinstance(device_ip, list) and device_ip:
                # Отображаем первый IP и указываем, если есть дополнительные
                ip_address = device_ip[0]
                if len(device_ip) > 1:
                    ip_address += " +"
            else:
                ip_address = str(device_ip)
        
        # Добавляем маркеры статуса к тексту IP-адреса
        if not is_active:
            ip_address = ip_address + " [!]"
        # Добавляем специальную метку для виртуального интерфейса
        elif is_virtual_interface:
            # Рисуем специальную метку рядом с IP-адресом
            ip_address = ip_address + " (V)"
        
        # Вычисляем примерную ширину текста
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.width(ip_address)
        
        # Рисуем текст с IP-адресом под устройством с динамически адаптированной шириной
        padding = 20  # Увеличенный отступ с каждой стороны для предотвращения обрезания
        text_rect = QRectF(
            rect.center().x() - text_width/2 - padding, 
            rect.bottom() + 5, 
            text_width + padding*2,  # Размер рамки основан на ширине текста с запасом
            24  # Увеличенная высота для лучшего отображения
        )
        
        # Устанавливаем стиль текста
        font = painter.font()
        font.setPointSize(8)
        if is_selected:
            font.setBold(True)
        painter.setFont(font)
        
        # Рисуем цветной фон для текста с более точным размером
        text_bg = QRectF(text_rect)
        text_bg.adjust(-5, -2, 5, 2)  # Немного расширяем фон для лучшего вида
        
        # Выбираем цвет фона в зависимости от статуса устройства
        if is_selected:
            painter.setBrush(QColor(52, 152, 219, 80))
            painter.setPen(QPen(QColor(52, 152, 219), 0.5))
        elif not is_active:
            # Серый полупрозрачный фон для неактивных устройств
            painter.setBrush(QColor(200, 200, 200, 180))
            painter.setPen(QPen(QColor(150, 150, 150), 0.5))
        else:
            # Белый фон для активных устройств
            painter.setBrush(QColor(255, 255, 255, 180))
            painter.setPen(QPen(QColor(200, 200, 200), 0.5))
        
        painter.drawRoundedRect(text_bg, 4, 4)
        
        # Устанавливаем цвет текста в зависимости от статуса устройства
        if is_selected:
            painter.setPen(QColor(0, 0, 0))
        elif not is_active:
            painter.setPen(QColor(100, 100, 100))  # Серый цвет для неактивных устройств
        else:
            painter.setPen(QColor(30, 30, 30))  # Почти черный для активных устройств
        
        # Если устройство неактивно, применяем эффект полупрозрачности ко всему изображению
        if not is_active:
            painter.setOpacity(0.6)  # Устанавливаем полупрозрачность для неактивных устройств
        
        # Рисуем текст
        painter.drawText(text_rect, Qt.AlignCenter, ip_address)
        
        # Восстанавливаем состояние художника
        painter.restore()

    def _draw_router_primary(self, painter, rect):
        """
        Отрисовка основного (физического) маршрутизатора с выделением
        """
        # Сохраняем текущее состояние художника
        painter.save()
        
        # Яркие цвета для основного маршрутизатора
        body_color = QColor(231, 76, 60)  # Насыщенный красный
        detail_color = QColor(192, 57, 43)
        highlight_color = QColor(236, 240, 241)
        
        # Добавляем светящийся эффект (ореол)
        glow = QRadialGradient(rect.center(), rect.width() * 0.8)
        glow.setColorAt(0, QColor(231, 76, 60, 50))
        glow.setColorAt(1, QColor(231, 76, 60, 0))
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect.center(), rect.width() * 0.8, rect.width() * 0.8)
        
        # Основная форма маршрутизатора (прямоугольник с закругленными углами)
        painter.setBrush(body_color)
        painter.setPen(Qt.NoPen)
        router_rect = rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(router_rect, 6, 6)
        
        # Детали маршрутизатора
        painter.setBrush(detail_color)
        
        # Верхняя панель
        top_panel = QRectF(router_rect.left() + 2, router_rect.top() + 2,
                           router_rect.width() - 4, router_rect.height() / 5)
        painter.drawRoundedRect(top_panel, 3, 3)
        
        # Антенны на основном маршрутизаторе
        antenna_width = 3
        antenna_height = router_rect.height() * 0.3
        
        # Левая антенна
        left_antenna = QRectF(router_rect.left() + router_rect.width() * 0.25 - antenna_width / 2,
                              router_rect.top() - antenna_height,
                              antenna_width, antenna_height)
        painter.drawRect(left_antenna)
        
        # Правая антенна
        right_antenna = QRectF(router_rect.left() + router_rect.width() * 0.75 - antenna_width / 2,
                              router_rect.top() - antenna_height,
                              antenna_width, antenna_height)
        painter.drawRect(right_antenna)
        
        # Индикаторы на панели (светодиоды)
        painter.setBrush(highlight_color)
        led_size = 3
        led_y = top_panel.top() + top_panel.height() / 2 - led_size / 2
        
        # Несколько индикаторов в ряд
        for i in range(4):
            led_x = top_panel.left() + 4 + i * (led_size + 3)
            painter.drawEllipse(QRectF(led_x, led_y, led_size, led_size))
        
        # Порты
        port_height = 4
        port_spacing = 2
        port_width = router_rect.width() * 0.15
        port_y = router_rect.bottom() - port_height - 2
        
        painter.setBrush(QColor(30, 30, 30))
        
        # Рисуем несколько портов в ряд
        for i in range(4):
            port_x = router_rect.left() + 4 + i * (port_width + port_spacing)
            painter.drawRect(QRectF(port_x, port_y, port_width, port_height))
        
        # Восстанавливаем состояние художника
        painter.restore()

    def _draw_router_virtual(self, painter, rect):
        """
        Отрисовка виртуального маршрутизатора
        """
        # Сохраняем текущее состояние художника
        painter.save()
        
        # Цвета для виртуального маршрутизатора
        body_color = QColor(142, 68, 173)  # Фиолетовый для виртуальных устройств
        detail_color = QColor(120, 50, 150)
        highlight_color = QColor(236, 240, 241)
        
        # Добавляем пунктирный контур для обозначения виртуальности
        pen = QPen(QColor(142, 68, 173), 1, Qt.DashLine)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(-3, -3, 3, 3), 8, 8)
        
        # Основная форма маршрутизатора (прямоугольник с закругленными углами)
        painter.setBrush(body_color)
        painter.setPen(Qt.NoPen)
        router_rect = rect.adjusted(2, 2, -2, -2)
        painter.drawRoundedRect(router_rect, 6, 6)
        
        # Детали маршрутизатора
        painter.setBrush(detail_color)
        
        # Верхняя панель
        top_panel = QRectF(router_rect.left() + 2, router_rect.top() + 2,
                           router_rect.width() - 4, router_rect.height() / 5)
        painter.drawRoundedRect(top_panel, 3, 3)
        
        # Индикаторы на панели (светодиоды)
        painter.setBrush(highlight_color)
        led_size = 3
        led_y = top_panel.top() + top_panel.height() / 2 - led_size / 2
        
        # Несколько индикаторов в ряд
        for i in range(3):
            led_x = top_panel.left() + 4 + i * (led_size + 3)
            painter.drawEllipse(QRectF(led_x, led_y, led_size, led_size))
        
        # Значок "V" для обозначения виртуальности
        font = painter.font()
        font.setPointSize(8)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(highlight_color)
        painter.drawText(router_rect, Qt.AlignCenter, "V")
        
        # Восстанавливаем состояние художника
        painter.restore()
    
    def _draw_connections(self, painter, positions):
        """
        Рисует соединения между устройствами простыми линиями
        """
        if not self.connections:
            return
        
        # Устанавливаем стиль линий
        pen = QPen(self.colors["connection"], 1.5)  # Уменьшаем толщину линий
        pen.setStyle(Qt.SolidLine)  # Сплошная линия
        painter.setPen(pen)
        
        # Рисуем линии соединений
        for connection in self.connections:
            if connection["from"] in positions and connection["to"] in positions:
                start_pos = positions[connection["from"]]
                end_pos = positions[connection["to"]]
                painter.drawLine(start_pos, end_pos)
    
    def _draw_router(self, painter, rect):
        """
        Рисует маршрутизатор с улучшенной визуализацией
        """
        # Создаем эффект тени
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 5, 5)
        
        # Создаем градиент для заливки
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, self.colors["router_fill"].lighter(110))
        gradient.setColorAt(1, self.colors["router_fill"])
        
        # Рисуем основной прямоугольник
        painter.setBrush(gradient)
        painter.setPen(QPen(self.colors["router_border"], 2))
        painter.drawRoundedRect(rect, 5, 5)
        
        # Рисуем антенны
        antenna_width = 3
        antenna_height = rect.height() * 0.3
        
        # Позиция для первой антенны
        x1 = rect.x() + rect.width() * 0.25 - antenna_width / 2
        y1 = rect.y() - antenna_height
        
        # Позиция для второй антенны
        x2 = rect.x() + rect.width() * 0.75 - antenna_width / 2
        y2 = rect.y() - antenna_height
        
        # Рисуем антенны
        painter.setBrush(self.colors["router_accent"])
        
        # Первая антенна
        antenna1_rect = QRectF(x1, y1, antenna_width, antenna_height)
        painter.drawRect(antenna1_rect)
        
        # Вторая антенна
        antenna2_rect = QRectF(x2, y2, antenna_width, antenna_height)
        painter.drawRect(antenna2_rect)
        
        # Рисуем верхнюю часть антенн
        antenna1_top_rect = QRectF(x1 - 5, y1, 10, 3)
        painter.drawRect(antenna1_top_rect)
        
        antenna2_top_rect = QRectF(x2 - 5, y2, 10, 3)
        painter.drawRect(antenna2_top_rect)
        
        # Рисуем индикаторы
        indicator_size = rect.width() * 0.1
        indicator_y = rect.y() + rect.height() * 0.8
        
        # Зеленый индикатор
        painter.setBrush(QColor(50, 205, 50))
        green_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.25 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(green_indicator_rect)
        
        # Желтый индикатор
        painter.setBrush(QColor(255, 215, 0))
        yellow_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.5 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(yellow_indicator_rect)
        
        # Красный индикатор
        painter.setBrush(QColor(220, 20, 60))
        red_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.75 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(red_indicator_rect)
    
    def _draw_switch(self, painter, rect):
        """
        Рисует коммутатор с улучшенной визуализацией
        """
        # Создаем эффект тени
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 5, 5)
        
        # Создаем градиент для заливки
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, self.colors["switch_fill"].lighter(110))
        gradient.setColorAt(1, self.colors["switch_fill"])
        
        # Рисуем основной прямоугольник
        painter.setBrush(gradient)
        painter.setPen(QPen(self.colors["switch_border"], 2))
        painter.drawRoundedRect(rect, 5, 5)
        
        # Рисуем порты коммутатора
        port_width = rect.width() * 0.12
        port_height = rect.height() * 0.15
        port_spacing = (rect.width() - 6 * port_width) / 7
        port_y = rect.y() + rect.height() * 0.7
        
        # Рисуем порты
        painter.setBrush(QColor(30, 30, 30))
        for i in range(6):
            port_x = rect.x() + port_spacing + i * (port_width + port_spacing)
            port_rect = QRectF(port_x, port_y, port_width, port_height)
            painter.drawRect(port_rect)
        
        # Рисуем индикаторы
        indicator_size = rect.width() * 0.08
        indicator_y = rect.y() + rect.height() * 0.3
        
        # Зеленый индикатор
        painter.setBrush(QColor(50, 205, 50))
        green_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.25 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(green_indicator_rect)
        
        # Оранжевый индикатор
        painter.setBrush(QColor(255, 165, 0))
        orange_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.5 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(orange_indicator_rect)
        
        # Синий индикатор
        painter.setBrush(QColor(30, 144, 255))
        blue_indicator_rect = QRectF(
            rect.x() + rect.width() * 0.75 - indicator_size/2, 
            indicator_y, 
            indicator_size, 
            indicator_size
        )
        painter.drawEllipse(blue_indicator_rect)
    
    def _draw_computer(self, painter, rect, is_same_subnet):
        """
        Рисует компьютер с улучшенной визуализацией
        """
        # Выбираем оттенок синего в зависимости от подсети
        if is_same_subnet:
            # Для устройств из текущей подсети используем стандартный синий
            computer_fill = self.colors["computer_fill"]
            computer_border = self.colors["computer_border"]
        else:
            # Для устройств из других подсетей используем более светлый оттенок синего
            computer_fill = QColor(150, 200, 255)  # Светло-синий для других подсетей
            computer_border = QColor(100, 170, 240)
            
        # Создаем эффект тени
        shadow_rect = rect.adjusted(2, 2, 2, 2)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 3, 3)
        
        # Размеры монитора и системного блока
        monitor_width = rect.width() * 0.75
        monitor_height = rect.height() * 0.46
        monitor_x = rect.x() + (rect.width() - monitor_width) / 2
        monitor_y = rect.y() + rect.height() * 0.15
        
        base_width = rect.width() * 0.35
        base_height = rect.height() * 0.35
        base_x = rect.x() + (rect.width() - base_width) / 2
        base_y = rect.y() + rect.height() * 0.61
        
        # Градиенты для монитора и системного блока
        monitor_gradient = QLinearGradient(
            monitor_x, monitor_y, 
            monitor_x + monitor_width, monitor_y + monitor_height
        )
        monitor_gradient.setColorAt(0, computer_fill.lighter(110))
        monitor_gradient.setColorAt(1, computer_fill)
        
        base_gradient = QLinearGradient(
            base_x, base_y, 
            base_x + base_width, base_y + base_height
        )
        base_gradient.setColorAt(0, computer_fill.lighter(105))
        base_gradient.setColorAt(1, computer_fill)
        
        # Рисуем монитор
        painter.setBrush(monitor_gradient)
        painter.setPen(QPen(computer_border, 1.5))
        monitor_rect = QRectF(monitor_x, monitor_y, monitor_width, monitor_height)
        painter.drawRoundedRect(monitor_rect, 2, 2)
        
        # Рисуем экран внутри монитора
        screen_margin = 2
        screen_rect = monitor_rect.adjusted(screen_margin, screen_margin, -screen_margin, -screen_margin)
        
        # Градиент для экрана
        screen_gradient = QLinearGradient(
            screen_rect.x(), screen_rect.y(),
            screen_rect.x() + screen_rect.width(), screen_rect.y() + screen_rect.height()
        )
        screen_gradient.setColorAt(0, QColor(220, 240, 255))
        screen_gradient.setColorAt(1, QColor(190, 220, 255))
        
        painter.setBrush(screen_gradient)
        painter.setPen(QPen(computer_border.darker(110), 1))
        painter.drawRect(screen_rect)
        
        # Рисуем подставку монитора
        stand_width = monitor_width * 0.2
        stand_height = rect.height() * 0.04
        stand_x = monitor_x + (monitor_width - stand_width) / 2
        stand_y = monitor_y + monitor_height
        
        painter.setBrush(computer_border)
        painter.setPen(Qt.NoPen)
        painter.drawRect(QRectF(stand_x, stand_y, stand_width, stand_height))
        
        # Рисуем системный блок
        painter.setBrush(base_gradient)
        painter.setPen(QPen(computer_border, 1.5))
        base_rect = QRectF(base_x, base_y, base_width, base_height)
        painter.drawRoundedRect(base_rect, 2, 2)
        
        # Добавляем дисковод и кнопки на системном блоке
        drive_width = base_width * 0.7
        drive_height = base_height * 0.1
        drive_x = base_x + (base_width - drive_width) / 2
        drive_y = base_y + base_height * 0.2
        
        painter.setBrush(QColor(210, 210, 210))
        painter.setPen(QPen(QColor(150, 150, 150), 0.5))
        painter.drawRect(QRectF(drive_x, drive_y, drive_width, drive_height))
        
        # Кнопка питания
        button_size = base_width * 0.12
        button_x = base_x + base_width * 0.75
        button_y = base_y + base_height * 0.05
        
        button_gradient = QRadialGradient(
            button_x + button_size/2, button_y + button_size/2, button_size/2
        )
        
        # Индикатор будет зеленым для устройств из той же подсети
        # и серым для устройств из других подсетей
        if is_same_subnet:
            button_color = QColor(20, 200, 20)  # Зеленый для устройств из той же подсети
        else:
            button_color = QColor(200, 200, 200)  # Серый для устройств из других подсетей
            
        button_gradient.setColorAt(0, button_color.lighter(150))
        button_gradient.setColorAt(1, button_color)
        
        painter.setBrush(button_gradient)
        painter.setPen(QPen(QColor(80, 80, 80), 0.5))
        painter.drawEllipse(QRectF(button_x, button_y, button_size, button_size))
    
    def _draw_other_device(self, painter, rect):
        """
        Рисует другое устройство с улучшенной визуализацией (прежняя версия)
        """
        # Создаем эффект тени
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 10, 10)
        
        # Создаем градиент для заливки
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, QColor(41, 128, 185)) # Более яркий синий цвет
        gradient.setColorAt(1, QColor(52, 152, 219)) # Основной синий цвет
        
        # Рисуем основной прямоугольник
        painter.setBrush(gradient)
        painter.setPen(QPen(QColor(36, 113, 163), 2))
        painter.drawRoundedRect(rect, 10, 10)
        
        # Добавляем блики на устройстве
        highlight = QLinearGradient(rect.topLeft(), QPointF(rect.right(), rect.top()))
        highlight.setColorAt(0, QColor(255, 255, 255, 80))
        highlight.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setBrush(highlight)
        painter.setPen(Qt.NoPen)
        highlight_rect = QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.3)
        painter.drawRoundedRect(highlight_rect, 8, 8)
        
        # Добавляем индикатор
        led_size = rect.width() * 0.15
        painter.setBrush(QColor(46, 204, 113))
        painter.setPen(QPen(QColor(39, 174, 96), 1))
        led_rect = QRectF(
            rect.right() - led_size - 5, 
            rect.top() + 5, 
            led_size, 
            led_size
        )
        painter.drawEllipse(led_rect)

    def set_data(self, devices, gateway=None):
        """
        Устанавливаем данные для отображения
        """
        if not devices:
            return
        
        self.devices = devices
        
        # Ищем маршрутизатор среди устройств
        self.router = None
        for device in self.devices:
            if device.get("Тип") == "Маршрутизатор":
                self.router = device
                break
        
        # Устанавливаем соединения между устройствами
        self.connections = []
        
        # Если есть маршрутизатор, все устройства соединяем с ним
        if self.router:
            router_ip = self.router["IP"] if isinstance(self.router["IP"], str) else self.router["IP"][0]
            for device in self.devices:
                if device != self.router:  # Не соединяем маршрутизатор с самим собой
                    device_ip = device["IP"] if isinstance(device["IP"], str) else device["IP"][0]
                    self.connections.append({
                        "from": router_ip,
                        "to": device_ip
                    })
        else:
            # Если нет маршрутизатора, соединяем все устройства каждое с каждым
            for i, device1 in enumerate(self.devices):
                device1_ip = device1["IP"] if isinstance(device1["IP"], str) else device1["IP"][0]
                for j, device2 in enumerate(self.devices[i+1:], i+1):
                    device2_ip = device2["IP"] if isinstance(device2["IP"], str) else device2["IP"][0]
                    self.connections.append({
                        "from": device1_ip,
                        "to": device2_ip
                    })
        
        # Рассчитываем позиции устройств
        self._calculate_positions()
        
        # Перерисовываем сцену
        self.update()

    def _calculate_positions(self, width=None, height=None):
        """
        Равномерное распределение устройств по окружности с маршрутизатором в центре
        """
        positions = {}
        
        # Если width и height не переданы, используем размеры виджета
        if width is None:
            width = self.width() / self.scale
        if height is None:
            height = self.height() / self.scale
        
        # Определяем центр области отображения
        center_x = width / 2
        center_y = height / 2
        
        # Сначала размещаем маршрутизатор в центре
        if self.router:
            router_ip = self.router["IP"]
            if isinstance(router_ip, list):
                router_ip = router_ip[0]
            positions[router_ip] = QPointF(center_x, center_y)
        
        # Находим все остальные устройства (не маршрутизатор)
        other_devices = [d for d in self.devices if d != self.router]
        
        # Равномерно распределяем остальные устройства по окружности
        if other_devices:
            # Увеличиваем радиус для большего расстояния между устройствами
            radius = min(width, height) * 0.4
            
            # Вычисляем угол между устройствами
            angle_step = 2 * math.pi / len(other_devices)
            
            # Начинаем с верхней точки окружности
            start_angle = -math.pi / 2
            
            for i, device in enumerate(other_devices):
                # Вычисляем угол для текущего устройства
                angle = start_angle + i * angle_step
                
                # Вычисляем координаты
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
                
                # Получаем IP для позиционирования
                device_ip = device["IP"]
                if isinstance(device_ip, list):
                    device_ip = device_ip[0]
                
                positions[device_ip] = QPointF(x, y)
        
        return positions
    
    def _find_device_at_pos(self, pos):
        """
        Находит устройство в заданной позиции
        """
        # Рассчитываем позиции устройств
        width = self.width() / self.scale
        height = self.height() / self.scale
        positions = self._calculate_positions(width, height)
        
        # Проверяем каждое устройство
        for device in self.devices:
            device_ip = device["IP"]
            if isinstance(device_ip, list):
                device_ip = device_ip[0]  # Используем первый IP для позиционирования
            
            if device_ip in positions:
                device_pos = positions[device_ip]
                scaled_pos = QPointF(
                    device_pos.x() * self.scale + self.offset_x,
                    device_pos.y() * self.scale + self.offset_y
                )
                
                # Проверяем, находится ли позиция в пределах иконки устройства
                rect = QRectF(
                    scaled_pos.x() - self.base_icon_size / 2,
                    scaled_pos.y() - self.base_icon_size / 2,
                    self.base_icon_size,
                    self.base_icon_size
                )
                
                if rect.contains(pos):
                    return device
        
        return None
    
    def reset_view(self):
        """
        Сбрасывает масштаб и положение к исходным значениям
        """
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.selected_device = None
        self.update()
    
    def _generate_device_tooltip(self, device):
        """
        Создает улучшенную подсказку для устройства
        """
        # Определяем цвет заголовка на основе типа устройства
        if device["Тип"] == "Маршрутизатор":
            header_color = "#e74c3c"
        elif device["Тип"] == "Коммутатор":
            header_color = "#3498db"
        elif device["Тип"] == "Локальный компьютер":
            header_color = "#2980b9"
        else:
            header_color = "#2ecc71"
        
        # Преобразуем IP-адреса в строку
        ip_text = ", ".join(device["IP"]) if isinstance(device["IP"], list) else str(device["IP"])
        
        # Определяем принадлежность к подсети
        subnet = device.get("Подсеть", "Неизвестно")
        is_same_subnet = device.get("СамаяПодсеть", True)
        
        # Определяем цвет и сообщение о подсети
        if is_same_subnet:
            subnet_color = "#4caf50"  # Зеленый для текущей подсети
            subnet_message = "Текущая подсеть"
        else:
            subnet_color = "#ff9800"  # Оранжевый для другой подсети
            subnet_message = "Другая подсеть"
        
        # Специальная обработка для виртуальных интерфейсов маршрутизатора
        special_info = ""
        
        # Список виртуальных интерфейсов с пояснениями
        virtual_interfaces = {
            "192.168.204.254": "Этот IP-адрес может представлять виртуальный интерфейс маршрутизатора для подсети 192.168.204.0/24, а не отдельное физическое устройство.",
            "192.168.10.254": "Этот IP-адрес может представлять виртуальный интерфейс маршрутизатора для подсети 192.168.10.0/24, а не отдельное физическое устройство."
        }
        
        # Проверяем, является ли IP виртуальным интерфейсом
        for virtual_ip, description in virtual_interfaces.items():
            if ip_text == virtual_ip:
                special_info = f"""
                <tr>
                    <td colspan="2" style="padding: 6px; text-align: left; 
                                         background-color: #f3e5f5; 
                                         color: #7b1fa2; border-radius: 3px; 
                                         margin-top: 5px; font-style: italic;">
                        <b>Примечание:</b> {description}
                    </td>
                </tr>
                """
                break
        
        # Собираем HTML для подсказки
        html = f"""
        <div style="min-width: 250px; padding: 8px;">
            <div style="background-color: {header_color}; padding: 4px; color: white; 
                       font-weight: bold; border-radius: 3px; margin-bottom: 5px;">
                {device["Тип"]}
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 3px; color: #666;">IP:</td>
                    <td style="padding: 3px;">{ip_text}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; color: #666;">MAC:</td>
                    <td style="padding: 3px;">{device["MAC"]}</td>
                </tr>
                <tr>
                    <td style="padding: 3px; color: #666;">Подсеть:</td>
                    <td style="padding: 3px;">{subnet}</td>
                </tr>
                <tr>
                    <td colspan="2" style="padding: 3px; text-align: center; 
                                         background-color: {subnet_color}; 
                                         color: white; border-radius: 3px;">
                        {subnet_message}
                    </td>
                </tr>
                {special_info}
            </table>
        </div>
        """
        return html
    
    def mousePressEvent(self, event):
        """
        Обработка нажатия кнопки мыши
        """
        if event.button() == Qt.LeftButton:
            # Проверяем, кликнули ли по устройству
            clicked_device = self._find_device_at_pos(event.pos())
            
            if clicked_device:
                # Устанавливаем выделенное устройство
                self.selected_device = clicked_device
                self.update()
            else:
                # Начинаем перетаскивание
                self.dragging = True
                self.last_mouse_pos = event.pos()
                self.setCursor(Qt.ClosedHandCursor)
    
    def mouseReleaseEvent(self, event):
        """
        Обработка отпускания кнопки мыши
        """
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(Qt.ArrowCursor)
    
    def mouseMoveEvent(self, event):
        """
        Обработка движения мыши
        """
        # Обрабатываем перетаскивание
        if self.dragging and self.last_mouse_pos:
            delta = event.pos() - self.last_mouse_pos
            self.offset_x += delta.x()
            self.offset_y += delta.y()
            self.last_mouse_pos = event.pos()
            self.update()
        
        # Обновляем устройство, на которое наведен курсор
        hovered_device = self._find_device_at_pos(event.pos())
        
        if hovered_device != self.hover_device:
            self.hover_device = hovered_device
            self.update()
            
            # Показываем всплывающую подсказку
            if hovered_device:
                QToolTip.showText(
                    event.globalPos(),
                    self._generate_device_tooltip(hovered_device),
                    self
                )
            else:
                QToolTip.hideText()
    
    def wheelEvent(self, event):
        """
        Обработка прокрутки колеса мыши - отключена
        """
        # Игнорируем событие колеса мыши
        event.ignore()

    def keyPressEvent(self, event):
        """
        Обработка нажатий клавиш
        """
        # Проверяем, нажата ли клавиша Ctrl
        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_Plus:  # Для увеличения масштаба
                self._zoom(1.1)
            elif event.key() == Qt.Key_Minus:  # Для уменьшения масштаба
                self._zoom(0.9)
        event.accept()

    def _zoom(self, factor):
        """
        Изменение масштаба с заданным коэффициентом
        """
        # Получаем центр виджета
        center = self.rect().center()
        
        # Точка под курсором в исходной системе координат
        old_pos_x = (center.x() - self.offset_x) / self.scale
        old_pos_y = (center.y() - self.offset_y) / self.scale
        
        # Вычисляем новый масштаб
        new_scale = self.scale * factor
        
        # Ограничиваем масштаб
        new_scale = max(0.2, min(5.0, new_scale))
        
        if new_scale != self.scale:
            # Устанавливаем новый масштаб
            self.scale = new_scale
            
            # Точка под курсором в новой системе координат
            new_pos_x = old_pos_x * self.scale
            new_pos_y = old_pos_y * self.scale
            
            # Корректируем смещение, чтобы центр остался на месте
            self.offset_x = center.x() - new_pos_x
            self.offset_y = center.y() - new_pos_y
            
            self.update()

    def _draw_virtual_interface(self, painter, rect):
        """
        Рисует устройство, представляющее виртуальный сетевой интерфейс
        """
        # Выбираем фиолетовый цвет для виртуального интерфейса
        virtual_fill = QColor(156, 39, 176)  # Фиолетовый
        virtual_border = QColor(123, 31, 162)  # Темно-фиолетовый
        
        # Создаем эффект тени
        shadow_rect = rect.adjusted(2, 2, 2, 2)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(shadow_rect, 8, 8)
        
        # Создаем градиент для основного прямоугольника
        gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0, virtual_fill.lighter(115))
        gradient.setColorAt(1, virtual_fill)
        
        # Рисуем основной прямоугольник с закругленными углами
        painter.setBrush(gradient)
        painter.setPen(QPen(virtual_border, 2))
        painter.drawRoundedRect(rect, 8, 8)
        
        # Рисуем узор, напоминающий сетевой интерфейс
        # Горизонтальные линии для коннекторов
        line_margin = rect.width() * 0.2
        line_width = rect.width() - 2 * line_margin
        line_count = 3
        line_spacing = rect.height() * 0.6 / (line_count + 1)
        line_y_start = rect.y() + rect.height() * 0.3
        
        painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
        
        for i in range(line_count):
            line_y = line_y_start + i * line_spacing
            painter.drawLine(
                QPointF(rect.x() + line_margin, line_y),
                QPointF(rect.x() + line_margin + line_width, line_y)
            )
        
        # Добавляем символ "виртуальности" (V)
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1))
        
        # Рисуем букву V в центре
        painter.drawText(
            QRectF(rect.x(), rect.y(), rect.width(), rect.height() * 0.3),
            Qt.AlignCenter,
            "V"
        )

    def _draw_local_computer(self, painter, rect):
        """
        Рисует локальный компьютер (наш компьютер) с особым дизайном
        """
        # Сохраняем текущее состояние художника
        painter.save()
        
        # Создаем эффект тени
        shadow_rect = rect.adjusted(3, 3, 3, 3)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.setPen(Qt.NoPen)
        painter.drawRect(shadow_rect)
        
        # Размеры монитора
        monitor_width = rect.width() * 0.8
        monitor_height = rect.height() * 0.6
        monitor_x = rect.x() + (rect.width() - monitor_width) / 2
        monitor_y = rect.y()
        
        # Размеры подставки
        base_width = rect.width() * 0.4
        base_height = rect.height() * 0.1
        base_x = rect.x() + (rect.width() - base_width) / 2
        base_y = rect.y() + monitor_height + rect.height() * 0.1
        
        # Размеры ножки
        stand_width = rect.width() * 0.1
        stand_height = rect.height() * 0.1
        stand_x = rect.x() + (rect.width() - stand_width) / 2
        stand_y = rect.y() + monitor_height
        
        # Используем синий цвет для локального компьютера
        local_computer_color = QColor(30, 144, 255)  # Синий цвет
        local_computer_border = QColor(25, 118, 210)  # Темно-синий для границ
        
        # Рисуем подставку
        base_gradient = QLinearGradient(base_x, base_y, base_x + base_width, base_y + base_height)
        base_gradient.setColorAt(0, local_computer_border.lighter(120))
        base_gradient.setColorAt(1, local_computer_border)
        
        painter.setBrush(base_gradient)
        painter.setPen(QPen(local_computer_border.darker(120), 1))
        base_rect = QRectF(base_x, base_y, base_width, base_height)
        painter.drawRoundedRect(base_rect, 2, 2)
        
        # Рисуем ножку
        painter.setBrush(local_computer_border)
        painter.drawRect(QRectF(stand_x, stand_y, stand_width, stand_height))
        
        # Рисуем монитор с градиентом
        monitor_gradient = QLinearGradient(monitor_x, monitor_y, monitor_x + monitor_width, monitor_y + monitor_height)
        monitor_gradient.setColorAt(0, local_computer_color.lighter(110))
        monitor_gradient.setColorAt(1, local_computer_color)
        
        painter.setBrush(monitor_gradient)
        painter.setPen(QPen(local_computer_border, 2))
        monitor_rect = QRectF(monitor_x, monitor_y, monitor_width, monitor_height)
        painter.drawRoundedRect(monitor_rect, 5, 5)
        
        # Рисуем экран
        screen_margin = 5
        screen_x = monitor_x + screen_margin
        screen_y = monitor_y + screen_margin
        screen_width = monitor_width - 2 * screen_margin
        screen_height = monitor_height - 2 * screen_margin
        
        # Градиент для экрана
        screen_gradient = QRadialGradient(screen_x + screen_width/2, screen_y + screen_height/2, 
                                        screen_width)
        screen_gradient.setColorAt(0, QColor(235, 245, 255))  # Светло-синий для экрана
        screen_gradient.setColorAt(1, QColor(220, 235, 255))
        
        painter.setBrush(screen_gradient)
        painter.setPen(QPen(local_computer_border.darker(120), 1))
        screen_rect = QRectF(screen_x, screen_y, screen_width, screen_height)
        painter.drawRect(screen_rect)
        
        # Восстанавливаем состояние художника
        painter.restore()

class NetworkTopologyTab(QWidget):
    """
    Вкладка с визуализацией топологии сети
    """
    def __init__(self, monitor_thread):
        super().__init__()
        self.monitor_thread = monitor_thread
        self.monitor = self.monitor_thread.monitor
        self.devices = []  # Добавляем список для хранения устройств
        self.init_ui()
        
        # Инициализируем таймер для автоматического обновления
        self.auto_update_timer = QTimer()
        self.auto_update_timer.timeout.connect(self.refresh_data)
        self.auto_update_timer.start(30000)  # Обновляем каждые 30 секунд
        
        # Автоматически определяем локальный IP и шлюз при запуске
        QTimer.singleShot(500, self.initialize_network_info)
    
    def initialize_network_info(self):
        """Инициализирует информацию о сети при запуске"""
        try:
            # Получаем все локальные IP-адреса и информацию об интерфейсах
            local_ips = []
            iface_info = {}
            
            for iface, addrs in psutil.net_if_addrs().items():
                # Пропускаем интерфейсы WSL (обычно содержат "WSL" в имени)
                if "WSL" in iface or "vEthernet" in iface:
                    continue
                    
                for addr in addrs:
                    if addr.family == socket.AF_INET and not self.monitor.is_special_ip(addr.address):
                        local_ips.append(addr.address)
                        iface_info[addr.address] = iface
            
            # Если есть IP-адреса, выбираем наиболее подходящий
            # Предпочитаем интерфейсы Ethernet и Wi-Fi над другими
            preferred_ip = None
            
            # Сначала ищем физические интерфейсы (Ethernet)
            for ip in local_ips:
                iface = iface_info.get(ip, "")
                if "Ethernet" in iface or "eth" in iface.lower() or "LAN" in iface:
                    preferred_ip = ip
                    break
            
            # Если Ethernet не найден, ищем Wi-Fi
            if not preferred_ip:
                for ip in local_ips:
                    iface = iface_info.get(ip, "")
                    if "Wi-Fi" in iface or "wlan" in iface.lower() or "Wireless" in iface:
                        preferred_ip = ip
                        break
            
            # Если ни один предпочтительный не найден, используем первый доступный
            if not preferred_ip and local_ips:
                preferred_ip = local_ips[0]
            
            # Сохраняем локальный IP
            self.monitor.local_ip = preferred_ip if preferred_ip else "Не определен"
            
            # Получаем информацию о шлюзах через улучшенные методы
            primary_gateway_info = self.monitor.get_gateway_info()
            all_gateways = self.monitor.get_all_gateways()
            
            # Сохраняем основной шлюз для обратной совместимости
            self.monitor.gateway = primary_gateway_info.get("IP", "Не определен") if primary_gateway_info else "Не определен"
            
            # Формируем текст для отображения
            gateway_text = ""
            if primary_gateway_info:
                gateway_ip = primary_gateway_info.get('IP', 'Не определен')
                gateway_type = "виртуальный" if primary_gateway_info.get('Виртуальный', False) else "физический"
                gateway_text = f"Основной шлюз: {gateway_ip} ({gateway_type})"
            else:
                gateway_text = "Шлюз: Не определен"
            
            # Добавляем информацию о других шлюзах, если они есть
            other_gateways = []
            for gw in all_gateways:
                if primary_gateway_info and gw["gateway"] != primary_gateway_info.get('IP'):
                    gw_type = "виртуальный" if gw["is_virtual"] else "физический"
                    other_gateways.append(f"{gw['gateway']} ({gw_type})")
            
            if other_gateways:
                gateway_text += f" | Другие шлюзы: {', '.join(other_gateways)}"
            
            # Обновляем информацию на экране
            self.network_info.setText(f"{self.monitor.local_ip} | {gateway_text}")
            
            # Запускаем обновление устройств
            self.update_devices_info()
        except Exception as e:
            logging.error(f"Ошибка при инициализации информации о сети: {str(e)}")
    
    def init_ui(self):
        # Основной вертикальный лейаут
        main_layout = QVBoxLayout()
        
        # Верхняя панель с информацией и кнопками
        top_panel = QHBoxLayout()
        
        # Добавляем информацию о локальной сети
        self.network_info = QLabel("-")
        self.network_info.setStyleSheet("font-weight: bold; color: #007ACC;")
        self.network_info.setAlignment(Qt.AlignCenter)
        top_panel.addWidget(self.network_info)
        
        # Добавляем настройку фильтрации подсетей
        self.show_only_local_subnet = QCheckBox("Только текущая подсеть")
        self.show_only_local_subnet.setChecked(False)  # По умолчанию показываем все устройства
        self.show_only_local_subnet.setStyleSheet("""
            QCheckBox {
                color: #2196F3;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #c0c8e0;
                background-color: white;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #2196F3;
                background-color: #2196F3;
                border-radius: 4px;
            }
        """)
        self.show_only_local_subnet.toggled.connect(self.update_devices_info)
        top_panel.addWidget(self.show_only_local_subnet)
        
        # Добавляем кнопки для управления
        scan_button = QPushButton("Сканировать сеть")
        scan_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        scan_button.clicked.connect(self.scan_network)
        top_panel.addWidget(scan_button)
        
        # Кнопка обновления
        refresh_button = QPushButton("Вернуть в исходное положение")
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        refresh_button.setToolTip("Возвращает топологию сети в исходное положение")
        refresh_button.clicked.connect(self.reset_view)  # Меняем функцию с refresh_data на reset_view
        top_panel.addWidget(refresh_button)
        
        # Убираем кнопку сброса масштаба, так как она больше не актуальна
        
        main_layout.addLayout(top_panel)
        
        # Создаем горизонтальный сплиттер для содержимого
        content_splitter = QSplitter(Qt.Horizontal)
        
        # Левая часть - холст топологии сети
        self.topology_canvas = NetworkTopologyCanvas()
        content_splitter.addWidget(self.topology_canvas)
        
        # Правая часть - таблица устройств
        devices_widget = QWidget()
        devices_layout = QVBoxLayout()
        devices_layout.setContentsMargins(0, 0, 0, 0)
        
        # Заголовок для таблицы устройств
        devices_label = QLabel("Устройства в сети")
        devices_label.setStyleSheet("font-weight: bold; margin-bottom: 5px;")
        devices_layout.addWidget(devices_label)
        
        # Таблица устройств
        self.devices_table = QTableWidget(0, 3)
        self.devices_table.setHorizontalHeaderLabels(["IP адрес", "MAC адрес", "Тип"])
        self.devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.devices_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.devices_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
            QTableWidget::item:selected {
                background-color: #e6f3ff;
                color: #000;
            }
            QHeaderView::section {
                background-color: #f2f2f2;
                border: 1px solid #ddd;
                padding: 5px;
                font-weight: bold;
            }
        """)
        devices_layout.addWidget(self.devices_table)
        
        devices_widget.setLayout(devices_layout)
        content_splitter.addWidget(devices_widget)
        
        # Устанавливаем размеры сплиттера (60% для топологии, 40% для таблицы)
        content_splitter.setSizes([int(self.width() * 0.6), int(self.width() * 0.4)])
        
        main_layout.addWidget(content_splitter)
        
        self.setLayout(main_layout)
        
        # Инициализируем данные
        self.update_devices_info()
        
        # Заменяем стандартный QProgressBar на наш анимированный
        self.scan_progress = AnimatedProgressBar()
        self.scan_progress.setVisible(False)
        main_layout.addWidget(self.scan_progress)
        
        # Добавляем таймер для проверки статуса сканирования
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.update_scan_progress)
        
        # Флаг для отслеживания процесса сканирования
        self.is_scanning = False
        
        # Для хранения потока сканирования
        self.scan_thread = None
    
    def refresh_data(self, event=None):
        """
        Обновление данных о сети
        """
        self.update_devices_info()
    
    def reset_view(self, event=None):
        """
        Сброс масштаба и позиции топологии
        """
        self.topology_canvas.reset_view()
    
    def scan_network(self):
        """
        Выполняет сканирование сети в отдельном потоке
        """
        if self.is_scanning:
            # Если сканирование уже идет, ничего не делаем
            return
            
        self.network_info.setText("Сканирование сети... (может занять до минуты)")
        self.scan_progress.setVisible(True)
        self.is_scanning = True
        
        # Сохраняем время начала сканирования для контроля таймаута
        self.scan_start_time = time.time()
        
        # Запускаем сканирование в отдельном потоке
        self.scan_thread = threading.Thread(target=self._scan_network_thread)
        self.scan_thread.daemon = True
        self.scan_thread.start()
        
        # Запускаем таймер для обновления прогресса
        self.scan_timer.start(150)  # Обновляем реже для уменьшения нагрузки
    
    def update_scan_progress(self):
        """
        Проверяет, завершено ли сканирование
        """
        if not self.is_scanning:
            self.scan_timer.stop()
            self.scan_progress.setVisible(False)
            return
            
        # Проверяем таймаут сканирования (2 минуты максимум)
        current_time = time.time()
        elapsed_time = current_time - self.scan_start_time
        max_scan_time = 120  # 2 минуты
        
        # Если поток сканирования завершился или прошло слишком много времени
        if not self.scan_thread.is_alive() or elapsed_time > max_scan_time:
            self.is_scanning = False
            
            if elapsed_time > max_scan_time:
                # Если сканирование заняло слишком много времени, выводим сообщение
                self.network_info.setText("Сканирование прервано из-за превышения времени ожидания")
            
            # Устанавливаем состояние "завершено" для прогресс-индикатора
            self.scan_progress.setCompleted(True)
            
            # Запускаем обновление интерфейса с небольшой задержкой для предотвращения фризов
            QTimer.singleShot(200, self.update_devices_info)
            
            # Останавливаем таймер обновления прогресса
            self.scan_timer.stop()
            
            # Скрываем прогресс-индикатор через 0.5 секунды после завершения
            QTimer.singleShot(500, lambda: self.scan_progress.setVisible(False))
    
    def _scan_network_thread(self):
        """
        Функция для сканирования сети в отдельном потоке
        """
        try:
            # Для хранения состояния сканирования
            if not hasattr(self.monitor, 'scan_state'):
                self.monitor.scan_state = {
                    'subnet_index': 0,
                    'batch': 1,
                    'completed': False
                }
            
            # Если предыдущее сканирование не завершено, продолжаем с места остановки
            start_subnet_index = self.monitor.scan_state['subnet_index']
            start_batch = self.monitor.scan_state['batch']
            
            # Запоминаем количество ранее обнаруженных устройств
            prev_count = len(getattr(self.monitor, 'discovered_devices', {}))
            
            # Сканируем сеть с учетом сохраненного состояния
            devices, completed = self.monitor.scan_network(
                start_subnet_index=start_subnet_index,
                start_batch=start_batch
            )
            
            # Если устройств не обнаружено или их очень мало, пробуем альтернативные методы
            if len(devices) < 2:  # Только локальный компьютер или пусто
                try:
                    # Попытка использовать альтернативное сканирование даже в случае завершенного обычного
                    alt_devices = self.monitor._scan_network_alternative()
                    # Добавляем только новые устройства
                    for ip, device_info in alt_devices.items():
                        if ip not in devices:
                            devices[ip] = device_info
                except Exception as e:
                    # Игнорируем ошибки при альтернативном сканировании
                    logging.error(f"Ошибка при альтернативном сканировании: {str(e)}")
            
            # Обновляем состояние сканирования для возможного продолжения
            if not completed:
                # Если не завершено - сохраняем текущее состояние для следующего запуска
                # Обновляем значения в scan_state, но не сбрасываем их
                self.monitor.scan_state = {
                    'subnet_index': self.monitor.current_subnet_index,
                    'batch': self.monitor.current_batch,
                    'completed': completed
                }
            else:
                # Если сканирование завершено - сбрасываем состояние
                self.monitor.scan_state = {
                    'subnet_index': 0,
                    'batch': 1,
                    'completed': True
                }
            
            # Сбрасываем ошибку, если она была раньше
            self.monitor.scan_error = None
            
            # Если не обнаружено новых устройств, выводим информационное сообщение
            if len(devices) <= prev_count and len(devices) <= 2:
                self.monitor.scan_info = "Мало устройств обнаружено. Возможно, в сети настроены ограничения."
            else:
                self.monitor.scan_info = None
            
            # Отправляем событие в основной поток для обновления интерфейса
            QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))
        except Exception as e:
            # Ошибка при выполнении сканирования
            error_message = f"Ошибка сканирования сети: {str(e)}"
            
            # Записываем ошибку для отображения в интерфейсе
            self.monitor.scan_error = error_message
            
            # Отправляем событие для обновления интерфейса
            QApplication.instance().postEvent(self, QEvent(QEvent.Type.User))
    
    def update_devices_info(self):
        """
        Обновляет информацию об устройствах в сети с улучшенным определением типов
        """
        try:
            # Получаем все локальные IP-адреса
            local_ips = []
            local_macs = {}
            iface_info = {}
            
            for iface, addrs in psutil.net_if_addrs().items():
                # Пропускаем интерфейсы WSL и виртуальные сетевые адаптеры
                if "WSL" in iface or "vEthernet" in iface or "Virtual" in iface:
                    continue
                    
                mac_address = None
                ip_address = None
                
                # Сначала найдем MAC-адрес
                for addr in addrs:
                    if addr.family == psutil.AF_LINK:
                        mac_address = addr.address
                        break
                
                # Теперь найдем соответствующий IP
                for addr in addrs:
                    if addr.family == socket.AF_INET and not self.monitor.is_special_ip(addr.address):
                        ip_address = addr.address
                        local_ips.append(ip_address)
                        iface_info[ip_address] = iface
                        if mac_address:
                            local_macs[ip_address] = mac_address
                        break

            # Получаем информацию о всех шлюзах с улучшенным алгоритмом
            all_gateways = self.monitor.get_all_gateways()
            
            # Получаем основной шлюз через улучшенный метод
            primary_gateway_info = self.monitor.get_gateway_info()
            primary_gateway_ip = primary_gateway_info.get('IP', '') if primary_gateway_info else ''
            
            # Словарь для хранения уникальных устройств
            unique_devices = {}
            
            # Добавляем все шлюзы в список устройств
            for gw in all_gateways:
                gateway_ip = gw["gateway"]
                
                # Проверяем, есть ли информация о MAC-адресе
                gateway_mac = "Не определен"
                
                # Пингуем шлюз для обновления ARP-записи (если еще не пинговали)
                try:
                    subprocess.call(f"ping -n 1 {gateway_ip}", shell=True, 
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except:
                    pass
                
                # Ищем в ARP-таблице
                for entry in self.monitor.get_arp_table():
                    if entry["IP"] == gateway_ip:
                        gateway_mac = entry["MAC"]
                        break
                
                # Определяем производителя по MAC
                vendor = self.monitor._get_mac_vendor(gateway_mac)
                
                # Определяем тип устройства с помощью улучшенного метода
                device_type = self.monitor._determine_device_type(gateway_ip, gateway_mac, True)
                
                unique_devices[gateway_ip] = {
                    'IP': gateway_ip,
                    'MAC': gateway_mac,
                    'Тип': device_type,
                    'Производитель': vendor if vendor else "Неизвестно",
                    'Локальный': False,
                    'Основной': gateway_ip == primary_gateway_ip,  # Отмечаем основной шлюз
                    'Виртуальный': gw["is_virtual"],
                    'Подсеть': self.monitor.get_subnet(gateway_ip),
                    'Название': gw["name"]
                }
            
            # Определяем предпочтительный локальный IP
            preferred_ip = None
            
            # Сначала ищем физические интерфейсы (Ethernet)
            for ip in local_ips:
                iface = iface_info.get(ip, "")
                if "Ethernet" in iface or "eth" in iface.lower() or "LAN" in iface:
                    preferred_ip = ip
                    break
            
            # Если Ethernet не найден, ищем Wi-Fi
            if not preferred_ip:
                for ip in local_ips:
                    iface = iface_info.get(ip, "")
                    if "Wi-Fi" in iface or "wlan" in iface.lower() or "Wireless" in iface:
                        preferred_ip = ip
                        break
            
            # Если ни один предпочтительный не найден, используем первый доступный
            if not preferred_ip and local_ips:
                preferred_ip = local_ips[0]
                
            # Обновляем локальный IP в мониторе
            if preferred_ip:
                self.monitor.local_ip = preferred_ip
            
            # *** Гарантированно добавляем локальный компьютер в список устройств ***
            # Добавляем ВСЕ локальные IP-адреса, но отмечаем предпочтительный
            for ip in local_ips:
                mac = local_macs.get(ip, 'Не определен')
                is_preferred = (ip == preferred_ip)
                
                # Добавляем локальный компьютер в словарь устройств
                unique_devices[ip] = {
                    'IP': ip,
                    'MAC': mac,
                    'Тип': 'Локальный компьютер',
                    'Производитель': 'Ваш компьютер',
                    'Локальный': True,
                    'Предпочтительный': is_preferred,  # Отмечаем предпочтительный IP
                    'Подсеть': self.monitor.get_subnet(ip)
                }
            
            # Получаем ARP таблицу и обнаруженные устройства
            arp_entries = self.monitor.get_arp_table()
            discovered_devices = getattr(self.monitor, 'discovered_devices', {})
            
            # Объединяем устройства из ARP-таблицы и обнаруженные устройства
            all_device_ips = set()
            for entry in arp_entries:
                all_device_ips.add(entry.get('IP', ''))
            
            for ip in discovered_devices:
                all_device_ips.add(ip)
                
            # Перебираем все найденные IP
            for ip in all_device_ips:
                # Пропускаем специальные IP и уже добавленные устройства
                if (not ip or self.monitor.is_special_ip(ip) or ip in unique_devices):
                    continue
                
                # Ищем информацию об устройстве в ARP-таблице
                mac = "Не определен"
                is_local = ip in local_ips
                
                for entry in arp_entries:
                    if entry.get('IP', '') == ip:
                        mac = entry.get('MAC', 'Не определен')
                        break
                
                # Если MAC не найден, проверяем в обнаруженных устройствах
                if mac == "Не определен" and ip in discovered_devices:
                    device_info = discovered_devices[ip]
                    mac = device_info.get('MAC', 'Не определен')
                
                # Проверяем специальные MAC-адреса
                if mac != "Не определен" and self.monitor.is_special_mac(mac):
                    continue
                
                # Определяем тип устройства и производителя
                vendor = self.monitor._get_mac_vendor(mac)
                
                # Определяем тип устройства с помощью улучшенного метода
                device_type = self.monitor._determine_device_type(ip, mac, False)
                
                # Проверяем, находится ли устройство в локальной подсети
                subnet = self.monitor.get_subnet(ip)
                same_subnet = preferred_ip and self.monitor.is_same_subnet(ip, preferred_ip)
                
                # Получаем статус устройства (активно/неактивно)
                status = "Активно"
                if ip in discovered_devices:
                    status = discovered_devices[ip].get('Статус', 'Активно')
                
                # Проверяем, есть ли информация о статусе в истории устройств
                if hasattr(self.monitor, '_devices_history') and ip in self.monitor._devices_history:
                    is_active = self.monitor._devices_history[ip].get('active', True)
                    if not is_active:
                        status = "Неактивно"
                        # Для неактивных устройств добавляем время последней активности в подсказке
                        last_active_time = self.monitor._devices_history[ip].get('last_active', 0)
                        if last_active_time > 0:
                            last_active_str = time.strftime('%H:%M:%S', time.localtime(last_active_time))
                            device_type += f" (последняя активность: {last_active_str})"
                
                unique_devices[ip] = {
                    'IP': ip,
                    'MAC': mac,
                    'Тип': device_type,
                    'Производитель': vendor if vendor else "Неизвестно",
                    'Локальный': is_local,
                    'Подсеть': subnet,
                    'СамаяПодсеть': same_subnet,
                    'Статус': status
                }
            
            # Применяем фильтрацию подсетей, если включена
            filtered_devices = {}
            
            for ip, device in unique_devices.items():
                if self.show_only_local_subnet.isChecked() and preferred_ip:
                    # Если включена фильтрация, добавляем только устройства из той же подсети
                    # и всегда добавляем шлюзы и локальный компьютер
                    if (ip == primary_gateway_ip or 
                        device.get('Тип') in ['Маршрутизатор', 'Коммутатор'] or 
                        device.get('Локальный', False) or 
                        self.monitor.is_same_subnet(ip, preferred_ip)):
                        filtered_devices[ip] = device
                else:
                    # Если фильтрация отключена, добавляем все устройства
                    filtered_devices[ip] = device
            
            # Преобразуем словарь в список для таблицы
            self.devices = list(filtered_devices.values())
            
            # Обновляем информацию о сети в верхней панели
            subnet_text = ""
            if preferred_ip:
                subnet = self.monitor.get_subnet(preferred_ip)
                if subnet:
                    subnet_text = f"Подсеть: {subnet.rstrip('.0')}.x"
            
            gateway_text = f"Основной шлюз: {primary_gateway_ip}" if primary_gateway_ip else "Шлюз не найден"
            
            self.network_info.setText(f"{subnet_text} | {gateway_text}")
            
            # Обновляем таблицу устройств
            self.update_device_table()
            
            # Отображаем устройства в топологии
            self.topology_canvas.set_data(self.devices)
            
        except Exception as e:
            self.network_info.setText(f"Ошибка при обновлении устройств: {str(e)}")
            logging.error(f"Ошибка при обновлении устройств: {str(e)}")

    def event(self, event):
        """
        Обработчик пользовательских событий
        """
        if event.type() == QEvent.Type.User:
            # Проверяем, есть ли ошибка сканирования
            if hasattr(self.monitor, 'scan_error') and self.monitor.scan_error:
                self.network_info.setText(f"Ошибка: {self.monitor.scan_error}")
            elif hasattr(self.monitor, 'scan_info') and self.monitor.scan_info:
                # Отображаем информационное сообщение, если оно есть
                self.network_info.setText(f"Информация: {self.monitor.scan_info}")
            else:
                # Получаем подробную информацию о шлюзах
                primary_gateway_info = self.monitor.get_gateway_info()
                all_gateways = self.monitor.get_all_gateways()
                
                # Формируем текст для отображения
                gateway_text = ""
                if primary_gateway_info:
                    gateway_ip = primary_gateway_info.get('IP', 'Не определен')
                    device_type = primary_gateway_info.get('Тип', 'Маршрутизатор')
                    gateway_text = f"Основной шлюз: {gateway_ip} ({device_type})"
                elif all_gateways:
                    gateway = all_gateways[0]
                    gateway_text = f"Шлюз: {gateway['gateway']}"
                else:
                    gateway_text = "Шлюз не найден"
                
                # Форматируем текст для отображения
                subnet_text = ""
                if hasattr(self.monitor, 'local_ip') and self.monitor.local_ip:
                    subnet = self.monitor.get_subnet(self.monitor.local_ip)
                    if subnet:
                        subnet_text = f"Подсеть: {subnet[:-2]}.x"
                
                # Считаем количество обнаруженных устройств
                devices_count = len(getattr(self.monitor, 'discovered_devices', {}))
                
                # Формируем текст о статусе сети
                if devices_count > 0:
                    devices_text = f"Обнаружено устройств: {devices_count}"
                else:
                    devices_text = "Устройства не обнаружены"
                
                # Объединяем информацию для отображения
                if subnet_text:
                    network_text = f"{subnet_text} | {gateway_text} | {devices_text}"
                else:
                    network_text = f"{gateway_text} | {devices_text}"
                
                self.network_info.setText(network_text)
            
            # Обновляем информацию об устройствах
            self.update_devices_info()
            return True
        
        return super().event(event)

    def update_device_table(self):
        """
        Обновляет таблицу устройств
        """
        # Список виртуальных интерфейсов маршрутизатора
        virtual_interfaces = ["192.168.204.254", "192.168.10.254"]
        
        # Добавляем колонку для подсети и статуса
        if self.devices_table.columnCount() < 5:
            self.devices_table.setColumnCount(5)
            self.devices_table.setHorizontalHeaderLabels(["IP адрес", "MAC адрес", "Тип", "Подсеть", "Статус"])
        
        self.devices_table.setRowCount(len(self.devices))
        
        for row, device in enumerate(self.devices):
            # IP адрес
            ip_text = device['IP'] if isinstance(device['IP'], str) else ', '.join(device['IP'])
            ip_item = QTableWidgetItem(ip_text)
            
            # Специальная обработка для виртуальных интерфейсов
            is_virtual_interface = ip_text in virtual_interfaces
            
            if is_virtual_interface:
                ip_item.setToolTip("Виртуальный интерфейс маршрутизатора")
                # Добавляем светло-фиолетовый фон для выделения
                ip_item.setBackground(QColor(243, 229, 245))  # Светло-фиолетовый
            
            self.devices_table.setItem(row, 0, ip_item)
            
            # MAC адрес
            self.devices_table.setItem(row, 1, QTableWidgetItem(device.get('MAC', 'Н/Д')))
            
            # Тип устройства
            type_item = QTableWidgetItem(device.get('Тип', 'Неизвестно'))
            
            # Если это виртуальный интерфейс, модифицируем тип устройства
            if is_virtual_interface:
                # Определяем подсеть для лучшего описания
                subnet = device.get('Подсеть', '').replace('.0', '')
                type_item = QTableWidgetItem(f"Виртуальный интерфейс ({subnet})")
                type_item.setToolTip(f"Этот IP представляет виртуальный интерфейс маршрутизатора для подсети {subnet}.0/24")
                type_item.setBackground(QColor(243, 229, 245))  # Светло-фиолетовый
            
            self.devices_table.setItem(row, 2, type_item)
            
            # Подсеть
            subnet_item = QTableWidgetItem(device.get('Подсеть', 'Неизвестно'))
            
            # Определяем цвет фона ячейки в зависимости от подсети
            if is_virtual_interface:
                # Для виртуальных интерфейсов используем фиолетовый
                subnet_item.setBackground(QColor(243, 229, 245))
            elif device.get('СамаяПодсеть', True):
                # Устройства из той же подсети с легким синим фоном
                subnet_item.setBackground(QColor(230, 242, 255))
            else:
                # Устройства из других подсетей с легким желтым фоном
                subnet_item.setBackground(QColor(255, 248, 225))
                
            self.devices_table.setItem(row, 3, subnet_item)
            
            # Статус устройства
            status_text = device.get('Статус', 'Активно')
            status_item = QTableWidgetItem(status_text)
            
            # Цветовая кодировка статуса
            if status_text == 'Активно':
                # Зеленый для активных устройств
                status_item.setBackground(QColor(232, 245, 233))
                status_item.setForeground(QColor(27, 94, 32))
                status_item.setIcon(QIcon.fromTheme('network-connect', QIcon()))
            elif status_text == 'Неактивно':
                # Серый для неактивных устройств
                status_item.setBackground(QColor(238, 238, 238))
                status_item.setForeground(QColor(117, 117, 117))
                status_item.setIcon(QIcon.fromTheme('network-disconnect', QIcon()))
                status_item.setToolTip("Устройство недавно было в сети, но сейчас не отвечает")
            else:
                # Жёлтый для неопределённого статуса
                status_item.setBackground(QColor(255, 248, 225))
                status_item.setForeground(QColor(245, 124, 0))
            
            self.devices_table.setItem(row, 4, status_item)
        
        # Подгоняем размеры столбцов под содержимое
        self.devices_table.resizeColumnsToContents()

class NetworkMonitorWidget(QTabWidget):
    """
    Виджет, содержащий вкладки для мониторинга сети
    """
    def __init__(self):
        super().__init__()
        
        # Создаем поток мониторинга
        self.monitor_thread = NetworkMonitorThread()
        
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
        
        # Инициализируем интерфейс
        self.init_ui()
        
        # Инициализируем локальный IP и шлюз
        self.monitor_thread.monitor.get_network_interfaces()
        self.monitor_thread.monitor.get_gateway_info()
        
        # Запускаем поток мониторинга
        self.monitor_thread.start()
        
        # Автоматически обновляем визуализацию сети при отображении вкладки
        self.currentChanged.connect(self.on_tab_changed)
    
    def on_tab_changed(self, index):
        """Обрабатывает изменение активной вкладки"""
        # Если выбрана вкладка топологии сети, запускаем инициализацию
        if index == 2 and hasattr(self, 'network_topology_tab'):
            QTimer.singleShot(100, self.network_topology_tab.initialize_network_info)
    
    def init_ui(self):
        # Вкладка с информацией о сетевых интерфейсах
        self.network_info_tab = NetworkInfoTab(self.monitor_thread)
        self.addTab(self.network_info_tab, "Сетевые интерфейсы")
        
        # Вкладка с ARP таблицей
        self.arp_table_tab = ARPTableTab(self.monitor_thread)
        self.addTab(self.arp_table_tab, "ARP таблица")
        
        # Вкладка с топологией сети
        self.network_topology_tab = NetworkTopologyTab(self.monitor_thread)
        self.addTab(self.network_topology_tab, "Топология сети")
        
        # Вкладка с трассировкой маршрута
        self.trace_route_tab = TraceRouteTab(self.monitor_thread)
        self.addTab(self.trace_route_tab, "Трассировка")
    
    def closeEvent(self, event):
        # Останавливаем поток при закрытии
        self.monitor_thread.stop()
        self.monitor_thread.wait()

class TraceRouteTab(QWidget):
    """
    Вкладка с трассировкой до указанного IP-адреса
    """
    def __init__(self, monitor_thread):
        super().__init__()
        self.monitor_thread = monitor_thread
        self.trace_results = []
        self.trace_thread = None
        self.init_ui()
    
    def init_ui(self):
        # Основной лейаут
        main_layout = QVBoxLayout()
        
        # Добавляем заголовок
        header_layout = QHBoxLayout()
        title_label = QLabel("Трассировка маршрута")
        title_label.setStyleSheet("""
            font-size: 14px;
            font-weight: bold;
            color: #2196F3;
            margin-bottom: 10px;
        """)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        # Создаем поле ввода и кнопку для запуска трассировки
        input_layout = QHBoxLayout()
        
        ip_label = QLabel("IP адрес или доменное имя:")
        ip_label.setStyleSheet("font-weight: bold;")
        
        self.ip_input = QLineEdit()
        self.ip_input.setPlaceholderText("Введите IP-адрес или доменное имя (например, 8.8.8.8 или google.com)")
        self.ip_input.setStyleSheet("""
            QLineEdit {
                padding: 6px;
                border: 1px solid #c0c8e0;
                border-radius: 4px;
                background-color: #f8faff;
            }
            QLineEdit:focus {
                border: 1px solid #2196F3;
                background-color: white;
            }
        """)
        
        self.trace_button = QPushButton("Запустить трассировку")
        self.trace_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.trace_button.clicked.connect(self.start_trace)
        
        # Добавляем кнопку отмены
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                padding: 6px 12px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:pressed {
                background-color: #B71C1C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_trace)
        self.cancel_button.setVisible(False)  # Изначально скрыта
        
        input_layout.addWidget(ip_label)
        input_layout.addWidget(self.ip_input, 1)  # 1 - коэффициент растяжения
        input_layout.addWidget(self.trace_button)
        input_layout.addWidget(self.cancel_button)
        
        # Создаем таблицу для отображения результатов трассировки
        self.trace_table = QTableWidget()
        self.trace_table.setColumnCount(4)
        self.trace_table.setHorizontalHeaderLabels([
            "Хоп", 
            "IP адрес", 
            "Имя хоста", 
            "Время отклика"
        ])
        
        # Скрываем номера строк слева (встроенные номера Qt)
        self.trace_table.verticalHeader().setVisible(False)
        
        # Устанавливаем свойства таблицы
        self.trace_table.setAlternatingRowColors(True)
        self.trace_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #e0e0e0;
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 4px;
                border-bottom: 1px solid #f0f0f0;
            }
            QTableWidget::item:selected {
                background-color: #e6f2ff;
                color: #2196F3;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 4px;
                border: 1px solid #d0d0d0;
                border-left: none;
                border-top: none;
                font-weight: bold;
                color: #424242;
            }
            QTableWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        # Растягиваем заголовки на всю ширину таблицы
        self.trace_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        # Добавляем индикатор выполнения
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setVisible(False)
        
        # Добавляем информационную метку
        self.info_label = QLabel()
        self.info_label.setStyleSheet("""
            color: #757575;
            font-style: italic;
        """)
        self.info_label.setVisible(False)
        
        # Добавляем компоненты в лейаут
        main_layout.addLayout(header_layout)
        main_layout.addLayout(input_layout)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.info_label)
        main_layout.addWidget(self.trace_table)
        
        # Устанавливаем основной лейаут
        self.setLayout(main_layout)
        
    def start_trace(self):
        """
        Запускает трассировку маршрута до указанного IP-адреса
        """
        target = self.ip_input.text().strip()
        if not target:
            self.info_label.setText("Пожалуйста, введите IP-адрес или доменное имя")
            self.info_label.setStyleSheet("color: #F44336; font-weight: bold;")
            self.info_label.setVisible(True)
            return
        
        # Сбрасываем прогресс-бар в исходное состояние
        self.progress_bar.reset()
        
        # Блокируем кнопку запуска и показываем кнопку отмены
        self.trace_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        self.progress_bar.setVisible(True)
        self.info_label.setText(f"Выполняется трассировка до {target}...")
        self.info_label.setStyleSheet("color: #757575; font-style: italic;")
        self.info_label.setVisible(True)
        
        # Очищаем таблицу
        self.trace_table.setRowCount(0)
        
        # Запускаем трассировку в отдельном потоке
        class TraceThread(QThread):
            # Сигнал для передачи данных о каждом хопе по мере его получения
            hop_found = pyqtSignal(dict)
            trace_completed = pyqtSignal(int)  # Передаем общее количество хопов
            trace_error = pyqtSignal(str)
            
            def __init__(self, target_ip):
                super().__init__()
                self.target_ip = target_ip
                self.total_hops = 0
                self.should_stop = False  # Флаг для остановки трассировки
            
            def stop(self):
                """Метод для остановки трассировки"""
                self.should_stop = True
            
            def run(self):
                try:
                    import subprocess
                    import re
                    import socket
                    import time
                    
                    # Windows использует tracert, Linux/MacOS используют traceroute
                    cmd = "tracert" if platform.system() == "Windows" else "traceroute"
                    max_hops = 30
                    params = f"-d -h {max_hops} {self.target_ip}" if cmd == "tracert" else f"-m {max_hops} {self.target_ip}"
                    
                    # Для Windows запускаем tracert и обрабатываем вывод построчно
                    if platform.system() == "Windows":
                        # Включаем режим отладки, если нужно
                        debug_mode = False
                        
                        # Создаем процесс
                        process = subprocess.Popen(
                            f"{cmd} {params}",
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            text=True,
                            encoding="cp866"
                        )
                        
                        # Ожидаем заголовок трассировки
                        header_seen = False
                        
                        for line in iter(process.stdout.readline, ''):
                            # Проверяем, не запрошена ли остановка
                            if self.should_stop:
                                # Прерываем процесс tracert
                                try:
                                    process.terminate()
                                except:
                                    pass
                                break
                            
                            if debug_mode:
                                print(f"DEBUG: {line.strip()}")
                            
                            # Пропускаем заголовки трассировки
                            if not header_seen and ("с максимальным числом прыжков" in line or "Tracing route to" in line):
                                header_seen = True
                                continue
                            
                            # Проверяем, не завершилась ли трассировка
                            if "Трассировка завершена" in line or "Trace complete" in line:
                                break
                            
                            # Пытаемся извлечь информацию о хопе
                            # Сначала проверяем, что строка начинается с числа (номера хопа)
                            hop_match = re.match(r'\s*(\d+)', line)
                            if not hop_match:
                                continue
                            
                            hop_num = hop_match.group(1)
                            
                            # Если строка начинается с номера хопа, получаем оставшуюся часть
                            line_after_hop = re.sub(r'^\s*\d+\s+', '', line.strip())
                            
                            # Находим все значения времени отклика или звездочки
                            # В выводе tracert они идут первыми после номера хопа
                            rtt_values = re.findall(r'(<?\d+\s+мс|\*|<\d+\s+ms|\d+\s+ms)', line_after_hop)
                            
                            # Проверяем наличие IP адреса
                            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
                            if ip_match:
                                ip_str = ip_match.group(1)
                                
                                # Получаем строку после IP-адреса
                                line_after_ip = line.split(ip_str, 1)
                                has_hostname_after_ip = len(line_after_ip) > 1 and line_after_ip[1].strip()
                                
                                # Получаем строку до IP-адреса
                                line_before_ip = line_after_hop
                                for rtt in rtt_values:
                                    line_before_ip = line_before_ip.replace(rtt, '')
                                line_before_ip = line_before_ip.replace(ip_str, '').strip()
                                
                                # Проверяем наличие имени хоста в квадратных скобках
                                hostname_bracket_match = re.search(r'([^\[\]]+)\s*\[\s*' + re.escape(ip_str) + r'\s*\]', line)
                                
                                # Определяем имя хоста
                                hostname = "—"  # По умолчанию прочерк
                                
                                if hostname_bracket_match:
                                    # Формат: hostname [ip]
                                    hostname = hostname_bracket_match.group(1).strip()
                                elif has_hostname_after_ip:
                                    # Имя хоста может быть после IP-адреса
                                    hostname_after_ip = line_after_ip[1].strip()
                                    if hostname_after_ip and not any(x in hostname_after_ip for x in ["мс", "ms"]):
                                        hostname = hostname_after_ip
                                elif line_before_ip and not any(x in line_before_ip for x in ["мс", "ms"]):
                                    # Имя хоста может быть перед IP-адресом (после RTT значений)
                                    hostname = line_before_ip
                                
                                # Если не удалось найти имя хоста, пробуем DNS
                                if hostname == "—":
                                    try:
                                        hostname_result = socket.gethostbyaddr(ip_str)
                                        if hostname_result and hostname_result[0]:
                                            hostname = hostname_result[0]
                                            # Проверяем, что имя хоста - не IP-адрес
                                            if re.match(r'\d+\.\d+\.\d+\.\d+', hostname):
                                                hostname = "—"
                                    except:
                                        pass  # Оставляем прочерк, если не получилось
                                
                                # Вычисляем минимальное значение RTT для отображения
                                min_rtt = float('inf')
                                for rtt in rtt_values:
                                    if rtt != "*":
                                        # Извлекаем числовое значение
                                        rtt_match = re.search(r'(\d+)', rtt)
                                        if rtt_match:
                                            rtt_value = float(rtt_match.group(1))
                                            if "<" in rtt and rtt_value == 1:
                                                # Для "<1 мс" используем 0.5
                                                rtt_value = 0.5
                                            if rtt_value < min_rtt:
                                                min_rtt = rtt_value
                                
                                # Форматируем время отклика
                                if min_rtt != float('inf'):
                                    if min_rtt == 0.5:
                                        rtt_str = "<1.00 мс"
                                    else:
                                        rtt_str = f"{min_rtt:.2f} мс"
                                else:
                                    rtt_str = "—"  # Если не нашли валидное время отклика
                            else:
                                # Если IP не найден, используем прочерки
                                ip_str = "—"
                                rtt_str = "—"
                                hostname = "—"
                                
                                # Проверяем, есть ли сообщение о превышении времени ожидания
                                if "Превышен" in line:
                                    ip_str = "Превышен"
                            
                            # Если нашли хоп, отправляем данные
                            if hop_num:
                                hop_data = {
                                    "hop": hop_num,
                                    "ip": ip_str,
                                    "hostname": hostname,
                                    "rtt": rtt_str
                                }
                                self.hop_found.emit(hop_data)
                                self.total_hops += 1
                        
                        # Дожидаемся завершения процесса
                        process.wait()
                    
                    # Linux/MacOS используют traceroute (оставляем существующий код)
                    else:
                        # Выполняем команду трассировки
                        process = subprocess.Popen(
                            f"{cmd} {params}",
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            shell=True,
                            text=True,
                            encoding="utf-8"
                        )
                        
                        header_seen = False
                        
                        for line in iter(process.stdout.readline, ''):
                            # Проверяем, не запрошена ли остановка
                            if self.should_stop:
                                # Прерываем процесс traceroute
                                try:
                                    process.terminate()
                                except:
                                    pass
                                break
                            
                            # Пропускаем заголовок
                            if not header_seen:
                                header_seen = True
                                continue
                                
                            # Парсим строку с информацией о хопе
                            match = re.match(r'\s*(\d+)\s+(?:([^\s]+)\s+)?\(([^\)]+|\*)\)\s+(?:(\d+\.\d+)\s+ms)?', line)
                            if match:
                                hop_num, hostname, ip, rtt = match.groups()
                                
                                # Определяем доступность хопа
                                is_reachable = ip != "*" and rtt is not None
                                
                                # Формируем информацию о хопе
                                ip_str = ip if ip != "*" else "—"
                                
                                # Улучшенная обработка имени хоста для Linux/MacOS
                                if hostname is None or hostname == "" or hostname == "*":
                                    hostname_str = "—"  # По умолчанию прочерк, если hostname пустой или "*"
                                    
                                    # Если есть IP-адрес, пробуем получить имя хоста через DNS
                                    if ip_str != "—":
                                        try:
                                            hostname_result = socket.gethostbyaddr(ip_str)
                                            if hostname_result and hostname_result[0]:
                                                hostname_str = hostname_result[0]
                                                # Проверяем, что имя хоста - не IP-адрес
                                                if re.match(r'\d+\.\d+\.\d+\.\d+', hostname_str):
                                                    hostname_str = "—"
                                        except:
                                            pass  # Оставляем прочерк, если не получилось
                                else:
                                    hostname_str = hostname  # Используем имя хоста из вывода traceroute
                                    # Проверяем, что имя хоста не является IP-адресом или не содержит "ms"
                                    if re.match(r'\d+\.\d+\.\d+\.\d+', hostname_str) or "ms" in hostname_str:
                                        hostname_str = "—"
                                
                                # Обрабатываем случай с "<1 ms" в Linux/MacOS трассировке
                                if rtt is not None:
                                    if "<" in rtt:
                                        rtt_str = "<1.00 мс"  # Для времени меньше 1 мс
                                    else:
                                        rtt_str = f"{float(rtt):.2f} мс"
                                else:
                                    rtt_str = "—"
                                
                                # Отправляем данные о хопе в основной поток
                                hop_data = {
                                    "hop": hop_num,
                                    "ip": ip_str,
                                    "hostname": hostname_str,
                                    "rtt": rtt_str
                                }
                                self.hop_found.emit(hop_data)
                                self.total_hops += 1
                        
                        # Дожидаемся завершения процесса
                        process.wait()
                    
                    # Сигнализируем о завершении трассировки только если не была запрошена остановка
                    if not self.should_stop:
                        self.trace_completed.emit(self.total_hops)
                    
                except Exception as e:
                    self.trace_error.emit(f"Ошибка при выполнении трассировки: {str(e)}")
        
        # Создаем и запускаем поток трассировки
        self.trace_thread = TraceThread(target)
        
        # Подключаем сигналы для обработки результатов
        self.trace_thread.hop_found.connect(self.on_hop_found)
        self.trace_thread.trace_completed.connect(self.on_trace_completed)
        self.trace_thread.trace_error.connect(self.on_trace_error)
        self.trace_thread.finished.connect(lambda: self.cleanup_thread())
        
        # Запускаем поток
        self.trace_thread.start()
    
    def cancel_trace(self):
        """
        Отменяет выполнение трассировки
        """
        if self.trace_thread and self.trace_thread.isRunning():
            # Останавливаем трассировку
            self.trace_thread.stop()
            
            # Обновляем UI
            self.info_label.setText("Трассировка отменена пользователем")
            self.info_label.setStyleSheet("color: #FF9800; font-weight: bold;")
            
            # Очищаем поле ввода и таблицу
            self.ip_input.clear()
            self.trace_table.setRowCount(0)
            
            # Скрываем прогресс-бар и кнопку отмены
            self.progress_bar.setVisible(False)
            self.cancel_button.setVisible(False)
            
            # Разблокируем кнопку запуска
            self.trace_button.setEnabled(True)
    
    def on_hop_found(self, hop_data):
        """
        Обрабатывает получение данных о новом хопе
        """
        # Добавляем новую строку в таблицу
        row = self.trace_table.rowCount()
        self.trace_table.insertRow(row)
        
        # Заполняем информацию о хопе
        self.trace_table.setItem(row, 0, QTableWidgetItem(hop_data["hop"]))
        self.trace_table.setItem(row, 1, QTableWidgetItem(hop_data["ip"]))
        self.trace_table.setItem(row, 2, QTableWidgetItem(hop_data["hostname"]))
        self.trace_table.setItem(row, 3, QTableWidgetItem(hop_data["rtt"]))
        
        # Прокручиваем таблицу до новой строки
        self.trace_table.scrollToItem(self.trace_table.item(row, 0))
        
        # Обновляем информационное сообщение
        self.info_label.setText(f"Трассировка до {self.ip_input.text().strip()}... (найдено {row+1} хопов)")
    
    def on_trace_completed(self, total_hops):
        """
        Обрабатывает завершение трассировки
        """
        # Показываем сообщение о завершении
        self.info_label.setText(f"Трассировка завершена. Найдено {total_hops} хопов.")
        self.info_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        
        # Скрываем прогресс и разблокируем кнопку
        self.progress_bar.setCompleted(True)
        self.trace_button.setEnabled(True)
        self.cancel_button.setVisible(False)
    
    def on_trace_error(self, error_msg):
        """
        Обрабатывает ошибку при трассировке
        """
        self.info_label.setText(error_msg)
        self.info_label.setStyleSheet("color: #F44336; font-weight: bold;")
        
        # Скрываем прогресс и разблокируем кнопку
        self.progress_bar.setVisible(False)
        self.trace_button.setEnabled(True)
        self.cancel_button.setVisible(False)
    
    def cleanup_thread(self):
        """
        Очищает поток после завершения
        """
        if self.trace_thread:
            self.trace_thread.deleteLater()
            self.trace_thread = None
