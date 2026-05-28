"""
Calculation Service for FastAPI Backend
Orchestrates calculations across equipment, simulation, and analysis engines
Handles async operations for long-running simulations
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.equipment import Equipment
from app.models.simulation import Simulation, SimulationStatus
from app.models.analysis import AnalysisResult
from app.core.equipment_engine import EquipmentEngine
from app.core.simulation_engine import SimulationEngine
from app.core.analysis_engine import AnalysisEngine

logger = logging.getLogger(__name__)


class CalculationService:
    """
    Service for orchestrating complex calculations across multiple engines.
    Supports synchronous and asynchronous execution modes.
    """
    
    def __init__(self):
        """Initialize calculation service with engine instances."""
        self.equipment_engine = EquipmentEngine()
        self.simulation_engine = SimulationEngine()
        self.analysis_engine = AnalysisEngine()
        
        # Track running calculations
        self.running_calculations: Dict[str, asyncio.Task] = {}
        
        logger.info("Calculation Service initialized")
    
    async def run_equipment_analysis(
        self,
        db: Session,
        equipment_id: int,
        analysis_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run analysis on specific equipment.
        
        Args:
            db: Database session
            equipment_id: Equipment ID
            analysis_type: Type of analysis (performance, health, efficiency, etc.)
            parameters: Analysis parameters
        
        Returns:
            Analysis results dictionary
        """
        try:
            # Get equipment
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError(f"Equipment {equipment_id} not found")
            
            logger.info(f"Running {analysis_type} analysis on equipment {equipment.tag}")
            
            # Route to appropriate analysis method
            if analysis_type == "performance":
                result = await self._analyze_performance(db, equipment, parameters)
            elif analysis_type == "health":
                result = await self._analyze_health(db, equipment, parameters)
            elif analysis_type == "efficiency":
                result = await self._analyze_efficiency(db, equipment, parameters)
            elif analysis_type == "vibration":
                result = await self._analyze_vibration(db, equipment, parameters)
            elif analysis_type == "thermal":
                result = await self._analyze_thermal(db, equipment, parameters)
            else:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            # Store result in database
            analysis_record = AnalysisResult(
                equipment_id=equipment_id,
                analysis_type=analysis_type,
                parameters=parameters,
                results=result,
                status="completed",
                created_at=datetime.now(timezone.utc)
            )
            db.add(analysis_record)
            db.commit()
            
            logger.info(f"Analysis {analysis_type} completed for equipment {equipment.tag}")
            return result
            
        except Exception as e:
            logger.error(f"Error running equipment analysis: {e}")
            raise
    
    async def run_simulation(
        self,
        db: Session,
        equipment_id: int,
        simulation_type: str,
        parameters: Dict[str, Any],
        async_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Run simulation on equipment.
        
        Args:
            db: Database session
            equipment_id: Equipment ID
            simulation_type: Type of simulation
            parameters: Simulation parameters
            async_mode: Run in background if True
        
        Returns:
            Simulation results or task ID if async
        """
        try:
            equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
            if not equipment:
                raise ValueError(f"Equipment {equipment_id} not found")
            
            # Create simulation record
            simulation = Simulation(
                equipment_id=equipment_id,
                simulation_type=simulation_type,
                parameters=parameters,
                status=SimulationStatus.PENDING,
                created_at=datetime.now(timezone.utc)
            )
            db.add(simulation)
            db.commit()
            db.refresh(simulation)
            
            if async_mode:
                # Run in background
                task = asyncio.create_task(
                    self._run_simulation_async(db, simulation.id, equipment, parameters)
                )
                self.running_calculations[str(simulation.id)] = task
                
                return {
                    "simulation_id": simulation.id,
                    "status": "running",
                    "message": "Simulation started in background"
                }
            else:
                # Run synchronously
                result = await self._execute_simulation(equipment, simulation_type, parameters)
                
                # Update simulation record
                simulation.status = SimulationStatus.COMPLETED
                simulation.results = result
                simulation.completed_at = datetime.now(timezone.utc)
                db.commit()
                
                return result
                
        except Exception as e:
            logger.error(f"Error running simulation: {e}")
            if 'simulation' in locals():
                simulation.status = SimulationStatus.FAILED
                simulation.error_message = str(e)
                db.commit()
            raise
    
    async def _run_simulation_async(
        self,
        db: Session,
        simulation_id: int,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ):
        """Run simulation asynchronously in background."""
        try:
            simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
            simulation.status = SimulationStatus.RUNNING
            db.commit()
            
            result = await self._execute_simulation(equipment, simulation.simulation_type, parameters)
            
            simulation.status = SimulationStatus.COMPLETED
            simulation.results = result
            simulation.completed_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"Async simulation {simulation_id} completed")
            
        except Exception as e:
            logger.error(f"Error in async simulation {simulation_id}: {e}")
            simulation.status = SimulationStatus.FAILED
            simulation.error_message = str(e)
            db.commit()
        finally:
            if str(simulation_id) in self.running_calculations:
                del self.running_calculations[str(simulation_id)]
    
    async def _execute_simulation(
        self,
        equipment: Equipment,
        simulation_type: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute the actual simulation logic."""
        logger.info(f"Executing {simulation_type} simulation for {equipment.tag}")
        
        # Route to appropriate simulation engine method
        if simulation_type == "steady_state":
            return await self.simulation_engine.run_steady_state(equipment, parameters)
        elif simulation_type == "transient":
            return await self.simulation_engine.run_transient(equipment, parameters)
        elif simulation_type == "what_if":
            return await self.simulation_engine.run_what_if(equipment, parameters)
        elif simulation_type == "optimization":
            return await self.simulation_engine.run_optimization(equipment, parameters)
        else:
            raise ValueError(f"Unknown simulation type: {simulation_type}")
    
    async def _analyze_performance(
        self,
        db: Session,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze equipment performance."""
        return await self.analysis_engine.analyze_performance(equipment, parameters)
    
    async def _analyze_health(
        self,
        db: Session,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze equipment health."""
        return await self.analysis_engine.analyze_health(equipment, parameters)
    
    async def _analyze_efficiency(
        self,
        db: Session,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze equipment efficiency."""
        return await self.analysis_engine.analyze_efficiency(equipment, parameters)
    
    async def _analyze_vibration(
        self,
        db: Session,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze vibration data."""
        return await self.analysis_engine.analyze_vibration(equipment, parameters)
    
    async def _analyze_thermal(
        self,
        db: Session,
        equipment: Equipment,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze thermal performance."""
        return await self.analysis_engine.analyze_thermal(equipment, parameters)
    
    async def batch_calculate(
        self,
        db: Session,
        calculations: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Run multiple calculations in batch.
        
        Args:
            db: Database session
            calculations: List of calculation specifications
        
        Returns:
            List of results
        """
        tasks = []
        for calc in calculations:
            if calc['type'] == 'analysis':
                task = self.run_equipment_analysis(
                    db,
                    calc['equipment_id'],
                    calc['analysis_type'],
                    calc.get('parameters', {})
                )
            elif calc['type'] == 'simulation':
                task = self.run_simulation(
                    db,
                    calc['equipment_id'],
                    calc['simulation_type'],
                    calc.get('parameters', {}),
                    async_mode=False
                )
            else:
                continue
            
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [
            result if not isinstance(result, Exception) else {"error": str(result)}
            for result in results
        ]
    
    def get_simulation_status(self, db: Session, simulation_id: int) -> Dict[str, Any]:
        """Get status of a running simulation."""
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if not simulation:
            raise ValueError(f"Simulation {simulation_id} not found")
        
        is_running = str(simulation_id) in self.running_calculations
        
        return {
            "simulation_id": simulation_id,
            "status": simulation.status.value,
            "is_running": is_running,
            "created_at": simulation.created_at.isoformat() if simulation.created_at else None,
            "completed_at": simulation.completed_at.isoformat() if simulation.completed_at else None,
            "error_message": simulation.error_message
        }
    
    async def cancel_simulation(self, db: Session, simulation_id: int) -> bool:
        """Cancel a running simulation."""
        if str(simulation_id) not in self.running_calculations:
            return False
        
        task = self.running_calculations[str(simulation_id)]
        task.cancel()
        
        simulation = db.query(Simulation).filter(Simulation.id == simulation_id).first()
        if simulation:
            simulation.status = SimulationStatus.CANCELLED
            db.commit()
        
        del self.running_calculations[str(simulation_id)]
        logger.info(f"Simulation {simulation_id} cancelled")
        
        return True
    
    def get_running_calculations(self) -> List[str]:
        """Get list of currently running calculation IDs."""
        return list(self.running_calculations.keys())
    
    async def calculate_equipment_metrics(
        self,
        db: Session,
        equipment_id: int,
        metric_types: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate multiple metrics for equipment.
        
        Args:
            db: Database session
            equipment_id: Equipment ID
            metric_types: List of metric types to calculate
        
        Returns:
            Dictionary of calculated metrics
        """
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise ValueError(f"Equipment {equipment_id} not found")
        
        metrics = {}
        
        for metric_type in metric_types:
            try:
                if metric_type == "availability":
                    metrics[metric_type] = await self.equipment_engine.calculate_availability(equipment)
                elif metric_type == "reliability":
                    metrics[metric_type] = await self.equipment_engine.calculate_reliability(equipment)
                elif metric_type == "mtbf":
                    metrics[metric_type] = await self.equipment_engine.calculate_mtbf(equipment)
                elif metric_type == "mttr":
                    metrics[metric_type] = await self.equipment_engine.calculate_mttr(equipment)
                elif metric_type == "oee":
                    metrics[metric_type] = await self.equipment_engine.calculate_oee(equipment)
                else:
                    logger.warning(f"Unknown metric type: {metric_type}")
            except Exception as e:
                logger.error(f"Error calculating {metric_type}: {e}")
                metrics[metric_type] = {"error": str(e)}
        
        return metrics
    
    async def optimize_operating_parameters(
        self,
        db: Session,
        equipment_id: int,
        objective: str,
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize equipment operating parameters.
        
        Args:
            db: Database session
            equipment_id: Equipment ID
            objective: Optimization objective (efficiency, cost, throughput, etc.)
            constraints: Operating constraints
        
        Returns:
            Optimized parameters and expected improvements
        """
        equipment = db.query(Equipment).filter(Equipment.id == equipment_id).first()
        if not equipment:
            raise ValueError(f"Equipment {equipment_id} not found")
        
        logger.info(f"Optimizing {equipment.tag} for {objective}")
        
        # Run optimization simulation
        result = await self.simulation_engine.run_optimization(
            equipment,
            {
                "objective": objective,
                "constraints": constraints,
                "current_parameters": equipment.operating_parameters
            }
        )
        
        return result


# Singleton instance
_calculation_service = None

def get_calculation_service() -> CalculationService:
    """Get singleton calculation service instance."""
    global _calculation_service
    if _calculation_service is None:
        _calculation_service = CalculationService()
    return _calculation_service