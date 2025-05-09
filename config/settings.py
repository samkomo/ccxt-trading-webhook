import os
from dotenv import load_dotenv

# Load environment variables from a .env file (if present)
load_dotenv()

# Required for all requests
WEBHOOK_SECRET = os.getenv('WEBHOOK_SECRET')

# Optional default exchange credentials (used only if dynamic ones aren't supplied)
DEFAULT_EXCHANGE = os.getenv('DEFAULT_EXCHANGE', 'binance')
DEFAULT_API_KEY = os.getenv('DEFAULT_API_KEY')
DEFAULT_API_SECRET = os.getenv('DEFAULT_API_SECRET')

# For rate limiting, logging, etc. (expand as needed)
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
