#!/usr/bin/env python3
"""
Test script to verify audit logging and API versioning implementation.

This script tests:
1. API versioning endpoints are accessible
2. Audit logging is working
3. All endpoints return expected responses
"""

import asyncio
import json
import sys
from datetime import datetime

import httpx
import asyncpg


BASE_URL = "http://localhost:8001"
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "qnt9_srs",
    "user": "postgres",
    "password": "postgres"
}


async def test_health_endpoint():
    """Test unversioned health endpoint."""
    print("\n1. Testing health endpoint (unversioned)...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        assert response.status_code == 200
        print(f"   ✓ Health endpoint working: {response.json()}")


async def test_signup(client):
    """Test versioned signup endpoint."""
    print("\n2. Testing signup endpoint (API v1)...")
    test_user = {
        "email": f"test_{datetime.now().timestamp()}@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }
    
    response = await client.post(
        f"{BASE_URL}/api/v1/auth/signup",
        json=test_user
    )
    
    assert response.status_code == 201
    data = response.json()
    print(f"   ✓ Signup successful: {data['user']['email']}")
    return data, test_user


async def test_signin(client, email, password):
    """Test versioned signin endpoint."""
    print("\n3. Testing signin endpoint (API v1)...")
    response = await client.post(
        f"{BASE_URL}/api/v1/auth/signin",
        json={"email": email, "password": password}
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"   ✓ Signin successful: {data['user']['email']}")
    return data


async def test_get_user(client, access_token):
    """Test versioned get user endpoint."""
    print("\n4. Testing get user endpoint (API v1)...")
    response = await client.get(
        f"{BASE_URL}/api/v1/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"   ✓ Get user successful: {data['email']}")
    return data


async def test_signout(client, refresh_token):
    """Test versioned signout endpoint."""
    print("\n5. Testing signout endpoint (API v1)...")
    response = await client.post(
        f"{BASE_URL}/api/v1/auth/signout",
        json={"refresh_token": refresh_token}
    )
    
    assert response.status_code == 200
    data = response.json()
    print(f"   ✓ Signout successful: {data['message']}")


async def check_audit_logs(email):
    """Check audit logs in database."""
    print("\n6. Checking audit logs in database...")
    
    try:
        conn = await asyncpg.connect(**DB_CONFIG)
        
        query = """
        SELECT action, success, email, ip_address, user_agent, created_at, details
        FROM audit_log
        WHERE email = $1
        ORDER BY created_at DESC
        LIMIT 5
        """
        
        rows = await conn.fetch(query, email)
        
        if rows:
            print(f"   ✓ Found {len(rows)} audit log entries:")
            for row in rows:
                print(f"      - {row['action']}: success={row['success']}, "
                      f"ip={row['ip_address']}, time={row['created_at']}")
        else:
            print(f"   ✗ No audit logs found for {email}")
        
        await conn.close()
        return len(rows) > 0
        
    except Exception as e:
        print(f"   ✗ Error checking audit logs: {e}")
        return False


async def test_metrics():
    """Test metrics endpoint."""
    print("\n7. Testing metrics endpoint (unversioned)...")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/metrics")
        assert response.status_code == 200
        
        # Check for audit metrics
        metrics_text = response.text
        if "audit_events_total" in metrics_text:
            print("   ✓ Audit metrics found in Prometheus output")
            
            # Extract audit metrics
            for line in metrics_text.split('\n'):
                if line.startswith('audit_events_total'):
                    print(f"      {line}")
        else:
            print("   ✗ Audit metrics not found")


async def run_tests():
    """Run all tests."""
    print("=" * 60)
    print("Testing Audit Logging and API Versioning Implementation")
    print("=" * 60)
    
    try:
        # Test health
        await test_health_endpoint()
        
        # Test authentication flow
        async with httpx.AsyncClient() as client:
            # Signup
            signup_data, test_user = await test_signup(client)
            email = signup_data['user']['email']
            access_token = signup_data['session']['access_token']
            refresh_token = signup_data['session']['refresh_token']
            
            # Signin
            signin_data = await test_signin(client, email, test_user['password'])
            
            # Get user
            user_data = await test_get_user(client, access_token)
            
            # Signout
            await test_signout(client, refresh_token)
        
        # Check audit logs
        audit_logs_exist = await check_audit_logs(email)
        
        # Check metrics
        await test_metrics()
        
        print("\n" + "=" * 60)
        if audit_logs_exist:
            print("✓ All tests passed!")
            print("✓ Audit logging is working")
            print("✓ API versioning is working")
        else:
            print("✗ Some tests failed - check audit logs")
        print("=" * 60)
        
        return 0 if audit_logs_exist else 1
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(run_tests()))
