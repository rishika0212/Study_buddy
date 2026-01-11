from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
import os
from backend.app.config import settings


class ConversationMemoryWrapper:
    """
    A simple wrapper that provides a memory interface similar to the deprecated
    ConversationBufferMemory but works with newer LangChain versions.
    """
    def __init__(self, chat_history: FileChatMessageHistory, memory_key: str = "chat_history"):
        self.chat_memory = chat_history
        self.memory_key = memory_key
    
    def load_memory_variables(self, inputs: dict = None) -> dict:
        """Load memory variables - returns messages as a list."""
        return {self.memory_key: self.chat_memory.messages}
    
    def save_context(self, inputs: dict, outputs: dict) -> None:
        """Save context from this conversation to buffer."""
        input_str = inputs.get("input", inputs.get("human", ""))
        output_str = outputs.get("output", outputs.get("ai", ""))
        
        if input_str:
            self.chat_memory.add_message(HumanMessage(content=input_str))
        if output_str:
            self.chat_memory.add_message(AIMessage(content=output_str))
    
    def clear(self) -> None:
        """Clear memory contents."""
        self.chat_memory.clear()


def get_conversation_memory(user_id: str, session_id: str = None):
    """
    Get conversation memory for a user - topic-centric model, no sessions.
    session_id parameter is DEPRECATED and ignored.
    """
    history_path = os.path.join(settings.USER_DATA_DIRECTORY, f"{user_id}_history.json")
    os.makedirs(settings.USER_DATA_DIRECTORY, exist_ok=True)
    
    chat_history = FileChatMessageHistory(history_path)
    return ConversationMemoryWrapper(
        chat_history=chat_history,
        memory_key="chat_history"
    )
