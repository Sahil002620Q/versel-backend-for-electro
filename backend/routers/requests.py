from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
import models
import schemas
from auth import get_current_user

router = APIRouter(prefix="/requests", tags=["Buy Requests"])

@router.post("/", response_model=schemas.BuyRequestResponse, status_code=status.HTTP_201_CREATED)
def create_buy_request(
    request_data: schemas.BuyRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get listing
    listing = db.query(models.Listing).filter(models.Listing.id == request_data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")
    
    # Check if listing is active
    if listing.status != models.ListingStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Listing is not active")
    
    # Check if user is not the seller
    if listing.seller_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot buy your own listing")
    
    # Check for existing pending request
    existing_request = db.query(models.BuyRequest).filter(
        models.BuyRequest.listing_id == request_data.listing_id,
        models.BuyRequest.buyer_id == current_user.id,
        models.BuyRequest.status == models.RequestStatus.PENDING
    ).first()
    
    if existing_request:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already have a pending request for this listing")
    
    # Create buy request
    new_request = models.BuyRequest(
        listing_id=request_data.listing_id,
        buyer_id=current_user.id,
        seller_id=listing.seller_id,
        commission_status="pending_calculation"  # Metadata only
    )
    
    db.add(new_request)
    db.commit()
    db.refresh(new_request)
    return new_request

@router.get("/my-requests", response_model=List[schemas.BuyRequestResponse])
def get_my_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get all requests sent by current user
    requests = db.query(models.BuyRequest).filter(
        models.BuyRequest.buyer_id == current_user.id
    ).all()
    return requests

@router.get("/incoming", response_model=List[schemas.BuyRequestResponse])
def get_incoming_requests(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Get all requests received by current user (as seller)
    requests = db.query(models.BuyRequest).filter(
        models.BuyRequest.seller_id == current_user.id
    ).all()
    return requests

@router.put("/{request_id}/accept", response_model=schemas.BuyRequestResponse)
def accept_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    buy_request = db.query(models.BuyRequest).filter(models.BuyRequest.id == request_id).first()
    if not buy_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Only seller can accept
    if buy_request.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Update status
    buy_request.status = models.RequestStatus.ACCEPTED
    buy_request.commission_status = "commission_logged"  # Metadata
    
    db.commit()
    db.refresh(buy_request)
    return buy_request

@router.put("/{request_id}/reject", response_model=schemas.BuyRequestResponse)
def reject_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    buy_request = db.query(models.BuyRequest).filter(models.BuyRequest.id == request_id).first()
    if not buy_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Only seller can reject
    if buy_request.seller_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Update status
    buy_request.status = models.RequestStatus.REJECTED
    
    db.commit()
    db.refresh(buy_request)
    return buy_request

@router.put("/{request_id}/complete", response_model=schemas.BuyRequestResponse)
def complete_request(
    request_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    buy_request = db.query(models.BuyRequest).filter(models.BuyRequest.id == request_id).first()
    if not buy_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")
    
    # Either buyer or seller can mark as complete
    if buy_request.seller_id != current_user.id and buy_request.buyer_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    # Update status and mark listing as sold
    buy_request.status = models.RequestStatus.COMPLETED
    
    listing = db.query(models.Listing).filter(models.Listing.id == buy_request.listing_id).first()
    if listing:
        listing.status = models.ListingStatus.SOLD
    
    db.commit()
    db.refresh(buy_request)
    return buy_request
