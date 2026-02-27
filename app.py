#!/usr/bin/env python3
"""クソコードバトル - 標準ライブラリのみ"""

import json, random, time, uuid, hashlib, struct, base64, threading
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse
import socketserver

KUSO_CODES = [
    {"id": "k001", "title": "謎の計算", "code": "_ = lambda __, ___, ____, _____: __ + ___ * ____ - _____\nprint(_( 1 , 2 , 3 , 1 ))", "answer": "6", "hint": "ラムダ式で計算している", "difficulty": 1, "tags": ["lambda", "math"]},
    {"id": "k002", "title": "文字の呪い", "code": "x=''.join(chr(ord(c)-32) if 96<ord(c)<123 else chr(ord(c)+32) if 64<ord(c)<91 else c for c in 'hELLO wORLD')\nprint(x)", "answer": "Hello World", "hint": "大文字小文字を操作している", "difficulty": 2, "tags": ["string", "ord"]},
    {"id": "k003", "title": "フィボ地獄", "code": "f=lambda n:n if n<2 else f(n-1)+f(n-2)\nprint(f(7))", "answer": "13", "hint": "有名なアルゴリズムの再帰", "difficulty": 2, "tags": ["recursion", "fibonacci"]},
    {"id": "k004", "title": "リスト錬金術", "code": "l=[i**2 for i in range(1,6)]\nprint(sum(l[::2]))", "answer": "35", "hint": "スライスと内包表記", "difficulty": 3, "tags": ["list", "comprehension"]},
    {"id": "k005", "title": "真理の海", "code": "print(int(True)+int(True)+int(False)+int(True)*3)", "answer": "5", "hint": "Boolは整数", "difficulty": 1, "tags": ["bool", "int"]},
    {"id": "k006", "title": "文字列の呪縛", "code": 's = "abcdefg"\nprint(s[len(s)//2::] + s[:len(s)//2])', "answer": "defgabc", "hint": "スライスの結合", "difficulty": 3, "tags": ["string", "slice"]},
    {"id": "k007", "title": "辞書の迷宮", "code": "d={str(i):i*i for i in range(5)}\nprint(d.get('3',0)+d.get('4',0))", "answer": "25", "hint": "辞書内包表記とget", "difficulty": 3, "tags": ["dict", "comprehension"]},
    {"id": "k008", "title": "ビット遊び", "code": "x = 0b1010\ny = 0b1100\nprint(x & y, x | y, x ^ y)", "answer": "8 14 6", "hint": "ビット演算子 AND OR XOR", "difficulty": 4, "tags": ["bitwise", "binary"]},
    {"id": "k009", "title": "ゼータもどき", "code": "import functools\nr = functools.reduce(lambda a,b:a+b, map(lambda x:1/x**2, range(1,6)))\nprint(round(r,4))", "answer": "1.4636", "hint": "1/n^2の和を計算", "difficulty": 4, "tags": ["math", "reduce"]},
    {"id": "k010", "title": "逆順の秘密", "code": 'words = "python is fun"\nprint(\' \'.join(word[::-1] for word in words.split()))', "answer": "nohtyp si nuf", "hint": "各単語を逆にする", "difficulty": 2, "tags": ["string", "slice"]},
    {"id": "k011", "title": "モジュロ地獄", "code": "print([x for x in range(50) if x%3==0 and x%5==0][-1])", "answer": "45", "hint": "FizzBuzz的なフィルタ", "difficulty": 3, "tags": ["modulo", "list"]},
    {"id": "k012", "title": "入れ子の罠", "code": "f = lambda x: (lambda y: y*y)(x+1)\nprint(f(4))", "answer": "25", "hint": "ネストされたラムダ", "difficulty": 3, "tags": ["lambda", "closure"]},
    {"id": "k013", "title": "謎のzip", "code": "a = [1,2,3,4,5]\nb = [10,20,30,40,50]\nprint(sum(x*y for x,y in zip(a,b)))", "answer": "550", "hint": "内積の計算", "difficulty": 3, "tags": ["zip", "math"]},
    {"id": "k014", "title": "型変換マジック", "code": 'x = "3.14"\ny = "2"\nprint(int(float(x) * int(y)))', "answer": "6", "hint": "型変換の連鎖", "difficulty": 2, "tags": ["type", "conversion"]},
    {"id": "k015", "title": "セット遊び", "code": "a = {1,2,3,4,5}\nb = {3,4,5,6,7}\nprint(len(a^b), sum(a&b))", "answer": "4 12", "hint": "集合の対称差と積集合", "difficulty": 4, "tags": ["set", "math"]},
    {"id": "k016", "title": "スター展開", "code": "first, *rest = [1, 2, 3, 4, 5]\n*init, last = rest\nprint(first + last)", "answer": "5", "hint": "アンパック代入", "difficulty": 3, "tags": ["unpack", "star"]},
    {"id": "k017", "title": "条件式の洞窟", "code": "x = 10\ny = x if x > 5 else x * 2 if x > 2 else 0\nprint(y)", "answer": "10", "hint": "三項演算子のネスト", "difficulty": 2, "tags": ["ternary", "condition"]},
    {"id": "k018", "title": "文字カウント", "code": 'from collections import Counter\nc = Counter("mississippi")\nprint(c.most_common(1)[0][1])', "answer": "4", "hint": "最頻出文字の出現回数", "difficulty": 3, "tags": ["counter", "string"]},
    {"id": "k019", "title": "謎のmap", "code": "nums = [1, -2, 3, -4, 5]\nprint(list(map(abs, nums)))", "answer": "[1, 2, 3, 4, 5]", "hint": "absをmapで適用", "difficulty": 1, "tags": ["map", "abs"]},
    {"id": "k020", "title": "ウォルラス演算子", "code": "data = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]\nif (n := len(data)) > 5:\n    print(n * 2)", "answer": "20", "hint": "セイウチ演算子 :=", "difficulty": 3, "tags": ["walrus", "operator"]},
]

