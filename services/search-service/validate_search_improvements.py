#!/usr/bin/env python3
"""
Test script for Yahoo Finance search improvements.

This script validates that the search service works correctly with
only Yahoo Finance API, without Alpha Vantage.
"""

import asyncio
import sys
from pathlib import Path

from app.domain.entities import IdentifierType, StockIdentifier
from app.infrastructure.yahoo_finance_client import YahooFinanceClient

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))


async def test_identifier_detection():
    """Test identifier type detection."""
    print("\n=== Testing Identifier Detection ===\n")

    test_cases = [
        ("AAPL", IdentifierType.SYMBOL),
        ("US0378331005", IdentifierType.ISIN),
        ("865985", IdentifierType.WKN),
        ("Apple", IdentifierType.SYMBOL),
        ("AMAZON", IdentifierType.NAME),
        ("Apple Inc", IdentifierType.NAME),
        ("BRK.B", IdentifierType.SYMBOL),
        ("VOW3.DE", IdentifierType.SYMBOL),
        ("Deutsche Bank", IdentifierType.NAME),
    ]

    passed = 0
    failed = 0

    for query, expected in test_cases:
        detected = StockIdentifier.detect_type(query.upper())
        status = "✓" if detected == expected else "✗"

        if detected == expected:
            passed += 1
        else:
            failed += 1

        print(f"{status} '{query}' -> {detected.value} (expected: {expected.value})")

    print(f"\nResults: {passed} passed, {failed} failed\n")
    return failed == 0


async def test_symbol_search():
    """Test direct symbol search."""
    print("\n=== Testing Symbol Search ===\n")

    client = YahooFinanceClient()

    test_symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]

    for symbol in test_symbols:
        try:
            identifier = StockIdentifier(symbol=symbol)
            stock = await client.fetch_stock(identifier)

            if stock:
                print(
                    f"✓ {symbol}: {stock.identifier.name} - ${stock.price.current} {stock.price.currency}"
                )
            else:
                print(f"✗ {symbol}: Not found")

        except Exception as e:
            print(f"✗ {symbol}: Error - {e}")

    print()


async def test_name_search():
    """Test name-based search."""
    print("\n=== Testing Name Search ===\n")

    client = YahooFinanceClient()

    test_names = ["Apple", "Microsoft", "Tesla", "Amazon"]

    for name in test_names:
        try:
            results = await client.search_by_name(name, limit=3)

            if results:
                print(f"✓ '{name}' found {len(results)} results:")
                for stock in results[:3]:
                    print(f"  - {stock.identifier.symbol}: {stock.identifier.name}")
            else:
                print(f"✗ '{name}': No results found")

        except Exception as e:
            print(f"✗ '{name}': Error - {e}")

    print()


async def test_isin_search():
    """Test ISIN-based search."""
    print("\n=== Testing ISIN Search ===\n")

    client = YahooFinanceClient()

    # Test cases: (ISIN, Expected Symbol)
    test_isins = [
        ("US0378331005", "AAPL"),  # Apple
        ("US5949181045", "MSFT"),  # Microsoft
    ]

    for isin, expected_symbol in test_isins:
        try:
            identifier = StockIdentifier(isin=isin)
            stock = await client.fetch_stock(identifier)

            if stock:
                symbol_match = stock.identifier.symbol == expected_symbol
                status = "✓" if symbol_match else "⚠"
                print(f"{status} {isin}: {stock.identifier.symbol} - {stock.identifier.name}")
            else:
                print(f"✗ {isin}: Not found")

        except Exception as e:
            print(f"✗ {isin}: Error - {e}")

    print()


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Yahoo Finance Search Service - Validation Tests")
    print("=" * 60)

    try:
        # Test 1: Identifier Detection
        detection_ok = await test_identifier_detection()

        # Test 2: Symbol Search
        await test_symbol_search()

        # Test 3: Name Search
        await test_name_search()

        # Test 4: ISIN Search
        await test_isin_search()

        print("=" * 60)
        if detection_ok:
            print("All identifier detection tests passed!")
        else:
            print("Some identifier detection tests failed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nError running tests: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
