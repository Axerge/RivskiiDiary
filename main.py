from PyQt5 import QtWidgets, QtCore, QtGui
import sys
import pyperclip
import json
import os
import keyboard
import threading
import ctypes
import win32api
import win32gui
import win32process
import webbrowser
import time
import requests
import subprocess
from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def get_current_version():
    try:
        with open(resource_path('version.txt'), 'r') as f:
            return f.read().strip()
    except Exception:
        return "1.0.0"

def check_for_updates():
    try:
        # Здесь должен быть URL вашего API или файла с последней версией
        response = requests.get('https://api.github.com/repos/yourusername/RivskiiDiary/releases/latest')
        if response.status_code == 200:
            latest_version = response.json()['tag_name'].replace('v', '')
            current_version = get_current_version()
            
            # Сравниваем версии
            latest_parts = [int(x) for x in latest_version.split('.')]
            current_parts = [int(x) for x in current_version.split('.')]
            
            for i in range(3):
                if latest_parts[i] > current_parts[i]:
                    return True, latest_version
                elif latest_parts[i] < current_parts[i]:
                    return False, current_version
            return False, current_version
        else:
            print(f"Ошибка при получении данных: {response.status_code}")
            return False, get_current_version()
    except Exception as e:
        print(f"Ошибка при проверке обновлений: {str(e)}")
        return False, get_current_version()
    finally:
        # Гарантируем возврат значений даже в случае непредвиденных ошибок
        return False, get_current_version()

