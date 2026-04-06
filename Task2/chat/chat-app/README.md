# Real-Time Multi-Room Chat Application

This is a simple beginner-friendly mini project made with:

- Python
- asyncio
- websockets
- SQLite
- HTML
- CSS
- JavaScript

It supports:

- username login
- multi-room chat
- direct messages using `/dm username message`
- typing indicator
- user presence
- message history
- message search

## Project Structure

```text
chat-app/
├── server.py
├── database.py
├── requirements.txt
├── README.md
├── static/
│   ├── index.html
│   ├── style.css
│   └── client.js
└── data/
    └── chat.db
```

## How It Works

1. The Python WebSocket server runs on `ws://0.0.0.0:8765`
2. The browser client connects to the server
3. Users join with a username
4. Users can chat in rooms: `general`, `python`, `random`
5. Messages are stored in SQLite
6. When a room is joined, old room messages are loaded
7. Search finds old messages from the database

## How to Run

### 1. Install Python packages

```bash
pip install -r requirements.txt
```

### 2. Start the WebSocket server

```bash
python server.py
```

### 3. Start a simple web server for the static files

Open a new terminal inside the `chat-app` folder and run:

```bash
python -m http.server 8000
```

### 4. Open the browser

Open:

```text
http://localhost:8000/static/
```

## How to Test

1. Open the chat page in two or more browser tabs
2. Login using different usernames
3. Send room messages
4. Change rooms and check room history
5. Send direct message:

```text
/dm alice hello
```

6. Type in the input box and see typing indicator in another tab
7. Stay inactive for about 60 seconds and the user becomes `away`
8. Close a tab and the user becomes `offline`
9. Use the search box to search old messages

## Notes

- Duplicate active usernames are blocked
- The database file is created automatically in `data/chat.db`
- This project keeps the code simple so it is easy to study and explain
