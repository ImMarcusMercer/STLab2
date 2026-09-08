from dataclasses import dataclass
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    api_base_url: str
    timeout_seconds: float

    @classmethod
    def load(cls):
        config_root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
        load_dotenv(config_root / '.env')
        url = os.getenv('FRONTEND_API_BASE_URL', 'http://127.0.0.1:8000/api/v1').rstrip('/')
        parsed = urlparse(url)
        if parsed.scheme not in ('http', 'https') or not parsed.netloc:
            raise RuntimeError('FRONTEND_API_BASE_URL must be a valid HTTP(S) URL.')
        try:
            timeout = float(os.getenv('FRONTEND_REQUEST_TIMEOUT_SECONDS', '15'))
        except ValueError as exc:
            raise RuntimeError('FRONTEND_REQUEST_TIMEOUT_SECONDS must be numeric.') from exc
        if not 1 <= timeout <= 120:
            raise RuntimeError('Request timeout must be between 1 and 120 seconds.')
        return cls(url, timeout)
