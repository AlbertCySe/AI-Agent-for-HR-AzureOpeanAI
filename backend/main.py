import os
from dotenv import load_dotenv
from openai import AzureOpenAI
from fastapi import FastAPI, UploadFile, File, HTTPException, status, Form
import json
import traceback

# Import Pydantic models using relative import (from .models)
from .models import (
    Message, FollowUpQuestionRequest, IndividualEvaluation, EvaluationResponse,
    FullAnalysisResponse, AiDetectionData, AiDetectionResponse
)

# Import core logic functions from service.py using relative import (from .service)
from .service import (
    score_resume_against_jd,
    answer_follow_up_question,
    generate_interview_questions,
    analyze_interview_questions,
    evaluate_candidate_responses_holistically,
    detect_ai_resume
)

# Import PDF extraction helpers from modules/pdf_extractor.py using relative import (from .modules.pdf_extractor)
from .modules.pdf_extractor import (
    extract_text_from_resume_file,
    extract_text_from_jd_file,
    extract_text_from_conversation_file,
    extract_text_from_pdf_bytes_for_detection  # This is now directly imported
)

# --- Load .env and Initialize Azure OpenAI Client ---
dotenv_path = os.path.join(os.path.dirname(__file__), "credit.env")
if not load_dotenv(dotenv_path):
    raise ValueError(
        f"Error: '{dotenv_path}' file not found or could not be loaded. "
        "Please ensure '.env' is in the same directory as this script and contains your Azure OpenAI credentials."
    )

AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME")

if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_KEY, AZURE_DEPLOYMENT_NAME, AZURE_OPENAI_API_VERSION]):
    raise ValueError(
        "Azure OpenAI credentials missing. Please ensure 'AZURE_OPENAI_KEY', "
        "'AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_VERSION', and 'AZURE_DEPLOYMENT_NAME' are correctly "
        "specified and not empty in your '.env' file."
    )

azure_openai_client = None
try:
    azure_openai_client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_KEY,
        api_version=AZURE_OPENAI_API_VERSION,
    )
    print("Azure OpenAI client initialized successfully in main.py.")
except Exception as e:
    print(f"Error initializing AzureOpenAI client: {e}")
    raise RuntimeError(f"Error initializing AzureOpenAI client: {e}") from e

# --- FastAPI Application Instance ---
app = FastAPI(
    title="Unified AI Resume & Interview Analyzer",
    description="Unified API for scoring resumes, generating interview questions, analyzing interview transcripts, evaluating responses, answering follow-up questions, and detecting AI-generated content using Azure OpenAI.",
    version="1.2.0"
)


# --- FastAPI Endpoints ---

@app.post("/full-analysis/", response_model=FullAnalysisResponse,
          summary="Perform full resume analysis and generate interview questions",
          description="Combines resume scoring against JD and interview question generation into one API call.")
async def api_full_analysis(
        resume_file: UploadFile = File(..., description="The candidate's resume file (.txt or .pdf)"),
        jd_file: UploadFile = File(..., description="The job description file (.txt)")
):
    """
    Performs a full analysis: scores the resume against the JD and generates interview questions.
    Returns both results in a single response, including the extracted text for frontend use.
    """
    resume_text = await extract_text_from_resume_file(resume_file)
    jd_text = await extract_text_from_jd_file(jd_file)

    scoring_result = score_resume_against_jd(azure_openai_client, AZURE_DEPLOYMENT_NAME, resume_text, jd_text)
    questions_text = generate_interview_questions(azure_openai_client, AZURE_DEPLOYMENT_NAME, resume_text, jd_text)

    return {
        "score": scoring_result,
        "interview_questions": questions_text,
        "extracted_resume_text": resume_text,
        "extracted_jd_text": jd_text
    }


@app.post("/result/analyze-interview-questions/",
          summary="Analyze interview question coverage",
          description="Determines which AI-generated questions were covered in a transcript and identifies interviewer's own questions.")
async def api_analyze_interview_questions(
        ai_generated_questions_file: UploadFile = File(...,
                                                       description="A .txt file containing the AI-generated interview questions."),
        conversation_transcript_file: UploadFile = File(...,
                                                        description="A .txt file containing the interview conversation transcript.")
):
    """
    Analyzes an interview transcript to identify which AI-generated questions were covered
    and which unique questions the interviewer asked.
    """
    ai_generated_questions_text = await extract_text_from_conversation_file(ai_generated_questions_file)
    conversation_transcript = await extract_text_from_conversation_file(conversation_transcript_file)

    result = analyze_interview_questions(azure_openai_client, AZURE_DEPLOYMENT_NAME, ai_generated_questions_text,
                                         conversation_transcript)
    return result


