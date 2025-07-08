from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timedelta
from app.core.config import settings
import httpx
import json
import base64

class SignatureService:
    def __init__(self):
        self.base_url = settings.DOCUSIGN_BASE_URL
        self.client_id = settings.DOCUSIGN_CLIENT_ID
        self.client_secret = settings.DOCUSIGN_CLIENT_SECRET
        self.access_token = None
        
    async def create_envelope(
        self,
        document_path: str,
        signers: List[Dict[str, str]],
        email_subject: str,
        email_message: str,
        contract_id: int
    ) -> Dict[str, Any]:
        """Create DocuSign envelope for contract signing"""
        
        try:
            # Ensure we have a valid access token
            await self._ensure_access_token()
            
            # Prepare document
            with open(document_path, 'rb') as file:
                document_base64 = base64.b64encode(file.read()).decode()
            
            # Build envelope definition
            envelope_definition = {
                "emailSubject": email_subject,
                "emailBlurb": email_message,
                "status": "sent",
                "documents": [
                    {
                        "documentBase64": document_base64,
                        "name": f"Contract_{contract_id}.pdf",
                        "fileExtension": "pdf",
                        "documentId": "1"
                    }
                ],
                "recipients": {
                    "signers": self._build_signers_list(signers)
                }
            }
            
            # Send envelope creation request
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v2.1/accounts/{await self._get_account_id()}/envelopes",
                    headers=headers,
                    json=envelope_definition
                )
            
            if response.status_code == 201:
                result = response.json()
                return {
                    "success": True,
                    "envelope_id": result.get("envelopeId"),
                    "status": result.get("status"),
                    "status_datetime": result.get("statusDateTime"),
                    "uri": result.get("uri")
                }
            else:
                return {
                    "success": False,
                    "error": f"DocuSign API error: {response.status_code} - {response.text}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Envelope creation failed: {str(e)}"
            }
    
    async def get_envelope_status(self, envelope_id: str) -> Dict[str, Any]:
        """Get current status of DocuSign envelope"""
        
        try:
            await self._ensure_access_token()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2.1/accounts/{await self._get_account_id()}/envelopes/{envelope_id}",
                    headers=headers
                )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "success": True,
                    "status": result.get("status"),
                    "created_datetime": result.get("createdDateTime"),
                    "sent_datetime": result.get("sentDateTime"),
                    "completed_datetime": result.get("completedDateTime"),
                    "status_changed_datetime": result.get("statusChangedDateTime")
                }
            else:
                return {
                    "success": False,
                    "error": f"DocuSign API error: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Status check failed: {str(e)}"
            }
    
    async def download_signed_document(self, envelope_id: str, document_id: str = "1") -> Dict[str, Any]:
        """Download signed document from DocuSign"""
        
        try:
            await self._ensure_access_token()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/v2.1/accounts/{await self._get_account_id()}/envelopes/{envelope_id}/documents/{document_id}",
                    headers=headers
                )
            
            if response.status_code == 200:
                return {
                    "success": True,
                    "document_content": response.content,
                    "content_type": response.headers.get("content-type", "application/pdf")
                }
            else:
                return {
                    "success": False,
                    "error": f"Document download failed: {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Download failed: {str(e)}"
            }
    
    async def send_reminder(self, envelope_id: str) -> Dict[str, Any]:
        """Send reminder to pending signers"""
        
        try:
            await self._ensure_access_token()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            reminder_data = {
                "reminderEnabled": "true",
                "reminderDelay": "2",
                "reminderFrequency": "2"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/v2.1/accounts/{await self._get_account_id()}/envelopes/{envelope_id}/notification",
                    headers=headers,
                    json=reminder_data
                )
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Reminder failed: {str(e)}"
            }
    
    async def void_envelope(self, envelope_id: str, reason: str) -> Dict[str, Any]:
        """Void an envelope (cancel signing process)"""
        
        try:
            await self._ensure_access_token()
            
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            void_data = {
                "status": "voided",
                "voidedReason": reason
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"{self.base_url}/v2.1/accounts/{await self._get_account_id()}/envelopes/{envelope_id}",
                    headers=headers,
                    json=void_data
                )
            
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Void failed: {str(e)}"
            }
    
    def _build_signers_list(self, signers: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Build DocuSign signers list from input data"""
        
        docusign_signers = []
        for i, signer in enumerate(signers):
            docusign_signers.append({
                "email": signer["email"],
                "name": signer["name"],
                "recipientId": str(i + 1),
                "routingOrder": str(i + 1),
                "tabs": {
                    "signHereTabs": [
                        {
                            "documentId": "1",
                            "pageNumber": "1",
                            "recipientId": str(i + 1),
                            "tabLabel": f"SignHere{i + 1}",
                            "xPosition": "100",
                            "yPosition": "100"
                        }
                    ],
                    "dateSignedTabs": [
                        {
                            "documentId": "1",
                            "pageNumber": "1",
                            "recipientId": str(i + 1),
                            "tabLabel": f"DateSigned{i + 1}",
                            "xPosition": "300",
                            "yPosition": "100"
                        }
                    ]
                }
            })
        
        return docusign_signers
    
    async def _ensure_access_token(self):
        """Ensure we have a valid DocuSign access token"""
        
        if not self.access_token:
            await self._get_access_token()
    
    async def _get_access_token(self):
        """Get DocuSign access token using client credentials"""
        
        try:
            auth_string = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            headers = {
                "Authorization": f"Basic {auth_string}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            data = "grant_type=client_credentials&scope=signature"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://account-d.docusign.com/oauth/token",
                    headers=headers,
                    data=data
                )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result.get("access_token")
            else:
                raise Exception(f"Authentication failed: {response.status_code}")
                
        except Exception as e:
            raise Exception(f"DocuSign authentication error: {str(e)}")
    
    async def _get_account_id(self) -> str:
        """Get DocuSign account ID"""
        
        # In production, this should be fetched from user info endpoint
        # For demo purposes, returning a placeholder
        return "YOUR_ACCOUNT_ID"
    
    # Fallback manual signature workflow
    async def create_manual_signature_workflow(
        self,
        contract_id: int,
        signers: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """Create manual signature workflow when e-signature service unavailable"""
        
        workflow_id = str(uuid.uuid4())
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "method": "manual",
            "signers": signers,
            "instructions": "Manual signature process initiated. Please coordinate with signers for wet signatures.",
            "expiry_date": datetime.now() + timedelta(days=30)
        }

# Global signature service instance
signature_service = SignatureService()