from dotenv import load_dotenv
import os
import shutil
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings  # Changed to OpenAI
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import TextLoader, UnstructuredMarkdownLoader, DirectoryLoader
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# This map now contains the standard filename for each type of data.
TAG_TO_FILENAME_MAP = {
    "Social media analysis": "social_media_analysis.txt",
    "Visual or user engagement": "visual_or_user_engagement.txt",
    "platform value or platform features": "platform_features.txt",
    "platform layout": "platform_layout.txt",
    "Sponsors": "sponsors.txt",
    "player performance": "player_performance.txt",
    "match summary": "match_summary.txt",
    "content strategy / brand engagements": "content_strategy_brand engagements.txt",
    "sponsor visibility": "sponsor_visibility.txt",
    "General Query": "General_Query.txt"
}

FRANCHISES = ['Delhi_Capitals', 'Gujrat_Titans', 'Punjab Kings']
DATABASE_LOCATION = os.getenv("DATABASE_LOCATION")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
PROJECT_ROOT = "."

print("Starting Data Ingestion Process")

def main():
    """
    Main function to run the data ingestion process.
    """
    logger.info("--- Starting Data Ingestion Process ---")

    # Initialized embeddings model
    try:
        embeddings = OpenAIEmbeddings(model=EMBEDDING_MODEL)  # Changed to OpenAI
        logger.info(f"Embeddings model '{EMBEDDING_MODEL}' initialized successfully.")
    except Exception as e:
        logger.error(f"Fatal: Could not initialize embeddings model. Error: {e}")
        return

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=200)

    # Loop through each franchise
    for franchise in FRANCHISES:
        print("-" * 5)
        logger.info(f"Processing franchise: {franchise}")
        
        # Loop through each tag and its corresponding filename
        for tag, filename in TAG_TO_FILENAME_MAP.items():
            
            # This will create paths like Delhi_Capitals/filename.txt
            file_path = os.path.join(PROJECT_ROOT, franchise, filename)
            
            
            if not os.path.exists(file_path):
                logger.warning(f"File for tag '{tag}' not found at '{file_path}'. Skipping.")
                continue

            logger.info(f"Processing tag: '{tag}' from file: {file_path}")

            
            tag_db_path = os.path.join(DATABASE_LOCATION, franchise, tag)

            # whenever we will run this script new vector db will be created and the previous one which was already there will be deleted automatically
            if os.path.exists(tag_db_path):
                logger.info(f"Removing existing database for tag '{tag}' at '{tag_db_path}'.")
                shutil.rmtree(tag_db_path)
            
            try:
                
                loader = TextLoader(file_path, encoding='utf-8')
                documents = loader.load()
                
                # Split the document into chunks
                docs = text_splitter.split_documents(documents)
                logger.info(f"Loaded and split '{os.path.basename(file_path)}' into {len(docs)} chunks.")

                
                collection_name = f"{franchise.lower().replace(' ', '_')}_{tag.lower().replace(' ', '_')}_docs"
                
                
                vector_store = Chroma.from_documents(
                    documents=docs,
                    embedding=embeddings,
                    collection_name=collection_name,
                    persist_directory=tag_db_path  
                )
                
                logger.info(f"[SUCCESS] Data for tag '{tag}' ingested into '{tag_db_path}'")

            except Exception as e:
                logger.error(f"error occurred while processing the tag '{tag}' for {franchise}: {e}")
                continue

    logger.info("--- Data Ingestion Process Finished ---")

if __name__ == "__main__":
    main()
