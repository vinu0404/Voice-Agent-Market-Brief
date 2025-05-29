from typing import Dict, Any, List
import json
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()  # this loads variables from .env into os.environ


def analysis_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyzes market and portfolio data based on intents.
    Input: State with 'market_data', 'portfolio_data', 'intents', 'companies'.
    Output: Updates State with 'analysis': Dict with portfolio_metrics, comparisons, recommendations.
    """
    market_data = state["market_data"]
    portfolio_data = state["portfolio_data"]
    intents = state["intents"]
    companies = state["companies"]
    transcript = state.get("transcript", "").lower()
    print(f"Analysis_Agent Input: market_data={market_data}, portfolio_data={portfolio_data}, intents={intents}, companies={companies}")

    analysis = {"portfolio_metrics": {}, "comparisons": {}, "recommendations": []}

    if "portfolio" in intents and portfolio_data.get("holdings"):
        holdings = portfolio_data["holdings"]
        total_value = 0
        portfolio_metrics = {"holdings": {}, "total_value": 0, "portfolio_pe": None, "portfolio_beta": None}
        pe_ratios = []
        betas = []

        # Calculate values
        for ticker, shares in holdings.items():
            ticker_data = market_data.get(ticker, {"current_price": 0, "pe_ratio": None, "beta": None, "volatility": None, "error": "No data"})
            price = ticker_data.get("current_price", 0)
            if price == 0:
                price = 100.0
                ticker_data["error"] = ticker_data.get("error", "Using default price due to missing data")
            value = shares * price
            total_value += value
            portfolio_metrics["holdings"][ticker] = {
                "shares": shares,
                "value": value,
                "pe_ratio": ticker_data.get("pe_ratio"),
                "beta": ticker_data.get("beta"),
                "volatility": ticker_data.get("volatility")
            }
            if ticker_data.get("pe_ratio"):
                pe_ratios.append(ticker_data["pe_ratio"])
            if ticker_data.get("beta"):
                betas.append(ticker_data["beta"])

        # Calculate allocations
        for ticker in portfolio_metrics["holdings"]:
            value = portfolio_metrics["holdings"][ticker]["value"]
            allocation = f"{(value / total_value * 100):.2f}%" if total_value > 0 else "0.00%"
            portfolio_metrics["holdings"][ticker]["allocation"] = allocation

        portfolio_metrics["total_value"] = total_value
        portfolio_metrics["portfolio_pe"] = float(np.mean(pe_ratios)) if pe_ratios else None
        portfolio_metrics["portfolio_beta"] = float(np.mean(betas)) if betas else None
        analysis["portfolio_metrics"] = portfolio_metrics

        if not any(ticker in market_data and "current_price" in market_data[ticker] for ticker in holdings):
            print("Analysis_Agent Warning: No valid market data for portfolio valuation")

    if "compare" in intents and companies:
        for company in companies:
            ticker_data = market_data.get(company, {"current_price": 0, "pe_ratio": None, "beta": None})
            analysis["comparisons"][company] = {
                "pe_ratio": ticker_data.get("pe_ratio"),
                "beta": ticker_data.get("beta"),
                "current_price": ticker_data.get("current_price", 100.0)
            }

    if "recommend" in intents:
        if "sell" in transcript:
            for ticker, details in analysis["portfolio_metrics"].get("holdings", {}).items():
                pe = details.get("pe_ratio")
                volatility = details.get("volatility")
                beta = details.get("beta")
                if (pe and pe > 30) or (volatility and volatility > 0.5) or (beta and beta > 1.5):
                    analysis["recommendations"].append({
                        "ticker": ticker,
                        "action": "sell",
                        "reason": f"High PE ({pe:.2f}), volatility ({volatility:.2f}), or beta ({beta:.2f})"
                    })
            if not analysis["recommendations"]:
                analysis["recommendations"].append({
                    "ticker": None,
                    "action": "sell",
                    "reason": "No clear candidates for selling based on current performance."
                })
        elif "buy" in transcript:
            analysis["recommendations"].append({
                "ticker": None,
                "action": "buy",
                "reason": "Selecting stocks to buy is complex due to the vast market. Consult a financial advisor."
            })

    print(f"Analysis_Agent Output: {analysis}")
    return {"analysis": analysis}
