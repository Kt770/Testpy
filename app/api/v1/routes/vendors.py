from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.vendor import Vendor
from app.services.ai_service import ai_service

router = APIRouter()

@router.post("/", response_model=dict)
async def create_vendor(
    name: str,
    email: str,
    industry: Optional[str] = None,
    phone: Optional[str] = None,
    website: Optional[str] = None,
    country: str = "Saudi Arabia",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new vendor"""
    
    # Check if vendor already exists
    existing_vendor = db.query(Vendor).filter(Vendor.email == email).first()
    if existing_vendor:
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")
    
    # Generate vendor code
    vendor_code = f"VND-{datetime.now().strftime('%Y%m%d')}-{name[:3].upper()}"
    counter = 1
    while db.query(Vendor).filter(Vendor.vendor_code == vendor_code).first():
        vendor_code = f"VND-{datetime.now().strftime('%Y%m%d')}-{name[:3].upper()}-{counter:02d}"
        counter += 1
    
    vendor = Vendor(
        name=name,
        vendor_code=vendor_code,
        email=email,
        industry=industry,
        phone=phone,
        website=website,
        country=country
    )
    
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return {
        "success": True,
        "vendor_id": vendor.id,
        "vendor_code": vendor.vendor_code,
        "message": "Vendor created successfully"
    }

@router.get("/", response_model=List[dict])
async def list_vendors(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    search: Optional[str] = None,
    industry: Optional[str] = None,
    country: Optional[str] = None,
    status: Optional[str] = None,
    preferred_only: bool = False,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List vendors with filtering and search"""
    
    query = db.query(Vendor)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Vendor.name.ilike(f"%{search}%"),
                Vendor.vendor_code.ilike(f"%{search}%"),
                Vendor.email.ilike(f"%{search}%"),
                Vendor.industry.ilike(f"%{search}%")
            )
        )
    
    if industry:
        query = query.filter(Vendor.industry.ilike(f"%{industry}%"))
    
    if country:
        query = query.filter(Vendor.country.ilike(f"%{country}%"))
    
    if status:
        query = query.filter(Vendor.status == status)
    
    if preferred_only:
        query = query.filter(Vendor.preferred_vendor == True)
    
    vendors = query.offset(skip).limit(limit).all()
    
    # Format response
    vendor_list = []
    for vendor in vendors:
        vendor_data = {
            "id": vendor.id,
            "name": vendor.name,
            "vendor_code": vendor.vendor_code,
            "email": vendor.email,
            "phone": vendor.phone,
            "website": vendor.website,
            "industry": vendor.industry,
            "country": vendor.country,
            "overall_rating": vendor.overall_rating,
            "status": vendor.status,
            "preferred_vendor": vendor.preferred_vendor,
            "total_contracts": vendor.total_contracts,
            "total_contract_value": vendor.total_contract_value,
            "ai_recommendation_score": vendor.ai_recommendation_score,
            "compliance_status": vendor.compliance_status,
            "created_at": vendor.created_at,
            "last_interaction": vendor.last_interaction
        }
        vendor_list.append(vendor_data)
    
    return vendor_list

@router.get("/{vendor_id}", response_model=dict)
async def get_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get vendor details"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return {
        "id": vendor.id,
        "name": vendor.name,
        "legal_name": vendor.legal_name,
        "vendor_code": vendor.vendor_code,
        "email": vendor.email,
        "phone": vendor.phone,
        "website": vendor.website,
        "address_line1": vendor.address_line1,
        "address_line2": vendor.address_line2,
        "city": vendor.city,
        "state_province": vendor.state_province,
        "country": vendor.country,
        "postal_code": vendor.postal_code,
        "industry": vendor.industry,
        "business_type": vendor.business_type,
        "tax_id": vendor.tax_id,
        "registration_number": vendor.registration_number,
        "established_date": vendor.established_date,
        "annual_revenue": vendor.annual_revenue,
        "employee_count": vendor.employee_count,
        "credit_rating": vendor.credit_rating,
        "overall_rating": vendor.overall_rating,
        "quality_rating": vendor.quality_rating,
        "delivery_rating": vendor.delivery_rating,
        "cost_rating": vendor.cost_rating,
        "communication_rating": vendor.communication_rating,
        "ai_risk_assessment": vendor.ai_risk_assessment,
        "ai_capabilities_analysis": vendor.ai_capabilities_analysis,
        "ai_market_position": vendor.ai_market_position,
        "ai_recommendation_score": vendor.ai_recommendation_score,
        "certifications": vendor.certifications,
        "compliance_status": vendor.compliance_status,
        "insurance_verified": vendor.insurance_verified,
        "security_clearance": vendor.security_clearance,
        "status": vendor.status,
        "categories": vendor.categories,
        "preferred_vendor": vendor.preferred_vendor,
        "total_contracts": vendor.total_contracts,
        "total_contract_value": vendor.total_contract_value,
        "avg_contract_duration": vendor.avg_contract_duration,
        "last_contract_date": vendor.last_contract_date,
        "notes": vendor.notes,
        "created_at": vendor.created_at,
        "updated_at": vendor.updated_at,
        "last_interaction": vendor.last_interaction
    }