def download_update():
    try:
        # Здесь должен быть URL для скачивания обновления
        response = requests.get('https://api.github.com/repos/yourusername/RivskiiDiary/releases/latest')
        if response.status_code == 200:
            download_url = response.json()['assets'][0]['browser_download_url']
            
            # Создаем временную директорию для обновления
            temp_dir = os.path.join(os.getenv('TEMP'), 'RivskiiDiary_update')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Скачиваем обновление
            update_file = os.path.join(temp_dir, 'RivskiiDiary_update.exe')
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(update_file, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                # Создаем bat-файл для обновления
                bat_file = os.path.join(temp_dir, 'update.bat')
                current_exe = sys.executable
                with open(bat_file, 'w') as f:
                    f.write(f'''@echo off
timeout /t 2 /nobreak
del "{current_exe}"
move "{update_file}" "{current_exe}"
start "" "{current_exe}"
del "%~f0"
''')
                return bat_file
    except Exception:
        return None

class TemplateWindow(QtWidgets.QWidget):
    def __init__(self, title, content):
        super().__init__()
        self.setWindowTitle(title)
        self.setGeometry(0, 0, 300, 200)  # Позиционируем окно
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        layout = QtWidgets.QVBoxLayout()

        # Создаем текстовое поле для отображения содержимого
        self.content_display = QtWidgets.QTextEdit()
        self.content_display.setPlainText(content)
        self.content_display.setReadOnly(True)  # Делаем текстовое поле только для чтения
        layout.addWidget(self.content_display)

        # Добавляем заметку о закрытии окна
        note_label = QtWidgets.QLabel("Нажмите на любое место в основном окне, чтобы закрыть это окно.")
        layout.addWidget(note_label)

        self.setLayout(layout)

    def mouseDoubleClickEvent(self, event):
        self.close()  # Закрываем окно при двойном клике

    def set_content(self, content):
        self.content_display.setPlainText(content)  # Устанавливаем текст в текстовом поле

def get_current_layout():
    # Получаем дескриптор активного окна
    hwnd = win32gui.GetForegroundWindow()
    # Получаем ID потока
    thread_id, _ = win32process.GetWindowThreadProcessId(hwnd)
    # Получаем раскладку клавиатуры для потока
    layout = ctypes.windll.user32.GetKeyboardLayout(thread_id)
    return hex(layout)

def switch_keyboard_layout(layout):
    # Переключаемся на указанную раскладку
    ctypes.windll.user32.LoadKeyboardLayoutW(layout, 1)  # Загружаем указанную раскладку

class CustomTreeWidget(QtWidgets.QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent  # Сохраняем ссылку на родительское окно
        self.setColumnCount(2)  # Устанавливаем количество столбцов
        self.setHeaderLabels(["Название", "Содержание"])  # Устанавливаем заголовки столбцов

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()  # Снимаем выделение, если кликнули на пустое пространство
            if self.parent_window.template_window is not None:
                self.parent_window.template_window.close()  # Закрываем окно шаблона
                self.parent_window.template_window = None  # Сбрасываем ссылку на окно
        # Убираем функциональность показа содержимого при нажатии на элемент
        super().mousePressEvent(event)  # Вызываем стандартное поведение

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Return or event.key() == QtCore.Qt.Key_Enter:
            current_item = self.currentItem()
            if current_item:
                self.parent_window.insert_template(current_item)  # Call the same method as double-click
        else:
            super().keyPressEvent(event)  # Ensure other key events are handled

class CustomListWidget(QtWidgets.QListWidget):
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()  # Снимаем выделение, если кликнули на пустое пространство
        super().mousePressEvent(event)  # Вызываем стандартное поведение

class CustomTriggerListWidget(QtWidgets.QListWidget):
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if item is None:
            self.clearSelection()  # Снимаем выделение, если кликнули на пустое пространство
        super().mousePressEvent(event)  # Вызываем стандартное поведение

class SplashScreen(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Загрузка...')
        self.setGeometry(0, 0, 400, 300)  # Устанавливаем размер окна загрузки
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)  # Без рамки и поверх всех окон
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)  # Делаем фон прозрачным

        # Устанавливаем иконку для SplashScreen
        self.setWindowIcon(QtGui.QIcon(resource_path('img/icon.png')))  # Используем resource_path

        # Центрируем окно на экране
        self.center()

        layout = QtWidgets.QVBoxLayout()
        self.setLayout(layout)

        # Добавляем растяжимое пространство для отступа сверху
        layout.addStretch(1)  # Это добавит растяжимое пространство вверху

        # Логотип
        logo_label = QtWidgets.QLabel()
        logo_pixmap = QtGui.QPixmap(resource_path('img/logo.png'))  # Используем resource_path
        logo_label.setPixmap(logo_pixmap.scaled(100, 100, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        logo_label.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(logo_label)

        # Название
        title_label = QtWidgets.QLabel("Rivskii Diary")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #ffffff;  /* Белый текст */
            }
        """)
        layout.addWidget(title_label)

        # Описание
        description_label = QtWidgets.QLabel("by Geralt Rivskii")
        description_label.setAlignment(QtCore.Qt.AlignCenter)
        description_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #ffffff;  /* Белый текст */
            }
        """)
        layout.addWidget(description_label)

        # Добавляем немного пространства
        layout.addStretch(1)  # Это добавит растяжимое пространство внизу, чтобы элементы были по центру

        # Прогресс-бар
        progress_bar = QtWidgets.QProgressBar()
        progress_bar.setRange(0, 0)  # Индикатор неопределенного прогресса
        progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #34495e;  /* Цвет рамки */
                border-radius: 5px;
                background-color: #f0f0f0;  /* Цвет фона прогресс-бара */
            }
            QProgressBar::chunk {
                background-color: #bd00ff;  /* Цвет заполнения прогресс-бара */
                width: 20px;
            }
        """)
        layout.addWidget(progress_bar)

        # Устанавливаем стиль для закругленных краев
        self.setStyleSheet("background-color: rgba(0, 0, 0, 0); border-radius: 20px;")  # Прозрачный фон и закругленные края

    def paintEvent(self, event):
        # Создаем градиент
        gradient = QtGui.QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QtGui.QColor(189, 0, 255))  # Фиолетовый
        gradient.setColorAt(1, QtGui.QColor(255, 105, 180))  # Розовый

        # Устанавливаем градиент как фон
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), gradient)
        painter.end()

    def center(self):
        # Получаем геометрию экрана и центра
        screen_geometry = QtWidgets.QDesktopWidget().availableGeometry().center()
        # Перемещаем окно в центр
        self.move(screen_geometry.x() - self.width() // 2, screen_geometry.y() - self.height() // 2)

class RivskiiDiary(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Rivskii Diary')
        
        # Устанавливаем иконку приложения
        self.setWindowIcon(QtGui.QIcon(resource_path('img/icon.png')))  # Используем resource_path

        # Устанавливаем размер окна
        self.setGeometry(100, 100, 630, 800)  # Размер по умолчанию
        
        # История буфера обмена
        self.clipboard_history = []
        
        # Шаблоны
        self.templates = {}
        
        # Триггеры
        self.triggers = {}  # Инициализируем словарь триггеров
        
        # Горячая клавиша
        self.hotkey = "win+v"  # Горячая клавиша по умолчанию
        
        # Элементы интерфейса
        self.status_label = QtWidgets.QLabel("")  # Инициализация статусной метки
        self.create_widgets()  # Сначала создаем виджеты
        
        # Загружаем настройки после создания виджетов
        self.load_settings()
        
        # Загружаем историю и шаблоны после создания виджетов
        self.load_history()
        self.load_templates()
        
        # Запускаем мониторинг буфера обмена после создания виджетов
        self.monitor_clipboard()

        # Устанавливаем стиль
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QPushButton {
                background-color: #28a745;  /* Зеленый цвет для всех кнопок */
                color: white;
                border-radius: 10px;
                padding: 10px;  
                font-size: 14px;  
                border: none;
            }
            QPushButton:hover {
                background-color: #218838;  /* Темно-зеленый при наведении */
            }
            QPushButton.delete-button, QPushButton.clear-button, QPushButton.red-button {
                background-color: #dc3545;  /* Красный цвет для кнопок "Удалить" и "Очистить" */
            }
            QPushButton.delete-button:hover, QPushButton.clear-button:hover, QPushButton.red-button:hover {
                background-color: #c82333;  /* Темно-красный при наведении */
            }
            QListWidget {
                font-size: 14px;
                border: 1px solid #ccc;
                border-radius: 10px;
                padding: 5px;
                background-color: #ffffff;
            }
            QListWidgetItem {
                padding: 10px;  
                border-radius: 5px;
            }
            QListWidget::item:selected {
                background-color: #0078d7;
                color: white;
            }
            QTabWidget::pane {
                border: none;  /* Убираем рамку вокруг вкладок */
            }
            QTabBar::tab {
                background: #e0e0e0;
                padding: 15px;  /* Увеличиваем отступы внутри вкладок */
                margin: 0 5px;  /* Отступы между вкладками */
                border-radius: 10px;  /* Закругленные края */
                font-weight: bold;  /* Жирный шрифт */
                min-width: 100px;  /* Минимальная ширина вкладки */
            }
            QTabBar::tab:selected {
                background: #0078d7;
                color: white;
            }
            QLabel {
                font-size: 12px;
                color: #333;
            }
        """)

        # Центрируем окно на экране
        self.center()

        # Загружаем позицию окна
        self.load_window_position()

        # Создаем иконку в системном трее
        self.create_tray_icon()

        # Регистрируем глобальную горячую клавишу
        keyboard.add_hotkey(self.hotkey, self.show_window)

        self.template_window = None  # Добавляем атрибут для хранения ссылки на окно шаблона
        self.current_layout = get_current_layout()  # Инициализируем текущую раскладку
        self.keyboard_hook = None  # Инициализируем атрибут keyboard_hook

        # Вызываем этот метод в методе __init__ после инициализации всех атрибутов
        self.monitor_triggers()

        # Загружаем триггеры после создания виджетов
        self.load_triggers()  # Загрузка триггеров

        # Проверяем обновления при запуске
        self.check_updates_on_startup()

    def check_updates_on_startup(self):
        has_update, version = check_for_updates()
        if has_update:
            reply = QtWidgets.QMessageBox.question(
                self, 
                'Доступно обновление',
                f'Доступна новая версия {version}. Хотите обновить программу?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.perform_update()

    def perform_update(self):
        bat_file = download_update()
        if bat_file:
            try:
                subprocess.Popen(['cmd', '/c', bat_file])
                QtWidgets.qApp.quit()
            except Exception as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    'Ошибка обновления',
                    f'Произошла ошибка при обновлении: {str(e)}'
                )
        else:
            QtWidgets.QMessageBox.critical(
                self,
                'Ошибка обновления',
                'Не удалось скачать обновление. Попробуйте позже.'
            )

    def center(self):
        # Получаем геометрию экрана
        screen = QtWidgets.QDesktopWidget().screenGeometry()
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

    def create_widgets(self):
        # Центральный виджет
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        # Макет
        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)  # Уменьшаем отступы
        central_widget.setLayout(layout)

        # Виджет вкладок
        tab_widget = QtWidgets.QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: none;  /* Убираем рамку вокруг вкладок */
            }
            QTabBar::tab {
                background: #e0e0e0;  /* Цвет фона вкладок */
                padding: 10px;  /* Уменьшаем отступы внутри вкладок */
                margin: 0 2px;  /* Уменьшаем отступы между вкладками */
                border-radius: 10px;  /* Закругленные края */
                font-weight: bold;  /* Жирный шрифт */
                min-width: 100px;  /* Минимальная ширина вкладки */
            }
            QTabBar::tab:selected {
                background: #0078d7;  /* Цвет фона для выбранной вкладки */
                color: white;  /* Цвет текста для выбранной вкладки */
            }
        """)
        layout.addWidget(tab_widget)

        # Вкладка истории
        history_tab = QtWidgets.QWidget()
        history_layout = QtWidgets.QVBoxLayout()
        history_tab.setLayout(history_layout)

        # Используем кастомный QListWidget
        self.history_list = CustomListWidget()  # Изменяем на кастомный виджет
        history_layout.addWidget(self.history_list)

        # Добавляем кнопку очистки истории
        self.clear_history_button = QtWidgets.QPushButton("Очистить историю")
        self.clear_history_button.setIcon(QtGui.QIcon(resource_path('img/delete_icon.png')))  # Используем resource_path
        self.clear_history_button.setObjectName("clear-button")  # Устанавливаем имя объекта для стиля
        self.clear_history_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")  # Жирный шрифт
        self.clear_history_button.clicked.connect(self.clear_history)
        history_layout.addWidget(self.clear_history_button)

        tab_widget.addTab(history_tab, 'История')

        # Вкладка шаблонов
        templates_tab = QtWidgets.QWidget()
        templates_layout = QtWidgets.QVBoxLayout()
        templates_tab.setLayout(templates_layout)

        # Search input for templates
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию и содержимому...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #0078d7;  /* Цвет рамки */
                border-radius: 10px;  /* Закругленные края */
                padding: 10px;  /* Отступы внутри */
                font-size: 14px;  /* Размер шрифта */
                color: #333;  /* Цвет текста */
            }
            QLineEdit:focus {
                border: 2px solid #0056b3;  /* Цвет рамки при фокусе */
                background-color: #f0f8ff;  /* Цвет фона при фокусе */
            }
        """)
        self.search_input.textChanged.connect(self.filter_templates)  # Connect the textChanged signal to the filter method
        templates_layout.addWidget(self.search_input)

        # Используем кастомный QTreeWidget
        self.template_tree = CustomTreeWidget(self)  # Передаем ссылку на родительское окно
        self.template_tree.setHeaderHidden(True)  # Скрываем заголовок
        self.template_tree.setFocusPolicy(QtCore.Qt.StrongFocus)  # Устанавливаем политику фокуса
        self.template_tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #ccc;  /* Цвет рамки */
                border-radius: 10px;  /* Закругленные края */
                background-color: #ffffff;  /* Цвет фона */
            }
            QTreeWidget::item {
                border-radius: 5px;  /* Закругленные края для элементов списка */
            }
            QTreeWidget::item:selected {
                background-color: #0078d7;  /* Цвет фона для выделенного элемента */
                color: white;  /* Цвет текста для выделенного элемента */
            }
        """)
        templates_layout.addWidget(self.template_tree)

        # Установка ширины столбца названий шаблонов
        self.template_tree.setColumnWidth(0, 200)  # Установите нужную ширину в пикселях

        # Подключаем событие двойного клика к дереву шаблонов
        self.template_tree.itemDoubleClicked.connect(self.insert_template)

        # Горизонтальный макет для кнопок управления шаблонами
        button_layout = QtWidgets.QHBoxLayout()

        # Кнопки для управления шаблонами
        self.add_folder_button = QtWidgets.QPushButton("Добавить папку")
        self.add_folder_button.setIcon(QtGui.QIcon(resource_path('img/folder_icon.png')))  # Используем resource_path
        self.add_folder_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.add_folder_button.clicked.connect(self.add_folder)
        button_layout.addWidget(self.add_folder_button)

        self.add_template_button = QtWidgets.QPushButton("Добавить шаблон")
        self.add_template_button.setIcon(QtGui.QIcon(resource_path('img/add_icon.png')))  # Используем resource_path
        self.add_template_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.add_template_button.clicked.connect(self.add_template)
        button_layout.addWidget(self.add_template_button)

        self.edit_template_button = QtWidgets.QPushButton("Изменить")
        self.edit_template_button.setIcon(QtGui.QIcon(resource_path('img/edit_icon.png')))  # Используем resource_path
        self.edit_template_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.edit_template_button.clicked.connect(self.edit_template)
        button_layout.addWidget(self.edit_template_button)

        self.delete_template_button = QtWidgets.QPushButton("Удалить")
        self.delete_template_button.setIcon(QtGui.QIcon(resource_path('img/delete_icon.png')))  # Используем resource_path
        self.delete_template_button.setObjectName("delete-button")  # Устанавливаем имя объекта для стиля
        self.delete_template_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")  # Жирный шрифт
        self.delete_template_button.clicked.connect(self.delete_template)
        button_layout.addWidget(self.delete_template_button)

        # Добавляем макет кнопок в макет шаблонов
        templates_layout.addLayout(button_layout)

        # Горизонтальный макет для кнопок перемещения
        move_button_layout = QtWidgets.QHBoxLayout()

        # Добавляем кнопки для перемещения шаблонов
        self.move_up_button = QtWidgets.QPushButton("Вверх")
        self.move_up_button.setIcon(QtGui.QIcon(resource_path('img/up_icon.png')))  # Используем resource_path
        self.move_up_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.move_up_button.clicked.connect(self.move_template_up)
        move_button_layout.addWidget(self.move_up_button)

        self.move_down_button = QtWidgets.QPushButton("Вниз")
        self.move_down_button.setIcon(QtGui.QIcon(resource_path('img/down_icon.png')))  # Используем resource_path
        self.move_down_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.move_down_button.clicked.connect(self.move_template_down)
        move_button_layout.addWidget(self.move_down_button)

        # Добавляем макет кнопок перемещения в макет шаблонов
        templates_layout.addLayout(move_button_layout)

        tab_widget.addTab(templates_tab, 'Шаблоны')

        # Вкладка триггеров
        triggers_tab = QtWidgets.QWidget()
        triggers_layout = QtWidgets.QVBoxLayout()
        triggers_tab.setLayout(triggers_layout)

        # Search input for triggers
        self.trigger_search_input = QLineEdit()
        self.trigger_search_input.setPlaceholderText("Поиск по названию и содержимому триггера...")
        self.trigger_search_input.setStyleSheet("""
            QLineEdit {
                border: 2px solid #0078d7;  /* Цвет рамки */
                border-radius: 10px;  /* Закругленные края */
                padding: 10px;  /* Отступы внутри */
                font-size: 14px;  /* Размер шрифта */
                color: #333;  /* Цвет текста */
            }
            QLineEdit:focus {
                border: 2px solid #0056b3;  /* Цвет рамки при фокусе */
                background-color: #f0f8ff;  /* Цвет фона при фокусе */
            }
        """)
        self.trigger_search_input.textChanged.connect(self.filter_triggers)  # Connect the textChanged signal to the filter method
        triggers_layout.addWidget(self.trigger_search_input)

        # Используем кастомный QListWidget для триггеров
        self.trigger_list = CustomTriggerListWidget()  # Изменяем на кастомный виджет
        self.trigger_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ccc;  /* Цвет рамки */
                border-radius: 10px;  /* Закругленные края */
                background-color: #ffffff;  /* Цвет фона */
                padding: 5px;  /* Отступы внутри виджета */
            }
            QListWidget::item {
                border-radius: 5px;  /* Закругленные края для элементов списка */
            }
            QListWidget::item:selected {
                background-color: #0078d7;  /* Цвет фона для выделенного элемента */
                color: white;  /* Цвет текста для выделенного элемента */
            }
        """)
        triggers_layout.addWidget(self.trigger_list)

        # Горизонтальный макет для кнопок управления триггерами
        trigger_button_layout = QtWidgets.QHBoxLayout()

        # Кнопки для управления триггерами
        self.add_trigger_button = QtWidgets.QPushButton("Добавить триггер")
        self.add_trigger_button.setIcon(QtGui.QIcon(resource_path('img/add_icon.png')))  # Используем resource_path
        self.add_trigger_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.add_trigger_button.clicked.connect(self.add_trigger)
        trigger_button_layout.addWidget(self.add_trigger_button)

        self.edit_trigger_button = QtWidgets.QPushButton("Изменить триггер")
        self.edit_trigger_button.setIcon(QtGui.QIcon(resource_path('img/edit_icon.png')))  # Используем resource_path
        self.edit_trigger_button.setStyleSheet("font-weight: bold;")  # Жирный шрифт
        self.edit_trigger_button.clicked.connect(self.edit_trigger)
        trigger_button_layout.addWidget(self.edit_trigger_button)

        self.delete_trigger_button = QtWidgets.QPushButton("Удалить триггер")
        self.delete_trigger_button.setIcon(QtGui.QIcon(resource_path('img/delete_icon.png')))  # Используем resource_path
        self.delete_trigger_button.setObjectName("red-button")  # Устанавливаем имя объекта для стиля
        self.delete_trigger_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")  # Жирный шрифт
        self.delete_trigger_button.clicked.connect(self.delete_trigger)
        trigger_button_layout.addWidget(self.delete_trigger_button)

        # Добавляем макет кнопок в макет триггеров
        triggers_layout.addLayout(trigger_button_layout)

        # Перемещаем кнопку очистки триггеров ниже кнопок управления триггерами
        self.clear_triggers_button = QtWidgets.QPushButton("Очистить триггеры")
        self.clear_triggers_button.setIcon(QtGui.QIcon(resource_path('img/delete_icon.png')))  # Используем resource_path
        self.clear_triggers_button.setObjectName("clear-button")  # Устанавливаем имя объекта для стиля
        self.clear_triggers_button.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")  # Жирный шрифт
        self.clear_triggers_button.clicked.connect(self.clear_triggers)
        triggers_layout.addWidget(self.clear_triggers_button)  # Добавляем кнопку очистки триггеров после кнопок управления

        tab_widget.addTab(triggers_tab, 'Триггеры')

        # Вкладка настроек
        settings_tab = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout()
        settings_tab.setLayout(settings_layout)

        # Ввод горячей клавиши
        self.hotkey_label = QtWidgets.QLabel("Горячая клавиша для открытия с трея: *По стандарту WIN+V*")
        self.hotkey_label.setStyleSheet("""
            QLabel {
                font-size: 14px;  /* Размер шрифта */
                color: #ffffff;  /* Цвет текста */
                font-weight: bold;  /* Жирный шрифт */
                margin-bottom: 10px;  /* Отступ снизу */
            }
        """)
        settings_layout.addWidget(self.hotkey_label)

        # Создаем комбобокс для модификаторов клавиш
        self.modifier_combo = QtWidgets.QComboBox()
        self.modifier_combo.addItems(["Не выбрано", "Ctrl", "Alt", "Shift", "Win"])  # Добавляем варианты модификаторов
        self.modifier_combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #ccc;  /* Цвет рамки */
                padding: 5px;  /* Отступы внутри */
                background-color: #ffffff;  /* Цвет фона */
                font-size: 14px;  /* Размер шрифта */
            }
            QComboBox::drop-down {
                border: none;  /* Убираем рамку у выпадающего списка */
                background-color: #ffffff;  /* Цвет фона выпадающего списка */
                width: 30px;  /* Ширина выпадающего списка */
            }
            QComboBox::down-arrow {
                image: url(resource_path('img/down_icon.png'));  /* Укажите путь к вашей стрелке вниз */
                width: 15px;  /* Ширина стрелки */
                height: 15px;  /* Высота стрелки */
                margin: 5px;  /* Отступ для стрелки */
                border-radius: 10px;  /* Закругленные края */
            }
            QComboBox::item {
                padding: 5px;  /* Отступы для элементов выпадающего списка */
            }
            QComboBox::item:selected {
                background-color: #0078d7;  /* Цвет фона для выделенного элемента */
                color: white;  /* Цвет текста для выделенного элемента */
            }
        """)
        settings_layout.addWidget(self.modifier_combo)

        # Создаем поле ввода для клавиши
        self.hotkey_input = QtWidgets.QLineEdit()
        self.hotkey_input.setPlaceholderText("Введите клавишу (например, V)")
        self.hotkey_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ccc;  /* Цвет рамки */
                border-radius: 10px;  /* Закругленные края */
                padding: 5px;  /* Отступы внутри */
                background-color: #ffffff;  /* Цвет фона */
                font-size: 14px;  /* Размер шрифта */
            }
        """)
        settings_layout.addWidget(self.hotkey_input)

        # Чекбокс для сворачивания в трей
        self.tray_checkbox = QtWidgets.QCheckBox("Свернуть в трей при закрытии")
        self.tray_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;  /* Белый текст */
                font-weight: bold;  /* Жирный текст */
            }
        """)
        settings_layout.addWidget(self.tray_checkbox)

        # Кнопка сохранения
        self.save_button = QtWidgets.QPushButton("Сохранить")
        self.save_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;  /* Зеленый цвет */
                color: white;
                font-weight: bold;  /* Жирный шрифт */
                border-radius: 10px;  /* Закругленные края */
                padding: 10px;  /* Отступы */
            }
            QPushButton:hover {
                background-color: #218838;  /* Темно-зеленый при наведении */
            }
        """)
        self.save_button.clicked.connect(self.save_settings)
        settings_layout.addWidget(self.save_button)

        # Статусная метка для сообщений
        self.status_label = QtWidgets.QLabel("")  # Инициализация статусной метки
        self.status_label.setStyleSheet("""
            QLabel {
                color: #0078d7;  /* Цвет текста */
                background-color: #e0f7fa;  /* Цвет фона */
                border: 1px solid #0078d7;  /* Граница */
                border-radius: 5px;  /* Закругленные углы */
                padding: 5px;  /* Отступы */
                font-size: 12px;  /* Размер шрифта */
            }
        """)  # Добавляем стиль к статусной метке
        self.status_label.setVisible(False)  # Скрываем статусную метку изначально
        settings_layout.addWidget(self.status_label)  # Добавляем статусную метку в макет

        # Добавляем немного пространства
        settings_layout.addStretch(1)  # Добавляем растяжимое пространство внизу

        # Кнопка открытия папки с JSON файлами
        self.open_folder_button = QtWidgets.QPushButton("Открыть папку с файлами")
        self.open_folder_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;  /* Синий цвет */
                color: white;
                font-weight: bold;  /* Жирный шрифт */
                border-radius: 10px;  /* Закругленные края */
                padding: 10px;  /* Отступы */
            }
            QPushButton:hover {
                background-color: #0056b3;  /* Темно-синий при наведении */
            }
        """)
        self.open_folder_button.clicked.connect(self.open_data_directory)
        settings_layout.addWidget(self.open_folder_button)

        # В разделе настроек добавляем кнопку проверки обновлений
        self.check_updates_button = QtWidgets.QPushButton("Проверить обновления")
        self.check_updates_button.setStyleSheet("""
            QPushButton {
                background-color: #0078d7;  /* Синий цвет */
                color: white;
                font-weight: bold;  /* Жирный шрифт */
                border-radius: 10px;  /* Закругленные края */
                padding: 10px;  /* Отступы */
            }
            QPushButton:hover {
                background-color: #0056b3;  /* Темно-синий при наведении */
            }
        """)
        self.check_updates_button.clicked.connect(self.check_updates_manually)
        settings_layout.addWidget(self.check_updates_button)

        tab_widget.addTab(settings_tab, 'Настройки')

        # Вкладка Инфо
        info_tab = QtWidgets.QWidget()
        info_layout = QtWidgets.QGridLayout()  # Use a grid layout for better organization
        info_tab.setLayout(info_layout)

        # Добавляем иконку по центру
        icon_label = QtWidgets.QLabel()
        icon_pixmap = QtGui.QPixmap(resource_path('img/logo.png'))  # Используем resource_path
        icon_label.setPixmap(icon_pixmap.scaled(150, 150, QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))
        icon_label.setAlignment(QtCore.Qt.AlignCenter)
        info_layout.addWidget(icon_label, 0, 0, 1, 2)  # Center the icon in the grid

        # Название приложения
        title_label = QtWidgets.QLabel("Rivskii Diary")
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;  /* Цвет заголовка */
            }
        """)
        info_layout.addWidget(title_label, 1, 0, 1, 2)  # Span across two columns

        # Описание приложения
        description_label = QtWidgets.QLabel('Rivskii Diary — это ваше личное приложение менеджера буфера обмена с историей и шаблонами для часто используемого текста, '
                                             'созданное для того, чтобы помочь вам эффективно управлять тем, что вы копировали и вашими шаблонами. '
                                             'С такими функциями, как настраиваемые шаблоны, триггеры для быстрого ввода текста и удобный интерфейс, '
                                             'вы можете легко упростить свои задачи.'
                                             '\n\nШаблоны представляют собой удобный инструмент для экономии времени при наборе текста. Сохраните в одном месте все ваши часто используемые фразы, стандартные ответы, адреса и многое другое. Вы сможете быстро и просто вставлять любой шаблон, избегая повторного ввода и ошибок.'
                                             '\n\nТриггеры в приложении предназначены для автоматизации ввода текста. Они позволяют пользователям создавать короткие команды, которые при вводе заменяются на заранее определенные фразы или тексты.'
                                             '\n\nДля получения поддержки по любым вопросам, пожалуйста, свяжитесь с нами с помощью кнопок ниже!'
                                             '\n\nРазработчик: Geralt Rivskii | Александр Буравлёв | Это один и тот же человек:)')
        description_label.setAlignment(QtCore.Qt.AlignCenter)
        description_label.setWordWrap(True)  # Allow text to wrap
        description_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                color: #ffffff;  /* Цвет текста */
                font-weight: bold;
                margin: 10px 0;  /* Отступы сверху и снизу */
            }
        """)
        info_layout.addWidget(description_label, 2, 0, 1, 2)  # Span across two columns

        # Добавляем текстовое поле для описания проблемы
        info_label = QtWidgets.QLabel('')
        info_label.setWordWrap(True)  # Allow text to wrap
        info_label.setAlignment(QtCore.Qt.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #ffffff;  /* Цвет текста */
                font-weight: bold;
                margin: 10px 0;  /* Отступы сверху и снизу */
            }
        """)
        info_layout.addWidget(info_label, 3, 0, 1, 2)  # Span across two columns

        # Горизонтальный макет для кнопок
        button_layout = QtWidgets.QHBoxLayout()

        # Кнопка для связи через Discord
        discord_button = QtWidgets.QPushButton("Связаться через Discord (rivskii)")
        discord_button.setStyleSheet("font-weight: bold;")  # Set the font weight to bold
        discord_button.clicked.connect(lambda: webbrowser.open("https://discordapp.com/users/310459688380792832/"))
        button_layout.addWidget(discord_button)

        # Кнопка для связи через Telegram
        telegram_button = QtWidgets.QPushButton("Связаться через Telegram (@GrayHizi)")
        telegram_button.setStyleSheet("font-weight: bold;")  # Set the font weight to bold
        telegram_button.clicked.connect(lambda: webbrowser.open("https://t.me/GrayHizi"))
        button_layout.addWidget(telegram_button)

        # Добавляем горизонтальный макет кнопок в основной макет
        info_layout.addLayout(button_layout, 5, 0, 1, 2)  # Span across two columns

        # Отдельный макет для кнопки документации
        docs_button_layout = QtWidgets.QHBoxLayout()
        docs_button_layout.setAlignment(QtCore.Qt.AlignCenter)  # Центрируем кнопку

        # Кнопка для перехода на веб-сайт документации
        website_button = QtWidgets.QPushButton("Документация на сайте")
        website_button.setStyleSheet("font-weight: bold;")  # Set the font weight to bold
        website_button.clicked.connect(lambda: webbrowser.open("https://rivskii-assistant.gitbook.io/rivskii-assistant-or-wiki/progi-dlya-vindy/rivskii-diary"))
        docs_button_layout.addWidget(website_button)

        # Добавляем макет кнопки документации в основной макет
        info_layout.addLayout(docs_button_layout, 6, 0, 1, 2)  # Span across two columns

        # Добавляем виджет вкладок в основной макет
        layout.addWidget(tab_widget)

        tab_widget.addTab(info_tab, 'Инфо')

    def save_settings(self):
        try:
            modifier = self.modifier_combo.currentText()
            key = self.hotkey_input.text()
            tray_setting = self.tray_checkbox.isChecked()  # Получаем состояние чекбокса

            # Сохраняем предыдущее значение hotkey, если новое не введено
            previous_hotkey = self.hotkey
            if modifier != "None" and key:
                hotkey = f"{modifier} + {key}"  # Формируем новую горячую клавишу
            else:
                hotkey = previous_hotkey  # Используем предыдущее значение, если новое не введено

            settings_path = os.path.join(get_data_directory(), 'settings.json')  # Обновляем путь
            with open(settings_path, 'w') as file:
                json.dump({'hotkey': hotkey, 'minimize_to_tray': tray_setting}, file)  # Сохраняем состояние чекбокса

            if hotkey:  # Регистрируем новую горячую клавишу только если она не пустая
                keyboard.remove_all_hotkeys()  # Удаляем предыдущие горячие клавиши
                keyboard.add_hotkey(hotkey, self.show_window)

            # Обновляем текст статусной метки и показываем её
            self.status_label.setText("Настройки успешно сохранены!")  # Показываем сообщение об успехе
            self.status_label.setVisible(True)  # Показываем статусную метку
        except Exception as e:
            self.status_label.setText(f"Ошибка при сохранении настроек: {str(e)}")  # Показываем сообщение об ошибке
            self.status_label.setVisible(True)  # Показываем статусную метку
            with open('error_log.txt', 'a') as log_file:  # Логируем ошибку в файл
                log_file.write(f"Ошибка: {str(e)}\n")  # Записываем ошибку

    def load_settings(self):
        settings_path = os.path.join(get_data_directory(), 'settings.json')
        try:
            if os.path.exists(settings_path):
                with open(settings_path, 'r') as file:
                    settings = json.load(file)
                    
                    self.hotkey = settings.get('hotkey', 'win+v')
                    
                    # Явно получаем значение minimize_to_tray
                    minimize_to_tray = settings['minimize_to_tray']  # Используем прямой доступ вместо get()
                    
                    # Устанавливаем состояние чекбокса
                    self.tray_checkbox.setChecked(minimize_to_tray)
        except Exception as e:
            # Устанавливаем значения по умолчанию
            self.hotkey = 'win+v'
            self.tray_checkbox.setChecked(False)

    def create_tray_icon(self):
        self.tray_icon = QtWidgets.QSystemTrayIcon(self)
        self.tray_icon.setIcon(QtGui.QIcon(resource_path('img/icon.png')))

        # Создаем контекстное меню для значка в трее
        tray_menu = QtWidgets.QMenu()
        restore_action = tray_menu.addAction("Развернуть")
        restore_action.triggered.connect(self.show_window)  # Убедитесь, что это правильно подключено
        exit_action = tray_menu.addAction("Выход")
        exit_action.triggered.connect(self.exit_application)

        tray_menu.addSeparator()
        self.tray_icon.setContextMenu(tray_menu)

        self.tray_icon.activated.connect(self.tray_icon_activated)
        self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.Trigger:
            QtCore.QTimer.singleShot(100, self.show_window)  # Задержка в 100 мс перед восстановлением окна

    def show_window(self):
        # Проверяем, является ли активное окно tvnviewer.exe
        hwnd = win32gui.GetForegroundWindow()
        window_title = win32gui.GetWindowText(hwnd)
        if 'vnc authentication' in window_title.lower():
            # Нажимаем backspace несколько раз с задержкой
            for _ in range(3):
                keyboard.press_and_release('backspace')
                time.sleep(0.1)
        
        QtCore.QTimer.singleShot(0, self._show_window)  # Отложенный вызов метода _show_window

        if hwnd:
            win32gui.SetForegroundWindow(hwnd)  # Возвращаем фокус предыдущему окну

    def _show_window(self):
        self.show()  # Показываем главное окно
        self.raise_()  # Поднимаем окно на передний план
        self.update()  # Обновляем интерфейс
        self.repaint()  # Перерисовываем интерфейс

    def monitor_clipboard(self):
        # Проверяем содержимое буфера обмена
        clipboard_content = pyperclip.paste()
        if clipboard_content and (not self.clipboard_history or clipboard_content != self.clipboard_history[-1]):
            self.clipboard_history.append(clipboard_content)
            self.add_history_item(clipboard_content)  # Используем новый метод для добавления истории
            self.save_history()
        QtCore.QTimer.singleShot(1000, self.monitor_clipboard)

    def add_history_item(self, item_text):
        # Mask sensitive information before adding to history
        masked_text = self.mask_sensitive_information(item_text)
        item = QtWidgets.QListWidgetItem(masked_text)
        
        # Определяем индекс нового элемента
        index = self.history_list.count()
        
        # Применяем разные стили в зависимости от индекса
        if index % 2 == 0:
            item.setBackground(QtGui.QColor(240, 240, 240))  # Светло-серый фон для четных строк
            item.setForeground(QtGui.QColor(0, 0, 0))  # Черный текст
        else:
            item.setBackground(QtGui.QColor(220, 220, 220))  # Темнее серый фон для нечетных строк
            item.setForeground(QtGui.QColor(50, 50, 50))  # Темно-серый текст
        
        self.history_list.addItem(item)

    def load_history(self):
        try:
            history_path = os.path.join(get_data_directory(), 'clipboard_history.json')  # Обновляем путь
            if os.path.exists(history_path):
                with open(history_path, 'r') as file:
                    self.clipboard_history = json.load(file)
                    for item in self.clipboard_history:
                        self.add_history_item(item)  # Используем новый метод для добавления истории
        except json.JSONDecodeError:
            self.status_label.setText("Ошибка при загрузке истории: файл поврежден.")  # Сообщение об ошибке
        except Exception as e:
            self.status_label.setText(f"Ошибка при загрузке истории: {str(e)}")  # Сообщение об ошибке

    def save_history(self):
        history_path = os.path.join(get_data_directory(), 'clipboard_history.json')  # Обновляем путь
        with open(history_path, 'w') as file:
            json.dump(self.clipboard_history, file)

    def load_templates(self):
        try:
            templates_path = os.path.join(get_data_directory(), 'templates.json')  # Обновляем путь
            if os.path.exists(templates_path):
                with open(templates_path, 'r', encoding='utf-8') as file:
                    templates_data = json.load(file)
                    self.template_tree.clear()  # Очищаем текущее дерево перед загрузкой
                    for item_data in templates_data:
                        self.deserialize_item(item_data, self.template_tree)
                        # Применяем стиль к загруженным элементам
                        self.apply_style_to_item(self.template_tree.topLevelItem(self.template_tree.topLevelItemCount() - 1))
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при загрузке шаблонов: {str(e)}")

    def deserialize_item(self, data, parent):
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(0, data['name'])
        hide_content = data.get('hide', False)
        item.setText(1, 'Скрытый контент' if hide_content else data['content'])
        item.setData(0, QtCore.Qt.UserRole, {'content': data['content'], 'hide': hide_content})

        # Устанавливаем иконку в зависимости от типа элемента
        if data.get('is_folder', False):  # Проверяем, является ли элемент папкой
            item.setIcon(0, QtGui.QIcon(resource_path('img/folder_icon.png')))  # Папка
            item.setData(0, QtCore.Qt.UserRole, 'folder')  # Устанавливаем тип элемента как папка
        else:
            item.setIcon(0, QtGui.QIcon(resource_path('img/template_icon.png')))  # Шаблон

        # Применяем стиль к элементу
        self.apply_style_to_item(item)

        # Устанавливаем стиль для второго столбца
        item.setForeground(1, QtGui.QBrush(QtGui.QColor("blue")))  # Цвет текста для второго столбца
        item.setFont(1, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт для второго столбца
        item.setBackground(1, QtGui.QBrush(QtGui.QColor("#e0f7fa")))  # Цвет фона для второго столбца

        for child_data in data.get('children', []):
            self.deserialize_item(child_data, item)  # Рекурсивно добавляем дочерние элементы

    def save_templates(self):
        def serialize_item(item):
            # Ensure the data is a dictionary
            item_data = item.data(0, QtCore.Qt.UserRole)
            if not isinstance(item_data, dict):
                item_data = {'content': '', 'hide': False}  # Default to an empty dictionary if not set

            data = {
                'name': item.text(0),
                'content': item_data.get('content', ''),
                'hide': item_data.get('hide', False),
                'children': [serialize_item(item.child(i)) for i in range(item.childCount())],
                'is_folder': item_data.get('is_folder', False)  # Ensure we get the correct value for is_folder
            }
            return data

        templates_data = [serialize_item(self.template_tree.topLevelItem(i)) for i in range(self.template_tree.topLevelItemCount())]
        templates_path = os.path.join(get_data_directory(), 'templates.json')  # Обновляем путь
        with open(templates_path, 'w', encoding='utf-8') as file:
            json.dump(templates_data, file, ensure_ascii=False, indent=4)

    def add_folder(self):
        try:
            current_item = self.template_tree.currentItem()
            if current_item is None or current_item not in self.template_tree.selectedItems():
                current_item = self.template_tree.invisibleRootItem()  # Устанавливаем корень, если ничего не выбрано

            folder_name, ok = QtWidgets.QInputDialog.getText(self, "Добавить папку", "Введите название папки:")
            if ok and folder_name:
                folder_item = QtWidgets.QTreeWidgetItem(current_item)
                folder_item.setText(0, folder_name)
                folder_item.setIcon(0, QtGui.QIcon(resource_path('img/folder_icon.png')))
                
                # Устанавливаем данные для папки, включая is_folder
                folder_item.setData(0, QtCore.Qt.UserRole, {'content': '', 'hide': False, 'is_folder': True})  # Устанавливаем тип элемента как папка
                folder_item.setForeground(0, QtGui.QBrush(QtGui.QColor("green")))  # Цвет текста
                folder_item.setFont(0, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт
                folder_item.setBackground(0, QtGui.QBrush(QtGui.QColor("#f0f0f0")))  # Цвет фона
                self.save_templates()  # Сохраняем изменения
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при добавлении папки: {str(e)}")

    def add_template(self):
        try:
            current_item = self.template_tree.currentItem()
            if current_item is None or current_item not in self.template_tree.selectedItems():
                current_item = self.template_tree.invisibleRootItem()  # Устанавливаем корень, если ничего не выбрано

            dialog = AddTemplateDialog(self)
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                name, content, hide_content = dialog.get_template_data()
                if name and content:
                    template_item = QtWidgets.QTreeWidgetItem(current_item)
                    template_item.setText(0, name)  # Название
                    template_item.setText(1, 'Скрытый контент' if hide_content else content)  # Содержание
                    template_item.setData(0, QtCore.Qt.UserRole, {'content': content, 'hide': hide_content})  # Store content and hide flag
                    
                    # Устанавливаем иконку для шаблона
                    template_item.setIcon(0, QtGui.QIcon(resource_path('img/template_icon.png')))

                    # Устанавливаем стиль для шаблона
                    template_item.setForeground(0, QtGui.QBrush(QtGui.QColor("blue")))  # Цвет текста для первого столбца
                    template_item.setForeground(1, QtGui.QBrush(QtGui.QColor("blue")))  # Цвет текста для второго столбца
                    template_item.setFont(0, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт для первого столбца
                    template_item.setFont(1, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт для второго столбца
                    template_item.setBackground(0, QtGui.QBrush(QtGui.QColor("#e0f7fa")))  # Цвет фона для первого столбца
                    template_item.setBackground(1, QtGui.QBrush(QtGui.QBrush(QtGui.QColor("#e0f7fa"))))  # Цвет фона для второго столбца

                    self.save_templates()  # Сохраняем изменения
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при добавлении шаблона: {str(e)}")

    def edit_template(self):
        current_item = self.template_tree.currentItem()
        if current_item:
            name = current_item.text(0)
            data = current_item.data(0, QtCore.Qt.UserRole)
            content = data['content']
            hide_content = data.get('hide', False)

            dialog = AddTemplateDialog(self)
            dialog.name_input.setText(name)
            dialog.content_input.setPlainText(content)
            dialog.hide_content_checkbox.setChecked(hide_content)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_name, new_content, new_hide_content = dialog.get_template_data()
                if not new_name or not new_content:
                    QtWidgets.QMessageBox.warning(self, "Ошибка", "Пожалуйста, заполните все поля.")
                    return

                current_item.setText(0, new_name)
                current_item.setText(1, 'Скрытый контент' if new_hide_content else new_content)
                current_item.setData(0, QtCore.Qt.UserRole, {'content': new_content, 'hide': new_hide_content})

                # Обновляем словарь шаблонов
                if new_name != name:  # Если новое название отличается от старого
                    if name in self.templates:
                        del self.templates[name]  # Удаляем старое название только если оно отличается
                    self.templates[new_name] = new_content  # Добавляем новое название
                else:
                    self.templates[name] = new_content  # Обновляем содержимое, если название не изменилось

                self.save_templates()  # Сохраняем изменения в файле

    def delete_template(self):
        current_item = self.template_tree.currentItem()
        if current_item:
            parent = current_item.parent()
            if parent:
                parent.removeChild(current_item)  # Удаляем элемент из родителя
            else:
                index = self.template_tree.indexOfTopLevelItem(current_item)
                self.template_tree.takeTopLevelItem(index)  # Удаляем верхний уровень

            # Обновляем словарь шаблонов, если это шаблон
            template_name = current_item.text(0)
            if template_name in self.templates:
                del self.templates[template_name]

            self.save_templates()  # Сохраняем изменения

    def load_window_position(self):
        # Загружаем позицию окна из JSON файла в AppData\Local
        window_position_path = os.path.join(get_data_directory(), 'window_position.json')  # Обновляем путь
        if os.path.exists(window_position_path):
            with open(window_position_path, 'r') as file:
                position = json.load(file)
                self.move(position['x'], position['y'])

    def save_window_position(self):
        # Сохраняем позицию окна в JSON файл в AppData\Local
        position = {'x': self.x(), 'y': self.y()}
        window_position_path = os.path.join(get_data_directory(), 'window_position.json')  # Обновляем путь
        with open(window_position_path, 'w') as file:
            json.dump(position, file)

    def closeEvent(self, event):
        if self.tray_checkbox.isChecked():
            event.ignore()  # Игнорируем событие закрытия
            self.hide()  # Скрываем окно вместо закрытия
        else:
            self.save_window_position()  # Сохраняем позицию окна при закрытии приложения
            self.save_triggers()  # Сохраняем триггеры при закрытии
            if self.template_window is not None:
                self.template_window.close()  # Закрываем окно шаблона, если оно открыто
                self.template_window = None  # Сбрасываем ссылку на окно
            event.accept()  # Принимаем событие, чтобы закрыть окно

    def show_template_content(self, item):
        if item and item.data(0, QtCore.Qt.UserRole):
            content = item.data(0, QtCore.Qt.UserRole)
            title = item.text(0)

            # Если окно уже открыто, закрываем его
            if self.template_window is not None:
                self.template_window.close()
                self.template_window = None

            # Теперь открываем новое окно
            self.display_template_window(title, content)

    def display_template_window(self, title, content):
        # Создаем новое окно для отображения содержимого шаблона
        if self.template_window is None:  # Проверяем, существует ли уже окно
            self.template_window = TemplateWindow(title, content)  # Используем новый класс для окна
            self.template_window.setGeometry(self.x() + self.width(), self.y(), 300, 200)  # Позиционируем окно справа от основного
            self.template_window.show()  # Показываем новое окно
        else:
            self.template_window.setWindowTitle(title)  # Обновляем заголовок окна
            self.template_window.set_content(content)  # Обновляем содержимое окна
            self.template_window.raise_()  # Если окно уже существует, поднимаем его на передний план
            self.template_window.activateWindow()  # Активируем окно

    def mousePressEvent(self, event):
        # Закрываем окно шаблона при нажатии на любое место в основном окне
        if self.template_window is not None:
            self.template_window.close()  # Закрываем окно шаблона
            self.template_window = None  # Сбрасываем ссылку на окно

    def clear_history(self):
        self.clipboard_history.clear()  # Очищаем историю буфера обмена
        self.history_list.clear()  # Очищаем отображаемый список истории
        self.save_history()  # Сохраняем очищенную историю в файл

    def add_trigger(self):
        dialog = AddTriggerDialog(self)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            name, content = dialog.get_trigger_data()
            if name and content:
                trigger_item = QtWidgets.QListWidgetItem(f"{self.trigger_list.count() + 1}. {name} - {content}")  # Include content
                trigger_item.setData(QtCore.Qt.UserRole, content)  # Store content in UserRole
                
                # Set style for the trigger
                trigger_item.setForeground(QtGui.QBrush(QtGui.QColor("blue")))
                trigger_item.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
                
                # Set background color based on the number of triggers
                if self.trigger_list.count() % 2 == 0:
                    trigger_item.setBackground(QtGui.QBrush(QtGui.QColor("#e0f7fa")))
                else:
                    trigger_item.setBackground(QtGui.QBrush(QtGui.QColor("#65d0ff")))
                
                self.trigger_list.addItem(trigger_item)  # Add the item to the trigger list
                self.triggers[name] = content  # Save the trigger in the dictionary

    def edit_trigger(self):
        current_item = self.trigger_list.currentItem()
        if current_item:
            name = current_item.text().split('. ')[1].split(' - ')[0]  # Extract the name without content
            content = self.triggers.get(name)

            dialog = AddTriggerDialog(self)
            dialog.name_input.setText(name)
            dialog.content_input.setPlainText(content)

            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                new_name, new_content = dialog.get_trigger_data()
                if new_name and new_content:
                    # Update the trigger in the dictionary
                    if new_name != name:
                        del self.triggers[name]
                        self.triggers[new_name] = new_content
                    else:
                        self.triggers[name] = new_content

                    # Update the list item text to include the content
                    current_item.setText(f"{self.trigger_list.row(current_item) + 1}. {new_name} - {new_content}")
                    current_item.setData(QtCore.Qt.UserRole, new_content)

                    # Update the numbering and content of all items
                    for index in range(self.trigger_list.count()):
                        item = self.trigger_list.item(index)
                        item_name = item.text().split('. ')[1].split(' - ')[0]  # Extract the name without content
                        item_content = item.data(QtCore.Qt.UserRole)  # Get the content from UserRole
                        item.setText(f"{index + 1}. {item_name} - {item_content}")

                    # Apply styles
                    current_item.setForeground(QtGui.QBrush(QtGui.QColor("blue")))
                    current_item.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
                    current_item.setBackground(QtGui.QBrush(QtGui.QColor("#e0f7fa")))

    def delete_trigger(self):
        current_item = self.trigger_list.currentItem()
        if current_item:
            # Extract the name without content
            name = current_item.text().split('. ')[1].split(' - ')[0]
            if name in self.triggers:
                del self.triggers[name]  # Remove from the dictionary
            self.trigger_list.takeItem(self.trigger_list.row(current_item))

    def replace_text_with_trigger(self, text):
        for trigger, replacement in self.triggers.items():
            text = text.replace(trigger, replacement)
        return text

    def monitor_triggers(self):
        ru_key_sequence = []  # Список для хранения последовательности нажатых клавиш на русской раскладке
        en_key_sequence = []  # Список для хранения последовательности нажатых клавиш на английской раскладке
        reset_timer = None  # Таймер для сброса последовательности клавиш

        def reset_key_sequence():
            nonlocal ru_key_sequence, en_key_sequence
            ru_key_sequence.clear()
            en_key_sequence.clear()

        def on_key_event(event):
            nonlocal reset_timer

            if event.event_type == keyboard.KEY_DOWN:
                if event.name == 'space':
                    # Объединяем последовательности клавиш в текущие слова
                    ru_current_word = ''.join(ru_key_sequence).lower()
                    en_current_word = ''.join(en_key_sequence).lower()

                    for trigger in self.triggers:
                        # Преобразуем триггер в обе раскладки
                        ru_converted_trigger = self.convert_to_layout(trigger, '0x419')
                        en_converted_trigger = self.convert_to_layout(trigger, '0x409')

                        if ru_current_word == ru_converted_trigger.lower() or en_current_word == en_converted_trigger.lower():
                            # Заменяем текущее слово содержимым триггера
                            replacement = self.triggers[trigger]
                            # Симулируем нажатие backspace для удаления текущего слова
                            for _ in range(max(len(ru_current_word), len(en_current_word)) + 1):  # +1 для пробела
                                keyboard.press_and_release('backspace')
                            # Печатаем содержимое замены
                            keyboard.write(replacement)
                            break
                    reset_key_sequence()
                elif event.name not in ['shift', 'ctrl', 'alt']:
                    # Добавляем клавишу в последовательности, если это не модификатор
                    ru_key_sequence.append(self.convert_to_layout(event.name, '0x419'))
                    en_key_sequence.append(self.convert_to_layout(event.name, '0x409'))
                    # Сбрасываем таймер
                    if reset_timer is not None:
                        reset_timer.cancel()
                    reset_timer = threading.Timer(0.7, reset_key_sequence)
                    reset_timer.start()

        # Отцепляем предыдущий хук, если он существует
        if self.keyboard_hook is not None:
            keyboard.unhook(self.keyboard_hook)

        # Регистрируем новый хук клавиатуры
        self.keyboard_hook = keyboard.hook(on_key_event)

        # Запускаем таймер для проверки изменения раскладки
        self.check_layout_change()

    def check_layout_change(self):
        new_layout = get_current_layout()
        if new_layout != self.current_layout:
            self.current_layout = new_layout
            self.monitor_triggers()  # Перезапускаем мониторинг триггеров при изменении раскладки

        # Проверяем раскладку каждые 500 мс
        QtCore.QTimer.singleShot(500, self.check_layout_change)

    def convert_to_layout(self, text, layout):
        if text is None:
            return ''  # Return an empty string if text is None

        # Маппинг символов между русской и английской раскладками
        ru_to_en = {
            'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y', 'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p',
            'х': '[', 'ъ': ']', 'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h', 'о': 'j', 'л': 'k',
            'д': 'l', 'ж': ';', 'э': "'", 'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n', 'ь': 'm',
            'б': ',', 'ю': '.', 'ё': '`'
        }
        en_to_ru = {v: k for k, v in ru_to_en.items()}  # Обратный маппинг

        # Выбираем маппинг в зависимости от текущей раскладки
        if layout == '0x409':  # Английская раскладка
            mapping = en_to_ru
        elif layout == '0x419':  # Русская раскладка
            mapping = ru_to_en
        else:
            return text  # Если раскладка не поддерживается, возвращаем текст без изменений

        # Преобразуем текст в соответствии с выбранным маппингом
        converted_text = ''.join(mapping.get(char, char) for char in text)
        return converted_text

    def load_triggers(self):
        triggers_path = os.path.join(get_data_directory(), 'triggers.json')  # Update path
        if os.path.exists(triggers_path):
            with open(triggers_path, 'r') as file:
                self.triggers = json.load(file)
                self.trigger_list.clear()  # Clear the list before loading
                for index, (name, content) in enumerate(self.triggers.items()):
                    trigger_item = QtWidgets.QListWidgetItem(f"{index + 1}. {name} - {content}")  # Include content
                    trigger_item.setData(QtCore.Qt.UserRole, content)  # Store content in UserRole
                    
                    # Set style for the trigger
                    trigger_item.setForeground(QtGui.QBrush(QtGui.QColor("blue")))
                    trigger_item.setFont(QtGui.QFont("Arial", weight=QtGui.QFont.Bold))
                    
                    # Alternate background colors
                    if index % 2 == 0:
                        trigger_item.setBackground(QtGui.QBrush(QtGui.QColor("#e0f7fa")))
                    else:
                        trigger_item.setBackground(QtGui.QBrush(QtGui.QColor("#65d0ff")))
                    
                    self.trigger_list.addItem(trigger_item)  # Add the item to the trigger list

    def save_triggers(self):
        triggers_path = os.path.join(get_data_directory(), 'triggers.json')  # Обновляем путь
        triggers_data = {}
        
        # Iterate through the trigger list to maintain order
        for index in range(self.trigger_list.count()):
            item = self.trigger_list.item(index)
            name = item.text().split('. ')[1].split(' - ')[0]  # Extract the trigger name
            content = item.data(QtCore.Qt.UserRole)  # Get the content from UserRole
            triggers_data[name] = content  # Store in the dictionary
            
        with open(triggers_path, 'w') as file:
            json.dump(triggers_data, file)

    def move_template_up(self):
        current_item = self.template_tree.currentItem()
        if current_item:
            index = self.template_tree.indexOfTopLevelItem(current_item)
            if index > 0:
                self.template_tree.takeTopLevelItem(index)
                self.template_tree.insertTopLevelItem(index - 1, current_item)
                self.template_tree.setCurrentItem(current_item)
                self.templates = self.update_templates_order()
                self.save_templates()

    def move_template_down(self):
        current_item = self.template_tree.currentItem()
        if current_item:
            index = self.template_tree.indexOfTopLevelItem(current_item)
            if index < self.template_tree.topLevelItemCount() - 1:
                self.template_tree.takeTopLevelItem(index)
                self.template_tree.insertTopLevelItem(index + 1, current_item)
                self.template_tree.setCurrentItem(current_item)
                self.templates = self.update_templates_order()
                self.save_templates()

    def update_templates_order(self):
        # Create a new dictionary to maintain the order
        new_templates = {}
        for index in range(self.template_tree.topLevelItemCount()):
            item = self.template_tree.topLevelItem(index)
            if item.text(0) in self.templates:
                new_templates[item.text(0)] = self.templates[item.text(0)]  # Preserve the content
        return new_templates

    def insert_template(self, item):
        if item and item.data(0, QtCore.Qt.UserRole):
            # Retrieve the actual content from the item's user data
            content_data = item.data(0, QtCore.Qt.UserRole)
            content = content_data['content']  # Get the actual content

            pyperclip.copy(content)  # Copy the content to the clipboard

            # Hide the main window to the tray
            self.hide()  # Hide the main window

            # Insert the text into the active window
            keyboard.write(content)  # Type the content from the clipboard

    def add_template_to_tree(self, name, content, parent=None):
        # Mask sensitive information before adding to templates
        masked_content = self.mask_sensitive_information(content)
        if parent is None:
            parent = self.template_tree
        template_item = QtWidgets.QTreeWidgetItem(parent)
        template_item.setText(0, name)
        template_item.setData(0, QtCore.Qt.UserRole, masked_content)
        template_item.setIcon(0, QtGui.QIcon(resource_path('img/template_icon.png')))

        # Устанавливаем стиль для первого столбца
        template_item.setForeground(0, QtGui.QBrush(QtGui.QColor("blue")))  # Цвет текста
        template_item.setFont(0, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт
        template_item.setBackground(0, QtGui.QBrush(QtGui.QColor("#e0f7fa")))  # Цвет фона

        # Устанавливаем стиль для второго столбца
        template_item.setText(1, content)  # Устанавливаем содержимое во второй столбец
        template_item.setForeground(1, QtGui.QBrush(QtGui.QColor("blue")))  # Цвет текста для второго столбца
        template_item.setFont(1, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт для второго столбца
        template_item.setBackground(1, QtGui.QBrush(QtGui.QColor("#e0f7fa")))  # Цвет фона для второго столбца

    def apply_style_to_item(self, item):
        # Проверяем, является ли элемент папкой по значению is_folder
        if item.data(0, QtCore.Qt.UserRole) == 'folder':
            # Устанавливаем стиль для папки
            item.setForeground(0, QtGui.QBrush(QtGui.QColor("green")))  # Зеленый цвет текста
        else:
            # Устанавливаем стиль для шаблона
            item.setForeground(0, QtGui.QBrush(QtGui.QColor("blue")))  # Синий цвет текста

        item.setFont(0, QtGui.QFont("Arial", weight=QtGui.QFont.Bold))  # Жирный шрифт
        item.setBackground(0, QtGui.QBrush(QtGui.QColor("#e0f7fa")))  # Цвет фона

    def exit_application(self):
        self.save_window_position()  # Сохраняем позицию окна перед выходом
        self.save_triggers()  # Сохраняем триггеры перед выходом
        QtWidgets.qApp.quit()  # Завершаем приложение

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Delete:
            # Check if the trigger list has focus
            if self.trigger_list.hasFocus():
                self.delete_trigger()  # Call the delete_trigger method
            else:
                self.delete_template()  # Call the delete_template method if the template list has focus
        elif event.key() == QtCore.Qt.Key_Left:
            # Get the current tab index
            current_index = self.findChild(QtWidgets.QTabWidget).currentIndex()
            # Switch to the previous tab
            new_index = (current_index - 1) % self.findChild(QtWidgets.QTabWidget).count()
            self.findChild(QtWidgets.QTabWidget).setCurrentIndex(new_index)
        elif event.key() == QtCore.Qt.Key_Right:
            # Get the current tab index
            current_index = self.findChild(QtWidgets.QTabWidget).currentIndex()
            # Switch to the next tab
            new_index = (current_index + 1) % self.findChild(QtWidgets.QTabWidget).count()
            self.findChild(QtWidgets.QTabWidget).setCurrentIndex(new_index)
        else:
            super().keyPressEvent(event)  # Ensure other key events are handled

    def show_with_animation(self):
        self.setWindowOpacity(0)  # Устанавливаем начальную прозрачность
        self.show()  # Показываем окно

        # Создаем анимацию для изменения прозрачности
        self.animation = QtCore.QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(1000)  # Длительность анимации в миллисекундах
        self.animation.setStartValue(0)  # Начальная прозрачность
        self.animation.setEndValue(1)  # Конечная прозрачность
        self.animation.start()  # Запускаем анимацию

    def clear_triggers(self):
        self.triggers.clear()  # Очищаем словарь триггеров
        self.trigger_list.clear()  # Очищаем отображаемый список триггеров
        self.save_triggers()  # Сохраняем очищенные триггеры в файл

    def paintEvent(self, event):
        # Создаем градиент
        gradient = QtGui.QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QtGui.QColor(189, 0, 255))  # Фиолетовый
        gradient.setColorAt(1, QtGui.QColor(255, 105, 180))  # Розовый

        # Устанавливаем градиент как фон
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), gradient)
        painter.end()

    def filter_templates(self):
        search_text = self.search_input.text().lower()  # Get the search text and convert to lowercase
        for index in range(self.template_tree.topLevelItemCount()):
            item = self.template_tree.topLevelItem(index)
            self.filter_item(item, search_text)  # Call the recursive filter method

    def filter_item(self, item, search_text):
        # Check if the item matches the search text
        matches = (search_text in item.text(0).lower()) or (search_text in item.text(1).lower())
        item.setHidden(not matches)  # Hide or show the item based on the match

        # Recursively check child items
        for i in range(item.childCount()):
            child_item = item.child(i)
            self.filter_item(child_item, search_text)  # Recursively filter child items

    def filter_triggers(self):
        search_text = self.trigger_search_input.text().lower()  # Get the search text and convert to lowercase
        for index in range(self.trigger_list.count()):
            item = self.trigger_list.item(index)
            matches = (search_text in item.text().lower()) or (search_text in item.data(QtCore.Qt.UserRole).lower())
            item.setHidden(not matches)  # Hide or show the item based on the match

    def mask_sensitive_information(self, text):
        # Example pattern to identify sensitive information
        # This is a simple example and should be replaced with a more robust pattern
        sensitive_patterns = ["password", "login", "user", "pass"]
        for pattern in sensitive_patterns:
            if pattern in text.lower():
                return '*' * len(text)  # Replace the entire text with asterisks
        return text

    def open_data_directory(self):
        # Открываем папку с JSON файлами
        data_directory = get_data_directory()
        os.startfile(data_directory)

    def reset_settings(self):
        settings_path = os.path.join(get_data_directory(), 'settings.json')
        default_settings = {
            "hotkey": "win+v",
            "minimize_to_tray": True
        }
        with open(settings_path, 'w') as file:
            json.dump(default_settings, file, indent=4)

    def check_updates_manually(self):
        has_update, version = check_for_updates()
        if has_update:
            reply = QtWidgets.QMessageBox.question(
                self, 
                'Доступно обновление',
                f'Доступна новая версия {version}. Хотите обновить программу?',
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            if reply == QtWidgets.QMessageBox.Yes:
                self.perform_update()
        else:
            QtWidgets.QMessageBox.information(
                self,
                'Обновления',
                'У вас установлена последняя версия программы.'
            )

class AddTemplateDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить шаблон')
        
        # Макет
        layout = QtWidgets.QVBoxLayout(self)

        # Ввод названия
        self.name_input = QtWidgets.QLineEdit(self)
        self.name_input.setPlaceholderText('Введите название шаблона')
        layout.addWidget(self.name_input)

        # Ввод содержимого
        self.content_input = QtWidgets.QTextEdit(self)
        self.content_input.setPlaceholderText('Введите содержимое шаблона')
        layout.addWidget(self.content_input)

        # Checkbox for hiding content
        self.hide_content_checkbox = QtWidgets.QCheckBox("Скрывать содержимое")
        layout.addWidget(self.hide_content_checkbox)

        # Кнопки
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_template_data(self):
        return self.name_input.text(), self.content_input.toPlainText(), self.hide_content_checkbox.isChecked()

class AddTriggerDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Добавить триггер')

        # Макет
        layout = QtWidgets.QVBoxLayout(self)

        # Ввод названия
        self.name_input = QtWidgets.QLineEdit(self)
        self.name_input.setPlaceholderText('Введите название триггера')
        layout.addWidget(self.name_input)

        # Ввод содержимого
        self.content_input = QtWidgets.QTextEdit(self)
        self.content_input.setPlaceholderText('Введите содержимое триггера')
        layout.addWidget(self.content_input)

        # Кнопки
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_trigger_data(self):
        return self.name_input.text(), self.content_input.toPlainText()

def get_data_directory():
    # Получаем путь к папке AppData\Local
    appdata_path = os.path.join(os.getenv('LOCALAPPDATA'), 'RivskiiDiary')
    if not os.path.exists(appdata_path):
        os.makedirs(appdata_path)  # Создаем папку, если она не существует
    return appdata_path

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)

    # Создаем и показываем экран загрузки
    splash = SplashScreen()
    splash.show()

    # Устанавливаем таймер на 5 секунд перед запуском основного окна
    def start_main_window():
        splash.close()
        main_window = RivskiiDiary()
        main_window.show_with_animation()

    QtCore.QTimer.singleShot(3000, start_main_window)

    sys.exit(app.exec_())