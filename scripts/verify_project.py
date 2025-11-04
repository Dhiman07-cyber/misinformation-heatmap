#!/usr/bin/env python3
"""
Project verification script to check if everything is ready for git push and deployment
"""

import os
import sys
import subprocess
from pathlib import Path

def check_file_exists(file_path, description):
    """Check if a file exists"""
    if os.path.exists(file_path):
        print(f"✅ {description}: {file_path}")
        return True
    else:
        print(f"❌ {description}: {file_path} - NOT FOUND")
        return False

def check_directory_exists(dir_path, description):
    """Check if a directory exists"""
    if os.path.isdir(dir_path):
        print(f"✅ {description}: {dir_path}")
        return True
    else:
        print(f"❌ {description}: {dir_path} - NOT FOUND")
        return False

def check_python_syntax(file_path):
    """Check Python file syntax"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            compile(f.read(), file_path, 'exec')
        return True
    except SyntaxError as e:
        print(f"❌ Syntax error in {file_path}: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Warning in {file_path}: {e}")
        return True

def main():
    """Main verification function"""
    print("🔍 Enhanced Fake News Detection System - Project Verification")
    print("=" * 70)
    
    all_checks_passed = True
    
    # Check core project structure
    print("\n📁 Project Structure:")
    structure_checks = [
        ("backend/", "Backend directory"),
        ("frontend/", "Frontend directory"),
        ("docs/", "Documentation directory"),
        ("map/", "Map assets directory"),
        ("data/", "Data directory"),
        ("tests/", "Tests directory"),
        ("scripts/", "Scripts directory"),
    ]
    
    for path, desc in structure_checks:
        if not check_directory_exists(path, desc):
            all_checks_passed = False
    
    # Check essential files
    print("\n📄 Essential Files:")
    file_checks = [
        ("README.md", "Main README"),
        ("requirements.txt", "Main requirements"),
        ("Dockerfile", "Docker configuration"),
        ("docker-compose.yml", "Docker Compose dev"),
        ("docker-compose.prod.yml", "Docker Compose prod"),
        (".gitignore", "Git ignore file"),
        ("backend/main_application.py", "Main backend application"),
        ("backend/requirements.txt", "Backend requirements"),
        ("docs/README.md", "Documentation index"),
    ]
    
    for path, desc in file_checks:
        if not check_file_exists(path, desc):
            all_checks_passed = False
    
    # Check Python syntax in key files
    print("\n🐍 Python Syntax Check:")
    python_files = [
        "backend/main_application.py",
        "backend/enhanced_fake_news_detector.py",
        "backend/advanced_ml_classifier.py",
        "backend/api.py",
    ]
    
    for py_file in python_files:
        if os.path.exists(py_file):
            if check_python_syntax(py_file):
                print(f"✅ Syntax OK: {py_file}")
            else:
                all_checks_passed = False
        else:
            print(f"⚠️  File not found: {py_file}")
    
    # Check documentation completeness
    print("\n📚 Documentation Check:")
    doc_files = [
        "docs/BACKEND_ARCHITECTURE.md",
        "docs/ML_MODEL_DOCUMENTATION.md",
        "docs/PROJECT_STRUCTURE.md",
        "docs/SYSTEM_OVERVIEW.md",
    ]
    
    for doc_file in doc_files:
        if not check_file_exists(doc_file, f"Documentation: {doc_file}"):
            all_checks_passed = False
    
    # Check for cleaned up files (should not exist)
    print("\n🧹 Cleanup Verification:")
    should_not_exist = [
        "backend/main_ibmcloud.py",
        "backend/watson_client.py",
        "backend/pubsub_emulator.py",
        "cloud/",
        "demo_api_test.py",
        "test_system_working.py",
        "debug_map.html",
    ]
    
    cleanup_ok = True
    for path in should_not_exist:
        if os.path.exists(path):
            print(f"❌ Should be removed: {path}")
            cleanup_ok = False
    
    if cleanup_ok:
        print("✅ All unnecessary files have been cleaned up")
    else:
        all_checks_passed = False
    
    # Check git status
    print("\n📦 Git Status:")
    try:
        result = subprocess.run(['git', 'status', '--porcelain'], 
                              capture_output=True, text=True, check=True)
        if result.stdout.strip():
            print("📝 Uncommitted changes found:")
            print(result.stdout)
        else:
            print("✅ Working directory is clean")
    except subprocess.CalledProcessError:
        print("⚠️  Could not check git status")
    except FileNotFoundError:
        print("⚠️  Git not found")
    
    # Final result
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("🎉 PROJECT VERIFICATION PASSED!")
        print("✅ Project is ready for git push and deployment")
        return 0
    else:
        print("❌ PROJECT VERIFICATION FAILED!")
        print("🔧 Please fix the issues above before proceeding")
        return 1

if __name__ == "__main__":
    sys.exit(main())