"""CLI-based idempotent seed script for NyaySetu Pro Firestore database.

Run this script ONCE per environment to seed the fresh Firestore database with:
- Case Types, Laws, Districts, Talukas, Courts, Police Stations
- Pricing Plans
- Initial Super Admin account
- Canonical Legal Templates (from _source_docs/)

Usage:
    cd backend
    python seed_firestore.py

Requires FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, and FIREBASE_PRIVATE_KEY
in the environment, OR FIRESTORE_EMULATOR_HOST for local development.
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

# Load .env first
load_dotenv()

# We set TEMPLATE_AUTO_SEED to true for this script so the underlying functions know it's intentional
os.environ["TEMPLATE_AUTO_SEED"] = "true"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nyaysetu.seed")

async def main():
    logger.info("Initializing Firestore seed...")
    
    # Import server which will initialize `db` via firestore_client
    import server
    
    if server.db is None:
        logger.error("Database client is None. Are Firebase credentials or emulator host set?")
        sys.exit(1)
        
    logger.info("Seeding Plans...")
    await server.seed_plans()
    
    logger.info("Seeding Catalogs...")
    await server.seed_catalogs()
    
    logger.info("Seeding Super Admin...")
    await server.seed_super_admin()
    
    logger.info("Seeding Templates...")
    await server.seed_templates()
    
    logger.info("Migrating Templates to Revisions...")
    await server.migrate_templates_to_revisions(server.db)
    
    logger.info("Firestore seed complete.")
    
if __name__ == "__main__":
    asyncio.run(main())
