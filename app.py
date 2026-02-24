#!/usr/bin/env python3
import http.server, json, uuid, threading, time, random, math

players = {}
queue = []
matches = {}

# =====================
# HTML
# =====================
HTML = """
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="utf-8">
<title>クソコードバトラーズ</title>
<style>
body{font-family:sans-serif;margin:20px;}
textarea{width:100%;max-width:600px;}
button{margin:2px;}
#code{background:#f5f5f5;padding:8px;min-height:40px;}
#log{border:1px solid #ccc;height:200px;overflow-y:auto;padding:4px;background:#fafafa;}
.status-box{padding:4px 8px;border-radius:4px;display:inline-block;margin-bottom:8px;}
.status-wait{background:#ffeeba;}
.status-play{background:#c3e6cb;}
.status-end{background:#f5c6cb;}
.score{font-weight:bold;}
</style>
</head>
<body>

<h2>クソコードバトラーズ</h2>
<p>pythonでクソコードを組んで相手を惑わそう。<br>
ターンが来たら自動でコードが出され、相手が答えるゲームです。</p>

<div>
  <button onclick="login()">入場</button>
  <button onclick="queueMatch()">マッチング</button>
</div>

<h3>デッキ（1行1コード・最大10枚）</h3>
<textarea id="deck" rows="8" cols="60"
placeholder="例: 1+1
round(3.14159,2)
max(1,2,3)
math.sin(1)
abs(-123)
"></textarea>
<br>
<button onclick="save()">セーブ</button>

<h3>Status</h3>
<div id="status" class="status-box status-wait">Not logged in</div>

<h3>Turn / Time</h3>
<div>YOU: <span id="mytime">-</span> 秒 |
OPP: <span id="opptime">-</span> 秒</div>

<h3>Score</h3>
<div>YOU: <span id="myscore" class="score">0</span> |
OPP: <span id="oppscore" class="score">0</span></div>

<h3>Code</h3>
<pre id="code"></pre>

<input id="guess" placeholder="出力を予想して入力">
<button onclick="guess()">Guess</button>

<h3>Log</h3>
<div id="log"></div>

<script>
let id=null,state={};

function log(s){
  let l=document.getElementById("log");
  let t=new Date().toLocaleTimeString();
  l.innerHTML+="["+t+"] "+s+"<br>";
  l.scrollTop=l.scrollHeight;
}

function setStatus(text, cls){
  let el=document.getElementById("status");
  el.innerText=text;
  el.className="status-box "+cls;
}

async function login(){
  let r=await fetch("/login",{method:"POST"});
  let j=await r.json();
  id=j.id;
  log("login "+id);
  setStatus("ログイン済み: "+id,"status-wait");
}

async function save(){
  if(!id){log("先に入場してください");return;}
  let deck=document.getElementById("deck").value
    .split("\\n")
    .map(x=>x.trim())
    .filter(x=>x);
  await fetch("/deck",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id,deck})
  });
  log("deck saved ("+deck.length+"枚)");
}

async function queueMatch(){
  if(!id){log("先に入場してください");return;}
  await fetch("/queue",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id})
  });
  log("queue...");
  setStatus("マッチング待ち...","status-wait");
}

async function guess(){
  if(!id){log("先に入場してください");return;}
  let g=document.getElementById("guess").value;
  if(!g){log("guessを入力してください");return;}
  let r=await fetch("/guess",{method:"POST",
    headers:{"Content-Type":"application/json"},
    body:JSON.stringify({id,guess:g})
  });
  let j=await r.json();
  if(j.error){
    log("guess error: "+j.error);
    return;
  }
  if(j.correct){
    log("正解！ あなたに1ポイント");
  }else{
    log("不正解... 残り時間が減りました");
  }
}

function highlight(code){
  let c=code
    .replace(/(\\d+)/g,"<b>$1</b>")
    .replace(/(\\+|\\-|\\*|\\/)/g,"<u>$1</u>");
  document.getElementById("code").innerHTML=c;
}

async function update(){
  if(!id)return;
  let r=await fetch("/state?id="+id);
  let j=await r.json();
  state=j;

  if(!j || Object.keys(j).length===0){
    setStatus("マッチなし / 待機中","status-wait");
    return;
  }

  if(j.wait){
    setStatus("マッチング待ち...","status-wait");
    return;
  }

  // ターン・時間
  if(j.turn){
    let myid=id;
    let opp = (j.p1===myid)?j.p2:j.p1;
    document.getElementById("mytime").innerText = j.time[myid] ?? "-";
    document.getElementById("opptime").innerText = j.time[opp] ?? "-";

    if(j.turn===myid){
      setStatus("あなたのターン（相手が答える）","status-play");
    }else{
      setStatus("相手のターン（あなたが答える）","status-play");
    }
  }

  // スコア
  if(j.score){
    let myid=id;
    let opp = (j.p1===myid)?j.p2:j.p1;
    document.getElementById("myscore").innerText = j.score[myid] ?? 0;
    document.getElementById("oppscore").innerText = j.score[opp] ?? 0;
  }

  // コード更新
  if(j.code && j.last!==id){
    highlight(j.code);
    log("相手がコードを出しました");
  }

  // 勝敗
  if(j.winner){
    if(j.winner===id){
      log("WINNER: YOU");
    }else{
      log("WINNER: OPPONENT");
    }
    setStatus("ゲーム終了","status-end");
  }
}
setInterval(update,1000);
</script>
</body>
</html>
"""

