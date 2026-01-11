from backend.app.llm.ollama_client import get_ollama_client
from backend.app.config import settings
import os

def get_summary_memory(user_id: str):
    """
    Get summary memory for a user.
    
    Args:
        user_id: User identifier (session_id is DEPRECATED and removed)
    """
    llm = get_ollama_client()
    summary_path = os.path.join(settings.USER_DATA_DIRECTORY, f"{user_id}_summary.txt")
    os.makedirs(settings.USER_DATA_DIRECTORY, exist_ok=True)
    
    # Simple manual summary persistence since LangChain summary memory 
    # usually expects to be part of a chain.
    # For now, we'll return a helper that can load/save summary.
    return SummaryManager(summary_path, llm)

class SummaryManager:
    def __init__(self, path, llm):
        self.path = path
        self.llm = llm

    def get_summary(self):
        if os.path.exists(self.path):
            with open(self.path, "r") as f:
                return f.read()
        return "New user. No summary available."

    def update_summary(self, new_messages_str: str):
        current_summary = self.get_summary()
        prompt = f"Current Summary: {current_summary}\n\nNew Interactions: {new_messages_str}\n\nUpdate the summary to include key learning points and progress."
        response = self.llm.invoke(prompt)
        new_summary = response.content
        with open(self.path, "w") as f:
            f.write(new_summary)
        return new_summary
