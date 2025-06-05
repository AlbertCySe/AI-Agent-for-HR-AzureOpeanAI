import re
import json
from typing import List, Dict, Any, Optional, Union
from openai import AzureOpenAI
from fastapi import HTTPException, status

# Corrected import path: using relative import for modules within the same package
from .modules.pdf_extractor import (
    extract_text_from_pdf_bytes_for_detection
)

def score_resume_against_jd(azure_openai_client: AzureOpenAI, deployment_name: str, resume_text: str,
                            jd_text: str) -> dict:
    """Scores a candidate's resume against a job description using AI."""
    prompt = (
        "You are an expert AI recruitment assistant. Your task is to meticulously analyze a candidate's resume against a specific job description.\n"
        "You must provide a detailed compatibility analysis. It is CRUCIAL that your response STRICTLY adheres to the precise format specified below.\n\n"
        f"--- Job Description (JD) ---\n{jd_text}\n\n"
        f"--- Candidate Resume ---\n{resume_text}\n\n"
        "--- Analysis ---\n"
        "Based on the provided Job Description and Candidate Resume, deliver your analysis. "
        "PAY VERY CLOSE ATTENTION to the required output format, including all headers, sub-headers, and bullet point styling.\n\n"
        "REQUIRED OUTPUT FORMAT (Strict Adherence Necessary):\n"
        "OVERALL_SCORE: [score]/100\n\n"
        "CRITERIA_SCORES:\n"
        "Technical Skills Match: [score]/100\n"
        "Experience Relevance: [score]/100\n"
        "Education Background: [score]/100\n"
        "Responsibilities Alignment: [score]/100\n"
        "Soft Skills/Communication: [score]/100\n\n"
        "HARD_REQUIREMENTS_MATCH:\n"
        "Location Match: [Yes/No/Not Specified in JD]\n"  # Updated option
        "Full-time Availability: [Yes/No/Not Specified in JD]\n"  # Updated option
        "Minimum Experience Met: [Yes/No/Not Specified in JD/Cannot Determine]\n"  # Updated option
        "Other Specific Requirements Met (e.g., Certifications, Specific Tools, etc.): [Yes/No/Not Specified in JD/N/A]\n\n"  # New, more general catch-all

        "STRENGTHS:\n"
        "- [Strength 1: A concise point directly highlighting how the candidate meets a key JD requirement.]\n"
        "- [Strength 2: Another specific, concise point of alignment with the JD.]"
        "- [Strength n: Mention n number of strengths only if it is related to the current Job Description (not much important if not critical)]\n\n"
        "IMPORTANT INSTRUCTIONS FOR THE AI MODEL:\n"
        "1.  The section headers (OVERALL_SCORE, CRITERIA_SCORES, HARD_REQUIREMENTS_MATCH, STRENGTHS) and criteria sub-headers (e.g., Technical Skills Match, Location Match) MUST be reproduced EXACTLY as shown above.\n"
        "2.  Each score MUST be an integer followed immediately by '/100'.\n"
        "3.  Each item under HARD_REQUIREMENTS_MATCH MUST use one of the specified values: 'Yes', 'No', 'Not Specified in JD', 'Cannot Determine', 'N/A'. Use 'No' if the resume clearly does NOT meet a requirement explicitly stated in JD. Use 'Not Specified in JD' if the JD does not mention that requirement. Use 'Cannot Determine' if the JD specifies a requirement but the resume provides insufficient information to confirm. Use 'N/A' for 'Other Specific Requirements Met' if no other specific requirements are found in the JD.\n"
        "4.  Each item under STRENGTHS MUST be a bullet point starting with '- ' (a hyphen followed by a single space).\n"
        "5.  Ensure there are blank lines separating OVERALL_SCORE, CRITERIA_SCORES, HARD_REQUIREMENTS_MATCH, and STRENGTHS sections as shown in the example format.\n"
        "6.  Do NOT add any introductory or concluding sentences or phrases around these structured blocks that are not part of the bullet points themselves.\n"
        "7.  The content for strengths should be concise, professional, and directly relevant to the comparison between the resume and the job description."
        "8.  **CRITICAL: DO NOT include any 'AREAS_FOR_IMPROVEMENT' section or similar constructive feedback. Only provide STRENGTHS.**"
    )
    try:
        response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are a highly precise recruitment AI. You are an expert in detailed resume analysis against job descriptions and strictly follow output formatting instructions."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,  # Increased max_tokens slightly for more output
        )
        content = response.choices[0].message.content

        overall_score_match = re.search(r"OVERALL_SCORE:\s*(\d+)/100", content)
        overall_score = int(overall_score_match.group(1)) if overall_score_match else 0

        criteria_scores = {}
        criteria_lines = re.findall(r"^\s*([A-Za-z\s\/]+[A-Za-z]):\s*(\d+)/100", content, re.MULTILINE)
        for label, score in criteria_lines:
            cleaned_label = label.strip()
            if cleaned_label.upper() != "OVERALL_SCORE":
                criteria_scores[cleaned_label] = int(score)

        hard_requirements = {}
        # Regex to capture hard requirement lines
        hard_req_matches = re.search(r"HARD_REQUIREMENTS_MATCH:\s*\n((?:.|\n)*?)(?=\nSTRENGTHS:|\Z)", content,
                                     re.MULTILINE)
        if hard_req_matches:
            lines = hard_req_matches.group(1).strip().split('\n')
            for line in lines:
                parts = line.split(':')
                if len(parts) >= 2:
                    key = parts[0].strip()
                    value = ":".join(parts[1:]).strip()  # Rejoin parts in case value contains colons
                    hard_requirements[key] = value

        strengths_match = re.search(r"STRENGTHS:\s*\n((?:-\s*.*\n?)+?)(?=\n[A-Z_]+:|IMPORTANT INSTRUCTIONS:|\[END\]|$)",
                                    content, re.MULTILINE | re.DOTALL)
        parsed_strengths = strengths_match.group(
            1).strip() if strengths_match else "Not explicitly found or format incorrect."

        return {
            "analysis_raw": content,
            "overall_score": overall_score,
            "criteria_scores": criteria_scores,
            "hard_requirements_match": hard_requirements,  # Include new data
            "strengths_text": parsed_strengths,
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during AI scoring: {e}"
        )


