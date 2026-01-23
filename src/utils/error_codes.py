"""
Error codes and standardized error responses per Architecture spec 9.1
"""
from datetime import datetime
from flask import g


class ErrorCode:
    """Standard error codes per Architecture spec 9.1.2"""
    # 400 Bad Request
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_SKU = "INVALID_SKU"
    INVALID_QUANTITY = "INVALID_QUANTITY"
    
    # 401 Unauthorized
    UNAUTHORIZED = "UNAUTHORIZED"
    
    # 403 Forbidden
    FORBIDDEN = "FORBIDDEN"
    
    # 404 Not Found
    SKU_NOT_FOUND = "SKU_NOT_FOUND"
    RESERVATION_NOT_FOUND = "RESERVATION_NOT_FOUND"
    
    # 409 Conflict
    INSUFFICIENT_STOCK = "INSUFFICIENT_STOCK"
    RESERVATION_CONFLICT = "RESERVATION_CONFLICT"
    SKU_ALREADY_EXISTS = "SKU_ALREADY_EXISTS"
    
    # 422 Unprocessable Entity
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    
    # 500 Internal Server Error
    INTERNAL_ERROR = "INTERNAL_ERROR"


def create_error_response(code: str, message: str, details: dict = None, status_code: int = 400):
    """
    Create a standardized error response per Architecture spec 9.1.1
    
    Args:
        code: Error code from ErrorCode class
        message: Human-readable error message
        details: Additional error details (optional)
        status_code: HTTP status code
        
    Returns:
        tuple: (error_dict, status_code)
    """
    correlation_id = getattr(g, 'correlation_id', None)
    
    error_response = {
        "error": {
            "code": code,
            "message": message,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    if details:
        error_response["error"]["details"] = details
    
    if correlation_id:
        error_response["error"]["correlation_id"] = correlation_id
    
    return error_response, status_code


def sku_not_found_error(sku: str):
    """SKU not found error - PRD 4.3"""
    return create_error_response(
        code=ErrorCode.SKU_NOT_FOUND,
        message=f"SKU not found",
        details={"sku": sku},
        status_code=404
    )


def insufficient_stock_error(sku: str, requested: int, available: int):
    """Insufficient stock error - PRD 4.7"""
    return create_error_response(
        code=ErrorCode.INSUFFICIENT_STOCK,
        message=f"Not enough stock available for {sku}",
        details={
            "sku": sku,
            "requested": requested,
            "available": available
        },
        status_code=409
    )


def sku_already_exists_error(sku: str):
    """Duplicate SKU error - PRD 4.17"""
    return create_error_response(
        code=ErrorCode.SKU_ALREADY_EXISTS,
        message=f"SKU already exists",
        details={"sku": sku},
        status_code=409
    )


def reservation_not_found_error(reservation_id: str):
    """Reservation not found error"""
    return create_error_response(
        code=ErrorCode.RESERVATION_NOT_FOUND,
        message=f"Reservation not found",
        details={"reservation_id": reservation_id},
        status_code=404
    )


def validation_error(message: str, details: dict = None):
    """Validation error"""
    return create_error_response(
        code=ErrorCode.VALIDATION_ERROR,
        message=message,
        details=details,
        status_code=400
    )
