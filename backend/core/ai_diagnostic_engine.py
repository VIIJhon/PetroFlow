"""
PetroFlow Generative AI Diagnostic Engine
Advanced LLM-powered diagnostic system for equipment analysis and maintenance recommendations.

Features:
- LLM integration (OpenAI GPT-4, Claude, local models)
- Natural language diagnostic queries
- Root cause analysis using historical data
- Maintenance recommendation generation
- Technical documentation search and summarization
- Multi-modal analysis (text, sensor data, images)
- Context-aware responses with equipment history
"""

import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum

from .audit_logging_service import get_audit_logger
from .failure_prediction_engine import predict_failure, get_risk_level

audit_logger = get_audit_logger()


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"
    MOCK = "mock"  # For testing without API


@dataclass
class DiagnosticQuery:
    """Diagnostic query structure."""
    query_id: str
    equipment_id: str
    equipment_type: str
    query_text: str
    sensor_data: Dict[str, Any]
    historical_data: Optional[List[Dict[str, Any]]] = None
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class DiagnosticResponse:
    """Diagnostic response structure."""
    query_id: str
    diagnosis: str
    root_cause: str
    recommendations: List[str]
    confidence: float
    risk_level: str
    estimated_time_to_failure: Optional[str]
    maintenance_priority: str
    technical_details: Dict[str, Any]
    references: List[str]
    timestamp: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


