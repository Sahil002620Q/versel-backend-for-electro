from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
import models
import schemas
from auth import get_current_user, require_role

router = APIRouter(prefix="/listings", tags=["Listings"])

@router.get("/", response_model=List[schemas.ListingResponse])
def get_listings(
    category: Optional[str] = None,
    brand: Optional[str] = None,
    model: Optional[str] = None,
    condition: Optional[models.ListingCondition] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    location: Optional[str] = None,
    status: Optional[models.ListingStatus] = models.ListingStatus.ACTIVE,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(models.Listing)
    
    # Apply filters
    if category:
        query = query.filter(models.Listing.category.ilike(f"%{category}%"))
    if brand:
        query = query.filter(models.Listing.brand.ilike(f"%{brand}%"))
    if model:
        query = query.filter(models.Listing.model.ilike(f"%{model}%"))
    if condition:
        query = query.filter(models.Listing.condition == condition)
    if min_price is not None:
        query = query.filter(models.Listing.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Listing.price <= max_price)
    if location:
        query = query.filter(models.Listing.location.ilike(f"%{location}%"))
    if status:
        query = query.filter(models.Listing.status == status)
    
    listings = query.offset(skip).limit(limit).all()
    return listings

@router.get("/{listing_id}", response_model=schemas.ListingResponse)
def get_listing(listing_id: int, db: Session = Depends(get_db)):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    return listing

@router.post("/", response_model=schemas.ListingResponse, status_code=status.HTTP_201_CREATED)
def create_listing(
    listing_data: schemas.ListingCreate,
    current_user: models.User = Depends(require_role([models.UserRole.SELLER, models.UserRole.ADMIN])),
    db: Session = Depends(get_db)
):
    new_listing = models.Listing(
        **listing_data.dict(),
        seller_id=current_user.id
    )
    
    db.add(new_listing)
    db.commit()
    db.refresh(new_listing)
    return new_listing

@router.put("/{listing_id}", response_model=schemas.ListingResponse)
def update_listing(
    listing_id: int,
    listing_data: schemas.ListingUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    
    # Only seller or admin can update
    if listing.seller_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Update fields
    for field, value in listing_data.dict(exclude_unset=True).items():
        setattr(listing, field, value)
    
    db.commit()
    db.refresh(listing)
    return listing

@router.delete("/{listing_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_listing(
    listing_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    listing = db.query(models.Listing).filter(models.Listing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    
    # Only seller or admin can delete
    if listing.seller_id != current_user.id and current_user.role != models.UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    db.delete(listing)
    db.commit()
    return None
