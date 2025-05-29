import logging
from langgraph.graph import StateGraph, END
from typing import TypedDict, List, Dict, Any
from agents.api_agent import api_agent
from agents.retriever_agent import retriever_agent
from agents.analysis_agent import analysis_agent
from agents.language_agent import language_agent
from agents.voice_agent import voice_agent
from agents.news_agent import news_agent
from langchain_aws import ChatBedrock
import json
import re
import os
import os
from dotenv import load_dotenv
load_dotenv() 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

class State(TypedDict):
    transcript: str
    companies: List[str]
    intents: List[str]
    market_data: Dict[str, Any]
    news_data: Dict[str, Any]
    retrieved_docs: List[Any]
    portfolio_data: Dict[str, Any]
    analysis: Dict[str, Any]
    narrative: str
    audio_input: str
    audio_output: str
    time_query: str
    error: str
    node: str  # Added to track node context

def intent_classifier(state: State) -> State:
    """
    Classifie intents using LLM with fallback keyword matching.
    """
    transcript = state.get("transcript", "").lower()
    logger.info(f"Intent_Classifier Input: transcript={transcript}")
    if not transcript:
        logger.error("Intent_Classifier Error: No transcript available")
        return {
            "intents": ["error"],
            "companies": [],
            "time_query": None,
            "error": "No transcript generated from audio."
        }

    # Load LLM configuration from environment variables
    model_id = os.getenv("LLM_MODEL_ID")
    region_name = os.getenv("LLM_REGION")
    if not model_id or not region_name:
        raise ValueError("LLM_MODEL_ID or LLM_REGION not set in environment variables")

    llm = ChatBedrock(model_id=model_id, region_name=region_name)

    # Load ticker_map from config.json
    with open("config.json", "r") as f:
        config = json.load(f)
    ticker_map = config["ticker_map"]

    companies = []
    for name, ticker in ticker_map.items():
        if name.lower() in transcript or ticker.lower() in transcript:
            companies.append(ticker)

    intents = []
    portfolio_keywords = ["portfolio", "balance", "holdings", "investment"]
    compare_keywords = ["compare", "versus", "vs"]
    recommend_keywords = ["recommend", "sell", "buy", "should i"]
    price_keywords = ["price", "stock", "value", "cost"]
    if any(keyword in transcript for keyword in portfolio_keywords):
        intents.append("portfolio")
    if any(keyword in transcript for keyword in compare_keywords):
        intents.append("compare")
    if any(keyword in transcript for keyword in recommend_keywords):
        intents.append("recommend")
    if any(keyword in transcript for keyword in price_keywords):
        intents.append("price")

    prompt = f"""
    You are a financial assistant. Analyze the query: '{transcript}'.
    Identify all applicable intents from: [price, portfolio, compare, recommend].
    - 'price': Queries about current or historical stock prices.
    - 'portfolio': Questions about the user's portfolio.
    - 'compare': Comparisons between companies.
    - 'recommend': Buy or sell recommendations.
    Return a JSON list of intents, allowing multiple intents.
    If no intents match, return ["error"].
    Example: ["portfolio", "recommend"]
    """
    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        if not content:
            raise ValueError("Empty LLM response")
        intents_llm = json.loads(content)
        if not intents_llm:
            intents_llm = ["error"]
        intents = list(set(intents + intents_llm))
        if not intents or intents == ["error"]:
            intents = ["error"]
    except Exception as e:
        logger.error(f"Intent_Classifier Error: {e}")
        intents = intents if intents else ["error"]

    time_query = None
    if "ago" in transcript:
        match = re.search(r"(\d+)\s*(day|week|month|year)s?\s*ago", transcript)
        if match:
            time_query = match.group(0)

    output = {
        "intents": intents,
        "companies": companies,
        "time_query": time_query,
        "error": None if intents != ["error"] else "Intent classification failed"
    }
    logger.info(f"Intent_Classifier Output: {output}")
    return output

def load_portfolio(state: State) -> State:
    """
    Loads portfolio data from data/portfolio.json.
    """
    logger.info("Loading portfolio data")
    try:
        with open("data/portfolio.json", "r") as f:
            portfolio_data = json.load(f)
        logger.info(f"Portfolio Data Loaded: {portfolio_data}")
        return {"portfolio_data": portfolio_data}
    except Exception as e:
        logger.error(f"Portfolio Load Error: {e}")
        return {"portfolio_data": {}, "error": str(e)}

def should_fetch_news(state: State) -> str:
    """
    Determines if news should be fetched based on intents and transcript.
    """
    transcript = state.get("transcript", "").lower()
    intents = state.get("intents", [])
    needs_news = any(word in transcript for word in ["why", "rising", "falling", "up", "down"])
    logger.info(f"Should fetch news: intents={intents}, needs_news={needs_news}")
    return "news_agent" if "price" in intents and needs_news else "api_agent"

def workflow():
    """
    Creates LangGraph workflow for finance assistant.
    """
    graph = StateGraph(State)
    graph.add_node("voice_agent_stt", lambda state: voice_agent({**state, "node": "voice_agent_stt"}))
    graph.add_node("intent_classifier", intent_classifier)
    graph.add_node("load_portfolio", load_portfolio)
    graph.add_node("api_agent", api_agent)
    graph.add_node("news_agent", news_agent)
    graph.add_node("retriever_agent", retriever_agent)
    graph.add_node("analysis_agent", analysis_agent)
    graph.add_node("language_agent", language_agent)
    graph.add_node("voice_agent_tts", lambda state: voice_agent({**state, "node": "voice_agent_tts"}))

    graph.add_edge("voice_agent_stt", "intent_classifier")
    graph.add_edge("intent_classifier", "load_portfolio")
    graph.add_conditional_edges("load_portfolio", should_fetch_news, {
        "news_agent": "news_agent",
        "api_agent": "api_agent"
    })
    graph.add_edge("news_agent", "retriever_agent")
    graph.add_edge("api_agent", "retriever_agent")
    graph.add_edge("retriever_agent", "analysis_agent")
    graph.add_edge("analysis_agent", "language_agent")
    graph.add_edge("language_agent", "voice_agent_tts")
    graph.add_edge("voice_agent_tts", END)

    graph.set_entry_point("voice_agent_stt")
    return graph.compile()