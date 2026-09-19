"""Container HEALTHCHECK: exit 0 if the API answers /health."""
import os
import sys
import urllib.request

try:
    urllib.request.urlopen(f"http://localhost:{os.getenv('PORT', '8000')}/health", timeout=3)
except Exception:
    sys.exit(1)
