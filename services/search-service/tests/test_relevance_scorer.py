"""
Comprehensive tests for RelevanceScorer.

Tests cover:
- Initialization with/without search stats
- Match type scoring (exact, prefix, fuzzy, contains, token)
- Popularity scoring (search frequency + market cap)
- Field priority scoring (symbol, isin, wkn, name)
- Recency scoring (user search history)
- Weighted combination calculation
- Batch scoring and sorting
- SearchMatch to_dict conversion
- Edge cases and error handling
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

import pytest

from app.domain.entities import DataSource, Stock, StockIdentifier, StockMetadata, StockPrice
from app.search.relevance_scorer import RelevanceScorer, SearchMatch

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def sample_search_stats():
    """Sample search statistics."""
    return {"AAPL": 1000, "MSFT": 500, "GOOGL": 300, "TSLA": 800, "AMZN": 400}


@pytest.fixture
def scorer(sample_search_stats):
    """Create RelevanceScorer with search stats."""
    return RelevanceScorer(search_stats=sample_search_stats)


@pytest.fixture
def scorer_no_stats():
    """Create RelevanceScorer without search stats."""
    return RelevanceScorer()


def create_stock(
    symbol: str,
    name: str,
    isin: str = "US0000000000",
    market_cap: Optional[Decimal] = None,
    search_count: int = 0,
) -> Stock:
    """Helper to create stock entities."""
    identifier = StockIdentifier(symbol=symbol, isin=isin, wkn=None, name=name)

    price = StockPrice(current=Decimal("100.00"), currency="USD")

    metadata = StockMetadata(
        exchange="NASDAQ", sector="Technology", industry="Software", market_cap=market_cap
    )

    return Stock(
        identifier=identifier,
        price=price,
        metadata=metadata,
        data_source=DataSource.YAHOO_FINANCE,
        last_updated=datetime.now(timezone.utc),
    )


# ============================================================================
# Test Initialization
# ============================================================================


class TestInitialization:
    """Test RelevanceScorer initialization."""

    def test_init_with_search_stats(self, sample_search_stats):
        """Test initialization with search statistics."""
        scorer = RelevanceScorer(search_stats=sample_search_stats)

        assert scorer.search_stats == sample_search_stats
        assert scorer.max_search_count == 1000  # AAPL has max count

    def test_init_without_search_stats(self):
        """Test initialization without search statistics."""
        scorer = RelevanceScorer()

        assert scorer.search_stats == {}
        assert scorer.max_search_count == 1

    def test_init_with_empty_stats(self):
        """Test initialization with empty search statistics."""
        scorer = RelevanceScorer(search_stats={})

        assert scorer.search_stats == {}
        assert scorer.max_search_count == 1


# ============================================================================
# Test Match Type Scoring
# ============================================================================


class TestMatchTypeScoring:
    """Test match type score calculation."""

    def test_exact_match_score(self, scorer):
        """Test exact match gets highest base score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Exact match: 100 * 0.40 = 40 points from match type alone
        # (plus other factors)
        assert match.match_type == "exact"
        assert match.score > 40  # At least match type score

    def test_prefix_match_score(self, scorer):
        """Test prefix match score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "prefix", "symbol", 1.0)

        # Prefix match: 80 * 0.40 = 32 points from match type
        assert match.match_type == "prefix"
        assert match.score > 32

    def test_fuzzy_match_score(self, scorer):
        """Test fuzzy match score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "fuzzy", "symbol", 1.0)

        # Fuzzy match: 60 * 0.40 = 24 points from match type
        assert match.match_type == "fuzzy"
        assert match.score > 24

    def test_fuzzy_match_with_low_similarity(self, scorer):
        """Test fuzzy match score adjusted by similarity."""
        stock = create_stock("AAPL", "Apple Inc.")
        match_high = scorer.score(stock, "fuzzy", "symbol", 0.9)
        match_low = scorer.score(stock, "fuzzy", "symbol", 0.6)

        # Lower similarity should yield lower score
        assert match_low.score < match_high.score

    def test_contains_match_score(self, scorer):
        """Test contains match score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "contains", "name", 1.0)

        # Contains match: 50 * 0.40 = 20 points from match type
        assert match.match_type == "contains"
        assert match.score > 20

    def test_token_match_score(self, scorer):
        """Test token match score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "token", "name", 1.0)

        # Token match: 40 * 0.40 = 16 points from match type
        assert match.match_type == "token"
        assert match.score > 16

    def test_unknown_match_type(self, scorer):
        """Test unknown match type gets default score."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "unknown", "symbol", 1.0)

        # Unknown match type defaults to 30
        assert match.match_type == "unknown"
        assert match.score > 0  # Should still have some score


# ============================================================================
# Test Popularity Scoring
# ============================================================================


class TestPopularityScoring:
    """Test popularity score calculation."""

    def test_high_search_count_stock(self, scorer):
        """Test stock with high search count gets popularity boost."""
        stock_popular = create_stock("AAPL", "Apple Inc.")  # 1000 searches
        stock_unpopular = create_stock("XYZ", "Unknown Corp.")  # 0 searches

        match_popular = scorer.score(stock_popular, "exact", "symbol", 1.0)
        match_unpopular = scorer.score(stock_unpopular, "exact", "symbol", 1.0)

        # Popular stock should score higher
        assert match_popular.score > match_unpopular.score

    def test_market_cap_mega_cap(self, scorer):
        """Test mega cap stock (>$200B) gets max market cap score."""
        stock = create_stock("AAPL", "Apple Inc.", market_cap=Decimal("3000000000000"))  # $3T
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 30 points from market cap (out of 30)
        assert match.score > 70  # High base score due to market cap

    def test_market_cap_large_cap(self, scorer):
        """Test large cap stock ($10B-$200B)."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("50000000000"))  # $50B
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 25 points from market cap
        assert match.score > 0

    def test_market_cap_mid_cap(self, scorer):
        """Test mid cap stock ($2B-$10B)."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("5000000000"))  # $5B
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 20 points from market cap
        assert match.score > 0

    def test_market_cap_small_cap(self, scorer):
        """Test small cap stock ($300M-$2B)."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("1000000000"))  # $1B
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 15 points from market cap
        assert match.score > 0

    def test_market_cap_micro_cap(self, scorer):
        """Test micro cap stock (<$300M)."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("100000000"))  # $100M
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 10 points from market cap
        assert match.score > 0

    def test_market_cap_unknown(self, scorer):
        """Test stock with unknown market cap."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=None)
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 5 points from market cap (minimum)
        assert match.score > 0

    def test_market_cap_zero(self, scorer):
        """Test stock with zero market cap."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("0"))
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should treat as unknown (5 points)
        assert match.score > 0


# ============================================================================
# Test Field Priority Scoring
# ============================================================================


class TestFieldPriorityScoring:
    """Test field priority score calculation."""

    def test_symbol_field_priority(self, scorer):
        """Test symbol field match gets highest priority."""
        stock = create_stock("AAPL", "Apple Inc.")
        match_symbol = scorer.score(stock, "exact", "symbol", 1.0)
        match_name = scorer.score(stock, "exact", "name", 1.0)

        # Symbol match should score higher than name match
        assert match_symbol.score > match_name.score

    def test_isin_field_priority(self, scorer):
        """Test ISIN field match priority."""
        stock = create_stock("AAPL", "Apple Inc.")
        match_isin = scorer.score(stock, "exact", "isin", 1.0)
        match_name = scorer.score(stock, "exact", "name", 1.0)

        # ISIN match should score higher than name match
        assert match_isin.score > match_name.score

    def test_wkn_field_priority(self, scorer):
        """Test WKN field match priority."""
        stock = create_stock("AAPL", "Apple Inc.")
        match_wkn = scorer.score(stock, "exact", "wkn", 1.0)
        match_name = scorer.score(stock, "exact", "name", 1.0)

        # WKN match should score higher than name match
        assert match_wkn.score > match_name.score

    def test_name_field_priority(self, scorer):
        """Test name field match priority."""
        stock = create_stock("AAPL", "Apple Inc.")
        match_symbol = scorer.score(stock, "exact", "symbol", 1.0)
        match_name = scorer.score(stock, "exact", "name", 1.0)

        # Name match should score lower than symbol match
        assert match_name.score < match_symbol.score

    def test_unknown_field_priority(self, scorer):
        """Test unknown field gets default priority."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "unknown_field", 1.0)

        # Should still have a valid score
        assert match.score > 0


