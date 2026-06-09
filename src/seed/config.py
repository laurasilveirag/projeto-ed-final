import os
from dotenv import load_dotenv

load_dotenv()

DB_HOST: str = os.environ.get("POSTGRES_HOST", "localhost")
DB_PORT: int = int(os.environ.get("POSTGRES_PORT", "5432"))
DB_NAME: str = os.environ.get("POSTGRES_DB", "streaming")
DB_USER: str = os.environ.get("POSTGRES_USER", "streaming")
DB_PASSWORD: str = os.environ.get("POSTGRES_PASSWORD", "streaming123")
