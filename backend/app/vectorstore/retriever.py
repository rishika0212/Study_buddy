from backend.app.vectorstore.chroma_client import get_chroma_client

def retrieve_context(query: str, k: int = 4):
    vectorstore = get_chroma_client()
    docs = vectorstore.similarity_search(query, k=k)
    return "\n\n".join([doc.page_content for doc in docs])
