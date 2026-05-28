#!/usr/bin/env python
"""
Phase Inspection Script
Shows what classes and methods exist in each phase.
"""

import sys
import importlib
import inspect
from pathlib import Path

workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))

print("\n" + "="*80)
print("PHASE STRUCTURE INSPECTION")
print("="*80 + "\n")

for i in range(1, 16):
    module_name = f"core.phase{i}_integration"
    
    try:
        mod = importlib.import_module(module_name)
        
        # Get all classes
        classes = [name for name in dir(mod) if not name.startswith('_') and inspect.isclass(getattr(mod, name))]
        
        print(f"\n📦 PHASE {i}: {module_name}")
        print(f"   Classes: {len(classes)}")
        
        for cls_name in classes[:3]:  # Show first 3 classes
            cls = getattr(mod, cls_name)
            methods = [m for m in dir(cls) if not m.startswith('_') and callable(getattr(cls, m))]
            print(f"   • {cls_name} - {len(methods)} methods")
            for method in methods[:5]:  # Show first 5 methods
                print(f"     - {method}()")
            if len(methods) > 5:
                print(f"     ... and {len(methods) - 5} more")
    
    except ImportError as e:
        print(f"\n❌ PHASE {i}: IMPORT ERROR")
        print(f"   {str(e)}")
    except Exception as e:
        print(f"\n⚠️  PHASE {i}: ERROR")
        print(f"   {str(e)}")

print("\n" + "="*80)
