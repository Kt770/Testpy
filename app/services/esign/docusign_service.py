import base64
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import requests
from docusign_esign import ApiClient, EnvelopesApi, EnvelopeDefinition, Document, Signer, SignHere, Tabs, Recipients
from docusign_esign.rest import ApiException
from app.core.config import settings
from app.models.models import Contract, WorkflowStep
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class DocuSignService:
    def __init__(self):
        self.integration_key = settings.DOCUSIGN_INTEGRATION_KEY
        self.user_id = settings.DOCUSIGN_USER_ID
        self.account_id = settings.DOCUSIGN_ACCOUNT_ID
        self.base_path = settings.DOCUSIGN_BASE_PATH
        self.private_key_path = settings.DOCUSIGN_PRIVATE_KEY_PATH
        
        self.api_client = None
        self.access_token = None
        
        if self.integration_key and self.user_id:
            self._initialize_client()
        else:
            logger.warning("DocuSign credentials not fully configured")

    def _initialize_client(self):
        """Initialize DocuSign API client with JWT authentication."""
        try:
            self.api_client = ApiClient()
            self.api_client.host = self.base_path
            
            # Get access token using JWT
            self.access_token = self._get_jwt_token()
            
            if self.access_token:
                self.api_client.set_default_header("Authorization", f"Bearer {self.access_token}")
                logger.info("DocuSign client initialized successfully")
            else:
                logger.error("Failed to obtain DocuSign access token")
                
        except Exception as e:
            logger.error(f"Error initializing DocuSign client: {str(e)}")

    def _get_jwt_token(self) -> Optional[str]:
        """Get JWT access token for DocuSign API."""
        try:
            # In a real implementation, you would use the DocuSign SDK's JWT authentication
            # For now, we'll return a placeholder
            # This should be implemented with proper JWT token generation
            logger.warning("JWT token generation not implemented - using placeholder")
            return None
            
        except Exception as e:
            logger.error(f"Error getting JWT token: {str(e)}")
            return None

    async def create_envelope(self, 
                            contract_id: int, 
                            signers: List[Dict[str, str]], 
                            document_content: str,
                            db: Session) -> Dict[str, Any]:
        """
        Create a DocuSign envelope for contract signing.
        
        Args:
            contract_id: ID of the contract to be signed
            signers: List of signers with name and email
            document_content: The contract document content
            db: Database session
        """
        try:
            if not self.api_client or not self.access_token:
                return await self._create_mock_envelope(contract_id, signers, db)

            # Get contract from database
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if not contract:
                raise ValueError(f"Contract with ID {contract_id} not found")

            # Create the envelope definition
            envelope_definition = EnvelopeDefinition()
            envelope_definition.email_subject = f"Please sign: {contract.title}"
            envelope_definition.email_blurb = f"Please review and sign the contract: {contract.title}"

            # Create document
            document = Document()
            document.document_base64 = base64.b64encode(document_content.encode()).decode()
            document.name = f"{contract.title}.pdf"
            document.file_extension = "pdf"
            document.document_id = "1"

            envelope_definition.documents = [document]

            # Create signers
            envelope_signers = []
            for i, signer_info in enumerate(signers, 1):
                signer = Signer()
                signer.email = signer_info["email"]
                signer.name = signer_info["name"]
                signer.recipient_id = str(i)
                signer.routing_order = str(i)

                # Add signature tabs
                sign_here = SignHere()
                sign_here.document_id = "1"
                sign_here.page_number = "1"
                sign_here.recipient_id = str(i)
                sign_here.tab_label = f"SignHere{i}"
                sign_here.x_position = "100"
                sign_here.y_position = str(200 + (i * 50))

                tabs = Tabs()
                tabs.sign_here_tabs = [sign_here]
                signer.tabs = tabs

                envelope_signers.append(signer)

            # Set recipients
            recipients = Recipients()
            recipients.signers = envelope_signers
            envelope_definition.recipients = recipients

            # Set status to 'sent' to immediately send the envelope
            envelope_definition.status = "sent"

            # Create the envelope
            envelopes_api = EnvelopesApi(self.api_client)
            results = envelopes_api.create_envelope(self.account_id, envelope_definition=envelope_definition)

            # Update contract with envelope ID
            contract.signature_envelope_id = results.envelope_id
            contract.status = "sent_for_signature"
            db.commit()

            # Create workflow steps for signing
            await self._create_signing_workflow_steps(contract_id, signers, db)

            return {
                "success": True,
                "envelope_id": results.envelope_id,
                "status": results.status,
                "signers_count": len(signers),
                "contract_id": contract_id
            }

        except ApiException as e:
            logger.error(f"DocuSign API error: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": f"DocuSign API error: {str(e)}",
                "envelope_id": None
            }
        except Exception as e:
            logger.error(f"Error creating envelope: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "envelope_id": None
            }

    async def _create_mock_envelope(self, contract_id: int, signers: List[Dict[str, str]], db: Session) -> Dict[str, Any]:
        """Create a mock envelope when DocuSign is not configured."""
        try:
            # Generate a mock envelope ID
            mock_envelope_id = f"mock-envelope-{contract_id}-{int(datetime.now().timestamp())}"
            
            # Update contract
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if contract:
                contract.signature_envelope_id = mock_envelope_id
                contract.status = "sent_for_signature"
                db.commit()

            # Create workflow steps
            await self._create_signing_workflow_steps(contract_id, signers, db)

            return {
                "success": True,
                "envelope_id": mock_envelope_id,
                "status": "sent",
                "signers_count": len(signers),
                "contract_id": contract_id,
                "note": "Mock envelope created - DocuSign not configured"
            }

        except Exception as e:
            logger.error(f"Error creating mock envelope: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e),
                "envelope_id": None
            }

    async def _create_signing_workflow_steps(self, contract_id: int, signers: List[Dict[str, str]], db: Session):
        """Create workflow steps for each signer."""
        try:
            for i, signer in enumerate(signers, 1):
                workflow_step = WorkflowStep(
                    step_name=f"Signature Required - {signer['name']}",
                    step_order=i,
                    status="pending",
                    assigned_to=signer["email"],
                    due_date=datetime.now() + timedelta(days=7),  # 7 days to sign
                    contract_id=contract_id,
                    notes=f"Awaiting signature from {signer['name']} ({signer['email']})"
                )
                db.add(workflow_step)
            
            db.commit()

        except Exception as e:
            logger.error(f"Error creating workflow steps: {str(e)}")
            db.rollback()

    async def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get the status of a DocuSign envelope."""
        try:
            if not self.api_client or not self.access_token:
                return await self._get_mock_envelope_status(envelope_id)

            envelopes_api = EnvelopesApi(self.api_client)
            envelope = envelopes_api.get_envelope(self.account_id, envelope_id)

            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": envelope.status,
                "created_date": envelope.created_date_time,
                "completed_date": envelope.completed_date_time,
                "status_date": envelope.status_changed_date_time
            }

        except ApiException as e:
            logger.error(f"DocuSign API error getting envelope status: {str(e)}")
            return {
                "success": False,
                "error": f"DocuSign API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error getting envelope status: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_mock_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get mock envelope status when DocuSign is not configured."""
        # Mock status progression based on envelope age
        if envelope_id.startswith("mock-envelope-"):
            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": "sent",
                "created_date": datetime.now().isoformat(),
                "completed_date": None,
                "status_date": datetime.now().isoformat(),
                "note": "Mock status - DocuSign not configured"
            }
        
        return {
            "success": False,
            "error": "Envelope not found"
        }

    async def get_envelope_recipients(self, envelope_id: str) -> Dict[str, Any]:
        """Get the recipients and their signing status for an envelope."""
        try:
            if not self.api_client or not self.access_token:
                return await self._get_mock_envelope_recipients(envelope_id)

            envelopes_api = EnvelopesApi(self.api_client)
            recipients = envelopes_api.list_recipients(self.account_id, envelope_id)

            recipient_status = []
            for signer in recipients.signers:
                recipient_status.append({
                    "name": signer.name,
                    "email": signer.email,
                    "status": signer.status,
                    "signed_date": signer.signed_date_time,
                    "delivery_method": signer.delivery_method
                })

            return {
                "success": True,
                "envelope_id": envelope_id,
                "recipients": recipient_status,
                "total_recipients": len(recipient_status)
            }

        except ApiException as e:
            logger.error(f"DocuSign API error getting recipients: {str(e)}")
            return {
                "success": False,
                "error": f"DocuSign API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error getting envelope recipients: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _get_mock_envelope_recipients(self, envelope_id: str) -> Dict[str, Any]:
        """Get mock envelope recipients when DocuSign is not configured."""
        if envelope_id.startswith("mock-envelope-"):
            return {
                "success": True,
                "envelope_id": envelope_id,
                "recipients": [
                    {
                        "name": "Mock Signer",
                        "email": "mock@example.com",
                        "status": "sent",
                        "signed_date": None,
                        "delivery_method": "email"
                    }
                ],
                "total_recipients": 1,
                "note": "Mock recipients - DocuSign not configured"
            }
        
        return {
            "success": False,
            "error": "Envelope not found"
        }

    async def get_signed_document(self, envelope_id: str, document_id: str = "combined") -> Dict[str, Any]:
        """Download the signed document from DocuSign."""
        try:
            if not self.api_client or not self.access_token:
                return {
                    "success": False,
                    "error": "DocuSign not configured - cannot download document"
                }

            envelopes_api = EnvelopesApi(self.api_client)
            document = envelopes_api.get_document(self.account_id, document_id, envelope_id)

            return {
                "success": True,
                "envelope_id": envelope_id,
                "document_data": document,
                "document_id": document_id
            }

        except ApiException as e:
            logger.error(f"DocuSign API error getting document: {str(e)}")
            return {
                "success": False,
                "error": f"DocuSign API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error getting signed document: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def void_envelope(self, envelope_id: str, reason: str = "Voided by system") -> Dict[str, Any]:
        """Void a DocuSign envelope."""
        try:
            if not self.api_client or not self.access_token:
                return {
                    "success": True,
                    "envelope_id": envelope_id,
                    "status": "voided",
                    "note": "Mock void - DocuSign not configured"
                }

            envelopes_api = EnvelopesApi(self.api_client)
            
            # Create envelope update to void
            envelope_definition = EnvelopeDefinition()
            envelope_definition.status = "voided"
            envelope_definition.voided_reason = reason

            result = envelopes_api.update(self.account_id, envelope_id, envelope=envelope_definition)

            return {
                "success": True,
                "envelope_id": envelope_id,
                "status": result.status,
                "voided_reason": reason
            }

        except ApiException as e:
            logger.error(f"DocuSign API error voiding envelope: {str(e)}")
            return {
                "success": False,
                "error": f"DocuSign API error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Error voiding envelope: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

    async def update_contract_status_from_envelope(self, envelope_id: str, db: Session) -> Dict[str, Any]:
        """Update contract status based on DocuSign envelope status."""
        try:
            # Get envelope status
            envelope_status = await self.get_envelope_status(envelope_id)
            
            if not envelope_status["success"]:
                return envelope_status

            # Find contract with this envelope ID
            contract = db.query(Contract).filter(Contract.signature_envelope_id == envelope_id).first()
            
            if not contract:
                return {
                    "success": False,
                    "error": f"Contract not found for envelope {envelope_id}"
                }

            # Update contract status based on envelope status
            docusign_status = envelope_status["status"]
            
            if docusign_status == "completed":
                contract.status = "signed"
                # Update workflow steps
                workflow_steps = db.query(WorkflowStep).filter(
                    WorkflowStep.contract_id == contract.id,
                    WorkflowStep.step_name.like("Signature Required%")
                ).all()
                
                for step in workflow_steps:
                    step.status = "completed"
                    step.completed_at = datetime.now()
                    
            elif docusign_status == "voided":
                contract.status = "terminated"
            elif docusign_status == "declined":
                contract.status = "draft"  # Reset to draft for revision

            db.commit()

            return {
                "success": True,
                "contract_id": contract.id,
                "old_status": contract.status,
                "new_status": contract.status,
                "envelope_status": docusign_status
            }

        except Exception as e:
            logger.error(f"Error updating contract status: {str(e)}")
            db.rollback()
            return {
                "success": False,
                "error": str(e)
            }

    async def send_reminder(self, envelope_id: str) -> Dict[str, Any]:
        """Send a reminder to recipients who haven't signed."""
        try:
            if not self.api_client or not self.access_token:
                return {
                    "success": True,
                    "envelope_id": envelope_id,
                    "note": "Mock reminder sent - DocuSign not configured"
                }

            # This would implement the actual DocuSign reminder functionality
            # For now, return a mock response
            return {
                "success": True,
                "envelope_id": envelope_id,
                "reminder_sent": True,
                "note": "Reminder functionality not yet implemented"
            }

        except Exception as e:
            logger.error(f"Error sending reminder: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }