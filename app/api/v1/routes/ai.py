from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.core.database import get_db
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.contract import Contract
from app.models.proposal import Proposal
from app.models.vendor import Vendor
from app.services.ai_service import ai_service
import aiofiles
import os
from app.core.config import settings

router = APIRouter()

@router.post("/generate-contract")
async def generate_contract(
    contract_type: str,
    parties: Dict[str, str],
    terms: Dict[str, Any],
    template_id: Optional[int] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Generate AI-powered contract content"""
    
    template_content = None
    if template_id:
        template = db.query(Contract).filter(
            Contract.id == template_id,
            Contract.is_template == True
        ).first()
        if template:
            template_content = template.terms_and_conditions
    
    result = await ai_service.generate_contract(
        contract_type=contract_type,
        parties=parties,
        terms=terms,
        template_content=template_content
    )
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "success": True,
        "content": result["content"],
        "ai_generated": result["ai_generated"],
        "model_used": result["model_used"],
        "confidence_score": result["confidence_score"]
    }

@router.post("/analyze-proposal/{proposal_id}")
async def analyze_proposal(
    proposal_id: int,
    requirements: Optional[List[str]] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Analyze proposal using AI"""
    
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    
    # Extract text from proposal file if available
    proposal_text = proposal.description or ""
    if proposal.original_file_path:
        file_ext = proposal.original_file_path.split('.')[-1].lower()
        extracted_text = await ai_service.extract_text_from_file(
            proposal.original_file_path, 
            file_ext
        )
        proposal_text += f"\n\n{extracted_text}"
    
    if not proposal_text.strip():
        raise HTTPException(
            status_code=400, 
            detail="No text content found in proposal"
        )
    
    analysis = await ai_service.analyze_proposal(proposal_text, requirements)
    
    if "error" in analysis:
        raise HTTPException(status_code=500, detail=analysis["error"])
    
    # Update proposal with AI analysis results
    proposal.ai_analysis_completed = True
    proposal.ai_overall_score = analysis.get("overall_score", 0)
    proposal.ai_technical_score = analysis.get("technical_score", 0)
    proposal.ai_financial_score = analysis.get("financial_score", 0)
    proposal.ai_risk_score = analysis.get("risk_score", 0)
    proposal.ai_compliance_score = analysis.get("compliance_score", 0)
    proposal.ai_key_points = analysis.get("key_points", [])
    proposal.ai_risks = analysis.get("risks", [])
    proposal.ai_advantages = analysis.get("advantages", [])
    proposal.ai_missing_items = analysis.get("missing_items", [])
    proposal.ai_summary = analysis.get("summary", "")
    proposal.ai_recommendation = analysis.get("recommendation", "")
    
    db.commit()
    
    return {
        "success": True,
        "proposal_id": proposal_id,
        "analysis": analysis
    }

@router.post("/analyze-vendor/{vendor_id}")
async def analyze_vendor(
    vendor_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """AI-powered vendor assessment"""
    
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    
    vendor_data = {
        "name": vendor.name,
        "industry": vendor.industry,
        "annual_revenue": vendor.annual_revenue,
        "employee_count": vendor.employee_count,
        "country": vendor.country,
        "certifications": vendor.certifications or [],
        "overall_rating": vendor.overall_rating
    }
    
    analysis = await ai_service.analyze_vendor(vendor_data)
    
    if "error" in analysis:
        raise HTTPException(status_code=500, detail=analysis["error"])
    
    # Update vendor with AI analysis
    vendor.ai_risk_assessment = analysis.get("risk_assessment", "")
    vendor.ai_capabilities_analysis = analysis.get("capabilities_analysis", "")
    vendor.ai_market_position = analysis.get("market_position", "")
    vendor.ai_recommendation_score = analysis.get("recommendation_score", 0.5)
    
    db.commit()
    
    return {
        "success": True,
        "vendor_id": vendor_id,
        "analysis": analysis
    }

@router.post("/extract-contract-terms/{contract_id}")
async def extract_contract_terms(
    contract_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Extract key terms from contract using AI"""
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")
    
    # Get contract text from file or database
    contract_text = contract.terms_and_conditions or ""
    if contract.original_file_path:
        file_ext = contract.original_file_path.split('.')[-1].lower()
        extracted_text = await ai_service.extract_text_from_file(
            contract.original_file_path,
            file_ext
        )
        contract_text += f"\n\n{extracted_text}"
    
    if not contract_text.strip():
        raise HTTPException(
            status_code=400,
            detail="No text content found in contract"
        )
    
    terms_analysis = await ai_service.extract_contract_terms(contract_text)
    
    if "error" in terms_analysis:
        raise HTTPException(status_code=500, detail=terms_analysis["error"])
    
    # Update contract with extracted terms
    contract.ai_risk_score = terms_analysis.get("risk_score", 0.5)
    contract.ai_summary = terms_analysis.get("summary", "")
    contract.ai_key_terms = str(terms_analysis)  # Store as JSON string
    
    db.commit()
    
    return {
        "success": True,
        "contract_id": contract_id,
        "extracted_terms": terms_analysis
    }

@router.post("/upload-document")
async def upload_document_for_analysis(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """Upload document for AI analysis"""
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")
    
    # Validate file type
    allowed_extensions = ['pdf', 'docx', 'doc', 'txt']
    file_ext = file.filename.split('.')[-1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed: {', '.join(allowed_extensions)}"
        )
    
    # Save uploaded file
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    
    file_path = os.path.join(upload_dir, f"{current_user.id}_{file.filename}")
    
    async with aiofiles.open(file_path, 'wb') as f:
        content = await file.read()
        await f.write(content)
    
    # Extract text from uploaded file
    extracted_text = await ai_service.extract_text_from_file(file_path, file_ext)
    
    return {
        "success": True,
        "filename": file.filename,
        "file_path": file_path,
        "extracted_text": extracted_text[:1000] + "..." if len(extracted_text) > 1000 else extracted_text,
        "text_length": len(extracted_text)
    }

@router.post("/quick-analysis")
async def quick_document_analysis(
    text_content: str,
    analysis_type: str = "contract",  # contract, proposal, general
    current_user: User = Depends(get_current_active_user)
):
    """Quick AI analysis of text content"""
    
    if not text_content.strip():
        raise HTTPException(status_code=400, detail="No text content provided")
    
    if analysis_type == "contract":
        result = await ai_service.extract_contract_terms(text_content)
    elif analysis_type == "proposal":
        result = await ai_service.analyze_proposal(text_content)
    else:
        # General analysis
        result = {"summary": "General text analysis not implemented yet"}
    
    return {
        "success": True,
        "analysis_type": analysis_type,
        "result": result
    }