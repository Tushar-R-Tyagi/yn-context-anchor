from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import HTMLResponse
from schemas import StoryContext
from llm_narrator import generate_story_turn
from llm_tracker import update_story_state
import database as db

app = FastAPI()

# Initialize SQLite database schema on startup
@app.on_event("startup")
def startup():
    db.init_db()

def update_and_persist_state(context: StoryContext, story_text: str, user_id: str):
    # Run Auditor to extract inventory / locations
    update_story_state(context, story_text)
    # Save updated state to SQLite and release busy status
    db.update_user_world_state(user_id, context)

@app.get("/user_state")
def get_user_state(user_id: str = "player_1"):
    context, history, is_busy = db.get_or_create_user(user_id)
    return {
        "location": context.world_state.location,
        "active_inventory": context.world_state.active_inventory,
        "is_busy": is_busy,
        "history": history
    }

@app.post("/chat")
def chat_endpoint(user_id: str, user_input: str, background_tasks: BackgroundTasks):
    current_state, chat_history, is_busy = db.get_or_create_user(user_id)
    
    if is_busy:
        raise HTTPException(status_code=429, detail="Previous action is still processing.")
    
    db.set_busy_status(user_id, True)
    story_text = generate_story_turn(current_state, chat_history, user_input)
    
    # Save chat messages directly to SQL
    db.append_chat_history(user_id, "user", user_input)
    db.append_chat_history(user_id, "assistant", story_text)
    
    # Pass background audit to update state
    background_tasks.add_task(update_and_persist_state, current_state, story_text, user_id)
    
    return {
        "reply": story_text,
        "location": current_state.world_state.location,
        "active_inventory": current_state.world_state.active_inventory
    }

@app.post("/intervene")
def intervene_endpoint(user_id: str, user_intervention: str, background_tasks: BackgroundTasks):
    current_state, chat_history, _ = db.get_or_create_user(user_id)
    
    intervention_input = f"[INTERVENTION ACTION]: The user cut in to say/do: {user_intervention}. Adjust plot course immediately!"
    
    db.set_busy_status(user_id, True)
    story_text = generate_story_turn(current_state, chat_history, intervention_input)
    
    db.append_chat_history(user_id, "user", intervention_input)
    db.append_chat_history(user_id, "assistant", story_text)
    
    background_tasks.add_task(update_and_persist_state, current_state, story_text, user_id)
    
    return {"reply": story_text}

# Keep the serve_ui HTML template function below unchanged...

