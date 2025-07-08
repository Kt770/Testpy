from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.auth import get_current_active_user, require_role
from app.models.models import Contract, ContractTemplate, User, Vendor, WorkflowStep
from app.models.schemas import (
    Contract as ContractSchema,
    ContractCreate,
    ContractUpdate,
    ContractTemplate as ContractTemplateSchema,
    ContractTemplateCreate,
    ContractGenerationRequest,
    WorkflowStep as WorkflowStepSchema,
    WorkflowStepCreate,
    APIResponse,
    PaginatedResponse
)
from app.services.genai.openai_service import OpenAIService
from app.services.esign.docusign_service import DocuSignService

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/", response_model=ContractSchema)
async def create_contract(
    contract_data: ContractCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new contract."""
    # Verify vendor exists
    vendor = db.query(Vendor).filter(Vendor.id == contract_data.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Create contract
    contract = Contract(
        **contract_data.dict(),
        created_by=current_user.id
    )
    
    db.add(contract)
    db.commit()
    db.refresh(contract)
    
    return contract


@router.get("/", response_model=PaginatedResponse)
async def list_contracts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    vendor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List contracts with filtering and pagination."""
    query = db.query(Contract)
    
    # Apply filters
    if status:
        query = query.filter(Contract.status == status)
    if vendor_id:
        query = query.filter(Contract.vendor_id == vendor_id)
    
    # Non-admin users can only see their own contracts
    if current_user.role != "admin":
        query = query.filter(Contract.created_by == current_user.id)
    
    total = query.count()
    contracts = query.offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=contracts,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.get("/{contract_id}", response_model=ContractSchema)
async def get_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get contract by ID."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    return contract


@router.put("/{contract_id}", response_model=ContractSchema)
async def update_contract(
    contract_id: int,
    contract_update: ContractUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Update fields
    for field, value in contract_update.dict(exclude_unset=True).items():
        setattr(contract, field, value)
    
    db.commit()
    db.refresh(contract)
    
    return contract


@router.delete("/{contract_id}")
async def delete_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin"))
):
    """Delete contract (admin only)."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    db.delete(contract)
    db.commit()
    
    return {"message": "Contract deleted successfully"}


@router.post("/generate", response_model=APIResponse)
async def generate_contract_with_ai(
    generation_request: ContractGenerationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Generate contract content using AI."""
    # Get vendor information
    vendor = db.query(Vendor).filter(Vendor.id == generation_request.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    # Get template if specified
    template_content = None
    if generation_request.template_id:
        template = db.query(ContractTemplate).filter(
            ContractTemplate.id == generation_request.template_id
        ).first()
        if template:
            template_content = template.template_content
    
    # Prepare vendor info and terms
    vendor_info = {
        "name": vendor.name,
        "address": vendor.address,
        "contact_person": vendor.contact_person,
        "email": vendor.email
    }
    
    terms = generation_request.custom_terms or {}
    terms.update({
        "contract_type": generation_request.contract_type
    })
    
    # Generate contract using AI
    openai_service = OpenAIService()
    result = await openai_service.generate_contract(
        generation_request.contract_type,
        vendor_info,
        terms,
        template_content
    )
    
    return APIResponse(
        success=True,
        message="Contract generated successfully",
        data=result
    )


@router.post("/{contract_id}/send-for-signature", response_model=APIResponse)
async def send_contract_for_signature(
    contract_id: int,
    signers: List[dict],  # [{"name": "...", "email": "..."}]
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Send contract for electronic signature using DocuSign."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Check if contract is ready for signature
    if contract.status not in ["approved", "draft"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Contract must be approved before sending for signature. Current status: {contract.status}"
        )
    
    # Generate document content (simplified - in real app, would generate PDF)
    document_content = f"""
    CONTRACT: {contract.title}
    
    VENDOR: {contract.vendor.name if contract.vendor else 'TBD'}
    VALUE: {contract.value} {contract.currency}
    
    TERMS AND CONDITIONS:
    {contract.terms_and_conditions or 'Standard terms apply.'}
    
    Start Date: {contract.start_date}
    End Date: {contract.end_date}
    """
    
    # Send for signature
    docusign_service = DocuSignService()
    result = await docusign_service.create_envelope(
        contract_id, 
        signers, 
        document_content, 
        db
    )
    
    return APIResponse(
        success=result["success"],
        message="Contract sent for signature" if result["success"] else "Failed to send contract",
        data=result
    )


@router.get("/{contract_id}/signature-status", response_model=APIResponse)
async def get_signature_status(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get signature status for a contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not contract.signature_envelope_id:
        return APIResponse(
            success=True,
            message="Contract not sent for signature yet",
            data={"status": "not_sent"}
        )
    
    # Get signature status
    docusign_service = DocuSignService()
    status_result = await docusign_service.get_envelope_status(contract.signature_envelope_id)
    recipients_result = await docusign_service.get_envelope_recipients(contract.signature_envelope_id)
    
    return APIResponse(
        success=True,
        message="Signature status retrieved",
        data={
            "envelope_status": status_result,
            "recipients": recipients_result,
            "contract_status": contract.status
        }
    )


@router.post("/{contract_id}/workflow-step", response_model=WorkflowStepSchema)
async def add_workflow_step(
    contract_id: int,
    step_data: WorkflowStepCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Add a workflow step to contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Create workflow step
    workflow_step = WorkflowStep(**step_data.dict())
    db.add(workflow_step)
    db.commit()
    db.refresh(workflow_step)
    
    return workflow_step


@router.get("/{contract_id}/workflow", response_model=List[WorkflowStepSchema])
async def get_contract_workflow(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get workflow steps for a contract."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    workflow_steps = db.query(WorkflowStep).filter(
        WorkflowStep.contract_id == contract_id
    ).order_by(WorkflowStep.step_order).all()
    
    return workflow_steps


@router.put("/workflow-step/{step_id}", response_model=WorkflowStepSchema)
async def update_workflow_step(
    step_id: int,
    step_update: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update workflow step status."""
    workflow_step = db.query(WorkflowStep).filter(WorkflowStep.id == step_id).first()
    if not workflow_step:
        raise HTTPException(status_code=404, detail="Workflow step not found")
    
    # Update fields
    for field, value in step_update.items():
        if hasattr(workflow_step, field):
            setattr(workflow_step, field, value)
    
    # Set completion time if marking as completed
    if step_update.get("status") == "completed":
        workflow_step.completed_at = datetime.now()
    
    db.commit()
    db.refresh(workflow_step)
    
    return workflow_step


# Contract Templates endpoints
@router.post("/templates/", response_model=ContractTemplateSchema)
async def create_contract_template(
    template_data: ContractTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("manager"))
):
    """Create a new contract template."""
    template = ContractTemplate(
        **template_data.dict(),
        created_by=current_user.id
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return template


@router.get("/templates/", response_model=List[ContractTemplateSchema])
async def list_contract_templates(
    contract_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List contract templates."""
    query = db.query(ContractTemplate).filter(ContractTemplate.is_active == True)
    
    if contract_type:
        query = query.filter(ContractTemplate.contract_type == contract_type)
    
    templates = query.all()
    return templates


@router.get("/templates/{template_id}", response_model=ContractTemplateSchema)
async def get_contract_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get contract template by ID."""
    template = db.query(ContractTemplate).filter(ContractTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    return template


@router.post("/{contract_id}/enhance-clauses", response_model=APIResponse)
async def enhance_contract_clauses(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Use AI to enhance contract clauses."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Check permissions
    if current_user.role != "admin" and contract.created_by != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    if not contract.terms_and_conditions:
        raise HTTPException(status_code=400, detail="Contract has no content to enhance")
    
    # Enhance clauses using AI
    openai_service = OpenAIService()
    enhancements = await openai_service.enhance_contract_clauses(
        contract.terms_and_conditions,
        contract.contract_type
    )
    
    return APIResponse(
        success=True,
        message="Contract clauses analyzed and enhanced",
        data=enhancements
    )