#!/usr/bin/env python3
"""
Analyze dependencies and identify what files are actually used
"""

import os
import re
from pathlib import Path
from typing import Dict, Set, List

def extract_imports(file_path: str) -> Set[str]:
    """Extract local imports from a Python file"""
    imports = set()
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find import statements
        import_patterns = [
            r'from\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)\s+import',
            r'import\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)',
        ]
        
        for pattern in import_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                # Only include local imports (not external packages)
                if not match.startswith(('pipecat', 'fastapi', 'uvicorn', 'asyncio', 'json', 'os', 'sys', 'typing', 'datetime', 'pathlib', 'structlog', 'dotenv', 'pytest', 'numpy', 'base64', 'time', 'requests', 'websockets', 'httpx', 'aiohttp', 'aiofiles', 'openai', 'loguru', 'sqlite3', 'jwt', 'passlib', 'pydantic', 'email_validator', 'dataclasses')):
                    imports.add(match)
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return imports

def analyze_dependencies():
    """Analyze dependencies in the project"""
    project_root = Path('.')
    python_files = list(project_root.rglob('*.py'))
    
    # Exclude test files and __pycache__ for main analysis
    main_files = [f for f in python_files if not str(f).startswith(('test_', 'tests/', '__pycache__'))]
    test_files = [f for f in python_files if str(f).startswith(('test_', 'tests/'))]
    
    dependencies = {}
    file_to_module = {}
    
    # Map files to module names
    for file_path in python_files:
        if file_path.name == '__init__.py':
            module_name = str(file_path.parent).replace('/', '.').replace('\\', '.')
        else:
            module_name = str(file_path.with_suffix('')).replace('/', '.').replace('\\', '.')
        file_to_module[str(file_path)] = module_name
    
    # Extract dependencies
    for file_path in main_files:
        imports = extract_imports(str(file_path))
        dependencies[str(file_path)] = imports
    
    # Find entry points (files with if __name__ == "__main__")
    entry_points = []
    for file_path in main_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'if __name__ == "__main__"' in content:
                    entry_points.append(str(file_path))
        except:
            pass
    
    return dependencies, entry_points, main_files, test_files, file_to_module

def find_used_files(dependencies: Dict[str, Set[str]], entry_points: List[str]) -> Set[str]:
    """Find all files that are used starting from entry points"""
    used = set()
    to_check = set(entry_points)
    
    while to_check:
        current = to_check.pop()
        if current in used:
            continue
        used.add(current)
        
        # Add all files this one imports
        for imported in dependencies.get(current, set()):
            # Try to find the actual file
            possible_files = [
                f"{imported}.py",
                f"{imported}/__init__.py",
                f"{imported.replace('.', '/')}.py",
                f"{imported.replace('.', '/')}/__init__.py"
            ]
            
            for possible in possible_files:
                if os.path.exists(possible):
                    to_check.add(possible)
                    break
    
    return used

def main():
    dependencies, entry_points, main_files, test_files, file_to_module = analyze_dependencies()
    
    print("=== DEPENDENCY ANALYSIS ===\n")
    
    print("📍 ENTRY POINTS:")
    for ep in entry_points:
        print(f"  • {ep}")
    print()
    
    print("📊 FILE CATEGORIES:")
    print(f"  • Main files: {len(main_files)}")
    print(f"  • Test files: {len(test_files)}")
    print()
    
    # Find potentially unused files
    used_files = find_used_files(dependencies, entry_points)
    all_main_files = set(str(f) for f in main_files)
    potentially_unused = all_main_files - used_files
    
    print("🔍 POTENTIALLY UNUSED FILES:")
    for unused in sorted(potentially_unused):
        print(f"  • {unused}")
    print()
    
    # Find files that import each other (potential duplicates)
    print("🔄 FILES WITH CROSS-DEPENDENCIES:")
    for file_path, imports in dependencies.items():
        for imported in imports:
            # Check if the imported module also imports this file
            imported_file = None
            for other_file, other_imports in dependencies.items():
                if file_to_module.get(file_path, '').replace('.', '/') in str(other_file) or file_path.replace('.py', '').replace('/', '.') in other_imports:
                    if imported in str(other_file) or imported.replace('.', '/') in other_file:
                        print(f"  • {file_path} ↔ {other_file}")
    print()
    
    # Show what imports what
    print("📋 IMPORT DEPENDENCIES:")
    for file_path in sorted(entry_points):
        print(f"\n🚀 {file_path}:")
        for imported in sorted(dependencies.get(file_path, set())):
            print(f"    → {imported}")

if __name__ == "__main__":
    main()
