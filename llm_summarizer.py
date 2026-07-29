import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUMMARIZER_SYSTEM_PROMPT = """You maintain a running memory summary for an interactive story.
You will be given the EXISTING SUMMARY and the NEXT CHUNK of transcript that just fell out of the
model's short-term context window. Write an updated summary that a story engine can use in place
of the raw transcript.

Rules:
1. Preserve concrete facts: character names introduced, relationships, locations visited, items
   gained or lost, and unresolved plot threads or promises made.
2. Do NOT invent details that aren't in the existing summary or the new chunk.
3. Keep it dense and factual, not narrative prose. Bullet-point style is fine.
4. Keep it under 200 words even as the story grows longer by trimming stale/resolved threads,
   not by dropping the user's core identity or active plot state.
"""

def fold_history_into_summary(existing_summary: str, messages_to_fold: list) -> str:
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in messages_to_fold)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": SUMMARIZER_SYSTEM_PROMPT},
            {"role": "user", "content": f"EXISTING SUMMARY:\n{existing_summary or '(none yet)'}\n\nNEXT CHUNK:\n{transcript}"}
        ],
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()
