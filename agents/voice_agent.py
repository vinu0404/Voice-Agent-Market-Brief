import logging
import os
import json
import requests
import time
import traceback
import boto3
import re
from botocore.exceptions import ClientError, ParamValidationError
from typing import Dict, Any
import os
from dotenv import load_dotenv
load_dotenv() 

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(name)s - %(message)s")
logger = logging.getLogger(__name__)

def process_stt(audio_input: str, assemblyai_api_key: str) -> Dict[str, str]:
    """Handles STT using AssemblyAI."""
    try:
        headers = {"authorization": assemblyai_api_key}
        with open(audio_input, "rb") as f:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=f,
                timeout=30
            )
        upload_response.raise_for_status()
        audio_url = upload_response.json()["upload_url"]

        transcribe_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers,
            json={"audio_url": audio_url, "language_code": "en_us"},
            timeout=30
        )
        transcribe_response.raise_for_status()
        transcript_id = transcribe_response.json()["id"]

        while True:
            status_response = requests.get(
                f"https://api.assemblyai.com/v2/transcript/{transcript_id}",
                headers=headers,
                timeout=10
            )
            status_response.raise_for_status()
            status = status_response.json()
            if status["status"] in ["completed", "error"]:
                break
            time.sleep(1)

        if status["status"] == "completed":
            transcript = status["text"] or ""
        else:
            raise Exception(f"AssemblyAI transcription failed: {status.get('error', 'Unknown error')}")

        print(f"Voice_Agent STT Output: {transcript}")
        logger.info(f"STT Success: {transcript}")
        return {"transcript": transcript}
    except Exception as e:
        error_msg = f"STT Error: {str(e)}\n{traceback.format_exc()}"
        print(f"Voice_Agent Error: {error_msg}")
        logger.error(error_msg)
        return {"error": error_msg}

def process_tts(narrative: str, aws_access_key_id: str, aws_secret_access_key: str, region_name: str) -> Dict[str, str]:
    """Handle TTS using AWS Polly."""
    logger.info(f"Voice_Agent TTS Input: narrative_length={len(narrative)}")
    print(f"Voice_Agent TTS Input: narrative={len(narrative)}...")

    try:
        # Validate narrative
        logger.info(f"Original narrative length: {len(narrative)} characters")
        if len(narrative) == 0:
            error_msg = "Empty narrative provided"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}
        if len(narrative) > 3000:  # Polly character limit
            error_msg = f"Narrative exceeds 3000 characters: {len(narrative)}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Sanitize narrative
        sanitized_narrative = re.sub(r'[^\w\s.,!?;:%$-]', '', narrative)
        logger.info(f"Sanitized narrative length: {len(sanitized_narrative)} characters")
        if not sanitized_narrative:
            error_msg = "Sanitized narrative is empty"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Validate AWS credentials
        logger.info("Validating AWS credentials")
        try:
            session = boto3.Session(
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=region_name
            )
            sts = session.client("sts")
            identity = sts.get_caller_identity()
            logger.info(f"AWS credentials validated: Account {identity['Account']}")
        except ClientError as e:
            error_msg = f"AWS credential validation failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Check region
        available_regions = ["us-east-1", "us-west-2", "eu-west-1"]
        if region_name not in available_regions:
            error_msg = f"Polly not supported in region {region_name}. Use {available_regions}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Pre-check file system
        audio_output = "data/output.mp3"
        os.makedirs("data", exist_ok=True)
        if not os.access("data", os.W_OK):
            error_msg = "No write permission for data directory"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        import shutil
        _, _, free_space = shutil.disk_usage(".")
        if free_space < 1024 * 1024:  # Less than 1MB
            error_msg = "Insufficient disk space in data directory"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Clean up existing file
        try:
            if os.path.exists(audio_output):
                os.remove(audio_output)
                logger.info(f"Removed existing {audio_output}")
        except Exception as e:
            error_msg = f"Failed to remove existing {audio_output}: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Call Polly
        logger.info("Calling AWS Polly for TTS")
        try:
            polly = session.client("polly")
            response = polly.synthesize_speech(
                Text=sanitized_narrative,
                OutputFormat="mp3",
                VoiceId="Joanna"
            )
            logger.info(f"Polly Response: {response.get('ResponseMetadata')}")
        except (ClientError, ParamValidationError) as e:
            error_msg = f"Polly TTS failed: {e.response['Error']['Code']} - {e.response['Error']['Message']}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

        # Write audio file
        logger.info(f"Writing audio to {audio_output}")
        try:
            with open(audio_output, "wb") as f:
                f.write(response["AudioStream"].read())
            if not os.path.exists(audio_output):
                error_msg = "Failed to write audio output file"
                logger.error(error_msg)
                return {"error": error_msg, "audio_output": ""}
            file_size = os.path.getsize(audio_output)
            print(f"Voice_Agent TTS Output: {audio_output} (File exists: {os.path.exists(audio_output)}, Size: {file_size} bytes)")
            logger.info(f"TTS Success: {audio_output} (Size: {file_size} bytes)")
            return {"audio_output": audio_output}
        except Exception as e:
            error_msg = f"File write failed: {str(e)}\n{traceback.format_exc()}"
            logger.error(error_msg)
            return {"error": error_msg, "audio_output": ""}

    except Exception as e:
        error_msg = f"TTS Error: {str(e)}\n{traceback.format_exc()}"
        print(f"Voice_Agent Error: {error_msg}")
        logger.error(error_msg)
        return {"error": error_msg, "audio_output": ""}

def voice_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handles STT or TTS based on node context.
    Input: State with 'audio_input' (STT), 'narrative' (TTS), and 'node' (context).
    Output: Updates State with 'transcript' or 'audio_output'.
    """
    audio_input = state.get("audio_input", "")
    narrative = state.get("narrative", "").strip()
    transcript = state.get("transcript", "")
    node = state.get("node", "")
    logger.info(f"Starting voice agent: node={node}, audio_input={audio_input}, narrative_length={len(narrative)}, transcript={transcript[:500]}")
    print(f"Voice_Agent Input: node={node}, audio_input={audio_input}, narrative={narrative[:50]}..., transcript={transcript[:100]}")

    try:
        assemblyai_api_key = os.getenv("ASSEMBLYAI_API_KEY")
        aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
        region_name = os.getenv("LLM_REGION")

        if not assemblyai_api_key or not aws_access_key_id or not aws_secret_access_key or not region_name:
            raise ValueError("Missing required environment variables: ASSEMBLYAI_API_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, or LLM_REGION")
    except Exception as e:
        error_msg = f"Environment variable load error: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return {"error": error_msg, "audio_output": ""}

    # Prioritize TTS for voice_agent_tts node
    if node == "voice_agent_tts" and narrative:
        return process_tts(narrative, aws_access_key_id, aws_secret_access_key, region_name)

    # Handle STT for voice_agent_stt node or if audio_input is present
    if audio_input and os.path.exists(audio_input):
        return process_stt(audio_input, assemblyai_api_key)

    # Fallback for invalid input
    error_msg = "No valid audio input or narrative provided for node: " + node
    logger.error(error_msg)
    return {"error": error_msg, "audio_output": ""}