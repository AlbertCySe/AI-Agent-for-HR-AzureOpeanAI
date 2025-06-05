import streamlit as st
import requests
import json
import io
import hashlib

# --- Configuration ---
FASTAPI_BASE_URL = "http://127.0.0.1:8000"  # Your FastAPI service URL

st.set_page_config(
    page_title="AI Resume & Interview Analyzer",
    layout="wide", # Use wide layout for more space
    initial_sidebar_state="expanded"
)

st.title("📄 AI Resume & Interview Analyzer")
st.markdown("Analyze resumes against job descriptions, get interview insights, and evaluate candidate responses.")

# --- Session State Initialization ---
# These variables store results and extracted texts across Streamlit reruns
if 'job_description_text' not in st.session_state:
    st.session_state.job_description_text = ""
if 'candidate_resume_text' not in st.session_state:
    st.session_state.candidate_resume_text = ""
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'jd_analysis_results' not in st.session_state:
    st.session_state.jd_analysis_results = None # Stores combined score and interview questions
if 'ai_detection_results' not in st.session_state:
    st.session_state.ai_detection_results = None
if 'interview_analysis_results' not in st.session_state:
    st.session_state.interview_analysis_results = None # Stores covered/uncovered/own questions
if 'candidate_evaluation_results' not in st.session_state:
    st.session_state.candidate_evaluation_results = None # Stores individual and overall evaluation

# Hashes for change detection - used to clear analysis results if files are re-uploaded
if 'last_jd_hash' not in st.session_state:
    st.session_state.last_jd_hash = None
if 'last_shared_resume_hash' not in st.session_state:
    st.session_state.last_shared_resume_hash = None
if 'last_conversation_transcript_hash' not in st.session_state:
    st.session_state.last_conversation_transcript_hash = None


def get_file_hash(file_uploader_object):
    """Generates a SHA256 hash for the content of an uploaded file."""
    if file_uploader_object is not None:
        file_uploader_object.seek(0) # Ensure we read from the beginning
        hasher = hashlib.sha256()
        buf = file_uploader_object.read(io.DEFAULT_BUFFER_SIZE)
        while buf:
            hasher.update(buf)
            buf = file_uploader_object.read(io.DEFAULT_BUFFER_SIZE)
        file_uploader_object.seek(0) # Reset pointer after hashing
        return hasher.hexdigest()
    return None


# --- Sidebar: File Uploads ---
st.sidebar.header("Upload Files")

# Essential uploads always visible
shared_resume_file = st.sidebar.file_uploader("1. Candidate Resume (PDF, TXT)", type=["pdf", "txt"],
                                              key="shared_resume_upload")
jd_file = st.sidebar.file_uploader("2. Job Description (TXT)", type=["txt"], key="jd_upload")

# Optional upload for interview analysis, hidden by default
with st.sidebar.expander("3. Interview Transcript (Optional)"):
    conversation_transcript_file = st.file_uploader("Upload Interview Transcript (TXT)", type=["txt"],
                                                            key="conversation_transcript_upload")


# --- Handle File Changes and Clear Relevant State ---
# This logic ensures that if a file is changed, previous analysis results dependent on it are cleared.
current_shared_resume_hash = get_file_hash(shared_resume_file)
current_jd_hash = get_file_hash(jd_file)
current_conversation_transcript_hash = get_file_hash(conversation_transcript_file)


# Check if shared resume file changed
if current_shared_resume_hash != st.session_state.last_shared_resume_hash:
    if st.session_state.ai_detection_results is not None or \
       st.session_state.jd_analysis_results is not None or \
       st.session_state.interview_analysis_results is not None or \
       st.session_state.candidate_evaluation_results is not None:
        st.info("New resume file detected. Clearing previous analysis results.")
    st.session_state.ai_detection_results = None
    st.session_state.jd_analysis_results = None
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = []
    st.session_state.candidate_resume_text = ""
    st.session_state.last_shared_resume_hash = current_shared_resume_hash

# Check if JD file changed
if current_jd_hash != st.session_state.last_jd_hash:
    if st.session_state.jd_analysis_results is not None or \
       st.session_state.interview_analysis_results is not None or \
       st.session_state.candidate_evaluation_results is not None:
        st.info("New Job Description detected. Clearing previous analysis results.")
    st.session_state.jd_analysis_results = None
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = []
    st.session_state.job_description_text = ""
    st.session_state.last_jd_hash = current_jd_hash

