"""
Generic Pattern Matching for Transaction Categorization.

Provides reusable pattern matching logic for keyword and regex-based categorization.
"""

import re
from typing import Dict, List, Optional, Tuple

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False


def match_keywords(
    text: str,
    keywords: List[str],
    fuzzy_threshold: int = 80
) -> Optional[Tuple[str, float, str]]:
    """
    Match text against a list of keywords.
    
    Uses exact matching first, then fuzzy matching if rapidfuzz is available.
    
    Args:
        text: Normalized text to match
        keywords: List of keyword strings
        fuzzy_threshold: Minimum score for fuzzy matching (0-100)
        
    Returns:
        Tuple of (matched_keyword, confidence, match_method) or None
        
    Example:
        >>> match_keywords("TESCO SUPERSTORE", ["TESCO", "SAINSBURY"])
        ("TESCO", 1.0, "keyword")
    """
    # Exact match
    for keyword in keywords:
        if keyword in text:
            return (keyword, 1.0, "keyword")
    
    # Fuzzy match if available
    if RAPIDFUZZ_AVAILABLE:
        best_score = 0
        best_match = None
        for keyword in keywords:
            score = fuzz.partial_ratio(keyword, text)
            if score > best_score and score >= fuzzy_threshold:
                best_score = score
                best_match = keyword
        
        if best_match:
            confidence = best_score / 100.0
            return (best_match, confidence, "fuzzy")
    
    return None


def match_regex_patterns(
    text: str,
    patterns: List[str]
) -> Optional[Tuple[str, float, str]]:
    """
    Match text against a list of regex patterns.
    
    Args:
        text: Text to match
        patterns: List of regex pattern strings
        
    Returns:
        Tuple of (matched_pattern, confidence, match_method) or None
    """
    for pattern in patterns:
        if re.search(pattern, text):
            return (pattern, 1.0, "regex")
    
    return None


def match_pattern_dict(
    text: str,
    pattern_dict: Dict[str, Dict],
    fuzzy_threshold: int = 80
) -> Optional[Tuple[str, float, str, Dict]]:
    """
    Match text against a pattern dictionary.
    
    Pattern dict format:
    {
        "category_name": {
            "keywords": ["KEYWORD1", "KEYWORD2"],
            "regex_patterns": [r"(?i)pattern1", r"(?i)pattern2"],
            "weight": 1.0,
            "description": "Category Description",
            ...
        }
    }
    
    Scoring: regex matches get +2, keyword matches get +1.
    Returns the best matching category.
    
    Args:
        text: Normalized text to match
        pattern_dict: Dictionary of pattern definitions
        fuzzy_threshold: Minimum score for fuzzy matching
        
    Returns:
        Tuple of (category_name, confidence, match_method, pattern_info) or None
    """
    best_match = None
    best_score = 0
    
    for category_name, pattern_info in pattern_dict.items():
        score = 0
        matched_method = None
        
        # Check regex patterns (score +2)
        regex_patterns = pattern_info.get("regex_patterns", [])
        if regex_patterns:
            regex_match = match_regex_patterns(text, regex_patterns)
            if regex_match:
                score += 2
                matched_method = "regex"
        
        # Check keywords (score +1)
        keywords = pattern_info.get("keywords", [])
        if keywords:
            keyword_match = match_keywords(text, keywords, fuzzy_threshold)
            if keyword_match:
                score += 1
                if not matched_method:
                    matched_method = keyword_match[2]  # Use the match method from keyword match
        
        # Update best match if this is better
        if score > best_score:
            best_score = score
            confidence = 0.95 if score >= 2 else (0.85 if score == 1 else 0.0)
            best_match = (category_name, confidence, matched_method, pattern_info)
    
    return best_match
