"""Run the checked-in Postman requests and assertions against a local HTTP server.

Requires Node.js 22+ for built-in fetch. Credentials are passed privately over stdin.
Usage: python scripts/run_demo.py [http://127.0.0.1:8000/api/v1]
"""
import json
import os
from pathlib import Path
import subprocess
import sys
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
load_dotenv(root / '.env')
if not os.getenv('DEMO_PASSWORD'):
    raise SystemExit('Set DEMO_PASSWORD in your local .env first.')
payload = {'base': sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8000/api/v1',
           'demo_password': os.environ['DEMO_PASSWORD']}
result = subprocess.run(['node', str(root / 'scripts/run_collection.mjs')],
                        input=json.dumps(payload), text=True, cwd=root)
raise SystemExit(result.returncode)