# Check if Conversation Transcript file changed
if current_conversation_transcript_hash != st.session_state.last_conversation_transcript_hash:
    if st.session_state.interview_analysis_results is not None or \
       st.session_state.candidate_evaluation_results is not None:
        st.info("New Interview Transcript detected. Clearing previous interview analysis and evaluation results.")
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = [] # Clear Q&A as context changed
    st.session_state.last_conversation_transcript_hash = current_conversation_transcript_hash


# --- Sidebar: Action Buttons ---
st.sidebar.markdown("---")
st.sidebar.header("Perform Analysis")

# AI Resume Detection Action
st.sidebar.subheader("AI Resume Detection")
# Removed 'include_explanation' checkbox - explanation is now always included
detect_ai_button = st.sidebar.button("Detect AI in Resume", type="secondary", help="Analyze the resume for AI-generated content.")

# Resume & JD Analysis Action
st.sidebar.subheader("Resume & JD Analysis")
analyze_button = st.sidebar.button("Analyze Resume against JD", type="primary", help="Get compatibility score and generate interview questions.")

# Interview Analysis & Evaluation Actions
st.sidebar.subheader("Interview Analysis")
analyze_interview_button = st.sidebar.button("Analyze Interview Coverage", type="secondary", help="Identify covered/uncovered questions from the transcript.")
evaluate_responses_button = st.sidebar.button("Evaluate Candidate Responses", type="primary", help="Get a holistic evaluation of candidate's interview performance.")


# --- Handle Button Clicks (Logic for FastAPI calls) ---

# AI Resume Detection Button Logic
if detect_ai_button:
    if not shared_resume_file:
        st.error("Please upload a **Candidate Resume** file (PDF or TXT) to perform AI detection.")
    else:
        st.session_state.ai_detection_results = None  # Clear previous results
        with st.spinner("Detecting AI generated content..."):
            try:
                files = {
                    "resume_file": (shared_resume_file.name, shared_resume_file.getvalue(), shared_resume_file.type)}
                # Always send include_explanation=True
                data = {"include_explanation": "true"}

                response = requests.post(f"{FASTAPI_BASE_URL}/resume/detect_ai", files=files, data=data, timeout=60)
                response.raise_for_status()

                ai_detection_data = response.json()
                if ai_detection_data.get("status") == "success":
                    st.session_state.ai_detection_results = ai_detection_data.get("data")
                    st.success("AI detection complete!")
                else:
                    st.error(f"AI detection failed: {ai_detection_data.get('detail', 'Unknown error')}")

            except requests.exceptions.Timeout:
                st.error("The AI detection request timed out. The server took too long to respond.")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the FastAPI server for AI detection.")
                st.info(f"Please ensure your FastAPI server is running at **{FASTAPI_BASE_URL}** and is accessible.")
            except requests.exceptions.HTTPError as e:
                st.error(f"HTTP error occurred during AI detection: {e}")
                if response.status_code == 422:
                    st.json(response.json())
                else:
                    st.text(f"Raw response: {response.text}")
            except json.JSONDecodeError:
                st.error("Received an invalid JSON response from the AI detection API. Check FastAPI logs for errors.")
                if 'response' in locals() and response:
                    st.text(f"Raw response: {response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred during AI detection: {e}")


