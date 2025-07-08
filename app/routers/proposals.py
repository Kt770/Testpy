from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import shutil
import os
from pathlib import Path

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_role
from app.models.models import Proposal, User, Vendor
from app.models.schemas import (
    Proposal as ProposalSchema,
    ProposalCreate,
    ProposalUpdate,
    ProposalAnalysisRequest,
    APIResponse,
    PaginatedResponse
)
from app.services.analysis.proposal_analyzer import ProposalAnalyzer

router = APIRouter(prefix="/proposals", tags=["proposals"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path("uploads/proposals")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=ProposalSchema)
async def create_proposal(
    proposal_data: ProposalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new proposal."""
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == proposal_data.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Create proposal
    proposal = Proposal(**proposal_data.dict())
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    
    return proposal


@router.post("/upload", response_model=APIResponse)
async def upload_proposal_document(
    file: UploadFile = File(...),
    vendor_id: int = Form(...),
    title: str = Form(...),
    description: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Upload a proposal document and create proposal record."""
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Validate file type
    allowed_types = {".pdf", ".docx", ".doc", ".txt"}
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"File type {file_extension} not supported. Allowed types: {', '.join(allowed_types)}"
        )
    
    # Save file
    file_path = UPLOAD_DIR / f"{vendor_id}_{file.filename}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Create proposal record
    proposal = Proposal(
        title=title,
        description=description,
        vendor_id=vendor_id,
        file_path=str(file_path),
        file_name=file.filename,
        file_type=file_extension[1:]  # Remove the dot
    )
    
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    
    # Automatically trigger analysis
    try:
        analyzer = ProposalAnalyzer()
        analysis_result = await analyzer.analyze_proposal_document(
            str(file_path), proposal.id, db
        )
        
        return APIResponse(
            success=True,
            message="Proposal uploaded and analyzed successfully",
            data={
                "proposal": proposal,
                "analysis_result": analysis_result,
                "file_path": str(file_path)
            }
        )
    except Exception as e:
        # If analysis fails, still return success for upload
        return APIResponse(
            success=True,
            message=f"Proposal uploaded successfully, but analysis failed: {str(e)}",
            data={
                "proposal": proposal,
                "file_path": str(file_path),
                "analysis_error": str(e)
            }
        )


@router.get("/", response_model=PaginatedResponse)
async def list_proposals(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    min_score: Optional[float] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List proposals with filtering and pagination."""
    query = db.query(Proposal)
    
    # Apply filters
    if status:
        query = query.filter(Proposal.status == status)
    if vendor_id:
        query = query.filter(Proposal.vendor_id == vendor_id)
    if min_score is not None:
        query = query.filter(Proposal.ai_score >= min_score)
    
    total = query.count()
    proposals = query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=proposals,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{proposal_id}", response_model=ProposalSchema)
async def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get proposal by ID."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    return proposal


@router.put("/{proposal_id}", response_model=ProposalSchema)
async def update_proposal(
    proposal_id: int,
    proposal_update: ProposalUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update proposal."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Update fields
    for field, value in proposal_update.dict(exclude_unset=True).items():
        setattr(proposal, field, value)
    
    # Update reviewed_by if status is being changed
    if proposal_update.status and proposal_update.status != proposal.status:
        proposal.reviewed_by = current_user.id
    
    db.commit()
    db.refresh(proposal)
    
    return proposal


@router.delete("/{proposal_id}")
async def delete_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete proposal (admin only)."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Delete associated file if it exists
    if proposal.file_path and os.path.exists(proposal.file_path):
        os.remove(proposal.file_path)
    
    db.delete(proposal)
    db.commit()
    
    return {"message": "Proposal deleted successfully"}


@router.post("/{proposal_id}/analyze", response_model=APIResponse)
async def analyze_proposal(
    proposal_id: int,
    analysis_request: Optional[ProposalAnalysisRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Analyze proposal using AI."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if not proposal.file_path:
        raise HTTPException(status_code=400, detail="No document file found for this proposal")
    
    if not os.path.exists(proposal.file_path):
        raise HTTPException(status_code=400, detail="Proposal document file not found on server")
    
    # Perform analysis
    analyzer = ProposalAnalyzer()
    result = await analyzer.analyze_proposal_document(
        proposal.file_path, proposal_id, db
    )
    
    return APIResponse(
        success=result["success"],
        message="Proposal analysis completed" if result["success"] else "Proposal analysis failed",
        data=result
    )


@router.post("/batch-analyze", response_model=APIResponse)
async def batch_analyze_proposals(
    proposal_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Analyze multiple proposals in batch."""
    # Verify all proposals exist
    proposals = db.query(Proposal).filter(Proposal.id.in_(proposal_ids)).all()
    if len(proposals) != len(proposal_ids):
        found_ids = [p.id for p in proposals]
        missing_ids = [pid for pid in proposal_ids if pid not in found_ids]
        raise HTTPException(
            status_code=404, 
            detail=f"Proposals not found: {missing_ids}"
        )
    
    # Perform batch analysis
    analyzer = ProposalAnalyzer()
    result = await analyzer.batch_analyze_proposals(proposal_ids, db)
    
    return APIResponse(
        success=True,
        message=f"Batch analysis completed: {result['successful']} successful, {result['failed']} failed",
        data=result
    )


@router.post("/compare", response_model=APIResponse)
async def compare_proposals(
    proposal_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Compare multiple proposals using AI analysis."""
    if len(proposal_ids) < 2:
        raise HTTPException(status_code=400, detail="At least 2 proposals required for comparison")
    
    # Verify all proposals exist
    proposals = db.query(Proposal).filter(Proposal.id.in_(proposal_ids)).all()
    if len(proposals) != len(proposal_ids):
        found_ids = [p.id for p in proposals]
        missing_ids = [pid for pid in proposal_ids if pid not in found_ids]
        raise HTTPException(
            status_code=404, 
            detail=f"Proposals not found: {missing_ids}"
        )
    
    # Perform comparison
    analyzer = ProposalAnalyzer()
    result = await analyzer.compare_proposals(proposal_ids, db)
    
    return APIResponse(
        success=result.get("success", False),
        message="Proposal comparison completed" if result.get("success") else "Proposal comparison failed",
        data=result
    )


@router.get("/{proposal_id}/download")
async def download_proposal_document(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Download the original proposal document."""
    from fastapi.responses import FileResponse
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if not proposal.file_path or not os.path.exists(proposal.file_path):
        raise HTTPException(status_code=404, detail="Proposal document file not found")
    
    return FileResponse(
        path=proposal.file_path,
        filename=proposal.file_name,
        media_type='application/octet-stream'
    )


@router.get("/{proposal_id}/analysis-report", response_model=APIResponse)
async def get_proposal_analysis_report(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get detailed analysis report for a proposal."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Get vendor information
    vendor = db.query(Vendor).filter(Vendor.id == proposal.vendor_id).first()
    
    analysis_report = {
        "proposal_info": {
            "id": proposal.id,
            "title": proposal.title,
            "vendor_name": vendor.name if vendor else "Unknown",
            "vendor_id": proposal.vendor_id,
            "proposed_value": proposal.proposed_value,
            "currency": proposal.currency,
            "status": proposal.status,
            "created_at": proposal.created_at
        },
        "ai_analysis": {
            "summary": proposal.ai_summary,
            "score": proposal.ai_score,
            "risk_assessment": proposal.ai_risk_assessment,
            "compliance_check": proposal.ai_compliance_check,
            "key_benefits": proposal.key_benefits or [],
            "concerns": proposal.concerns or []
        },
        "technical_specifications": proposal.technical_specifications or {},
        "deliverables": proposal.deliverables or [],
        "timeline": {
            "proposed_start_date": proposal.proposed_start_date,
            "proposed_end_date": proposal.proposed_end_date,
            "delivery_timeline": proposal.delivery_timeline
        }
    }
    
    return APIResponse(
        success=True,
        message="Analysis report retrieved successfully",
        data=analysis_report
    )


@router.post("/{proposal_id}/accept", response_model=APIResponse)
async def accept_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Accept a proposal and optionally create a contract."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if proposal.status != "analyzed":
        raise HTTPException(
            status_code=400, 
            detail=f"Proposal must be analyzed before acceptance. Current status: {proposal.status}"
        )
    
    # Update proposal status
    proposal.status = "accepted"
    proposal.reviewed_by = current_user.id
    
    # Create a contract from the proposal
    from app.models.models import Contract
    contract = Contract(
        title=f"Contract for {proposal.title}",
        description=proposal.description,
        contract_type="service",  # Default type, can be customized
        value=proposal.proposed_value,
        currency=proposal.currency,
        start_date=proposal.proposed_start_date,
        end_date=proposal.proposed_end_date,
        vendor_id=proposal.vendor_id,
        created_by=current_user.id,
        status="draft"
    )
    
    db.add(contract)
    db.commit()
    db.refresh(contract)
    db.refresh(proposal)
    
    return APIResponse(
        success=True,
        message="Proposal accepted and contract created",
        data={
            "proposal": proposal,
            "contract": contract
        }
    )


@router.post("/{proposal_id}/reject", response_model=APIResponse)
async def reject_proposal(
    proposal_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Reject a proposal."""
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Update proposal status
    proposal.status = "rejected"
    proposal.reviewed_by = current_user.id
    
    # Add rejection reason to notes if provided
    if reason:
        current_notes = proposal.description or ""
        proposal.description = f"{current_notes}\n\nRejection Reason: {reason}"
    
    db.commit()
    db.refresh(proposal)
    
    return APIResponse(
        success=True,
        message="Proposal rejected",
        data={"proposal": proposal, "rejection_reason": reason}
    )


@router.get("/search/high-scoring", response_model=APIResponse)
async def get_high_scoring_proposals(
    min_score: float = 80.0,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get high-scoring proposals above a certain threshold."""
    proposals = db.query(Proposal).filter(
        Proposal.ai_score >= min_score,
        Proposal.ai_score.isnot(None)
    ).order_by(Proposal.ai_score.desc()).limit(limit).all()
    
    # Get vendor information for each proposal
    proposal_data = []
    for proposal in proposals:
        vendor = db.query(Vendor).filter(Vendor.id == proposal.vendor_id).first()
        proposal_dict = {
            "id": proposal.id,
            "title": proposal.title,
            "vendor_name": vendor.name if vendor else "Unknown",
            "ai_score": proposal.ai_score,
            "proposed_value": proposal.proposed_value,
            "status": proposal.status,
            "created_at": proposal.created_at
        }
        proposal_data.append(proposal_dict)
    
    return APIResponse(
        success=True,
        message=f"Found {len(proposals)} high-scoring proposals",
        data={
            "min_score_threshold": min_score,
            "proposals": proposal_data,
            "total_found": len(proposals)
        }
    )


@router.get("/analytics/dashboard", response_model=APIResponse)
async def get_proposals_analytics_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Get proposals analytics dashboard data."""
    from sqlalchemy import func
    
    # Get proposal statistics
    total_proposals = db.query(Proposal).count()
    analyzed_proposals = db.query(Proposal).filter(Proposal.ai_score.isnot(None)).count()
    accepted_proposals = db.query(Proposal).filter(Proposal.status == "accepted").count()
    rejected_proposals = db.query(Proposal).filter(Proposal.status == "rejected").count()
    
    # Get average scores
    avg_score = db.query(func.avg(Proposal.ai_score)).filter(
        Proposal.ai_score.isnot(None)
    ).scalar() or 0
    
    # Get status distribution
    status_distribution = db.query(
        Proposal.status,
        func.count(Proposal.id).label('count')
    ).group_by(Proposal.status).all()
    
    # Get top scoring proposals
    top_proposals = db.query(Proposal).filter(
        Proposal.ai_score.isnot(None)
    ).order_by(Proposal.ai_score.desc()).limit(5).all()
    
    # Get vendor performance
    vendor_stats = db.query(
        Vendor.name,
        func.count(Proposal.id).label('proposal_count'),
        func.avg(Proposal.ai_score).label('avg_score')
    ).join(Proposal).filter(
        Proposal.ai_score.isnot(None)
    ).group_by(Vendor.id, Vendor.name).order_by(
        func.avg(Proposal.ai_score).desc()
    ).limit(5).all()
    
    dashboard_data = {
        "summary": {
            "total_proposals": total_proposals,
            "analyzed_proposals": analyzed_proposals,
            "accepted_proposals": accepted_proposals,
            "rejected_proposals": rejected_proposals,
            "pending_review": total_proposals - accepted_proposals - rejected_proposals,
            "average_score": round(avg_score, 2)
        },
        "status_distribution": [
            {"status": status, "count": count} 
            for status, count in status_distribution
        ],
        "top_proposals": [
            {
                "id": p.id,
                "title": p.title,
                "ai_score": p.ai_score,
                "proposed_value": p.proposed_value
            } for p in top_proposals
        ],
        "vendor_performance": [
            {
                "vendor_name": name,
                "proposal_count": count,
                "average_score": round(avg_score, 2)
            } for name, count, avg_score in vendor_stats
        ]
    }
    
    return APIResponse(
        success=True,
        message="Proposals analytics dashboard data retrieved",
        data=dashboard_data
    )