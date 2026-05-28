#!/usr/bin/env python
"""
Phase Inspection Script - Simple Version
"""

import sys
import importlib
import inspect
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))

print("\n" + "="*80)
print("PHASE STRUCTURE INSPECTION")
print("="*80)

for i in range(1, 16):
    module_name = f"core.phase{i}_integration"
    
    try:
        mod = importlib.import_module(module_name)
        
        # Get all classes
        classes = [name for name in dir(mod) if not name.startswith('_') and inspect.isclass(getattr(mod, name))]
        
        print(f"\nPHASE {i}: {module_name}")
        print(f"  Classes: {len(classes)}")
        
        for cls_name in classes[:2]:  # Show first 2 classes
            cls = getattr(mod, cls_name)
            methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m))]
            print(f"  Class: {cls_name} ({len(methods)} methods)")
            for method in methods[:8]:  # Show first 8 methods
                print(f"    - {method}")
    
    except ImportError as e:
        print(f"\nPHASE {i}: IMPORT ERROR - {str(e)}")
    except Exception as e:
        print(f"\nPHASE {i}: ERROR - {str(e)}")

print("\n" + "="*80)