# Resume & JD Analysis Button Logic
if analyze_button:
    if not jd_file or not shared_resume_file:
        st.error("Please upload both a **Job Description** and a **Candidate Resume** file to analyze.")
    else:
        st.session_state.jd_analysis_results = None
        st.session_state.interview_analysis_results = None
        st.session_state.candidate_evaluation_results = None
        st.session_state.conversation_history = []
        st.session_state.job_description_text = ""
        st.session_state.candidate_resume_text = ""

        with st.spinner("Analyzing resume against job description and generating questions..."):
            files = {
                "jd_file": (jd_file.name, jd_file.getvalue(), jd_file.type),
                "resume_file": (shared_resume_file.name, shared_resume_file.getvalue(), shared_resume_file.type)
            }
            try:
                response = requests.post(f"{FASTAPI_BASE_URL}/full-analysis/", files=files, timeout=120)
                response.raise_for_status()

                full_analysis_data = response.json()
                st.session_state.jd_analysis_results = full_analysis_data

                st.session_state.job_description_text = full_analysis_data.get("extracted_jd_text", "")
                st.session_state.candidate_resume_text = full_analysis_data.get("extracted_resume_text", "")

                st.session_state.conversation_history = [
                    {
                        "role": "assistant",
                        "content": "I have reviewed the resume against the job description and generated initial interview questions. How can I help you further with this candidate's profile?"
                    }
                ]
                st.success("JD & Resume analysis complete! See results below and ask questions.")
            except requests.exceptions.Timeout:
                st.error("The analysis request timed out. The server took too long to respond.")
                st.info("This might happen if the analysis is very complex or the server is busy. Try again or check server logs.")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the FastAPI server for analysis.")
                st.info(f"Please ensure your FastAPI server is running at **{FASTAPI_BASE_URL}** and is accessible.")
            except requests.exceptions.HTTPError as e:
                st.error(f"HTTP error occurred during analysis: {e}")
                if response.status_code == 422:
                    try:
                        st.json(response.json())
                    except json.JSONDecodeError:
                        st.text(f"Raw response: {response.text}")
                else:
                    st.text(f"Raw response: {response.text}")
            except json.JSONDecodeError:
                st.error("Received an invalid JSON response from the analysis API. Check FastAPI logs for errors.")
                if 'response' in locals() and response:
                    st.text(f"Raw response: {response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred during analysis: {e}")


# Interview Coverage Analysis Button Logic
if analyze_interview_button:
    if not conversation_transcript_file:
        st.error("Please upload an **Interview Transcript** file to analyze interview coverage.")
    elif not st.session_state.jd_analysis_results:
        st.error("Please run **'Analyze Resume against JD'** first to generate interview questions for analysis.")
    else:
        st.session_state.interview_analysis_results = None # Clear previous
        st.session_state.candidate_evaluation_results = None # Clear downstream
        with st.spinner("Analyzing interview questions coverage..."):
            try:
                # Prepare AI generated questions as a file-like object
                ai_gen_q_bytes = io.BytesIO(st.session_state.jd_analysis_results['interview_questions'].encode('utf-8'))
                ai_gen_q_file_obj = ("ai_generated_questions.txt", ai_gen_q_bytes, "text/plain")

                files = {
                    "ai_generated_questions_file": ai_gen_q_file_obj,
                    "conversation_transcript_file": (conversation_transcript_file.name, conversation_transcript_file.getvalue(), conversation_transcript_file.type)
                }
                response = requests.post(f"{FASTAPI_BASE_URL}/result/analyze-interview-questions/", files=files, timeout=90)
                response.raise_for_status()
                
                interview_analysis_data = response.json()
                st.session_state.interview_analysis_results = interview_analysis_data
                st.success("Interview coverage analysis complete!")
            except requests.exceptions.Timeout:
                st.error("The interview coverage analysis request timed out.")
            except requests.exceptions.ConnectionError:
                st.error("Failed to connect to the FastAPI server for interview coverage analysis.")
            except requests.exceptions.HTTPError as e:
                st.error(f"HTTP error occurred during interview coverage analysis: {e}")
                if response.status_code == 422:
                    st.json(response.json())
                else:
                    st.text(f"Raw response: {response.text}")
            except json.JSONDecodeError:
                st.error("Received an invalid JSON response from the interview coverage API.")
                if 'response' in locals() and response:
                    st.text(f"Raw response: {response.text}")
            except Exception as e:
                st.error(f"An unexpected error occurred during interview coverage analysis: {e}")


