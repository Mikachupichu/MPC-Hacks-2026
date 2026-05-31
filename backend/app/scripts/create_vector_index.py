"""Create Atlas Vector Search index for custom_rules collection.

This script creates a vector search index on the rule_embedding field
in the custom_rules collection, optimized for Cosine similarity.

Usage:
    python -m app.scripts.create_vector_index

Prerequisites:
    - MongoDB Atlas cluster (not a local instance - Atlas Search is cloud-only)
    - Network access configured
    - pymongo installed
"""

import asyncio

from motor.motor_asyncio import AsyncIOMotorClient

MONGODB_URI = "mongodb://localhost:27017"
DB_NAME = "mpc_hacks_2026"


async def create_index():
    """Create the vector search index for custom rules."""
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client[DB_NAME]
    collection = db["custom_rules"]

    # Define the vector search index model
    index_model = {
        "name": "custom_rules_vector_index",
        "type": "vectorSearch",
        "definition": {
            "fields": [
                {
                    "type": "vector",
                    "path": "rule_embedding",
                    "numDimensions": 1536,
                    "similarity": "cosine",
                }
            ]
        },
    }

    try:
        # Create the index via the create_search_index method (Atlas-only)
        # Note: This only works on MongoDB Atlas clusters, not local instances
        result = await collection.create_search_index(index_model)
        print(f"✓ Created vector search index: {result}")

    except Exception as e:
        error_msg = str(e)
        if "not supported" in error_msg.lower() or "atlas" in error_msg.lower():
            print(f"ℹ  Vector search requires MongoDB Atlas (not a local instance).")
            print(f"   To create the index manually in Atlas UI:")
            print(f"   1. Go to your Atlas cluster → Search → Create Index")
            print(f"   2. Use the following JSON definition:")
            print(f"{_format_index_json(index_model)}")
            print(f"\n   Or run this command in mongosh against your Atlas cluster:")
            print(f'   db.custom_rules.createSearchIndex({{\n'
                  f'     "name": "custom_rules_vector_index",\n'
                  f'     "type": "vectorSearch",\n'
                  f'     "definition": {{\n'
                  f'       "fields": [{{\n'
                  f'         "type": "vector",\n'
                  f'         "path": "rule_embedding",\n'
                  f'         "numDimensions": 1536,\n'
                  f'         "similarity": "cosine"\n'
                  f'       }}]\n'
                  f'     }}\n'
                  f'   }})')
        else:
            print(f"✗ Error creating index: {error_msg}")

    client.close()


def _format_index_json(index_model: dict) -> str:
    import json
    return json.dumps(index_model, indent=2)


def main():
    """Run the vector index creation."""
    asyncio.run(create_index())


if __name__ == "__main__":
    main()
