import asyncio
import re

import anthropic
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import ANTHROPIC_MODEL
from app.data_sources import binance
from app.engine.feature_builder import build_features
from app.engine.reasoning import SYSTEM_PROMPT

router = APIRouter()
_client = anthropic.Anthropic()

_SYMBOL_RE = re.compile(r"\b([A-Z]{2,10})(USDT)?\b")
_KNOWN_QUOTE = "USDT"


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    symbols_used: list[str]


async def _resolve_symbols(question: str) -> list[str]:
    candidates = {m.group(1) for m in _SYMBOL_RE.finditer(question.upper())}
    candidates.discard(_KNOWN_QUOTE)
    symbols = [f"{c}{_KNOWN_QUOTE}" for c in candidates]

    if not symbols:
        tickers = await binance.get_24h_tickers()
        usdt_pairs = [t for t in tickers if t["symbol"].endswith("USDT")]
        usdt_pairs.sort(key=lambda t: abs(float(t["priceChangePercent"])), reverse=True)
        symbols = [t["symbol"] for t in usdt_pairs[:3]]

    return symbols[:5]


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    symbols = await _resolve_symbols(req.question)

    feature_sets = await asyncio.gather(
        *(build_features(s) for s in symbols), return_exceptions=True
    )
    valid = {
        s: f for s, f in zip(symbols, feature_sets) if not isinstance(f, Exception)
    }

    import json

    context = json.dumps(valid, indent=2, default=str)
    prompt = (
        f"User question: {req.question}\n\n"
        f"Market data for relevant pairs:\n{context}\n\n"
        "Answer the user's question directly, grounded only in this data. "
        "Never claim certainty about future price movement."
    )

    response = _client.messages.create(
        model=ANTHROPIC_MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    answer = next((b.text for b in response.content if b.type == "text"), "")

    return AskResponse(answer=answer, symbols_used=list(valid.keys()))
