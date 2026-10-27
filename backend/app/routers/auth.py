"""
Authentication router for QADoc FastAPI backend.
"""

from fastapi import APIRouter, HTTPException, status
from app.schemas import UserLoginRequest, UserRegisterRequest, UserResponse
from qadoc.database.auth import login_user, register_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=UserResponse)
def login(payload: UserLoginRequest):
    """
    Authenticate user credentials against MongoDB.
    """
    try:
        user_info = login_user(username=payload.username, password=payload.password)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password.",
            )

        if isinstance(user_info, dict):
            uid = str(user_info.get("user_id", ""))
            uname = str(user_info.get("username", payload.username))
        else:
            uid = str(user_info)
            uname = payload.username

        return UserResponse(user_id=uid, username=uname)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database authentication error: {str(e)}",
        )


@router.post("/register", response_model=UserResponse)
def register(payload: UserRegisterRequest):
    """
    Register a new user account.
    """
    try:
        user_info = register_user(username=payload.username, password=payload.password)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed. Username may already exist.",
            )

        if isinstance(user_info, dict):
            uid = str(user_info.get("user_id", ""))
            uname = str(user_info.get("username", payload.username))
        else:
            uid = str(user_info)
            uname = payload.username

        return UserResponse(user_id=uid, username=uname)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration error: {str(e)}",
        )
