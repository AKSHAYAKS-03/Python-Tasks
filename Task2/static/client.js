let socket = null;
let currentUser = "";
let currentRoom = "general";
let typingTimer = null;
let typingUsers = new Set();

// HTML elements
const usernameInput = document.getElementById("username");
const connectBtn = document.getElementById("connectBtn");
const statusText = document.getElementById("statusText");
const roomSelect = document.getElementById("roomSelect");
const messagesDiv = document.getElementById("messages");
const typingArea = document.getElementById("typingArea");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const userList = document.getElementById("userList");
const searchKeyword = document.getElementById("searchKeyword");
const searchUser = document.getElementById("searchUser");
const searchRoom = document.getElementById("searchRoom");
const searchBtn = document.getElementById("searchBtn");
const searchResults = document.getElementById("searchResults");



function connectToServer() {
    const username = usernameInput.value.trim();

    if (username === "") {
        alert("Please enter a username.");
        return;
    }

    socket = new WebSocket("ws://localhost:8765");

    socket.onopen = function () {
        sendData({
            action: "register",
            username: username
        });
    };
    //sending register request to server

    socket.onmessage = function (event) {
        const data = JSON.parse(event.data);
        handleServerMessage(data);
    };

    //receiving server message 

    socket.onclose = function () {
        statusText.textContent = "Disconnected";
        disableChat();
    };

}



function sendData(data) {
    if (socket) {
        socket.send(JSON.stringify(data));
    }
}



function handleServerMessage(data) {
    if (data.action === "registered") {
        currentUser = data.username;
        currentRoom = data.room;
        roomSelect.value = currentRoom;
        statusText.textContent = "Connected as " + currentUser;
        enableChat();
    }

    else if (data.action === "history") {
        messagesDiv.innerHTML = "";
        data.messages.forEach(function (msg) {
            addMessage(msg);
        });
    }

    else if (data.action === "message") {
        if (data.message_type === "room" || data.message_type === "system") {
            if (data.room === currentRoom) {
                addMessage(data);
            }
        } else if (data.message_type === "dm") {
            addMessage(data);
        }
    }

    else if (data.action === "user_list") {
        showUsers(data.users);
    }

    else if (data.action === "typing") {
        updateTyping(data);
    }

    else if (data.action === "room_changed") {
        currentRoom = data.room;
        messagesDiv.innerHTML = "";
        typingUsers.clear();
        showTypingText();
    }

    else if (data.action === "search_results") {
        showSearchResults(data.results);
    }

    else if (data.action === "error") {
        alert(data.message);
    }
}



function enableChat() {
    roomSelect.disabled = false;
    messageInput.disabled = false;
    sendBtn.disabled = false;
    searchBtn.disabled = false;
    connectBtn.disabled = true;
    usernameInput.disabled = true;
}

function disableChat() {
    roomSelect.disabled = true;
    messageInput.disabled = true;
    sendBtn.disabled = true;
    searchBtn.disabled = true;
    connectBtn.disabled = false;
    usernameInput.disabled = false;
    currentUser = "";
}



function sendMessage() {
    const text = messageInput.value.trim();

    if (text === "" || !socket) {
        return;
    }

    sendData({
        action: "message",
        message: text
    });

    sendData({
        action: "typing",
        is_typing: false
    });

    messageInput.value = "";
}



function addMessage(data) {
    const div = document.createElement("div");
    div.className = "message";

    if (data.message_type === "system") {
        div.classList.add("system");
    }

    if (data.message_type === "dm") {
        div.classList.add("dm");
    }

    let title = "";

    if (data.message_type === "dm") {
        title = "[Direct Message] " + data.sender + " -> " + data.receiver;
    } else {
        title = data.sender;
    }

    div.innerHTML =
        '<div class="message-header">' + escapeHtml(title) + '</div>' +
        '<div>' + escapeHtml(data.message) + '</div>' +
        '<small>' + escapeHtml(data.timestamp || "") + '</small>';

    messagesDiv.appendChild(div);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}



function showUsers(users) {
    userList.innerHTML = "";

    users.forEach(function (user) {
        const li = document.createElement("li");

        let text = user.username + " (" + user.status + ")";
        if (user.room) {
            text += " - " + user.room;
        }

        li.textContent = text;
        userList.appendChild(li);
    });
}



function changeRoom() {
    if (!socket) {
        return;
    }

    sendData({
        action: "join_room",
        room: roomSelect.value
    });
}



function sendTyping(isTyping) {
    if (!socket) {
        return;
    }

    sendData({
        action: "typing",
        is_typing: isTyping
    });
}

function updateTyping(data) {
    if (data.room !== currentRoom) {
        return;
    }

    if (data.is_typing) {
        typingUsers.add(data.username);
    } else {
        typingUsers.delete(data.username);
    }

    showTypingText();
}

function showTypingText() {
    if (typingUsers.size === 0) {
        typingArea.textContent = "";
        return;
    }

    typingArea.textContent =
        Array.from(typingUsers).join(", ") + " is typing...";
}



function searchMessages() {
    if (!socket) {
        return;
    }

    sendData({
        action: "search",
        keyword: searchKeyword.value.trim(),
        room: searchRoom.value,
        username: searchUser.value.trim()
    });
}

function showSearchResults(results) {
    searchResults.innerHTML = "";

    if (results.length === 0) {
        searchResults.textContent = "No messages found.";
        return;
    }

    results.forEach(function (item) {
        const div = document.createElement("div");
        div.className = "search-item";

        let topLine = item.sender + " | " + item.timestamp;

        if (item.type === "room") {
            topLine += " | Room: " + item.room;
        } else {
            topLine += " | DM to: " + item.receiver;
        }

        div.innerHTML =
            '<strong>' + escapeHtml(topLine) + '</strong>' +
            '<div>' + escapeHtml(item.message) + '</div>';

        searchResults.appendChild(div);
    });
}



function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}



connectBtn.addEventListener("click", connectToServer);
sendBtn.addEventListener("click", sendMessage);
roomSelect.addEventListener("change", changeRoom);
searchBtn.addEventListener("click", searchMessages);

messageInput.addEventListener("keypress", function (event) {
    if (event.key === "Enter") {
        sendMessage();
    }
});

messageInput.addEventListener("input", function () {
    clearTimeout(typingTimer);

    sendTyping(true);

    typingTimer = setTimeout(function () {
        sendTyping(false);
    }, 800);
});

// 800ms waits after user stops typing 