def answer_follow_up_question(azure_openai_client: AzureOpenAI, deployment_name: str, messages: list) -> str:
    """Answers a follow-up question based on a conversation history."""
    try:
        response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=messages,
            max_tokens=1000,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sorry, I couldn't answer that question due to an AI processing error: {e}"
        )


def generate_interview_questions(azure_openai_client: AzureOpenAI, deployment_name: str, resume_text: str,
                                 jd_text: str) -> str:
    """Generates interview questions based on a candidate's resume and a job description."""
    prompt = (
        "You are an AI assistant acting as an expert interviewer. Based on the following resume and job description, "
        "generate 15 relevant and insightful interview questions for the candidate. "
        "Focus on clarifying their experience, assessing technical skills, understanding problem-solving abilities, and evaluating cultural fit for the role.\n"
        "Present the questions as a numbered list from 1 to 15. Ensure questions are open-ended and probe for specific examples (STAR method encouragement where applicable).\n\n"
        f"--- JOB DESCRIPTION ---\n{jd_text}\n\n"
        f"--- RESUME ---\n{resume_text}\n\n"
        "--- INTERVIEW QUESTIONS ---"
    )
    try:
        response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are an expert interviewer, skilled at generating insightful and probing questions based on resume and job description analysis."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=700,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sorry, I couldn't generate interview questions due to an AI processing error: {e}"
        )


def _parse_generated_questions(question_text: str) -> List[str]:
    """
    Parses a raw string of numbered questions (e.g., from LLM output) into a clean list of strings.
    Handles various numbering formats and cleans extra whitespace.
    """
    questions = []
    # Regex to capture content between numbers or until the end
    matches = re.finditer(r'^\s*\d+[\.\)]\s*(.*?)(?=\n\s*\d+[\.\)]|\n\n|\Z)', question_text, re.DOTALL | re.MULTILINE)

    parsed_matches = []
    for match in matches:
        question = match.group(1).strip()
        if question:
            parsed_matches.append(question)

    if not parsed_matches:  # Fallback if primary regex fails to find any matches
        # Simpler approach: split by newlines, then look for lines that might be questions (start with a number, then clean)
        lines = question_text.split('\n')
        for line in lines:
            line = line.strip()
            if re.match(r'^\d+[\.\)]\s*.+', line):
                questions.append(re.sub(r'^\d+[\.\)]\s*', '', line).strip())
            elif line:  # Add non-empty lines that don't match numbering as potential questions
                questions.append(line)
        return [q for q in questions if q]  # Filter out any empty strings
    else:
        return parsed_matches


