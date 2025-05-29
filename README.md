# Market Brief - Voice-Enabled Finance Assistant

**Market Brief** is a voice-enabled financial assistant built with Streamlit, LangGraph, and various APIs to provide real-time market insights, portfolio analysis, and recommendations through a sleek, voice-driven interface.

## Overview

Market Brief allows users to interact via voice commands to query stock prices, analyze portfolios, compare companies, or get recommendations. It leverages Speech-to-Text (STT) and Text-to-Speech (TTS) for a seamless experience, with a dark-themed UI featuring a centered "Record" button for voice input.

## Features

- **Voice Interaction**: Record queries using a centered "Record" button, with auto-playing audio responses.
- **Real-Time Data**: Fetches live market data and news using Alpha Vantage and NewsAPI.
- **Portfolio Analysis**: Analyzes user portfolios from `data/portfolio.json`.
- **Sleek UI**: Dark gradient theme, compact chat, Roboto font, no white rectangle around the button.
- **Deployment Ready**: Deployed on Render with environment variables for secure API key management.

## Agents

Each agent in the pipeline handles a specific task:

- **Voice Agent (`voice_agent.py`)**: Manages STT (AssemblyAI) and TTS (AWS Polly) for voice input/output.
- **Intent Classifier (`workflow.py`)**: Identifies user intents (price, portfolio, compare, recommend) using LLM and keyword matching.
- **API Agent (`api_agent.py`)**: Fetches market data for specified companies using Alpha Vantage API.
- **News Agent (`news_agent.py`)**: Retrieves relevant news articles using NewsAPI for price trend queries.
- **Retriever Agent (`retriever_agent.py`)**: Combines market and news data for analysis.
- **Analysis Agent (`analysis_agent.py`)**: Performs financial analysis (portfolio metrics, comparisons, recommendations).
- **Language Agent (`language_agent.py`)**: Generates humanized narratives using AWS Bedrock LLM.

## Pipeline Process

The application uses a LangGraph workflow (`orchestrator/workflow.py`) to process user queries in the following steps:

1. **Voice Input (STT)**:
   - User clicks the "Record" button (centered in the UI).
   - `voice_agent` (STT node) uses AssemblyAI to transcribe the audio (`data/input.wav`) into text.

2. **Intent Classification**:
   - `intent_classifier` analyzes the transcript to identify intents (e.g., price, portfolio) and extracts companies and time queries using LLM and keyword matching.

3. **Portfolio Loading**:
   - `load_portfolio` loads user portfolio data from `data/portfolio.json`.

4. **Data Fetching**:
   - If the query involves trends ("why", "rising"), `news_agent` fetches news via NewsAPI.
   - Otherwise, `api_agent` fetches market data via Alpha Vantage.

5. **Data Retrieval**:
   - `retriever_agent` consolidates market and news data for analysis.

6. **Analysis**:
   - `analysis_agent` processes the data to compute portfolio metrics, comparisons, or recommendations based on the intent.

7. **Narrative Generation**:
   - `language_agent` uses AWS Bedrock LLM to generate a concise, humanized narrative (e.g., "Tesla’s stock is $800.50, up due to a new factory opening.").

8. **Voice Output (TTS)**:
   - `voice_agent` (TTS node) converts the narrative to audio (`data/output.mp3`) using AWS Polly.
   - The audio auto-plays in the UI with a "Audio playing" message.

9. **UI Update**:
   - The query and response are displayed in a compact chat (newest first) with user (blue) and bot (gray) bubbles.

## Directory Structure

```
project-root/
│
├── app.py                  # Main Streamlit app with UI and workflow integration
├── config.json             # Ticker mapping for companies
├── requirements.txt        # Dependencies for deployment
├── data/
│   └── portfolio.json      # User portfolio data
├── orchestrator/
│   └── workflow.py         # LangGraph workflow definition
├── agents/
│   ├── api_agent.py        # Fetches market data
│   ├── news_agent.py       # Fetches news articles
│   ├── retriever_agent.py  # Combines data for analysis
│   ├── analysis_agent.py   # Performs financial analysis
│   ├── language_agent.py   # Generates narratives
│   └── voice_agent.py      # Handles STT/TTS
└── .gitignore              # Ignores sensitive files
```

## Installation (Local)

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/your-username/finance-assistant.git
   cd finance-assistant
   ```

2. **Set Up Environment**:
   ```bash
   conda create -n market python=3.9
   conda activate market
   pip install -r requirements.txt
   ```

3. **Create `.env` File**:
   Create a `.env` file in the project root with your API keys:
   ```
   ASSEMBLYAI_API_KEY=your_assemblyai_key
   AWS_ACCESS_KEY_ID=your_aws_access_key
   AWS_SECRET_ACCESS_KEY=your_aws_secret_key
   ALPHA_VANTAGE_KEY=your_alpha_vantage_key
   NEWS_API_KEY=your_newsapi_key
   LLM_MODEL_ID=amazon.nova-micro-v1:0
   LLM_REGION=us-east-1
   ```

4. **Run the App**:
   ```bash
   streamlit run app.py
   ```

5. **Test Queries**:
   - Open `http://localhost:8501`.
   - Click "Record" and say: "Current Tesla stock price."
   - Expect: Chat shows query/response, audio auto-plays.

## Deployment on Render

1. **Push to GitHub**:
   - Create a GitHub repository and push your code.

2. **Set Up Render**:
   - Create a Web Service on [Render](https://render.com).
   - Configure:
     - **Environment**: Python
     - **Build Command**: `pip install -r requirements.txt`
     - **Start Command**: `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`
   - Add environment variables (see `.env` template above).

3. **Deploy**:
   - Deploy the app and access it via the provided Render URL.

## Demo Video

Watch a demo of Market Brief in action:

[Demo Video](https://drive.google.com/file/d/1pKWnXAqMctbOpB5EzRRp8Cf53Mq6kmlr/view?usp=sharing)

## Live Link

Try Market Brief live:

[Live Demo](https://voice-agent-market-brief.onrender.com)

## Dependencies

- **Streamlit**: 1.34.0 (UI framework)
- **streamlit-mic-recorder**: 0.0.8 (Voice recording)
- **boto3**: 1.34.113 (AWS Polly for TTS)
- **langgraph**: 0.2.5 (Workflow orchestration)
- **langchain-aws**: 0.1.17 (LLM integration)
- **requests**: 2.32.3 (API calls)
