import os
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from state import State


llm = ChatOpenAI(model='gpt-4o-mini', temperature=0)
output_parser = StrOutputParser()

def generator(state: State):
    """
    Generates a response based on the user's question and retrieved documents for a specific franchise.
    """
    print("--- GENERATOR NODE ---")
    question = state['question']
    documents = state['documents']
    franchise = state.get('franchise', 'the team')

    # Dynamic prompt
    system_message = f"""You are CricketGPT, a specialized AI assistant for the {franchise}.
    Your primary function is to provide highly accurate and concise answers using ONLY the information from the retrieved context.

    Instructions:
    - Answer the user's question directly using the provided "Context" below.
    - If the context does not contain the answer, state that the information is not available in the knowledge base.
    - Do NOT invent, assume, or infer any information that is not explicitly present in the context.
    - Be factual and maintain the persona of a professional sports analyst.

    Context:
    {{context}}
    """
    
    prompt = ChatPromptTemplate.from_messages([
        ('system', system_message),
        ('user', "Question: {question}")
    ])

    rag_chain = prompt | llm | output_parser
    
    # Prepare context from documents
    context_str = '\\n\\n'.join(doc.page_content for doc in documents)
    
    response = rag_chain.invoke({'question': question, 'context': context_str})

    return {"answer": response, "documents": documents}