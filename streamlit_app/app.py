import streamlit as st
import requests
import json
import io
import hashlib
from datetime import datetime  # Import datetime module

# Import modular components using direct imports (no leading dot)
from utils import get_file_hash, clear_all_analysis_state, clear_jd_dependent_analysis_state, \
    clear_interview_related_state
from api_client import (
    call_detect_ai_resume,
    call_full_analysis,
    call_analyze_interview_coverage,
    call_evaluate_responses,
    call_answer_follow_up
)

# --- Configuration ---
# FASTAPI_BASE_URL is now defined in api_client.py

st.set_page_config(
    page_title="AI Resume & Interview Analyzer",
    layout="wide",  # Use wide layout for more space
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
    st.session_state.jd_analysis_results = None  # Stores combined score and interview questions
if 'ai_detection_results' not in st.session_state:
    st.session_state.ai_detection_results = None
if 'interview_analysis_results' not in st.session_state:
    st.session_state.interview_analysis_results = None  # Stores covered/uncovered/own questions
if 'candidate_evaluation_results' not in st.session_state:
    st.session_state.candidate_evaluation_results = None  # Stores individual and overall evaluation

# Hashes for change detection - used to clear analysis results if files are re-uploaded
if 'last_jd_hash' not in st.session_state:
    st.session_state.last_jd_hash = None
if 'last_shared_resume_hash' not in st.session_state:
    st.session_state.last_shared_resume_hash = None
if 'last_conversation_transcript_hash' not in st.session_state:
    st.session_state.last_conversation_transcript_hash = None

# New: State variables to track if an analysis is in progress
if 'is_ai_detection_in_progress' not in st.session_state:
    st.session_state.is_ai_detection_in_progress = False
if 'is_jd_analysis_in_progress' not in st.session_state:
    st.session_state.is_jd_analysis_in_progress = False
if 'is_interview_analysis_in_progress' not in st.session_state:
    st.session_state.is_interview_analysis_in_progress = False
if 'is_evaluation_in_progress' not in st.session_state:
    st.session_state.is_evaluation_in_progress = False

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

# Check if shared resume file changed (most impactful change, clears EVERYTHING related to a new candidate)
if current_shared_resume_hash != st.session_state.last_shared_resume_hash:
    if st.session_state.last_shared_resume_hash is not None:  # Only show info if it's not the initial load
        st.info("New resume file detected. Clearing all previous analysis results for a new candidate scenario.")
    clear_all_analysis_state()  # This function clears ALL states, including AI detection
    st.session_state.last_shared_resume_hash = current_shared_resume_hash
    # Also reset JD and conversation hashes when the resume changes, as it signifies a completely new analysis context.
    st.session_state.last_jd_hash = None  # Ensure JD is treated as new for next comparison
    st.session_state.last_conversation_transcript_hash = None  # Ensure transcript is treated as new

# Check if JD file changed (clears JD-dependent analysis, but PRESERVES AI detection)
# Use 'elif' to ensure this only runs if the resume hash has NOT changed in this run
elif current_jd_hash != st.session_state.last_jd_hash:
    if st.session_state.last_jd_hash is not None:  # Only show info if it's not the initial load
        st.info("New Job Description detected. Clearing previous JD-dependent analysis results.")
    clear_jd_dependent_analysis_state()  # Use newly defined utility function
    st.session_state.last_jd_hash = current_jd_hash

# Check if Conversation Transcript file changed (only clears interview analysis)
# Use 'elif' to ensure this only runs if neither resume nor JD hashes changed in this run
elif current_conversation_transcript_hash != st.session_state.last_conversation_transcript_hash:
    if st.session_state.last_conversation_transcript_hash is not None:  # Only show info if it's not the initial load
        st.info("New Interview Transcript detected. Clearing previous interview analysis and evaluation results.")
    clear_interview_related_state()  # Use utility function
    st.session_state.last_conversation_transcript_hash = current_conversation_transcript_hash

# --- Main Content Area with Tabs ---
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "AI Resume Detection",
    "Resume & JD Analysis",
    "Interview Analysis",
    "Detailed Response Evaluation",
    "Interactive Q&A"
])

