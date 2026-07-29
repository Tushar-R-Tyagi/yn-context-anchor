import os
import json
from openai import OpenAI
from schemas import StoryContext

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def update_story_state(context: StoryContext, recent_text: str):
    system_prompt = f"""
    You are a backend state tracker for a video game. 
    Read the following story text and determine if the world state has changed.
    
    CURRENT STATE:
    Location: {context.world_state.location}
    Inventory: {context.world_state.active_inventory}
    
    INSTRUCTIONS:
    1. If the text explicitly states the character moved, update the location. Otherwise, keep it the same.
    2. If the text explicitly states the character acquired or lost an item, update the inventory.
    3. You MUST respond in pure JSON format matching exactly this structure:
    {{
        "location": "string",
        "active_inventory": ["item1", "item2"]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"LATEST STORY EVENT: {recent_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json_string = response.choices[0].message.content
        updated_data = json.loads(raw_json_string)
        
        context.world_state.location = updated_data.get("location", context.world_state.location)
        context.world_state.active_inventory = updated_data.get("active_inventory", context.world_state.active_inventory)
        
        print("\n--- [AUDITOR REPORT] ---")
        print(f"Location: {context.world_state.location}")
        print(f"Inventory: {context.world_state.active_inventory}")
        print("------------------------\n")
        
    except Exception as e:
        print(f"[AUDITOR ERROR] Something went wrong: {e}")