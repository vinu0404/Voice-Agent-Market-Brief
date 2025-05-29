from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from typing import Dict, Any
import json
import os
import os
from dotenv import load_dotenv
load_dotenv() 

def language_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesizes narrative response using LLM for multiple intents.
    Input: State with 'market_data', 'analysis', 'retrieved_docs', 'intents', 'transcript'.
    Output: Updates State with 'narrative': str.
    """
    market_data = state["market_data"]
    analysis = state["analysis"]
    retrieved_docs = state["retrieved_docs"]
    intents = state["intents"]
    transcript = state["transcript"]
    print(f"Language_Agent Input: market_data={market_data}, analysis={analysis}, retrieved_docs={retrieved_docs}, intents={intents}, transcript={transcript}")

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
    reverse_ticker_map = {v: k for k, v in ticker_map.items()}

    narratives = []
    needs_news = any(word in transcript.lower() for word in ["why", "rising", "falling", "up", "down"])

    for intent in intents:
        if intent == "portfolio":
            prompt_template = """You are a friendly financial advisor. For the query: '{transcript}', generate a concise, humanized narrative (under 100 words) summarizing:
            - Portfolio metrics: total value and holdings from {analysis}.
            - If total value is 0 or market data is missing, note potential data issues.Give answer in continous and same fonts.
            Use company names, not tickers. Format as: 'Your portfolio is worth $X, with $Y in Company1, $Z in Company2, etc.' or 'Unable to value your portfolio due to missing market data...'"""
        elif intent == "compare":
            prompt_template = """You are a friendly financial advisor. For the query: '{transcript}', generate a concise, humanized narrative (under 100 words) comparing companies:
            - Market data (prices, metrics) from {market_data}.
            - Comparisons (PE, beta) from {analysis}.Give answer in continous and same fonts.
            Use company names, not tickers. Example: 'Apple’s stock is $200.45, PE 31.22, vs. Microsoft’s $458.61, PE 35.51.'"""
        elif intent == "recommend":
            prompt_template = """You are a friendly financial advisor. For the query: '{transcript}', generate a concise, humanized narrative (under 100 words) for recommendations:
            - Recommendations (with reasons) from {analysis}.Give answer in continous and same fonts.Dont confuse the user with too many recommendations.
            Use company names, not tickers. Example: 'Consider selling TSMC due to high PE (35.00). For buying, consult an advisor.'"""
        elif intent == "price":
            prompt_template = """You are a friendly financial advisor. For the query: '{transcript}', generate a concise, humanized narrative (under 100 words) summarizing:
            - Market data (current/historical prices, metrics) from {market_data}.
            - Relevant news from {retrieved_docs} if the query asks 'why' or mentions trends (rising/falling).Give answer in continous and same fonts.
            Use company names, not tickers. Example: 'Apple’s stock is $200.45, up from $190.30 last month, due to a new product launch (news). PE is 31.22.'"""
        elif intent == "error":
            prompt_template = """You are a friendly financial advisor. For the query: '{transcript}', generate a concise narrative (under 100 words):
            - Apologize and suggest rephrasing.Give answer in continous and same fonts.
            Example: 'Sorry, I couldn’t understand your query. Please try rephrasing.'"""
        else:
            continue

        prompt = PromptTemplate(
            input_variables=["transcript", "market_data", "analysis", "retrieved_docs"],
            template=prompt_template
        )

        # Format data with company names
        formatted_market_data = {
            reverse_ticker_map.get(ticker, ticker): data
            for ticker, data in market_data.items()
        }
        formatted_analysis = {
            "portfolio_metrics": {
                "total_value": analysis.get("portfolio_metrics", {}).get("total_value", 0),
                "holdings": {
                    reverse_ticker_map.get(ticker, ticker): details
                    for ticker, details in analysis.get("portfolio_metrics", {}).get("holdings", {}).items()
                }
            },
            "comparisons": {
                reverse_ticker_map.get(ticker, ticker): details
                for ticker, details in analysis.get("comparisons", {}).items()
            },
            "recommendations": [
                {"company": reverse_ticker_map.get(rec["ticker"], rec["ticker"]), "action": rec["action"], "reason": rec["reason"]}
                for rec in analysis.get("recommendations", []) if rec["ticker"]
            ] + [
                {"company": None, "action": rec["action"], "reason": rec["reason"]}
                for rec in analysis.get("recommendations", []) if not rec["ticker"]
            ]
        }

        try:
            response = llm.invoke(prompt.format(
                transcript=transcript,
                market_data=json.dumps(formatted_market_data),
                analysis=json.dumps(formatted_analysis),
                retrieved_docs=json.dumps(retrieved_docs if needs_news and intent == "price" else [])
            ))
            narratives.append(response.content.strip())
        except Exception as e:
            print(f"Language_Agent Error for {intent}: {e}")
            narratives.append(f"Error generating response for {intent}.")

    narrative = " ".join(narratives) if narratives else "Sorry, I couldn’t process your query. Please try rephrasing."
    print(f"Language_Agent Output: {narrative}")
    return {"narrative": narrative}