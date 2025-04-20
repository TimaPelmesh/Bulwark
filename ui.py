from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QApplication, 
                           QVBoxLayout, QHBoxLayout, QWidget, QSplitter, QLabel, 
                           QStatusBar, QAction, QMenu, QMenuBar, QToolBar,
                           QSystemTrayIcon, QFileDialog, QDialog, QGroupBox,
                           QCheckBox, QPushButton, QGridLayout, QMessageBox, QLineEdit,
                           QTabBar)
from PyQt5.QtCore import Qt, QSize, QTimer, QObject, QEvent
from PyQt5.QtGui import QIcon, QCursor
import sys
import os
import datetime

from system_monitor import SystemMonitorWidget
from network_monitor import NetworkMonitorWidget

class NoSelectTabBar(QTabBar):
    """
    Класс вкладок без возможности выделения текста
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.NoFocus)
        # Полностью отключаем стиль фокуса
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        # Применяем кастомный стиль напрямую
        self.setStyleSheet("""
            QTabBar::tab {
                border: 1px solid #c0c8e0;
                border-bottom-color: #c0c8e0;
                color: #3e4458;
                border-radius: 4px 4px 0 0;
                outline: none;
            }
            QTabBar::tab:selected {
                background-color: #2196F3;
                border: 1px solid #2196F3;
                border-bottom-color: #2196F3;
                color: white;
                outline: none;
            }
            QTabBar::tab:focus, QTabBar:focus, QTabBar:selected {
                outline: none;
                border-color: transparent;
            }
        """)
    
    def mousePressEvent(self, event):
        # Предотвращаем выделение текста при клике
        if event.button() == Qt.LeftButton:
            index = self.tabAt(event.pos())
            if index >= 0:
                self.setCurrentIndex(index)
                event.accept()
                return
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        # Предотвращаем выделение при отпускании мыши
        if event.button() == Qt.LeftButton:
            event.accept()
            return
        super().mouseReleaseEvent(event)
    
    def tabSizeHint(self, index):
        # Размер вкладки без учета обводки
        size = super().tabSizeHint(index)
        return size
    
    def focusInEvent(self, event):
        # Игнорируем событие получения фокуса
        event.ignore()
    
    def focusOutEvent(self, event):
        # Игнорируем событие потери фокуса
        event.ignore()

class MainWindow(QMainWindow):
    """
    Главное окно приложения
    """
    def __init__(self):
        super().__init__()
        
        # Устанавливаем атрибут для предотвращения фокуса
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_MacShowFocusRect, False)
        
        self.setWindowTitle("Bulwark")
        self.setMinimumSize(1050, 700)  # Увеличиваем минимальный размер для лучшего отображения
        
        # Стиль главного окна
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            
            /* Стиль для вкладок с небольшой тенью */
            QTabWidget::pane { 
                background-color: white;
                border: 1px solid #d0d8e8;
                border-radius: 6px;
                top: -1px; 
            }
            
            /* Делаем полоски прокрутки более стильными */
            QScrollBar:vertical {
                border: none;
                background: #f0f5ff;
                width: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical {
                background: #c0c8e0;
                min-height: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:vertical:hover {
                background: #3a7bd5;
            }
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            
            QScrollBar:horizontal {
                border: none;
                background: #f0f5ff;
                height: 10px;
                margin: 0px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:horizontal {
                background: #c0c8e0;
                min-width: 20px;
                border-radius: 5px;
            }
            
            QScrollBar::handle:horizontal:hover {
                background: #3a7bd5;
            }
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Установка иконки приложения
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.ico"))
        self.setWindowIcon(QIcon(icon_path))
        
        # Сохраняем ссылку на окно "О программе"
        self.about_window = None
        
        # Создаем центральный виджет
        self.central_widget = QTabWidget()
        
        # Заменяем стандартный QTabBar на наш кастомный NoSelectTabBar
        custom_tab_bar = NoSelectTabBar()
        self.central_widget.setTabBar(custom_tab_bar)
        
        # Отключаем эффект фокуса для всего виджета
        self.central_widget.setGraphicsEffect(None)
        
        # Устанавливаем свойство для отключения выделения текста
        self.setProperty("disableTextSelection", True)
        
        self.central_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #c0c8e0;
                border-radius: 6px;
                background-color: white;
                padding: 4px;
                margin-top: -1px;
            }
            QTabWidget:focus, QTabBar:focus, QTabBar::tab:focus {
                border: none;
                outline: none;
                border-color: transparent;
                border-width: 0px;
                padding: 0px;
                margin: 0px;
                background-color: transparent;
            }
            QTabBar::tab {
                background-color: #f0f5ff;
                border: 1px solid #c0c8e0;
                border-bottom-color: #c0c8e0;
                padding: 4px 8px;
                margin-right: 0px;
                color: #434d66;
                min-width: 130px;
                font-weight: bold;
                font-size: 10px;
                outline: none;
                cursor: pointer;
            }
            QTabBar::tab:selected {
                background-color: #3a7bd5;
                border: 1px solid #3a7bd5;
                border-bottom-color: #3a7bd5;
                color: white;
                outline: none;
            }
            QTabBar::tab:hover:!selected {
                background-color: #d6e4ff;
            }
        """)
        self.setCentralWidget(self.central_widget)
        
        # Создаем виджеты мониторинга
        self.system_monitor = SystemMonitorWidget()
        self.network_monitor = NetworkMonitorWidget()
        
        # Добавляем вкладки в центральный виджет
        self.central_widget.addTab(self.system_monitor, "Системный мониторинг")
        self.central_widget.addTab(self.network_monitor, "Сетевой мониторинг")
        
        # Полностью отключаем выделение и фокус для всех вкладок
        tabBar = self.central_widget.tabBar()
        
        # Устанавливаем фильтр событий для вкладок
        class EventFilter(QObject):
            def eventFilter(self, obj, event):
                # Блокируем только события выделения текста
                if event.type() == QEvent.MouseButtonPress:
                    # Получаем индекс вкладки под курсором
                    pos = event.pos()
                    index = tabBar.tabAt(pos)
                    
                    # Если нажата вкладка, обрабатываем клик, но без выделения
                    if index >= 0:
                        tabBar.setCurrentIndex(index)
                        return True  # Событие обработано, предотвращаем выделение
                elif event.type() == QEvent.MouseButtonDblClick:
                    # Блокируем двойной клик, чтобы предотвратить выделение
                    return True
                
                # Для остальных событий используем стандартную обработку
                return False  # Не обрабатываем другие события
        
        filter = EventFilter(self)
        tabBar.installEventFilter(filter)
        
        # Отключаем возможность выделения текста на вкладках программно
        self.central_widget.setFocusPolicy(Qt.NoFocus)
        tabBar.setFocusPolicy(Qt.NoFocus)
        
        # Явно отключаем обводку фокуса для tabBar
        tabBar.setAttribute(Qt.WA_MacShowFocusRect, False)
        
        # Устанавливаем дополнительные свойства для предотвращения выделения текста
        self.central_widget.setTabBarAutoHide(False)  # Всегда показывать панель вкладок
        tabBar.setSelectionBehaviorOnRemove(QTabBar.SelectPreviousTab)
        tabBar.setDrawBase(True)
        tabBar.setExpanding(False)
        tabBar.setMovable(False)
        
        # Создаем строку состояния
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background-color: #f5f8ff;
                color: #3a7bd5;
                border-top: 1px solid #e0e6f0;
                padding: 4px;
                font-weight: bold;
            }
        """)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Готово")
        
        # Создаем статусный лейбл для системной информации
        self.status_label = QLabel()
        self.statusBar.addPermanentWidget(self.status_label)
        
        # Создаем меню
        self.create_menu()
        
        # Настройка системного трея
        self.setup_tray()
        
        # Таймер для обновления статус-бара
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.update_status)
        self.status_timer.start(2000)  # Обновление каждые 2 секунды
    
    def create_menu(self):
        """
        Создание главного меню
        """
        # Создаем верхнее меню
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #f5f8ff;
                border-bottom: 1px solid #e0e6f0;
                font-weight: bold;
                color: #3e4458;
            }
            QMenuBar::item {
                background-color: transparent;
                padding: 6px 12px;
            }
            QMenuBar::item:selected {
                background-color: #d0e0ff;
                border-radius: 4px;
            }
            QMenuBar::item:pressed {
                background-color: #3a7bd5;
                color: white;
                border-radius: 4px;
            }
            QMenu {
                background-color: white;
                border: 1px solid #e0e6f0;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 25px 5px 20px;
                border-radius: 3px;
                margin: 2px 5px;
            }
            QMenu::item:selected {
                background-color: #f0f5ff;
                color: #3a7bd5;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e0e6f0;
                margin: 5px 10px;
            }
        """)
        
        # Меню "Файл"
        file_menu = menubar.addMenu("Файл")
        
        # Действие "Выход"
        exit_action = QAction("Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Меню "Отчет"
        report_menu = menubar.addMenu("Отчет")
        
        # Действие "Сгенерировать отчет о системе"
        system_report_action = QAction("Сгенерировать отчет о системе", self)
        system_report_action.setShortcut("Ctrl+R")
        system_report_action.triggered.connect(self.show_report_dialog)
        report_menu.addAction(system_report_action)
        
        # Меню "Справка"
        help_menu = menubar.addMenu("Справка")
        
        # Действие "О программе"
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def show_about(self):
        """
        Отображение информации о программе
        """
        # Отображаем окно
        about_window = QDialog(self)
        about_window.setWindowTitle("О программе")
        about_window.setFixedSize(550, 500)  # Увеличиваем высоту окна
        about_window.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 10px;
            }
        """)
        
        # Установка иконки
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.ico"))
        if os.path.exists(icon_path):
            about_window.setWindowIcon(QIcon(icon_path))
        
        # Создаем основной макет
        main_layout = QVBoxLayout(about_window)
        main_layout.setSpacing(15)  # Уменьшаем отступы между элементами
        main_layout.setContentsMargins(35, 25, 35, 25)  # Уменьшаем отступы от краев
        
        # Добавляем иконку приложения вверху
        logo_label = QLabel()
        logo_pixmap = QIcon(icon_path).pixmap(64, 64)  # Уменьшаем размер логотипа
        logo_label.setPixmap(logo_pixmap)
        logo_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(logo_label)
        
        # Добавляем заголовок с названием проекта
        title_label = QLabel("Bulwark")
        title_label.setStyleSheet("""
            font-size: 32px;
            font-weight: bold;
            color: #2a6ac5;
            margin-bottom: 5px;
            letter-spacing: 1px;
        """)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)
        
        # Добавляем подзаголовок
        subtitle_label = QLabel("Система мониторинга компьютера")
        subtitle_label.setStyleSheet("""
            font-size: 16px;
            color: #5a6891;
            margin-bottom: 10px;
        """)
        subtitle_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(subtitle_label)
        
        # Небольшой отступ перед списком разработчиков
        spacer_tiny = QLabel()
        spacer_tiny.setFixedHeight(5)  # Уменьшаем отступ перед списком
        main_layout.addWidget(spacer_tiny)
        
        # Создаем единую метку для всех разработчиков с более компактным отображением
        developers_html = """
        <div style="text-align: center; margin: 5px 0;">
            <p style="margin: 4px 0; font-size: 15px; color: #000000; font-weight: 500;">Иванов Тимур</p>
            <p style="margin: 4px 0; font-size: 15px; color: #000000; font-weight: 500;">Кучин Матвей</p>
            <p style="margin: 4px 0; font-size: 15px; color: #000000; font-weight: 500;">Кадасемчук Динар</p>
            <p style="margin: 4px 0; font-size: 15px; color: #000000; font-weight: 500;">Гановичев Никита</p>
        </div>
        """
        
        devs_label = QLabel(developers_html)
        devs_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(devs_label)
        
        # Небольшой отступ после списка
        spacer_tiny2 = QLabel()
        spacer_tiny2.setFixedHeight(5)  # Уменьшаем отступ после списка
        main_layout.addWidget(spacer_tiny2)
        
        # Добавляем версию программы
        version_label = QLabel("Версия 1.0")
        version_label.setStyleSheet("""
            font-size: 13px; 
            color: #667899; 
            margin-top: 15px;
            font-weight: bold;
        """)
        version_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(version_label)
        
        # Добавляем копирайт
        copyright_label = QLabel("© 2025 Группа 2АСС9-13.")
        copyright_label.setStyleSheet("""
            font-size: 12px; 
            color: #8995a9;
            margin-top: 5px;
        """)
        copyright_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(copyright_label)
        
        # Добавляем автоматическое растягивание для выравнивания
        main_layout.addStretch(1)
        
        # Отображаем окно
        about_window.exec_()
    
    def closeEvent(self, event):
        """
        Обработка события закрытия окна
        """
        # Закрываем все дочерние окна и потоки
        event.accept()
    
    def focusInEvent(self, event):
        """
        Предотвращаем стандартное поведение при получении фокуса
        """
        # Предотвращаем стандартное поведение при фокусе
        event.accept()
    
    def setup_tray(self):
        """
        Настройка иконки в системном трее
        """
        # Создаем значок трея
        self.tray_icon = QSystemTrayIcon(self)
        
        # Установка иконки для системного трея
        icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.ico"))
        self.tray_icon.setIcon(QIcon(icon_path))
        
        # Создаем меню для трея
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #e0e6f0;
                border-radius: 4px;
                padding: 5px;
            }
            QMenu::item {
                padding: 6px 25px 6px 20px;
                border-radius: 3px;
                margin: 2px 5px;
                color: #3e4458;
            }
            QMenu::item:selected {
                background-color: #f0f5ff;
                color: #3a7bd5;
            }
            QMenu::separator {
                height: 1px;
                background-color: #e0e6f0;
                margin: 5px 10px;
            }
        """)
        
        # Действие для открытия/восстановления окна
        show_action = QAction("Показать", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        # Действие для выхода
        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(QApplication.quit)
        tray_menu.addAction(quit_action)
        
        # Устанавливаем меню
        self.tray_icon.setContextMenu(tray_menu)
        
        # Включаем отображение трея
        self.tray_icon.show()
        
        # Подключаем обработчик клика
        self.tray_icon.activated.connect(self.tray_icon_activated)
    
    def tray_icon_activated(self, reason):
        """
        Обработчик активации иконки в трее
        """
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
    
    def update_status(self):
        """
        Обновление строки состояния
        """
        # Получаем активную вкладку
        current_tab = self.central_widget.currentWidget()
        
        if isinstance(current_tab, SystemMonitorWidget):
            try:
                # Обновляем статус системных ресурсов
                system_tab = current_tab.system_tab if hasattr(current_tab, 'system_tab') else None
                
                if system_tab:
                    cpu_usage = system_tab.cpu_usage if hasattr(system_tab, 'cpu_usage') else 0
                    ram_usage = system_tab.ram_usage if hasattr(system_tab, 'ram_usage') else 0
                    
                    # Получаем только общий процент CPU вместо полной строки
                    if isinstance(cpu_usage, dict) and 'total' in cpu_usage:
                        cpu_percentage = cpu_usage['total']
                    else:
                        cpu_percentage = cpu_usage
                    
                    # Создаем красивый статус с использованием HTML, оставляем дробное значение
                    status_html = f"""
                        <span style="color: #004b8d; font-weight: bold;">CPU:</span> 
                        <span style="color: #0055cc; font-weight: bold;">{cpu_percentage}%</span> &nbsp;|&nbsp; 
                        <span style="color: #004b8d; font-weight: bold;">ОЗУ:</span> 
                        <span style="color: #0055cc; font-weight: bold;">{ram_usage}%</span>
                    """
                    self.status_label.setText(status_html)
                    self.statusBar.showMessage("")  # Очищаем текстовое сообщение
                    
                    # Обновляем всплывающую подсказку в трее с точным значением
                    tooltip_text = f"Bulwark Монитор\nЗагрузка ЦП: {cpu_percentage}%\nИспользование ОЗУ: {ram_usage}%"
                    self.tray_icon.setToolTip(tooltip_text)
                else:
                    self.statusBar.showMessage("Мониторинг системы")
            except Exception:
                self.statusBar.showMessage("Мониторинг системы")
        elif isinstance(current_tab, NetworkMonitorWidget):
            try:
                # Обновляем статус сети
                network_tab = current_tab.network_topology_tab
                network_info = network_tab.network_info.text()
                self.statusBar.showMessage(network_info)
                self.status_label.setText("")  # Очищаем HTML лейбл
            except:
                self.statusBar.showMessage("Мониторинг сети")
                self.status_label.setText("")
        else:
            self.statusBar.showMessage("Готово")
            self.status_label.setText("")
    
    def show_and_activate(self):
        """
        Показывает и активирует окно
        """
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()  # Для фокуса на окно
    
    def show_report_dialog(self):
        """
        Показывает диалог настройки отчета о системе
        """
        dialog = QDialog(self)
        dialog.setWindowTitle("Настройка отчета о системе")
        dialog.setMinimumWidth(550)
        dialog.setMinimumHeight(450)
        # Отключаем кнопку помощи (знак вопроса) в заголовке окна
        dialog.setWindowFlags(dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        # Применяем стиль без глобальных стилей для чекбоксов
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border-radius: 8px;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: 1px solid #e0e6f0;
                border-radius: 8px;
                margin-top: 16px;
                padding: 15px;
                background-color: white;
                margin-bottom: 5px;
            }
            QGroupBox:hover {
                border: 1px solid #3a7bd5;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 8px;
                background-color: white;
                color: #3a7bd5;
            }
            QLabel {
                font-size: 12px;
                color: #3e4458;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #e0e6f0;
                border-radius: 4px;
                background-color: #f5f8ff;
                selection-background-color: #3a7bd5;
                selection-color: white;
            }
            QLineEdit:focus {
                border-color: #3a7bd5;
                background-color: white;
            }
            QPushButton {
                padding: 8px 15px;
                border: 1px solid #e0e6f0;
                border-radius: 5px;
                background-color: #f5f8ff;
                color: #3a7bd5;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #d0e0ff;
            }
            QPushButton:pressed {
                background-color: #3a7bd5;
                color: white;
            }
            QPushButton#generate {
                background-color: #3a7bd5;
                color: white;
                border: none;
                font-weight: bold;
                padding: 10px 20px;
                min-width: 140px;
            }
            QPushButton#generate:hover {
                background-color: #2a6ac5;
            }
            QPushButton#browse {
                font-weight: normal;
                padding: 8px 12px;
            }
            QPushButton#select-all {
                margin-top: 10px;
                padding: 6px 12px;
                background-color: #f5f8ff;
                font-weight: normal;
                font-style: italic;
                border-radius: 4px;
            }
            QPushButton#select-all:hover {
                background-color: #d0e0ff;
            }
        """)
        
        # Основной макет
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Добавляем заголовок
        title_label = QLabel("Создание отчета о состоянии системы")
        title_label.setStyleSheet("""
            font-size: 18px;
            font-weight: bold;
            color: #3a7bd5;
            margin-bottom: 10px;
        """)
        title_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(title_label)
        
        # Добавляем информацию о назначении
        info_label = QLabel("Это окно позволяет настроить и сгенерировать отчет о состоянии вашей системы в текстовом формате.")
        info_label.setStyleSheet("""
            font-size: 12px;
            color: #6a7891;
            margin-bottom: 10px;
        """)
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignLeft)
        layout.addWidget(info_label)
        
        # Группа настроек сохранения
        save_group = QGroupBox("Сохранение отчета")
        save_layout = QGridLayout()
        save_layout.setContentsMargins(15, 20, 15, 15)
        save_layout.setSpacing(10)
        
        # Поле для выбора пути сохранения
        path_label = QLabel("Путь для сохранения:")
        path_label.setStyleSheet("font-weight: bold;")
        save_layout.addWidget(path_label, 0, 0)
        
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("Выберите путь для сохранения отчета...")
        
        # Получаем директорию документов пользователя и имя компьютера
        documents_path = os.path.expanduser("~/Документы")
        # Получаем имя компьютера через SystemMonitor
        computer_name = self.system_monitor.system_tab.monitor.get_system_info().get("Имя компьютера", "unknown")
        default_filename = f"{computer_name}_report_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        default_path = os.path.join(documents_path, default_filename)
        self.path_edit.setText(default_path)
        
        save_layout.addWidget(self.path_edit, 0, 1)
        
        # Кнопка выбора пути
        browse_button = QPushButton("Обзор...")
        browse_button.setObjectName("browse")
        browse_button.setCursor(Qt.PointingHandCursor)  # Меняем курсор при наведении
        browse_button.clicked.connect(self.browse_save_path)
        save_layout.addWidget(browse_button, 0, 2)
        
        save_group.setLayout(save_layout)
        layout.addWidget(save_group)
        
        # Группа с выбором секций для отчета
        sections_group = QGroupBox("Включить в отчет")
        sections_layout = QVBoxLayout()
        sections_layout.setContentsMargins(15, 20, 15, 15)
        sections_layout.setSpacing(8)
        
        # Чекбоксы для выбора секций
        self.sections = {}
        
        # Создаем сетку для чекбоксов (2 колонки)
        checkbox_grid = QGridLayout()
        checkbox_grid.setSpacing(10)
        
        # Отдельные стили для чекбоксов
        checkbox_style = """
            QCheckBox {
                font-size: 12px;
                color: #3e4458;
                spacing: 8px;
                padding: 5px 0;
            }
            QCheckBox:hover {
                color: #3a7bd5;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
        """
        
        # Информация о системе
        self.sections["system_info"] = QCheckBox("Общая информация о системе")
        self.sections["system_info"].setStyleSheet(checkbox_style)
        self.sections["system_info"].setChecked(True)
        self.sections["system_info"].setCursor(Qt.PointingHandCursor)
        checkbox_grid.addWidget(self.sections["system_info"], 0, 0)
        
        # Информация о сети
        self.sections["network_info"] = QCheckBox("Информация о сети")
        self.sections["network_info"].setStyleSheet(checkbox_style)
        self.sections["network_info"].setChecked(True)
        self.sections["network_info"].setCursor(Qt.PointingHandCursor)
        checkbox_grid.addWidget(self.sections["network_info"], 0, 1)
        
        # Информация о диспетчере устройств
        self.sections["device_manager_info"] = QCheckBox("Информация о диспетчере устройств")
        self.sections["device_manager_info"].setStyleSheet(checkbox_style)
        self.sections["device_manager_info"].setChecked(True)
        self.sections["device_manager_info"].setCursor(Qt.PointingHandCursor)
        checkbox_grid.addWidget(self.sections["device_manager_info"], 1, 0)
        
        sections_layout.addLayout(checkbox_grid)
        
        # Кнопка "Выбрать все"
        select_all_button = QPushButton("Выбрать все")
        select_all_button.setObjectName("select-all")
        select_all_button.setCursor(Qt.PointingHandCursor)
        select_all_button.clicked.connect(self.select_all_sections)
        sections_layout.addWidget(select_all_button, alignment=Qt.AlignRight)
        
        sections_group.setLayout(sections_layout)
        layout.addWidget(sections_group)
        
        # Кнопки действий
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(15)
        
        # Добавляем растягивающийся элемент для смещения кнопок вправо
        buttons_layout.addStretch()
        
        # Кнопка генерации отчета
        generate_button = QPushButton("Сгенерировать")
        generate_button.setObjectName("generate")
        generate_button.setCursor(Qt.PointingHandCursor)
        generate_button.clicked.connect(lambda: self.generate_report(dialog))
        buttons_layout.addWidget(generate_button)
        
        layout.addLayout(buttons_layout)
        
        # Показываем диалог
        dialog.exec_()
    
    def browse_save_path(self):
        """
        Открывает диалог выбора пути для сохранения отчета
        """
        # Получаем текущий путь
        current_path = self.path_edit.text()
        
        # Получаем директорию и имя файла
        if current_path:
            directory = os.path.dirname(current_path)
            filename = os.path.basename(current_path)
        else:
            documents_path = os.path.expanduser("~/Документы")
            # Получаем имя компьютера для имени файла
            computer_name = self.system_monitor.system_tab.monitor.get_system_info().get("Имя компьютера", "unknown")
            filename = f"{computer_name}_report_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.txt"
        
        # Открываем диалог сохранения
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет",
            os.path.join(directory, filename),
            "Текстовые файлы (*.txt);;Все файлы (*.*)"
        )
        
        # Если пользователь выбрал путь, обновляем текстовое поле
        if path:
            self.path_edit.setText(path)
    
    def select_all_sections(self):
        """
        Выбирает или снимает выбор всех секций отчета
        """
        # Проверяем, все ли чекбоксы отмечены
        all_checked = all(checkbox.isChecked() for checkbox in self.sections.values())
        
        # Если все отмечены, то снимаем все галочки, иначе отмечаем все
        for checkbox in self.sections.values():
            checkbox.setChecked(not all_checked)
    
    def generate_report(self, dialog):
        """
        Генерирует отчет о системе
        """
        # Получаем путь для сохранения
        save_path = self.path_edit.text()
        
        # Если путь не выбран, показываем предупреждение
        if not save_path:
            QMessageBox.warning(self, "Ошибка", "Пожалуйста, укажите путь для сохранения отчета.")
            return
        
        try:
            # Открываем файл для записи
            with open(save_path, 'w', encoding='utf-8') as f:
                # Получаем имя компьютера для отчета
                computer_name = self.system_monitor.system_tab.monitor.get_system_info().get("Имя компьютера", "unknown")
                
                # Заголовок отчета с именем компьютера
                f.write("=" * 80 + "\n")
                f.write(f"ОТЧЕТ О СИСТЕМЕ - {computer_name} - {datetime.datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                # Информация о системе
                if "system_info" in self.sections and self.sections["system_info"].isChecked():
                    f.write("-" * 40 + "\n")
                    f.write("ОБЩАЯ ИНФОРМАЦИЯ О СИСТЕМЕ\n")
                    f.write("-" * 40 + "\n")
                    
                    system_info = self.system_monitor.system_tab.monitor.get_system_info()
                    if isinstance(system_info, dict):
                        for key, value in system_info.items():
                            f.write(f"{key}: {value}\n")
                    else:
                        f.write(f"Информация о системе: {system_info}\n")
                    f.write("\n")
                
                # Информация о сети
                if "network_info" in self.sections and self.sections["network_info"].isChecked():
                    f.write("-" * 40 + "\n")
                    f.write("ИНФОРМАЦИЯ О СЕТИ\n")
                    f.write("-" * 40 + "\n")
                    
                    try:
                        network_info = self.system_monitor.system_tab.monitor.get_network_io()
                        if isinstance(network_info, dict):
                            for adapter, data in network_info.items():
                                f.write(f"Сетевой адаптер: {adapter}\n")
                                if isinstance(data, dict):
                                    for key, value in data.items():
                                        f.write(f"  {key}: {value}\n")
                                else:
                                    f.write(f"  Информация: {data}\n")
                                f.write("\n")
                        else:
                            f.write(f"Информация о сети: {network_info}\n\n")
                    except Exception as e:
                        f.write(f"Не удалось получить информацию о сети: {str(e)}\n\n")
                
                # НОВОЕ: Информация о диспетчере устройств
                if "device_manager_info" in self.sections and self.sections["device_manager_info"].isChecked():
                    f.write("-" * 40 + "\n")
                    f.write("ИНФОРМАЦИЯ О ДИСПЕТЧЕРЕ УСТРОЙСТВ\n")
                    f.write("-" * 40 + "\n")
                    
                    try:
                        from system_monitor import get_cpu_info_for_device_manager, get_gpu_info_for_device_manager
                        from system_monitor import get_disk_info_for_device_manager, get_network_info_for_device_manager
                        from system_monitor import get_motherboard_info_for_device_manager, get_audio_info_for_device_manager
                        from system_monitor import get_monitors_info_for_device_manager
                        
                        # Добавляем информацию о различных категориях устройств
                        categories = [
                            ("Процессоры", get_cpu_info_for_device_manager()),
                            ("Видеокарты", get_gpu_info_for_device_manager()),
                            ("Диски", get_disk_info_for_device_manager()),
                            ("Сетевые адаптеры", get_network_info_for_device_manager()),
                            ("Материнская плата", get_motherboard_info_for_device_manager()),
                            ("Аудио устройства", get_audio_info_for_device_manager()),
                            ("Мониторы", get_monitors_info_for_device_manager())
                        ]
                        
                        for category_name, devices in categories:
                            if devices:
                                f.write(f"\n{category_name}:\n")
                                f.write("-" * 30 + "\n")
                                
                                for device_id, device_info in devices.items():
                                    if isinstance(device_info, dict):
                                        f.write(f"Устройство: {device_info.get('name', 'Неизвестно')}\n")
                                        for key, value in device_info.items():
                                            if key != 'name' and value:
                                                f.write(f"  {key}: {value}\n")
                                        f.write("\n")
                                    else:
                                        f.write(f"  {device_id}: {device_info}\n\n")
                            else:
                                f.write(f"\n{category_name}: информация недоступна\n")
                            
                    except Exception as e:
                        f.write(f"Не удалось получить информацию о диспетчере устройств: {str(e)}\n")
                    f.write("\n")
                
                # Заключение
                f.write("=" * 80 + "\n")
                f.write("КОНЕЦ ОТЧЕТА\n")
                f.write("=" * 80 + "\n")
            
            # Показываем сообщение об успешном сохранении
            QMessageBox.information(
                self,
                "Успех",
                f"Отчет успешно сохранен в:\n{save_path}"
            )
            
            # Закрываем диалог
            dialog.accept()
            
        except Exception as e:
            # В случае ошибки показываем сообщение
            QMessageBox.critical(
                self,
                "Ошибка",
                f"Не удалось сохранить отчет:\n{str(e)}"
            )

def create_app():
    """
    Создает и настраивает приложение
    """
    app = QApplication([])
    app.setStyle('Fusion')  # Используем стиль Fusion
    
    # Устанавливаем иконку приложения
    icon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "icon.ico"))
    app.setWindowIcon(QIcon(icon_path))
    
    # Отключаем фокусную обводку глобально
    app.setAttribute(Qt.AA_UseHighDpiPixmaps)  # Для лучшей отрисовки на HiDPI экранах
    app.setAttribute(Qt.AA_DisableWindowContextHelpButton)  # Отключаем кнопку помощи в заголовке
    
    # Устанавливаем глобальные стили для приложения
    app.setStyleSheet("""
        QMainWindow, QDialog, QWidget {
            background-color: #ffffff;
        }
        
        * {
            outline: none;
            border-style: none;
        }
        
        /* Глобальное отключение обводки фокуса */
        QTabWidget:focus, QTabBar:focus, QTabBar::tab:focus, QWidget:focus {
            border: none;
            outline: none;
            padding: 0px;
            margin: 0px;
            border-width: 0px;
            border-color: transparent;
            background-color: transparent;
        }
        
        QGroupBox {
            border: 1px solid #e0e6f0;
            border-radius: 5px;
            margin-top: 1.1em;
            font-weight: bold;
            background-color: white;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 3px 5px;
            background-color: white;
            border-radius: 3px;
            color: #3a7bd5;
        }
        QTabWidget::pane { 
            border: 1px solid #c0c8e0;
            border-radius: 0px;
            background-color: white;
            padding: 2px;
        }
        QTabBar::tab {
            background-color: #f0f5ff;
            border: 1px solid #c0c8e0;
            border-bottom-color: #c0c8e0;
            padding: 4px 8px;
            margin-right: 0px;
            color: #434d66;
            min-width: 130px;
            font-weight: bold;
            font-size: 10px;
            outline: none;
            cursor: pointer;
        }
        QTabBar::tab:selected {
            background-color: #3a7bd5;
            border: 1px solid #3a7bd5;
            border-bottom-color: #3a7bd5;
            color: white;
            outline: none;
        }
        QTabBar::tab:hover:!selected {
            background-color: #d6e4ff;
        }
        QStatusBar {
            background-color: #f5f8ff;
            color: #3a7bd5;
            border-top: 1px solid #e0e6f0;
        }
        QProgressBar {
            text-align: center;
            border: 1px solid #e0e6f0;
            border-radius: 4px;
            background-color: #f5f8ff;
            height: 16px;
        }
        QProgressBar::chunk {
            background-color: #3a7bd5;
            border-radius: 3px;
        }
        QPushButton {
            background-color: #f5f8ff;
            border: 1px solid #e0e6f0;
            border-radius: 4px;
            padding: 6px 12px;
            color: #3a7bd5;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #d0e0ff;
        }
        QPushButton:pressed {
            background-color: #3a7bd5;
            color: white;
        }
        QLabel {
            color: #3e4458;
        }
        QLineEdit {
            border: 1px solid #e0e6f0;
            border-radius: 4px;
            padding: 5px;
            background-color: white;
        }
        QLineEdit:focus {
            border: 1px solid #3a7bd5;
        }
        QComboBox {
            border: 1px solid #e0e6f0;
            border-radius: 4px;
            padding: 5px;
            background-color: white;
        }
        QHeaderView::section {
            background-color: #f5f8ff;
            border: 1px solid #e0e6f0;
            padding: 4px;
        }
        QTableView {
            border: 1px solid #e0e6f0;
            gridline-color: #e0e6f0;
            selection-background-color: #d0e0ff;
        }
    """)
    
    # Создаем и показываем главное окно
    main_window = MainWindow()
    main_window.show()
    
    return app, main_window
