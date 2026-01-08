import uuid
from langgraph_sdk import Auth

auth = Auth()


@auth.authenticate
async def get_user(headers: dict):
    """
    模擬認證流程。
    在實際環境中，你會檢查 JWT 或 API Key。
    這裡我們隨機產生一個 User ID。
    """
    # 這裡我們隨機產生一個，或是從自訂 Header 拿
    user_id = headers.get("x-user-id", f"user-{uuid.uuid4().hex[:8]}")

    return {"identity": user_id, "permissions": ["read", "write"]}
