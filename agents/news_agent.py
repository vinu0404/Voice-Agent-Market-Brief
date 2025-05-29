import json
import requests
from typing import Dict, Any, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
load_dotenv() 
def news_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetches news articles for companies using NewsAPI.
    Input: State with 'companies'.
    Output: Update State with 'news_data': Dict[str, List[Dict]].
    """
    companies = state["companies"]
    print(f"News_Agent Input: companies={companies}")

    with open("config.json", "r") as f:
        config = json.load(f)
    api_key = config["api_keys"]["news_api"]




    news_data = {}
    for company in companies:
        try:
            url = f"https://newsapi.org/v2/everything?q={company}&apiKey={api_key}&from={(datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')}&sortBy=relevancy"
            response = requests.get(url)
            data = response.json()
            if data.get("status") == "ok":
                news_data[company] = [
                    {"title": article["title"], "content": article.get("description", ""), "url": article["url"]}
                    for article in data.get("articles", [])[:5]
                ]
            else:
                print(f"News_Agent Error for {company}: {data.get('message')}")
                news_data[company] = []
        except Exception as e:
            print(f"News_Agent Error for {company}: {e}")
            news_data[company] = []

    print(f"News_Agent Output: news_data={news_data}")
    return {"news_data": news_data}