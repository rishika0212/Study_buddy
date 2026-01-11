from langchain_community.vectorstores import Chroma
from langchain_ollama import OllamaEmbeddings
from backend.app.config import settings

def get_chroma_client():
    embeddings = OllamaEmbeddings(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL
    )
    return Chroma(
        persist_directory=settings.CHROMA_PERSIST_DIRECTORY,
        embedding_function=embeddings,
        collection_name="study_materials"
    )
