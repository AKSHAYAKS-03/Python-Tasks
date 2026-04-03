import asyncio
import json
import sqlite3
import uuid
import time
from datetime import datetime
from collections import defaultdict

import websockets

HOST = "0.0.0.0"
PORT = 8765

# ---------------- DATABASE ----------------
conn = sqlite3.connect("chat.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    room TEXT,
    sender TEXT,
    receiver TEXT,
    content TEXT,
    type TEXT,
    timestamp TEXT
)
""")
conn.commit()

# ---------------- MEMORY ----------------
connected_users = {}         # username -> websocket
user_sessions = {}           # websocket -> info
rooms = defaultdict(set)     # room -> usernames
user_current_room = {}       # username -> room
typing_users = defaultdict(set)

# ---------------- UTIL ----------------
def now_str():
    return datetime.now().strftime("%H:%M:%S")

def full_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_info(msg):
    print(f'[INFO] {msg}')

def save_message(room, sender, receiver, content, msg_type):
    cursor.execute("""
        INSERT INTO messages (room, sender, receiver, content, type, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (room, sender, receiver, content, msg_type, full_timestamp()))
    conn.commit()

def fetch_room_history(room, limit=30):
    cursor.execute("""
        SELECT sender, content, timestamp
        FROM messages
        WHERE room = ? AND type = 'room_message'
        ORDER BY id DESC
        LIMIT ?
    """, (room, limit))
    rows = cursor.fetchall()
    rows.reverse()
    return rows

def fetch_dm_history(user1, user2, limit=30):
    cursor.execute("""
        SELECT sender, receiver, content, timestamp
        FROM messages
        WHERE type = 'private_message'
          AND (
            (sender = ? AND receiver = ?)
            OR
            (sender = ? AND receiver = ?)
          )
        ORDER BY id DESC
        LIMIT ?
    """, (user1, user2, user2, user1, limit))
    rows = cursor.fetchall()
    rows.reverse()
    return rows

def search_messages(keyword, room=None):
    query = """
        SELECT room, sender, receiver, content, type, timestamp
        FROM messages
        WHERE content LIKE ?
    """
    params = [f"%{keyword}%"]

    if room:
        query += " AND room = ?"
        params.append(room)

    query += " ORDER BY id DESC LIMIT 30"
    cursor.execute(query, params)
    return cursor.fetchall()

async def send_json(ws, data):
    try:
        await ws.send(json.dumps(data))
    except:
        pass

async def broadcast_to_room(room, data):
    for username in rooms[room]:
        ws = connected_users.get(username)
        if ws:
            await send_json(ws, data)

async def send_room_members(room):
    await broadcast_to_room(room, {
        "type": "room_members",
        "room": room,
        "members": list(rooms[room])
    })

async def broadcast_presence():
    users = []
    for username, ws in connected_users.items():
        if ws in user_sessions:
            users.append({
                "username": username,
                "status": user_sessions[ws]["status"]
            })

    payload = {"type": "presence_update", "users": users}

    for ws in list(user_sessions.keys()):
        await send_json(ws, payload)

async def set_user_status(username, status):
    ws = connected_users.get(username)
    if ws and ws in user_sessions:
        user_sessions[ws]["status"] = status
        user_sessions[ws]["last_seen"] = time.time()
        await broadcast_presence()

async def auto_away_checker():
    while True:
        current = time.time()
        changed = False

        for ws, info in list(user_sessions.items()):
            if info["status"] == "online" and current - info["last_seen"] > 60:
                info["status"] = "away"
                changed = True

        if changed:
            await broadcast_presence()

        await asyncio.sleep(10)

# ---------------- HANDLERS ----------------
async def handle_register(ws, data):
    username = data.get("username", "").strip()

    if not username:
        await send_json(ws, {"type": "error", "message": "Username required"})
        return False

    if username in connected_users:
        await send_json(ws, {"type": "error", "message": "Username already taken"})
        return False

    session_id = str(uuid.uuid4())[:6]

    connected_users[username] = ws
    user_sessions[ws] = {
        "username": username,
        "session_id": session_id,
        "last_seen": time.time(),
        "status": "online"
    }

    log_info(f'User "{username}" connected (session: {session_id})')

    await send_json(ws, {
        "type": "registered",
        "username": username,
        "session_id": session_id
    })

    await broadcast_presence()
    return True