def analyze_interview_questions(azure_openai_client: AzureOpenAI, deployment_name: str,
                                ai_generated_questions_text: str, conversation_transcript: str) -> dict:
    """
    Analyzes an interview transcript to identify which AI-generated questions were covered
    and which unique questions the interviewer asked.
    """
    # Parse the raw AI-generated questions into a clean list first
    ai_generated_questions_list = _parse_generated_questions(ai_generated_questions_text)

    # Format the parsed questions for the LLM prompt
    ai_questions_formatted_for_prompt = "\n".join([f"{i + 1}. {q}" for i, q in enumerate(ai_generated_questions_list)])

    prompt = (
        "You are an expert interviewer and interview analysis AI. Your task is to analyze a conversation transcript "
        "against a list of pre-generated interview questions.\n\n"
        "**Instructions:**\n"
        "1.  **Identify Covered Generated Questions:** From the 'PRE-GENERATED QUESTIONS' list, identify and list "
        "    ALL questions that were clearly asked or semantically covered by the interviewer in the 'INTERVIEW TRANSCRIPT'. "
        "    The exact phrasing does not need to match, but the essence of the question from the 'PRE-GENERATED QUESTIONS' list must be clearly addressed.\n"
        "2.  **Identify Uncovered Generated Questions:** From the 'PRE-GENERATED QUESTIONS' list, identify and list "
        "    ALL questions that were *not* covered by the interviewer in the transcript.\n"
        "3.  **Identify Interviewer's Own Questions:** List any distinct questions asked by the interviewer in the "
        "    'INTERVIEW TRANSCRIPT' that are *not* semantically similar to any of the 'PRE-GENERATED QUESTIONS'. "
        "    Focus only on explicit questions ending in '?' or clear interrogative phrases from the interviewer's side.\n\n"
        "**PRE-GENERATED QUESTIONS (Exactly as provided, use these for comparison):**\n"
        f"{ai_questions_formatted_for_prompt}\n\n"  # Use the parsed and formatted list
        "**INTERVIEW TRANSCRIPT:**\n"
        f"{conversation_transcript}\n\n"
        "**OUTPUT FORMAT (Strict Adherence):**\n\n"
        "COVERED_GENERATED_QUESTIONS:\n"
        "- [Full text of AI-generated question 1 that was covered]\n"
        "- [Full text of AI-generated question 2 that was covered]\n"
        "...\n\n"
        "UNCOVERED_GENERATED_QUESTIONS:\n"
        "- [Full text of AI-generated question 1 that was NOT covered]\n"
        "- [Full text of AI-generated question 2 that was NOT covered]\n"
        "...\n\n"
        "INTERVIEWER_OWN_QUESTIONS:\n"
        "- [Full text of interviewer's unique question 1]\n"
        "- [Full text of interviewer's unique question 2]\n"
        "..."
    )
    try:
        response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are a precise interview analysis AI. You categorize questions based on a given list and transcript content, strictly adhering to output formats. Do not hallucinate or create new questions for coverage analysis."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=1500,
        )
        content = response.choices[0].message.content.strip()

        def parse_section(section_name, text_content):
            questions = []
            match = re.search(rf"{section_name}:\s*\n((?:-\s*.*\n?)+?)(?=\n[A-Z_]+:|\n\Z|$)", text_content,
                              re.MULTILINE | re.DOTALL)
            if match:
                lines = match.group(1).strip().split('\n')
                for line in lines:
                    if line.strip().startswith('- '):
                        questions.append(line[2:].strip())
            return questions

        covered_generated_questions = parse_section("COVERED_GENERATED_QUESTIONS", content)
        uncovered_generated_questions = parse_section("UNCOVERED_GENERATED_QUESTIONS", content)
        interviewer_own_questions = parse_section("INTERVIEWER_OWN_QUESTIONS", content)

        return {
            "analysis_raw": content,
            "covered_generated_questions": covered_generated_questions,
            "uncovered_generated_questions": uncovered_generated_questions,
            "interviewer_own_questions": interviewer_own_questions,
            "original_ai_generated_count": len(ai_generated_questions_list)  # Add this for debugging/verification
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during interview question analysis: {e}"
        )


