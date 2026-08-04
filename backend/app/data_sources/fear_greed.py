import httpx

from app.config import ALTERNATIVE_ME_BASE

_client = httpx.AsyncClient(base_url=ALTERNATIVE_ME_BASE, timeout=10.0)


async def get_fear_greed_index() -> dict:
    resp = await _client.get("/fng/", params={"limit": 1})
    resp.raise_for_status()
    data = resp.json()["data"][0]
    return {"value": int(data["value"]), "classification": data["value_classification"]}
