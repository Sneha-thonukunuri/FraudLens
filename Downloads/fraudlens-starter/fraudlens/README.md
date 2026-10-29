# FraudLens
Multimodal LLM scam detector: text, screenshots, URLs, conversations -> risk score + explanation.

## Setup
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
pytest                                   # should pass on the mocks
uvicorn system.api:app --reload          # API at http://127.0.0.1:8000/docs
streamlit run system/dashboard.py        # dashboard
```

## Ownership
| Member | Folder | Entry points |
|---|---|---|
| 1 LLM/NLP | `nlp/` | `analyze_text`, `analyze_conversation` |
| 2 CV/Multimodal | `vision/` | `analyze_screenshot` |
| 3 System/Eval | `system/` | `analyze_url`, `fuse`, API, dashboard |

`common/schema.py` is the shared contract. Discuss before changing it.

## Rules
- Keep function signatures unchanged; replace the mock internals.
- Each member works on their own branch and opens a PR to `main`.
- Add a test in `tests/` for every new function.
