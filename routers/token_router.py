import os
from fastapi import APIRouter, Request, HTTPException
from models import TokenRequest, ChatTokenRequest
from services import token_service

router = APIRouter()

async def authenticate_request(request: Request):
    if os.getenv('API_KEY'):
        PYTHON_APP_API_KEY = os.getenv('API_KEY')
        if request.headers.get("X-Api-Key") != PYTHON_APP_API_KEY:
            raise HTTPException(status_code=401, detail="Invalid API key")
    else:
        return

@router.post("/tokens")
async def count_tokens(token_request: TokenRequest, request: Request):
    await authenticate_request(request)
    return await token_service.handle_token_request(token_request)

@router.post("/chat_tokens")
async def count_chat_tokens(chat_token_request: ChatTokenRequest, request: Request):
    await authenticate_request(request)
    return await token_service.handle_chat_token_request(chat_token_request)