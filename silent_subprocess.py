import subprocess
import os
import sys

# Сохраняем оригинальные функции
original_popen = subprocess.Popen
original_system = os.system
original_spawn = os.spawnv

# Переопределяем Popen для скрытия консоли
def silent_popen(*args, **kwargs):
    if 'startupinfo' not in kwargs and os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0  # SW_HIDE
        kwargs['startupinfo'] = startupinfo
    
    if 'creationflags' not in kwargs and os.name == 'nt':
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    
    return original_popen(*args, **kwargs)

# Переопределяем system для скрытия консоли
def silent_system(cmd):
    if os.name == 'nt':
        return silent_popen(cmd, shell=True).wait()
    else:
        return original_system(cmd)

# Переопределяем spawnv для скрытия консоли
def silent_spawn(mode, file, args):
    if os.name == 'nt':
        return silent_popen([file] + list(args[1:])).wait()
    else:
        return original_spawn(mode, file, args)

# Заменяем стандартные функции на тихие версии
subprocess.Popen = silent_popen
os.system = silent_system
os.spawnv = silent_spawn

# Добавляем информацию для PyInstaller
# Это гарантирует, что модуль будет включен в сборку 