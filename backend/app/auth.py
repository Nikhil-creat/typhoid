"""JWT auth with organisation multi-tenancy. Every query is scoped by org_id."""
from datetime import datetime, timedelta, timezone
import jwt
from fastapi import Depends, HTTPException, WebSocket, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import get_settings

bearer = HTTPBearer(auto_error=False)


def issue_token(sub: str, org_id: str, role: str = "engineer") -> str:
    s = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=s.jwt_ttl_minutes)
    return jwt.encode({"sub": sub, "org": org_id, "role": role, "exp": exp},
                      s.typhoid_secret_key, algorithm=s.jwt_algorithm)


def decode(token: str) -> dict:
    s = get_settings()
    try:
        return jwt.decode(token, s.typhoid_secret_key, algorithms=[s.jwt_algorithm])
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}")


class Principal(dict):
    @property
    def org(self) -> str: return self["org"]
    @property
    def role(self) -> str: return self["role"]


async def current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)) -> Principal:
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    return Principal(decode(creds.credentials))


def require_role(*roles: str):
    async def dep(p: Principal = Depends(current_user)) -> Principal:
        if p.role not in roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "insufficient role")
        return p
    return dep


def ws_principal(ws: WebSocket) -> Principal:
    token = ws.query_params.get("token", "")
    return Principal(decode(token))
