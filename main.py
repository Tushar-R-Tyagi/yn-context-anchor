from pathlib import Path

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from schemas import StoryContext
from llm_narrator import generate_story_turn, HISTORY_WINDOW
from llm_tracker import update_story_state
from llm_summarizer import fold_history_into_summary
import database as db

app = FastAPI()

INDEX_HTML_PATH = Path(__file__).parent / "index.html"

# Initialize SQLite database schema on startup
@app.on_event("startup")
def startup():
    db.init_db()

def fold_history_if_needed(user_id: str):
    # Once messages fall outside the narrator's raw HISTORY_WINDOW, compress
    # them into the rolling summary so those details aren't just lost.
    summary, history, summarized_count = db.get_summarization_state(user_id)
    overflow_end = len(history) - HISTORY_WINDOW

    if overflow_end > summarized_count:
        messages_to_fold = history[summarized_count:overflow_end]
        new_summary = fold_history_into_summary(summary, messages_to_fold)
        db.update_summary(user_id, new_summary)
        db.set_summarized_count(user_id, overflow_end)

def update_and_persist_state(context: StoryContext, story_text: str, user_id: str):
    # Run Auditor to extract inventory / locations
    update_story_state(context, story_text)
    # Save updated state to SQLite and release busy status
    db.update_user_world_state(user_id, context)
    # Fold any newly-overflowed history into the rolling summary
    fold_history_if_needed(user_id)

@app.get("/user_state")
def get_user_state(user_id: str = "player_1"):
    context, _summary, history, is_busy = db.get_or_create_user(user_id)
    return {
        "location": context.world_state.location,
        "active_inventory": context.world_state.active_inventory,
        "is_busy": is_busy,
        "history": history
    }

@app.post("/chat")
def chat_endpoint(user_id: str, user_input: str, background_tasks: BackgroundTasks):
    current_state, summary, chat_history, is_busy = db.get_or_create_user(user_id)

    if is_busy:
        raise HTTPException(status_code=429, detail="Previous action is still processing.")

    db.set_busy_status(user_id, True)
    story_text = generate_story_turn(current_state, chat_history, user_input, summary)
    
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
    current_state, summary, chat_history, _ = db.get_or_create_user(user_id)

    intervention_input = f"[INTERVENTION ACTION]: The user cut in to say/do: {user_intervention}. Adjust plot course immediately!"

    db.set_busy_status(user_id, True)
    story_text = generate_story_turn(current_state, chat_history, intervention_input, summary)
    
    db.append_chat_history(user_id, "user", intervention_input)
    db.append_chat_history(user_id, "assistant", story_text)
    
    background_tasks.add_task(update_and_persist_state, current_state, story_text, user_id)
    
    return {"reply": story_text}

@app.get("/")
def serve_ui():
    return FileResponse(INDEX_HTML_PATH)