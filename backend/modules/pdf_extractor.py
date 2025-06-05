import os
import sys
import io
import tempfile
from fastapi import UploadFile, HTTPException, status
from pdfminer.high_level import extract_text as extract_pdf_text_library
import pdfplumber # For AI detection's PDF handling

async def extract_text_from_resume_file(resume_file: UploadFile) -> str:
    """Extracts text from an uploaded .txt or .pdf resume file."""
    file_extension = os.path.splitext(resume_file.filename)[1].lower()

    if file_extension == ".txt":
        try:
            content = await resume_file.read()
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    elif file_extension == ".pdf":
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            temp_pdf.write(await resume_file.read())
            temp_pdf_path = temp_pdf.name
        try:
            return extract_pdf_text_library(temp_pdf_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Error extracting text from PDF: {e}. Ensure pdfminer.six is correctly installed and the PDF is not corrupted."
            )
        finally:
            if os.path.exists(temp_pdf_path):
                os.remove(temp_pdf_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported resume file format: '{file_extension}'. Please provide a .txt or .pdf file."
        )

async def extract_text_from_jd_file(jd_file: UploadFile) -> str:
    """Extracts text from an uploaded .txt job description file."""
    file_extension = os.path.splitext(jd_file.filename)[1].lower()

    if file_extension == ".txt":
        try:
            content = await jd_file.read()
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported Job Description file format: '{file_extension}'. Please provide a .txt file."
        )

async def extract_text_from_conversation_file(conversation_file: UploadFile) -> str:
    """Extracts text from an uploaded .txt conversation transcript file."""
    file_extension = os.path.splitext(conversation_file.filename)[1].lower()

    if file_extension == ".txt":
        try:
            content = await conversation_file.read()
            return content.decode("utf-8")
        except UnicodeDecodeError:
            return content.decode("latin-1")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported conversation file format: '{file_extension}'. Please provide a .txt file."
        )

def extract_text_from_pdf_bytes_for_detection(pdf_file_bytes: bytes) -> str:
    """
    Extracts text from PDF file bytes using pdfplumber, suppressing warnings.
    Used specifically by the AI detection endpoint.
    """
    text = ""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        temp_pdf.write(pdf_file_bytes)
        temp_pdf_path = temp_pdf.name

    original_stderr = sys.stderr
    sys.stderr = open(os.devnull, 'w')
    try:
        with pdfplumber.open(temp_pdf_path) as pdf:
            for page in pdf.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF for detection: {e}")
    finally:
        sys.stderr.close()
        sys.stderr = original_stderr
        if os.path.exists(temp_pdf_path):
            os.remove(temp_pdf_path)
