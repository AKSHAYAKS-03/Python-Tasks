import asyncio
import json
import websockets



# websockets - one live connection between one client and the server

from database import (
    init_db,
    save_user,
    update_user_status,
    save_message,
    get_room_history,
    search_messages,
)

HOST = "0.0.0.0"
PORT = 8765
ROOMS = ["general", "python", "random"]
AWAY_SECONDS = 60

# Active users
connected_users = {}   # username -> websocket
user_rooms = {}        # username -> room
user_status = {}       # username -> online/away/offline
last_activity = {}     # username -> last active time


# ------------------ Helper Functions ------------------

async def send_json(websocket, data):
    await websocket.send(json.dumps(data))


async def broadcast_user_list():
    users = []

    for username in sorted(user_status.keys()):
        users.append({
            "username": username,
            "status": user_status.get(username, "offline"),
            "room": user_rooms.get(username, "")
        })

    data = {"action": "user_list", "users": users}

    for websocket in connected_users.values():
        await send_json(websocket, data)

# “Online users list” ellarukum update aagum.
async def send_room_history(username, room):
    websocket = connected_users.get(username)
    if not websocket:
        return

    history = get_room_history(room)
    await send_json(websocket, {
        "action": "history",
        "room": room,
        "messages": history
    })


async def broadcast_room_message(room, data):
    for username, websocket in connected_users.items():
        if user_rooms.get(username) == room:
            await send_json(websocket, data)


async def broadcast_system_message(room, text):
    data = {
        "action": "message",
        "message_type": "system",
        "room": room,
        "sender": "System",
        "message": text,
        "timestamp": ""
    }
    await broadcast_room_message(room, data)


async def set_status(username, status):
    user_status[username] = status
    update_user_status(username, status)
    await broadcast_user_list()


# ------------------ Presence Watcher ------------------

async def activity_watcher(username, websocket):
    while True:
        await asyncio.sleep(5)

        if username not in connected_users:
            break

        if connected_users.get(username) != websocket:
            break

        idle_time = asyncio.get_event_loop().time() - last_activity.get(username, 0)

        if idle_time > AWAY_SECONDS and user_status.get(username) == "online":
            await set_status(username, "away")


# ------------------ User Registration ------------------

async def register_user(websocket, username):
    username = username.strip()

    if not username:
        await send_json(websocket, {
            "action": "error",
            "message": "Username cannot be empty."
        })
        return None

    if username in connected_users:
        await send_json(websocket, {
            "action": "error",
            "message": "Username already active."
        })
        return None

    connected_users[username] = websocket
    user_rooms[username] = "general"
    user_status[username] = "online"
    last_activity[username] = asyncio.get_event_loop().time()

    save_user(username, "online")

    await send_json(websocket, {
        "action": "registered",
        "username": username,
        "room": "general",
        "rooms": ROOMS
    })

    await send_room_history(username, "general")
    await broadcast_user_list()
    await broadcast_system_message("general", f"{username} joined the room.")
    print(f'[INFO] User "{username}" connected')

    return username


# ------------------ Room Join ------------------

async def join_room(username, room):
    websocket = connected_users.get(username)

    if room not in ROOMS:
        if websocket:
            await send_json(websocket, {
                "action": "error",
                "message": "Room not found."
            })
        return

    old_room = user_rooms.get(username)
    user_rooms[username] = room

    if websocket:
        await send_json(websocket, {
            "action": "room_changed",
            "room": room
        })
        await send_room_history(username, room)

    await broadcast_user_list()

    if old_room and old_room != room:
        await broadcast_system_message(old_room, f"{username} left the room.")
        await broadcast_system_message(room, f"{username} joined the room.")
        print(f'[INFO] {username} joined room #{room}')


# ------------------ Room Message ------------------

async def handle_room_message(username, text):
    room = user_rooms.get(username, "general")
    timestamp = save_message(username, "", room, text, "room")

    data = {
        "action": "message",
        "message_type": "room",
        "room": room,
        "sender": username,
        "message": text,
        "timestamp": timestamp
    }

    await broadcast_room_message(room, data)


# ------------------ Direct Message ------------------

async def handle_dm(username, target_user, text):
    sender_socket = connected_users.get(username)
    target_socket = connected_users.get(target_user)

    if not target_socket:
        if sender_socket:
            await send_json(sender_socket, {
                "action": "error",
                "message": "User is not online."
            })
        return

    timestamp = save_message(username, target_user, "", text, "dm")

    data = {
        "action": "message",
        "message_type": "dm",
        "sender": username,
        "receiver": target_user,
        "message": text,
        "timestamp": timestamp
    }

    await send_json(sender_socket, data)
    if target_user != username:
        await send_json(target_socket, data)


# ------------------ Typing ------------------

async def handle_typing(username, is_typing):
    room = user_rooms.get(username)

    data = {
        "action": "typing",
        "username": username,
        "room": room,
        "is_typing": is_typing
    }

    for other_user, websocket in connected_users.items():
        if other_user != username and user_rooms.get(other_user) == room:
            await send_json(websocket, data)


# ------------------ Search ------------------

async def handle_search(username, keyword, room):
    websocket = connected_users.get(username)
    if not websocket:
        return

    results = search_messages(keyword, room)

    await send_json(websocket, {
        "action": "search_results",
        "results": results
    })


# ------------------ Main Client Handler ------------------

async def handle_client(websocket):
    username = None
    watcher_task = None

    try:
        async for message_text in websocket:
            data = json.loads(message_text)
            action = data.get("action")

            # Register first
            if action == "register":
                if username:
                    continue

                username = await register_user(websocket, data.get("username", ""))
                if username:
                    watcher_task = asyncio.create_task(activity_watcher(username, websocket))
                continue

            # If not registered
            if not username:
                await send_json(websocket, {
                    "action": "error",
                    "message": "Please register first."
                })
                continue

            # Update activity
            last_activity[username] = asyncio.get_event_loop().time()
            if user_status.get(username) != "online":
                await set_status(username, "online")

            # Join room
            if action == "join_room":
                await join_room(username, data.get("room", "general"))

            # Send message
            elif action == "message":
                text = data.get("message", "").strip()
                if not text:
                    continue

                if text.startswith("/dm "):
                    parts = text.split(" ", 2)
                    if len(parts) < 3:
                        await send_json(websocket, {
                            "action": "error",
                            "message": "Use: /dm username message"
                        })
                    else:
                        await handle_dm(username, parts[1], parts[2])
                else:
                    await handle_room_message(username, text)

            # Typing
            elif action == "typing":
                await handle_typing(username, data.get("is_typing", False))

            # Search
            elif action == "search":
                await handle_search(
                    username,
                    data.get("keyword", ""),
                    data.get("room", "")
                )

    except websockets.exceptions.ConnectionClosed:
        pass

    finally:
        if watcher_task:
            watcher_task.cancel()

        if username:
            room = user_rooms.get(username, "general")

            connected_users.pop(username, None)
            user_rooms.pop(username, None)
            last_activity.pop(username, None)
            user_status[username] = "offline"
            update_user_status(username, "offline")

            await broadcast_user_list()
            await broadcast_system_message(room, f"{username} went offline.")
            print(f'[INFO] User "{username}" disconnected')


# ------------------ Start Server ------------------

async def main():
    init_db()
    print(f"[INFO] Chat server started on ws://{HOST}:{PORT}")

    async with websockets.serve(handle_client, HOST, PORT):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())