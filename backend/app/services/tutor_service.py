from backend.app.agents.study_agent import StudyAgent
from backend.app.utils.logger import logger

class TutorService:
    def __init__(self):
        self.agent = StudyAgent()

    async def process_message(self, user_id: str, message: str, session_id: str = None):
        """
        Process a message - topic-centric model, no sessions.
        session_id parameter is DEPRECATED and ignored.
        """
        logger.info(f"Processing message from {user_id}: {message}")
        
        try:
            # Get AI response 
            agent_data = await self.agent.generate_response(user_id, message)
            
            if not agent_data or not isinstance(agent_data, dict):
                raise ValueError("Agent failed to return valid data")

            response_text = agent_data.get("content", "I'm sorry, I couldn't process that.")
            
            return {
                "response": response_text,
                "metadata": agent_data.get("metadata", {})
            }
        except Exception as e:
            logger.error(f"Error in TutorService.process_message: {e}", exc_info=True)
            return {
                "response": f"I encountered an internal error: {str(e)}",
                "metadata": {}
            }
