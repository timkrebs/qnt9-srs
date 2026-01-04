#!/usr/bin/env python3
"""
Migration script to move existing users from custom auth to Supabase Auth.

This script:
1. Reads existing users from public.users table
2. For each user, sends a password reset email via Supabase
3. Creates corresponding user_profiles entries
4. Provides migration status report

IMPORTANT: This script does NOT migrate passwords as they cannot be transferred.
Users must reset their passwords via the email link they receive.

Usage:
    python migrate_to_supabase.py --dry-run  # Test without making changes
    python migrate_to_supabase.py            # Execute migration
"""

import argparse
import asyncio
# Configuration from environment or defaults
import os
import sys
from datetime import datetime
from typing import Any, Dict, List

import asyncpg
from dotenv import load_dotenv
from gotrue.errors import AuthApiError

from supabase import Client, create_client

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:pass@localhost:5432/qnt9_db"
)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.total_users = 0
        self.success_count = 0
        self.already_exists_count = 0
        self.error_count = 0
        self.errors: List[Dict[str, Any]] = []

    def print_report(self):
        """Print migration summary report."""
        print("\n" + "=" * 60)
        print("MIGRATION SUMMARY")
        print("=" * 60)
        print(f"Total users processed:     {self.total_users}")
        print(f"Successfully migrated:     {self.success_count}")
        print(f"Already existed:           {self.already_exists_count}")
        print(f"Errors:                    {self.error_count}")
        print("=" * 60)

        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  - {error['email']}: {error['error']}")

        success_rate = (
            (self.success_count / self.total_users * 100) if self.total_users > 0 else 0
        )
        print(f"\nSuccess rate: {success_rate:.1f}%")


async def fetch_existing_users(conn: asyncpg.Connection) -> List[Dict[str, Any]]:
    """
    Fetch all users from the legacy public.users table.

    Args:
        conn: Database connection

    Returns:
        List of user records
    """
    query = """
        SELECT 
            id, 
            email, 
            full_name, 
            tier, 
            email_verified,
            created_at,
            last_login,
            subscription_start,
            subscription_end,
            stripe_customer_id,
            stripe_subscription_id,
            metadata
        FROM users
        WHERE is_active = true
        ORDER BY created_at ASC
    """

    rows = await conn.fetch(query)
    return [dict(row) for row in rows]


async def create_supabase_user(
    supabase: Client,
    email: str,
    full_name: str = None,
    tier: str = "free",
    email_verified: bool = False,
) -> Dict[str, Any]:
    """
    Create user in Supabase Auth via Admin API.

    Since we can't migrate passwords, we create the user with a random password
    and immediately trigger a password reset email.

    Args:
        supabase: Supabase client
        email: User email
        full_name: User's full name
        tier: Subscription tier
        email_verified: Whether email is verified

    Returns:
        Created user data

    Raises:
        AuthApiError: If user creation fails
    """
    import secrets

    # Generate a random password (user will reset it)
    temp_password = secrets.token_urlsafe(32)

    # Create user in Supabase Auth
    response = supabase.auth.admin.create_user(
        {
            "email": email.lower(),
            "password": temp_password,
            "email_confirm": email_verified,
            "user_metadata": {
                "full_name": full_name,
                "tier": tier,
                "migrated_at": datetime.now().isoformat(),
            },
        }
    )

    if not response.user:
        raise Exception("User creation failed")

    return {
        "id": response.user.id,
        "email": response.user.email,
    }


async def send_password_reset_email(supabase: Client, email: str) -> bool:
    """
    Send password reset email to user.

    Args:
        supabase: Supabase client
        email: User email

    Returns:
        True if email sent successfully
    """
    try:
        supabase.auth.reset_password_for_email(
            email.lower(),
            {"redirect_to": f"{FRONTEND_URL}/reset-password?migrated=true"},
        )
        return True
    except Exception as e:
        print(f"  Warning: Failed to send reset email to {email}: {e}")
        return False


async def create_user_profile(
    conn: asyncpg.Connection,
    user_id: str,
    full_name: str,
    tier: str,
    subscription_start: datetime,
    subscription_end: datetime,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    metadata: dict,
) -> None:
    """
    Create user profile in user_profiles table.

    Args:
        conn: Database connection
        user_id: User UUID from Supabase
        full_name: User's full name
        tier: Subscription tier
        subscription_start: Subscription start date
        subscription_end: Subscription end date
        stripe_customer_id: Stripe customer ID
        stripe_subscription_id: Stripe subscription ID
        metadata: Additional metadata
    """
    query = """
        INSERT INTO user_profiles (
            id, tier, full_name, subscription_start, subscription_end,
            stripe_customer_id, stripe_subscription_id, metadata,
            created_at, updated_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW())
        ON CONFLICT (id) DO NOTHING
    """

    await conn.execute(
        query,
        user_id,
        tier,
        full_name,
        subscription_start,
        subscription_end,
        stripe_customer_id,
        stripe_subscription_id,
        metadata,
    )


