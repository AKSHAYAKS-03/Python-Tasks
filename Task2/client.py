import asyncio
import json
import websockets
import os
from datetime import datetime

SERVER_URI = "ws://localhost:8765"

username = ""
current_room = ""
online_users = []
current_mode = "room"   # room / dm
current_dm_user = ""

# ---------------- UTIL ----------------
def clear():
    os.system("cls" if os.name == "nt" else "clear")

def fmt_time(ts):
    if not ts:
        return ""
    try:
        if len(ts) <= 8:
            return ts
        dt = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%H:%M:%S")
    except:
        return ts

def print_header():
    clear()
    title = f"#{current_room}" if current_mode == "room" else f"DM with {current_dm_user}"
    print(f"{title} | {len([u for u in online_users if u['status']=='online'])} members online")
    print("─" * 50)

def print_footer():
    online = [u["username"] for u in online_users if u["status"] == "online"]
    away = [u["username"] for u in online_users if u["status"] == "away"]

    line = ""
    if online:
        line += "Online: " + ", ".join(online)
    if away:
        if line:
            line += " | "
        line += "Away: " + ", ".join(away)

    print("─" * 50)
    print(line)
    print("\nCommands:")
    print("/join roomname")
    print("/dm username message")
    print("/history username")
    print("/search keyword")
    print("/typing")
    print("/away")
    print("/online")
    print("/quit")
    print()

# ---------------- RECEIVE ----------------
async def receiver(ws):
    global online_users, current_room, current_mode, current_dm_user

    while True:
        try:
            msg = await ws.recv()
            data = json.loads(msg)

            if data["type"] == "registered":
                print(f'\nConnected as {data["username"]} (session: {data["session_id"]})')

            elif data["type"] == "room_history":
                current_mode = "room"
                current_room = data["room"]
                current_dm_user = ""

                print_header()
                for m in data["messages"]:
                    print(f"[{fmt_time(m['timestamp'])}] {m['sender']}: {m['content']}")
                print_footer()

            elif data["type"] == "room_message":
                if current_mode == "room" and data["room"] == current_room:
                    print(f"\n[{data['timestamp']}] {data['sender']}: {data['content']}")

            elif data["type"] == "private_message":
                if (
                    current_mode == "dm" and
                    (data["sender"] == current_dm_user or data["receiver"] == current_dm_user)
                ):
                    print(f"\n[DM] [{data['timestamp']}] {data['sender']} -> {data['receiver']}: {data['content']}")
                else:
                    print(f"\n[DM] [{data['timestamp']}] {data['sender']} -> {data['receiver']}: {data['content']}")

            elif data["type"] == "typing_update":
                others = [u for u in data["typing_users"] if u != username]
                if current_mode == "room" and data["room"] == current_room and others:
                    if len(others) == 1:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {others[0]} is typing...")
                    else:
                        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] {', '.join(others)} are typing...")

            elif data["type"] == "presence_update":
                online_users = data["users"]

            elif data["type"] == "room_members":
                pass

            elif data["type"] == "search_results":
                print("\n=== Search Results ===")
                if not data["results"]:
                    print("No results found.")
                else:
                    for r in data["results"]:
                        room = f"#{r['room']}" if r["room"] else "DM"
                        print(f"[{fmt_time(r['timestamp'])}] [{room}] {r['sender']}: {r['content']}")

            elif data["type"] == "dm_history":
                current_mode = "dm"
                current_dm_user = data["user"]

                print_header()
                for m in data["messages"]:
                    print(f"[DM] [{fmt_time(m['timestamp'])}] {m['sender']} -> {m['receiver']}: {m['content']}")
                print_footer()

            elif data["type"] == "error":
                print(f"\n[ERROR] {data['message']}")

        except:
            print("\nDisconnected from server.")
            break

# ---------------- SEND ----------------
async def sender(ws):
    global current_room

    while True:
        msg = await asyncio.to_thread(input, "> ")

        if msg.strip() == "":
            continue

        if msg.startswith("/join "):
            room = msg.split(" ", 1)[1].strip()
            await ws.send(json.dumps({
                "type": "join_room",
                "room": room
            }))

        elif msg.startswith("/dm "):
            parts = msg.split(" ", 2)
            if len(parts) < 3:
                print("Usage: /dm username message")
                continue

            to = parts[1]
            content = parts[2]

            await ws.send(json.dumps({
                "type": "private_message",
                "to": to,
                "content": content
            }))

        elif msg.startswith("/history "):
            user = msg.split(" ", 1)[1].strip()
            await ws.send(json.dumps({
                "type": "dm_history",
                "user": user
            }))

        elif msg.startswith("/search "):
            keyword = msg.split(" ", 1)[1].strip()
            await ws.send(json.dumps({
                "type": "search",
                "keyword": keyword,
                "room": current_room if current_room else None
            }))

        elif msg == "/typing":
            await ws.send(json.dumps({
                "type": "typing",
                "is_typing": True
            }))
            await asyncio.sleep(2)
            await ws.send(json.dumps({
                "type": "typing",
                "is_typing": False
            }))

        elif msg == "/away":
            await ws.send(json.dumps({
                "type": "set_status",
                "status": "away"
            }))

        elif msg == "/online":
            await ws.send(json.dumps({
                "type": "set_status",
                "status": "online"
            }))

        elif msg == "/quit":
            print("Exiting chat...")
            break

        else:
            # normal room message
            await ws.send(json.dumps({
                "type": "room_message",
                "content": msg
            }))

            await ws.send(json.dumps({
                "type": "typing",
                "is_typing": False
            }))

# ---------------- MAIN ----------------
async def main():
    global username

    username = input("Enter username: ").strip()

    async with websockets.connect(SERVER_URI) as ws:
        await ws.send(json.dumps({
            "type": "register",
            "username": username
        }))

        recv_task = asyncio.create_task(receiver(ws))
        send_task = asyncio.create_task(sender(ws))

        done, pending = await asyncio.wait(
            [recv_task, send_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

if __name__ == "__main__":
    asyncio.run(main())