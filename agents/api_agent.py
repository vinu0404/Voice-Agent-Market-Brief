import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import time
import os
import yfinance as yf
import pandas as pd
import os
from dotenv import load_dotenv
load_dotenv() 

def api_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches market data for companies based on intents and portfolio holdings.
    Uses Alpha Vantage, falls back to yfinance if it fails. Converts non-USD prices (e.g., KRW for .KS tickers) to USD.
    Input: State with 'companies', 'time_query', 'intents', 'portfolio_data'.
    Output: Updates State with 'market_data': Dict[str, Any].
    """
    companies = state["companies"]
    time_query = state["time_query"]
    intents = state["intents"]
    portfolio_data = state["portfolio_data"]
    print(f"API_Agent Input: companies={companies}, time_query={time_query}, intents={intents}")

    api_key = os.getenv("ALPHA_VANTAGE_KEY")
    if not api_key:
        raise ValueError("ALPHA_VANTAGE_KEY not set in environment variables")

    market_data = {}
    
    if "portfolio" in intents and portfolio_data.get("holdings"):
        companies = list(set(companies + list(portfolio_data["holdings"].keys())))
    companies = list(set(companies))

    max_retries = 1
    retry_delay = 5
    krw_to_usd = 0.00073  # Approximate exchange rate as of May 2025

    for company in companies:
        if company in market_data and "error" not in market_data[company]:
            continue
        alpha_vantage_success = False
        for attempt in range(max_retries):
            try:
                symbol = company if "." in company else company + ".US"
                url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={api_key}"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                print(f"API_Agent Response for {company} (Attempt {attempt+1}): {data}")

                if "Global Quote" in data and data["Global Quote"]:
                    quote = data["Global Quote"]
                    current_price = float(quote.get("05. price", 0))
                    market_data[company] = {
                        "current_price": current_price,
                        "change_percent": quote.get("10. change percent", "0%"),
                        "timestamp": quote.get("07. latest trading day", datetime.now().strftime("%Y-%m-%d"))
                    }
                else:
                    raise Exception("No data in Global Quote")

                if time_query:
                    period = {"day": 1, "week": 7, "month": 30, "year": 365}.get(time_query.split()[1], 30)
                    url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol={symbol}&apikey={api_key}"
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    if "Time Series (Daily)" in data:
                        date = (datetime.now() - timedelta(days=period)).strftime("%Y-%m-%d")
                        if date in data["Time Series (Daily)"]:
                            market_data[company]["historical_price"] = float(data["Time Series (Daily)"][date]["4. close"])

                url = f"https://www.alphavantage.co/query?function=OVERVIEW&symbol={symbol}&apikey={api_key}"
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                if data:
                    market_data[company].update({
                        "pe_ratio": float(data.get("PERatio", 0)) if data.get("PERatio") != "None" else None,
                        "beta": float(data.get("Beta", 0)) if data.get("Beta") != "None" else None,
                        "volatility": float(data.get("Volatility", 0)) if data.get("Volatility") else None
                    })

                alpha_vantage_success = True
                break
            except Exception as e:
                print(f"API_Agent Error for {company} (Attempt {attempt+1}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                break

        if not alpha_vantage_success:
            try:
                ticker = company
                yf_ticker = yf.Ticker(ticker)
                info = yf_ticker.info
                history = yf_ticker.history(period="1d")

                if not history.empty:
                    current_price = float(history["Close"].iloc[-1])
                    # Convert KRW to USD for .KS tickers
                    if ticker.endswith(".KS"):
                        current_price *= krw_to_usd
                    market_data[company] = {
                        "current_price": current_price,
                        "change_percent": f"{(history['Close'].iloc[-1] - history['Open'].iloc[-1]) / history['Open'].iloc[-1] * 100:.2f}%",
                        "timestamp": datetime.now().strftime("%Y-%m-%d")
                    }
                else:
                    raise Exception("No price data from yfinance")

                market_data[company].update({
                    "pe_ratio": float(info.get("trailingPE", 0)) if info.get("trailingPE") else None,
                    "beta": float(info.get("beta", 0)) if info.get("beta") else None,
                    "volatility": float(yf_ticker.history(period="1y")["Close"].pct_change().std() * (252 ** 0.5)) if not yf_ticker.history(period="1y").empty else None
                })

                if time_query:
                    period = {"day": "1d", "week": "5d", "month": "1mo", "year": "1y"}.get(time_query.split()[1], "1mo")
                    history = yf_ticker.history(period=period)
                    if not history.empty:
                        historical_price = float(history["Close"].iloc[0])
                        if ticker.endswith(".KS"):
                            historical_price *= krw_to_usd
                        market_data[company]["historical_price"] = historical_price

                print(f"API_Agent yfinance Success for {company}: {market_data[company]}")
            except Exception as e:
                print(f"API_Agent yfinance Error for {company}: {e}")
                market_data[company] = {"error": str(e)}

    os.makedirs("data", exist_ok=True)
    print(f"API_Agent Output: market_data={market_data}")
    return {"market_data": market_data}