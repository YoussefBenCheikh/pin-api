import requests
from schemas.board_schema import BoardCreateRequest

PINTEREST_API_BASE = "https://api-sandbox.pinterest.com/v5"

def create_board(board: BoardCreateRequest):
    url = f"{PINTEREST_API_BASE}/boards"
    headers = {"Authorization": f"Bearer {board.access_token}"}
    payload = {
        "name": board.name,
        "description": board.description,
        "privacy": board.privacy
    }
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    return response.json()

def get_boards(access_token: str):
    url = f"{PINTEREST_API_BASE}/boards"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json().get("items", [])
