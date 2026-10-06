"""Create or update the standalone RDP administrator account."""

from pathlib import Path
import sys

# Ensure backend/ is available on Python's import path even when this
# script is executed directly.
BACKEND_ROOT = Path(__file__).resolve().parents[1]

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import asyncio
import getpass

from sqlalchemy import select

from app.db.session import AsyncSessionLocal, engine
from app.models.user import User
from app.auth.password import hash_password


async def main() -> None:
    try:
        email = input("Admin email: ").strip().lower()
        full_name = input("Full name: ").strip() or None
        password = getpass.getpass("Password (min 8 chars): ")

        if len(password) < 8:
            raise SystemExit("Password too short")

        async with AsyncSessionLocal() as db:
            existing = (
                await db.execute(
                    select(User).where(User.email == email)
                )
            ).scalar_one_or_none()

            if existing:
                existing.hashed_password = hash_password(password)
                existing.is_active = True
                existing.is_admin = True
                existing.role = "admin"
                existing.full_name = full_name or existing.full_name

                print("Updated existing admin account.")
            else:
                db.add(
                    User(
                        email=email,
                        hashed_password=hash_password(password),
                        full_name=full_name,
                        role="admin",
                        is_active=True,
                        is_admin=True,
                    )
                )

                print("Created admin account.")

            await db.commit()

    finally:
        # Dispose pooled async connections while the asyncio
        # event loop is still alive.
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())