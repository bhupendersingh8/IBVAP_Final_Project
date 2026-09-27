# Contributing to IBVAP

Thank you for contributing to the Intelligent Border Video Analytics Platform.

## Ground Rules

1. **Never commit secrets** — no `.env`, passwords, API keys, camera credentials, certificates, or private keys.
2. **Never commit video footage** — no `.mp4`, `.avi`, or any recorded surveillance material.
3. **Never commit ML model weights** — no `.pt`, `.onnx`, `.engine` files.
4. **Never fabricate benchmark results** — all performance numbers must come from actual measured runs.
5. **Never claim production readiness** without formal security assessment and validation.

## Branch Strategy

```
main          ← stable, demo-ready
develop       ← integration branch
feature/<name> ← individual feature branches
fix/<name>    ← bug fixes
```

## Code Style

- **Python:** PEP 8, type hints required, docstrings on all public functions
- **TypeScript:** strict mode, ESLint, Prettier
- **Commits:** conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`)

## Pull Request Checklist

- [ ] Tests pass (`pytest tests/`)
- [ ] No secrets introduced
- [ ] Type hints present (Python)
- [ ] Docstrings on new public functions
- [ ] THIRD_PARTY_LICENSES.md updated if new dependency added
- [ ] `.env.example` updated if new env variable added

## Adding a New Dependency

1. Add to the appropriate `requirements/*.txt`
2. Update `THIRD_PARTY_LICENSES.md` with name, version, license, and commercial-use status
3. Verify the license is compatible with the project's intended use

## Adding a New ML Model

1. Create an adapter in `services/detection/` or relevant service
2. Never hard-code the model vendor in application logic
3. Document licensing in `docs/MODEL_GUIDE.md`
4. Add entry to `ml/models/model_registry.json`
