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
<html>
<head>
<meta charset="utf-8">
<style>
body{font-family:sans-serif}
#log{background:#111;color:#0f0;padding:10px;height:200px;overflow:auto}
#code{background:#222;color:#fff;padding:10px}
</style>
</head>
<body>

<h2>Code Battle</h2>

<button onclick="login()">Login</button>
<button onclick="queue()">Match</button>
<button onclick="play()">Play</button>

<h3>Deck</h3>
<textarea id="deck" rows="8" cols="50"></textarea>
<br><button onclick="save()">Save</button>

<h3>Status</h3>
<div id="status">Not logged in</div>

<h3>Turn</h3>
YOU: <span id="mytime"></span> |
OPP: <span id="opptime"></span>

<h3>Code</h3>
<pre id="code"></pre>

<input id="guess">
<button onclick="guess()">Guess</button>

<h3>Log</h3>
<div id="log"></div>

<script>
let id=null,state={};

function log(s){
  let l=document.getElementById("log");
  l.innerHTML+=s+"<br>";
  l.scrollTop=l.scrollHeight;
}

async function login(){
 let r=await fetch("/login",{method:"POST"});
 id=(await r.json()).id;
 log("login "+id);
}

async function save(){
 let deck=document.getElementById("deck").value.split("\\n");
 await fetch("/deck",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id,deck})
 });
 log("deck saved");
}

async function queue(){
 await fetch("/queue",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id})
 });
 log("queue...");
}

async function play(){
 let r=await fetch("/play",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id})
 });
 let j=await r.json();
 if(j.code){highlight(j.code);log("your turn");}
 if(j.error)log(j.error);
}

async function guess(){
 let g=document.getElementById("guess").value;
 let r=await fetch("/guess",{method:"POST",
  headers:{"Content-Type":"application/json"},
  body:JSON.stringify({id,guess:g})
 });
 let j=await r.json();
 log(JSON.stringify(j));
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
 state=await r.json();

 if(state.wait)document.getElementById("status").innerText="waiting";

 if(state.turn){
  document.getElementById("status").innerText=
    state.turn==id?"YOUR TURN":"OPPONENT";

  document.getElementById("mytime").innerText=
    state.time[id];

  let opp=state.p1==id?state.p2:state.p1;
  document.getElementById("opptime").innerText=
    state.time[opp];
 }

 if(state.code && state.last!=id){
   highlight(state.code);
   log("opponent played");
 }

 if(state.winner){
   log("WINNER:"+state.winner);
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
    except:
        return "error"

# =====================
# matchmaking
# =====================
def matchmaking():
    while True:
        if len(queue)>=2:
            p1=queue.pop(0)
            p2=queue.pop(0)

            mid=str(uuid.uuid4())
            matches[mid]={
                "p1":p1,"p2":p2,
                "time":{p1:60,p2:60},
                "turn":random.choice([p1,p2]),
                "code":None,
                "answer":None,
                "last":None,
                "winner":None
            }
            players[p1]["match"]=mid
            players[p2]["match"]=mid
        time.sleep(1)

threading.Thread(target=matchmaking,daemon=True).start()

# =====================
# timer
# =====================
def timer():
    while True:
        for m in matches.values():
            if m["winner"]:continue
            t=m["turn"]
            m["time"][t]-=1
            if m["time"][t]<=0:
                m["winner"]=m["p1"] if t==m["p2"] else m["p2"]
        time.sleep(1)

threading.Thread(target=timer,daemon=True).start()

# =====================
# HTTP
# =====================
class H(http.server.BaseHTTPRequestHandler):

    def reply(self,x):
        self.send_response(200)
        self.send_header("Content-Type","application/json")
        self.end_headers()
        self.wfile.write(json.dumps(x).encode())

    def do_GET(self):
        if self.path=="/":
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.end_headers()
            self.wfile.write(HTML.encode());return

        if self.path.startswith("/state"):
            pid=self.path.split("=")[1]
            if pid not in players:return self.reply({})
            mid=players[pid]["match"]
            if not mid:return self.reply({"wait":1})
            return self.reply(matches[mid])

    def do_POST(self):
        l=int(self.headers.get("Content-Length",0))
        d=json.loads(self.rfile.read(l) or "{}")

        if self.path=="/login":
            pid=str(uuid.uuid4())
            players[pid]={"deck":[],"match":None}
            return self.reply({"id":pid})

        if self.path=="/deck":
            players[d["id"]]["deck"]=d["deck"][:10]
            return self.reply({"ok":1})

        if self.path=="/queue":
            if d["id"] not in queue:
                queue.append(d["id"])
            return self.reply({"ok":1})

        if self.path=="/play":
            pid=d["id"]
            mid=players[pid]["match"]
            if not mid:return self.reply({"error":"no match"})
            m=matches[mid]

            if m["winner"]:
                return self.reply({"error":"finished"})

            if m["turn"]!=pid:
                return self.reply({"error":"not turn"})

            if not players[pid]["deck"]:
                return self.reply({"error":"deck empty"})

            code=random.choice(players[pid]["deck"])
            m["code"]=code
            m["answer"]=run_code(code)
            m["last"]=pid

            m["turn"]=m["p2"] if pid==m["p1"] else m["p1"]
            return self.reply({"code":code})

        if self.path=="/guess":
            pid=d["id"]
            mid=players[pid]["match"]
            m=matches[mid]

            if d["guess"]==m["answer"]:
                m["winner"]=pid
                return self.reply({"correct":1})
            else:
                m["time"][pid]-=5
                return self.reply({"correct":0})

print("http://localhost:8080")
http.server.HTTPServer(("0.0.0.0",8080),H).serve_forever()
