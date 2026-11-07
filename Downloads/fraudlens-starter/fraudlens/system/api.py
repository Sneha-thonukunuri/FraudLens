# """MEMBER 3 owns this file. Run from repo root: uvicorn system.api:app --reload"""
# from typing import List, Optional
# from fastapi import FastAPI, File, UploadFile
# from pydantic import BaseModel
# from common.schema import Verdict
# from nlp.analyzer import analyze_text, analyze_conversation
# from vision.analyzer import analyze_screenshot
# from system.url_analyzer import analyze_url
# from system.fusion import fuse

# app = FastAPI(title="FraudLens")


# @app.get("/")
# def root():
#     return {"service": "FraudLens", "status": "ok"}


# class AnalyzeRequest(BaseModel):
#     text: Optional[str] = None
#     messages: Optional[List[str]] = None
#     url: Optional[str] = None


# @app.get("/health")
# def health():
#     return {"status": "ok"}


# @app.post("/analyze", response_model=Verdict)
# def analyze(req: AnalyzeRequest):
#     results = []
#     if req.text:
#         results.append(analyze_text(req.text))
#     if req.messages:
#         results.append(analyze_conversation(req.messages))
#     if req.url:
#         results.append(analyze_url(req.url))
#     return fuse(results)


# @app.post("/analyze/screenshot", response_model=Verdict)
# async def analyze_image(file: UploadFile = File(...)):
#     return fuse([analyze_screenshot(await file.read())])


"""MEMBER 3 owns this file. Run from repo root: uvicorn system.api:app --reload"""
import logging
from typing import List, Optional
from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from common.schema import Verdict
from nlp.analyzer import analyze_text, analyze_conversation
from vision.analyzer import analyze_screenshot
from system.url_analyzer import analyze_url
from system.fusion import fuse

logger = logging.getLogger("fraudlens.api")
app = FastAPI(title="FraudLens")

MAX_IMAGE_BYTES = 5 * 1024 * 1024   # 5 MB upload limit
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg"}


@app.get("/")
def root():
    return {"service": "FraudLens", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "ok"}


class AnalyzeRequest(BaseModel):
    text: Optional[str] = Field(None, max_length=10000)
    messages: Optional[List[str]] = Field(None, max_length=100)
    url: Optional[str] = Field(None, max_length=2048)


def _run(name: str, func, arg, results: list, errors: list):
    """Run one analyzer. If it crashes, record the failure instead of crashing the API."""
    try:
        results.append(func(arg))
    except Exception:
        logger.exception("Analyzer '%s' failed", name)   # details stay in the server log
        errors.append(name)


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    results, errors = [], []
    if req.text and req.text.strip():
        _run("text", analyze_text, req.text, results, errors)
    if req.messages:
        _run("conversation", analyze_conversation, req.messages, results, errors)
    if req.url and req.url.strip():
        _run("url", analyze_url, req.url, results, errors)
    return fuse(results, errors)


@app.post("/analyze/screenshot", response_model=Verdict)
async def analyze_image(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Only PNG or JPEG images are accepted.")
    data = await file.read(MAX_IMAGE_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="Image is too large (max 5 MB).")
    results, errors = [], []
    _run("screenshot", analyze_screenshot, data, results, errors)
    return fuse(results, errors)