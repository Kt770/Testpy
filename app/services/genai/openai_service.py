import openai
from typing import Dict, List, Any, Optional
import json
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIService:
    def __init__(self):
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
        else:
            logger.warning("OpenAI API key not configured")

    async def analyze_proposal(self, proposal_content: str, vendor_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a vendor proposal using GPT-4 to extract insights, risks, and recommendations.
        """
        try:
            prompt = f"""
            As an expert contract analyst, please analyze the following vendor proposal:

            VENDOR INFORMATION:
            Name: {vendor_info.get('name', 'Unknown')}
            Industry: {vendor_info.get('industry', 'Unknown')}
            Years in Business: {vendor_info.get('years_in_business', 'Unknown')}

            PROPOSAL CONTENT:
            {proposal_content}

            Please provide a comprehensive analysis in the following JSON format:
            {{
                "summary": "Brief 2-3 sentence summary of the proposal",
                "risk_assessment": {{
                    "financial_risk": "low/medium/high",
                    "delivery_risk": "low/medium/high", 
                    "technical_risk": "low/medium/high",
                    "compliance_risk": "low/medium/high",
                    "overall_risk": "low/medium/high",
                    "risk_factors": ["list of specific risk factors"]
                }},
                "compliance_check": {{
                    "legal_compliance": "compliant/non-compliant/unclear",
                    "industry_standards": "meets/exceeds/below/unclear",
                    "documentation": "complete/incomplete/unclear",
                    "issues": ["list of compliance issues if any"]
                }},
                "score": 85,
                "key_benefits": ["list of key benefits and strengths"],
                "concerns": ["list of concerns and weaknesses"],
                "recommendations": ["list of recommendations for decision makers"]
            }}

            Ensure the response is valid JSON.
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert contract analyst with 20+ years of experience in vendor proposal evaluation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            analysis_text = response.choices[0].message.content
            
            # Parse JSON response
            try:
                analysis = json.loads(analysis_text)
                return analysis
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {analysis_text}")
                return self._fallback_analysis()

        except Exception as e:
            logger.error(f"Error analyzing proposal: {str(e)}")
            return self._fallback_analysis()

    async def select_vendors(self, 
                           project_description: str, 
                           vendors: List[Dict[str, Any]], 
                           criteria: Dict[str, Any]) -> Dict[str, Any]:
        """
        Use AI to select and rank vendors based on project requirements.
        """
        try:
            vendor_summaries = []
            for vendor in vendors:
                summary = f"""
                - {vendor['name']} (ID: {vendor['id']})
                  Industry: {vendor.get('industry', 'N/A')}
                  Years in Business: {vendor.get('years_in_business', 'N/A')}
                  Specialties: {', '.join(vendor.get('specialties', [])) if vendor.get('specialties') else 'N/A'}
                  Overall Score: {vendor.get('overall_score', 0)}/100
                  Reliability Score: {vendor.get('reliability_score', 0)}/100
                """
                vendor_summaries.append(summary)

            vendors_text = "\n".join(vendor_summaries)

            prompt = f"""
            As a procurement expert, help select the best vendors for this project:

            PROJECT DESCRIPTION:
            {project_description}

            SELECTION CRITERIA:
            Budget Range: {criteria.get('budget_range', 'Not specified')}
            Required Skills: {', '.join(criteria.get('required_skills', [])) if criteria.get('required_skills') else 'Not specified'}
            Timeline: {criteria.get('project_timeline', 'Not specified')}
            Preferred Location: {criteria.get('preferred_location', 'Not specified')}

            AVAILABLE VENDORS:
            {vendors_text}

            Please provide your recommendation in the following JSON format:
            {{
                "recommended_vendors": [
                    {{
                        "vendor_id": 1,
                        "vendor_name": "Vendor Name",
                        "rank": 1,
                        "score": 95,
                        "strengths": ["list of strengths"],
                        "fit_reasoning": "Why this vendor is a good fit"
                    }}
                ],
                "reasoning": "Overall reasoning for vendor selection and ranking",
                "top_vendor_id": 1
            }}

            Rank up to 5 vendors in order of best fit for the project.
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert procurement specialist with extensive experience in vendor selection and evaluation."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1500,
                temperature=0.3
            )

            selection_text = response.choices[0].message.content
            
            try:
                selection = json.loads(selection_text)
                return selection
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {selection_text}")
                return self._fallback_vendor_selection(vendors)

        except Exception as e:
            logger.error(f"Error selecting vendors: {str(e)}")
            return self._fallback_vendor_selection(vendors)

    async def generate_contract(self, 
                              contract_type: str, 
                              vendor_info: Dict[str, Any], 
                              terms: Dict[str, Any],
                              template: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate contract content with AI-enhanced clauses and terms.
        """
        try:
            base_template = template or self._get_default_template(contract_type)
            
            prompt = f"""
            Generate a comprehensive {contract_type} contract with the following details:

            VENDOR INFORMATION:
            Name: {vendor_info.get('name', '')}
            Address: {vendor_info.get('address', '')}
            Contact: {vendor_info.get('contact_person', '')}

            CONTRACT TERMS:
            Value: {terms.get('value', 'TBD')} {terms.get('currency', 'USD')}
            Start Date: {terms.get('start_date', 'TBD')}
            End Date: {terms.get('end_date', 'TBD')}
            Description: {terms.get('description', '')}

            BASE TEMPLATE:
            {base_template}

            Please provide a response in the following JSON format:
            {{
                "contract_content": "Complete contract document with all clauses",
                "ai_suggested_clauses": {{
                    "termination_clause": "AI-enhanced termination clause",
                    "liability_clause": "AI-enhanced liability clause",
                    "intellectual_property": "AI-enhanced IP clause",
                    "payment_terms": "AI-enhanced payment terms"
                }},
                "risk_factors": ["List of potential legal/business risks"],
                "recommendations": ["List of recommendations for contract improvement"]
            }}

            Focus on legal accuracy, clarity, and protection for both parties.
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert contract lawyer with 25+ years of experience in business law and contract drafting."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=3000,
                temperature=0.2
            )

            contract_text = response.choices[0].message.content
            
            try:
                contract_data = json.loads(contract_text)
                return contract_data
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {contract_text}")
                return self._fallback_contract_generation()

        except Exception as e:
            logger.error(f"Error generating contract: {str(e)}")
            return self._fallback_contract_generation()

    async def enhance_contract_clauses(self, existing_contract: str, contract_type: str) -> Dict[str, Any]:
        """
        Enhance existing contract clauses with AI suggestions.
        """
        try:
            prompt = f"""
            Review and enhance the following {contract_type} contract:

            {existing_contract}

            Please provide suggestions for improvement in the following JSON format:
            {{
                "suggested_improvements": [
                    {{
                        "clause_type": "termination",
                        "current_clause": "Current clause text",
                        "suggested_clause": "Improved clause text",
                        "reasoning": "Why this improvement is recommended"
                    }}
                ],
                "missing_clauses": [
                    {{
                        "clause_type": "force_majeure",
                        "suggested_clause": "Suggested clause text",
                        "importance": "high/medium/low"
                    }}
                ],
                "risk_analysis": {{
                    "high_risk_areas": ["List of high-risk areas"],
                    "compliance_issues": ["List of potential compliance issues"],
                    "recommendations": ["List of overall recommendations"]
                }}
            }}
            """

            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a senior contract review specialist with expertise in risk assessment and legal compliance."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.3
            )

            enhancement_text = response.choices[0].message.content
            
            try:
                enhancements = json.loads(enhancement_text)
                return enhancements
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON response: {enhancement_text}")
                return {"suggested_improvements": [], "missing_clauses": [], "risk_analysis": {}}

        except Exception as e:
            logger.error(f"Error enhancing contract clauses: {str(e)}")
            return {"suggested_improvements": [], "missing_clauses": [], "risk_analysis": {}}

    def _fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when AI service fails"""
        return {
            "summary": "Analysis unavailable - AI service error",
            "risk_assessment": {
                "financial_risk": "medium",
                "delivery_risk": "medium",
                "technical_risk": "medium",
                "compliance_risk": "medium",
                "overall_risk": "medium",
                "risk_factors": ["Unable to assess - manual review required"]
            },
            "compliance_check": {
                "legal_compliance": "unclear",
                "industry_standards": "unclear",
                "documentation": "unclear",
                "issues": ["Manual review required"]
            },
            "score": 50,
            "key_benefits": ["Manual review required"],
            "concerns": ["AI analysis unavailable"],
            "recommendations": ["Conduct manual review of proposal"]
        }

    def _fallback_vendor_selection(self, vendors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Fallback vendor selection when AI service fails"""
        if not vendors:
            return {
                "recommended_vendors": [],
                "reasoning": "No vendors available",
                "top_vendor_id": None
            }
        
        # Sort by overall score
        sorted_vendors = sorted(vendors, key=lambda x: x.get('overall_score', 0), reverse=True)
        top_vendor = sorted_vendors[0]
        
        return {
            "recommended_vendors": [
                {
                    "vendor_id": top_vendor['id'],
                    "vendor_name": top_vendor['name'],
                    "rank": 1,
                    "score": top_vendor.get('overall_score', 0),
                    "strengths": ["Manual review required"],
                    "fit_reasoning": "Selected based on overall score - AI analysis unavailable"
                }
            ],
            "reasoning": "AI vendor selection unavailable - ranked by overall score",
            "top_vendor_id": top_vendor['id']
        }

    def _fallback_contract_generation(self) -> Dict[str, Any]:
        """Fallback contract generation when AI service fails"""
        return {
            "contract_content": "Contract generation unavailable - please use template",
            "ai_suggested_clauses": {},
            "risk_factors": ["Manual contract drafting required"],
            "recommendations": ["Use existing templates and legal review"]
        }

    def _get_default_template(self, contract_type: str) -> str:
        """Get default contract template based on type"""
        templates = {
            "service": """
            SERVICE AGREEMENT
            
            This Service Agreement ("Agreement") is entered into on [DATE] between [CLIENT_NAME] ("Client") and [VENDOR_NAME] ("Service Provider").
            
            1. SERVICES: The Service Provider agrees to provide the following services: [DESCRIPTION]
            
            2. TERM: This Agreement shall commence on [START_DATE] and continue until [END_DATE].
            
            3. COMPENSATION: Client agrees to pay Service Provider [AMOUNT] [CURRENCY] for the services.
            
            4. PAYMENT TERMS: [PAYMENT_TERMS]
            
            5. TERMINATION: Either party may terminate this Agreement with [NOTICE_PERIOD] written notice.
            
            6. CONFIDENTIALITY: Both parties agree to maintain confidentiality of proprietary information.
            
            7. LIABILITY: [LIABILITY_CLAUSE]
            
            8. GOVERNING LAW: This Agreement shall be governed by [JURISDICTION] law.
            """,
            "product": """
            PRODUCT PURCHASE AGREEMENT
            
            This Purchase Agreement ("Agreement") is entered into on [DATE] between [BUYER_NAME] ("Buyer") and [VENDOR_NAME] ("Seller").
            
            1. PRODUCTS: Seller agrees to sell and deliver the following products: [DESCRIPTION]
            
            2. DELIVERY: Products shall be delivered by [DELIVERY_DATE] to [DELIVERY_ADDRESS].
            
            3. PRICE: The total purchase price is [AMOUNT] [CURRENCY].
            
            4. PAYMENT: Payment terms are [PAYMENT_TERMS].
            
            5. WARRANTY: [WARRANTY_TERMS]
            
            6. RISK OF LOSS: Risk of loss passes to Buyer upon delivery.
            
            7. GOVERNING LAW: This Agreement shall be governed by [JURISDICTION] law.
            """
        }
        
        return templates.get(contract_type, templates["service"])