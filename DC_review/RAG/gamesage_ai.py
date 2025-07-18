import os
from dotenv import load_dotenv
import base64
import streamlit as st
import logging
import json
import re
from langchain_chroma import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_ollama import ChatOllama
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


TAG_LIST = [
    "Social media analysis", "Visual or user engagement",
    "platform value or platform features", "platform layout", "Sponsors",
    "player performance", "match summary", "content strategy / brand engagements",
    "sponsor visibility", "General Query"
]

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
    with open(image_file, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()
    css = f"""
    <style>
    [data-testid="stAppViewContainer"] {{
        background-image: url("data:image/png;base64,{encoded}");
        background-size: cover;
        background-repeat: no-repeat;
        background-position: center;
        background-attachment: fixed;
    }}

    [data-testid="stHeader"] {{
        background: rgba(0,0,0,0);
    }}

    [data-testid="stToolbar"] {{
        right: 2rem;
        top: 2rem;
    }}

    /* Optional: make text white for better contrast */
    h1, h2, h3, h4, h5, h6, p, div, span {{
        color: white !important;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# Load environment variables
load_dotenv()

# streamlit UI
st.set_page_config(page_title="GameSage AI")

set_background("final_bg_blurred_more.png")


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


def get_svg_content(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        st.warning(f"Logo file not found at {file_path}")
        return None

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

    TAG_TO_PROMPT_MAP = get_tag_to_prompt_map(selected_franchise)
    embeddings = OllamaEmbeddings(model=os.getenv("EMBEDDING_MODEL"))
    embeddings = OllamaEmbeddings(
    model=os.getenv("EMBEDDING_MODEL"),

    query_instruction=(
          "Analyze the user's cricket question to extract all key entities, statistics, "
        "match specifics (e.g., player names, runs, wickets, overs, match dates, opponents), "
        "and conceptual tags (e.g., social media, sponsorship, player performance, content strategy). "
        "Formulate a precise retrieval query that captures the user's intent to find exact matches "
        "or closely related information from the knowledge base. Prioritize numerical data and proper nouns."
    ),

    embed_instruction=(
        "Represent this cricket and franchise-specific data for highly precise semantic retrieval. "
        "Emphasize named entities (players, sponsors, campaigns), numerical statistics (runs, wickets, percentages), "
        "dates, match outcomes, and key descriptive phrases related to content, platforms, and fan engagement. "
        "Ensure the embedding captures the exact meaning and context of cricket actions and business strategies "
        "to enable direct matching with user queries across all relevant data categories."
    )

)

    llm = ChatOllama(model="llama3.1:8b")


    # Load Vector Store
    db_path = os.path.join(os.getenv("DATABASE_LOCATION"), selected_franchise)
    collection_name = f"{selected_franchise.lower().replace(' ', '_')}_docs"
    if not os.path.exists(db_path):
        st.error(f"Database for {selected_franchise} not found. Please run the data ingestion script.")
        st.stop() # Keep this st.stop() as it's a critical setup issue.
    vector_store = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=db_path,
    )
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 10})

    # Retriever Tool created
    @tool
    def retrieve_franchise_data(query: str) -> str:
        """  Retrieves highly relevant, granular cricket and franchise-specific data from the knowledge base.
        This includes player statistics, match summaries, social media insights,
        platform features, sponsor details, and content strategies.
        Prioritize extracting exact keywords and numerical data to ensure precise
        information retrieval for the user's specific query."""
        docs = retriever.invoke(query)
        return "\n\n".join([doc.page_content for doc in docs])

    tools = [retrieve_franchise_data]


    #Agent Prompt

    agent_prompt = ChatPromptTemplate.from_messages([
    ("system", (
        f"You are CricketGPT, an advanced AI designed for {selected_franchise}, acting as a precise cricket data analyst and strategist. "
        "Your primary function is to provide highly accurate, concise, and direct answers using ONLY the information retrieved from the knowledge base. "
        "Adhere strictly to the defined roles and purposes of each content tag.\n\n"

        "- CORE PRINCIPLES:\n"
        "- Accuracy First: Only provide information explicitly present in the retrieved context. Do NOT invent or infer.\n"
        "- Conciseness: Answer directly and avoid unnecessary preamble or conversational filler.\n"
        "- Role Adherence: Maintain the persona and scope defined by the most relevant tag's prompt (e.g., social media analyst, brand strategist).\n"
        "- Comprehensive Retrieval: Always use the 'retrieve_franchise_data' tool for ANY cricket-related question to gather all necessary context.\n"
        "- Contextual Reliance: If the retrieved context does not contain the answer, state that the information is not available in the knowledge base.\n\n"

        "Remember: Your goal is to be a factual, efficient, and highly specialized cricket information agent for {selected_franchise}."
    )),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])


    agent = create_tool_calling_agent(llm, tools, agent_prompt)

    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    #Managed Chat History
    session_key = f"agent_messages_{selected_franchise.replace(' ', '_')}"
    if session_key not in st.session_state:
        st.session_state[session_key] = [
            AIMessage(content=f"Hello! I'm your agent for {selected_franchise}. How can I help?")
        ]

    for message in st.session_state[session_key]:
        with st.chat_message(message.type):
            st.markdown(message.content)


    if user_question := st.chat_input(f"Ask about {selected_franchise}..."):
        
        if session_key not in st.session_state:
            st.session_state[session_key] = []
        st.session_state[session_key].append(HumanMessage(content=user_question))

        with st.chat_message("user"):
            st.markdown(user_question)

        with st.chat_message("assistant"):
            with st.spinner("Agent is analyzing and retrieving data..."):

                #Classifying the user query to get relevant tags
                tagged_query_data = classify_and_tag_query(user_question, llm)

                if not tagged_query_data or not tagged_query_data.get("queries"):
                    ai_response = "Sorry, I could not understand the intent of your query. Please try rephrasing."
                    st.markdown(ai_response)
                    st.session_state[session_key].append(AIMessage(content=ai_response))
                else: 
                    final_context = []

                    
                    for item in tagged_query_data.get("queries", []):
                        sub_query = item.get("query_text")
                        tag = item.get("tag")

                    
                        if not sub_query or not tag or tag not in TAG_LIST:
                            continue

                        
                        collection_name_for_retrieval = f"{selected_franchise.lower().replace(' ', '_')}_{tag.lower().replace(' ', '_')}_docs"

                        # path to the specific database for the tag
                        db_path_for_tag = os.path.join(os.getenv("DATABASE_LOCATION"), selected_franchise, tag)

                        if not os.path.exists(db_path_for_tag):
                            logging.warning(f"Database for tag '{tag}' not found at {db_path_for_tag}. Skipping.")
                            continue

                        try:
                            # Loaded the specific vector store for the tag
                            vector_store_for_tag = Chroma(
                                collection_name=collection_name_for_retrieval,
                                embedding_function=embeddings,
                                persist_directory=db_path_for_tag,
                            )
                            retriever_for_tag = vector_store_for_tag.as_retriever(search_kwargs={"k": 5})

                            # Retrieved relevant documents
                            docs = retriever_for_tag.invoke(sub_query)
                            final_context.append(f"--- Data for tag '{tag}' ---\n" + "\n\n".join([doc.page_content for doc in docs]))

                        except Exception as e:
                            logging.error(f"Error retrieving data for tag '{tag}' for {selected_franchise}: {e}")

                    if not final_context:
                        ai_response = "No relevant information found for your query."
                        st.markdown(ai_response) 
                        st.session_state[session_key].append(AIMessage(content=ai_response))
                    else:
                        
                        combined_context = "\n\n".join(final_context)
                        primary_tag = tagged_query_data["queries"][0].get("tag")
                        system_instruction = TAG_TO_PROMPT_MAP.get(primary_tag, TAG_TO_PROMPT_MAP.get("General Query", "You are a helpful assistant."))

        
                        rag_prompt = ChatPromptTemplate.from_messages([
                            ("system", system_instruction + "\n\n--- IMPORTANT INSTRUCTIONS ---\n"
                             "You MUST use the context provided below to answer the user's question. "
                             "Synthesize the information accurately and answer comprehensively."
                             "\n\nCONTEXT:\n{context}"
                            ),
                            MessagesPlaceholder(variable_name="chat_history"),
                            ("human", "{input}"),
                        ])

                        rag_chain = (
                            {
                                "context": lambda x: combined_context,
                                "input": lambda x: x["input"],
                                "chat_history": lambda x: x["chat_history"]
                            }
                            | rag_prompt
                            | llm
                            | StrOutputParser()
                        )

                        # final response
                        response = rag_chain.invoke({
                            "input": user_question,
                            "chat_history": st.session_state[session_key]
                        })

                        ai_response = response
                        st.markdown(ai_response)
                        st.session_state[session_key].append(AIMessage(content=ai_response))