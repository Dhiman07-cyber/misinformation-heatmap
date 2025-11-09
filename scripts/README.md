# 🛠️ Scripts Usage Guide

This folder contains useful development, testing, and deployment scripts for the Enhanced Fake News Detection System.

## 📋 **Available Scripts**

### 🔍 **Verification & Testing**

#### `verify_project.py`
**Purpose**: Comprehensive project verification before deployment
```bash
python scripts/verify_project.py
```
**What it checks**:
- ✅ Project structure completeness
- ✅ Python syntax validation
- ✅ Documentation completeness
- ✅ Docker configuration
- ✅ Git repository status

#### `final_verification.py`
**Purpose**: Final deployment readiness check with Docker testing
```bash
python scripts/final_verification.py
```
**What it checks**:
- ✅ All project verification checks
- ✅ Docker build testing
- ✅ Docker Compose validation
- ✅ System requirements
- ✅ Deployment summary

#### `health_check.py`
**Purpose**: Application health monitoring and status checks
```bash
python scripts/health_check.py
# Or with custom URL
python scripts/health_check.py --url http://localhost:8080
```
**What it monitors**:
- ✅ API endpoint health
- ✅ Database connectivity
- ✅ Service response times
- ✅ System resource usage

#### `performance_benchmark.py`
**Purpose**: Performance testing and benchmarking
```bash
python scripts/performance_benchmark.py
```
**What it tests**:
- ✅ API response times
- ✅ Throughput testing
- ✅ Memory usage analysis
- ✅ Concurrent request handling

#### `validate_environment.py`
**Purpose**: Environment setup validation
```bash
python scripts/validate_environment.py
```
**What it validates**:
- ✅ Python dependencies
- ✅ Environment variables
- ✅ System requirements
- ✅ Configuration files

---

### 🐳 **Docker Management**

#### `docker-dev.sh`
**Purpose**: Docker development environment management
```bash
# Make executable (Linux/Mac)
chmod +x scripts/docker-dev.sh

# Start development environment
./scripts/docker-dev.sh start

# Stop development environment
./scripts/docker-dev.sh stop

# Rebuild and restart
./scripts/docker-dev.sh restart

# View logs
./scripts/docker-dev.sh logs

# Clean up
./scripts/docker-dev.sh clean
```

#### `docker-prod.sh`
**Purpose**: Docker production environment management
```bash
# Make executable (Linux/Mac)
chmod +x scripts/docker-prod.sh

# Deploy to production
./scripts/docker-prod.sh deploy

# Stop production
./scripts/docker-prod.sh stop

# Update production
./scripts/docker-prod.sh update

# View production logs
./scripts/docker-prod.sh logs
```

---

### 🚀 **Local Development**

#### `run_local.sh` (Linux/Mac)
**Purpose**: Local development environment setup
```bash
# Make executable
chmod +x scripts/run_local.sh

# Start local development
./scripts/run_local.sh

# Start with specific mode
./scripts/run_local.sh --mode development

# Skip dependency installation
./scripts/run_local.sh --skip-deps

# Run in background
./scripts/run_local.sh --detached
```

#### `run_local.ps1` (Windows)
**Purpose**: Windows local development setup
```powershell
# Run in PowerShell
.\scripts\run_local.ps1

# With parameters
.\scripts\run_local.ps1 -Mode development -SkipDeps
```

#### `run_tests.sh`
**Purpose**: Test execution and validation
```bash
# Make executable
chmod +x scripts/run_tests.sh

# Run all tests
./scripts/run_tests.sh

# Run specific test suite
./scripts/run_tests.sh --suite unit
./scripts/run_tests.sh --suite integration
./scripts/run_tests.sh --suite e2e

# Run with coverage
./scripts/run_tests.sh --coverage

# Run in verbose mode
./scripts/run_tests.sh --verbose
```

---

## 🎯 **Common Workflows**

### **1. New Developer Setup**
```bash
# 1. Verify project setup
python scripts/verify_project.py

# 2. Validate environment
python scripts/validate_environment.py

# 3. Start local development
./scripts/run_local.sh

# 4. Run tests to ensure everything works
./scripts/run_tests.sh
```

### **2. Before Deployment**
```bash
# 1. Run comprehensive verification
python scripts/final_verification.py

# 2. Performance benchmark
python scripts/performance_benchmark.py

# 3. Deploy with Docker
./scripts/docker-prod.sh deploy
```

### **3. Health Monitoring**
```bash
# Check application health
python scripts/health_check.py

# Continuous monitoring (every 30 seconds)
watch -n 30 python scripts/health_check.py
```

### **4. Development Workflow**
```bash
# Start development environment
./scripts/docker-dev.sh start

# Make changes to code...

# Run tests
./scripts/run_tests.sh

# Restart with changes
./scripts/docker-dev.sh restart

# Check health
python scripts/health_check.py
```

---

## 🔧 **Script Requirements**

### **Python Scripts**
- Python 3.8+
- Dependencies from `requirements.txt`
- Some scripts may need additional packages (specified in script headers)

### **Shell Scripts**
- **Linux/Mac**: Bash shell
- **Windows**: PowerShell 5.0+
- Docker and Docker Compose installed
- Git (for some verification scripts)

---

## 📊 **Script Output Examples**

### **Verification Success**
```
🔍 Enhanced Fake News Detection System - Project Verification
======================================================================
✅ PASS     Project Structure
✅ PASS     Python Dependencies  
✅ PASS     Documentation
✅ PASS     Docker Availability
✅ PASS     Docker Build
✅ PASS     Docker Compose
✅ PASS     Git Status

Score: 7/7 checks passed
🎉 ALL CHECKS PASSED!
```

### **Health Check Success**
```
🏥 Application Health Check
======================================================================
✅ API Health: HEALTHY (200ms)
✅ Database: CONNECTED
✅ Memory Usage: 45% (2.1GB/4.0GB)
✅ CPU Usage: 12%
✅ Disk Space: 78% available

Overall Status: HEALTHY 🟢
```

---

## 🚨 **Troubleshooting**

### **Permission Issues (Linux/Mac)**
```bash
# Make scripts executable
chmod +x scripts/*.sh
```

### **PowerShell Execution Policy (Windows)**
```powershell
# Allow script execution
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Docker Issues**
```bash
# Ensure Docker is running
docker --version
docker-compose --version

# Check Docker daemon
docker ps
```

---

## 📝 **Adding New Scripts**

When adding new scripts to this folder:

1. **Follow naming convention**: `action_description.py` or `action_description.sh`
2. **Add documentation**: Include usage instructions in script header
3. **Update this README**: Add the new script to the appropriate section
4. **Make executable**: `chmod +x scripts/new_script.sh`
5. **Test thoroughly**: Ensure script works in different environments

---

**🛠️ These scripts help streamline development, testing, and deployment workflows for the Enhanced Fake News Detection System.**