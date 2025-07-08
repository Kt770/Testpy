from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
from datetime import datetime
import uuid
import os
import aiofiles
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.proposal import Proposal, ProposalStatus, ProposalType
from app.models.vendor import Vendor
from app.services.ai_service import ai_service
from app.core.config import settings

router = APIRouter()

@router.post("/", response_model=dict)
async def create_proposal(
    title: str,
    vendor_id: int,
    proposal_type: ProposalType,
    proposed_amount: float,
    currency: str = "SAR",
    description: Optional[str] = None,
    scope_of_work: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new proposal"""
    
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Generate unique proposal number
    proposal_number = f"PRP-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    proposal = Proposal(
        title=title,
        proposal_number=proposal_number,
        proposal_type=proposal_type,
        vendor_id=vendor_id,
        proposed_amount=proposed_amount,
        currency=currency,
        description=description,
        scope_of_work=scope_of_work,
        received_by_id=current_user.id,
        assigned_to_id=current_user.id
    )
    
    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    
    return {
        "success": True,
        "proposal_id": proposal.id,
        "proposal_number": proposal.proposal_number,
        "message": "Proposal created successfully"
    }

@router.get("/", response_model=List[dict])
async def list_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[ProposalStatus] = None,
    proposal_type: Optional[ProposalType] = None,
    vendor_id: Optional[int] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List proposals with filtering"""
    
    query = db.query(Proposal)
    
    # Apply filters
    if status:
        query = query.filter(Proposal.status == status)
    
    if proposal_type:
        query = query.filter(Proposal.proposal_type == proposal_type)
    
    if vendor_id:
        query = query.filter(Proposal.vendor_id == vendor_id)
    
    if search:
        query = query.filter(
            or_(
                Proposal.title.ilike(f"%{search}%"),
                Proposal.proposal_number.ilike(f"%{search}%"),
                Proposal.description.ilike(f"%{search}%")
            )
        )
    
    # For non-admin users, show only proposals they're involved with
    if current_user.role not in ["admin", "manager"]:
        query = query.filter(
            or_(
                Proposal.received_by_id == current_user.id,
                Proposal.assigned_to_id == current_user.id,
                Proposal.evaluated_by_id == current_user.id
            )
        )
    
    proposals = query.order_by(Proposal.received_date.desc()).offset(skip).limit(limit).all()
    
    # Format response
    proposal_list = []
    for proposal in proposals:
        proposal_data = {
            "id": proposal.id,
            "title": proposal.title,
            "proposal_number": proposal.proposal_number,
            "proposal_type": proposal.proposal_type.value,
            "status": proposal.status.value,
            "vendor_name": proposal.vendor.name if proposal.vendor else None,
            "vendor_id": proposal.vendor_id,
            "proposed_amount": proposal.proposed_amount,
            "currency": proposal.currency,
            "received_date": proposal.received_date,
            "due_date": proposal.due_date,
            "ai_overall_score": proposal.ai_overall_score,
            "ai_analysis_completed": proposal.ai_analysis_completed,
            "priority": proposal.priority,
            "assigned_to": proposal.assigned_to.full_name if proposal.assigned_to else None,
            "created_at": proposal.created_at
        }
        proposal_list.append(proposal_data)
    
    return proposal_list

@router.get("/{proposal_id}", response_model=dict)
async def get_proposal(
    proposal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get proposal details"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        proposal.received_by_id != current_user.id and 
        proposal.assigned_to_id != current_user.id and
        proposal.evaluated_by_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this proposal")
    
    return {
        "id": proposal.id,
        "title": proposal.title,
        "proposal_number": proposal.proposal_number,
        "proposal_type": proposal.proposal_type.value,
        "status": proposal.status.value,
        "description": proposal.description,
        "scope_of_work": proposal.scope_of_work,
        "deliverables": proposal.deliverables,
        "proposed_amount": proposal.proposed_amount,
        "currency": proposal.currency,
        "payment_schedule": proposal.payment_schedule,
        "cost_breakdown": proposal.cost_breakdown,
        "proposed_start_date": proposal.proposed_start_date,
        "proposed_end_date": proposal.proposed_end_date,
        "duration_months": proposal.duration_months,
        "key_milestones": proposal.key_milestones,
        "vendor": {
            "id": proposal.vendor.id,
            "name": proposal.vendor.name,
            "email": proposal.vendor.email,
            "overall_rating": proposal.vendor.overall_rating
        } if proposal.vendor else None,
        "ai_analysis_completed": proposal.ai_analysis_completed,
        "ai_overall_score": proposal.ai_overall_score,
        "ai_technical_score": proposal.ai_technical_score,
        "ai_financial_score": proposal.ai_financial_score,
        "ai_risk_score": proposal.ai_risk_score,
        "ai_compliance_score": proposal.ai_compliance_score,
        "ai_key_points": proposal.ai_key_points,
        "ai_risks": proposal.ai_risks,
        "ai_advantages": proposal.ai_advantages,
        "ai_missing_items": proposal.ai_missing_items,
        "ai_summary": proposal.ai_summary,
        "ai_recommendation": proposal.ai_recommendation,
        "technical_evaluation": proposal.technical_evaluation,
        "financial_evaluation": proposal.financial_evaluation,
        "risk_assessment": proposal.risk_assessment,
        "compliance_check": proposal.compliance_check,
        "evaluator_notes": proposal.evaluator_notes,
        "decision_rationale": proposal.decision_rationale,
        "rejection_reason": proposal.rejection_reason,
        "received_date": proposal.received_date,
        "due_date": proposal.due_date,
        "evaluation_completed_date": proposal.evaluation_completed_date,
        "decision_date": proposal.decision_date,
        "priority": proposal.priority,
        "confidentiality_level": proposal.confidentiality_level,
        "tags": proposal.tags,
        "received_by": proposal.received_by.full_name if proposal.received_by else None,
        "assigned_to": proposal.assigned_to.full_name if proposal.assigned_to else None,
        "evaluated_by": proposal.evaluated_by.full_name if proposal.evaluated_by else None,
        "approved_by": proposal.approved_by.full_name if proposal.approved_by else None,
        "created_at": proposal.created_at,
        "updated_at": proposal.updated_at
    }

@router.put("/{proposal_id}", response_model=dict)
async def update_proposal(
    proposal_id: int,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update proposal information"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        proposal.received_by_id != current_user.id and 
        proposal.assigned_to_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this proposal")
    
    # Update allowed fields
    allowed_fields = [
        'title', 'description', 'scope_of_work', 'deliverables',
        'proposed_amount', 'currency', 'payment_schedule', 'cost_breakdown',
        'proposed_start_date', 'proposed_end_date', 'duration_months',
        'key_milestones', 'due_date', 'priority', 'confidentiality_level',
        'tags', 'assigned_to_id', 'technical_evaluation', 'financial_evaluation',
        'risk_assessment', 'compliance_check', 'evaluator_notes'
    ]
    
    for field, value in updates.items():
        if field in allowed_fields and hasattr(proposal, field):
            setattr(proposal, field, value)
    
    proposal.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Proposal updated successfully"
    }

@router.put("/{proposal_id}/status", response_model=dict)
async def update_proposal_status(
    proposal_id: int,
    new_status: ProposalStatus,
    decision_rationale: Optional[str] = None,
    rejection_reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update proposal status"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        proposal.assigned_to_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update proposal status")
    
    old_status = proposal.status
    proposal.status = new_status
    proposal.updated_at = datetime.utcnow()
    
    if decision_rationale:
        proposal.decision_rationale = decision_rationale
    
    if rejection_reason:
        proposal.rejection_reason = rejection_reason
    
    # Update dates based on status
    if new_status == ProposalStatus.UNDER_REVIEW:
        proposal.evaluation_completed_date = None
        proposal.decision_date = None
    elif new_status in [ProposalStatus.ACCEPTED, ProposalStatus.REJECTED]:
        proposal.decision_date = datetime.utcnow()
        proposal.approved_by_id = current_user.id
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Proposal status updated from {old_status.value} to {new_status.value}",
        "old_status": old_status.value,
        "new_status": new_status.value
    }

@router.post("/{proposal_id}/upload", response_model=dict)
async def upload_proposal_document(
    proposal_id: int,
    file: UploadFile = File(...),
    document_type: str = "original",  # original, supporting, amendment
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload proposal document"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file type
    allowed_extensions = ['pdf', 'docx', 'doc', 'xlsx', 'xls']
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create upload directory
    upload_dir = os.path.join(settings.UPLOAD_DIR, "proposals", str(proposal_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Update proposal with file path
    if document_type == "original":
        proposal.original_file_path = file_path
    else:
        # Add to supporting documents list
        supporting_docs = proposal.supporting_documents or []
        supporting_docs.append(file_path)
        proposal.supporting_documents = supporting_docs
    
    proposal.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Document uploaded successfully",
        "filename": filename,
        "file_path": file_path
    }

@router.post("/{proposal_id}/evaluate", response_model=dict)
async def evaluate_proposal(
    proposal_id: int,
    technical_score: Optional[float] = None,
    financial_score: Optional[float] = None,
    risk_score: Optional[float] = None,
    compliance_score: Optional[float] = None,
    evaluator_notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Manually evaluate proposal"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Update evaluation scores
    if technical_score is not None:
        proposal.ai_technical_score = technical_score
    if financial_score is not None:
        proposal.ai_financial_score = financial_score
    if risk_score is not None:
        proposal.ai_risk_score = risk_score
    if compliance_score is not None:
        proposal.ai_compliance_score = compliance_score
    
    # Calculate overall score
    scores = [s for s in [technical_score, financial_score, risk_score, compliance_score] if s is not None]
    if scores:
        proposal.ai_overall_score = sum(scores) / len(scores)
    
    if evaluator_notes:
        proposal.evaluator_notes = evaluator_notes
    
    proposal.evaluated_by_id = current_user.id
    proposal.evaluation_completed_date = datetime.utcnow()
    proposal.updated_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Proposal evaluation completed",
        "overall_score": proposal.ai_overall_score
    }

@router.get("/analytics/dashboard", response_model=dict)
async def get_proposal_analytics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get proposal analytics for dashboard"""
    
    query = db.query(Proposal)
    
    # For non-admin users, filter by their proposals
    if current_user.role not in ["admin", "manager"]:
        query = query.filter(
            or_(
                Proposal.received_by_id == current_user.id,
                Proposal.assigned_to_id == current_user.id,
                Proposal.evaluated_by_id == current_user.id
            )
        )
    
    # Get statistics
    total_proposals = query.count()
    received_proposals = query.filter(Proposal.status == ProposalStatus.RECEIVED).count()
    under_review = query.filter(Proposal.status == ProposalStatus.UNDER_REVIEW).count()
    ai_analyzing = query.filter(Proposal.status == ProposalStatus.AI_ANALYZING).count()
    shortlisted = query.filter(Proposal.status == ProposalStatus.SHORTLISTED).count()
    accepted = query.filter(Proposal.status == ProposalStatus.ACCEPTED).count()
    rejected = query.filter(Proposal.status == ProposalStatus.REJECTED).count()
    
    # Calculate total proposed value
    total_value = query.filter(Proposal.proposed_amount.isnot(None)).with_entities(
        db.func.sum(Proposal.proposed_amount)
    ).scalar() or 0
    
    # Average AI scores
    avg_ai_score = query.filter(Proposal.ai_overall_score.isnot(None)).with_entities(
        db.func.avg(Proposal.ai_overall_score)
    ).scalar() or 0
    
    return {
        "total_proposals": total_proposals,
        "received_proposals": received_proposals,
        "under_review": under_review,
        "ai_analyzing": ai_analyzing,
        "shortlisted": shortlisted,
        "accepted": accepted,
        "rejected": rejected,
        "total_proposed_value": total_value,
        "average_ai_score": round(avg_ai_score, 2) if avg_ai_score else 0,
        "currency": "SAR"
    }

@router.delete("/{proposal_id}", response_model=dict)
async def delete_proposal(
    proposal_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete proposal (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    db.delete(proposal)
    db.commit()
    
    return {
        "success": True,
        "message": "Proposal deleted successfully"
    }