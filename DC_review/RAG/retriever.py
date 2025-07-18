import os
import json
import re
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.messages import AIMessage
from state import State

# Load environment variables from .env file
load_dotenv()

TAG_LIST = [
    "Social media analysis", "Visual or user engagement",
    "platform value or platform features", "platform layout", "Sponsors",
    "player performance", "match summary", "content strategy / brand engagements",
    "sponsor visibility", "General Query"
]

def classify_and_tag_query(query: str, llm) -> dict:
    """
    Analyzes the user's query to assign one or more relevant tags.
    """
    prompt_template = f"""
    You are an expert query analyzer. Your task is to analyze the user's query and assign it to one or more of the following categories.
    Categories: {TAG_LIST}
    User Query: "{query}"

    Your response MUST be ONLY a JSON object in this format:
    {{
        "query_type": "single" or "multiple",
        "queries": [
            {{"query_text": "The first part of the query", "tag": "assigned_tag_for_part_1"}}
        ]
    }}
    """
    response = llm.invoke(prompt_template)
    raw_text = response.content if isinstance(response, AIMessage) else str(response)
    
    
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            print("Error: Failed to decode JSON from LLM response.")
            return {}
    return {}

def retriever(state: State):
    """
    Analyzes the user's question, identifies the correct tag, and retrieves 
    documents from the corresponding franchise-specific ChromaDB.
    """
    print("--- CHROMA DB RETRIEVER NODE (using OpenAI) ---")
    question = state['question']
    franchise = state.get('franchise')

    if not franchise:
        print("Error: Franchise not found in the application state. Cannot retrieve data.")
        return {"documents": [], "question": question}

    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    
    tagged_query_data = classify_and_tag_query(question, llm)
    print(f"Classifier Output: {tagged_query_data}")

    if not tagged_query_data or not tagged_query_data.get("queries"):
        print("Classifier failed. No documents will be retrieved.")
       
        return {"documents": [], "question": question}

  
    final_docs = []
    for item in tagged_query_data.get("queries", []):
        sub_query = item.get("query_text")
        tag = item.get("tag")

        if not sub_query or not tag or tag not in TAG_LIST:
            continue
        
       
        db_path_for_tag = os.path.join(os.getenv("DATABASE_LOCATION"), franchise, tag)
        
        if not os.path.exists(db_path_for_tag):
            print(f"Warning: Database for tag '{tag}' not found at '{db_path_for_tag}'. Skipping.")
            continue
        
        try:
            print(f"Loading DB for tag: {tag}")
            vector_store = Chroma(
                persist_directory=db_path_for_tag,
                embedding_function=embeddings,
            )
            retriever_for_tag = vector_store.as_retriever(search_kwargs={"k": 5})
            
            docs = retriever_for_tag.invoke(sub_query)
            final_docs.extend(docs)
            print(f"Retrieved {len(docs)} documents for tag '{tag}'.")
        
        except Exception as e:
            print(f"Error retrieving data for tag '{tag}': {e}")

    return {"documents": final_docs, "question": question}