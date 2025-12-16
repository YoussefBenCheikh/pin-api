from fastapi import APIRouter
from schemas.board_schema import BoardCreateRequest, BoardResponse
from services.board_service import create_board, get_boards

router = APIRouter(prefix="/boards", tags=["boards"])

@router.post("/", response_model=BoardResponse)
def api_create_board(board: BoardCreateRequest):
    return create_board(board)

@router.get("/")
def api_get_boards(access_token: str):
    return get_boards(access_token)
