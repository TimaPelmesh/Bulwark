import os
import sys
import shutil
import subprocess
import PyInstaller.__main__

def clean_build_folders():
    """
    Очистка директорий сборки от предыдущих файлов
    """
    print("Очистка директорий сборки...")
    folders_to_clean = ['build', 'dist']
    
    for folder in folders_to_clean:
        if os.path.exists(folder):
            shutil.rmtree(folder)
            print(f"Директория {folder} удалена")

def collect_data_files():
    """
    Собирает список файлов ресурсов для включения в сборку
    """
    print("Сбор файлов ресурсов...")
    data_files = []
    
    # Добавляем иконку приложения
    if os.path.exists('icon.ico'):
        data_files.append(('icon.ico', '.'))
        print("Добавлена иконка приложения: icon.ico")
    
    # Папка с изображениями (если есть)
    if os.path.exists('img'):
        for file in os.listdir('img'):
            if file.endswith('.png') or file.endswith('.jpg') or file.endswith('.ico'):
                data_files.append((os.path.join('img', file), 'img'))
                print(f"Добавлен файл изображения: {os.path.join('img', file)}")
    
    return data_files

def build_exe():
    """
    Сборка EXE-файла с помощью PyInstaller
    """
    print("Начало сборки EXE-файла...")
    
    # Очистка предыдущих сборок
    clean_build_folders()
    
    # Сбор файлов ресурсов
    data_files = collect_data_files()
    
    # Добавляем data_files в формате PyInstaller
    datas = []
    for src, dst in data_files:
        datas.append(f"--add-data={src}{os.pathsep}{dst}")
    
    # Обязательно добавляем client_subprocess.py
    if os.path.exists('client_subprocess.py'):
        print("Найден client_subprocess.py, добавляем его в сборку...")
        datas.append(f"--add-data=client_subprocess.py{os.pathsep}.")
    else:
        print("ВНИМАНИЕ: client_subprocess.py не найден!")
    
    # Добавляем silent_subprocess.py
    if os.path.exists('silent_subprocess.py'):
        print("Найден silent_subprocess.py, добавляем его в сборку...")
        datas.append(f"--add-data=silent_subprocess.py{os.pathsep}.")
    else:
        print("ВНИМАНИЕ: silent_subprocess.py не найден!")
    
    # Настраиваем параметры PyInstaller
    pyinstaller_args = [
        'main.py',                # Основной файл запуска
        '--name=Bulwark',         # Имя выходного файла
        '--onefile',              # Сборка в один файл
        '--windowed',             # Без консоли (GUI-приложение)
        '--clean',                # Очистка кеша сборки
        f"--icon={'icon.ico' if os.path.exists('icon.ico') else ''}",  # Иконка приложения
        '--noconfirm',            # Без подтверждения перезаписи
    ]
    
    # Добавляем файлы ресурсов
    pyinstaller_args.extend(datas)
    
    # Добавляем скрытые импорты (могут быть необходимы)
    hidden_imports = [
        '--hidden-import=wmi',
        '--hidden-import=psutil',
        '--hidden-import=GPUtil',
    ]
    pyinstaller_args.extend(hidden_imports)
    
    print("Запуск PyInstaller со следующими аргументами:")
    for arg in pyinstaller_args:
        print(f"  {arg}")
    
    # Запуск PyInstaller
    PyInstaller.__main__.run(pyinstaller_args)
    
    print("\nСборка завершена!")
    print(f"Исполняемый файл создан: dist/Bulwark.exe")

def check_dependencies():
    """
    Проверка наличия необходимых зависимостей
    """
    print("Проверка наличия необходимых зависимостей...")
    try:
        import PyInstaller
        print("PyInstaller установлен")
    except ImportError:
        print("PyInstaller не установлен. Установка...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Проверяем другие зависимости из requirements.txt
    if os.path.exists('requirements.txt'):
        print("Установка зависимостей из requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    else:
        print("Файл requirements.txt не найден, пропускаем установку зависимостей")

if __name__ == "__main__":
    print("=== Утилита сборки Bulwark в EXE ===")
    
    # Проверяем зависимости
    check_dependencies()
    
    # Собираем EXE
    build_exe()
    
    print("\nПроцесс упаковки завершен!")
    print("Для запуска приложения запустите dist/Bulwark.exe")
    input("Нажмите Enter для выхода...") 