waiting_players = []
active_games = {}
player_connections = {}
global_lock = threading.Lock()
WS_MAGIC = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

class GameRoom:
    def __init__(self, gid, p1id, p1name, p2id, p2name):
        self.game_id = gid
        self.player1_id = p1id
        self.player2_id = p2id
        self.players = {
            p1id: {"name": p1name, "time_left": 60.0, "score": 0, "deck": [], "hand": [], "solved": [], "current_code": None, "last_tick": time.time()},
            p2id: {"name": p2name, "time_left": 60.0, "score": 0, "deck": [], "hand": [], "solved": [], "current_code": None, "last_tick": time.time()},
        }
        self.finished = False
        self.winner = None

    def opp(self, pid):
        return self.player2_id if pid == self.player1_id else self.player1_id

    def build_deck(self, pid):
        deck = random.sample(KUSO_CODES, min(10, len(KUSO_CODES)))
        self.players[pid]["deck"] = [c["id"] for c in deck]
        self.draw_hand(pid, 3)

    def draw_hand(self, pid, n=1):
        p = self.players[pid]
        for _ in range(n):
            if p["deck"] and len(p["hand"]) < 5:
                p["hand"].append(p["deck"].pop(0))

    def card(self, cid):
        return next((c for c in KUSO_CODES if c["id"] == cid), None)

    def play_card(self, pid, cid):
        p = self.players[pid]
        if cid not in p["hand"]: return False
        p["hand"].remove(cid)
        p["current_code"] = cid
        p["last_tick"] = time.time()
        return True

    def tick(self, pid):
        p = self.players[pid]
        now = time.time()
        if p["current_code"]:
            p["time_left"] = max(0, p["time_left"] - (now - p["last_tick"]))
        p["last_tick"] = now
        return p["time_left"]

    def submit(self, pid, answer):
        p = self.players[pid]
        if not p["current_code"]: return {"correct": False, "message": "コードを選んでいません"}
        c = self.card(p["current_code"])
        if answer.strip() == c["answer"].strip():
            p["score"] += 1
            p["solved"].append(p["current_code"])
            p["current_code"] = None
            self.draw_hand(pid, 1)
            return {"correct": True, "message": "正解！", "score": p["score"]}
        return {"correct": False, "message": f"不正解... 正解は: {c['answer']}", "answer": c["answer"]}

    def check_over(self):
        for pid, p in self.players.items():
            if p["time_left"] <= 0:
                self.finished = True
                self.winner = self.opp(pid)
                return True
        return False

    def state(self, pid):
        oid = self.opp(pid)
        me = self.players[pid]
        opp = self.players[oid]
        return {
            "game_id": self.game_id,
            "me": {"time_left": round(me["time_left"],1), "score": me["score"],
                   "hand": [self.card(c) for c in me["hand"]], "hand_count": len(me["hand"]),
                   "deck_count": len(me["deck"]), "current_code": self.card(me["current_code"]) if me["current_code"] else None,
                   "solved_count": len(me["solved"])},
            "opponent": {"time_left": round(opp["time_left"],1), "score": opp["score"],
                         "hand_count": len(opp["hand"]), "deck_count": len(opp["deck"]),
                         "solving": opp["current_code"] is not None, "solved_count": len(opp["solved"])},
            "finished": self.finished, "winner": self.winner,
        }

