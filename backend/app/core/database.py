from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client: AsyncIOMotorClient | None = None


async def get_database():
    return client[settings.mongodb_db_name]


async def connect_db():
    global client
    client = AsyncIOMotorClient(settings.mongodb_uri)
    try:
        await client.admin.command("ping")
        print(f"Connected to MongoDB: {settings.mongodb_uri}")
    except Exception as e:
        print(f"WARNING: MongoDB connection failed ({e}). Server will start, but DB routes won't work until MongoDB is available.")


async def close_db():
    global client
    if client:
        client.close()
    print("MongoDB connection closed")
