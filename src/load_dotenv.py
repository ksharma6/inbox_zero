from pathlib import Path
import os
from dotenv import load_dotenv

def load_dotenv_helper():
    if load_dotenv():
        print("Successfully loaded .env (default search).")
    else:
        project_root_env_alt = Path.cwd() / ".env" 
        if project_root_env_alt.exists():
            load_dotenv(dotenv_path=project_root_env_alt)
            print(f"Loaded .env from CWD: {project_root_env_alt}")
        else:
            print("Warning: .env file not found via default search or in CWD.")