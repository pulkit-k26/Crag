import os
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from state import State
import re
import json
from langchain_core.messages import AIMessage

class QueryEvaluator(BaseModel):
    """
        Evaluate and categorize the user question.
    """
    category: str = Field(description="The category of the user's question, such as 'greeting', 'relevant', 'irrelevant'.")

system_prompt = """You are an AI support representative of 'Gamesage' tasked with identifying the type of user query. 
Classify each query into one of the following categories:

1. **Greeting**: A friendly or polite greeting.  
2. **Relevant**: A query seeking information related to the given context.  
3. **Irrelevant**: Queries unrelated to Gamesage, such as questions about other topics or random input. Return "irrelevant" for these queries.  

### **Instructions**:  

- Always return **'greeting'** for greeting queries, **'relevant'** for relevant queries, and **'irrelevant'** for irrelevant queries.  
- Clearly determine the category of the query based on its content.  
- Ask for clarification only if the query is ambiguous.  

Your goal is to classify the query accurately and concisely.
"""

llm = ChatOpenAI(
    temperature=0,
    model='gpt-4o-mini'
).with_structured_output(QueryEvaluator)

prompt = ChatPromptTemplate.from_messages([
    ('system', system_prompt),
    ('user', 'User Question: \\n\\n {question}')
])

chain = prompt | llm

def analyze_query(state: State):
    """
    Analyze and categorize the user question

    Args:
        state (State): Current state of the conversation
    Returns:
        dict: State with updated answer and relevance evaluation
    """

    question = state['question']
    
    response = chain.invoke({"question": question})

    return {"question": question, "category": response.category}

TAG_LIST = [
    "Social media analysis", "Visual or user engagement",
    "platform value or platform features", "platform layout", "Sponsors",
    "player performance", "match summary", "content strategy / brand engagements",
    "sponsor visibility", "General Query"
]

def classify_and_tag_query(query: str, llm) -> dict:
    tag_list = TAG_LIST
    prompt_template = f"""
    You are an expert query analyzer. Your task is to analyze the user's query and assign it to one or more of the following categories.

    Categories: {tag_list}

    User Query: "{query}"

    Please perform two tasks:
    1. First, determine if the query has a 'single' intent or 'multiple' intents.
    2. Second, assign the most relevant tag to each distinct part of the query.

    Your response MUST be ONLY a JSON object. Do NOT include any additional text, explanations, or prose outside the JSON.
    The JSON object MUST be in this format:
    {{
      "query_type": "single" or "multiple",
      "queries": [
        {{
          "query_text": "The first part of the query",
          "tag": "assigned_tag_for_part_1"
        }}
      ]
    }}
    """

    response = llm.invoke(prompt_template)
    if isinstance(response, AIMessage):
        raw_text = response.content
    else:
        raw_text = str(response)
    
    json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
    if json_match:
        json_string = json_match.group(0)
        try:
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            return None
    else:
        return None