from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

client: AsyncIOMotorClient | None = None


def _build_client():
    kwargs = {}
    if "mongodb+srv" in settings.mongodb_uri:
        kwargs["tlsInsecure"] = True
    return AsyncIOMotorClient(settings.mongodb_uri, **kwargs)


async def get_database():
    return client[settings.mongodb_db_name]


async def connect_db():
    global client
    client = _build_client()
    try:
        await client.admin.command("ping")
        print(f"Connected to MongoDB: {settings.mongodb_uri}")
    except Exception as e:
        print(
            f"WARNING: MongoDB connection failed ({e}). "
            "Server will start, but DB routes won't work until MongoDB is available."
        )


async def close_db():
    global client
    if client:
        client.close()
    print("MongoDB connection closed")


async def get_collection(name: str):
    db = await get_database()
    return db[name]
