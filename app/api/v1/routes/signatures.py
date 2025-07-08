from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.contract import Contract
from app.models.signature import Signature, SignatureStatus
from app.services.signature_service import signature_service

router = APIRouter()

@router.post("/{contract_id}/initiate")
async def initiate_signature(
    contract_id: int,
    signers: List[Dict[str, str]],
    email_subject: str,
    email_message: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Initiate e-signature process for contract"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    if not contract.original_file_path:
        raise HTTPException(status_code=400, detail="Contract document not found")
    
    # Create signature envelope
    result = await signature_service.create_envelope(
        document_path=contract.original_file_path,
        signers=signers,
        email_subject=email_subject,
        email_message=email_message,
        contract_id=contract_id
    )
    
    if result["success"]:
        # Create signature record
        signature = Signature(
            envelope_id=result["envelope_id"],
            contract_id=contract_id,
            status=SignatureStatus.SENT,
            method="docusign",
            signers=signers,
            document_name=f"Contract_{contract_id}.pdf",
            initiated_by_id=current_user.id,
            email_subject=email_subject,
            email_message=email_message
        )
        
        db.add(signature)
        db.commit()
        
        return {
            "success": True,
            "signature_id": signature.id,
            "envelope_id": result["envelope_id"],
            "message": "E-signature process initiated successfully"
        }
    else:
        return {"success": False, "error": result["error"]}

@router.get("/{signature_id}/status")
async def get_signature_status(
    signature_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get signature status"""
    
    signature = db.query(Signature).filter(Signature.id == signature_id).first()
    if not signature:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    # Get updated status from DocuSign
    status_result = await signature_service.get_envelope_status(signature.envelope_id)
    
    if status_result["success"]:
        # Update signature status
        signature.provider_status = status_result["status"]
        db.commit()
        
        return {
            "success": True,
            "signature_id": signature_id,
            "status": signature.status.value,
            "provider_status": status_result["status"],
            "created_datetime": status_result.get("created_datetime"),
            "sent_datetime": status_result.get("sent_datetime"),
            "completed_datetime": status_result.get("completed_datetime")
        }
    else:
        return {"success": False, "error": status_result["error"]}

@router.post("/{signature_id}/download")
async def download_signed_document(
    signature_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Download signed document"""
    
    signature = db.query(Signature).filter(Signature.id == signature_id).first()
    if not signature:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    # Download from DocuSign
    download_result = await signature_service.download_signed_document(signature.envelope_id)
    
    if download_result["success"]:
        # Save signed document
        signed_path = f"uploads/contracts/{signature.contract_id}/signed_{signature.envelope_id}.pdf"
        with open(signed_path, 'wb') as f:
            f.write(download_result["document_content"])
        
        signature.signed_document_path = signed_path
        signature.status = SignatureStatus.COMPLETED
        db.commit()
        
        return {"success": True, "signed_document_path": signed_path}
    else:
        return {"success": False, "error": download_result["error"]}

@router.get("/contract/{contract_id}")
async def list_contract_signatures(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """List all signatures for a contract"""
    
    signatures = db.query(Signature).filter(Signature.contract_id == contract_id).all()
    
    return [
        {
            "id": sig.id,
            "envelope_id": sig.envelope_id,
            "status": sig.status.value,
            "method": sig.method.value,
            "created_at": sig.created_at,
            "sent_date": sig.sent_date,
            "completed_date": sig.completed_date
        }
        for sig in signatures
    ]