from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime
import uuid
import os
import aiofiles
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.contract import Contract, ContractStatus, ContractType
from app.models.vendor import Vendor
from app.core.config import settings

router = APIRouter()

@router.post("/", response_model=dict)
async def create_contract(
    title: str,
    contract_type: ContractType,
    party_a_name: str,
    party_b_name: str,
    description: Optional[str] = None,
    contract_value: Optional[float] = None,
    currency: str = "SAR",
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Create a new contract"""
    
    # Generate unique contract number
    contract_number = f"CNT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    contract = Contract(
        title=title,
        contract_number=contract_number,
        contract_type=contract_type,
        party_a_name=party_a_name,
        party_b_name=party_b_name,
        description=description,
        contract_value=contract_value,
        currency=currency,
        vendor_id=vendor_id,
        created_by_id=current_user.id,
        assigned_to_id=current_user.id
    )
    
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    return {
        "success": True,
        "contract_id": contract.id,
        "contract_number": contract.contract_number,
        "message": "Contract created successfully"
    }

@router.get("/", response_model=List[dict])
async def list_contracts(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=100),
    status: Optional[ContractStatus] = None,
    contract_type: Optional[ContractType] = None,
    search: Optional[str] = None,
    vendor_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List contracts with filtering and pagination"""
    
    query = db.query(Contract)
    
    # Apply filters
    if status:
        query = query.filter(Contract.status == status)
    
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    
    if vendor_id:
        query = query.filter(Contract.vendor_id == vendor_id)
    
    if search:
        query = query.filter(
            or_(
                Contract.title.ilike(f"%{search}%"),
                Contract.contract_number.ilike(f"%{search}%"),
                Contract.party_b_name.ilike(f"%{search}%"),
                Contract.description.ilike(f"%{search}%")
            )
        )
    
    # For non-admin users, show only contracts they created or are assigned to
    if current_user.role not in ["admin", "manager"]:
        query = query.filter(
            or_(
                Contract.created_by_id == current_user.id,
                Contract.assigned_to_id == current_user.id
            )
        )
    
    contracts = query.offset(skip).limit(limit).all()
    
    # Format response
    contract_list = []
    for contract in contracts:
        contract_data = {
            "id": contract.id,
            "title": contract.title,
            "contract_number": contract.contract_number,
            "contract_type": contract.contract_type.value,
            "status": contract.status.value,
            "party_a_name": contract.party_a_name,
            "party_b_name": contract.party_b_name,
            "contract_value": contract.contract_value,
            "currency": contract.currency,
            "start_date": contract.start_date,
            "end_date": contract.end_date,
            "created_at": contract.created_at,
            "created_by": contract.created_by.full_name if contract.created_by else None,
            "assigned_to": contract.assigned_to.full_name if contract.assigned_to else None,
            "vendor_name": contract.vendor.name if contract.vendor else None,
            "ai_risk_score": contract.ai_risk_score,
            "priority": contract.priority
        }
        contract_list.append(contract_data)
    
    return contract_list

@router.get("/{contract_id}", response_model=dict)
async def get_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get contract details"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        contract.created_by_id != current_user.id and 
        contract.assigned_to_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to view this contract")
    
    return {
        "id": contract.id,
        "title": contract.title,
        "contract_number": contract.contract_number,
        "contract_type": contract.contract_type.value,
        "status": contract.status.value,
        "party_a_name": contract.party_a_name,
        "party_b_name": contract.party_b_name,
        "party_a_email": contract.party_a_email,
        "party_b_email": contract.party_b_email,
        "description": contract.description,
        "contract_value": contract.contract_value,
        "currency": contract.currency,
        "payment_terms": contract.payment_terms,
        "start_date": contract.start_date,
        "end_date": contract.end_date,
        "signature_date": contract.signature_date,
        "terms_and_conditions": contract.terms_and_conditions,
        "special_clauses": contract.special_clauses,
        "ai_generated_content": contract.ai_generated_content,
        "ai_risk_score": contract.ai_risk_score,
        "ai_summary": contract.ai_summary,
        "created_at": contract.created_at,
        "updated_at": contract.updated_at,
        "created_by": contract.created_by.full_name if contract.created_by else None,
        "assigned_to": contract.assigned_to.full_name if contract.assigned_to else None,
        "vendor": {
            "id": contract.vendor.id,
            "name": contract.vendor.name,
            "email": contract.vendor.email
        } if contract.vendor else None,
        "priority": contract.priority,
        "tags": contract.tags
    }

@router.put("/{contract_id}", response_model=dict)
async def update_contract(
    contract_id: int,
    updates: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update contract details"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        contract.created_by_id != current_user.id and 
        contract.assigned_to_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this contract")
    
    # Update allowed fields
    allowed_fields = [
        'title', 'description', 'party_a_email', 'party_b_email',
        'contract_value', 'currency', 'payment_terms', 'start_date',
        'end_date', 'terms_and_conditions', 'special_clauses', 'priority',
        'tags', 'assigned_to_id'
    ]
    
    for field, value in updates.items():
        if field in allowed_fields and hasattr(contract, field):
            setattr(contract, field, value)
    
    contract.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Contract updated successfully"
    }

@router.put("/{contract_id}/status", response_model=dict)
async def update_contract_status(
    contract_id: int,
    new_status: ContractStatus,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update contract status"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if (current_user.role not in ["admin", "manager"] and 
        contract.created_by_id != current_user.id and 
        contract.assigned_to_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not authorized to update this contract")
    
    old_status = contract.status
    contract.status = new_status
    contract.updated_at = datetime.utcnow()
    
    # Update signature date if status is ACTIVE
    if new_status == ContractStatus.ACTIVE and not contract.signature_date:
        contract.signature_date = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Contract status updated from {old_status.value} to {new_status.value}",
        "old_status": old_status.value,
        "new_status": new_status.value
    }

@router.post("/{contract_id}/upload", response_model=dict)
async def upload_contract_document(
    contract_id: int,
    file: UploadFile = File(...),
    document_type: str = "original",  # original, signed, amendment
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Upload contract document"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file type
    allowed_extensions = ['pdf', 'docx', 'doc']
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Create upload directory
    upload_dir = os.path.join(settings.UPLOAD_DIR, "contracts", str(contract_id))
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file
    filename = f"{document_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    file_path = os.path.join(upload_dir, filename)
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Update contract with file path
    if document_type == "original":
        contract.original_file_path = file_path
    elif document_type == "signed":
        contract.signed_file_path = file_path
    
    contract.updated_at = datetime.utcnow()
    db.commit()
    
    return {
        "success": True,
        "message": "Document uploaded successfully",
        "filename": filename,
        "file_path": file_path
    }

@router.delete("/{contract_id}", response_model=dict)
async def delete_contract(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Delete contract (admin only)"""
    
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db.delete(contract)
    db.commit()
    
    return {
        "success": True,
        "message": "Contract deleted successfully"
    }

@router.get("/statistics/dashboard", response_model=dict)
async def get_contract_statistics(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get contract statistics for dashboard"""
    
    query = db.query(Contract)
    
    # For non-admin users, filter by their contracts
    if current_user.role not in ["admin", "manager"]:
        query = query.filter(
            or_(
                Contract.created_by_id == current_user.id,
                Contract.assigned_to_id == current_user.id
            )
        )
    
    # Get statistics
    total_contracts = query.count()
    draft_contracts = query.filter(Contract.status == ContractStatus.DRAFT).count()
    active_contracts = query.filter(Contract.status == ContractStatus.ACTIVE).count()
    pending_signature = query.filter(Contract.status == ContractStatus.PENDING_SIGNATURE).count()
    
    # Calculate total value
    total_value = query.filter(Contract.contract_value.isnot(None)).with_entities(
        db.func.sum(Contract.contract_value)
    ).scalar() or 0
    
    return {
        "total_contracts": total_contracts,
        "draft_contracts": draft_contracts,
        "active_contracts": active_contracts,
        "pending_signature": pending_signature,
        "total_value": total_value,
        "currency": "SAR"
    }