def evaluate_candidate_responses_holistically(
        azure_openai_client: AzureOpenAI,
        deployment_name: str,
        all_questions_asked: list[str],  # This list should now only contain actually asked questions
        conversation_transcript: str,
        jd_text: str,
        resume_text: str
) -> dict:
    """
    Evaluates the candidate's responses to all questions asked in the interview transcript,
    and provides an overall interview performance score and summary.
    """
    if not all_questions_asked:
        return {
            "individual_evaluations": [],
            "overall_interview_score": 0,
            "overall_interview_summary": "No questions were asked or evaluated."
        }

    questions_list_formatted = "\n".join([f"{i + 1}. {q}" for i, q in enumerate(all_questions_asked)])

    prompt = (
        "You are an expert interview evaluator. Your task is to meticulously evaluate the candidate's response "
        "to EACH question identified as asked during the interview. "
        "Use the provided Job Description and Candidate Resume as context for evaluation.\n\n"
        "**For each question, provide:**\n"
        "1.  The full text of the question.\n"
        "2.  A concise summary of the candidate's relevant response from the transcript.\n"
        "3.  A score for the response (out of 10), considering the following criteria:\n"
        "    -   **Relevance:** How directly did the candidate answer the question?\n"
        "    -   **Depth/Specificity:** How detailed and specific was the answer? Did it provide concrete examples?\n"
        "    -   **Technical Accuracy:** If technical, was the information accurate and well-explained?\n"
        "    -   **Clarity/Articulation:** How clear and well-articulated was the response?\n"
        "    -   **Alignment with JD/Resume:** How well did the response demonstrate skills/experience relevant to the JD and mentioned in the resume?\n"
        "4.  A **brief rationale** (1-2 sentences) for the score, highlighting strengths and weaknesses of the response.\n\n"
        "**After evaluating all individual questions, provide an overall assessment:**\n"
        "5.  An **Overall Interview Performance Score** (out of 100), based on all responses.\n"
        "6.  A **Concise Overall Summary** (2-4 sentences) of the candidate's interview performance, highlighting key strengths and areas (if any) where the interview performance could have been stronger, considering the JD and Resume.\n\n"
        "**IMPORTANT:** If a question was listed as 'asked' but no clear answer is present in the transcript for that specific question, indicate 'No clear response found' for the summary and score 0/10 with rationale.\n\n"
        "--- QUESTIONS ASKED IN INTERVIEW ---\n"
        f"{questions_list_formatted}\n\n"
        "--- INTERVIEW TRANSCRIPT ---\n"
        f"{conversation_transcript}\n\n"
        "--- JOB DESCRIPTION ---\n"
        f"{jd_text}\n\n"
        "--- CANDIDATE RESUME ---\n"
        f"{resume_text}\n\n"
        "**OUTPUT FORMAT (Strict Adherence):**\n"
        "--- EVALUATION START ---\n"
        "Question: [Full text of question 1]\n"
        "Response Summary: [Concise summary of candidate's relevant answer]\n"
        "Score: X/10\n"
        "Rationale: [Brief explanation for score based on criteria]\n"
        "---\n"
        "Question: [Full text of question 2]\n"
        "Response Summary: [Concise summary of candidate's relevant answer]\n"
        "Score: Y/10\n"
        "Rationale: [Brief explanation for score based on criteria]\n"
        "---\n"
        "...\n"
        "--- OVERALL INTERVIEW PERFORMANCE ---\n"
        "Overall Score: Z/100\n"
        "Overall Summary: [Concise 2-4 sentence summary of performance]\n"
        "--- EVALUATION END ---"
    )

    try:
        response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are an expert interview evaluator, highly skilled at analyzing interview transcripts, summarizing responses, and providing precise scores and rationales based on job descriptions and resumes."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=3500,
        )
        content = response.choices[0].message.content.strip()

        individual_evaluations = []
        overall_interview_score = 0
        overall_interview_summary = "N/A"

        overall_score_match = re.search(r"Overall Score:\s*(\d+)/100", content)
        overall_summary_match = re.search(r"Overall Summary:\s*(.*?)(?=\n--- EVALUATION END ---|$)", content, re.DOTALL)

        if overall_score_match:
            overall_interview_score = int(overall_score_match.group(1))
        if overall_summary_match:
            overall_interview_summary = overall_summary_match.group(1).strip()

        individual_blocks = re.findall(
            r"Question: (.*?)\nResponse Summary: (.*?)\nScore: (\d+)/10\nRationale: (.*?)(?=\n---\n|--- OVERALL INTERVIEW PERFORMANCE ---|$)",
            content, re.DOTALL)

        for block in individual_blocks:
            question = block[0].strip()
            response_summary = block[1].strip()
            score = int(block[2])
            rationale = block[3].strip()
            individual_evaluations.append({
                "question": question,
                "response_summary": response_summary,
                "score": score,
                "rationale": rationale
            })
        return {
            "individual_evaluations": individual_evaluations,
            "overall_interview_score": overall_interview_score,
            "overall_interview_summary": overall_interview_summary
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error during holistic response evaluation: {e}"
        )