# Candidate Response Evaluation Button Logic
if evaluate_responses_button:
    if not st.session_state.interview_analysis_results:
        st.error("Please run **'Analyze Interview Coverage'** first to get questions for evaluation.")
    elif not conversation_transcript_file or not jd_file or not shared_resume_file:
        st.error("Please ensure **Interview Transcript**, **Job Description**, and **Candidate Resume** files are uploaded for evaluation.")
    else:
        st.session_state.candidate_evaluation_results = None # Clear previous
        covered_generated_questions = st.session_state.interview_analysis_results.get("covered_generated_questions", [])
        interviewer_own_questions = st.session_state.interview_analysis_results.get("interviewer_own_questions", [])

        if not covered_generated_questions and not interviewer_own_questions:
            st.warning("No questions were identified as asked in the interview. Cannot evaluate responses.")
        else:
            with st.spinner("Evaluating candidate responses holistically..."):
                try:
                    all_questions_asked = covered_generated_questions + interviewer_own_questions
                    
                    files = {
                        "conversation_transcript_file": (conversation_transcript_file.name, conversation_transcript_file.getvalue(), conversation_transcript_file.type),
                        "jd_file": (jd_file.name, jd_file.getvalue(), jd_file.type),
                        "resume_file": (shared_resume_file.name, shared_resume_file.getvalue(), shared_resume_file.type)
                    }
                    data = {
                        "all_questions_asked_json": json.dumps(all_questions_asked)
                    }

                    response = requests.post(f"{FASTAPI_BASE_URL}/evaluate-candidate-responses/", files=files, data=data, timeout=180)
                    response.raise_for_status()

                    evaluation_data = response.json()
                    st.session_state.candidate_evaluation_results = evaluation_data
                    st.success("Candidate response evaluation complete!")
                except requests.exceptions.Timeout:
                    st.error("The response evaluation request timed out. The server took too long to respond.")
                except requests.exceptions.ConnectionError:
                    st.error("Failed to connect to the FastAPI server for response evaluation.")
                except requests.exceptions.HTTPError as e:
                    st.error(f"HTTP error occurred during response evaluation: {e}")
                    if response.status_code == 422:
                        st.json(response.json())
                    else:
                        st.text(f"Raw response: {response.text}")
                except json.JSONDecodeError:
                    st.error("Received an invalid JSON response from the evaluation API.")
                    if 'response' in locals() and response:
                        st.text(f"Raw response: {response.text}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during response evaluation: {e}")


# --- Main Content Area with Tabs ---
tab1, tab2, tab3, tab4 = st.tabs([
    "AI Resume Detection",
    "Resume & JD Analysis",
    "Interview Analysis & Evaluation",
    "Interactive Q&A"
])

with tab1:
    st.header("AI Resume Detection Results")
    if st.session_state.ai_detection_results:
        results = st.session_state.ai_detection_results

        col_ai1, col_ai2 = st.columns(2)
        with col_ai1:
            st.metric(label="Classification", value=results.get('classification', 'N/A'))
        with col_ai2:
            score = results.get('overall_confidence_score', 'N/A')
            st.metric(label="Overall Confidence Score", value=f"{score}/100" if score != "N/A" else "N/A")

        st.markdown("---")
        st.subheader("Detection Criteria Scores")
        ai_criteria_scores = {
            "Formatting Consistency": results.get('formatting_consistency_score', 'N/A'),
            "Language Use": results.get('language_use_score', 'N/A'),
            "Detail Depth": results.get('detail_depth_score', 'N/A'),
            "Error Detection": results.get('error_detection_score', 'N/A')
        }

        if any(score != "N/A" for score in ai_criteria_scores.values()):
            cols_ai_criteria = st.columns(min(len(ai_criteria_scores), 4))
            i = 0
            for criterion, score in ai_criteria_scores.items():
                with cols_ai_criteria[i % len(cols_ai_criteria)]:
                    st.metric(label=criterion, value=f"{score}/100" if score != "N/A" else "N/A")
                i += 1
        else:
            st.info("No detailed criteria scores available.")

        explanation = results.get('explanation')
        if explanation:
            with st.expander("Detailed Explanation"): # Explanation is always provided, hidden by default
                st.write(explanation)
    else:
        st.info("Upload a resume and click 'Detect AI in Resume' in the sidebar to see results here.")