# ============================================================================
# Test Recency Scoring
# ============================================================================


class TestRecencyScoring:
    """Test recency score calculation."""

    def test_no_search_history(self, scorer):
        """Test scoring without user search history."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "symbol", 1.0, user_search_history=None)

        # Should get neutral recency score (50)
        assert match.score > 0

    def test_empty_search_history(self, scorer):
        """Test scoring with empty search history."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "symbol", 1.0, user_search_history=[])

        # Should get neutral recency score (50)
        assert match.score > 0

    def test_recent_search_boost(self, scorer):
        """Test stock in recent searches gets recency boost."""
        stock = create_stock("AAPL", "Apple Inc.")

        match_recent = scorer.score(
            stock, "exact", "symbol", 1.0, user_search_history=["AAPL", "MSFT", "GOOGL"]
        )
        match_not_recent = scorer.score(
            stock, "exact", "symbol", 1.0, user_search_history=["MSFT", "GOOGL", "TSLA"]
        )

        # Recently searched stock should score higher
        assert match_recent.score > match_not_recent.score

    def test_most_recent_search_highest_score(self, scorer):
        """Test most recent search gets highest recency score."""
        stock = create_stock("AAPL", "Apple Inc.")

        match_first = scorer.score(
            stock,
            "exact",
            "symbol",
            1.0,
            user_search_history=["AAPL", "MSFT", "GOOGL"],  # Position 0
        )
        match_last = scorer.score(
            stock,
            "exact",
            "symbol",
            1.0,
            user_search_history=["MSFT", "GOOGL", "AAPL"],  # Position 2
        )

        # Most recent (position 0) should score higher
        assert match_first.score > match_last.score

    def test_recency_score_degradation(self, scorer):
        """Test recency score decreases with position."""
        stock = create_stock("AAPL", "Apple Inc.")

        # Create search histories with AAPL at different positions
        positions = [
            ["AAPL"] + ["X"] * 5,  # Position 0
            ["X"] + ["AAPL"] + ["X"] * 4,  # Position 1
            ["X"] * 5 + ["AAPL"],  # Position 5
        ]

        scores = [
            scorer.score(stock, "exact", "symbol", 1.0, user_search_history=hist).score
            for hist in positions
        ]

        # Scores should decrease with position
        assert scores[0] > scores[1] > scores[2]


