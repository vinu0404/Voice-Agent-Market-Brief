from typing import Dict, Any, List
import json
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv() 

def retriever_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Indexes news data and retrieves relevant documents based on query.
    Input: State with 'news_data', 'transcript'.
    Output: Update State with 'retrieved_docs': List[Dict].
    """
    news_data = state["news_data"]
    transcript = state["transcript"]
    print(f"Retriever_Agent Input: news_data={news_data}, transcript={transcript}")

    if not news_data:
        print("Retriever_Agent: No news data to process")
        return {"retrieved_docs": []}

    try:
        model = SentenceTransformer("all-MiniLM-L6-v2")
        all_docs = []
        doc_metadata = []

        # Flatten news data
        for company, articles in news_data.items():
            for article in articles:
                content = article.get("content", "")
                if content:
                    all_docs.append(content)
                    doc_metadata.append({"company": company, "title": article["title"], "url": article["url"]})

        if not all_docs:
            print("Retriever_Agent: No texts to index")
            return {"retrieved_docs": []}

        # Encode documents and query
        doc_embeddings = model.encode(all_docs)
        query_embedding = model.encode([transcript])[0]

        # Compute similarity
        similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
        top_k = min(3, len(all_docs))
        top_indices = np.argsort(similarities)[-top_k:][::-1]

        # Retrieve top documents
        retrieved_docs = [
            {"content": all_docs[i], "metadata": doc_metadata[i], "score": float(similarities[i])}
            for i in top_indices
        ]

        print(f"Retriever_Agent Output: retrieved_docs={retrieved_docs}")
        return {"retrieved_docs": retrieved_docs}
    except Exception as e:
        print(f"Retriever_Agent Error: {e}")
        return {"retrieved_docs": []}