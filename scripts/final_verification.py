#!/usr/bin/env python3
"""
Final verification script for Enhanced Fake News Detection System
Comprehensive checks before deployment
"""

import os
import sys
import subprocess
import json
import time
from pathlib import Path

def run_command(cmd, timeout=30):
    """Run a command with timeout"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, 
            text=True, timeout=timeout, check=True
        )
        return True, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", f"Command timed out after {timeout}s"
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr
    except Exception as e:
        return False, "", str(e)

def check_docker_availability():
    """Check if Docker is available and running"""
    print("🐳 Checking Docker availability...")
    
    success, stdout, stderr = run_command("docker --version")
    if not success:
        print("❌ Docker not available")
        return False
    
    print(f"✅ Docker version: {stdout.strip()}")
    
    # Check if Docker daemon is running
    success, stdout, stderr = run_command("docker ps")
    if not success:
        print("❌ Docker daemon not running")
        return False
    
    print("✅ Docker daemon is running")
    return True

def check_project_structure():
    """Verify project structure is complete"""
    print("\n📁 Checking project structure...")
    
    required_files = [
        "README.md",
        "requirements.txt", 
        "Dockerfile",
        "Dockerfile.simple",
        "docker-compose.yml",
        "docker-compose.prod.yml",
        "DEPLOYMENT_GUIDE.md",
        "backend/main_application.py",
        "backend/requirements.txt",
        "docs/README.md",
        "docs/BACKEND_ARCHITECTURE.md",
        "docs/ML_MODEL_DOCUMENTATION.md",
    ]
    
    required_dirs = [
        "backend/",
        "frontend/", 
        "docs/",
        "map/",
        "data/",
        "tests/",
        "scripts/"
    ]
    
    all_good = True
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ Missing: {file_path}")
            all_good = False
    
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            print(f"✅ {dir_path}")
        else:
            print(f"❌ Missing directory: {dir_path}")
            all_good = False
    
    return all_good

def test_docker_build():
    """Test Docker build process"""
    print("\n🔨 Testing Docker build...")
    
    # Test simple build first
    print("Building simple Docker image...")
    success, stdout, stderr = run_command(
        "docker build -f Dockerfile.simple -t fake-news-test:simple .", 
        timeout=300
    )
    
    if not success:
        print(f"❌ Simple Docker build failed: {stderr}")
        return False
    
    print("✅ Simple Docker build successful")
    
    # Clean up test image
    run_command("docker rmi fake-news-test:simple")
    
    return True

def test_docker_compose():
    """Test Docker Compose configuration"""
    print("\n🐙 Testing Docker Compose...")
    
    # Validate docker-compose.yml
    success, stdout, stderr = run_command("docker-compose config")
    if not success:
        print(f"❌ Docker Compose validation failed: {stderr}")
        return False
    
    print("✅ Docker Compose configuration valid")
    
    # Validate production compose
    success, stdout, stderr = run_command("docker-compose -f docker-compose.prod.yml config")
    if not success:
        print(f"❌ Production Docker Compose validation failed: {stderr}")
        return False
    
    print("✅ Production Docker Compose configuration valid")
    return True

def check_git_status():
    """Check git repository status"""
    print("\n📦 Checking Git status...")
    
    # Check if we're in a git repo
    success, stdout, stderr = run_command("git status --porcelain")
    if not success:
        print("⚠️  Not a git repository or git not available")
        return True  # Not critical
    
    if stdout.strip():
        print("📝 Uncommitted changes found:")
        print(stdout)
        print("💡 Consider committing changes before deployment")
    else:
        print("✅ Working directory is clean")
    
    # Check for commits
    success, stdout, stderr = run_command("git log --oneline -1")
    if success and stdout.strip():
        print(f"✅ Latest commit: {stdout.strip()}")
    
    return True

def check_python_dependencies():
    """Check if Python dependencies can be resolved"""
    print("\n🐍 Checking Python dependencies...")
    
    # Check main requirements
    if os.path.exists("requirements.txt"):
        print("✅ Main requirements.txt found")
    else:
        print("❌ Main requirements.txt missing")
        return False
    
    # Check backend requirements
    if os.path.exists("backend/requirements.txt"):
        print("✅ Backend requirements.txt found")
    else:
        print("❌ Backend requirements.txt missing")
        return False
    
    return True

def check_documentation():
    """Verify documentation completeness"""
    print("\n📚 Checking documentation...")
    
    doc_files = [
        "docs/README.md",
        "docs/BACKEND_ARCHITECTURE.md", 
        "docs/ML_MODEL_DOCUMENTATION.md",
        "docs/PROJECT_STRUCTURE.md",
        "DEPLOYMENT_GUIDE.md"
    ]
    
    all_good = True
    for doc_file in doc_files:
        if os.path.exists(doc_file):
            # Check if file has content
            with open(doc_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if len(content) > 100:  # Reasonable minimum
                    print(f"✅ {doc_file} ({len(content)} chars)")
                else:
                    print(f"⚠️  {doc_file} seems too short")
        else:
            print(f"❌ Missing: {doc_file}")
            all_good = False
    
    return all_good

def generate_deployment_summary():
    """Generate deployment summary"""
    print("\n📋 Deployment Summary:")
    print("=" * 50)
    
    # Project info
    if os.path.exists("README.md"):
        with open("README.md", 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
            print(f"Project: {first_line.replace('#', '').strip()}")
    
    # File counts
    backend_files = len([f for f in Path("backend").rglob("*.py") if f.is_file()])
    doc_files = len([f for f in Path("docs").rglob("*.md") if f.is_file()])
    
    print(f"Backend Python files: {backend_files}")
    print(f"Documentation files: {doc_files}")
    
    # Docker info
    if os.path.exists("Dockerfile"):
        print("✅ Docker support available")
    if os.path.exists("docker-compose.yml"):
        print("✅ Docker Compose support available")
    
    print("\n🚀 Deployment Options:")
    print("1. docker-compose up --build")
    print("2. docker build -f Dockerfile.simple -t fake-news .")
    print("3. pip install -r requirements.txt && cd backend && python main_application.py")
    
    print("\n🌐 Access URLs (after deployment):")
    print("- Main Dashboard: http://localhost:8080")
    print("- Interactive Map: http://localhost:8080/map/enhanced-india-heatmap.html")
    print("- API Docs: http://localhost:8080/docs")
    print("- Health Check: http://localhost:8080/health")

def main():
    """Main verification function"""
    print("🔍 Enhanced Fake News Detection System - Final Verification")
    print("=" * 70)
    
    checks = [
        ("Project Structure", check_project_structure),
        ("Python Dependencies", check_python_dependencies),
        ("Documentation", check_documentation),
        ("Docker Availability", check_docker_availability),
        ("Docker Build", test_docker_build),
        ("Docker Compose", test_docker_compose),
        ("Git Status", check_git_status),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        print(f"\n{'='*20} {check_name} {'='*20}")
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with error: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*70)
    print("📊 VERIFICATION RESULTS")
    print("="*70)
    
    passed = 0
    total = len(results)
    
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:<10} {check_name}")
        if result:
            passed += 1
    
    print(f"\nScore: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL CHECKS PASSED!")
        print("✅ Project is ready for deployment")
        generate_deployment_summary()
        return 0
    else:
        print(f"\n⚠️  {total - passed} checks failed")
        print("🔧 Please fix the issues above before deployment")
        return 1

if __name__ == "__main__":
    sys.exit(main())