# =====================
# 安全eval
# =====================
SAFE = {
    "abs":abs,
    "round":round,
    "min":min,
    "max":max,
    "math":math
}

def run_code(code):
    try:
        return str(eval(code, {"__builtins__":None}, SAFE))
    except Exception:
        return "error"

# =====================
# 自動プレイ
# =====================
def auto_play(m):
    pid = m["turn"]
    deck = players[pid]["deck"]
    if not deck:
        m["winner"] = m["p2"] if pid == m["p1"] else m["p1"]
        return

    code = random.choice(deck)
    m["code"] = code
    m["answer"] = run_code(code)
    m["last"] = pid

# =====================
# matchmaking
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
                "last": None,
                "winner": None,
                "score": {p1: 0, p2: 0},
                "max_score": 3,
            }
            players[p1]["match"] = mid
            players[p2]["match"] = mid
        time.sleep(1)

threading.Thread(target=matchmaking, daemon=True).start()

# =====================
# timer
# =====================
def timer():
    while True:
        for m in list(matches.values()):
            if m.get("winner"):
                continue

            t = m["turn"]
            m["time"][t] -= 1
            if m["time"][t] <= 0:
                loser = t
                winner = m["p1"] if t == m["p2"] else m["p2"]
                m["winner"] = winner
                continue

            # ★ 自動プレイ：コードがまだ出ていない時だけ
            if m["code"] is None:
                auto_play(m)

        time.sleep(1)

threading.Thread(target=timer, daemon=True).start()

# =====================
# HTTP
# =====================
class H(http.server.BaseHTTPRequestHandler):

    def reply(self, x, status=200, ctype="application/json"):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if ctype == "application/json":
            self.wfile.write(json.dumps(x).encode())
        else:
            self.wfile.write(x.encode())

    def do_GET(self):
        if self.path == "/":
            self.reply(HTML, ctype="text/html")
            return

        if self.path.startswith("/state"):
            pid = self.path.split("=")[1]
            if pid not in players:
                return self.reply({})
            mid = players[pid].get("match")
            if not mid or mid not in matches:
                return self.reply({"wait": 1})
            return self.reply(matches[mid])

        self.reply({"error":"not found"}, status=404)

    def do_POST(self):
        l = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(l) if l>0 else b"{}"
        try:
            d = json.loads(raw or "{}")
        except Exception:
            d = {}

        path = self.path

        if path == "/login":
            pid = str(uuid.uuid4())
            players[pid] = {"deck": [], "match": None}
            return self.reply({"id": pid})

        if path == "/deck":
            pid = d.get("id")
            if pid not in players:
                return self.reply({"error":"invalid id"})
            deck = d.get("deck") or []
            deck = [str(x) for x in deck][:10]
            players[pid]["deck"] = deck
            return self.reply({"ok": 1})

        if path == "/queue":
            pid = d.get("id")
            if pid not in players:
                return self.reply({"error":"invalid id"})
            if pid not in queue and players[pid].get("match") is None:
                queue.append(pid)
            return self.reply({"ok": 1})

        if path == "/guess":
            pid = d.get("id")
            if pid not in players:
                return self.reply({"error":"invalid id"})
            mid = players[pid].get("match")
            if not mid or mid not in matches:
                return self.reply({"error":"no match"})
            m = matches[mid]

            if m.get("winner"):
                return self.reply({"error":"finished"})

            if not m.get("answer"):
                return self.reply({"error":"no code to guess"})

            g = str(d.get("guess","")).strip()

            if g == m["answer"]:
                m["score"][pid] += 1
                if m["score"][pid] >= m["max_score"]:
                    m["winner"] = pid

                m["turn"] = m["p2"] if pid == m["p1"] else m["p1"]
                m["code"] = None
                m["answer"] = None
                return self.reply({"correct":1})
            else:
                m["time"][pid] -= 5
                if m["time"][pid] <= 0:
                    opp = m["p1"] if pid == m["p2"] else m["p2"]
                    m["winner"] = opp
                return self.reply({"correct":0})

        self.reply({"error":"not found"}, status=404)

print("http://localhost:8080")
http.server.HTTPServer(("0.0.0.0",8080), H).serve_forever()
