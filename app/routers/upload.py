import os
import uuid
import jwt
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import APIRouter, UploadFile, File, HTTPException,Depends
from pydantic import BaseModel

router = APIRouter(prefix="/upload", tags=["Upload"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

SECRET_KEY = "your-secret-key"
security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token 无效或已过期")


class UploadResponse(BaseModel):
    filename: str
    size: int


@router.post("", response_model=UploadResponse)
async def upload(file: UploadFile = File(...),user_id: int = Depends(get_current_user)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="缺少文件名")

    ext = os.path.splitext(file.filename)[1]
    safe_name = f"{uuid.uuid4().hex}{ext}"
    save_path = os.path.join(UPLOAD_DIR, safe_name)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    return {"filename": safe_name, "size": len(content)}
