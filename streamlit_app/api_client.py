import requests
import json
import io
from typing import List, Dict, Any

FASTAPI_BASE_URL = "http://127.0.0.1:8000"

def _handle_api_response(response: requests.Response, endpoint_name: str):
    """Helper to handle common API response patterns and errors."""
    try:
        response.raise_for_status() # Raises HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.Timeout:
        raise requests.exceptions.Timeout(f"The {endpoint_name} request timed out. The server took too long to respond.")
    except requests.exceptions.ConnectionError:
        raise requests.exceptions.ConnectionError(f"Failed to connect to the FastAPI server for {endpoint_name}.")
    except requests.exceptions.HTTPError as e:
        status_code = response.status_code
        detail = response.text
        try:
            detail = response.json().get("detail", detail)
        except json.JSONDecodeError:
            pass # Keep raw text if not JSON
        raise requests.exceptions.HTTPError(f"HTTP error {status_code} occurred during {endpoint_name}: {detail}", response=response)
    except json.JSONDecodeError:
        raise json.JSONDecodeError(f"Received an invalid JSON response from the {endpoint_name} API. Raw response: {response.text}", doc=response.text, pos=0)


def call_detect_ai_resume(resume_file_obj: io.BytesIO, resume_filename: str, resume_file_type: str) -> Dict[str, Any]:
    """Calls the backend API to detect AI-generated content in a resume."""
    files = {
        "resume_file": (resume_filename, resume_file_obj.getvalue(), resume_file_type)
    }
    data = {"include_explanation": "true"} # Always request detailed explanation
    response = requests.post(f"{FASTAPI_BASE_URL}/resume/detect_ai", files=files, data=data, timeout=60)
    return _handle_api_response(response, "AI detection")

def call_full_analysis(jd_file_obj: io.BytesIO, jd_filename: str, jd_file_type: str,
                       resume_file_obj: io.BytesIO, resume_filename: str, resume_file_type: str) -> Dict[str, Any]:
    """Calls the backend API for full resume analysis against JD and question generation."""
    files = {
        "jd_file": (jd_filename, jd_file_obj.getvalue(), jd_file_type),
        "resume_file": (resume_filename, resume_file_obj.getvalue(), resume_file_type)
    }
    response = requests.post(f"{FASTAPI_BASE_URL}/full-analysis/", files=files, timeout=120)
    return _handle_api_response(response, "full analysis")

def call_analyze_interview_coverage(ai_gen_q_text: str, conversation_file_obj: io.BytesIO, conversation_filename: str, conversation_file_type: str) -> Dict[str, Any]:
    """Calls the backend API to analyze interview question coverage."""
    ai_gen_q_bytes = io.BytesIO(ai_gen_q_text.encode('utf-8'))
    ai_gen_q_file_obj = ("ai_generated_questions.txt", ai_gen_q_bytes, "text/plain")

    files = {
        "ai_generated_questions_file": ai_gen_q_file_obj,
        "conversation_transcript_file": (conversation_filename, conversation_file_obj.getvalue(), conversation_file_type)
    }
    response = requests.post(f"{FASTAPI_BASE_URL}/result/analyze-interview-questions/", files=files, timeout=90)
    return _handle_api_response(response, "interview coverage analysis")

def call_evaluate_responses(all_questions_asked: List[str], conversation_file_obj: io.BytesIO, conversation_filename: str, conversation_file_type: str,
                            jd_file_obj: io.BytesIO, jd_filename: str, jd_file_type: str,
                            resume_file_obj: io.BytesIO, resume_filename: str, resume_file_type: str) -> Dict[str, Any]:
    """Calls the backend API to evaluate candidate responses holistically."""
    files = {
        "conversation_transcript_file": (conversation_filename, conversation_file_obj.getvalue(), conversation_file_type),
        "jd_file": (jd_filename, jd_file_obj.getvalue(), jd_file_type),
        "resume_file": (resume_filename, resume_file_obj.getvalue(), resume_file_type)
    }
    data = {
        "all_questions_asked_json": json.dumps(all_questions_asked)
    }
    response = requests.post(f"{FASTAPI_BASE_URL}/evaluate-candidate-responses/", files=files, data=data, timeout=180)
    return _handle_api_response(response, "candidate response evaluation")

def call_answer_follow_up(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """Calls the backend API to get an AI answer for a follow-up question."""
    qa_payload = {"messages": messages}
    response = requests.post(f"{FASTAPI_BASE_URL}/answer-follow-up-question/", json=qa_payload, timeout=90)
    return _handle_api_response(response, "interactive Q&A")
