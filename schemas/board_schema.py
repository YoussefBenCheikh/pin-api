from pydantic import BaseModel

class BoardCreateRequest(BaseModel):
    access_token: str       # Pinterest token included in request
    name: str
    description: str = None
    privacy: str = "public"  # "public" or "secret"

class BoardResponse(BaseModel):
    id: str
    name: str
    description: str = None