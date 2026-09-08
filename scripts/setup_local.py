"""Generate private local configuration without changing existing configuration."""
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
destination = root / '.env'
if destination.exists():
    print('.env already exists; configuration preserved.')
else:
    content = (root / '.env.example').read_text(encoding='utf-8')
    content = content.replace('replace-with-a-random-local-secret', secrets.token_urlsafe(48))
    content = content.replace('DEMO_PASSWORD=\n', 'DEMO_PASSWORD=' + secrets.token_urlsafe(24) + '\n')
    destination.write_text(content, encoding='utf-8')
    print('Created .env with private random values. Read it locally for DEMO_PASSWORD.')
