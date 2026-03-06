from sqlalchemy import Column, String, Integer, Float, Enum, ForeignKey, DateTime, Text, ARRAY
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from database import Base

class UserRole(str, enum.Enum):
    SELLER = "seller"
    BUYER = "buyer"
    ADMIN = "admin"

class ListingStatus(str, enum.Enum):
    ACTIVE = "active"
    SOLD = "sold"
    EXPIRED = "expired"

class ListingCondition(str, enum.Enum):
    NEW = "new"
    USED = "used"
    BROKEN = "broken"
    FOR_PARTS = "for_parts"

class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True)
    phone = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.BUYER)
    location = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    listings = relationship("Listing", back_populates="seller", foreign_keys="Listing.seller_id")
    buy_requests_sent = relationship("BuyRequest", back_populates="buyer", foreign_keys="BuyRequest.buyer_id")
    buy_requests_received = relationship("BuyRequest", back_populates="seller", foreign_keys="BuyRequest.seller_id")

class Listing(Base):
    __tablename__ = "listings"
    
    id = Column(Integer, primary_key=True, index=True)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String, nullable=False)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    condition = Column(Enum(ListingCondition), nullable=False)
    working_parts = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    status = Column(Enum(ListingStatus), default=ListingStatus.ACTIVE)
    photos = Column(ARRAY(String), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    seller = relationship("User", back_populates="listings", foreign_keys=[seller_id])
    buy_requests = relationship("BuyRequest", back_populates="listing")

class BuyRequest(Base):
    __tablename__ = "buy_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("listings.id"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDING)
    commission_status = Column(String, nullable=True)  # Metadata only
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    listing = relationship("Listing", back_populates="buy_requests")
    buyer = relationship("User", back_populates="buy_requests_sent", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="buy_requests_received", foreign_keys=[seller_id])
