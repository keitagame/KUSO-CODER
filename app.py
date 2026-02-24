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

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or "{}")

        # Login
        if self.path == "/login":
            pid = str(uuid.uuid4())
            players[pid] = {
                "deck": [],
                "match": None
            }
            return self.reply({"id": pid})

        # Deck
        if self.path == "/deck":
            pid = data["id"]
            deck = data["deck"][:10]
            players[pid]["deck"] = deck
            return self.reply({"ok": True})

        # Queue
        if self.path == "/queue":
            queue.append(data["id"])
            return self.reply({"ok": True})

        # Play card
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

            m["turn"] = (
                m["p2"] if pid == m["p1"] else m["p1"]
            )

            return self.reply({"code": code})

        # Guess
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

    def do_GET(self):
        if self.path.startswith("/state"):
            pid = self.path.split("=")[1]
            mid = players.get(pid, {}).get("match")

            if not mid:
                return self.reply({"state": "waiting"})

            return self.reply(matches[mid])

    def reply(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())


print("Server: http://localhost:8080")
http.server.HTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
