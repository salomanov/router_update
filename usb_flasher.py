#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RouterKit USB Auto-Flasher for Xiaomi Mi Router 3G (KeeneticOS MIPS)
Creates a bootable Entware USB drive with pre-configured RouterKit stack.
"""

import os
import sys
import time
import json
import gzip
import ctypes
from ctypes import wintypes
import subprocess

# Ensure UTF-8 console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Win32 Constants
GENERIC_READ = 0x80000000
GENERIC_WRITE = 0x40000000
FILE_SHARE_READ = 0x00000001
FILE_SHARE_WRITE = 0x00000002
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x00000080
INVALID_HANDLE_VALUE = wintypes.HANDLE(-1).value

FSCTL_LOCK_VOLUME = 0x00090018
FSCTL_DISMOUNT_VOLUME = 0x00090020
FSCTL_UNLOCK_VOLUME = 0x0009001C

kernel32 = ctypes.windll.kernel32
CreateFileW = kernel32.CreateFileW
CreateFileW.argtypes = [
    wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE
]
CreateFileW.restype = wintypes.HANDLE

WriteFile = kernel32.WriteFile
WriteFile.argtypes = [
    wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
WriteFile.restype = wintypes.BOOL

DeviceIoControl = kernel32.DeviceIoControl
DeviceIoControl.argtypes = [
    wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
    ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p
]
DeviceIoControl.restype = wintypes.BOOL

FlushFileBuffers = kernel32.FlushFileBuffers
FlushFileBuffers.argtypes = [wintypes.HANDLE]
FlushFileBuffers.restype = wintypes.BOOL

CloseHandle = kernel32.CloseHandle
CloseHandle.argtypes = [wintypes.HANDLE]
CloseHandle.restype = wintypes.BOOL

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def elevate():
    if not is_admin():
        try:
            params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit(0)
        except Exception as e:
            print(f"[!] Не удалось получить права администратора: {e}")
            input("Нажмите Enter для выхода...")
            sys.exit(1)

def get_base_dir():
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_usb_disks():
    ps_cmd = """
    Get-Disk | Where-Object { $_.BusType -eq 'USB' -and $_.Size -gt 0 } | ForEach-Object {
        $disk = $_
        $letters = (Get-Partition -DiskNumber $disk.Number -ErrorAction SilentlyContinue | Where-Object { $_.DriveLetter } | ForEach-Object { $_.DriveLetter + ':' }) -join ', '
        [PSCustomObject]@{
            Number = $disk.Number
            Model = $disk.FriendlyName
            SizeBytes = $disk.Size
            SizeGB = [math]::Round($disk.Size / 1GB, 1)
            Letters = $letters
        }
    } | ConvertTo-Json -Compress
    """
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_cmd],
            capture_output=True, text=True, timeout=10
        )
        out = res.stdout.strip()
        if not out:
            return []
        data = json.loads(out)
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
    except Exception:
        pass
    return []

def dismount_volumes(letters):
    if not letters:
        return
    for let in letters.split(","):
        let = let.strip().rstrip(":")
        if not let:
            continue
        vol_path = f"\\\\.\\{let}:"
        h_vol = CreateFileW(
            vol_path, GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE, None,
            OPEN_EXISTING, 0, None
        )
        if h_vol != INVALID_HANDLE_VALUE:
            bytes_ret = wintypes.DWORD(0)
            DeviceIoControl(h_vol, FSCTL_LOCK_VOLUME, None, 0, None, 0, ctypes.byref(bytes_ret), None)
            DeviceIoControl(h_vol, FSCTL_DISMOUNT_VOLUME, None, 0, None, 0, ctypes.byref(bytes_ret), None)
            CloseHandle(h_vol)

def clear_disk_partitions(disk_num):
    ps_clean = f"Clear-Disk -Number {disk_num} -RemoveData -Confirm:$false -ErrorAction SilentlyContinue"
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps_clean],
            capture_output=True, timeout=10
        )
    except Exception:
        pass

def flash_image_to_disk(image_gz_path, disk_num, letters):
    print("\n[1/3] Подготовка накопителя (размонтирование разделов)...")
    dismount_volumes(letters)
    clear_disk_partitions(disk_num)
    time.sleep(1)

    print("[2/3] Открытие физического диска для прямой поблочной записи...")
    physical_path = f"\\\\.\\PhysicalDrive{disk_num}"
    
    h_disk = CreateFileW(
        physical_path, GENERIC_READ | GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE, None,
        OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
    )

    if h_disk == INVALID_HANDLE_VALUE:
        err = kernel32.GetLastError()
        print(f"[!] Ошибка открытия {physical_path}: код {err}")
        print("    Возможно накопитель занят другой программой (Проводник, Total Commander).")
        return False

    print("[3/3] Запись загрузочного образа RouterKit (ext4, Entware, nfqws2, DNS)...")
    
    # Total decompressed size of raw master image is 269,484,032 bytes (~257 MiB)
    total_uncompressed = 269484032
    bytes_written_total = 0
    start_time = time.time()
    chunk_size = 1024 * 1024 # 1 MiB

    buf = ctypes.create_string_buffer(chunk_size)
    bytes_written = wintypes.DWORD(0)

    try:
        with gzip.open(image_gz_path, "rb") as gz:
            while True:
                data = gz.read(chunk_size)
                if not data:
                    break
                
                # Write to disk
                ctypes.memmove(buf, data, len(data))
                success = WriteFile(h_disk, buf, len(data), ctypes.byref(bytes_written), None)
                if not success:
                    err = kernel32.GetLastError()
                    print(f"\n[!] Ошибка записи сектора: Win32 Error {err}")
                    CloseHandle(h_disk)
                    return False
                
                bytes_written_total += bytes_written.value
                elapsed = time.time() - start_time + 0.001
                speed_mbs = (bytes_written_total / 1024 / 1024) / elapsed
                pct = min(100.0, (bytes_written_total * 100.0) / total_uncompressed)
                bar_len = 35
                filled = int(bar_len * pct / 100)
                bar = "=" * filled + (">" if filled < bar_len else "") + " " * (bar_len - filled - 1 if filled < bar_len else 0)
                
                mb_done = bytes_written_total / 1024 / 1024
                mb_tot = total_uncompressed / 1024 / 1024
                print(f"\r[{bar}] {pct:5.1f}% ({mb_done:5.1f}/{mb_tot:5.1f} МБ) [{speed_mbs:4.1f} МБ/с] ", end="", flush=True)

        FlushFileBuffers(h_disk)
        print("\n\n[+] Запись успешно завершена и зафиксирована на носителе!")
    finally:
        CloseHandle(h_disk)

    # Refresh disk layout in Windows
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "Update-HostStorageCache -ErrorAction SilentlyContinue"],
            capture_output=True, timeout=5
        )
    except Exception:
        pass

    return True

def print_banner():
    banner = r"""
