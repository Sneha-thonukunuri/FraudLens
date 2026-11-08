# FraudLens
Multimodal LLM scam detector: text, screenshots, URLs, conversations -> risk score + explanation.

## Setup
```
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
pytest                                   # no API key or network needed
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

## LLM configuration (Member 1)
`nlp/analyzer.py` calls an LLM when `.env` has `LLM_API_KEY` and `LLM_MODEL`
(`LLM_PROVIDER=anthropic` by default, or `openai` for OpenAI-compatible APIs;
optional `LLM_BASE_URL`). The reply is validated into an `AnalysisResult`.
If no key is set, or a call/parse fails, the keyword analyzer is used instead.
Tests never call a real LLM.

## OCR
`vision/analyzer.py` needs the Tesseract binary. It is found on PATH, at the default
Windows install path, or at `TESSERACT_CMD` from `.env`.

## Evaluation
`python -m system.evaluate` compares approaches on `data/eval_set.jsonl`
(synthetic and small: indicative only, not real-world accuracy).
