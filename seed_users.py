import os
import asyncio
from app.db.mongo_utils import mongo_service
from app.core.security import get_password_hash

async def seed_users():
    print("--- Seeding User Data ---")
    collection = mongo_service.db.get_collection("users")
    
    users = [
        {
            "email": "namitha@neural-nexus.dev",
            "full_name": "Namitha",
            "password": "namitha_password", # Plain for hashing
            "role": "RESEARCHER"
        },
        {
            "email": "harshan@neural-nexus.dev",
            "full_name": "Harshan",
            "password": "harshan_password",
            "role": "RESEARCHER"
        }
    ]
    
    for user_data in users:
        existing = await collection.find_one({"email": user_data["email"]})
        if existing:
            print(f"User {user_data['email']} already exists. Skipping.")
            continue
            
        hashed_password = get_password_hash(user_data["password"])
        user_doc = {
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "hashed_password": hashed_password,
            "role": user_data["role"]
        }
        
        await collection.insert_one(user_doc)
        print(f"Created user: {user_data['full_name']} ({user_data['email']})")

    print("--- User Seeding Complete ---")

if __name__ == "__main__":
    asyncio.run(seed_users())
