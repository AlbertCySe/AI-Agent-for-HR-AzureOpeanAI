import os
from dotenv import load_dotenv

# Get the directory of the current script (check_env.py)
script_dir = os.path.dirname(__file__)
dotenv_path = os.path.join(script_dir, "credit.env")

print(f"Attempting to load .env from: {dotenv_path}")

# Check if the file exists
if not os.path.exists(dotenv_path):
    print(f"ERROR: The .env file does NOT exist at {dotenv_path}")
    print("Please ensure it is named exactly '.env' and is in the 'backend' directory.")
    print("On Windows, ensure 'File name extensions' are visible in File Explorer (View tab -> Show/hide).")
else:
    print(f"SUCCESS: The .env file EXISTS at {dotenv_path}")
    # Try to load it
    if load_dotenv(dotenv_path):
        print("SUCCESS: .env file loaded successfully by python-dotenv.")
        # Verify a key
        azure_key = os.getenv("AZURE_OPENAI_KEY")
        if azure_key:
            print(f"SUCCESS: AZURE_OPENAI_KEY is loaded (first 5 chars): {azure_key[:5]}*****")
        else:
            print("WARNING: AZURE_OPENAI_KEY is NOT found in .env or is empty. Please check its content.")
    else:
        print("ERROR: python-dotenv could NOT load the .env file.")
        print("This might mean the file is empty, corrupted, or has incorrect permissions.")
        print("Please open the .env file in a text editor and ensure it contains your credentials.")

