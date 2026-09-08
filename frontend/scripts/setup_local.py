from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    print('frontend/.env already exists; configuration preserved.')
else:
    target.write_text((root / '.env.example').read_text(encoding='utf-8'), encoding='utf-8')
    print('Created frontend/.env for the local API URL.')