# Inject custom CSS for the fixed chat input
st.markdown(
    """
    <style>
    /* Adjust padding for the main content area to prevent overlap with fixed chat input */
    /* This targets the main content area that wraps all tabs */
    .st-emotion-cache-z5fcl4 { /* This is a common class for the main content div */
        padding-bottom: 90px; /* Adjust based on the height of the chat input */
    }

    /* Make the st.chat_input sticky at the bottom of the viewport */
    div[data-testid="stForm"] > div:last-child { /* Targets the last div child of st-chat-container, which is the input wrapper */
        position: fixed;
        bottom: 0px;
        left: 0; /* Aligns to left edge of content area */
        right: 0; /* Aligns to right edge of content area */
        width: 100%; /* Ensures it spans the full width of the main content */
        background-color: var(--background-color); /* Use Streamlit's background color variable */
        padding: 10px 1rem; /* Padding inside the input bar container */
        box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.1); /* Optional shadow */
        z-index: 1000; /* Ensure it stays on top */
    }

    /* Ensure the padding applies within the tab content area too if needed */
    div[data-testid="stVerticalBlock"] > div.st-emotion-cache-h5f0k { /* Example for a container inside a tab */
        padding-bottom: 90px; /* Adjust for content within the tab */
    }
    </style>
    """,
    unsafe_allow_html=True
)

with tab1:
    st.header("AI Resume Detection Results")

    # Determine button text
    detect_ai_button_text = "Detect AI in Resume" if st.session_state.ai_detection_results is None else "Redetect AI in Resume"

    # AI Resume Detection Action Button - MOVED HERE
    detect_ai_button = st.button(detect_ai_button_text, type="primary",
                                 help="Analyze the resume for AI-generated content.")

    if detect_ai_button:
        if not shared_resume_file:
            st.error("Please upload a **Candidate Resume** file (PDF or TXT) in the sidebar to perform AI detection.")
        else:
            # Clear previous AI detection results immediately on click
            st.session_state.ai_detection_results = None
            st.session_state.is_ai_detection_in_progress = True  # Set progress flag
            with st.spinner("Detecting AI generated content..."):
                try:
                    ai_detection_data = call_detect_ai_resume(
                        resume_file_obj=shared_resume_file,
                        resume_filename=shared_resume_file.name,
                        resume_file_type=shared_resume_file.type
                    )
                    st.session_state.ai_detection_results = ai_detection_data.get("data")
                    st.success("AI detection complete!")
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    st.error(f"Error during AI detection: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during AI detection: {e}")
                finally:
                    st.session_state.is_ai_detection_in_progress = False  # Reset progress flag

    # Display results only if they exist AND no analysis is in progress
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
                    st.metric(label=criterion, value=f"{score}/100")
                i += 1
        else:
            st.info("No detailed criteria scores available.")

        explanation = results.get('explanation')
        if explanation:
            with st.expander("Detailed Explanation"):
                st.write(explanation)
    elif not st.session_state.is_ai_detection_in_progress:  # Only show info if not loading
        st.info("Upload a resume in the sidebar and click 'Detect AI in Resume' above to see results here.")

