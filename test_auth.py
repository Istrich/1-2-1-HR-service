import asyncio
from app.core.security import get_current_user, create_token
from fastapi import Request

async def main():
    token = create_token("admin")
    scope = {
        "type": "http",
        "headers": [(b"authorization", f"Bearer {token}".encode("utf-8"))],
        "query_string": b""
    }
    class MockReceive:
        async def __call__(self): return {}
    req = Request(scope, MockReceive())
    user = await get_current_user(req)
    print("User is:", user)

asyncio.run(main())
