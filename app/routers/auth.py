from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token, get_password_hash, verify_password, get_current_user, TokenData
from app.models.schemas import UserLogin, UserRegister, Token
from app.db.mongo_utils import mongo_service
from datetime import timedelta

router = APIRouter()

@router.post("/register", response_model=Token, summary="User Onboarding", description="Registers a new research entity with a specific role and generates an initial access token.")
async def register(user: UserRegister):
    # Check if user exists in Mongo
    collection = mongo_service.db.get_collection("users")
    existing_user = await collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Hash password and save
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    user_dict["hashed_password"] = hashed_password
    del user_dict["password"]
    
    await collection.insert_one(user_dict)
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role}
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@router.post("/login", response_model=Token, summary="System Access", description="Authenticates credentials and issues a bearer token for secure session management.")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    collection = mongo_service.db.get_collection("users")
    user = await collection.find_one({"email": form_data.username})
    
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": user["email"], "role": user["role"]}
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user["role"]}

@router.get("/me", summary="Identity Verification", description="Decodes the current session's token to return investigator identity and authorization level.")
async def read_users_me(current_user: TokenData = Depends(get_current_user)):
    return current_user
