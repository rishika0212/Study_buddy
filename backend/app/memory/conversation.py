from langchain_community.chat_message_histories import FileChatMessageHistory
from langchain.memory import ConversationBufferMemory
import os
from backend.app.config import settings

def get_conversation_memory(user_id: str, session_id: str = None):
    """
    Get conversation memory for a user - topic-centric model, no sessions.
    session_id parameter is DEPRECATED and ignored.
    """
    history_path = os.path.join(settings.USER_DATA_DIRECTORY, f"{user_id}_history.json")
    os.makedirs(settings.USER_DATA_DIRECTORY, exist_ok=True)
    
    chat_history = FileChatMessageHistory(history_path)
    return ConversationBufferMemory(
        memory_key="chat_history",
        chat_memory=chat_history,
        return_messages=True
    )
