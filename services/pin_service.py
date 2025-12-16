import requests
from schemas.pin_schema import PinRequest

def create_pin(pin: PinRequest):
    url = "https://api-sandbox.pinterest.com/v5/pins"
    headers = {"Authorization": f"Bearer {pin.access_token}"}
    payload = {
        "board_id": pin.board_id,
        "title": pin.title,
        "description": pin.description,
        "link": pin.link,
        "media_source": {"source_type": "image_url", "url": pin.image_url},
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code >= 400:
        print("❌ Error creating pin:", response.text)
    else:
        print("✅ Pin created:", response.json())