async def migrate_user(
    supabase: Client,
    db_conn: asyncpg.Connection,
    user: Dict[str, Any],
    stats: MigrationStats,
    dry_run: bool = False,
) -> bool:
    """
    Migrate a single user to Supabase.

    Args:
        supabase: Supabase client
        db_conn: Database connection
        user: User data from legacy table
        stats: Migration statistics
        dry_run: If True, don't actually make changes

    Returns:
        True if migration successful
    """
    email = user["email"]
    print(f"Migrating user: {email}")

    try:
        if dry_run:
            print(f"  [DRY RUN] Would create Supabase user for {email}")
            stats.success_count += 1
            return True

        # Create user in Supabase
        supabase_user = await create_supabase_user(
            supabase,
            email=email,
            full_name=user.get("full_name"),
            tier=user.get("tier", "free"),
            email_verified=user.get("email_verified", False),
        )

        print(f"  ✓ Created Supabase user: {supabase_user['id']}")

        # Create user profile
        await create_user_profile(
            db_conn,
            user_id=supabase_user["id"],
            full_name=user.get("full_name"),
            tier=user.get("tier", "free"),
            subscription_start=user.get("subscription_start"),
            subscription_end=user.get("subscription_end"),
            stripe_customer_id=user.get("stripe_customer_id"),
            stripe_subscription_id=user.get("stripe_subscription_id"),
            metadata=user.get("metadata", {}),
        )

        print("  ✓ Created user profile")

        # Send password reset email
        email_sent = await send_password_reset_email(supabase, email)
        if email_sent:
            print("  ✓ Sent password reset email")

        stats.success_count += 1
        return True

    except AuthApiError as e:
        if "already registered" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"  ⚠ User already exists in Supabase: {email}")
            stats.already_exists_count += 1
            return True
        else:
            print(f"  ✗ Supabase error: {e}")
            stats.error_count += 1
            stats.errors.append({"email": email, "error": str(e)})
            return False

    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        stats.error_count += 1
        stats.errors.append({"email": email, "error": str(e)})
        return False


async def run_migration(dry_run: bool = False) -> None:
    """
    Execute the migration process.

    Args:
        dry_run: If True, simulate migration without making changes
    """
    print("=" * 60)
    print("SUPABASE MIGRATION SCRIPT")
    print("=" * 60)

    if dry_run:
        print("Running in DRY RUN mode - no changes will be made\n")
    else:
        print("WARNING: This will migrate users to Supabase Auth")
        print("Users will receive password reset emails\n")
        response = input("Continue? (yes/no): ")
        if response.lower() != "yes":
            print("Migration cancelled")
            return

    # Validate configuration
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        sys.exit(1)

    stats = MigrationStats()

    try:
        # Connect to database
        print("\nConnecting to database...")
        db_conn = await asyncpg.connect(DATABASE_URL)
        print("✓ Connected to PostgreSQL")

        # Initialize Supabase client
        print("Initializing Supabase client...")
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print("✓ Supabase client initialized\n")

        # Fetch existing users
        print("Fetching existing users...")
        users = await fetch_existing_users(db_conn)
        stats.total_users = len(users)
        print(f"Found {stats.total_users} users to migrate\n")

        if stats.total_users == 0:
            print("No users to migrate")
            return

        # Migrate each user
        for i, user in enumerate(users, 1):
            print(f"\n[{i}/{stats.total_users}]", end=" ")
            await migrate_user(supabase, db_conn, user, stats, dry_run)

        # Print summary
        stats.print_report()

        if not dry_run and stats.success_count > 0:
            print("\n" + "=" * 60)
            print("NEXT STEPS:")
            print("=" * 60)
            print("1. Users will receive password reset emails")
            print("2. Verify the migration in Supabase dashboard")
            print("3. Test authentication with a migrated user")
            print("4. Once verified, consider archiving the old users table")
            print("5. Update your application to use Supabase auth endpoints")
            print("=" * 60)

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    finally:
        if "db_conn" in locals():
            await db_conn.close()
            print("\n✓ Database connection closed")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Migrate users from custom auth to Supabase Auth"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without making changes",
    )
    args = parser.parse_args()

    asyncio.run(run_migration(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
