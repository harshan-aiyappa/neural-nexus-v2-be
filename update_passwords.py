import asyncio
from app.db.mongo_utils import mongo_service
from app.core.security import get_password_hash

async def update_passwords():
    print("--- Updating User Passwords to '12345' ---")
    collection = mongo_service.db.get_collection("users")
    
    new_password = "12345"
    hashed_password = get_password_hash(new_password)
    
    emails = ["namitha@neural-nexus.dev", "harshan@neural-nexus.dev"]
    
    for email in emails:
        result = await collection.update_one(
            {"email": email},
            {"$set": {"hashed_password": hashed_password}}
        )
        if result.modified_count > 0:
            print(f"Updated password for {email}")
        else:
            print(f"User {email} not found or password already set to this hash.")

    print("--- Password Update Complete ---")

if __name__ == "__main__":
    asyncio.run(update_passwords())
