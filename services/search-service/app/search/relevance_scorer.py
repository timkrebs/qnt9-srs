"""
Relevance scoring system for search results.

Scores stock search results based on multiple factors including
match quality, popularity, field priority, and recency.
"""
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional

from ..domain.entities import Stock

logger = logging.getLogger(__name__)


@dataclass
class SearchMatch:
    """
    Container for a search match with relevance score.

    Attributes:
        stock: The matched stock entity
        score: Relevance score (0-100)
        match_type: Type of match (exact, prefix, fuzzy, contains)
        matched_field: Which field matched (symbol, name, isin, wkn)
        similarity: Fuzzy match similarity (0-1)
    """

    stock: Stock
    score: float
    match_type: str
    matched_field: str
    similarity: float = 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        result = self.stock.to_dict()
        result["_relevance"] = {
            "score": round(self.score, 2),
            "match_type": self.match_type,
            "matched_field": self.matched_field,
            "similarity": round(self.similarity, 3),
        }
        return result


class RelevanceScorer:
    """
    Calculate relevance scores for search results.

    Scoring factors:
    1. Match Type (40%) - Exact > Prefix > Fuzzy > Contains
    2. Popularity (30%) - Search frequency and market cap
    3. Field Priority (20%) - Symbol > ISIN > WKN > Name
    4. Recency (10%) - Recently searched stocks

    Total score normalized to 0-100 scale.
    """

    # Scoring weights
    MATCH_TYPE_WEIGHT = 0.40
    POPULARITY_WEIGHT = 0.30
    FIELD_PRIORITY_WEIGHT = 0.20
    RECENCY_WEIGHT = 0.10

    # Match type scores (out of 100)
    MATCH_TYPE_SCORES = {"exact": 100, "prefix": 80, "fuzzy": 60, "contains": 50, "token": 40}

    # Field priority scores (out of 100)
    FIELD_PRIORITY_SCORES = {"symbol": 100, "isin": 90, "wkn": 85, "name": 70}

    def __init__(self, search_stats: Optional[dict] = None):
        """
        Initialize relevance scorer.

        Args:
            search_stats: Dictionary mapping stock symbols to search counts
                         Format: {"AAPL": 1000, "MSFT": 500, ...}
        """
        self.search_stats = search_stats or {}

        # Calculate max search count for normalization
        self.max_search_count = max(self.search_stats.values()) if self.search_stats else 1

    def score(
        self,
        stock: Stock,
        match_type: str,
        matched_field: str,
        similarity: float = 1.0,
        user_search_history: Optional[List[str]] = None,
    ) -> SearchMatch:
        """
        Calculate relevance score for a search match.

        Args:
            stock: The matched stock entity
            match_type: Type of match (exact, prefix, fuzzy, contains, token)
            matched_field: Which field matched (symbol, name, isin, wkn)
            similarity: Fuzzy match similarity score (0-1)
            user_search_history: List of user's recent searches

        Returns:
            SearchMatch with calculated score
        """
        # Calculate individual component scores
        match_score = self._calculate_match_score(match_type, similarity)
        popularity_score = self._calculate_popularity_score(stock)
        field_score = self._calculate_field_score(matched_field)
        recency_score = self._calculate_recency_score(stock, user_search_history)

        # Weighted combination
        total_score = (
            match_score * self.MATCH_TYPE_WEIGHT
            + popularity_score * self.POPULARITY_WEIGHT
            + field_score * self.FIELD_PRIORITY_WEIGHT
            + recency_score * self.RECENCY_WEIGHT
        )

        return SearchMatch(
            stock=stock,
            score=total_score,
            match_type=match_type,
            matched_field=matched_field,
            similarity=similarity,
        )

    def score_batch(
        self, matches: List[tuple], user_search_history: Optional[List[str]] = None
    ) -> List[SearchMatch]:
        """
        Score multiple matches and return sorted by relevance.

        Args:
            matches: List of (stock, match_type, matched_field, similarity) tuples
            user_search_history: List of user's recent searches

        Returns:
            List of SearchMatch objects sorted by score (descending)
        """
        scored_matches = []

        for match_data in matches:
            if len(match_data) == 3:
                stock, match_type, matched_field = match_data
                similarity = 1.0
            else:
                stock, match_type, matched_field, similarity = match_data

            scored_match = self.score(
                stock, match_type, matched_field, similarity, user_search_history
            )
            scored_matches.append(scored_match)

        # Sort by score descending
        scored_matches.sort(key=lambda m: m.score, reverse=True)

        return scored_matches

    def _calculate_match_score(self, match_type: str, similarity: float) -> float:
        """
        Calculate match quality score.

        Args:
            match_type: Type of match (exact, prefix, fuzzy, etc.)
            similarity: Fuzzy match similarity (0-1)

        Returns:
            Match score (0-100)
        """
        base_score = self.MATCH_TYPE_SCORES.get(match_type, 30)

        # For fuzzy matches, adjust score based on similarity
        if match_type == "fuzzy" and similarity < 1.0:
            # Scale fuzzy score based on similarity
            # similarity 1.0 = 60 points
            # similarity 0.8 = 48 points
            # similarity 0.6 = 36 points
            base_score = int(base_score * similarity)

        return base_score

    def _calculate_popularity_score(self, stock: Stock) -> float:
        """
        Calculate popularity score based on search frequency and market cap.

        Args:
            stock: Stock entity

        Returns:
            Popularity score (0-100)
        """
        # Get search count for this stock
        symbol = stock.identifier.symbol
        search_count = self.search_stats.get(symbol, 0)

        # Normalize search count (0-70 points)
        search_score = 0
        if self.max_search_count > 0:
            search_score = (search_count / self.max_search_count) * 70

        # Market cap contribution (0-30 points)
        market_cap_score = self._score_market_cap(stock.metadata.market_cap)

        return search_score + market_cap_score

    def _score_market_cap(self, market_cap: Optional[Decimal]) -> float:
        """
        Score based on market capitalization.

        Tiers:
        - Mega cap (>$200B): 30 points
        - Large cap ($10B-$200B): 25 points
        - Mid cap ($2B-$10B): 20 points
        - Small cap ($300M-$2B): 15 points
        - Micro cap (<$300M): 10 points
        - Unknown: 5 points
        """
        if not market_cap or market_cap <= 0:
            return 5

        cap_billions = float(market_cap) / 1_000_000_000

        if cap_billions >= 200:
            return 30
        elif cap_billions >= 10:
            return 25
        elif cap_billions >= 2:
            return 20
        elif cap_billions >= 0.3:
            return 15
        else:
            return 10

    def _calculate_field_score(self, matched_field: str) -> float:
        """
        Calculate field priority score.

        Args:
            matched_field: Which field matched (symbol, name, isin, wkn)

        Returns:
            Field priority score (0-100)
        """
        return self.FIELD_PRIORITY_SCORES.get(matched_field, 50)

    def _calculate_recency_score(
        self, stock: Stock, user_search_history: Optional[List[str]] = None
    ) -> float:
        """
        Calculate recency score based on user's search history.

        Args:
            stock: Stock entity
            user_search_history: List of user's recent searches (symbols)

        Returns:
            Recency score (0-100)
        """
        if not user_search_history:
            return 50  # Neutral score

        symbol = stock.identifier.symbol

        # Check if stock is in recent searches
        if symbol in user_search_history:
            # Score based on position (more recent = higher score)
            try:
                position = user_search_history.index(symbol)
                # Most recent (position 0) = 100 points
                # Position 10 = 50 points
                # Position 20+ = 20 points
                score = max(20, 100 - (position * 4))
                return score
            except ValueError:
                pass

        return 30  # Not in recent searches

    def update_search_stats(self, search_stats: dict):
        """
        Update search statistics for popularity scoring.

        Args:
            search_stats: Dictionary mapping symbols to search counts
        """
        self.search_stats = search_stats
        self.max_search_count = max(search_stats.values()) if search_stats else 1
        logger.info(
            f"Updated search stats: {len(search_stats)} symbols, max count: {self.max_search_count}"
        )

    def get_stats(self) -> dict:
        """
        Get scorer configuration and statistics.

        Returns:
            Dictionary with scorer stats
        """
        return {
            "weights": {
                "match_type": self.MATCH_TYPE_WEIGHT,
                "popularity": self.POPULARITY_WEIGHT,
                "field_priority": self.FIELD_PRIORITY_WEIGHT,
                "recency": self.RECENCY_WEIGHT,
            },
            "search_stats_count": len(self.search_stats),
            "max_search_count": self.max_search_count,
        }
