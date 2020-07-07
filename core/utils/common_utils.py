"""
Common utils
"""

def clean_split(s, separator=','):
    """
    Split a string by separator and collect only non-empty values
    """
    return [x.strip() for x in s.split(separator) if s.strip()]