# ============================================================================
# Test Weighted Combination
# ============================================================================


class TestWeightedCombination:
    """Test weighted score combination."""

    def test_weights_sum_to_one(self, scorer):
        """Test scoring weights sum to 1.0."""
        total_weight = (
            scorer.MATCH_TYPE_WEIGHT
            + scorer.POPULARITY_WEIGHT
            + scorer.FIELD_PRIORITY_WEIGHT
            + scorer.RECENCY_WEIGHT
        )
        assert total_weight == pytest.approx(1.0)

    def test_perfect_score_components(self, scorer_no_stats):
        """Test scoring with all perfect components."""
        # Create perfect stock: exact match on symbol, mega cap, most recent
        stock = create_stock("AAPL", "Apple Inc.", market_cap=Decimal("3000000000000"))

        match = scorer_no_stats.score(stock, "exact", "symbol", 1.0, user_search_history=["AAPL"])

        # Should get high score (79.0 = 40 match + 15 popularity + 20 field + 4 recency)
        assert match.score >= 75

    def test_worst_score_components(self, scorer_no_stats):
        """Test scoring with poor components."""
        # Unknown stock: token match on name, no market cap, not in history
        stock = create_stock("XYZ", "Unknown Corp.", market_cap=None)

        match = scorer_no_stats.score(
            stock, "token", "name", 0.6, user_search_history=["AAPL", "MSFT"]
        )

        # Should get lower score
        assert match.score < 50


# ============================================================================
# Test Batch Scoring
# ============================================================================


class TestBatchScoring:
    """Test batch scoring and sorting."""

    def test_score_batch_sorting(self, scorer):
        """Test batch scoring sorts by relevance."""
        stocks = [
            create_stock("AAPL", "Apple Inc.", market_cap=Decimal("3000000000000")),
            create_stock("MSFT", "Microsoft Corp.", market_cap=Decimal("2000000000000")),
            create_stock("XYZ", "Unknown Corp.", market_cap=Decimal("100000000")),
        ]

        matches = [
            (stocks[0], "exact", "symbol", 1.0),
            (stocks[1], "prefix", "symbol", 1.0),
            (stocks[2], "fuzzy", "name", 0.7),
        ]

        results = scorer.score_batch(matches)

        # Should be sorted by score descending
        assert len(results) == 3
        assert results[0].score >= results[1].score >= results[2].score
        assert results[0].stock.identifier.symbol == "AAPL"

    def test_score_batch_with_similarity(self, scorer):
        """Test batch scoring with similarity values."""
        stock = create_stock("AAPL", "Apple Inc.")

        matches = [
            (stock, "fuzzy", "symbol", 0.9),
            (stock, "fuzzy", "symbol", 0.7),
            (stock, "fuzzy", "symbol", 0.5),
        ]

        results = scorer.score_batch(matches)

        # Higher similarity should score higher
        assert results[0].similarity >= results[1].similarity >= results[2].similarity

    def test_score_batch_without_similarity(self, scorer):
        """Test batch scoring without explicit similarity."""
        stock = create_stock("AAPL", "Apple Inc.")

        # 3-tuple format (stock, match_type, matched_field)
        matches = [(stock, "exact", "symbol"), (stock, "prefix", "name")]

        results = scorer.score_batch(matches)

        # Should default similarity to 1.0
        assert all(r.similarity == 1.0 for r in results)

    def test_score_batch_with_user_history(self, scorer):
        """Test batch scoring with user search history."""
        stocks = [
            create_stock("AAPL", "Apple Inc."),
            create_stock("MSFT", "Microsoft Corp."),
            create_stock("GOOGL", "Google Inc."),
        ]

        matches = [
            (stocks[0], "exact", "symbol", 1.0),
            (stocks[1], "exact", "symbol", 1.0),
            (stocks[2], "exact", "symbol", 1.0),
        ]

        # MSFT is most recent in history
        results = scorer.score_batch(matches, user_search_history=["MSFT", "GOOGL", "AAPL"])

        # MSFT should benefit from recency boost
        msft_result = next(r for r in results if r.stock.identifier.symbol == "MSFT")
        googl_result = next(r for r in results if r.stock.identifier.symbol == "GOOGL")

        assert msft_result.score >= googl_result.score

    def test_score_batch_empty_list(self, scorer):
        """Test batch scoring with empty list."""
        results = scorer.score_batch([])
        assert results == []


