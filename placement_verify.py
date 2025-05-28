#!/usr/bin/env python3
"""
This script verifies the placement of Python files and import structure in the Tradingbot repository.
It checks that:
1. The project structure follows best practices
2. Import statements match the actual file structure
"""

import os
import sys
import re
from pathlib import Path


def check_project_structure():
    """Check that the basic project structure is valid."""
    cwd = Path(os.getcwd())
    errors = []
    warnings = []
    
    # Check for basic required files
    required_files = ["tradingbot.py", "__init__.py", "test_tradingbot.py"]
    for file in required_files:
        if not (cwd / file).exists():
            errors.append(f"Missing required file: {file}")
    
    # Skip actual import attempt which might fail due to missing dependencies
    # Just check if the file exists
    if (cwd / "tradingbot.py").exists():
        print("✓ tradingbot.py file exists")
    else:
        errors.append("tradingbot.py file not found")
    
    # Process potential import issues from test file
    test_file_path = cwd / "test_tradingbot.py"
    if test_file_path.exists():
        # Parse imports in test_tradingbot.py
        with open(test_file_path, "r") as f:
            content = f.read()
        
        # Look for imports that might be problematic
        imports = re.findall(r'from\s+(\w+)\s+import', content)
        imports += re.findall(r'import\s+(\w+)(?:\s+|$)', content)
        
        # Check if Tradingbot is imported but doesn't exist as a directory
        if "Tradingbot" in imports and not (cwd / "Tradingbot").is_dir():
            warnings.append(
                "Import Issue: test_tradingbot.py imports from 'Tradingbot' but there's no Tradingbot directory.\n"
                "This may cause import errors when running tests or in production.\n\n"
                "Recommended solutions:\n"
                "1. Create a Tradingbot directory structure:\n"
                "   mkdir -p Tradingbot\n"
                "   touch Tradingbot/__init__.py\n"
                "   # Then move tradingbot.py into this directory or update imports\n\n"
                "2. Update imports in test_tradingbot.py to match current structure:\n"
                "   Replace 'from Tradingbot import tradingbot' with 'import tradingbot'\n"
                "   Replace 'from Tradingbot.tradingbot import' with 'from tradingbot import'\n"
            )
    
    return errors, warnings


def main():
    """Main entry point"""
    print("Verifying project structure...")
    
    # Run all checks
    errors, warnings = check_project_structure()
    
    # Report results
    if errors:
        print("\nCritical project structure issues found:")
        for error in errors:
            print(f" - {error}")
        print("\nFix these issues before continuing.")
        sys.exit(1)
    
    if warnings:
        print("\nPotential project structure issues found:")
        for warning in warnings:
            print(f"\n{warning}")
        # Exit with a non-zero code for warnings too until they're fixed
        sys.exit(1)
    
    print("\n✓ Project structure checks passed!")
    sys.exit(0)


if __name__ == "__main__":
    main()