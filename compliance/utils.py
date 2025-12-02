"""
KYC Validation Utilities
Name matching and validation functions
"""
import re
from difflib import SequenceMatcher


def normalize_name(name):
    """
    Normalize name for comparison
    - Convert to uppercase
    - Remove extra spaces
    - Remove special characters
    - Remove common titles
    """
    if not name:
        return ""
    
    # Convert to uppercase
    name = name.upper()
    
    # Remove titles
    titles = ['MR', 'MRS', 'MS', 'DR', 'PROF', 'SH', 'SMT', 'KUM']
    for title in titles:
        name = re.sub(rf'\b{title}\.?\b', '', name)
    
    # Remove special characters except spaces
    name = re.sub(r'[^A-Z\s]', '', name)
    
    # Remove extra spaces
    name = ' '.join(name.split())
    
    return name.strip()


def extract_name_parts(name):
    """
    Extract first and last name from full name
    Returns: (first_name, last_name)
    """
    name = normalize_name(name)
    parts = name.split()
    
    if len(parts) == 0:
        return "", ""
    elif len(parts) == 1:
        return parts[0], ""
    else:
        # First word is first name, last word is last name
        return parts[0], parts[-1]


def calculate_similarity(str1, str2):
    """
    Calculate similarity percentage between two strings
    Returns: float between 0 and 1
    """
    if not str1 or not str2:
        return 0.0
    
    return SequenceMatcher(None, str1, str2).ratio()


def fuzzy_name_match(name1, name2, threshold=0.8):
    """
    Fuzzy match two names
    
    Args:
        name1: First name
        name2: Second name
        threshold: Minimum similarity score (0-1)
    
    Returns:
        dict with:
            - match: bool
            - score: float (0-1)
            - reason: str
    """
    # Normalize both names
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return {
            'match': False,
            'score': 0.0,
            'reason': 'One or both names are empty'
        }
    
    # Full name similarity
    full_similarity = calculate_similarity(norm1, norm2)
    
    if full_similarity >= threshold:
        return {
            'match': True,
            'score': full_similarity,
            'reason': f'Full name match ({full_similarity:.2%})'
        }
    
    # Extract first and last names
    first1, last1 = extract_name_parts(name1)
    first2, last2 = extract_name_parts(name2)
    
    # Check if first and last names match
    first_match = calculate_similarity(first1, first2)
    last_match = calculate_similarity(last1, last2)
    
    # Average of first and last name similarity
    avg_similarity = (first_match + last_match) / 2
    
    if avg_similarity >= threshold:
        return {
            'match': True,
            'score': avg_similarity,
            'reason': f'First+Last name match ({avg_similarity:.2%})'
        }
    
    # Check if one name is contained in the other
    if norm1 in norm2 or norm2 in norm1:
        return {
            'match': True,
            'score': 0.85,  # High score for substring match
            'reason': 'Name substring match'
        }
    
    return {
        'match': False,
        'score': max(full_similarity, avg_similarity),
        'reason': f'Names do not match (score: {max(full_similarity, avg_similarity):.2%})'
    }


def validate_dob_match(dob1, dob2):
    """
    Validate if two dates of birth match
    
    Args:
        dob1: datetime.date or string (DD/MM/YYYY)
        dob2: datetime.date or string (DD/MM/YYYY)
    
    Returns:
        dict with:
            - match: bool
            - reason: str
    """
    from datetime import datetime
    
    # Convert strings to dates if needed
    if isinstance(dob1, str):
        try:
            dob1 = datetime.strptime(dob1, '%d/%m/%Y').date()
        except:
            try:
                dob1 = datetime.strptime(dob1, '%Y-%m-%d').date()
            except:
                return {
                    'match': False,
                    'reason': 'Invalid date format for first date'
                }
    
    if isinstance(dob2, str):
        try:
            dob2 = datetime.strptime(dob2, '%d/%m/%Y').date()
        except:
            try:
                dob2 = datetime.strptime(dob2, '%Y-%m-%d').date()
            except:
                return {
                    'match': False,
                    'reason': 'Invalid date format for second date'
                }
    
    if dob1 == dob2:
        return {
            'match': True,
            'reason': 'Date of birth matches'
        }
    else:
        return {
            'match': False,
            'reason': f'Date of birth mismatch: {dob1} vs {dob2}'
        }