@router.put("/{vendor_id}", response_model=dict)
async def update_vendor(
    vendor_id: int,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update vendor information"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Update allowed fields
    allowed_fields = [
        'name', 'legal_name', 'email', 'phone', 'website',
        'address_line1', 'address_line2', 'city', 'state_province',
        'country', 'postal_code', 'industry', 'business_type',
        'tax_id', 'registration_number', 'established_date',
        'annual_revenue', 'employee_count', 'credit_rating',
        'certifications', 'compliance_status', 'insurance_verified',
        'security_clearance', 'status', 'categories', 'preferred_vendor',
        'notes'
    ]
    
    for field, value in updates.items():
        if field in allowed_fields and hasattr(vendor, field):
            setattr(vendor, field, value)
    
    vendor.updated_at = datetime.utcnow()
    vendor.last_interaction = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Vendor updated successfully"
    }

@router.post("/{vendor_id}/rating", response_model=dict)
async def rate_vendor(
    vendor_id: int,
    overall_rating: float,
    quality_rating: Optional[float] = None,
    delivery_rating: Optional[float] = None,
    cost_rating: Optional[float] = None,
    communication_rating: Optional[float] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Rate vendor performance"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Validate rating values (1-5 scale)
    if not (1 <= overall_rating <= 5):
        raise HTTPException(status_code=400, detail="Overall rating must be between 1 and 5")
    
    vendor.overall_rating = overall_rating
    if quality_rating is not None:
        vendor.quality_rating = quality_rating
    if delivery_rating is not None:
        vendor.delivery_rating = delivery_rating
    if cost_rating is not None:
        vendor.cost_rating = cost_rating
    if communication_rating is not None:
        vendor.communication_rating = communication_rating
    
    if notes:
        vendor.notes = (vendor.notes or "") + f"\n\nRating by {current_user.full_name} on {datetime.now().strftime('%Y-%m-%d')}: {notes}"
    
    vendor.updated_at = datetime.utcnow()
    vendor.last_interaction = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Vendor rating updated successfully",
        "overall_rating": vendor.overall_rating
    }

@router.get("/{vendor_id}/recommend", response_model=dict)
async def get_vendor_recommendation(
    vendor_id: int,
    project_requirements: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get AI-powered vendor recommendation for specific project"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Prepare vendor data for AI analysis
    vendor_data = {
        "name": vendor.name,
        "industry": vendor.industry,
        "annual_revenue": vendor.annual_revenue,
        "employee_count": vendor.employee_count,
        "country": vendor.country,
        "certifications": vendor.certifications or [],
        "overall_rating": vendor.overall_rating,
        "total_contracts": vendor.total_contracts,
        "compliance_status": vendor.compliance_status,
        "project_requirements": project_requirements
    }
    
    # Get AI recommendation
    recommendation = await ai_service.analyze_vendor(vendor_data)
    
    return {
        "success": True,
        "vendor_id": vendor_id,
        "recommendation": recommendation,
        "project_requirements": project_requirements
    }

@router.get("/search/similar", response_model=List[dict])
async def find_similar_vendors(
    industry: Optional[str] = None,
    country: Optional[str] = None,
    min_rating: Optional[float] = None,
    categories: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Find vendors similar to given criteria"""
    
    query = db.query(Vendor).filter(Vendor.status == "active")
    
    if industry:
        query = query.filter(Vendor.industry.ilike(f"%{industry}%"))
    
    if country:
        query = query.filter(Vendor.country.ilike(f"%{country}%"))
    
    if min_rating:
        query = query.filter(Vendor.overall_rating >= min_rating)
    
    # Order by AI recommendation score and overall rating
    vendors = query.order_by(
        Vendor.ai_recommendation_score.desc().nullslast(),
        Vendor.overall_rating.desc().nullslast()
    ).limit(20).all()
    
    return [
        {
            "id": vendor.id,
            "name": vendor.name,
            "industry": vendor.industry,
            "country": vendor.country,
            "overall_rating": vendor.overall_rating,
            "ai_recommendation_score": vendor.ai_recommendation_score,
            "total_contracts": vendor.total_contracts,
            "preferred_vendor": vendor.preferred_vendor
        }
        for vendor in vendors
    ]

@router.delete("/{vendor_id}", response_model=dict)
async def delete_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete vendor (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Check if vendor has active contracts
    active_contracts = len([c for c in vendor.contracts if c.status.value in ["active", "pending_signature"]])
    if active_contracts > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete vendor with {active_contracts} active contracts"
        )
    
    db.delete(vendor)
    db.commit()
    
    return {
        "success": True,
        "message": "Vendor deleted successfully"
    }