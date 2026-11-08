from typing import Any, Dict, Optional
from pydantic import BaseModel


def success_response(
    message: str = "Success",
    data: Optional[Any] = None,
    status_code: int = 200,
) -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
        "statusCode": status_code,
    }


def error_response(
    message: str = "Error",
    error: Optional[str] = None,
    status_code: int = 400,
) -> Dict[str, Any]:
    return {
        "success": False,
        "message": message,
        "data": None,
        "error": error or message,
        "statusCode": status_code,
    }

