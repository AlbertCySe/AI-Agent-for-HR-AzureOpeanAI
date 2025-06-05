
# AI Resume Analyzer

This project provides a comprehensive AI-powered tool for analyzing candidate resumes against job descriptions, gaining interview insights, and evaluating candidate responses. It consists of a FastAPI backend for AI logic and a Streamlit frontend for the user interface.

---

## Features

- **Resume-to-Job Description Matching:** Analyze how well a candidate's resume aligns with a given job description.
- **Interview Insights:** Generate potential interview questions and insights based on the resume and job description.
- **Candidate Response Evaluation:** Evaluate candidate responses for interview questions.

---

## Development Tools and Environment

This project is developed and best run using:

- **Python 3.9+**: The core programming language.
- **PyCharm (Recommended IDE)**: Provides an integrated development environment with excellent support for Python, virtual environments, and debugging. You can also use other IDEs like VS Code or a text editor.
- **Virtual Environments**: Essential for managing project-specific Python dependencies, ensuring a clean and isolated development environment.

---

## File Map

\`\`\`
ai_resume_analyzer/
├── .venv/                     # Python Virtual Environment (created after setup)
├── backend/
│   ├── main.py                # FastAPI application entry point
│   ├── models.py              # Data models (Pydantic)
│   ├── service.py             # Core AI logic/orchestration
│   ├── modules/
│   │   ├── __init__.py        # Python package marker (MUST BE PRESENT AND EMPTY)
│   │   └── pdf_extractor.py   # PDF text extraction utility
│   └── .env                   # Environment variables (e.g., API keys, deployment names)
├── streamlit_app/
│   ├── __init__.py            # Python package marker (CRITICAL! MUST BE PRESENT AND EMPTY)
│   ├── app.py                 # Streamlit application entry point
│   ├── api_client.py          # Handles communication with FastAPI backend
│   └── utils.py               # Utility functions for Streamlit app
├── logs/                      # Directory for application logs (if configured)
├── .gitignore                 # Specifies intentionally untracked files to ignore
└── requirements.txt           # Lists all Python dependencies
\`\`\`

---

## Setup Instructions

### 1. Navigate to the Project Root

Open your terminal or command prompt and change your directory to the `ai_resume_analyzer` folder.

\`\`\`bash
cd "path/to/ai_resume_analyzer"
\`\`\`

### 2. Create a Virtual Environment

\`\`\`bash
python -m venv .venv
\`\`\`

### 3. Activate the Virtual Environment

**On Windows:**

\`\`\`bash
.venv\Scripts\activate
\`\`\`

**On macOS / Linux:**

\`\`\`bash
source .venv/bin/activate
\`\`\`

### 4. Install Dependencies

\`\`\`bash
pip install -r requirements.txt
\`\`\`

---

## Running the Application

### 1. Start the FastAPI Backend

\`\`\`bash
uvicorn backend.main:app --reload --port 8000
\`\`\`

### 2. Start the Streamlit Frontend

In a new terminal:

\`\`\`bash
streamlit run streamlit_app/app.py
\`\`\`

Visit [http://localhost:8501](http://localhost:8501) in your browser to use the app.

---

## Deactivating the Virtual Environment

\`\`\`bash
deactivate
\`\`\`

---

## Troubleshooting

If the virtual environment is not working:

1. **Deactivate Existing Environment:**

\`\`\`bash
deactivate
\`\`\`

2. **Delete the `.venv` Folder:**

**On Windows:**

\`\`\`bash
rmdir /s /q .venv
\`\`\`

**On macOS / Linux:**

\`\`\`bash
rm -rf .venv
\`\`\`

3. **Recreate and Reinstall:**

Follow the setup instructions again from Step 2.
