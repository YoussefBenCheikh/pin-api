from pydantic import BaseModel
from datetime import datetime

class PinRequest(BaseModel):
    access_token: str
    board_id: str
    title: str
    description: str
    link: str
    image_url: str
    scheduled_time: datetime
