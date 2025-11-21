"""
Root conftest.py for QNT9-SRS project.

This file helps pytest discover and configure tests across multiple services.
Only adds the current service to path based on the test file being run.
"""

import sys
from pathlib import Path


def pytest_configure(config):
    """
    Configure pytest to add service directories to sys.path dynamically.

    This only adds the service directory that contains the test being run,
    avoiding conflicts when multiple services have an 'app' module.
    """
    root_dir = Path(__file__).parent

    # Always add common directory
    sys.path.insert(0, str(root_dir / "common"))
    sys.path.insert(0, str(root_dir))


def pytest_collection_modifyitems(session, config, items):
    """
    Add the appropriate service directory to sys.path before tests run.

    This examines each test file and adds its service directory to the path.
    """
    root_dir = Path(__file__).parent
    services_added = set()

    for item in items:
        test_path = Path(item.fspath)

        # Check if test is in a service directory
        if "services" in test_path.parts:
            try:
                services_idx = test_path.parts.index("services")
                if services_idx + 1 < len(test_path.parts):
                    service_name = test_path.parts[services_idx + 1]
                    service_path = root_dir / "services" / service_name

                    if service_path.exists() and service_name not in services_added:
                        sys.path.insert(0, str(service_path))
                        services_added.add(service_name)
            except (ValueError, IndexError):
                pass