with tab2:
    st.header("Job Description & Resume Analysis Results")

    # Determine button text
    analyze_jd_resume_button_text = "Analyze Resume against JD" if st.session_state.jd_analysis_results is None else "Reanalyze Resume against JD"

    # Resume & JD Analysis Action Button - MOVED HERE
    analyze_jd_resume_button = st.button(analyze_jd_resume_button_text, type="primary",
                                         help="Get compatibility score and generate interview questions.")

    if analyze_jd_resume_button:
        if not jd_file or not shared_resume_file:
            st.error(
                "Please upload both a **Job Description** and a **Candidate Resume** file in the sidebar to analyze.")
        else:
            # Clear previous JD-dependent analysis results immediately on click
            clear_jd_dependent_analysis_state()  # This function already clears JD-dependent state
            st.session_state.is_jd_analysis_in_progress = True  # Set progress flag
            with st.spinner("Analyzing resume against job description and generating questions..."):
                try:
                    full_analysis_data = call_full_analysis(
                        jd_file_obj=jd_file, jd_filename=jd_file.name, jd_file_type=jd_file.type,
                        resume_file_obj=shared_resume_file, resume_filename=shared_resume_file.name,
                        resume_file_type=shared_resume_file.type
                    )
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
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    st.error(f"Error during JD & Resume analysis: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during JD & Resume analysis: {e}")
                finally:
                    st.session_state.is_jd_analysis_in_progress = False  # Reset progress flag

    # Display results only if they exist AND no analysis is in progress
    if st.session_state.jd_analysis_results:
        analysis_score = st.session_state.jd_analysis_results.get('score', {})
        interview_questions = st.session_state.jd_analysis_results.get('interview_questions',
                                                                       "No interview questions generated.")
        hard_requirements = analysis_score.get('hard_requirements_match', {})  # Get the new hard requirements

        st.markdown("---")

        overall_score = analysis_score.get('overall_score', 'N/A')
        st.metric(label="Overall Score", value=f"{overall_score}/100")

        is_eligible = True
        eligibility_reasons = []

        # Hard requirements check
        if hard_requirements:
            st.markdown("---")
            st.subheader("Hard Requirements Match")
            st.markdown(
                "*(These are strict criteria like **location**, **working hours**, or **minimum experience**. 'Yes' means met, 'No' means not met, 'Not Specified' means JD didn't mention it, 'Cannot Determine' means insufficient info, 'N/A' means not applicable.)*"
            )

            # Create a list of items to iterate over to maintain order for display
            hard_req_items = [
                ("Location Match", hard_requirements.get("Location Match", "N/A")),
                ("Full-time Availability", hard_requirements.get("Full-time Availability", "N/A")),
                ("Minimum Experience Met", hard_requirements.get("Minimum Experience Met", "N/A")),
                ("Other Specific Requirements Met", hard_requirements.get("Other Specific Requirements Met", "N/A"))
            ]

            # Display each hard requirement on a new line for better readability and alignment
            for req_key, req_value in hard_req_items:
                st.markdown(f"**{req_key}:** ", unsafe_allow_html=True)  # Bold key
                if req_value == "No":
                    st.error(f"**{req_value}** ❌")
                    is_eligible = False
                    eligibility_reasons.append(f"Hard Requirement '{req_key}' was not met.")
                elif req_value == "Yes":
                    st.success(f"**{req_value}** ✅")
                else:  # For "Not Specified in JD", "Cannot Determine", "N/A"
                    st.warning(f"**{req_value}** ⚠️")

            st.markdown("---")  # Visual separator after hard requirements

        if isinstance(overall_score, (int, float)) and overall_score < 60:
            is_eligible = False
            eligibility_reasons.append("Overall score is below 60%.")

        if is_eligible:
            st.success("Candidate is ELIGIBLE! 🎉")
        else:
            st.warning("Candidate is NOT ELIGIBLE. ❌")
            if eligibility_reasons:
                st.markdown("**Reasons for Ineligibility:**")
                for reason in eligibility_reasons:
                    st.markdown(f"- {reason}")

        st.markdown("---")

        st.subheader("Criteria Scores")
        st.markdown(
            "*(These scores reflect the compatibility of the resume with the JD across various soft and technical aspects, out of 100.)*"
        )
        criteria_scores = analysis_score.get('criteria_scores', {})
        if criteria_scores:
            # Using st.columns for metrics, which are generally well-aligned
            cols = st.columns(min(len(criteria_scores), 3))
            i = 0
            for criterion, score in criteria_scores.items():
                with cols[i % len(cols)]:
                    st.metric(label=criterion, value=f"{score}/100")
                i += 1  # Increment correctly
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
    elif not st.session_state.is_jd_analysis_in_progress:  # Only show info if not loading
        st.info(
            "Upload a Job Description and Resume in the sidebar, then click 'Analyze Resume against JD' above to see results here.")

