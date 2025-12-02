"""API module for backend services."""


def get_data():
    """Retrieve data from the backend."""
    return {"status": "ok", "message": "Backend is running"}


def process_request(request_data):
    """Process an incoming request.
    
    Args:
        request_data: Dictionary containing request information.
        
    Returns:
        Processed response data.
    """
    return {"processed": True, "data": request_data}
