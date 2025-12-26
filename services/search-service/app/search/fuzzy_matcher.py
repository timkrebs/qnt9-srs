"""
Fuzzy matching engine for stock search.

Provides typo-tolerant matching for stock symbols and names using
Levenshtein distance and other similarity algorithms.
"""

import logging
import re
from typing import Optional, Tuple

try:
    import Levenshtein

    LEVENSHTEIN_AVAILABLE = True
except ImportError:
    LEVENSHTEIN_AVAILABLE = False
    logging.warning("python-Levenshtein not available, using fallback implementation")

try:
    from rapidfuzz import fuzz

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    logging.warning("rapidfuzz not available, using fallback implementation")

logger = logging.getLogger(__name__)


class FuzzyMatcher:
    """
    Fuzzy string matching for stock identifiers and names.

    Supports multiple similarity algorithms:
    - Levenshtein distance (edit distance)
    - Jaro-Winkler similarity (prefix-focused)
    - Normalized matching (case/whitespace insensitive)
    - Symbol normalization (handles variations like BRK.B / BRK-B)
    """

    # Default similarity thresholds
    DEFAULT_SYMBOL_THRESHOLD = 0.75  # 75% similarity for symbols (was 0.8)
    DEFAULT_NAME_THRESHOLD = 0.70  # 70% similarity for names (was 0.75)

    # Symbol normalization patterns
    SYMBOL_SEPARATORS = re.compile(r"[\.\-\s]")  # Dots, hyphens, spaces

    def __init__(
        self,
        symbol_threshold: float = DEFAULT_SYMBOL_THRESHOLD,
        name_threshold: float = DEFAULT_NAME_THRESHOLD,
    ):
        """
        Initialize fuzzy matcher.

        Args:
            symbol_threshold: Minimum similarity for symbol matches (0-1)
            name_threshold: Minimum similarity for name matches (0-1)
        """
        self.symbol_threshold = symbol_threshold
        self.name_threshold = name_threshold

        if not LEVENSHTEIN_AVAILABLE and not RAPIDFUZZ_AVAILABLE:
            logger.warning("No fuzzy matching library available, using basic fallback")

    def match_symbol(self, query: str, target: str) -> Tuple[bool, float]:
        """
        Check if query matches target symbol with fuzzy matching.

        Handles symbol variations:
        - BRK.B == BRK-B == BRKB
        - VOW3 == VOW.3

        Args:
            query: Search query (e.g., "APPL")
            target: Target symbol (e.g., "AAPL")

        Returns:
            Tuple of (matches: bool, similarity_score: float)
        """
        # Normalize both strings
        query_norm = self._normalize_symbol(query)
        target_norm = self._normalize_symbol(target)

        # Exact match after normalization
        if query_norm == target_norm:
            return (True, 1.0)

        # Prefix match (e.g., "APP" matches "AAPL")
        # Check if either string starts with the other
        if len(query_norm) <= len(target_norm):
            if target_norm.startswith(query_norm):
                similarity = len(query_norm) / len(target_norm)
                if similarity >= 0.5:
                    return (True, 0.85)  # Good score for prefix matches

        if len(target_norm) < len(query_norm):
            if query_norm.startswith(target_norm):
                similarity = len(target_norm) / len(query_norm)
                if similarity >= 0.5:
                    return (True, 0.80)  # Slightly lower for reverse prefix

        # Fuzzy matching
        similarity = self._calculate_similarity(query_norm, target_norm)
        matches = similarity >= self.symbol_threshold

        return (matches, similarity)

    def match_name(self, query: str, target: str) -> Tuple[bool, float]:
        """
        Check if query matches target name with fuzzy matching.

        Uses token-based matching for multi-word names:
        - "Apple" matches "Apple Inc."
        - "Microsft" matches "Microsoft Corporation"

        Args:
            query: Search query (e.g., "Microsft")
            target: Target name (e.g., "Microsoft Corporation")

        Returns:
            Tuple of (matches: bool, similarity_score: float)
        """
        # Normalize
        query_norm = self._normalize_name(query)
        target_norm = self._normalize_name(target)

        # Exact match
        if query_norm == target_norm:
            return (True, 1.0)

        # Contains match (query is substring of target)
        if query_norm in target_norm:
            return (True, 0.9)

        # Token-based matching for multi-word names
        if " " in target_norm:
            similarity = self._match_tokens(query_norm, target_norm)
            matches = similarity >= self.name_threshold
            return (matches, similarity)

        # Full string fuzzy matching
        similarity = self._calculate_similarity(query_norm, target_norm)
        matches = similarity >= self.name_threshold

        return (matches, similarity)

    def find_best_match(
        self, query: str, candidates: list[str], is_symbol: bool = True
    ) -> Optional[Tuple[str, float]]:
        """
        Find best matching candidate for query.

        Args:
            query: Search query
            candidates: List of potential matches
            is_symbol: True for symbol matching, False for name matching

        Returns:
            Tuple of (best_match, similarity_score) or None if no good match
        """
        best_match = None
        best_score = 0.0
        best_matches = False

        matcher = self.match_symbol if is_symbol else self.match_name
        threshold = self.symbol_threshold if is_symbol else self.name_threshold

        for candidate in candidates:
            matches, score = matcher(query, candidate)
            if score > best_score:
                best_match = candidate
                best_score = score
                best_matches = matches

        # Return best match if it meets threshold OR if it's the best we found
        if best_match and (best_matches or best_score >= threshold * 0.9):
            return (best_match, best_score)
        return None

    def _normalize_symbol(self, symbol: str) -> str:
        """
        Normalize symbol for comparison.

        - Convert to uppercase
        - Remove separators (., -, spaces)

        Examples:
            "BRK.B" -> "BRKB"
            "brk-b" -> "BRKB"
            "VOW 3" -> "VOW3"
        """
        if not symbol:
            return ""

        # Remove separators and convert to uppercase
        normalized = self.SYMBOL_SEPARATORS.sub("", symbol.upper())
        return normalized

    def _normalize_name(self, name: str) -> str:
        """
        Normalize company name for comparison.

        - Convert to lowercase
        - Strip whitespace
        - Normalize internal whitespace

        Examples:
            "Apple Inc." -> "apple inc"
            "  Microsoft   Corp  " -> "microsoft corp"
        """
        if not name:
            return ""

        # Convert to lowercase, strip, normalize whitespace
        normalized = " ".join(name.lower().split())

        # Remove common suffixes for better matching
        suffixes = ["inc", "corp", "corporation", "ltd", "limited", "ag", "se", "plc"]
        words = normalized.split()

        # Remove trailing suffix if present
        if words and words[-1] in suffixes:
            words = words[:-1]

        return " ".join(words)

    def _match_tokens(self, query: str, target: str) -> float:
        """
        Match query against tokens in target.

        For multi-word names, check if query matches any token or
        the full string with fuzzy matching.

        Examples:
            "Apple" vs "Apple Inc" -> High similarity
            "Micro" vs "Microsoft Corporation" -> Medium similarity
        """
        target_tokens = target.split()

        # Check if query matches start of any token
        for token in target_tokens:
            if token.startswith(query):
                return 0.95  # High score for prefix match

        # Check fuzzy match against each token
        max_token_similarity = 0.0
        for token in target_tokens:
            similarity = self._calculate_similarity(query, token)
            max_token_similarity = max(max_token_similarity, similarity)

        # Also check against full target
        full_similarity = self._calculate_similarity(query, target)

        # Return best of token match or full match
        return max(max_token_similarity, full_similarity)

    def _calculate_similarity(self, s1: str, s2: str) -> float:
        """
        Calculate similarity between two strings.

        Uses Levenshtein distance if available, otherwise falls back
        to simpler algorithm.

        Returns:
            Similarity score between 0.0 (no match) and 1.0 (exact match)
        """
        if not s1 or not s2:
            return 0.0

        if s1 == s2:
            return 1.0

        # Try python-Levenshtein (fastest)
        if LEVENSHTEIN_AVAILABLE:
            return Levenshtein.ratio(s1, s2)

        # Try rapidfuzz
        if RAPIDFUZZ_AVAILABLE:
            return fuzz.ratio(s1, s2) / 100.0

        # Fallback: Simple character overlap ratio
        return self._fallback_similarity(s1, s2)

    def _fallback_similarity(self, s1: str, s2: str) -> float:
        """
        Fallback similarity calculation using character overlap.

        This is a simple implementation when no fuzzy matching library
        is available. Not as accurate but provides basic functionality.
        """
        # Convert to sets of characters
        set1 = set(s1)
        set2 = set(s2)

        # Calculate Jaccard similarity
        intersection = len(set1 & set2)
        union = len(set1 | set2)

        if union == 0:
            return 0.0

        # Adjust for length difference
        length_ratio = min(len(s1), len(s2)) / max(len(s1), len(s2))
        jaccard = intersection / union

        # Combine both factors
        return (jaccard + length_ratio) / 2

    def get_stats(self) -> dict:
        """
        Get matcher configuration and status.

        Returns:
            Dictionary with matcher statistics
        """
        return {
            "symbol_threshold": self.symbol_threshold,
            "name_threshold": self.name_threshold,
            "levenshtein_available": LEVENSHTEIN_AVAILABLE,
            "rapidfuzz_available": RAPIDFUZZ_AVAILABLE,
            "algorithm": self._get_algorithm_name(),
        }

    def _get_algorithm_name(self) -> str:
        """Get name of active fuzzy matching algorithm."""
        if LEVENSHTEIN_AVAILABLE:
            return "python-Levenshtein"
        elif RAPIDFUZZ_AVAILABLE:
            return "rapidfuzz"
        else:
            return "fallback"