with tab3:  # Interview Analysis tab
    st.header("Interview Analysis")

    # Determine button text
    analyze_interview_button_text = "Analyze Interview Coverage" if st.session_state.interview_analysis_results is None else "Reanalyze Interview Coverage"

    # Interview Analysis Action Button - MOVED HERE
    analyze_interview_button = st.button(analyze_interview_button_text, type="primary",
                                         help="Identify covered/uncovered questions from the transcript.")

    if analyze_interview_button:
        if not conversation_transcript_file:
            st.error("Please upload an **Interview Transcript** file in the sidebar to analyze interview coverage.")
        elif not st.session_state.jd_analysis_results:
            st.error(
                "Please run **'Analyze Resume against JD'** first on the 'Resume & JD Analysis' tab to generate interview questions for analysis.")
        else:
            # Clear previous interview-related results immediately on click
            clear_interview_related_state()  # This function already clears interview-related state
            st.session_state.is_interview_analysis_in_progress = True  # Set progress flag
            with st.spinner("Analyzing interview questions coverage..."):
                try:
                    ai_gen_q_text_from_state = st.session_state.jd_analysis_results.get('interview_questions', "")
                    if not ai_gen_q_text_from_state:
                        st.error(
                            "No AI-generated interview questions found in session state. Please re-run 'Analyze Resume against JD'.")
                        st.stop()

                    interview_analysis_data = call_analyze_interview_coverage(
                        ai_gen_q_text=ai_gen_q_text_from_state,
                        conversation_file_obj=conversation_transcript_file,
                        conversation_filename=conversation_transcript_file.name,
                        conversation_file_type=conversation_transcript_file.type
                    )
                    st.session_state.interview_analysis_results = interview_analysis_data
                    st.success("Interview coverage analysis complete!")
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    st.error(f"Error during interview coverage analysis: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred during interview coverage analysis: {e}")
                finally:
                    st.session_state.is_interview_analysis_in_progress = False  # Reset progress flag

    # Display results only if they exist AND no analysis is in progress
    if st.session_state.interview_analysis_results:
        results = st.session_state.interview_analysis_results
        st.markdown("### Interview Question Coverage Report")

        covered_generated_questions = results.get("covered_generated_questions", [])
        uncovered_generated_questions = results.get("uncovered_generated_questions", [])
        interviewer_own_questions = results.get("interviewer_own_questions", [])

        # Consolidated dropdown for all question types
        with st.expander("Interview Questions Breakdown"):
            if covered_generated_questions:
                st.subheader("AI-Generated Questions Covered:")
                for q in covered_generated_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("No AI-generated questions were identified as covered.")

            st.markdown("---")  # Separator for clarity within the expander

            if uncovered_generated_questions:
                st.subheader("AI-Generated Questions NOT Covered:")
                for q in uncovered_generated_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("All AI-generated questions appear to have been covered.")

            st.markdown("---")  # Separator for clarity within the expander

            if interviewer_own_questions:
                st.subheader("Interviewer's Own Unique Questions:")
                for q in interviewer_own_questions:
                    st.markdown(f"- {q}")
            else:
                st.info("No unique questions asked by the interviewer beyond the AI-generated list were identified.")
    elif not st.session_state.is_interview_analysis_in_progress:  # Only show info if not loading
        st.info(
            "Upload an Interview Transcript in the sidebar and click 'Analyze Interview Coverage' above to see results here.")