def find_room(pid):
    return next((r for r in active_games.values() if pid in r.players), None)

class WS:
    def __init__(self, sock, pid):
        self.sock = sock; self.player_id = pid; self.closed = False
        self._lock = threading.Lock()

    def send(self, obj):
        if self.closed: return
        data = json.dumps(obj, ensure_ascii=False).encode()
        length = len(data)
        hdr = bytearray([0x81])
        if length < 126: hdr.append(length)
        elif length < 65536: hdr += bytearray([126]) + struct.pack('>H', length)
        else: hdr += bytearray([127]) + struct.pack('>Q', length)
        with self._lock:
            try: self.sock.sendall(bytes(hdr) + data)
            except: self.closed = True

    def recv(self):
        try:
            def rb(n):
                b = b''
                while len(b) < n:
                    c = self.sock.recv(n-len(b))
                    if not c: raise ConnectionError()
                    b += c
                return b
            h = rb(2)
            op = h[0] & 0xF
            masked = bool(h[1] & 0x80)
            length = h[1] & 0x7F
            if length == 126: length = struct.unpack('>H', rb(2))[0]
            elif length == 127: length = struct.unpack('>Q', rb(8))[0]
            mask = rb(4) if masked else b''
            payload = bytearray(rb(length))
            if masked:
                for i in range(len(payload)): payload[i] ^= mask[i%4]
            return op, bytes(payload)
        except: return None, None

    def close(self):
        self.closed = True
        try: self.sock.sendall(bytes([0x88, 0x00]))
        except: pass
        try: self.sock.close()
        except: pass


def handle_msg(ws, pid, data):
    t = data.get("type")
    if t == "ping": ws.send({"type": "pong"})
    elif t == "find_match": do_find_match(ws, pid, data.get("username","PLAYER"))
    elif t == "play_card": do_play_card(ws, pid, data.get("card_id"))
    elif t == "submit_answer": do_submit(ws, pid, data.get("answer",""))
    elif t == "tick": do_tick(pid)
    elif t == "cancel_match": do_cancel(pid)

def do_find_match(ws, pid, username):
    to_start = None
    with global_lock:
        if find_room(pid): return
        if any(p["id"]==pid for p in waiting_players): return
        waiting_players.append({"id": pid, "username": username})
        ws.send({"type": "waiting"})
        if len(waiting_players) >= 2:
            p1 = waiting_players.pop(0)
            p2 = waiting_players.pop(0)
            to_start = (p1, p2)
    if to_start: do_start(*to_start)

def do_start(p1, p2):
    gid = str(uuid.uuid4())[:8]
    room = GameRoom(gid, p1["id"], p1["username"], p2["id"], p2["username"])
    room.build_deck(p1["id"]); room.build_deck(p2["id"])
    with global_lock: active_games[gid] = room
    for pid, pinfo in [(p1["id"],p1),(p2["id"],p2)]:
        ws = player_connections.get(pid)
        opp = p2 if pid==p1["id"] else p1
        if ws and not ws.closed:
            ws.send({"type":"game_start","game_id":gid,"opponent_name":opp["username"],"state":room.state(pid)})

