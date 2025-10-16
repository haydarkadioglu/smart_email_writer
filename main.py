import os
from dotenv import load_dotenv

from ui.app import run_app

# Load environment variables from .env and then .env.local (local overrides)
load_dotenv(dotenv_path=".env", override=False)
load_dotenv(dotenv_path=".env.local", override=False)


if __name__ == "__main__":
    run_app()