with tab2:
    st.header("Job Description & Resume Analysis Results")
    if st.session_state.jd_analysis_results:
        analysis_score = st.session_state.jd_analysis_results.get('score', {})
        interview_questions = st.session_state.jd_analysis_results.get('interview_questions', "No interview questions generated.")

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            overall_score = analysis_score.get('overall_score', 'N/A')
            st.metric(label="Overall Score", value=f"{overall_score}/100")
        with col2:
            if isinstance(overall_score, (int, float)) and overall_score >= 60:
                st.success("Candidate is ELIGIBLE! 🎉")
            else:
                st.warning("Candidate is NOT ELIGIBLE. ❌")

        st.markdown("---")

        st.subheader("Criteria Scores")
        criteria_scores = analysis_score.get('criteria_scores', {})
        if criteria_scores:
            cols = st.columns(min(len(criteria_scores), 3))
            i = 0
            for criterion, score in criteria_scores.items():
                with cols[i % len(cols)]:
                    st.metric(label=criterion, value=f"{score}/100")
                i += 1
        else:
            st.info("No detailed criteria scores available.")

        st.markdown("---")

        st.subheader("Strengths")
        strengths_text = analysis_score.get('strengths_text', "No strengths identified.")
        st.write(strengths_text)

        st.markdown("---")

        with st.expander("Generated Interview Questions"):
            if interview_questions:
                st.markdown(interview_questions)
            else:
                st.info("No interview questions generated.")
    else:
        st.info("Upload a Job Description and Resume, then click 'Analyze Resume against JD' in the sidebar to see results here.")


with tab3:
    st.header("Interview Analysis & Evaluation")
    # Conditional display for the entire tab's content
    if not conversation_transcript_file or not st.session_state.jd_analysis_results:
        st.info("Please upload an Interview Transcript and run 'Analyze Resume against JD' first to enable this section.")
    else:
        # Display interview coverage results if available
        if st.session_state.interview_analysis_results:
            results = st.session_state.interview_analysis_results
            st.markdown("### Interview Question Coverage Report")
            
            covered_generated_questions = results.get("covered_generated_questions", [])
            uncovered_generated_questions = results.get("uncovered_generated_questions", [])
            interviewer_own_questions = results.get("interviewer_own_questions", [])

            if covered_generated_questions:
                st.subheader("AI-Generated Questions Covered:")
                for q in covered_generated_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("No AI-generated questions were identified as covered.")

            if uncovered_generated_questions:
                st.subheader("AI-Generated Questions NOT Covered:")
                for q in uncovered_generated_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("All AI-generated questions appear to have been covered.")

            if interviewer_own_questions:
                st.subheader("Interviewer's Own Unique Questions:")
                for q in interviewer_own_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("No unique questions asked by the interviewer beyond the AI-generated list were identified.")

        if st.session_state.candidate_evaluation_results:
            evaluation_results = st.session_state.candidate_evaluation_results
            st.markdown("### Detailed Response Evaluation")

            st.subheader("Overall Interview Performance:")
            st.metric(label="Overall Score", value=f"{evaluation_results.get('overall_interview_score', 'N/A')}/100")
            st.write(evaluation_results.get('overall_interview_summary', 'N/A'))

            st.subheader("Individual Question Evaluations:")
            individual_evals = evaluation_results.get('individual_evaluations', [])
            if individual_evals:
                for i, eval_item in enumerate(individual_evals):
                    st.markdown(f"**Question {i+1}:** {eval_item.get('question', 'N/A')}")
                    st.markdown(f"**Score:** {eval_item.get('score', 'N/A')}/10")
                    st.markdown(f"**Rationale:** {eval_item.get('rationale', 'N/A')}")
                    st.markdown("---")
            else:
                st.info("No individual question evaluations available.")
        else:
            # Only show this if interview_analysis_results are present, prompting for next step
            if st.session_state.interview_analysis_results:
                st.info("Click 'Evaluate Candidate Responses' in the sidebar to see detailed response evaluations.")


