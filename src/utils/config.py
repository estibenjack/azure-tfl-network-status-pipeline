import os
from dotenv import load_dotenv

load_dotenv()

# API credentials
LINE_API_KEY = os.environ.get("TFL_LINE_API_KEY")
STOPPOINT_API_KEY = os.environ.get("TFL_STOPPOINT_API_KEY")

# API base URLs
TFL_BASE_URL = "https://api.tfl.gov.uk"
TFL_MODES = 'tube,dlr,overground,elizabeth-line'
