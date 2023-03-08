"""
Some functions to parse content from CLI arguments
or environment variables.
"""


def parse_bool(value: str | None) -> bool:
    """
    Parse a boolean value from a string.
    If value is None or if it is not equal to "true" string
    It will return False.
    """
    if value and str(value).lower() == "true":
        return True
    return False
