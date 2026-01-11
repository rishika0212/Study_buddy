from backend.app.llm.ollama_client import get_ollama_client
from backend.app.llm.prompts import GAP_DETECTION_PROMPT
from backend.app.memory.user_profile import UserProfile
import json

class GapDetector:
    def __init__(self):
        self.llm = get_ollama_client(temperature=0)

    async def detect_and_update(self, user_id: str, user_input: str, ai_output: str):
        """
        Detect learning gaps from user interaction.
        
        Args:
            user_id: User identifier (session_id is DEPRECATED and removed)
            user_input: User's input message
            ai_output: AI's response
        """
        try:
            profile = UserProfile(user_id)
            
            from langchain.prompts import PromptTemplate
            prompt_template = PromptTemplate.from_template(GAP_DETECTION_PROMPT)
            prompt = prompt_template.format(input=user_input, output=ai_output)
            
            response = await self.llm.ainvoke(prompt + "\n\nReturn the analysis as a JSON object with keys: 'detected_gaps' (list), 'mastered_concepts' (list), 'suggested_level' (beginner/intermediate/advanced).")
            analysis = response.content
            
            # Simple cleanup in case LLM adds markdown or preamble
            json_start = analysis.find('{')
            json_end = analysis.rfind('}') + 1
            if json_start != -1 and json_end != -1:
                data = json.loads(analysis[json_start:json_end])
                
                # Update profile (DISABLED to comply with prohibitions: NEVER infer topics or estimate mastery)
                # for gap in data.get("detected_gaps", []):
                #     profile.data["weak"][gap] = True
                #     if gap in profile.data["strong"]:
                #         del profile.data["strong"][gap]
                # 
                # for concept in data.get("mastered_concepts", []):
                #     profile.data["strong"][concept] = True
                #     if concept in profile.data["weak"]:
                #         del profile.data["weak"][concept]
                # 
                # profile.save()
                pass
            
        except Exception as e:
            # Log error but don't break the flow
            from backend.app.utils.logger import logger
            logger.error(f"Error in gap detection: {e}")
