import streamlit as st
import asyncio
import os
import logging
import base64
from orchestrator.workflow import workflow
from streamlit_mic_recorder import mic_recorder
from datetime import datetime
import os
from dotenv import load_dotenv
load_dotenv() 

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

# Custom CSS for design
st.markdown("""
<style>
    /* Import Roboto font */
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700&display=swap');

    /* Dark theme with sleek styling */
    .stApp {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        color: #e2e8f0;
        font-family: 'Roboto', sans-serif;
    }
    h1 {
        font-family: 'Roboto', sans-serif;
        color: #60a5fa;
        font-size: 28px;
        font-weight: 700;
        text-align: center;
        margin-bottom: 20px;
        padding-top: 20px;
    }
    /* Chat container */
    .chat-container {
        max-height: 300px;
        overflow-y: auto;
        padding: 10px;
        border-radius: 12px;
        background-color: rgba(30, 41, 59, 0.8);
        margin: 80px auto 20px auto;
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.3);
        max-width: 800px;
    }
    .user-message, .bot-message {
        padding: 8px 15px;
        margin: 5px 0;
        border-radius: 12px;
        font-size: 14px;
        line-height: 1.4;
        max-width: 80%;
        animation: fadeIn 0.5s ease-in;
    }
    .user-message {
        background-color: #2563eb;
        color: #ffffff;
        margin-left: auto;
        border-bottom-right: none;
    }
    .bot-message {
        background-color: #334155;
        color: #e2e8f0;
        margin-right: auto;
        border-bottom-left: none;
    }
    /* Animation */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    /* Recorder button */
    .recorder {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        background: transparent;
        padding: 5px;
        border: none;
        z-index: 10;
    }
    .recorder button {
        background-color: #2563eb;
        color: #ffffff;
        border-radius: 50%;
        width: 100px;
        height: 100px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: none;
        box-shadow: 0 0 12px rgba(37, 99, 235, 0.6);
        transition: transform 0.2s;
        font-family: 'Roboto', sans-serif;
        font-size: 18px;
        font-weight: 700;
        text-align: center;
    }
    .recorder button:hover {
        transform: scale(1.15);
    }
    .recorder.disabled button {
        pointer-events: none;
        opacity: 0.5;
        cursor: not-allowed;
    }
    /* Spinner */
    .stSpinner > div {
        color: #60a5fa;
        border-color: #60a5fa transparent transparent transparent;
    }
    /* Error and success messages */
    .stAlert {
        font-family: 'Roboto', sans-serif;
        border-radius: 8px;
        font-size: 14px;
    }
    .success {
        color: #16a34a;
        font-family: 'Roboto', sans-serif;
        font-size: 14px;
        text-align: center;
        max-width: 800px;
        margin: 10px auto;
    }
</style>
""", unsafe_allow_html=True)

async def main():
    st.title("Market Brief")

    # Initialize session state
    if "conversation" not in st.session_state:
        st.session_state.conversation = []
    if "audio_trigger" not in st.session_state:
        st.session_state.audio_trigger = 0
    if "is_processing" not in st.session_state:
        st.session_state.is_processing = False

    # Workflow setup
    graph = workflow()
    state = {
        "transcript": "",
        "companies": [],
        "intents": [],
        "market_data": {},
        "news_data": {},
        "retrieved_docs": [],
        "portfolio_data": {},
        "analysis": {},
        "narrative": "",
        "audio_input": "",
        "audio_output": "",
        "time_query": None,
        "error": None,
        "node": ""
    }

    # Recorder
    recorder_class = "recorder disabled" if st.session_state.is_processing else "recorder"
    st.markdown(f"<div class='{recorder_class}'>", unsafe_allow_html=True)
    audio = mic_recorder(start_prompt="Record", stop_prompt="Stop", key="recorder")
    st.markdown("</div>", unsafe_allow_html=True)

    if audio and not st.session_state.is_processing:
        st.session_state.is_processing = True
        with st.spinner(""):
            audio_input = "data/input.wav"
            os.makedirs("data", exist_ok=True)
            try:
                with open(audio_input, "wb") as f:
                    f.write(audio["bytes"])
                state["audio_input"] = audio_input
                logger.info(f"Running workflow with state: {state}")
                result = graph.invoke(state)
                state.update(result)
                logger.info(f"Workflow result: {state}")

                # Update conversation history
                if state["transcript"]:
                    st.session_state.conversation.append({
                        "role": "user",
                        "content": state["transcript"],
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                if state["narrative"]:
                    st.session_state.conversation.append({
                        "role": "bot",
                        "content": state["narrative"],
                        "timestamp": datetime.now().strftime("%H:%M:%S")
                    })
                # Trigger audio playback
                if state["audio_output"]:
                    st.session_state.audio_trigger += 1
            except Exception as e:
                logger.error(f"Workflow error: {str(e)}")
                st.error(f"Error: {str(e)}")
                state["error"] = str(e)
            finally:
                st.session_state.is_processing = False

    # Auto-play audio
    if state["audio_output"] and os.path.exists(state["audio_output"]):
        try:
            with open(state["audio_output"], "rb") as f:
                audio_bytes = f.read()
            audio_b64 = base64.b64encode(audio_bytes).decode()
            st.markdown(f"""
                <audio autoplay hidden>
                    <source src="data:audio/mp3;base64,{audio_b64}" type="audio/mp3">
                </audio>
                <p class='success'>Audio playing</p>
            """, unsafe_allow_html=True)
            # Reset processing state
            st.session_state.is_processing = False
        except Exception as e:
            st.error(f"Audio playback error: {str(e)}")
    elif state["audio_output"]:
        st.error(f"Audio file not found: {state['audio_output']}")

    # Display conversation history
    if st.session_state.conversation:
        st.markdown("<div class='chat-container'>", unsafe_allow_html=True)
        for msg in reversed(st.session_state.conversation):
            if msg["role"] == "user":
                st.markdown(f"<div class='user-message'>👤 {msg['content']}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='bot-message'>🤖 {msg['content']}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # Display errors
    if state["error"]:
        st.error(f"Error: {state['error']}")

if __name__ == "__main__":
    # For Render deployment, bind to PORT environment variable
    port = int(os.getenv("PORT", 8501))
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())