def do_play_card(ws, pid, cid):
    room = find_room(pid)
    if not room: ws.send({"type":"error","message":"ゲームが見つかりません"}); return
    if not room.play_card(pid, cid): ws.send({"type":"error","message":"そのカードを出せません"}); return
    broadcast_state(room)

def do_submit(ws, pid, answer):
    room = find_room(pid)
    if not room: return
    result = room.submit(pid, answer)
    ws.send({"type":"answer_result",**result})
    if room.check_over(): broadcast_over(room); return
    broadcast_state(room)

def do_tick(pid):
    room = find_room(pid)
    if not room or room.finished: return
    room.tick(pid)
    if room.check_over(): broadcast_over(room); return
    ws = player_connections.get(pid)
    if ws and not ws.closed:
        me = room.players[pid]; opp = room.players[room.opp(pid)]
        ws.send({"type":"timer_update","my_time":round(me["time_left"],1),"opponent_time":round(opp["time_left"],1)})

def do_cancel(pid):
    with global_lock:
        for i,p in enumerate(waiting_players):
            if p["id"]==pid: waiting_players.pop(i); break

def broadcast_state(room):
    for pid in [room.player1_id, room.player2_id]:
        ws = player_connections.get(pid)
        if ws and not ws.closed: ws.send({"type":"state_update","state":room.state(pid)})

def broadcast_over(room):
    room.finished = True
    for pid in [room.player1_id, room.player2_id]:
        ws = player_connections.get(pid)
        if ws and not ws.closed:
            ws.send({"type":"game_over","winner":room.winner,"is_winner":room.winner==pid,"state":room.state(pid)})

def cleanup(pid):
    with global_lock:
        for i,p in enumerate(waiting_players):
            if p["id"]==pid: waiting_players.pop(i); break
    room = find_room(pid)
    if room and not room.finished:
        room.finished = True; room.winner = room.opp(pid)
        ws = player_connections.get(room.winner)
        if ws and not ws.closed:
            ws.send({"type":"game_over","winner":room.winner,"is_winner":True,"reason":"opponent_disconnected","state":room.state(room.winner)})

HTML = open("index.html","r",encoding="utf-8").read()

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        p = urlparse(self.path).path
        if p == '/':
            body = HTML.encode(); self.send_response(200)
            self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Content-Length',len(body)); self.end_headers(); self.wfile.write(body)
        elif p == '/ws': self._ws()
        elif p == '/stats':
            with global_lock:
                body = json.dumps({"waiting":len(waiting_players),"active_games":len(active_games),"total_connections":len(player_connections)}).encode()
            self.send_response(200); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',len(body)); self.end_headers(); self.wfile.write(body)
        else: self.send_response(404); self.end_headers()

    def _ws(self):
        key = self.headers.get('Sec-WebSocket-Key','')
        accept = base64.b64encode(hashlib.sha1((key+WS_MAGIC).encode()).digest()).decode()
        self.send_response(101); self.send_header('Upgrade','websocket')
        self.send_header('Connection','Upgrade'); self.send_header('Sec-WebSocket-Accept',accept); self.end_headers()
        pid = str(uuid.uuid4())
        ws = WS(self.connection, pid)
        with global_lock: player_connections[pid] = ws
        print(f"[+] {pid[:8]}")
        try:
            while not ws.closed:
                op, payload = ws.recv()
                if op is None or op == 0x8: break
                if op == 0x1:
                    try: handle_msg(ws, pid, json.loads(payload.decode()))
                    except Exception as e: ws.send({"type":"error","message":str(e)})
        finally:
            print(f"[-] {pid[:8]}")
            cleanup(pid)
            with global_lock: player_connections.pop(pid, None)

if __name__ == "__main__":
    PORT = 8080
    server = socketserver.ThreadingTCPServer(('0.0.0.0', PORT), Handler)
    server.allow_reuse_address = True
    print(f"🎮 クソコードバトル起動!")
    print(f"   → http://localhost:{PORT}")
    print(f"   → 依存なし (標準ライブラリのみ)")
    try: server.serve_forever()
    except KeyboardInterrupt: print("停止")
