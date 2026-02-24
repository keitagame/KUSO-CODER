#!/usr/bin/env python3
import http.server
import json
import uuid
import threading
import time
import random

players = {}
queue = []
matches = {}

# =====================
# HTML（埋め込み）
# =====================
HTML = """
<!DOCTYPE html>
<html>
<body>

<h2>クソコーダー</h2>

<button onclick="login()">Login</button>
<button onclick="queue()">Match</button>
<button onclick="play()">Play</button>

<h3>Deck（1行1カード）</h3>
<textarea id="deck" rows="10" cols="50"></textarea>
<br>
<button onclick="save()">Save Deck</button>

<h3>Game</h3>
Turn: <span id="turn"></span><br>
Time: <span id="time"></span><br>

<pre id="code"></pre>

<input id="guess">
<button onclick="guess()">Guess</button>

<script>
let id = null;
let state = {};

async function login(){
  let r = await fetch("/login",{method:"POST"});
  id = (await r.json()).id;
}

async function save(){
  let deck = document.getElementById("deck")
    .value.split("\\n");
  await fetch("/deck",{
    method:"POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id,deck})
  });
}

async function queue(){
  await fetch("/queue",{
    method:"POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id})
  });
}

async function play(){
  let r = await fetch("/play",{
    method:"POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id})
  });
  let j = await r.json();
  if(j.code) highlight(j.code);
}

async function guess(){
  let g = document.getElementById("guess").value;
  await fetch("/guess",{
    method:"POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({id,guess:g})
  });
}

function highlight(code){
  let c = code
    .replace(/(\\d+)/g,"<b>$1</b>")
    .replace(/(\\+|\\-|\\*|\\/)/g,"<u>$1</u>")
    .replace(/([a-zA-Z]+)/g,"<i>$1</i>");
  document.getElementById("code").innerHTML = c;
}

async function update(){
  if(!id) return;

  let r = await fetch("/state?id="+id);
  state = await r.json();

  if(state.turn){
    document.getElementById("turn").innerText =
      state.turn == id ? "YOU" : "OPPONENT";

    document.getElementById("time").innerText =
      state.time[id];
  }

  if(state.code && state.last != id){
    highlight(state.code);
  }
}

setInterval(update, 1000);
</script>

</body>
</html>
"""

# =====================
# 安全コード実行
# =====================
def run_code(code):
    try:
        return str(eval(code, {"__builtins__": {}}))
    except:
        return "error"

# =====================
# マッチング
# =====================
def matchmaking():
    while True:
        if len(queue) >= 2:
            p1 = queue.pop(0)
            p2 = queue.pop(0)

            mid = str(uuid.uuid4())
            matches[mid] = {
                "p1": p1,
                "p2": p2,
                "time": {p1: 60, p2: 60},
                "turn": random.choice([p1, p2]),
                "code": None,
                "answer": None,
                "last": None
            }

            players[p1]["match"] = mid
            players[p2]["match"] = mid

        time.sleep(1)

threading.Thread(target=matchmaking, daemon=True).start()

# =====================
# タイマー
# =====================
def timer_loop():
    while True:
        for mid, m in list(matches.items()):
            if "turn" in m:
                m["time"][m["turn"]] -= 1

                if m["time"][m["turn"]] <= 0:
                    m["winner"] = (
                        m["p1"] if m["turn"] == m["p2"] else m["p2"]
                    )
        time.sleep(1)

threading.Thread(target=timer_loop, daemon=True).start()

# =====================
# HTTP
# =====================
class Handler(http.server.BaseHTTPRequestHandler):

    def reply(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML.encode())
            return

        if self.path.startswith("/state"):
            pid = self.path.split("=")[1]
            mid = players.get(pid, {}).get("match")

            if not mid:
                return self.reply({"state": "waiting"})

            return self.reply(matches[mid])

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or "{}")

        if self.path == "/login":
            pid = str(uuid.uuid4())
            players[pid] = {"deck": [], "match": None}
            return self.reply({"id": pid})

        if self.path == "/deck":
            pid = data.get("id")
            deck = data.get("deck")
            if not pid or pid not in players:
                return self.reply({"error": "invalid id"})
            if not isinstance(deck, list):
                return self.reply({"error": "invalid deck"})
            players[pid]["deck"] = deck[:10]
            return self.reply({"ok": True})

        if self.path == "/queue":
            queue.append(data["id"])
            return self.reply({"ok": True})

        if self.path == "/play":
            pid = data["id"]
            mid = players[pid]["match"]
            m = matches[mid]

            if m["turn"] != pid:
                return self.reply({"error": "not turn"})

            if not players[pid]["deck"]:
                return self.reply({"error": "empty deck"})

            code = random.choice(players[pid]["deck"])
            m["code"] = code
            m["answer"] = run_code(code)
            m["last"] = pid
            m["turn"] = m["p2"] if pid == m["p1"] else m["p1"]

            return self.reply({"code": code})

        if self.path == "/guess":
            pid = data["id"]
            guess = str(data["guess"])
            mid = players[pid]["match"]
            m = matches[mid]

            if guess == m["answer"]:
                return self.reply({"correct": True})
            else:
                m["time"][pid] -= 5
                return self.reply({"correct": False})


print("Server: http://localhost:8080")
http.server.HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