@app.get("/", response_class=HTMLResponse)
def serve_ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Snap Story</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
            background-color: #000; 
            margin: 0; 
            display: flex; 
            justify-content: center; 
            height: 100vh; 
            color: #fff;
        }
        #app-container { 
            width: 100%; 
            max-width: 420px; 
            background-color: #000; 
            display: flex; 
            flex-direction: column; 
            height: 100%; 
            position: relative;
        }
        
        #header { 
            background-color: #000; 
            padding: 15px 20px; 
            display: flex;
            align-items: center;
            justify-content: space-between;
            border-bottom: 1px solid #111;
        }
        .header-title { color: #3498db; font-weight: 600; font-size: 17px; }

        #chat-box { 
            flex: 1; 
            padding: 20px 15px; 
            overflow-y: auto; 
            display: flex; 
            flex-direction: column; 
            gap: 18px; 
        }
        
        .msg-row { display: flex; width: 100%; }
        .msg-row.npc { gap: 12px; align-items: flex-start; }
        .avatar { 
            width: 36px; height: 36px; border-radius: 8px; 
            display: flex; align-items: center; justify-content: center; 
            font-size: 16px; font-weight: bold; flex-shrink: 0; background-color: #1a1a1a;
        }
        .npc-msg-content { 
            display: flex; flex-direction: column; 
            border-left: 2px solid var(--sender-color); padding-left: 10px; padding-bottom: 2px;
        }
        .sender-name { font-size: 15px; font-weight: 700; color: var(--sender-color); margin-bottom: 4px; }
        .msg-text { font-size: 16px; line-height: 1.4; color: #fff; word-wrap: break-word; }
        
        .msg-row.user { justify-content: flex-end; }
        .user-msg-content { 
            background-color: #1a1a1a; padding: 10px 15px; border-radius: 20px; 
            font-size: 15px; border: 1px solid #333; max-width: 85%;
        }

        .narrator-msg { width: 100%; font-size: 16px; color: #e0e0e0; line-height: 1.45; padding: 0 5px; }
        .action-text { color: #aaa; font-style: italic; }

        #input-area { 
            padding: 10px 15px 25px 15px; background-color: #000; display: flex; gap: 12px; align-items: center;
        }
        .input-wrapper {
            flex: 1; background-color: #111; border: 1px solid #222; border-radius: 30px; display: flex; align-items: center; padding: 4px 6px 4px 15px;
        }
        input { flex: 1; border: none; background: transparent; color: white; outline: none; font-size: 16px; }
        input:disabled { color: #555; cursor: not-allowed; }
        input::placeholder { color: #666; }
        
        .action-btn {
            background-color: #333; color: #fff; width: 34px; height: 34px; border-radius: 50%; display: flex; align-items: center; justify-content: center; border: none; cursor: pointer; margin-left: 8px; font-size: 14px; flex-shrink: 0;
            transition: background-color 0.2s ease;
        }
        .action-btn.pause-mode { background-color: #ff3b30; }
        .action-btn:disabled { opacity: 0.3; cursor: not-allowed; }
    </style>
</head>
<body>

<div id="app-container">
    <div id="header">
        <div class="header-title">Interactive Fiction Engine</div>
    </div>
    
    <div id="chat-box"></div>

    <div id="input-area">
        <div class="input-wrapper">
            <input type="text" id="user-input" placeholder="Type your action..." onkeypress="handleKeyPress(event)" autocomplete="off">
            <button id="action-btn" class="action-btn" onclick="handleActionButton()">▶</button>
        </div>
    </div>
</div>

<script>
    const userId = "player_1"; 
    const chatBox = document.getElementById("chat-box");
    const inputField = document.getElementById("user-input");
    const actionBtn = document.getElementById("action-btn");

    let isPlaying = false;
    let isPaused = false;
    let isInterventionPending = false;

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    // Load Chat History from Server on startup
    async function loadChatHistory() {
        try {
            const res = await fetch(`/user_state?user_id=${userId}`);
            const data = await res.json();
            chatBox.innerHTML = "";
            
            if (data.history && data.history.length > 0) {
                for (let msg of data.history) {
                    if (msg.role === "user") {
                        appendUserMessage(msg.content);
                    } else if (msg.role === "assistant") {
                        const lines = msg.content.split('\\n').filter(line => line.trim() !== '');
                        for (let line of lines) {
                            let name = "Narrator";
                            let msgText = line.trim();
                            const match = line.match(/^([^:]+):\\s*(.*)/);
                            if (match) { name = match[1].trim(); msgText = match[2].trim(); }
                            appendNPCMessage(name, msgText);
                        }
                    }
                }
            } else {
                chatBox.innerHTML = '<div class="narrator-msg">Session active. Tap Send to play or Pause during chat to intervene.</div>';
            }
            chatBox.scrollTop = chatBox.scrollHeight;
        } catch (e) {
            chatBox.innerHTML = '<div class="narrator-msg">Session active. Tap Send to play or Pause during chat to intervene.</div>';
        }
    }

    window.onload = loadChatHistory;

    function handleKeyPress(event) { 
        if (event.key === "Enter" && !actionBtn.disabled) {
            handleActionButton();
        } 
    }

    function setBtnState(state) {
        if (state === 'PLAY') {
            actionBtn.innerText = "▶";
            actionBtn.classList.remove("pause-mode");
            actionBtn.disabled = false;
            inputField.disabled = false;
            inputField.placeholder = "Type your action...";
        } else if (state === 'PAUSE') {
            actionBtn.innerText = "⏸";
            actionBtn.classList.add("pause-mode");
            actionBtn.disabled = false;
            inputField.disabled = true;
            inputField.placeholder = "Story playing... tap ⏸ to intervene";
        } else if (state === 'INTERVENE') {
            actionBtn.innerText = "▶";
            actionBtn.classList.remove("pause-mode");
            actionBtn.disabled = false;
            inputField.disabled = false;
            inputField.placeholder = "Intervene plot point...";
            inputField.focus();
        }
    }

    function handleActionButton() {
        if (isPlaying && !isPaused) {
            isPaused = true;
            setBtnState('INTERVENE');
        } else if (isPaused) {
            const text = inputField.value.trim();
            if (text) {
                isInterventionPending = true;
                sendMessage(text, true);
            } else {
                isPaused = false;
                setBtnState('PAUSE');
            }
        } else {
            const text = inputField.value.trim();
            if (text) sendMessage(text, false);
        }
    }

    function getCharacterColor(name) {
        const colors = ["#ff3b30", "#00e5ff", "#ff2d55", "#4cd964", "#ff9500"];
        let hash = 0;
        for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
        return colors[Math.abs(hash) % colors.length];
    }

    function formatActionText(text) {
        return text.replace(/\\*(.*?)\\*/g, '<span class="action-text">* $1 *</span>');
    }

    function appendUserMessage(text) {
        chatBox.insertAdjacentHTML("beforeend", `<div class="msg-row user"><div class="user-msg-content">${formatActionText(text)}</div></div>`);
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    function appendNPCMessage(name, text) {
        const formattedText = formatActionText(text);
        if (name.toLowerCase().includes("narrator")) {
            chatBox.insertAdjacentHTML("beforeend", `<div class="narrator-msg">${formattedText}</div>`);
            return;
        }
        const color = getCharacterColor(name);
        chatBox.insertAdjacentHTML("beforeend", `
            <div class="msg-row npc">
                <div class="avatar" style="color: ${color};">${name.substring(0,2).toUpperCase()}</div>
                <div class="npc-msg-content" style="--sender-color: ${color}">
                    <div class="sender-name">${name}</div>
                    <div class="msg-text">${formattedText}</div>
                </div>
            </div>`);
    }

    async function sendMessage(text, isIntervention) {
        appendUserMessage(text);
        inputField.value = "";

        isPlaying = true;
        setBtnState('PAUSE');

        const serverWaitId = "wait-" + Date.now();
        chatBox.insertAdjacentHTML("beforeend", `<div id="${serverWaitId}" class="narrator-msg action-text">...</div>`);
        chatBox.scrollTop = chatBox.scrollHeight;

        const endpoint = isIntervention 
            ? `/intervene?user_id=${userId}&user_intervention=${encodeURIComponent(text)}` 
            : `/chat?user_id=${userId}&user_input=${encodeURIComponent(text)}`;

        try {
            const response = await fetch(endpoint, { method: "POST" });
            const data = await response.json();
            document.getElementById(serverWaitId).remove();

            const lines = data.reply.split('\\n').filter(line => line.trim() !== '');

            for (let line of lines) {
                if (isInterventionPending && !isIntervention) break;

                while (isPaused) {
                    await sleep(150);
                    if (isInterventionPending) break;
                }
                if (isInterventionPending && !isIntervention) break;

                let name = "Narrator";
                let msgText = line.trim();
                const match = line.match(/^([^:]+):\\s*(.*)/);
                if (match) { name = match[1].trim(); msgText = match[2].trim(); }

                const typingId = "typing-" + Date.now();
                chatBox.insertAdjacentHTML("beforeend", `<div id="${typingId}" class="narrator-msg action-text" style="font-size: 13px;">${name} is typing...</div>`);
                chatBox.scrollTop = chatBox.scrollHeight;

                const delay = Math.min(Math.max(msgText.length * 25, 600), 2500);
                await sleep(delay);

                const typingEl = document.getElementById(typingId);
                if (typingEl) typingEl.remove();

                appendNPCMessage(name, msgText);
                chatBox.scrollTop = chatBox.scrollHeight;
            }

            if (isIntervention) isInterventionPending = false;
            isPlaying = false;
            isPaused = false;
            setBtnState('PLAY');

        } catch (error) {
            if (document.getElementById(serverWaitId)) document.getElementById(serverWaitId).remove();
            isPlaying = false;
            isPaused = false;
            setBtnState('PLAY');
        }
    }
</script>

</body>
</html>
    """