with tab4:
    st.header("Interactive Q&A")
    st.info("Ask follow-up questions about the candidate's resume, job description, or interview analysis.")

    if st.session_state.job_description_text and st.session_state.candidate_resume_text:
        # Build the comprehensive system context message once
        if not st.session_state.conversation_history or st.session_state.conversation_history[0].get("role") != "system":
            qa_context_summary = (
                f"\n\n--- FULL JOB DESCRIPTION CONTEXT ---\n{st.session_state.job_description_text}\n\n--- FULL RESUME CONTEXT ---\n{st.session_state.candidate_resume_text}"
            )
            if conversation_transcript_file:
                qa_context_summary += f"\n\n--- FULL INTERVIEW TRANSCRIPT CONTEXT ---\n{conversation_transcript_file.getvalue().decode('utf-8')}"

            if st.session_state.jd_analysis_results:
                qa_context_summary += (
                    f"\n\n--- INITIAL ANALYSIS SUMMARY ---\n"
                    f"Overall Score: {st.session_state.jd_analysis_results.get('score', {}).get('overall_score', 'N/A')}/100\n"
                    f"Strengths: {st.session_state.jd_analysis_results.get('score', {}).get('strengths_text', 'N/A')}\n"
                    f"Generated Interview Questions:\n{st.session_state.jd_analysis_results.get('interview_questions', 'N/A')}"
                )
            if st.session_state.interview_analysis_results:
                qa_context_summary += (
                    f"\n\n--- INTERVIEW QUESTION COVERAGE ---\n"
                    f"Covered AI Questions: {st.session_state.interview_analysis_results.get('covered_generated_questions', [])}\n"
                    f"Uncovered AI Questions: {st.session_session_state.interview_analysis_results.get('uncovered_generated_questions', [])}\n"
                    f"Interviewer's Own Questions: {st.session_state.interview_analysis_results.get('interviewer_own_questions', [])}"
                )
            if st.session_state.candidate_evaluation_results:
                eval_summary_text = f"\n\n--- RESPONSE EVALUATIONS ---\n"
                eval_summary_text += f"Overall Interview Score: {st.session_state.candidate_evaluation_results.get('overall_interview_score', 'N/A')}/100\n"
                eval_summary_text += f"Overall Interview Summary: {st.session_state.candidate_evaluation_results.get('overall_interview_summary', 'N/A')}\n"
                for item in st.session_state.candidate_evaluation_results.get('individual_evaluations', []):
                    eval_summary_text += f"Q: {item.get('question', '')}\nScore: {item.get('score', '')}/10. Rationale: {item.get('rationale', '')}\n"
                qa_context_summary += eval_summary_text

            st.session_state.conversation_history = [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant providing concise answers about a candidate's resume, its compatibility with a job description, and detailed interview analysis including question coverage and response evaluations. "
                        "You have access to the full resume, job description, interview transcript, and all analysis results. Provide short, direct, point-by-point answers where appropriate."
                        f"{qa_context_summary}"
                    ),
                },
                {"role": "assistant",
                 "content": "I have completed the full analysis. How can I help you further with this candidate's profile?"},
            ]
            with st.chat_message("assistant"):
                st.write(st.session_state.conversation_history[1]["content"])


        for msg in st.session_state.conversation_history[1:]:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])

        user_question = st.chat_input("Your question:")

        if user_question:
            st.session_state.conversation_history.append({"role": "user", "content": user_question})
            with st.chat_message("user"):
                st.write(user_question)

            with st.spinner("AI is thinking..."):
                try:
                    qa_payload = {"messages": st.session_state.conversation_history}
                    
                    qa_response = requests.post(f"{FASTAPI_BASE_URL}/answer-follow-up-question/", json=qa_payload, timeout=90)
                    qa_response.raise_for_status()
                    answer = qa_response.json().get("answer",
                                                    "I couldn't get an answer for that question. Please try rephrasing.")
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.write(answer)
                except requests.exceptions.Timeout:
                    answer = "The Q&A request timed out. The AI took too long to respond."
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.error(answer)
                except requests.exceptions.ConnectionError:
                    answer = "Failed to connect to the FastAPI server for Q&A. Is it running?"
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.error(answer)
                except requests.exceptions.HTTPError as e:
                    answer = f"HTTP error during Q&A: {e}. Check FastAPI logs."
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.error(answer)
                except json.JSONDecodeError:
                    answer = "Received an invalid JSON response for Q&A. Check FastAPI logs."
                    if 'qa_response' in locals() and qa_response:
                        st.text(f"Raw response: {qa_response.text}")
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.error(answer)
                except Exception as e:
                    answer = f"An unexpected error occurred during Q&A: {e}"
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    with st.chat_message("assistant"):
                        st.error(answer)
    else:
        st.info("Upload and analyze a Job Description and Resume to enable interactive Q&A.")