======================================================================
       RouterKit Auto-Flasher v2.0 (Xiaomi Mi 3G / KeeneticOS)
       Автономная запись загрузочной флешки «Вставил и работает»
======================================================================
"""
    print(banner)

def main():
    elevate()
    print_banner()

    base_dir = get_base_dir()
    image_gz_path = os.path.join(base_dir, "routerkit-mipsel.img.gz")
    
    if not os.path.exists(image_gz_path):
        print(f"[!] КРИТИЧЕСКАЯ ОШИБКА: Файл образа не найден:\n    {image_gz_path}")
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

    while True:
        print("[*] Поиск подключенных USB-накопителей...")
        disks = get_usb_disks()
        
        if not disks:
            print("\n[!] USB-накопитель (флешка) не обнаружен!")
            print("    Пожалуйста, вставьте флешку в USB-разъём компьютера.")
            ans = input("    Нажмите [Enter] для повторного сканирования (или 'q' для выхода): ").strip().lower()
            if ans in ("q", "й", "exit"):
                sys.exit(0)
            print("-" * 70)
            continue
        
        break

    print(f"\nОбнаружено USB-накопителей: {len(disks)}")
    for idx, d in enumerate(disks, start=1):
        letters_str = f"Буква: {d['Letters']}" if d.get('Letters') else "Без буквы"
        print(f"  [{idx}] Диск {d['Number']}: {d['Model']} ({d['SizeGB']} ГБ) [{letters_str}]")

    selected_idx = 0
    if len(disks) == 1:
        selected_idx = 0
    else:
        while True:
            choice = input(f"\nВыберите номер накопителя [1-{len(disks)}]: ").strip()
            if choice.isdigit() and 1 <= int(choice) <= len(disks):
                selected_idx = int(choice) - 1
                break
            print("Неверный выбор, попробуйте снова.")

    target = disks[selected_idx]
    
    print("\n" + "=" * 70)
    print("ВНИМАНИЕ! ПОДТВЕРЖДЕНИЕ ЗАПИСИ:")
    print(f"Целевой накопитель: Диск {target['Number']} - {target['Model']} ({target['SizeGB']} ГБ)")
    if target.get('Letters'):
        print(f"Разделы: {target['Letters']}")
    print("ВСЕ СУЩЕСТВУЮЩИЕ ДАННЫЕ НА ЭТОЙ ФЛЕШКЕ БУДУТ ПОЛНОСТЬЮ СТЁРТЫ!")
    print("На флешку будет записана система RouterKit (ext4, Entware, nfqws2, DNS, GRouter).")
    print("=" * 70)

    confirm = input("Точно ли шьём? Введите [Y / Д] для старта, либо любую другую клавишу для отмены: ").strip()
    if confirm not in ("y", "Y", "д", "Д", "yes", "YES", "да", "ДА"):
        print("\n[-] Запись отменена пользователем. Накопитель остался нетронутым.")
        input("\nНажмите Enter для выхода...")
        sys.exit(0)

    success = flash_image_to_disk(image_gz_path, target['Number'], target.get('Letters', ''))

    if success:
        print("\n" + "=" * 70)
        print("          ГОТОВО! ФЛЕШКА ПОЛНОСТЬЮ НАСТРОЕНА И ГОТОВА К РАБОТЕ        ")
        print("=" * 70)
        print("Инструкция по запуску:")
        print("  1. Безопасно извлеките флешку из компьютера.")
        print("  2. Вставьте её в USB-разъём роутера Xiaomi Mi Router 3G.")
        print("     (Роутер может быть уже включён или выключен - не имеет значения).")
        print("  3. Подождите 15-20 секунд.")
        print("     KeeneticOS автоматически смонтирует раздел /opt, выполнит")
        print("     скрипт автонастройки S01auto-setup и поднимет все службы.")
        print("")
        print("Что уже работает сразу из коробки:")
        print("  • Защищённый DNS-over-TLS (Cloudflare 1.1.1.1 + Yandex 77.88.8.8)")
        print("  • Обход блокировок nfqws2 (YouTube, Discord и др. без замедления)")
        print("  • Веб-панель управления GRouter: http://192.168.1.1:8089/")
        print("  • Доступ по SSH (Dropbear): root@192.168.1.1 (порт 22)")
        print("=" * 70)
    else:
        print("\n[!] Произошла ошибка при записи. Проверьте права и попробуйте снова.")

    input("\nНажмите [Enter] для закрытия программы...")

if __name__ == "__main__":
    main()
