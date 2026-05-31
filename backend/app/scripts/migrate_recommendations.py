"""Migration: Add recommendation field to all non-not_required transactions
and strip any "Recommendation: ... —" prefix from reasoning fields.

Run: python -m app.scripts.migrate_recommendations
"""

"""Migration: Set recommendation field (Approve/Decline) on all transactions
and strip any "Recommendation: ... —" prefix from reasoning fields.

IMPORTANT: recommendation is the AI agent's binary call — "Approve" or "Decline" only.
"Pending" belongs on approval_status (the human workflow state), never on recommendation.

Run: python -m app.scripts.migrate_recommendations
"""

import asyncio
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

env_path = Path(__file__).resolve().parents[2] / ".env.local"
load_dotenv(env_path)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB_NAME", "mpc_hacks_2026")

# Pattern matches "Recommendation: <anything — >" or "Recommendation: <anything> — " at the start
REC_PREFIX_RE = re.compile(r"^Recommendation:\s*(?:Pending|Approve|Decline)\s*[—–-]?\s*")


async def migrate():
    kwargs = {"serverSelectionTimeoutMS": 30000}
    if "mongodb+srv" in MONGODB_URI:
        kwargs["tlsInsecure"] = True

    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient(MONGODB_URI, **kwargs)
    db = client[DB_NAME]
    collection = db["transactions"]

    total = await collection.count_documents({})
    print(f"Total transactions: {total}")

    # Step 1: Set recommendation on missing/null transactions
    # approved → "Approve", denied → "Decline"
    for status, rec in [("approved", "Approve"), ("denied", "Decline")]:
        for field in [None, {"$exists": False}]:
            query = {"approval_status": status, "recommendation": field}
            result = await collection.update_many(query, {"$set": {"recommendation": rec}})
            if result.modified_count > 0:
                print(f"  Set recommendation='{rec}' for {result.modified_count} {status} transactions")

    # Step 2: Fix pending transactions — recommendation must NOT be "Pending"
    # Determine based on reasoning: suspicious patterns → "Decline", else "Approve"
    cursor = collection.find(
        {"approval_status": "pending", "$or": [
            {"recommendation": None},
            {"recommendation": "Pending"},
            {"recommendation": {"$exists": False}},
        ]},
        {"_id": 1, "reasoning": 1, "amount": 1},
    )
    pending_fixed = 0
    async for doc in cursor:
        reasoning = doc.get("reasoning", "")
        amount = doc.get("amount", 0)
        suspicious = any(kw in reasoning for kw in ["Unusual", "currency conversion", "violation"])
        if suspicious or amount > 10000:
            rec = "Decline"
        else:
            rec = "Approve"
        await collection.update_one(
            {"_id": doc["_id"]},
            {"$set": {"recommendation": rec}},
        )
        pending_fixed += 1

    if pending_fixed > 0:
        print(f"  Fixed {pending_fixed} pending transactions (recommendation set to Approve or Decline)")

    # Step 3: Fix any remaining "Pending" recommendation values (edge cases from bugs)
    result = await collection.update_many(
        {"recommendation": "Pending"},
        {"$set": {"recommendation": "Approve"}},
    )
    if result.modified_count > 0:
        print(f"  Fixed {result.modified_count} remaining 'Pending' recommendations → 'Approve'")

    # Step 4: Strip "Recommendation: ... —" prefix from reasoning fields
    cursor2 = collection.find({"reasoning": {"$regex": "^Recommendation:"}}, {"_id": 1, "reasoning": 1})
    cleaned = 0
    async for doc in cursor2:
        old = doc.get("reasoning", "")
        new = REC_PREFIX_RE.sub("", old).strip()
        if new != old:
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"reasoning": new}},
            )
            cleaned += 1

    print(f"  Stripped recommendation prefix from {cleaned} reasoning fields")

    # Summary
    still_pending_rec = await collection.count_documents({"recommendation": "Pending"})
    missing = await collection.count_documents(
        {"approval_status": {"$ne": "not_required"}, "recommendation": None},
    )
    missing_field = await collection.count_documents(
        {"approval_status": {"$ne": "not_required"}, "recommendation": {"$exists": False}},
    )

    print(f"\nDone. Remaining 'Pending' recommendations: {still_pending_rec}")
    print(f"Remaining missing recommendations: {missing + missing_field}")
    client.close()


if __name__ == "__main__":
    asyncio.run(migrate())
