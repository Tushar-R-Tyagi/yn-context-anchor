import os
from openai import OpenAI
from dotenv import load_dotenv
from schemas import StoryContext

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Number of raw messages sent verbatim; anything older is folded into the
# rolling summary by llm_summarizer.py so details aren't silently dropped.
HISTORY_WINDOW = 6

def build_system_prompt(context: StoryContext, summary: str = "") -> str:
    name = context.user_profile.first_name
    pronouns = context.user_profile.pronouns
    subject_pronoun = pronouns.split("/")[0] if "/" in pronouns else pronouns

    return f"""
YOU ARE: The engine for a visual novel / chat-fiction game.

=== IMMUTABLE USER PROFILE (never contradict this, never re-derive it from context) ===
Name: {name} {context.user_profile.last_name}
Pronouns: {pronouns}
Traits: {', '.join(context.user_profile.persona_traits)}

=== STORY SO FAR (condensed memory of everything before the recent messages below) ===
{summary or "The story has just begun."}

=== CURRENT WORLD STATE ===
Location: {context.world_state.location}
Inventory: {', '.join(context.world_state.active_inventory)}

=== INSTRUCTIONS ===
1. The story takes place in the PHYSICAL WORLD. The characters are physically together, speaking out loud. They are NOT texting on phones.
2. Invent 2 companion characters who are currently exploring with the user.
3. You MUST format your response as a script so our UI can render it. Use this exact format:

CharacterName: Their spoken dialogue here.
AnotherCharacter: Their spoken dialogue here.
Narrator: Physical actions, environmental descriptions, and what the user sees/feels.

NEVER output raw paragraphs. EVERY single line must start with a Name and a colon.
4. Refer to the user ONLY as "{name}" or "{subject_pronoun}". NEVER write the literal placeholder "Y/N" under any circumstances, even as a generic stand-in.
5. Do not invent or change the user's name, pronouns, or traits based on story events. They are fixed for the entire session regardless of how long it runs.
"""

def generate_story_turn(context: StoryContext, chat_history: list, user_input: str, summary: str = "") -> str:
    messages = [{"role": "system", "content": build_system_prompt(context, summary)}]
    messages.extend(chat_history[-HISTORY_WINDOW:])
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
    )
    
    story_text = response.choices[0].message.content
    return context.sanitize_template(story_text)