with tab4:  # Detailed Response Evaluation tab
    st.header("Detailed Response Evaluation")

    # Determine button text
    evaluate_responses_button_text = "Evaluate Candidate Responses" if st.session_state.candidate_evaluation_results is None else "Re-evaluate Candidate Responses"

    # Evaluate Candidate Responses Action Button - MOVED HERE
    evaluate_responses_button = st.button(evaluate_responses_button_text, type="primary",
                                          help="Get a holistic evaluation of candidate's interview performance.")

    if evaluate_responses_button:
        if not st.session_state.interview_analysis_results:
            st.error(
                "Please run **'Analyze Interview Coverage'** first on the 'Interview Analysis' tab to get questions for evaluation.")
        elif not conversation_transcript_file or not jd_file or not shared_resume_file:
            st.error(
                "Please ensure **Interview Transcript**, **Job Description**, and **Candidate Resume** files are uploaded in the sidebar for evaluation.")
        else:
            st.session_state.candidate_evaluation_results = None  # Clear previous
            st.session_state.is_evaluation_in_progress = True  # Set progress flag
            # CRITICAL CHANGE: Only pass questions that were actually *covered* or *interviewer's own*
            covered_generated_questions = st.session_state.interview_analysis_results.get("covered_generated_questions",
                                                                                          [])
            interviewer_own_questions = st.session_state.interview_analysis_results.get("interviewer_own_questions", [])

            # The list of questions to send for evaluation should ONLY include questions actually asked.
            all_questions_to_evaluate = covered_generated_questions + interviewer_own_questions

            if not all_questions_to_evaluate:
                st.warning("No questions were identified as asked in the interview. Cannot evaluate responses.")
                st.session_state.is_evaluation_in_progress = False  # Reset flag even on warning
            else:
                with st.spinner("Evaluating candidate responses holistically..."):
                    try:
                        evaluation_data = call_evaluate_responses(
                            all_questions_asked=all_questions_to_evaluate,  # Pass only the *asked* questions
                            conversation_file_obj=conversation_transcript_file,
                            conversation_filename=conversation_transcript_file.name,
                            conversation_file_type=conversation_transcript_file.type,
                            jd_file_obj=jd_file, jd_filename=jd_file.name, jd_file_type=jd_file.type,
                            resume_file_obj=shared_resume_file, resume_filename=shared_resume_file.name,
                            resume_file_type=shared_resume_file.type
                        )
                        st.session_state.candidate_evaluation_results = evaluation_data
                        st.success("Candidate response evaluation complete!")
                    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                        st.error(f"Error during candidate response evaluation: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred during candidate response evaluation: {e}")
                    finally:
                        st.session_state.is_evaluation_in_progress = False  # Reset progress flag

    # Display results only if they exist AND no analysis is in progress
    if st.session_state.candidate_evaluation_results:
        evaluation_results = st.session_state.candidate_evaluation_results

        st.subheader("Overall Interview Performance:")
        st.metric(label="Overall Score", value=f"{evaluation_results.get('overall_interview_score', 'N/A')}/100")
        st.write(evaluation_results.get('overall_interview_summary', 'N/A'))

        st.subheader("Individual Question Evaluations:")
        individual_evals = evaluation_results.get('individual_evaluations', [])
        if individual_evals:
            for i, eval_item in enumerate(individual_evals):
                st.markdown(f"**Question {i + 1}:** {eval_item.get('question', 'N/A')}")
                st.markdown(f"**Response Summary:** {eval_item.get('response_summary', 'N/A')}")
                st.markdown(f"**Score:** {eval_item.get('score', 'N/A')}/10")
                st.markdown(f"**Rationale:** {eval_item.get('rationale', 'N/A')}")
                st.markdown("---")
        else:
            st.info(
                "No individual question evaluations available. This might occur if no questions were identified as asked and answered in the transcript.")
    elif not st.session_state.is_evaluation_in_progress:  # Only show info if not loading
        st.info(
            "Upload Interview Transcript, Job Description, and Resume in the sidebar. Then run 'Analyze Resume against JD' and 'Analyze Interview Coverage' on previous tabs, followed by 'Evaluate Candidate Responses' above to see results here.")

