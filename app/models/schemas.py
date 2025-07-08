from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"


class ContractStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    SENT_FOR_SIGNATURE = "sent_for_signature"
    SIGNED = "signed"
    EXECUTED = "executed"
    TERMINATED = "terminated"


class ProposalStatus(str, Enum):
    RECEIVED = "received"
    UNDER_REVIEW = "under_review"
    ANALYZED = "analyzed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class VendorStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: str
    role: UserRole = UserRole.USER
    is_active: bool = True


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    username: Optional[str] = None
    full_name: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class User(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Vendor schemas
class VendorBase(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    years_in_business: Optional[int] = None
    certifications: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    contact_person: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    years_in_business: Optional[int] = None
    certifications: Optional[List[str]] = None
    specialties: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[VendorStatus] = None


class Vendor(VendorBase):
    id: int
    reliability_score: float = 0.0
    quality_score: float = 0.0
    price_competitiveness: float = 0.0
    overall_score: float = 0.0
    status: VendorStatus = VendorStatus.ACTIVE
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Contract schemas
class ContractBase(BaseModel):
    title: str
    description: Optional[str] = None
    contract_type: str
    value: Optional[float] = None
    currency: str = "USD"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    signature_deadline: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None


class ContractCreate(ContractBase):
    vendor_id: int


class ContractUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    contract_type: Optional[str] = None
    value: Optional[float] = None
    currency: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    signature_deadline: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    status: Optional[ContractStatus] = None
    vendor_id: Optional[int] = None


class Contract(ContractBase):
    id: int
    status: ContractStatus = ContractStatus.DRAFT
    ai_generated_clauses: Optional[Dict[str, Any]] = None
    document_url: Optional[str] = None
    signature_envelope_id: Optional[str] = None
    vendor_id: Optional[int] = None
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Proposal schemas
class ProposalBase(BaseModel):
    title: str
    description: Optional[str] = None
    proposed_value: Optional[float] = None
    currency: str = "USD"
    proposed_start_date: Optional[datetime] = None
    proposed_end_date: Optional[datetime] = None
    delivery_timeline: Optional[str] = None
    proposal_content: Optional[str] = None
    technical_specifications: Optional[Dict[str, Any]] = None
    deliverables: Optional[List[str]] = None


class ProposalCreate(ProposalBase):
    vendor_id: int
    file_name: Optional[str] = None
    file_type: Optional[str] = None


class ProposalUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    proposed_value: Optional[float] = None
    currency: Optional[str] = None
    proposed_start_date: Optional[datetime] = None
    proposed_end_date: Optional[datetime] = None
    delivery_timeline: Optional[str] = None
    proposal_content: Optional[str] = None
    technical_specifications: Optional[Dict[str, Any]] = None
    deliverables: Optional[List[str]] = None
    status: Optional[ProposalStatus] = None


class Proposal(ProposalBase):
    id: int
    ai_summary: Optional[str] = None
    ai_risk_assessment: Optional[Dict[str, Any]] = None
    ai_compliance_check: Optional[Dict[str, Any]] = None
    ai_score: float = 0.0
    key_benefits: Optional[List[str]] = None
    concerns: Optional[List[str]] = None
    status: ProposalStatus = ProposalStatus.RECEIVED
    file_path: Optional[str] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    vendor_id: int
    reviewed_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Workflow schemas
class WorkflowStepBase(BaseModel):
    step_name: str
    step_order: int
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    notes: Optional[str] = None


class WorkflowStepCreate(WorkflowStepBase):
    contract_id: int


class WorkflowStepUpdate(BaseModel):
    step_name: Optional[str] = None
    step_order: Optional[int] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    notes: Optional[str] = None


class WorkflowStep(WorkflowStepBase):
    id: int
    status: str = "pending"
    completed_at: Optional[datetime] = None
    contract_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Contract Template schemas
class ContractTemplateBase(BaseModel):
    name: str
    description: Optional[str] = None
    contract_type: str
    template_content: str
    variables: Optional[Dict[str, Any]] = None
    is_active: bool = True


class ContractTemplateCreate(ContractTemplateBase):
    pass


class ContractTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    contract_type: Optional[str] = None
    template_content: Optional[str] = None
    variables: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class ContractTemplate(ContractTemplateBase):
    id: int
    created_by: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# AI Analysis schemas
class ProposalAnalysisRequest(BaseModel):
    proposal_id: int
    analysis_type: str = "comprehensive"  # comprehensive, risk, compliance, scoring


class ProposalAnalysisResult(BaseModel):
    proposal_id: int
    summary: str
    risk_assessment: Dict[str, Any]
    compliance_check: Dict[str, Any]
    score: float
    key_benefits: List[str]
    concerns: List[str]
    recommendations: List[str]


class VendorSelectionRequest(BaseModel):
    project_description: str
    budget_range: Optional[Dict[str, float]] = None
    required_skills: Optional[List[str]] = None
    project_timeline: Optional[str] = None
    preferred_location: Optional[str] = None


class VendorSelectionResult(BaseModel):
    recommended_vendors: List[Dict[str, Any]]
    reasoning: str
    top_vendor_id: int


class ContractGenerationRequest(BaseModel):
    contract_type: str
    vendor_id: int
    template_id: Optional[int] = None
    custom_terms: Optional[Dict[str, Any]] = None
    ai_enhance: bool = True


class ContractGenerationResult(BaseModel):
    contract_content: str
    ai_suggested_clauses: Dict[str, Any]
    risk_factors: List[str]
    recommendations: List[str]


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# API Response schemas
class APIResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int