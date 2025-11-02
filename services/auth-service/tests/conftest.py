# Test configuration
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["VAULT_ADDR"] = "http://localhost:8200"
os.environ["VAULT_TOKEN"] = "test-token"