with tab5:  # Interactive Q&A tab
    st.header("Interactive Q&A")
    st.info("Ask follow-up questions about the candidate's resume, job description, or interview analysis.")

    current_datetime = datetime.now().strftime("%B %d, %Y %H:%M:%S")

    if st.session_state.job_description_text and st.session_state.candidate_resume_text:
        # Pre-compute eligibility verdict based on hard requirements *before* populating conversation history
        hard_requirements = st.session_state.jd_analysis_results.get('score', {}).get('hard_requirements_match', {})
        is_hard_eligible = True
        hard_ineligibility_reasons = []

        # Check all hard requirements
        for req_key, req_value in hard_requirements.items():
            if req_value == "No":
                is_hard_eligible = False
                hard_ineligibility_reasons.append(f"'{req_key}' was not met.")

        eligibility_summary = ""
        if not is_hard_eligible:
            eligibility_summary = (
                f"**CRITICAL ELIGIBILITY STATUS:** Based on the hard requirements, "
                f"the candidate is **NOT ELIGIBLE** for this position. "
                f"Reasons: {'; '.join(hard_ineligibility_reasons)}. "
                f"This overrides any other scores or strengths for initial qualification.\n\n"
            )
        else:
            eligibility_summary = (
                "**CRITICAL ELIGIBILITY STATUS:** Based on the hard requirements, "
                "the candidate **MEETS THE MINIMUM CRITERIA** for this position.\n\n"
            )

        # Initialize conversation history with system message including current date and hard eligibility
        if not st.session_state.conversation_history or st.session_state.conversation_history[0].get(
                "role") != "system":
            qa_context_summary = (
                f"**IMPORTANT:** The current date and time is **{current_datetime}**. When asked for the current date or time, refer to this information.\n\n"
                f"{eligibility_summary}"  # Inject hard eligibility summary here
                f"--- FULL JOB DESCRIPTION CONTEXT ---\n{st.session_state.job_description_text}\n\n--- FULL RESUME CONTEXT ---\n{st.session_state.candidate_resume_text}"
            )
            if conversation_transcript_file:
                conversation_transcript_file.seek(0)  # Ensure reading from start
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
                    f"Uncovered AI Questions: {st.session_state.interview_analysis_results.get('uncovered_generated_questions', [])}\n"
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
                        "**Always prioritize the hard requirements for overall eligibility determination.** If any hard requirement is 'No', the candidate is definitively NOT eligible, regardless of other scores."
                        f"{qa_context_summary}"
                    ),
                },
                {"role": "assistant",
                 "content": "I have completed the full analysis. How can I help you further with this candidate's profile?"},
            ]

        # Display existing messages
        chat_messages_container = st.container(height=500, border=True)  # Give it a fixed height and border
        with chat_messages_container:
            for msg in st.session_state.conversation_history[1:]:  # Start from 1 to skip the system message
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])

        user_question = st.chat_input("Your question:")

        if user_question:
            st.session_state.conversation_history.append({"role": "user", "content": user_question})

            with st.spinner("AI is thinking..."):
                try:
                    answer_data = call_answer_follow_up(st.session_state.conversation_history)
                    answer = answer_data.get("answer",
                                             "I couldn't get an answer for that question. Please try rephrasing.")
                    st.session_state.conversation_history.append({"role": "assistant", "content": answer})
                    st.rerun()
                except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                    error_message = f"Error during Q&A: {e}"
                    st.session_state.conversation_history.append({"role": "assistant", "content": error_message})
                    st.error(error_message)
                    st.rerun()
                except Exception as e:
                    error_message = f"An unexpected error occurred during Q&A: {e}"
                    st.session_state.conversation_history.append({"role": "assistant", "content": error_message})
                    st.error(error_message)
                    st.rerun()

    else:  # If JD and Resume are not uploaded, hide chat input
        st.info("Upload and analyze a Job Description and Resume to enable interactive Q&A.")

