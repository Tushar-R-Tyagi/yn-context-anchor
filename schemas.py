from pydantic import BaseModel
from typing import List

class UserProfile(BaseModel):
    first_name: str
    last_name: str
    pronouns: str
    persona_traits: List[str]

class WorldState(BaseModel):
    location: str
    active_inventory: List[str]

class StoryContext(BaseModel):
    user_profile: UserProfile
    world_state: WorldState
    
    def sanitize_template(self, text: str) -> str:
        return text.replace("Y/N", self.user_profile.first_name)