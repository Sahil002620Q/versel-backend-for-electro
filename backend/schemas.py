from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from models import UserRole, ListingStatus, ListingCondition, RequestStatus

# User Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None

class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.BUYER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    role: UserRole
    created_at: datetime
    
    class Config:
        from_attributes = True

# Listing Schemas
class ListingBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    condition: ListingCondition
    working_parts: Optional[str] = None
    price: float
    location: str
    photos: Optional[List[str]] = []

class ListingCreate(ListingBase):
    pass

class ListingUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    status: Optional[ListingStatus] = None
    photos: Optional[List[str]] = None

class ListingResponse(ListingBase):
    id: int
    seller_id: int
    status: ListingStatus
    created_at: datetime
    seller: UserResponse
    
    class Config:
        from_attributes = True

# Buy Request Schemas
class BuyRequestCreate(BaseModel):
    listing_id: int

class BuyRequestResponse(BaseModel):
    id: int
    listing_id: int
    buyer_id: int
    seller_id: int
    status: RequestStatus
    commission_status: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# Token Schema
class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
