__import__('pysqlite3')
import sys
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
from streamlit.components.v1 import html
import os
import base64
import streamlit as st
import logging
import json
import re
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.documents import Document
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import TypedDict

# State Definition
class State(TypedDict):
    question: str
    category: str
    documents: list[Document]
    web_search: str
    answer: str
    franchise: str


from retriever import retriever
from generator import generator
from evaluator import document_evaluator
from decision_maker import decide_to_go_next, decide_response_generator
from query_transformer import transform_query
from web_search import tavily_web_search
from query_analyzer import analyze_query,  classify_and_tag_query
from llm import customer_support

# Graph Builder
graph_builder = StateGraph(State)

# Nodes
graph_builder.add_node('query_analyzer', analyze_query)
graph_builder.add_node('chatbot', customer_support)
graph_builder.add_node('retriever', retriever)
graph_builder.add_node('generator', generator)
graph_builder.add_node('evaluator', document_evaluator)
graph_builder.add_node('query_transformer', transform_query)
graph_builder.add_node('search_web', tavily_web_search)

# Edges
graph_builder.add_edge(START, 'query_analyzer')
graph_builder.add_conditional_edges(
    'query_analyzer',
    decide_response_generator,
    {
        "llm": 'chatbot',
        "retriever": 'retriever',
    }
)
graph_builder.add_edge('chatbot', END)
graph_builder.add_edge('retriever', 'evaluator')

graph_builder.add_conditional_edges(
    'evaluator',
    decide_to_go_next,
    {
        "transform_query": 'query_transformer',
        "generator": 'generator',
    }
)

graph_builder.add_edge('query_transformer', 'search_web')
graph_builder.add_edge('search_web', 'generator')
graph_builder.add_edge('generator', END)

graph = graph_builder.compile()

# Streamlit


def get_tag_to_prompt_map(franchise_name: str) -> dict:
    """Generates a dictionary of system prompts for the given franchise."""
    return {
        "Social media analysis": f"You are a social media analyst for {franchise_name}. Your purpose is to interpret fan engagement data about tweets, likes, shares, and fanbase growth.",
        "Visual or user engagement": f"You are a fan engagement strategist for {franchise_name}. Your role is to explain how the franchise connects with its audience through visuals and videos.",
        "platform value or platform features": f"You are a product manager for the {franchise_name} fan engagement platform. Explain the features and value of the fan app.",
        "platform layout": f"You are a UI/UX analyst. Describe the layout and user experience of the {franchise_name} fan platform.",
        "Sponsors": f"You are a sponsorship expert for {franchise_name}. Detail the franchise's sponsor relationships and strategies.",
        "player performance": f"You are a cricket performance analyst for {franchise_name}. Answer questions about player and team performance using provided data.",
        "match summary": f"You are a cricket commentator for {franchise_name}. Provide match summaries based on the provided documents.",
        "content strategy / brand engagements": f"You are a brand strategist for {franchise_name}. Articulate the team's content marketing plan.",
        "sponsor visibility": f"You are a sponsorship expert for {franchise_name}. Detail how sponsors are placed and made visible in content.",
        "General Query": f"You are a comprehensive team analyst for {franchise_name}. Answer high-level or multi-faceted queries using the provided context.",
    }

def set_background(image_file):
    """
    Sets a background image and applies custom CSS to the Streamlit app.
    This version includes fixes for both dropdown and error message visibility.
    """
    with open(image_file, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()

    # CSS with fixes for dropdown and the new fix for error messages
    css = f"""
    <style>
    /* Basic app styling with background image */
    [data-testid="stAppViewContainer"],
    .stApp {{
        background-image: url("data:image/png;base64,{encoded}") !important;
        background-size: cover !important;
        background-repeat: no-repeat !important;
        background-position: center !important;
        background-attachment: fixed !important;
    }}

    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0) !important;
    }}

    /* General text color */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {{
        color: white !important;
    }}

    /* --- ERROR MESSAGE VISIBILITY FIX --- */
    /* This targets the Streamlit exception/error box */
    [data-testid="stException"] {{
        background-color: rgba(40, 0, 0, 0.8) !important; /* Dark red semi-transparent background */
        border: 1px solid #FF4B4B !important;
        border-radius: 0.5rem !important;
    }}

    /* This targets all text inside the error box to make it white and readable */
    [data-testid="stException"] * {{
        color: white !important;
    }}
    /* --- END OF FIX --- */

    /* Style for the main selectbox component (when closed) */
    .stSelectbox > div[data-baseweb="select"] > div {{
        background-color: rgba(0,0,0,0.7) !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
        color: white !important;
    }}

    /* Dropdown menu fix */
    div[data-baseweb="popover"] ul {{
        background-color: #222222 !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }}

    div[data-baseweb="popover"] ul li {{
        color: white !important;
        background-color: transparent !important;
    }}

    div[data-baseweb="popover"] ul li:hover {{
        background-color: rgba(255, 255, 255, 0.2) !important;
    }}

    div[data-baseweb="popover"] ul li[aria-selected="true"] {{
        background-color: rgba(255, 255, 255, 0.4) !important;
    }}

    /* Other component styles */
    .stChatInput > div > div {{
        background-color: rgba(0,0,0,0.5) !important;
        color: white !important;
        border: 1px solid rgba(255,255,255,0.3) !important;
    }}

    .stChatMessage {{
        background-color: rgba(0,0,0,0.3) !important;
        color: white !important;
        border-radius: 10px !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def get_svg_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Logo file not found at {file_path}")
        return None

# Load environment variables
load_dotenv()

if __name__ == "__main__":
    st.set_page_config(page_title="GameSage AI")
    set_background("final_bg_blurred_more.png")

    svg_logo_path = "original_gamesage_logo.svg"
    svg_content = get_svg_content(svg_logo_path)
    col1, col2 = st.columns([2, 10])
    with col1:
        if svg_content:
            st.image("original_gamesage_logo.svg", width=120)
    with col2:
        st.title("𝙶𝚊𝚖𝚎𝚂𝚊g𝚎 𝙰𝙸 ◔_◔")
    st.divider()

    st.subheader("Choose Franchise")
    franchise_options = ['Delhi_Capitals', 'Gujrat_Titans', 'Punjab Kings']
    selected_franchise = st.selectbox(
        label="Choose a franchise to chat with:",
        options=franchise_options,
        label_visibility='collapsed'
    )

    if selected_franchise:
        # Managed Chat History
        session_key = f"agent_messages_{selected_franchise.replace(' ', '_')}"
        if session_key not in st.session_state:
            st.session_state[session_key] = [
                AIMessage(content=f"Hello! I'm your agent for {selected_franchise}. How can I help?")
            ]

        for message in st.session_state[session_key]:
            with st.chat_message(message.type):
                st.markdown(message.content)

        if user_question := st.chat_input(f"Ask about {selected_franchise}..."):
            st.session_state[session_key].append(HumanMessage(content=user_question))
            with st.chat_message("user"):
                st.markdown(user_question)
            with st.chat_message("assistant"):
                with st.spinner("Agent is analyzing and retrieving data..."):
                    inputs = {"question": user_question, "franchise": selected_franchise}
                    response_generator = graph.invoke(inputs)
                    ai_response = response_generator.get("answer", "Sorry, I encountered an error.")
                    st.markdown(ai_response)
            st.session_state[session_key].append(AIMessage(content=ai_response))
