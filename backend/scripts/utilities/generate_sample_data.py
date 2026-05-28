"""
Sample Data Generator for Petroflow Demos
Author: Jhon Villegas
Purpose: Generate realistic equipment data for demonstrations and testing
Cost: $0 (uses only standard library and numpy)
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import numpy as np
except ImportError:
    print("NumPy not found. Installing...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "numpy"])
    import numpy as np


class SampleDataGenerator:
    """Generate realistic sample data for equipment monitoring"""
    
    def __init__(self, seed: int = 42):
        """Initialize generator with random seed for reproducibility"""
        random.seed(seed)
        np.random.seed(seed)
    
    def generate_pump_data(self, condition: str = "normal") -> Dict[str, Any]:
        """
        Generate pump data based on condition
        
        Args:
            condition: "normal", "warning", or "critical"
        
        Returns:
            Dictionary with pump parameters
        """
        base_data = {
            "equipment_id": f"P-{random.randint(100, 999)}",
            "equipment_type": "PUMP_CENTRIFUGAL",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if condition == "normal":
            parameters = {
                "discharge_pressure": np.random.uniform(250, 280),
                "suction_pressure": np.random.uniform(1.5, 2.5),
                "flow_rate": np.random.uniform(400, 450),
                "temperature": np.random.uniform(60, 75),
                "speed": np.random.uniform(3500, 3600),
                "vibration_velocity": np.random.uniform(1.5, 2.5),
                "bearing_temperature": np.random.uniform(50, 65),
                "power": np.random.uniform(180, 220)
            }
        elif condition == "warning":
            parameters = {
                "discharge_pressure": np.random.uniform(310, 325),  # Near limit
                "suction_pressure": np.random.uniform(1.8, 2.2),
                "flow_rate": np.random.uniform(420, 460),
                "temperature": np.random.uniform(80, 88),  # Elevated
                "speed": np.random.uniform(3550, 3650),
                "vibration_velocity": np.random.uniform(3.8, 4.3),  # High
                "bearing_temperature": np.random.uniform(75, 82),  # High
                "power": np.random.uniform(240, 270)
            }
        else:  # critical
            parameters = {
                "discharge_pressure": np.random.uniform(335, 345),  # Over limit
                "suction_pressure": np.random.uniform(1.2, 1.6),  # Low
                "flow_rate": np.random.uniform(380, 410),  # Low
                "temperature": np.random.uniform(92, 98),  # Very high
                "speed": np.random.uniform(3700, 3800),  # High
                "vibration_velocity": np.random.uniform(5.2, 6.0),  # Critical
                "bearing_temperature": np.random.uniform(88, 95),  # Critical
                "power": np.random.uniform(290, 320)
            }
        
        base_data["parameters"] = parameters
        base_data["units"] = {
            "discharge_pressure": "bar",
            "suction_pressure": "bar",
            "flow_rate": "m3/h",
            "temperature": "°C",
            "speed": "rpm",
            "vibration_velocity": "mm/s",
            "bearing_temperature": "°C",
            "power": "kW"
        }
        
        return base_data
    
    def generate_compressor_data(self, condition: str = "normal") -> Dict[str, Any]:
        """Generate compressor data based on condition"""
        base_data = {
            "equipment_id": f"C-{random.randint(100, 999)}",
            "equipment_type": "COMPRESSOR_CENTRIFUGAL",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if condition == "normal":
            parameters = {
                "suction_pressure": np.random.uniform(1.5, 2.0),
                "discharge_pressure": np.random.uniform(8.0, 10.0),
                "suction_temperature": np.random.uniform(25, 35),
                "discharge_temperature": np.random.uniform(120, 140),
                "flow_rate": np.random.uniform(8000, 9500),
                "speed": np.random.uniform(10000, 11000),
                "vibration_velocity": np.random.uniform(2.0, 3.0),
                "power": np.random.uniform(450, 550)
            }
        elif condition == "warning":
            parameters = {
                "suction_pressure": np.random.uniform(1.2, 1.5),  # Low
                "discharge_pressure": np.random.uniform(11.5, 12.5),  # High
                "suction_temperature": np.random.uniform(35, 42),
                "discharge_temperature": np.random.uniform(155, 168),  # High
                "flow_rate": np.random.uniform(7200, 8000),  # Low
                "speed": np.random.uniform(11200, 11800),
                "vibration_velocity": np.random.uniform(4.2, 4.8),  # High
                "power": np.random.uniform(580, 650)
            }
        else:  # critical
            parameters = {
                "suction_pressure": np.random.uniform(0.8, 1.1),  # Very low
                "discharge_pressure": np.random.uniform(13.5, 14.5),  # Very high
                "suction_temperature": np.random.uniform(45, 52),
                "discharge_temperature": np.random.uniform(175, 185),  # Critical
                "flow_rate": np.random.uniform(6500, 7200),  # Very low
                "speed": np.random.uniform(12000, 12500),
                "vibration_velocity": np.random.uniform(5.5, 6.5),  # Critical
                "power": np.random.uniform(680, 750)
            }
        
        base_data["parameters"] = parameters
        base_data["units"] = {
            "suction_pressure": "bar",
            "discharge_pressure": "bar",
            "suction_temperature": "°C",
            "discharge_temperature": "°C",
            "flow_rate": "m3/h",
            "speed": "rpm",
            "vibration_velocity": "mm/s",
            "power": "kW"
        }
        
        return base_data
    
    def generate_turbine_data(self, condition: str = "normal") -> Dict[str, Any]:
        """Generate turbine data based on condition"""
        base_data = {
            "equipment_id": f"T-{random.randint(100, 999)}",
            "equipment_type": "TURBINE_STEAM",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        if condition == "normal":
            parameters = {
                "inlet_pressure": np.random.uniform(40, 45),
                "exhaust_pressure": np.random.uniform(0.08, 0.12),
                "inlet_temperature": np.random.uniform(480, 510),
                "exhaust_temperature": np.random.uniform(120, 140),
                "speed": np.random.uniform(5000, 5500),
                "power_output": np.random.uniform(2800, 3200),
                "vibration_velocity": np.random.uniform(2.5, 3.5),
                "bearing_temperature": np.random.uniform(65, 75)
            }
        elif condition == "warning":
            parameters = {
                "inlet_pressure": np.random.uniform(48, 52),  # High
                "exhaust_pressure": np.random.uniform(0.14, 0.18),  # High
                "inlet_temperature": np.random.uniform(520, 545),  # High
                "exhaust_temperature": np.random.uniform(155, 170),  # High
                "speed": np.random.uniform(5600, 5900),
                "power_output": np.random.uniform(3300, 3600),
                "vibration_velocity": np.random.uniform(4.5, 5.2),  # High
                "bearing_temperature": np.random.uniform(82, 88)  # High
            }
        else:  # critical
            parameters = {
                "inlet_pressure": np.random.uniform(54, 58),  # Very high
                "exhaust_pressure": np.random.uniform(0.20, 0.25),  # Very high
                "inlet_temperature": np.random.uniform(555, 575),  # Critical
                "exhaust_temperature": np.random.uniform(180, 195),  # Critical
                "speed": np.random.uniform(6000, 6300),
                "power_output": np.random.uniform(3700, 4000),
                "vibration_velocity": np.random.uniform(6.0, 7.0),  # Critical
                "bearing_temperature": np.random.uniform(92, 98)  # Critical
            }
        
        base_data["parameters"] = parameters
        base_data["units"] = {
            "inlet_pressure": "bar",
            "exhaust_pressure": "bar",
            "inlet_temperature": "°C",
            "exhaust_temperature": "°C",
            "speed": "rpm",
            "power_output": "kW",
            "vibration_velocity": "mm/s",
            "bearing_temperature": "°C"
        }
        
        return base_data
    
    def generate_demo_dataset(self) -> Dict[str, List[Dict[str, Any]]]:
        """Generate complete demo dataset with multiple equipment and conditions"""
        dataset = {
            "pumps": {
                "normal": [self.generate_pump_data("normal") for _ in range(3)],
                "warning": [self.generate_pump_data("warning") for _ in range(2)],
                "critical": [self.generate_pump_data("critical") for _ in range(1)]
            },
            "compressors": {
                "normal": [self.generate_compressor_data("normal") for _ in range(2)],
                "warning": [self.generate_compressor_data("warning") for _ in range(2)],
                "critical": [self.generate_compressor_data("critical") for _ in range(1)]
            },
            "turbines": {
                "normal": [self.generate_turbine_data("normal") for _ in range(2)],
                "warning": [self.generate_turbine_data("warning") for _ in range(1)],
                "critical": [self.generate_turbine_data("critical") for _ in range(1)]
            }
        }
        
        return dataset
    
    def save_to_file(self, dataset: Dict, filename: str = "sample_data.json"):
        """Save dataset to JSON file"""
        output_path = Path(__file__).parent.parent / "storage" / filename
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(dataset, f, indent=2)
        
        print(f"Sample data saved to: {output_path}")
        return output_path


def main():
    """Generate and save sample data"""
    print("Petroflow Sample Data Generator")
    print("=" * 50)
    
    generator = SampleDataGenerator()
    
    print("\nGenerating demo dataset...")
    dataset = generator.generate_demo_dataset()
    
    print(f"\nGenerated:")
    print(f"  - Pumps: {sum(len(v) for v in dataset['pumps'].values())} units")
    print(f"  - Compressors: {sum(len(v) for v in dataset['compressors'].values())} units")
    print(f"  - Turbines: {sum(len(v) for v in dataset['turbines'].values())} units")
    
    output_file = generator.save_to_file(dataset)
    
    print(f"\nSample data ready for demos!")
    print(f"\nUsage:")
    print(f"  1. Start Petroflow: start_petroflow.bat")
    print(f"  2. Open API docs: http://localhost:8000/api/docs")
    print(f"  3. Use data from: {output_file}")
    print(f"  4. POST to /api/v2/equipment/validate")
    
    # Generate individual examples
    print("\n" + "=" * 50)
    print("Example: Normal Pump")
    print("=" * 50)
    normal_pump = generator.generate_pump_data("normal")
    print(json.dumps(normal_pump, indent=2))
    
    print("\n" + "=" * 50)
    print("Example: Critical Compressor")
    print("=" * 50)
    critical_compressor = generator.generate_compressor_data("critical")
    print(json.dumps(critical_compressor, indent=2))


if __name__ == "__main__":
    main()