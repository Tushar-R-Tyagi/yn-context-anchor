import os
from openai import OpenAI
from dotenv import load_dotenv
from schemas import StoryContext

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def build_system_prompt(context: StoryContext) -> str:
    name = context.user_profile.first_name
    
    return f"""
YOU ARE: The engine for a visual novel / chat-fiction game.

=== IMMUTABLE USER PROFILE ===
Name: {name} {context.user_profile.last_name} (Also referred to as 'You' or 'Y/N')
Traits: {', '.join(context.user_profile.persona_traits)}

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
"""

def generate_story_turn(context: StoryContext, chat_history: list, user_input: str) -> str:
    messages = [{"role": "system", "content": build_system_prompt(context)}]
    messages.extend(chat_history[-6:])
    messages.append({"role": "user", "content": user_input})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=0.8,
    )
    
    story_text = response.choices[0].message.content
    return context.sanitize_template(story_text)