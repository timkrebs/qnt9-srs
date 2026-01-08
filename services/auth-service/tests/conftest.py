# Test configuration
import os
import sys
from pathlib import Path

# Add parent directory (auth-service) to sys.path so 'app' can be imported
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

# Set test environment variables BEFORE importing app modules
os.environ["DATABASE_URL"] = "postgresql://finio:finiopassword@localhost:5432/finio_test"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only-32chars"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["PASSWORD_HASH_ROUNDS"] = "4"  # Lower rounds for faster tests
os.environ["VAULT_ADDR"] = "http://localhost:8200"
os.environ["VAULT_TOKEN"] = "test-token"
os.environ["ENVIRONMENT"] = "test"
os.environ["LOG_LEVEL"] = "WARNING"

# Supabase test environment variables (mock values for testing)
os.environ["SUPABASE_URL"] = "https://test-project.supabase.co"
os.environ["SUPABASE_KEY"] = "test-anon-key-for-testing-purposes-only"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = (
    "test-service-role-key-for-testing-purposes-only"
)
os.environ["SUPABASE_JWT_SECRET"] = (
    "test-jwt-secret-key-for-testing-purposes-only-must-be-at-least-32-chars"
)