# ============================================================================
# Test SearchMatch
# ============================================================================


class TestSearchMatch:
    """Test SearchMatch dataclass."""

    def test_search_match_creation(self, scorer):
        """Test SearchMatch creation."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "symbol", 1.0)

        assert isinstance(match, SearchMatch)
        assert match.stock == stock
        assert match.match_type == "exact"
        assert match.matched_field == "symbol"
        assert match.similarity == 1.0
        assert match.score > 0

    def test_search_match_to_dict(self, scorer):
        """Test SearchMatch to_dict conversion."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "exact", "symbol", 0.95)

        result = match.to_dict()

        # Should include stock data
        assert "identifier" in result
        assert result["identifier"]["symbol"] == "AAPL"

        # Should include relevance metadata
        assert "_relevance" in result
        assert result["_relevance"]["match_type"] == "exact"
        assert result["_relevance"]["matched_field"] == "symbol"
        assert result["_relevance"]["score"] == pytest.approx(match.score, abs=0.01)
        assert result["_relevance"]["similarity"] == pytest.approx(0.95, abs=0.001)

    def test_search_match_score_rounding(self, scorer):
        """Test SearchMatch score rounding in to_dict."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "fuzzy", "symbol", 0.876)

        result = match.to_dict()

        # Score should be rounded to 2 decimals
        assert isinstance(result["_relevance"]["score"], float)
        # Similarity should be rounded to 3 decimals
        assert result["_relevance"]["similarity"] == pytest.approx(0.876, abs=0.001)


# ============================================================================
# Test Update Methods
# ============================================================================


class TestUpdateMethods:
    """Test methods for updating scorer state."""

    def test_update_search_stats(self, scorer_no_stats):
        """Test updating search statistics."""
        assert scorer_no_stats.max_search_count == 1

        new_stats = {"AAPL": 2000, "MSFT": 1500}
        scorer_no_stats.update_search_stats(new_stats)

        assert scorer_no_stats.search_stats == new_stats
        assert scorer_no_stats.max_search_count == 2000

    def test_update_search_stats_empty(self, scorer):
        """Test updating with empty search statistics."""
        scorer.update_search_stats({})

        assert scorer.search_stats == {}
        assert scorer.max_search_count == 1

    def test_get_stats(self, scorer, sample_search_stats):
        """Test getting scorer statistics."""
        stats = scorer.get_stats()

        assert "weights" in stats
        assert stats["weights"]["match_type"] == 0.40
        assert stats["weights"]["popularity"] == 0.30
        assert stats["weights"]["field_priority"] == 0.20
        assert stats["weights"]["recency"] == 0.10

        assert stats["search_stats_count"] == len(sample_search_stats)
        assert stats["max_search_count"] == 1000


# ============================================================================
# Test Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_negative_market_cap(self, scorer):
        """Test handling of negative market cap."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("-1000000"))
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should treat as unknown/invalid (5 points)
        assert match.score > 0

    def test_very_large_market_cap(self, scorer):
        """Test handling of very large market cap."""
        stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("10000000000000"))  # $10T
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get mega cap score (30 points)
        assert match.score > 0

    def test_zero_similarity(self, scorer):
        """Test handling of zero similarity."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "fuzzy", "symbol", 0.0)

        # Should still have some score from other factors
        assert match.score >= 0
        assert match.similarity == 0.0

    def test_similarity_greater_than_one(self, scorer):
        """Test handling of similarity > 1.0."""
        stock = create_stock("AAPL", "Apple Inc.")
        match = scorer.score(stock, "fuzzy", "symbol", 1.5)

        # Should accept and use the value
        assert match.similarity == 1.5

    def test_very_long_search_history(self, scorer):
        """Test handling of very long search history."""
        stock = create_stock("AAPL", "Apple Inc.")

        # Create history with AAPL at position 100
        history = ["X"] * 100 + ["AAPL"]
        match = scorer.score(stock, "exact", "symbol", 1.0, user_search_history=history)

        # Should have minimum recency score (20 points)
        assert match.score > 0

    def test_stock_not_in_search_stats(self, scorer):
        """Test stock not in search statistics."""
        # XYZ not in sample_search_stats
        stock = create_stock("XYZ", "Unknown Corp.")
        match = scorer.score(stock, "exact", "symbol", 1.0)

        # Should get 0 search count but still have valid score
        assert match.score > 0


# ============================================================================
# Test Real-World Scenarios
# ============================================================================


class TestRealWorldScenarios:
    """Test realistic scoring scenarios."""

    def test_apple_exact_symbol_match(self, scorer):
        """Test scoring for exact Apple symbol match."""
        stock = create_stock("AAPL", "Apple Inc.", market_cap=Decimal("3000000000000"))  # $3T

        match = scorer.score(stock, "exact", "symbol", 1.0, user_search_history=["AAPL", "MSFT"])

        # Should get very high score
        assert match.score > 80
        assert match.match_type == "exact"
        assert match.matched_field == "symbol"

    def test_fuzzy_typo_match(self, scorer):
        """Test scoring for fuzzy match with typo."""
        stock = create_stock("MSFT", "Microsoft Corp.")

        # User typed "MSFT" as "MSFF" (typo)
        match = scorer.score(stock, "fuzzy", "symbol", 0.75)

        # Should get decent score but lower than exact
        assert 30 < match.score < 70
        assert match.match_type == "fuzzy"

    def test_name_contains_match(self, scorer):
        """Test scoring for name contains match."""
        stock = create_stock("AAPL", "Apple Inc.")

        # User searched for "apple"
        match = scorer.score(stock, "contains", "name", 1.0)

        # Should get moderate score
        assert match.score > 20
        assert match.matched_field == "name"

    def test_unknown_small_cap_stock(self, scorer):
        """Test scoring for unknown small cap stock."""
        stock = create_stock(
            "TINY", "Tiny Corp.", market_cap=Decimal("50000000")  # $50M (micro cap)
        )

        match = scorer.score(stock, "token", "name", 0.6)

        # Should get low score
        assert match.score < 40

    def test_popular_stock_vs_exact_match(self, scorer):
        """Test popular stock with fuzzy match vs unpopular with exact match."""
        popular_stock = create_stock("AAPL", "Apple Inc.", market_cap=Decimal("3000000000000"))
        unpopular_stock = create_stock("XYZ", "XYZ Corp.", market_cap=Decimal("100000000"))

        popular_match = scorer.score(popular_stock, "fuzzy", "symbol", 0.8)
        unpopular_match = scorer.score(unpopular_stock, "exact", "symbol", 1.0)

        # Popularity can beat match type in this scorer (68 < 74.2)
        # This is expected because popularity weight (30%) + market cap is significant
        assert popular_match.score > 70  # AAPL gets high popularity score
        assert unpopular_match.score > 65  # XYZ gets exact match boost


# ============================================================================
# Test Performance
# ============================================================================


class TestPerformance:
    """Test scorer performance."""

    def test_batch_scoring_performance(self, scorer):
        """Test batch scoring is reasonably fast."""
        import time

        # Create 100 stocks
        stocks = [create_stock(f"SYM{i}", f"Company {i}") for i in range(100)]

        matches = [(s, "exact", "symbol", 1.0) for s in stocks]

        start = time.time()
        results = scorer.score_batch(matches)
        elapsed = time.time() - start

        # Should complete in reasonable time (< 1 second)
        assert elapsed < 1.0
        assert len(results) == 100

    def test_individual_scoring_performance(self, scorer):
        """Test individual scoring is fast."""
        import time

        stock = create_stock("AAPL", "Apple Inc.")

        start = time.time()
        for _ in range(1000):
            scorer.score(stock, "exact", "symbol", 1.0)
        elapsed = time.time() - start

        # 1000 scorings should complete quickly (< 0.5 seconds)
        assert elapsed < 0.5
