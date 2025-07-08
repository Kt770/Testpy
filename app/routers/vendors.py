from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_role
from app.models.models import Vendor, User
from app.models.schemas import (
    Vendor as VendorSchema,
    VendorCreate,
    VendorUpdate,
    VendorSelectionRequest,
    APIResponse,
    PaginatedResponse
)
from app.services.vendor.vendor_selector import VendorSelector

router = APIRouter(prefix="/vendors", tags=["vendors"])


@router.post("/", response_model=VendorSchema)
async def create_vendor(
    vendor_data: VendorCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new vendor."""
    # Check if vendor with same email already exists
    existing_vendor = db.query(Vendor).filter(Vendor.email == vendor_data.email).first()
    if existing_vendor:
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")
    
    # Create vendor
    vendor = Vendor(**vendor_data.dict())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    
    return vendor


@router.get("/", response_model=PaginatedResponse)
async def list_vendors(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List vendors with filtering and pagination."""
    query = db.query(Vendor)
    
    # Apply filters
    if status:
        query = query.filter(Vendor.status == status)
    if industry:
        query = query.filter(Vendor.industry.ilike(f"%{industry}%"))
    if search:
        query = query.filter(
            Vendor.name.ilike(f"%{search}%") |
            Vendor.email.ilike(f"%{search}%") |
            Vendor.contact_person.ilike(f"%{search}%")
        )
    
    total = query.count()
    vendors = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=vendors,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{vendor_id}", response_model=VendorSchema)
async def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get vendor by ID."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    return vendor


@router.put("/{vendor_id}", response_model=VendorSchema)
async def update_vendor(
    vendor_id: int,
    vendor_update: VendorUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update vendor information."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Check for email uniqueness if email is being updated
    if vendor_update.email and vendor_update.email != vendor.email:
        existing_vendor = db.query(Vendor).filter(Vendor.email == vendor_update.email).first()
        if existing_vendor:
            raise HTTPException(status_code=400, detail="Vendor with this email already exists")
    
    # Update fields
    for field, value in vendor_update.dict(exclude_unset=True).items():
        setattr(vendor, field, value)
    
    db.commit()
    db.refresh(vendor)
    
    return vendor


@router.delete("/{vendor_id}")
async def delete_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete vendor (admin only)."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Check if vendor has active contracts
    from app.models.models import Contract
    active_contracts = db.query(Contract).filter(
        Contract.vendor_id == vendor_id,
        Contract.status.in_(["draft", "pending_approval", "approved", "sent_for_signature", "signed"])
    ).count()
    
    if active_contracts > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete vendor with {active_contracts} active contracts"
        )
    
    # Soft delete by setting status to inactive
    vendor.status = "inactive"
    db.commit()
    
    return {"message": "Vendor deactivated successfully"}


@router.post("/select", response_model=APIResponse)
async def select_vendors(
    selection_request: VendorSelectionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Use AI to select and rank vendors based on project requirements."""
    vendor_selector = VendorSelector()
    result = await vendor_selector.select_vendors(selection_request, db)
    
    return APIResponse(
        success=result["success"],
        message="Vendor selection completed" if result["success"] else "Vendor selection failed",
        data=result
    )


@router.post("/{vendor_id}/update-scores", response_model=APIResponse)
async def update_vendor_scores(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Update vendor scores based on recent performance."""
    vendor_selector = VendorSelector()
    result = await vendor_selector.update_vendor_scores(vendor_id, db)
    
    return APIResponse(
        success=result["success"],
        message="Vendor scores updated" if result["success"] else "Failed to update vendor scores",
        data=result
    )


@router.post("/batch-update-scores", response_model=APIResponse)
async def batch_update_vendor_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Update scores for all active vendors (admin only)."""
    vendor_selector = VendorSelector()
    result = await vendor_selector.batch_update_all_vendor_scores(db)
    
    return APIResponse(
        success=result["success"],
        message="Batch vendor score update completed" if result["success"] else "Batch update failed",
        data=result
    )


@router.get("/{vendor_id}/performance", response_model=APIResponse)
async def get_vendor_performance(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed vendor performance metrics."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    from app.models.models import Contract, Proposal
    
    # Get contract statistics
    total_contracts = db.query(Contract).filter(Contract.vendor_id == vendor_id).count()
    completed_contracts = db.query(Contract).filter(
        Contract.vendor_id == vendor_id,
        Contract.status.in_(["signed", "executed"])
    ).count()
    
    # Get proposal statistics
    total_proposals = db.query(Proposal).filter(Proposal.vendor_id == vendor_id).count()
    accepted_proposals = db.query(Proposal).filter(
        Proposal.vendor_id == vendor_id,
        Proposal.status == "accepted"
    ).count()
    
    # Calculate average proposal score
    proposal_scores = db.query(Proposal.ai_score).filter(
        Proposal.vendor_id == vendor_id,
        Proposal.ai_score.isnot(None)
    ).all()
    
    avg_proposal_score = 0
    if proposal_scores:
        avg_proposal_score = sum(score[0] for score in proposal_scores) / len(proposal_scores)
    
    # Calculate total contract value
    contract_values = db.query(Contract.value).filter(
        Contract.vendor_id == vendor_id,
        Contract.value.isnot(None)
    ).all()
    
    total_contract_value = sum(value[0] for value in contract_values) if contract_values else 0
    
    performance_data = {
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "overall_score": vendor.overall_score,
        "reliability_score": vendor.reliability_score,
        "quality_score": vendor.quality_score,
        "price_competitiveness": vendor.price_competitiveness,
        "statistics": {
            "total_contracts": total_contracts,
            "completed_contracts": completed_contracts,
            "completion_rate": round((completed_contracts / total_contracts * 100), 2) if total_contracts > 0 else 0,
            "total_proposals": total_proposals,
            "accepted_proposals": accepted_proposals,
            "acceptance_rate": round((accepted_proposals / total_proposals * 100), 2) if total_proposals > 0 else 0,
            "average_proposal_score": round(avg_proposal_score, 2),
            "total_contract_value": total_contract_value
        }
    }
    
    return APIResponse(
        success=True,
        message="Vendor performance data retrieved",
        data=performance_data
    )


@router.get("/{vendor_id}/contracts", response_model=APIResponse)
async def get_vendor_contracts(
    vendor_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get contracts for a specific vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    from app.models.models import Contract
    
    query = db.query(Contract).filter(Contract.vendor_id == vendor_id)
    total = query.count()
    contracts = query.offset(skip).limit(limit).all()
    
    return APIResponse(
        success=True,
        message="Vendor contracts retrieved",
        data={
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "contracts": contracts,
            "total": total,
            "page": skip // limit + 1,
            "size": limit
        }
    )


@router.get("/{vendor_id}/proposals", response_model=APIResponse)
async def get_vendor_proposals(
    vendor_id: int,
    skip: int = 0,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get proposals for a specific vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    from app.models.models import Proposal
    
    query = db.query(Proposal).filter(Proposal.vendor_id == vendor_id)
    
    if status:
        query = query.filter(Proposal.status == status)
    
    total = query.count()
    proposals = query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit).all()
    
    return APIResponse(
        success=True,
        message="Vendor proposals retrieved",
        data={
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "proposals": proposals,
            "total": total,
            "page": skip // limit + 1,
            "size": limit
        }
    )


@router.get("/search/by-skills", response_model=APIResponse)
async def search_vendors_by_skills(
    skills: str,  # Comma-separated skills
    min_score: Optional[float] = 0.0,
    max_results: Optional[int] = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Search vendors by required skills."""
    skill_list = [skill.strip().lower() for skill in skills.split(",")]
    
    # Query vendors with matching specialties
    vendors = db.query(Vendor).filter(
        Vendor.status == "active",
        Vendor.overall_score >= min_score
    ).all()
    
    # Filter vendors with matching skills
    matching_vendors = []
    for vendor in vendors:
        if vendor.specialties:
            vendor_skills = [spec.lower() for spec in vendor.specialties]
            matches = sum(1 for skill in skill_list if any(skill in vs for vs in vendor_skills))
            if matches > 0:
                match_score = (matches / len(skill_list)) * 100
                matching_vendors.append({
                    **vendor.__dict__,
                    "skill_match_score": round(match_score, 2),
                    "matching_skills": matches
                })
    
    # Sort by match score and overall score
    matching_vendors.sort(key=lambda x: (x["skill_match_score"], x["overall_score"]), reverse=True)
    
    return APIResponse(
        success=True,
        message=f"Found {len(matching_vendors)} vendors matching skills",
        data={
            "search_skills": skill_list,
            "matching_vendors": matching_vendors[:max_results],
            "total_matches": len(matching_vendors)
        }
    )


@router.get("/analytics/dashboard", response_model=APIResponse)
async def get_vendor_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Get vendor analytics dashboard data."""
    # Get vendor statistics
    total_vendors = db.query(Vendor).count()
    active_vendors = db.query(Vendor).filter(Vendor.status == "active").count()
    
    # Get top performing vendors
    top_vendors = db.query(Vendor).filter(
        Vendor.status == "active"
    ).order_by(Vendor.overall_score.desc()).limit(5).all()
    
    # Get vendor distribution by industry
    from sqlalchemy import func
    industry_distribution = db.query(
        Vendor.industry,
        func.count(Vendor.id).label('count')
    ).filter(
        Vendor.status == "active",
        Vendor.industry.isnot(None)
    ).group_by(Vendor.industry).all()
    
    # Get average scores
    avg_scores = db.query(
        func.avg(Vendor.overall_score).label('avg_overall'),
        func.avg(Vendor.reliability_score).label('avg_reliability'),
        func.avg(Vendor.quality_score).label('avg_quality'),
        func.avg(Vendor.price_competitiveness).label('avg_price')
    ).filter(Vendor.status == "active").first()
    
    dashboard_data = {
        "summary": {
            "total_vendors": total_vendors,
            "active_vendors": active_vendors,
            "inactive_vendors": total_vendors - active_vendors
        },
        "top_vendors": [
            {
                "id": v.id,
                "name": v.name,
                "overall_score": v.overall_score,
                "industry": v.industry
            } for v in top_vendors
        ],
        "industry_distribution": [
            {"industry": industry, "count": count} 
            for industry, count in industry_distribution
        ],
        "average_scores": {
            "overall": round(avg_scores.avg_overall or 0, 2),
            "reliability": round(avg_scores.avg_reliability or 0, 2),
            "quality": round(avg_scores.avg_quality or 0, 2),
            "price_competitiveness": round(avg_scores.avg_price or 0, 2)
        }
    }
    
    return APIResponse(
        success=True,
        message="Vendor analytics dashboard data retrieved",
        data=dashboard_data
    )