class AIDiagnosticEngine:
    """
    AI-powered diagnostic engine with LLM integration.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize AI diagnostic engine.
        
        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config or self._load_default_config()
        self.provider = LLMProvider(self.config.get("provider", "mock"))
        self.model = self.config.get("model", "gpt-4")
        self.api_key = self.config.get("api_key", os.getenv("OPENAI_API_KEY", ""))
        self.max_tokens = self.config.get("max_tokens", 2000)
        self.temperature = self.config.get("temperature", 0.7)
        self.offline_mode = self.config.get("offline_mode", False)
        
        # Initialize LLM client
        self.llm_client = self._initialize_llm_client()
        
        # Knowledge base for offline fallback
        self.knowledge_base = self._load_knowledge_base()
        
        audit_logger.log_system(
            f"AI Diagnostic Engine initialized with provider: {self.provider.value}",
            action="AI_DIAGNOSTIC_INIT",
            level="INFO"
        )
    
    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration."""
        return {
            "provider": "mock",
            "model": "gpt-4",
            "max_tokens": 2000,
            "temperature": 0.7,
            "offline_mode": False,
            "enable_multimodal": True,
            "enable_context_memory": True,
            "max_context_length": 10,
            "confidence_threshold": 0.7,
            "languages": ["en", "es"]
        }
    
    def _initialize_llm_client(self) -> Optional[Any]:
        """Initialize LLM client based on provider."""
        if self.offline_mode or self.provider == LLMProvider.MOCK:
            return None
        
        try:
            if self.provider == LLMProvider.OPENAI:
                try:
                    import openai
                    openai.api_key = self.api_key
                    return openai
                except ImportError:
                    audit_logger.log_system(
                        "OpenAI library not installed, falling back to offline mode",
                        action="AI_DIAGNOSTIC_FALLBACK",
                        level="WARNING"
                    )
                    self.offline_mode = True
                    return None
            
            elif self.provider == LLMProvider.ANTHROPIC:
                try:
                    import anthropic
                    return anthropic.Anthropic(api_key=self.api_key)
                except ImportError:
                    audit_logger.log_system(
                        "Anthropic library not installed, falling back to offline mode",
                        action="AI_DIAGNOSTIC_FALLBACK",
                        level="WARNING"
                    )
                    self.offline_mode = True
                    return None
            
            elif self.provider == LLMProvider.LOCAL:
                # Local model integration (e.g., llama.cpp, transformers)
                audit_logger.log_system(
                    "Local LLM not implemented, using offline mode",
                    action="AI_DIAGNOSTIC_FALLBACK",
                    level="WARNING"
                )
                self.offline_mode = True
                return None
        
        except Exception as e:
            audit_logger.log_system(
                f"Failed to initialize LLM client: {str(e)}",
                action="AI_DIAGNOSTIC_ERROR",
                level="ERROR"
            )
            self.offline_mode = True
            return None
        
        return None
    
    def _load_knowledge_base(self) -> Dict[str, Any]:
        """Load knowledge base for offline diagnostics."""
        return {
            "pump": {
                "common_issues": [
                    {
                        "symptoms": ["high vibration", "noise"],
                        "cause": "Bearing wear or misalignment",
                        "recommendations": [
                            "Inspect and replace bearings",
                            "Check shaft alignment",
                            "Verify foundation stability"
                        ]
                    },
                    {
                        "symptoms": ["high temperature", "reduced flow"],
                        "cause": "Cavitation or impeller damage",
                        "recommendations": [
                            "Check suction pressure",
                            "Inspect impeller for damage",
                            "Verify NPSH requirements"
                        ]
                    },
                    {
                        "symptoms": ["seal leakage", "high temperature"],
                        "cause": "Mechanical seal failure",
                        "recommendations": [
                            "Replace mechanical seal",
                            "Check seal cooling system",
                            "Verify seal flush pressure"
                        ]
                    }
                ],
                "thresholds": {
                    "vibration": {"normal": 4.5, "warning": 7.1, "critical": 11.2},
                    "temperature": {"normal": 60, "warning": 90, "critical": 120},
                    "pressure": {"normal": 50, "warning": 80, "critical": 100}
                }
            },
            "compressor": {
                "common_issues": [
                    {
                        "symptoms": ["surge", "high vibration"],
                        "cause": "Operating in surge region",
                        "recommendations": [
                            "Adjust operating point",
                            "Install anti-surge control",
                            "Check recycle valve operation"
                        ]
                    },
                    {
                        "symptoms": ["high temperature", "reduced efficiency"],
                        "cause": "Fouling or intercooler issues",
                        "recommendations": [
                            "Clean compressor internals",
                            "Inspect intercooler",
                            "Check air filter condition"
                        ]
                    }
                ],
                "thresholds": {
                    "vibration": {"normal": 5.0, "warning": 8.0, "critical": 12.0},
                    "temperature": {"normal": 80, "warning": 110, "critical": 140},
                    "pressure_ratio": {"normal": 3.0, "warning": 4.5, "critical": 6.0}
                }
            },
            "turbine": {
                "common_issues": [
                    {
                        "symptoms": ["high vibration", "blade damage"],
                        "cause": "Blade erosion or foreign object damage",
                        "recommendations": [
                            "Inspect turbine blades",
                            "Check inlet filtration",
                            "Perform borescope inspection"
                        ]
                    },
                    {
                        "symptoms": ["high temperature", "reduced power"],
                        "cause": "Combustion issues or fuel quality",
                        "recommendations": [
                            "Check fuel quality",
                            "Inspect combustion chamber",
                            "Verify fuel nozzle condition"
                        ]
                    }
                ],
                "thresholds": {
                    "vibration": {"normal": 6.0, "warning": 9.0, "critical": 13.0},
                    "temperature": {"normal": 500, "warning": 700, "critical": 900},
                    "rpm": {"normal": 3600, "warning": 3800, "critical": 4000}
                }
            }
        }
    
    def diagnose(
        self,
        equipment_id: str,
        equipment_type: str,
        query_text: str,
        sensor_data: Dict[str, Any],
        historical_data: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DiagnosticResponse:
        """
        Perform AI-powered diagnostic analysis.
        
        Args:
            equipment_id: Unique equipment identifier
            equipment_type: Type of equipment (pump, compressor, turbine)
            query_text: Natural language diagnostic query
            sensor_data: Current sensor readings
            historical_data: Historical sensor data and events
            context: Additional context information
            
        Returns:
            DiagnosticResponse with diagnosis and recommendations
        """
        query_id = f"diag_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{equipment_id}"
        
        query = DiagnosticQuery(
            query_id=query_id,
            equipment_id=equipment_id,
            equipment_type=equipment_type,
            query_text=query_text,
            sensor_data=sensor_data,
            historical_data=historical_data,
            context=context
        )
        
        audit_logger.log_system(
            f"Diagnostic query initiated: {query_id}",
            action="AI_DIAGNOSTIC_QUERY",
            level="INFO",
            metadata={"equipment_id": equipment_id, "type": equipment_type}
        )
        
        try:
            if self.offline_mode or self.llm_client is None:
                response = self._offline_diagnosis(query)
            else:
                response = self._llm_diagnosis(query)
            
            audit_logger.log_system(
                f"Diagnostic completed: {query_id}",
                action="AI_DIAGNOSTIC_COMPLETE",
                level="INFO",
                metadata={
                    "confidence": response.confidence,
                    "risk_level": response.risk_level
                }
            )
            
            return response
        
        except Exception as e:
            audit_logger.log_system(
                f"Diagnostic error: {str(e)}",
                action="AI_DIAGNOSTIC_ERROR",
                level="ERROR"
            )
            
            # Fallback to offline diagnosis
            return self._offline_diagnosis(query)
    
    def _llm_diagnosis(self, query: DiagnosticQuery) -> DiagnosticResponse:
        """
        Perform diagnosis using LLM.
        
        Args:
            query: Diagnostic query
            
        Returns:
            DiagnosticResponse
        """
        # Prepare context for LLM
        context_text = self._prepare_llm_context(query)
        
        # Create prompt
        prompt = self._create_diagnostic_prompt(query, context_text)
        
        try:
            if self.provider == LLMProvider.OPENAI:
                response_text = self._query_openai(prompt)
            elif self.provider == LLMProvider.ANTHROPIC:
                response_text = self._query_anthropic(prompt)
            else:
                return self._offline_diagnosis(query)
            
            # Parse LLM response
            return self._parse_llm_response(query, response_text)
        
        except Exception as e:
            audit_logger.log_system(
                f"LLM query failed: {str(e)}",
                action="AI_LLM_ERROR",
                level="ERROR"
            )
            return self._offline_diagnosis(query)
    
    def _prepare_llm_context(self, query: DiagnosticQuery) -> str:
        """Prepare context information for LLM."""
        context_parts = []
        
        # Equipment information
        context_parts.append(f"Equipment Type: {query.equipment_type}")
        context_parts.append(f"Equipment ID: {query.equipment_id}")
        
        # Current sensor data
        context_parts.append("\nCurrent Sensor Readings:")
        for key, value in query.sensor_data.items():
            context_parts.append(f"  - {key}: {value}")
        
        # Historical data summary
        if query.historical_data:
            context_parts.append("\nRecent Historical Trends:")
            context_parts.append(f"  - Data points: {len(query.historical_data)}")
            # Add trend analysis
            trends = self._analyze_trends(query.historical_data)
            for key, trend in trends.items():
                context_parts.append(f"  - {key}: {trend}")
        
        # Additional context
        if query.context:
            context_parts.append("\nAdditional Context:")
            for key, value in query.context.items():
                context_parts.append(f"  - {key}: {value}")
        
        return "\n".join(context_parts)
    
    def _analyze_trends(self, historical_data: List[Dict[str, Any]]) -> Dict[str, str]:
        """Analyze trends in historical data."""
        trends = {}
        
        if not historical_data or len(historical_data) < 2:
            return trends
        
        # Extract time series for each parameter
        parameters = set()
        for record in historical_data:
            parameters.update(record.keys())
        
        parameters.discard('timestamp')
        
        for param in parameters:
            values = [record.get(param) for record in historical_data if param in record]
            values = [v for v in values if isinstance(v, (int, float))]
            
            if len(values) >= 2:
                # Simple trend analysis
                first_half = np.mean(values[:len(values)//2])
                second_half = np.mean(values[len(values)//2:])
                
                if second_half > first_half * 1.1:
                    trends[param] = "Increasing"
                elif second_half < first_half * 0.9:
                    trends[param] = "Decreasing"
                else:
                    trends[param] = "Stable"
        
        return trends
    
    def _create_diagnostic_prompt(self, query: DiagnosticQuery, context: str) -> str:
        """Create diagnostic prompt for LLM."""
        prompt = f"""You are an expert industrial equipment diagnostic system for oil and gas operations.

{context}

User Query: {query.query_text}

Please provide a comprehensive diagnostic analysis including:
1. Primary diagnosis of the current condition
2. Root cause analysis
3. Specific maintenance recommendations (prioritized)
4. Risk assessment and urgency level
5. Estimated time to failure (if applicable)
6. Technical details and supporting evidence

Format your response as JSON with the following structure:
{{
    "diagnosis": "Brief diagnosis summary",
    "root_cause": "Detailed root cause analysis",
    "recommendations": ["Recommendation 1", "Recommendation 2", ...],
    "confidence": 0.0-1.0,
    "risk_level": "low/medium/high/critical",
    "estimated_time_to_failure": "time estimate or null",
    "maintenance_priority": "low/medium/high/urgent",
    "technical_details": {{"key": "value"}},
    "references": ["Reference 1", "Reference 2", ...]
}}

Provide accurate, actionable insights based on the sensor data and equipment type."""
        
        return prompt
    
    def _query_openai(self, prompt: str) -> str:
        """Query OpenAI API."""
        try:
            if self.llm_client is None:
                raise Exception("OpenAI client not initialized")
            response = self.llm_client.ChatCompletion.create(  # type: ignore
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an expert industrial equipment diagnostic system."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            return response.choices[0].message.content  # type: ignore
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    def _query_anthropic(self, prompt: str) -> str:
        """Query Anthropic Claude API."""
        try:
            if self.llm_client is None:
                raise Exception("Anthropic client not initialized")
            response = self.llm_client.messages.create(  # type: ignore
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text  # type: ignore
        except Exception as e:
            raise Exception(f"Anthropic API error: {str(e)}")
    
    def _parse_llm_response(self, query: DiagnosticQuery, response_text: str) -> DiagnosticResponse:
        """Parse LLM response into DiagnosticResponse."""
        try:
            # Try to extract JSON from response
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx >= 0 and end_idx > start_idx:
                json_str = response_text[start_idx:end_idx]
                data = json.loads(json_str)
            else:
                # Fallback parsing
                data = {
                    "diagnosis": response_text[:200],
                    "root_cause": "Unable to parse detailed root cause",
                    "recommendations": ["Review equipment manually"],
                    "confidence": 0.5,
                    "risk_level": "medium",
                    "estimated_time_to_failure": None,
                    "maintenance_priority": "medium",
                    "technical_details": {},
                    "references": []
                }
            
            return DiagnosticResponse(
                query_id=query.query_id,
                diagnosis=data.get("diagnosis", "No diagnosis available"),
                root_cause=data.get("root_cause", "Unknown"),
                recommendations=data.get("recommendations", []),
                confidence=float(data.get("confidence", 0.7)),
                risk_level=data.get("risk_level", "medium"),
                estimated_time_to_failure=data.get("estimated_time_to_failure"),
                maintenance_priority=data.get("maintenance_priority", "medium"),
                technical_details=data.get("technical_details", {}),
                references=data.get("references", [])
            )
        
        except Exception as e:
            audit_logger.log_system(
                f"Failed to parse LLM response: {str(e)}",
                action="AI_PARSE_ERROR",
                level="WARNING"
            )
            
            # Return basic response
            return DiagnosticResponse(
                query_id=query.query_id,
                diagnosis=response_text[:200] if response_text else "Unable to generate diagnosis",
                root_cause="Unable to determine root cause",
                recommendations=["Manual inspection required"],
                confidence=0.5,
                risk_level="medium",
                estimated_time_to_failure=None,
                maintenance_priority="medium",
                technical_details={},
                references=[]
            )
    
    def _offline_diagnosis(self, query: DiagnosticQuery) -> DiagnosticResponse:
        """
        Perform rule-based diagnosis without LLM (offline mode).
        
        Args:
            query: Diagnostic query
            
        Returns:
            DiagnosticResponse
        """
        equipment_type = query.equipment_type.lower()
        sensor_data = query.sensor_data
        
        # Get equipment knowledge base
        kb = self.knowledge_base.get(equipment_type, {})
        thresholds = kb.get("thresholds", {})
        common_issues = kb.get("common_issues", [])
        
        # Analyze sensor data against thresholds
        anomalies = []
        risk_scores = []
        
        for param, value in sensor_data.items():
            if param in thresholds:
                threshold = thresholds[param]
                if value >= threshold.get("critical", float('inf')):
                    anomalies.append(f"{param} is CRITICAL ({value})")
                    risk_scores.append(1.0)
                elif value >= threshold.get("warning", float('inf')):
                    anomalies.append(f"{param} is in WARNING range ({value})")
                    risk_scores.append(0.6)
                else:
                    risk_scores.append(0.2)
        
        # Calculate overall risk
        avg_risk = np.mean(risk_scores) if risk_scores else 0.5
        
        if avg_risk >= 0.8:
            risk_level = "critical"
            maintenance_priority = "urgent"
        elif avg_risk >= 0.6:
            risk_level = "high"
            maintenance_priority = "high"
        elif avg_risk >= 0.4:
            risk_level = "medium"
            maintenance_priority = "medium"
        else:
            risk_level = "low"
            maintenance_priority = "low"
        
        # Match symptoms to common issues
        matched_issue = None
        for issue in common_issues:
            symptoms = issue.get("symptoms", [])
            # Simple keyword matching
            if any(symptom.lower() in query.query_text.lower() for symptom in symptoms):
                matched_issue = issue
                break
        
        # Generate diagnosis
        if anomalies:
            diagnosis = f"Equipment showing {len(anomalies)} anomalies: " + ", ".join(anomalies)
        else:
            diagnosis = "Equipment operating within normal parameters"
        
        # Root cause
        if matched_issue:
            root_cause = matched_issue.get("cause", "Unknown cause")
            recommendations = matched_issue.get("recommendations", [])
        else:
            root_cause = "Based on sensor readings, potential issues with " + ", ".join(
                [param for param, _ in sensor_data.items() if param in thresholds]
            )
            recommendations = [
                "Perform detailed equipment inspection",
                "Review maintenance history",
                "Monitor sensor trends closely"
            ]
        
        # Estimate time to failure using prediction engine
        try:
            failure_prob, days_to_failure, risk_level_pred, _ = predict_failure(equipment_type, sensor_data, sensor_data)
            estimated_ttf = f"{days_to_failure} days"
            confidence = failure_prob / 100.0
        except Exception:
            estimated_ttf = None
            confidence = 0.7
        
        return DiagnosticResponse(
            query_id=query.query_id,
            diagnosis=diagnosis,
            root_cause=root_cause,
            recommendations=recommendations,
            confidence=confidence,
            risk_level=risk_level,
            estimated_time_to_failure=estimated_ttf,
            maintenance_priority=maintenance_priority,
            technical_details={
                "anomalies": anomalies,
                "sensor_data": sensor_data,
                "thresholds": thresholds
            },
            references=[
                "PetroFlow Knowledge Base",
                f"{equipment_type.title()} Maintenance Manual"
            ]
        )
    
    def search_documentation(
        self,
        query: str,
        equipment_type: Optional[str] = None,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search technical documentation and return relevant results.
        
        Args:
            query: Search query
            equipment_type: Optional equipment type filter
            max_results: Maximum number of results
            
        Returns:
            List of search results with summaries
        """
        audit_logger.log_system(
            f"Documentation search: {query}",
            action="AI_DOC_SEARCH",
            level="INFO"
        )
        
        # In production, this would search a vector database or documentation system
        # For now, return mock results
        results = [
            {
                "title": f"{equipment_type or 'Equipment'} Maintenance Manual",
                "summary": "Comprehensive maintenance procedures and troubleshooting guide",
                "relevance": 0.95,
                "source": "Internal Documentation"
            },
            {
                "title": "Predictive Maintenance Best Practices",
                "summary": "Industry standards for predictive maintenance implementation",
                "relevance": 0.87,
                "source": "API Standards"
            },
            {
                "title": "Sensor Calibration Procedures",
                "summary": "Guidelines for sensor installation and calibration",
                "relevance": 0.75,
                "source": "Technical Manual"
            }
        ]
        
        return results[:max_results]
    
    def generate_maintenance_plan(
        self,
        equipment_id: str,
        equipment_type: str,
        diagnostic_response: DiagnosticResponse,
        timeframe_days: int = 30
    ) -> Dict[str, Any]:
        """
        Generate detailed maintenance plan based on diagnostic results.
        
        Args:
            equipment_id: Equipment identifier
            equipment_type: Type of equipment
            diagnostic_response: Diagnostic analysis results
            timeframe_days: Planning timeframe in days
            
        Returns:
            Detailed maintenance plan
        """
        plan = {
            "equipment_id": equipment_id,
            "equipment_type": equipment_type,
            "generated_at": datetime.now().isoformat(),
            "timeframe_days": timeframe_days,
            "priority": diagnostic_response.maintenance_priority,
            "risk_level": diagnostic_response.risk_level,
            "tasks": []
        }
        
        # Generate tasks from recommendations
        for idx, recommendation in enumerate(diagnostic_response.recommendations):
            task = {
                "task_id": f"task_{idx + 1}",
                "description": recommendation,
                "priority": diagnostic_response.maintenance_priority,
                "estimated_duration_hours": 2 + idx,
                "required_skills": ["Mechanical", "Electrical"],
                "required_parts": [],
                "scheduled_date": (datetime.now() + timedelta(days=idx * 3)).isoformat()
            }
            plan["tasks"].append(task)
        
        audit_logger.log_system(
            f"Maintenance plan generated for {equipment_id}",
            action="AI_MAINTENANCE_PLAN",
            level="INFO",
            metadata={"tasks": len(plan["tasks"])}
        )
        
        return plan
    
    def explain_diagnosis(self, diagnostic_response: DiagnosticResponse) -> str:
        """
        Generate human-readable explanation of diagnosis.
        
        Args:
            diagnostic_response: Diagnostic response to explain
            
        Returns:
            Formatted explanation text
        """
        explanation = f"""
DIAGNOSTIC ANALYSIS REPORT
{'=' * 50}

Equipment Diagnosis:
{diagnostic_response.diagnosis}

Root Cause Analysis:
{diagnostic_response.root_cause}

Risk Assessment:
- Risk Level: {diagnostic_response.risk_level.upper()}
- Confidence: {diagnostic_response.confidence * 100:.1f}%
- Maintenance Priority: {diagnostic_response.maintenance_priority.upper()}
{f"- Estimated Time to Failure: {diagnostic_response.estimated_time_to_failure}" if diagnostic_response.estimated_time_to_failure else ""}

Recommended Actions:
"""
        
        for idx, rec in enumerate(diagnostic_response.recommendations, 1):
            explanation += f"{idx}. {rec}\n"
        
        if diagnostic_response.technical_details:
            explanation += f"\nTechnical Details:\n"
            for key, value in diagnostic_response.technical_details.items():
                explanation += f"- {key}: {value}\n"
        
        if diagnostic_response.references:
            explanation += f"\nReferences:\n"
            for ref in diagnostic_response.references:
                explanation += f"- {ref}\n"
        
        explanation += f"\nReport Generated: {diagnostic_response.timestamp}\n"
        explanation += f"Query ID: {diagnostic_response.query_id}\n"
        
        return explanation


def create_diagnostic_engine(config_path: Optional[str] = None) -> AIDiagnosticEngine:
    """
    Factory function to create AI diagnostic engine instance.
    
    Args:
        config_path: Optional path to configuration file
        
    Returns:
        AIDiagnosticEngine instance
    """
    config = None
    if config_path:
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            audit_logger.log_system(
                f"Failed to load AI config: {str(e)}",
                action="AI_CONFIG_LOAD_FAILED",
                level="WARNING"
            )
    
    return AIDiagnosticEngine(config)