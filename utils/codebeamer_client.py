import os
import httpx
from utils.errors import RateLimited


class CodebeamerClient:
    def __init__(self):
        self.base_url = os.getenv("CODEBEAMER_URL")
        
    async def request(self, token: str, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": token
            }
        ) as client:
            resp = await client.request(method=method, path=path, **kwargs)

        if resp.status_code == 429:
            retry = int(resp.headers.get("Retry-After", 30))
            raise RateLimited(retry)
        
        resp.raise_for_status()
        return resp.json()
    