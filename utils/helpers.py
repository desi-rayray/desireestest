"""Helper utilities module."""


def format_string(text):
    """Format a string by stripping whitespace and converting to lowercase.
    
    Args:
        text: Input string to format. Must be a string type.
        
    Returns:
        Formatted string, or empty string if input is not a valid string.
    """
    if not isinstance(text, str):
        return ""
    return text.strip().lower()


def validate_input(data):
    """Validate that input data is a non-empty string.
    
    Args:
        data: Data to validate. Expected to be a string.
        
    Returns:
        True if data is a non-empty string, False otherwise.
    """
    if not isinstance(data, str):
        return False
    return len(data.strip()) > 0