def detect_ai_resume(azure_openai_client: AzureOpenAI, deployment_name: str, resume_text: str,
                     include_explanation: bool) -> dict:
    """
    Analyzes a resume and determines if it's AI-generated or human-written, with optional explanation.
    """
    if azure_openai_client is None:
        raise HTTPException(status_code=500,
                            detail="Azure OpenAI client not initialized. Check server logs for details.")

    if not resume_text:
        raise HTTPException(status_code=400,
                            detail="No text extracted from resume. The file might be empty or unreadable.")

    initial_prompt = f"""
    You are an AI Resume Detector.

    Your task is to analyze a given resume and determine whether it was generated by an AI or written by a human.

    Evaluate the resume based on the following criteria:

    1.  **Formatting Consistency**: Check layout structure, alignment, font usage, and section organization.
    2.  **Language Use**: Analyze tone, vocabulary diversity, sentence complexity, and naturalness of expression.
    3.  **Detail Depth**: Evaluate specificity and contextual richness of job descriptions, achievements, and skills.
    4.  **Error Detection**: Identify grammatical, typographical, and syntactical errors.

    Return the following output in a clear, line-by-line format. Do NOT include any explanations in this initial response.

    Classification: [AI-Generated/Human-Written]
    Overall Confidence Score: [0-100]
    Formatting Consistency Score: [0-100]
    Language Use Score: [0-100]
    Detail Depth Score: [0-100]
    Error Detection Score: [0-100]

    Resume Text:
    {resume_text}
    """

    try:
        initial_response = azure_openai_client.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system",
                 "content": "You are your task is to determine whether the given resume is AI-generated and provide scores."},
                {"role": "user", "content": initial_prompt}
            ],
            max_tokens=200
        )

        analysis_content = ""
        if initial_response.choices and initial_response.choices[0].message and initial_response.choices[
            0].message.content:
            analysis_content = initial_response.choices[0].message.content
        else:
            raise HTTPException(status_code=500, detail="No concise analysis content received from AI.")

        classification = re.search(r"Classification: (.*)", analysis_content)
        overall_score = re.search(r"Overall Confidence Score: (\d+)", analysis_content)
        fc_score = re.search(r"Formatting Consistency Score: (\d+)", analysis_content)
        lu_score = re.search(r"Language Use Score: (\d+)", analysis_content)
        dd_score = re.search(r"Detail Depth Score: (\d+)", analysis_content)
        ed_score = re.search(r"Error Detection Score: (\d+)", analysis_content)

        classification_val = classification.group(1).strip() if classification else "N/A"
        overall_score_val = int(overall_score.group(1).strip()) if overall_score else "N/A"
        fc_score_val = int(fc_score.group(1).strip()) if fc_score else "N/A"
        lu_score_val = int(lu_score.group(1).strip()) if lu_score else "N/A"
        dd_score_val = int(dd_score.group(1).strip()) if dd_score else "N/A"
        ed_score_val = int(ed_score.group(1).strip()) if ed_score else "N/A"

        response_data = {
            "classification": classification_val,
            "overall_confidence_score": overall_score_val,
            "formatting_consistency_score": fc_score_val,
            "language_use_score": lu_score_val,
            "detail_depth_score": dd_score_val,
            "error_detection_score": ed_score_val
        }

        if include_explanation:
            explanation_prompt = f"""
            Based on the previous analysis of the following resume, which was classified as '{classification_val}' with an overall confidence score of {overall_score_val}% and individual scores as follows:
            - Formatting Consistency: {fc_score_val}%
            - Language Use: {lu_score_val}%
            - Detail Depth: {dd_score_val}%
            - Error Detection: {ed_score_val}%

            Please provide a detailed explanation for each of these scores and the overall classification. Elaborate on the specific aspects of the resume that led to these conclusions, referencing the criteria: Formatting Consistency, Language Use, Detail Depth, and Error Detection.

            Resume Text:
            {resume_text}
            """
            explanation_response = azure_openai_client.chat.completions.create(
                model=deployment_name,
                messages=[
                    {"role": "system", "content": "Provide a detailed explanation for the resume analysis scores."},
                    {"role": "user", "content": explanation_prompt}
                ],
                max_tokens=2000  # Increased max_tokens significantly
            )

            if explanation_response.choices and explanation_response.choices[0].message and \
                    explanation_response.choices[0].message.content:
                response_data["explanation"] = explanation_response.choices[0].message.content
            else:
                response_data["explanation"] = "Could not generate detailed explanation."

        return {"status": "success", "data": response_data}

    except Exception as e:
        print(f"An unexpected error occurred during AI detection: {e}")
        raise HTTPException(status_code=500,
                            detail=f"An unexpected error occurred during AI detection processing or AI analysis: {str(e)}")
