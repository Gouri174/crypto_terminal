import json

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import ANTHROPIC_MODEL
from app.engine.ask_router import gather_context

router = APIRouter()
_client = anthropic.Anthropic(timeout=120.0)

_RESEARCH_SYSTEM_PROMPT = """You are a research analyst for a crypto trading system, not a signal \
generator and not a general chatbot. You answer questions using ONLY the JSON data block the user \
provides — that data was pulled directly from this system's own trade database (TradeOutcome), its \
append-only prediction-validation log (PredictionSnapshot), and its calibration/diagnostic reports. \
It is not live market data and not something you fetched yourself.

Rules:
- Never state a number that is not present in the provided data. If the data doesn't cover something \
the question asks about, say so plainly instead of estimating or guessing.
- If a report section contains a "note" saying the sample size is too small, say that explicitly \
rather than drawing a conclusion from it anyway.
- Cite the actual figures you're using (win rate, sample size, return %) so the answer is checkable \
against the data, not a vibe.
- Never predict future price movement or claim certainty about what a trade will do.
- If the data shows the system is unprofitable or a pattern is bad news, say so directly — do not \
soften or hide an unflattering result.
- Keep answers focused and grounded; a short answer citing real numbers beats a long one that pads \
around them."""


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    categories_matched: list[str]
    symbols_used: list[str]
    data: dict


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    """Research-assistant endpoint: classifies the question deterministically
    (app/engine/ask_router.py), pulls only real data from the existing
    TradeOutcome/PredictionSnapshot/report functions for the matched
    categories, and hands THAT — not live market features, not a free-form
    prompt — to Claude to explain. Claude never sees anything this system
    hasn't already computed deterministically."""
    result = gather_context(req.question)

    context_json = json.dumps(result.data, indent=2, default=str)
    prompt = (
        f"User question: {req.question}\n\n"
        f"Matched categories: {result.categories or ['none — general snapshot']}\n"
        f"Time window: last {result.window_days} day(s)\n\n"
        f"Data pulled from the system's own database:\n{context_json}\n\n"
        "Answer the question directly using only this data, per the rules in your system prompt."
    )

    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=1500,
        system=_RESEARCH_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = next((b.text for b in response.content if b.type == "text"), "")

    return AskResponse(
        answer=answer,
        categories_matched=result.categories,
        symbols_used=result.symbols,
        data=result.data,
    )
