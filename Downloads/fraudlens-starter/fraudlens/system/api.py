"""MEMBER 3 owns this file. Run from repo root: uvicorn system.api:app --reload"""
from typing import List, Optional
from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from common.schema import Verdict
from nlp.analyzer import analyze_text, analyze_conversation
from vision.analyzer import analyze_screenshot
from system.url_analyzer import analyze_url
from system.fusion import fuse

app = FastAPI(title="FraudLens")


@app.get("/")
def root():
    return {"service": "FraudLens", "status": "ok"}


class AnalyzeRequest(BaseModel):
    text: Optional[str] = None
    messages: Optional[List[str]] = None
    url: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    results = []
    if req.text:
        results.append(analyze_text(req.text))
    if req.messages:
        results.append(analyze_conversation(req.messages))
    if req.url:
        results.append(analyze_url(req.url))
    return fuse(results)


@app.post("/analyze/screenshot", response_model=Verdict)
async def analyze_image(file: UploadFile = File(...)):
    return fuse([analyze_screenshot(await file.read())])
