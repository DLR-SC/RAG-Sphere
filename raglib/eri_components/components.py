from pydantic import BaseModel
from enum import Enum
from typing import List, Dict, Optional

class AuthorizationMethods(Enum):
    NONE = "NONE"
    TOKEN = "TOKEN"
    USERNAME_PASSWORD = "USERNAME_PASSWORD"

class AllowedTypes(Enum):
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    TEXT = "TEXT"

class Roles(Enum):
    NONE = "NONE"
    UNKNOWN = "UNKNOWN"
    SYSTEM = "SYSTEM"
    USER = "USER"
    AI = "AI"
    AGENT = "AGENT"

class AuthHeader(BaseModel):
    token: str

class AuthResponse(BaseModel):
    success: bool
    token: str
    message: str

class ContentBlocks_(BaseModel):
    content: str
    role: Roles
    type: AllowedTypes

class ContentBlocks(BaseModel):
    contentBlocks: List[ContentBlocks_]

class RetrievalRequest(BaseModel):
    latestUserPrompt: str
    latestUserPromptType: AllowedTypes
    thread: ContentBlocks
    retrievalProcessId: Optional[str]
    parameters: Optional[Dict[str, int]]
    maxMatches: int

class RetrievalAnswer(BaseModel):
    name: str
    category: str
    path: str
    type: AllowedTypes
    matchedContent: str
    surroundingContent: List[str]
    links: List[str]
