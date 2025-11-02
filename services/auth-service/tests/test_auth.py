from fastapi.testclient import TestClient

from app.app import app

client = TestClient(app)


def test_read_root():
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_register_user():
    """Test user registration"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123",
            "full_name": "Test User",
        },
    )
    assert response.status_code in [200, 201]


def test_login():
    """Test user login"""
    # First register
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "login@example.com",
            "password": "testpassword123",
            "full_name": "Login User",
        },
    )

    # Then login
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "login@example.com", "password": "testpassword123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_invalid_login():
    """Test login with invalid credentials"""
    response = client.post(
        "/api/v1/auth/login",
        data={"username": "invalid@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
