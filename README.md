# AI Resume Analyzer

This project provides a comprehensive AI-powered tool for analyzing candidate resumes against job descriptions, gaining interview insights, and evaluating candidate responses. It consists of a FastAPI backend for AI logic and a Streamlit frontend for the user interface.

---
## Features

* **Resume-to-Job Description Matching:** Analyze how well a candidate's resume aligns with a given job description.
* **Interview Insights:** Generate potential interview questions and insights based on the resume and job description.
* **Candidate Response Evaluation:** Evaluate candidate responses for interview questions.

---
## Development Tools and Environment

This project is developed and best run using:

* **Python 3.9+**: The core programming language.
* **PyCharm (Recommended IDE)**: Provides an integrated development environment with excellent support for Python, virtual environments, and debugging. You can also use other IDEs like VS Code or a text editor.
* **Virtual Environments**: Essential for managing project-specific Python dependencies, ensuring a clean and isolated development environment.

---
## File Map

ai_resume_analyzer/
├── .venv/                   # Python Virtual Environment (created after setup)
├── backend/
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # Data models (Pydantic)
│   ├── service.py           # Core AI logic/orchestration
│   ├── modules/
│   │   ├── init.py      # Python package marker (MUST BE PRESENT AND EMPTY)
│   │   └── pdf_extractor.py # PDF text extraction utility
│   └── .env                 # Environment variables (e.g., API keys, deployment names)
├── streamlit_app/
│   ├── init.py          # Python package marker (CRITICAL! MUST BE PRESENT AND EMPTY)
│   ├── app.py               # Streamlit application entry point
│   ├── api_client.py        # Handles communication with FastAPI backend
│   └── utils.py             # Utility functions for Streamlit app
├── logs/                    # Directory for application logs (if configured)
├── .gitignore               # Specifies intentionally untracked files to ignore
└── requirements.txt         # Lists all Python dependencies


---
## Setup Instructions

Follow these steps to set up the project on your local machine.

### 1. Navigate to the Project Root

Open your terminal or command prompt and change your directory to the `ai_resume_analyzer` folder. If you're using PyCharm, you can open a terminal directly within PyCharm (usually at the bottom of the window, named "Terminal") which will automatically be in your project root.

*COPY CODE*
cd "copy paste the location where the file 'ai_resume_analyzer' is located. Ex,. cd C:\Users\albert.j\PyCharmMiscProject\ai_resume_analyzer"
2. Create a Virtual Environment
It's highly recommended to use a virtual environment to manage dependencies.

*COPY CODE*

python -m venv .venv
3. Activate the Virtual Environment
On Windows (Command Prompt/PowerShell):

*COPY CODE*

.venv\Scripts\activate
On macOS / Linux (Bash/Zsh):

*COPY CODE*

source .venv/bin/activate
(You should see (.venv) or similar in your terminal prompt, indicating the environment is active.)

4. Install Dependencies
Install all required Python packages using pip:

*COPY CODE*

pip install -r requirements.txt
Running the Application
The application consists of two main parts: the FastAPI backend and the Streamlit frontend. Both need to be running concurrently.

1. Start the FastAPI Backend
Open your first terminal or command prompt (or a PyCharm terminal tab), navigate to the project root (if not already there), and ensure your virtual environment is activated. Then run:

*COPY CODE*

uvicorn backend.main:app --reload --port 8000
Keep this terminal open and running.

2. Start the Streamlit Frontend
Open your second terminal or command prompt (or another PyCharm terminal tab), navigate to the project root (if not already there), and ensure your virtual environment is activated. Then run:

*COPY CODE*

streamlit run streamlit_app/app.py
Once both servers are running, your Streamlit application should automatically open in your web browser (usually http://localhost:8501), and you can start using all the functionalities (AI detection, resume/JD analysis, interview analysis, and Q&A).

Deactivating the Virtual Environment
When you are done working on the project, you can deactivate your virtual environment in both terminals:

*COPY CODE*

deactivate
Troubleshooting: If the Virtual Environment (or Frontend) Doesn't Work
If you encounter issues like "unable to find the parent folder" or other errors related to the virtual environment not being recognized, your .venv might be corrupted or improperly set up. Follow these steps to rebuild it:

1. Deactivate Existing Environment (if active):
In your terminal, run:

*COPY CODE*

deactivate
2. Delete the Corrupted Virtual Environment:
Manually delete the entire .venv folder from your ai_resume_analyzer directory.

On Windows (in Command Prompt/PowerShell):

*COPY CODE*

rmdir /s /q .venv
On macOS / Linux (in Bash/Zsh):

*COPY CODE*

rm -rf .venv
3. Recreate and Reinstall (Follow Setup Instructions):
Now, go back to the "Setup Instructions" section above and start from Step 2 (Create a Virtual Environment). This will ensure a clean virtual environment is created and all dependencies are installed correctly within it.

"If you face any issues, Final option 'GEMINI' - https://g.co/gemini/share/a92867bd1e8e"
