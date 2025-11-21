# Test configuration
import os
import sys
from pathlib import Path

# Add parent directory (auth-service) to sys.path so 'app' can be imported
service_dir = Path(__file__).parent.parent
sys.path.insert(0, str(service_dir))

# Set test environment variables
os.environ["DATABASE_URL"] = "sqlite:///./test.db"
os.environ["JWT_SECRET"] = "test-secret-key"
os.environ["VAULT_ADDR"] = "http://localhost:8200"
os.environ["VAULT_TOKEN"] = "test-token"
