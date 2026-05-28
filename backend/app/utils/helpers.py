"""
Helper Functions
Utility functions for common operations across the application
"""

import hashlib
import secrets
import string
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


def generate_random_string(length: int = 32, include_special: bool = False) -> str:
    """
    Generate a random string.
    
    Args:
        length: Length of the string
        include_special: Include special characters
    
    Returns:
        Random string
    """
    characters = string.ascii_letters + string.digits
    if include_special:
        characters += string.punctuation
    
    return ''.join(secrets.choice(characters) for _ in range(length))


def generate_token(length: int = 32) -> str:
    """Generate a secure random token."""
    return secrets.token_urlsafe(length)


def hash_string(text: str, algorithm: str = "sha256") -> str:
    """
    Hash a string using specified algorithm.
    
    Args:
        text: Text to hash
        algorithm: Hash algorithm (md5, sha1, sha256, sha512)
    
    Returns:
        Hexadecimal hash string
    """
    hash_obj = hashlib.new(algorithm)
    hash_obj.update(text.encode('utf-8'))
    return hash_obj.hexdigest()


def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime to string."""
    return dt.strftime(format_str)


def parse_datetime(dt_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """Parse string to datetime."""
    return datetime.strptime(dt_str, format_str)


def get_utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


def add_time_delta(dt: datetime, **kwargs) -> datetime:
    """
    Add time delta to datetime.
    
    Args:
        dt: Base datetime
        **kwargs: Arguments for timedelta (days, hours, minutes, seconds, etc.)
    
    Returns:
        New datetime
    """
    return dt + timedelta(**kwargs)


def time_ago(dt: datetime) -> str:
    """
    Get human-readable time ago string.
    
    Args:
        dt: Past datetime
    
    Returns:
        String like "2 hours ago", "3 days ago"
    """
    now = get_utc_now()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    delta = now - dt
    
    if delta.days > 365:
        years = delta.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif delta.days > 30:
        months = delta.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    elif delta.seconds > 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif delta.seconds > 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string like "1.5 MB"
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to maximum length.
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def deep_merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary (takes precedence)
    
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict, parent_key: str = '', sep: str = '.') -> Dict:
    """
    Flatten nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for keys
    
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List, chunk_size: int) -> List[List]:
    """
    Split list into chunks.
    
    Args:
        lst: Input list
        chunk_size: Size of each chunk
    
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def remove_none_values(d: Dict) -> Dict:
    """Remove None values from dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def convert_keys_to_snake_case(d: Dict) -> Dict:
    """Convert dictionary keys from camelCase to snake_case."""
    def to_snake_case(name: str) -> str:
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
    
    return {to_snake_case(k): v for k, v in d.items()}


def convert_keys_to_camel_case(d: Dict) -> Dict:
    """Convert dictionary keys from snake_case to camelCase."""
    def to_camel_case(name: str) -> str:
        components = name.split('_')
        return components[0] + ''.join(x.title() for x in components[1:])
    
    return {to_camel_case(k): v for k, v in d.items()}


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if denominator is zero.
    
    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero
    
    Returns:
        Result of division or default
    """
    try:
        return numerator / denominator if denominator != 0 else default
    except (TypeError, ZeroDivisionError):
        return default


def calculate_percentage(part: float, total: float, decimals: int = 2) -> float:
    """
    Calculate percentage.
    
    Args:
        part: Part value
        total: Total value
        decimals: Number of decimal places
    
    Returns:
        Percentage value
    """
    if total == 0:
        return 0.0
    return round((part / total) * 100, decimals)


def clamp(value: float, min_value: float, max_value: float) -> float:
    """
    Clamp value between min and max.
    
    Args:
        value: Value to clamp
        min_value: Minimum value
        max_value: Maximum value
    
    Returns:
        Clamped value
    """
    return max(min_value, min(value, max_value))


def parse_time_interval(interval: str) -> timedelta:
    """
    Parse time interval string to timedelta.
    
    Args:
        interval: Time interval string (e.g., '1h', '30m', '7d')
    
    Returns:
        timedelta object
    """
    import re
    pattern = re.compile(r'^(\d+)([smhd])$')
    match = pattern.match(interval)
    
    if not match:
        raise ValueError(f"Invalid time interval format: {interval}")
    
    value, unit = match.groups()
    value = int(value)
    
    units = {
        's': 'seconds',
        'm': 'minutes',
        'h': 'hours',
        'd': 'days'
    }
    
    return timedelta(**{units[unit]: value})


def load_json_file(filepath: Union[str, Path]) -> Dict:
    """
    Load JSON file.
    
    Args:
        filepath: Path to JSON file
    
    Returns:
        Parsed JSON data
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def save_json_file(data: Dict, filepath: Union[str, Path], indent: int = 2):
    """
    Save data to JSON file.
    
    Args:
        data: Data to save
        filepath: Path to JSON file
        indent: JSON indentation
    """
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=indent)


def ensure_directory(directory: Union[str, Path]):
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
    """
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_file_extension(filename: str) -> str:
    """Get file extension without dot."""
    return Path(filename).suffix.lstrip('.')


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    import re
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)
    # Replace spaces with underscores
    filename = filename.replace(' ', '_')
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    return filename


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate unique ID with optional prefix.
    
    Args:
        prefix: Optional prefix for the ID
    
    Returns:
        Unique ID string
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    random_part = generate_random_string(8)
    
    if prefix:
        return f"{prefix}_{timestamp}_{random_part}"
    return f"{timestamp}_{random_part}"


def retry_on_exception(func, max_attempts: int = 3, delay: float = 1.0, exceptions: tuple = (Exception,)):
    """
    Retry function on exception.
    
    Args:
        func: Function to retry
        max_attempts: Maximum number of attempts
        delay: Delay between attempts in seconds
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Function result
    """
    import time
    
    for attempt in range(max_attempts):
        try:
            return func()
        except exceptions as e:
            if attempt == max_attempts - 1:
                raise
            time.sleep(delay)


def format_number(value: float, decimals: int = 2, thousands_sep: str = ",") -> str:
    """
    Format number with thousands separator.
    
    Args:
        value: Number to format
        decimals: Number of decimal places
        thousands_sep: Thousands separator
    
    Returns:
        Formatted number string
    """
    return f"{value:,.{decimals}f}".replace(",", thousands_sep)


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """
    Calculate basic statistics for a list of values.
    
    Args:
        values: List of numeric values
    
    Returns:
        Dictionary with statistics (min, max, mean, median, stddev)
    """
    if not values:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "stddev": 0
        }
    
    import statistics
    
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": statistics.mean(values),
        "median": statistics.median(values),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0
    }