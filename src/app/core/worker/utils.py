from pathlib import Path

def sanitize_filename(filename: str) -> str:
    # Remove/replace invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove leading/trailing spaces and dots
    filename = filename.strip('. ')
    
    # Limit length (255 is typical filesystem limit)
    filename = filename[:255]
    
    return filename


