# Secrets Policy

## Rules

1. **Never commit secrets to git** — enforced via `.gitignore` and pre-commit scan
2. **All secrets in `.env`** — load via `python-dotenv` or OS environment
3. **`.env.example`** contains only placeholder values, never real secrets
4. **Secret scanning** — run before every commit: `git grep -E "(password|secret|key|token)\s*=\s*['\"][^'\"]{8,}" -- "*.py" "*.yaml" "*.json"`

## Current Audit Result

- Regex scan result: **0 matches** ✅
- No hardcoded passwords in source code
- No hardcoded JWT secrets
- No API keys in source code

## Secrets Inventory

| Secret | Location | Rotation |
|--------|----------|---------|
| `IBVAP_JWT_SECRET` | `.env` (not committed) | Rotate every 90 days |
| Database password | `.env` (future PostgreSQL) | Rotate on breach |
| Camera RTSP credentials | `configs/cameras.yaml` local only | Per camera |

## Generation

```powershell
# Generate a 256-bit JWT secret:
[System.Convert]::ToBase64String([System.Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
```

## .env.example Template

```ini
IBVAP_JWT_SECRET=REPLACE_WITH_GENERATED_SECRET
APP_ENV=development
DATABASE_URL=sqlite+aiosqlite:///./data/ibvap_dev.db
CORS_ALLOWED_ORIGINS=["http://localhost:5173"]
```
