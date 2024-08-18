from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from datetime import datetime, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from jose import JWTError, jwt
from passlib.context import CryptContext
from typing import List, Optional

# Database Setup
client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["calendar_app"]

# FastAPI setup
app = FastAPI()


origins =["https://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins = origins,
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

# security
SECRET_KEY = "YOUR_SECRET_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated = "auto")
oauth2_scheme = OAuth2PasswordBearer(tokenURL = "token")


# user 
class User(BaseModel):
    username : str
    full_name : Optional[str] = None
    email : Optional[str] = None
    hashed_password : str
    disabled : Optional[bool] = None
    role : str

class UserInDB(User):
    hashed_password: str

class Token(BaseModel):
    access_token : str
    token_type = str

class TokenData(BaseModel):
    username : Optional[str] = None

class Event(BaseModel):
    title: str
    description: str
    start_time : datetime
    end_time : datetime
    user_defined: bool
    owner: str

# helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_user(db, username: str):
    user = await db["users"].find_one({"username": username})
    if user:
        return UserInDB(**user)

async def authenticate_user(db, username: str, password : str):
    user =await get_user(db, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + expires_delta(minutes = 15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm = ALGORITHM)
    return encoded_jwt

async def get_current_user(db = Depends(), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail="could not validate credentials", headers={"WWW-Authenticate": "Bearer"},)
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms = [ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username = username)
    except JWTError:
        raise credentials_exception
    return User

async def get_current_active_user(current_user: User = Depends(get_current_user)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    return current_user

#routes
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password", headers={"WWW-Authinticate": "Bearer"},)
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "Bearer"}

@app.post("/users/", response_model=User)
async def create_user(user: User):
    hashed_password = get_password_hash(user.hashed_password)
    user_data = user.dict()
    user_data["hashed_password"] = hashed_password
    await db["users"].insert_one(user_data)
    return user

@app.post("/events/", response_model= dict)
async def create_event(event: Event, current_user : User = Depends(get_current_active_user)):
    event_data = event.dict()
    event_data["owner"] = current_user.username
    result = await db["events"].insert_one(event_data)
    return {"id": str(result.inserted_id)}

@app.get("/events/", response_model=List[Event])
async def get_events(current_user: User = Depends(get_current_active_user)):
    events = await db["events"].find({"owner": current_user.username}).to_list(100)
    return events

@app.get("/admin/events/", response_model=List[Event])
async def get_all_events(current_user: User = Depends(get_current_admin_user)):
    events = await db["events"].find().to_list(100)
    return events