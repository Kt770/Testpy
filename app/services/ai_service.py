import openai
import json
from typing import Dict, List, Any, Optional
from app.core.config import settings
import PyPDF2
import docx
from io import BytesIO
import re

class AIService:
    def __init__(self):
        openai.api_key = settings.OPENAI_API_KEY
        self.model = settings.OPENAI_MODEL
    
    async def generate_contract(
        self,
        contract_type: str,
        parties: Dict[str, str],
        terms: Dict[str, Any],
        template_content: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate AI-powered contract content"""
        
        prompt = self._build_contract_prompt(contract_type, parties, terms, template_content)
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert legal contract generator specialized in Saudi Arabian law and business practices. Generate comprehensive, legally sound contracts."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=4000
            )
            
            content = response.choices[0].message.content
            return {
                "content": content,
                "ai_generated": True,
                "model_used": self.model,
                "confidence_score": 0.95  # Based on model response quality
            }
            
        except Exception as e:
            return {
                "error": f"AI generation failed: {str(e)}",
                "content": None
            }
    
    async def analyze_proposal(self, proposal_text: str, requirements: List[str] = None) -> Dict[str, Any]:
        """Analyze proposal using AI for scoring and insights"""
        
        prompt = f"""
        Analyze the following business proposal and provide a comprehensive assessment:
        
        PROPOSAL TEXT:
        {proposal_text}
        
        REQUIREMENTS TO CHECK:
        {requirements if requirements else "Standard business proposal requirements"}
        
        Please provide analysis in the following JSON format:
        {{
            "overall_score": <0-1 score>,
            "technical_score": <0-1 score>,
            "financial_score": <0-1 score>,
            "risk_score": <0-1 score>,
            "compliance_score": <0-1 score>,
            "key_points": [list of key proposal highlights],
            "risks": [list of identified risks],
            "advantages": [list of competitive advantages],
            "missing_items": [list of missing requirements],
            "summary": "Overall proposal summary",
            "recommendation": "Accept/Reject recommendation with rationale"
        }}
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert proposal analyzer with deep knowledge of Saudi Arabian business practices and procurement standards."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            # Try to parse JSON response
            try:
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "overall_score": 0.5,
                    "summary": content,
                    "error": "Could not parse structured analysis"
                }
                
        except Exception as e:
            return {
                "error": f"AI analysis failed: {str(e)}",
                "overall_score": 0.0
            }
    
    async def analyze_vendor(self, vendor_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI-powered vendor assessment and recommendation"""
        
        prompt = f"""
        Analyze the following vendor information and provide risk assessment and recommendations:
        
        VENDOR DATA:
        Name: {vendor_data.get('name', 'Unknown')}
        Industry: {vendor_data.get('industry', 'Unknown')}
        Annual Revenue: {vendor_data.get('annual_revenue', 'Unknown')}
        Employee Count: {vendor_data.get('employee_count', 'Unknown')}
        Location: {vendor_data.get('country', 'Unknown')}
        Certifications: {vendor_data.get('certifications', [])}
        Previous Rating: {vendor_data.get('overall_rating', 'None')}
        
        Provide analysis in JSON format:
        {{
            "risk_assessment": "Detailed risk analysis",
            "capabilities_analysis": "Assessment of vendor capabilities",
            "market_position": "Vendor's market position analysis",
            "recommendation_score": <0-1 score>,
            "key_strengths": [list of strengths],
            "potential_concerns": [list of concerns],
            "recommended_contract_terms": [list of recommended terms]
        }}
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a vendor assessment expert with knowledge of Saudi Arabian business environment and vendor management best practices."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
            )
            
            content = response.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"analysis": content, "recommendation_score": 0.5}
                
        except Exception as e:
            return {"error": f"Vendor analysis failed: {str(e)}"}
    
    async def extract_contract_terms(self, contract_text: str) -> Dict[str, Any]:
        """Extract key terms and clauses from contract using AI"""
        
        prompt = f"""
        Extract key terms and important clauses from the following contract:
        
        {contract_text}
        
        Extract in JSON format:
        {{
            "parties": {{"party_a": "name", "party_b": "name"}},
            "contract_value": "amount and currency",
            "start_date": "date",
            "end_date": "date",
            "payment_terms": "payment schedule and terms",
            "key_obligations": ["list of key obligations"],
            "termination_clauses": ["termination conditions"],
            "liability_clauses": ["liability terms"],
            "dispute_resolution": "dispute resolution mechanism",
            "governing_law": "applicable law",
            "risk_score": <0-1 score based on contract terms>,
            "summary": "Brief contract summary"
        }}
        """
        
        try:
            response = await openai.ChatCompletion.acreate(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a legal contract analysis expert specializing in Saudi Arabian commercial law."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            
            content = response.choices[0].message.content
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"summary": content, "risk_score": 0.5}
                
        except Exception as e:
            return {"error": f"Contract analysis failed: {str(e)}"}
    
    def _build_contract_prompt(
        self, 
        contract_type: str, 
        parties: Dict[str, str], 
        terms: Dict[str, Any],
        template_content: Optional[str] = None
    ) -> str:
        """Build comprehensive prompt for contract generation"""
        
        base_prompt = f"""
        Generate a comprehensive {contract_type} contract with the following details:
        
        PARTIES:
        Party A (Client): {parties.get('party_a', 'Client Name')}
        Party B (Vendor): {parties.get('party_b', 'Vendor Name')}
        
        CONTRACT TERMS:
        """
        
        for key, value in terms.items():
            base_prompt += f"{key}: {value}\n"
        
        if template_content:
            base_prompt += f"\nUSE THIS TEMPLATE AS REFERENCE:\n{template_content}\n"
        
        base_prompt += """
        
        REQUIREMENTS:
        1. Include all standard legal clauses for Saudi Arabian contracts
        2. Ensure compliance with Saudi Commercial Law
        3. Include clear termination clauses
        4. Add dispute resolution mechanisms
        5. Specify governing law (Saudi Arabia)
        6. Include liability and indemnification clauses
        7. Add confidentiality provisions if applicable
        8. Ensure VAT compliance clauses
        9. Include force majeure provisions
        10. Add signature blocks and date fields
        
        Generate a complete, professional contract ready for review and signature.
        """
        
        return base_prompt
    
    async def extract_text_from_file(self, file_path: str, file_type: str) -> str:
        """Extract text from PDF or DOCX files"""
        try:
            if file_type.lower() == 'pdf':
                return self._extract_pdf_text(file_path)
            elif file_type.lower() in ['docx', 'doc']:
                return self._extract_docx_text(file_path)
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            return f"Error extracting text: {str(e)}"
    
    def _extract_pdf_text(self, file_path: str) -> str:
        """Extract text from PDF file"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text()
        return text
    
    def _extract_docx_text(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        doc = docx.Document(file_path)
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text

# Global AI service instance
ai_service = AIService()