async def handle_join_room(ws, data):
    username = user_sessions[ws]["username"]
    room = data.get("room", "").strip()

    if not room:
        return

    old_room = user_current_room.get(username)
    if old_room and username in rooms[old_room]:
        rooms[old_room].remove(username)
        typing_users[old_room].discard(username)
        await send_room_members(old_room)

    rooms[room].add(username)
    user_current_room[username] = room

    log_info(f'{username} joined room #{room}')

    history = fetch_room_history(room)

    await send_json(ws, {
        "type": "room_history",
        "room": room,
        "messages": [
            {"sender": s, "content": c, "timestamp": t}
            for s, c, t in history
        ]
    })

    await send_room_members(room)

async def handle_room_message(ws, data):
    username = user_sessions[ws]["username"]
    room = user_current_room.get(username)
    content = data.get("content", "").strip()

    if not room or not content:
        return

    save_message(room, username, None, content, "room_message")
    typing_users[room].discard(username)

    await broadcast_to_room(room, {
        "type": "room_message",
        "room": room,
        "sender": username,
        "content": content,
        "timestamp": now_str()
    })

    await broadcast_to_room(room, {
        "type": "typing_update",
        "room": room,
        "typing_users": list(typing_users[room])
    })

async def handle_private_message(ws, data):
    sender = user_sessions[ws]["username"]
    receiver = data.get("to", "").strip()
    content = data.get("content", "").strip()

    if not receiver or not content:
        return

    save_message(None, sender, receiver, content, "private_message")

    payload = {
        "type": "private_message",
        "sender": sender,
        "receiver": receiver,
        "content": content,
        "timestamp": now_str()
    }

    await send_json(ws, payload)

    receiver_ws = connected_users.get(receiver)
    if receiver_ws:
        await send_json(receiver_ws, payload)

async def handle_typing(ws, data):
    username = user_sessions[ws]["username"]
    room = user_current_room.get(username)
    is_typing = data.get("is_typing", False)

    if not room:
        return

    if is_typing:
        typing_users[room].add(username)
    else:
        typing_users[room].discard(username)

    await broadcast_to_room(room, {
        "type": "typing_update",
        "room": room,
        "typing_users": list(typing_users[room])
    })

async def handle_search(ws, data):
    keyword = data.get("keyword", "").strip()
    room = data.get("room")

    if not keyword:
        return

    results = search_messages(keyword, room=room)

    await send_json(ws, {
        "type": "search_results",
        "results": [
            {
                "room": r[0],
                "sender": r[1],
                "receiver": r[2],
                "content": r[3],
                "message_type": r[4],
                "timestamp": r[5]
            }
            for r in results
        ]
    })

async def handle_dm_history(ws, data):
    username = user_sessions[ws]["username"]
    other = data.get("user", "").strip()

    if not other:
        return

    history = fetch_dm_history(username, other)

    await send_json(ws, {
        "type": "dm_history",
        "user": other,
        "messages": [
            {
                "sender": s,
                "receiver": r,
                "content": c,
                "timestamp": t
            }
            for s, r, c, t in history
        ]
    })

# ---------------- MAIN WS HANDLER ----------------
async def handler(ws):
    registered = False

    try:
        async for message in ws:
            try:
                data = json.loads(message)
            except:
                await send_json(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            if ws in user_sessions:
                user_sessions[ws]["last_seen"] = time.time()
                if user_sessions[ws]["status"] != "online":
                    user_sessions[ws]["status"] = "online"
                    await broadcast_presence()

            action = data.get("type")

            if action == "register":
                registered = await handle_register(ws, data)

            elif not registered:
                await send_json(ws, {"type": "error", "message": "Register first"})

            elif action == "join_room":
                await handle_join_room(ws, data)

            elif action == "room_message":
                await handle_room_message(ws, data)

            elif action == "private_message":
                await handle_private_message(ws, data)

            elif action == "typing":
                await handle_typing(ws, data)

            elif action == "search":
                await handle_search(ws, data)

            elif action == "dm_history":
                await handle_dm_history(ws, data)

            elif action == "set_status":
                username = user_sessions[ws]["username"]
                await set_user_status(username, data.get("status", "online"))

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if ws in user_sessions:
            username = user_sessions[ws]["username"]
            room = user_current_room.get(username)

            if room and username in rooms[room]:
                rooms[room].remove(username)
                typing_users[room].discard(username)
                await send_room_members(room)

            connected_users.pop(username, None)
            user_current_room.pop(username, None)
            user_sessions.pop(ws, None)

            log_info(f'User "{username}" disconnected')
            await broadcast_presence()

# ---------------- SERVER ----------------
async def main():
    log_info(f"Chat server started on ws://{HOST}:{PORT}")
    asyncio.create_task(auto_away_checker())

    async with websockets.serve(handler, HOST, PORT):
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_info("Server stopped gracefully")