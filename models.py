from pydantic import BaseModel
from typing import List, Optional, Union

class TokenRequest(BaseModel):
    text: str
    number: int
    model: Optional[str] = None

class ImgContent(BaseModel):
    url: str
    detail: Optional[str] = "auto"

class TextContent(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[ImgContent] = None

class FunctionCall(BaseModel):
    name: str
    arguments: str

class ChatMessage(BaseModel):
    role: str = None
    content: Optional[Union[str, List[TextContent]]] = None
    name: Optional[str] = None
    function_call: Optional[FunctionCall] = None     

class ChatTokenRequest(BaseModel):
    messages: List[ChatMessage]
    number: int
    model: str

class TokenResponse(BaseModel):
    text: str
    token_count: int

class ChatTokenResponse(BaseModel):
    messages: List[ChatMessage]
    token_count: int
