import sys
import os
# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import CharacterTextSplitter
from backend.app.vectorstore.chroma_client import get_chroma_client
from backend.app.utils.logger import logger

def ingest_documents(directory_path: str):
    logger.info(f"Ingesting documents from {directory_path}")
    
    loader = DirectoryLoader(directory_path, glob="**/*.txt", loader_cls=TextLoader)
    documents = loader.load()
    
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
    docs = text_splitter.split_documents(documents)
    
    vectorstore = get_chroma_client()
    vectorstore.add_documents(docs)
    vectorstore.persist()
    
    logger.info("Ingestion completed successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=str, required=True, help="Path to the directory containing study materials (.txt files)")
    args = parser.parse_argument()
    ingest_documents(args.path)
