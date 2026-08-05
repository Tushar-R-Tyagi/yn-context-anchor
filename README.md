# Motivation & Project Background

## Discovering Y/n

I first stumbled upon **Y/N** while browsing [Work at a Startup](https://www.workatastartup.com/). Intrigued by the concept of interactive fiction, I downloaded the app, and was instantly hooked. Within just two weeks, I spent **over 40 hours** on the platform. It stands out because it allows me to step directly into my favorite screenplays, interact with iconic characters, and co-write stories in real time.

---

## The Problems I noticed

After spending dozens of hours interacting with deep, multi-turn storylines (40+ turns), I began noticing some limitations

1. **Memory Amnesia (MECW Collapse):** Over extended sessions, key inventory items, past events, time and physical locations fade as older context scrolls past the model's active window.
2. **Identity Drift ("Y/N" Placeholder Leakage):** As context grows long, character identity, gender markers, and user naming conventions can occasionally bleed back into generic raw template variables (e.g., rendering `"Y/N"` directly to the screen).

After long usage, some chats just became dissapointing because the details were being forgotten by the engine. I also noticed similar complaints in the discord channel as well.

---

## The Solution 

Rather than just logging feedback or pointing out these edge cases, I wanted to **actively contribute to solving them**.

This repository is an **experimental proof-of-concept**, not a benchmarked production system, built to test a simple thesis:

> *"By decoupling creative prose generation (Narrator) from deterministic state tracking (Auditor) into an isolated Dual-LLM + SQLite architecture, we can drive state hallucinations and identity drift toward zero, with minimal added latency from the background tracking calls."*

---

## How it actually works

The core idea here is pretty simple: stop asking one model to write the story AND remember everything about it at the same time. Those are two different jobs, and cramming both into a single long chat history is exactly why things fall apart after 40+ turns. So this splits it into a few pieces that each do one job.

**The Narrator.** This is the model that actually writes the story (`llm_narrator.py`). Every turn it gets a system prompt built fresh from the user's stored profile (name, pronouns, traits) and the current world state (location, inventory), not from whatever it can dig up in the scrollback. That's the whole point. Identity and location aren't things the model needs to "remember," they're just handed to it every single time. There's also a `sanitize_template()` step that hard swaps the literal `Y/N` placeholder for the real name if it ever slips through anyway, since I'd rather have a dumb safety net than trust the model 100% of the time.

**The Auditor.** After the Narrator generates a reply, a second, cheaper model call runs in the background (`llm_tracker.py`) and reads that reply to figure out if the location changed or if an item was picked up or dropped. It writes the result straight to SQLite. This is the part that actually fixes the inventory hallucination problem, because the game state isn't something the model has to infer from a paragraph of prose three screens back, it's a row in a database that gets updated deterministically after every turn.

**The rolling summarizer.** This one took the most thought. The Narrator only ever sees the last few raw messages (`HISTORY_WINDOW` in `llm_narrator.py`), same as most chat apps, but instead of just letting everything older than that vanish, those older turns get folded into a running summary before they fall out of the window (`llm_summarizer.py`). So the model always gets a compact "story so far" alongside the recent raw messages. Nothing just disappears, it gets compressed instead. I track how much of the history has already been folded with a `summarized_count` column so nothing gets summarized twice.

**Persistence.** Everything lives in SQLite (`database.py`), not in memory and not in the chat history itself. Chat history is stored so the frontend can replay a session, but the story state (name, pronouns, location, inventory, summary) is its own thing entirely, separate from the raw transcript. That separation is really the whole trick this project is built around.

A rough map of the pieces:

- `main.py` - the FastAPI app, wires everything together, exposes `/chat`, `/intervene` (for jumping in mid-scene), and `/user_state`
- `schemas.py` - the Pydantic models for user profile and world state
- `llm_narrator.py` - builds the prompt and generates the actual story text
- `llm_tracker.py` - the background auditor that extracts state changes
- `llm_summarizer.py` - folds old history into a running summary
- `database.py` - SQLite reads/writes for everything above
- `index.html` - the frontend, plain HTML/JS, no framework

To run it locally you'll need an `OPENAI_API_KEY` in a `.env` file, then:

```
pip install -r requirements.txt
uvicorn main:app --reload
```

and open `http://127.0.0.1:8000`.
