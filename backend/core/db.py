"""MongoDB client + shared db handle."""
from motor.motor_asyncio import AsyncIOMotorClient
from .config import MONGO_URL, DB_NAME

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]


async def create_indexes():
    await db.users.create_index("email", unique=True)
    await db.invoices.create_index([("user_id", 1), ("invoice_date", -1)])
    await db.invoices.create_index([("user_id", 1), ("type", 1)])
    await db.upi_transactions.create_index([("user_id", 1), ("date", -1)])
    await db.chat_messages.create_index([("user_id", 1), ("session_id", 1), ("created_at", 1)])
    await db.client_links.create_index([("ca_id", 1), ("vendor_id", 1)], unique=True)
    await db.filings.create_index([("ca_id", 1), ("vendor_id", 1), ("period", 1)], unique=True)