@app.post("/evaluate-candidate-responses/", response_model=EvaluationResponse,
          summary="Evaluate candidate responses holistically",
          description="Provides detailed evaluation of candidate responses to interview questions and an overall performance summary.")
async def api_evaluate_candidate_responses(
        all_questions_asked_json: str = Form(...,
                                             description="A JSON string representing a list of all questions asked in the interview, e.g., '[\"Question 1\", \"Question 2\"]'"),
        conversation_transcript_file: UploadFile = File(...,
                                                        description="A .txt file containing the interview conversation transcript."),
        jd_file: UploadFile = File(..., description="The job description file (.txt) used for context."),
        resume_file: UploadFile = File(..., description="The candidate's resume file (.txt or .pdf) used for context.")
):
    """
    Evaluates the candidate's responses to all questions asked in the interview transcript,
    and provides an overall interview performance score and summary.
    Requires the list of *all* questions asked (covered generated + interviewer's own).
    """
    try:
        all_questions_asked = json.loads(all_questions_asked_json)
        if not isinstance(all_questions_asked, list) or not all(isinstance(q, str) for q in all_questions_asked):
            raise ValueError("all_questions_asked must be a list of strings.")
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format for 'all_questions_asked'."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    conversation_transcript = await extract_text_from_conversation_file(conversation_transcript_file)
    jd_text = await extract_text_from_jd_file(jd_file)
    resume_text = await extract_text_from_resume_file(resume_file)

    result = evaluate_candidate_responses_holistically(
        azure_openai_client, AZURE_DEPLOYMENT_NAME,
        all_questions_asked,
        conversation_transcript,
        jd_text,
        resume_text
    )
    return result


@app.post("/answer-follow-up-question/",
          summary="Get AI answer for follow-up questions",
          description="Provides an AI answer based on the full job description, resume, and previous conversation history.")
async def api_answer_follow_up_question(request: FollowUpQuestionRequest):
    """
    Answers a follow-up question based on a conversation history.
    Provide a list of messages in the format: `[{"role": "user", "content": "..."}]`.
    """
    response_content = answer_follow_up_question(azure_openai_client, AZURE_DEPLOYMENT_NAME, request.messages)
    return {"answer": response_content}


@app.post(
    '/resume/detect_ai',
    response_model=AiDetectionResponse,
    summary="Detect if a resume is AI-generated or human-written",
    description="Accepts a resume file (PDF or TXT) and determines if it's AI-generated or human-written, with optional explanation."
)
async def detect_ai_resume_endpoint(
        resume_file: UploadFile = File(..., description="The resume file to analyze (PDF or TXT)."),
        include_explanation: bool = Form(True, description="Set to true to include a detailed explanation.")
):
    """
    API endpoint to analyze a resume and determine if it's AI-generated or human-written.
    Accepts a PDF or TXT file upload and an optional boolean for explanation.
    """
    if azure_openai_client is None:
        raise HTTPException(status_code=500,
                            detail="Azure OpenAI client not initialized. Check server logs for details.")

    resume_text = ""
    try:
        if resume_file.content_type == "application/pdf":
            pdf_content = await resume_file.read()
            # CORRECTED: Call the function directly as it's imported via relative path
            resume_text = extract_text_from_pdf_bytes_for_detection(pdf_content)
        elif resume_file.content_type == "text/plain":
            resume_text = (await resume_file.read()).decode('utf-8')
        else:
            raise HTTPException(status_code=400,
                                detail="Unsupported resume file type. Only PDF and TXT are allowed for AI detection.")

        result = detect_ai_resume(azure_openai_client, AZURE_DEPLOYMENT_NAME, resume_text, include_explanation)
        return result

    except Exception as e:
        print(traceback.format_exc())
        print(f"An unexpected error occurred during AI detection endpoint processing: {e}")
        raise HTTPException(status_code=500,
                            detail=f"An unexpected error occurred during AI detection processing or AI analysis: {str(e)}")


@app.get("/health", summary="Health Check", description="Checks if the API is running and responsive.")
async def health_check():
    return {"status": "ok", "message": "Unified AI Resume Analyzer API is up and running!"}



