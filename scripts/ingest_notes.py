import os
import sys

# Add the project root to the python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from backend.app.vectorstore.chroma_client import get_chroma_client

def ingest():
    # Create some dummy notes
    notes = [
        "Quantum Mechanics: The study of matter and light at the atomic and subatomic scale.",
        "Newton's First Law: An object at rest stays at rest, and an object in motion stays in motion unless acted upon by a force.",
        "Photosynthesis: The process by which green plants and some other organisms use sunlight to synthesize foods from carbon dioxide and water.",
        "DNA: Deoxyribonucleic acid is a molecule that carries the genetic instructions used in the growth, development, functioning, and reproduction of all known organisms.",
        "Python: A high-level, interpreted programming language known for its readability and versatility.",
        "The Great Gatsby: A novel by F. Scott Fitzgerald that explores themes of wealth, class, and the American Dream in the 1920s."
    ]
    
    with open("temp_notes.txt", "w") as f:
        f.write("\n\n".join(notes))
    
    loader = TextLoader("temp_notes.txt")
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=100, chunk_overlap=0)
    docs = text_splitter.split_documents(documents)
    
    vectorstore = get_chroma_client()
    vectorstore.add_documents(docs)
    print(f"Ingested {len(docs)} documents into ChromaDB")
    
    os.remove("temp_notes.txt")

if __name__ == "__main__":
    ingest()
