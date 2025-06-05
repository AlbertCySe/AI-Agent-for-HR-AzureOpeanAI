import streamlit as st
import hashlib
import io

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

def clear_all_analysis_state():
    """Clears ALL analysis-related session state variables."""
    st.session_state.jd_analysis_results = None
    st.session_state.ai_detection_results = None
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = []
    st.session_state.job_description_text = ""
    st.session_state.candidate_resume_text = ""
    # Removed: st.info("Previous analysis results cleared.")

def clear_jd_dependent_analysis_state():
    """Clears analysis results that depend on the Job Description.
    This preserves AI detection results if only the JD changes.
    """
    st.session_state.jd_analysis_results = None
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = [] # Clear Q&A as context changed (JD is part of context)
    st.session_state.job_description_text = "" # Clear extracted JD text
    # Removed: st.info("Previous JD-dependent analysis results cleared.")


def clear_interview_related_state():
    """Clears only interview-related analysis results."""
    st.session_state.interview_analysis_results = None
    st.session_state.candidate_evaluation_results = None
    st.session_state.conversation_history = [] # Clear Q&A as context changed
    # Removed: st.info("Previous interview analysis results cleared.")
