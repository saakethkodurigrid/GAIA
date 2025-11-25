"""
Validation script for code executor service

This script validates that the service is properly configured and working,
checks all dependencies, and generates a comprehensive report.
"""
import sys
import os
import json
from pathlib import Path
from datetime import datetime
import subprocess

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ServiceValidator:
    """Validates the code executor service"""
    
    def __init__(self):
        self.validation_results = []
        self.warnings = []
        self.errors = []
    
    def add_result(self, category: str, test: str, passed: bool, message: str = ""):
        """Add a validation result"""
        result = {
            "category": category,
            "test": test,
            "passed": passed,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
        self.validation_results.append(result)
        
        if not passed:
            self.errors.append(f"{category} - {test}: {message}")
    
    def add_warning(self, message: str):
        """Add a warning"""
        self.warnings.append(message)
    
    def print_section(self, title: str):
        """Print section header"""
        print(f"\n{'='*70}")
        print(f"  {title}")
        print('='*70)
    
    def print_test(self, test_name: str, passed: bool, message: str = ""):
        """Print test result"""
        status = "✓" if passed else "✗"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        print(f"{color}{status}{reset} {test_name}")
        if message:
            print(f"  └─ {message}")
    
    def validate_python_environment(self):
        """Validate Python environment"""
        self.print_section("Python Environment")
        
        # Check Python version
        version = sys.version_info
        passed = version.major == 3 and version.minor >= 8
        self.add_result(
            "Python",
            "Version Check",
            passed,
            f"Python {version.major}.{version.minor}.{version.micro}"
        )
        self.print_test(
            f"Python version {version.major}.{version.minor}.{version.micro}",
            passed,
            "Requires Python 3.8+"
        )
        
        # Check required packages
        required_packages = ["docker"]
        for package in required_packages:
            try:
                __import__(package)
                self.add_result("Python", f"Package: {package}", True, "Installed")
                self.print_test(f"Package '{package}' installed", True)
            except ImportError:
                self.add_result("Python", f"Package: {package}", False, "Not installed")
                self.print_test(f"Package '{package}' installed", False, "Run: pip install docker")
    
    def validate_docker(self):
        """Validate Docker installation and connectivity"""
        self.print_section("Docker Environment")
        
        # Check Docker installation
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            docker_installed = result.returncode == 0
            docker_version = result.stdout.strip()
            self.add_result("Docker", "Installation", docker_installed, docker_version)
            self.print_test("Docker installed", docker_installed, docker_version)
        except Exception as e:
            self.add_result("Docker", "Installation", False, str(e))
            self.print_test("Docker installed", False, "Docker not found")
            return
        
        # Check Docker daemon
        try:
            result = subprocess.run(
                ["docker", "ps"],
                capture_output=True,
                text=True,
                timeout=5
            )
            daemon_running = result.returncode == 0
            self.add_result("Docker", "Daemon Running", daemon_running)
            self.print_test("Docker daemon running", daemon_running)
        except Exception as e:
            self.add_result("Docker", "Daemon Running", False, str(e))
            self.print_test("Docker daemon running", False, "Start Docker daemon")
        
        # Check Docker images
        from services.code_executor.config import ExecutorConfig
        
        for lang, image in ExecutorConfig.DOCKER_IMAGES.items():
            try:
                result = subprocess.run(
                    ["docker", "images", "-q", image],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                image_exists = bool(result.stdout.strip())
                self.add_result("Docker", f"Image: {image}", image_exists)
                self.print_test(
                    f"Image '{image}' available",
                    image_exists,
                    f"Pull with: docker pull {image}" if not image_exists else ""
                )
                
                if not image_exists:
                    self.add_warning(f"Docker image '{image}' not found. It will be pulled automatically.")
            except Exception as e:
                self.add_result("Docker", f"Image: {image}", False, str(e))
                self.print_test(f"Image '{image}' check", False, str(e))
    
    def validate_file_structure(self):
        """Validate file structure"""
        self.print_section("File Structure")
        
        base_dir = Path(__file__).parent
        required_files = [
            "__init__.py",
            "models.py",
            "config.py",
            "executor.py",
            "test_executor.py",
            "validate_service.py",
            "README.md"
        ]
        
        for file in required_files:
            file_path = base_dir / file
            exists = file_path.exists()
            self.add_result("Files", file, exists)
            self.print_test(f"File '{file}' exists", exists)
        
        # Check output directory
        output_dir = base_dir / "outputs"
        if not output_dir.exists():
            output_dir.mkdir(exist_ok=True)
            self.print_test("Output directory created", True)
        else:
            self.print_test("Output directory exists", True)
    
    def validate_service_functionality(self):
        """Validate service can execute code"""
        self.print_section("Service Functionality")
        
        try:
            from services.code_executor import CodeExecutor, ExecutionRequest, Language
            
            # Initialize executor
            try:
                executor = CodeExecutor()
                self.add_result("Service", "Initialization", True)
                self.print_test("CodeExecutor initialized", True)
            except Exception as e:
                self.add_result("Service", "Initialization", False, str(e))
                self.print_test("CodeExecutor initialized", False, str(e))
                return
            
            # Test Python execution
            try:
                request = ExecutionRequest(
                    code='print("Hello from validator!")',
                    language=Language.PYTHON,
                    timeout=10
                )
                result = executor.execute(request)
                success = result.status.value in ["success", "failed"]
                self.add_result("Service", "Python Execution", success, result.status.value)
                self.print_test(
                    "Python code execution",
                    success,
                    f"Status: {result.status.value}, Time: {result.metrics.total_execution_time_ms:.2f}ms"
                )
            except Exception as e:
                self.add_result("Service", "Python Execution", False, str(e))
                self.print_test("Python code execution", False, str(e))
            
        except Exception as e:
            self.add_result("Service", "Import", False, str(e))
            self.print_test("Service import", False, str(e))
    
    def check_system_resources(self):
        """Check system resources"""
        self.print_section("System Resources")
        
        try:
            import psutil
            
            # CPU
            cpu_count = psutil.cpu_count()
            self.print_test(f"CPU cores: {cpu_count}", True)
            
            # Memory
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            memory_available_gb = memory.available / (1024**3)
            self.print_test(
                f"Memory: {memory_gb:.1f}GB total, {memory_available_gb:.1f}GB available",
                True
            )
            
            if memory_available_gb < 1:
                self.add_warning("Low available memory. Recommended: 2GB+")
            
            # Disk
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / (1024**3)
            self.print_test(f"Disk space: {disk_free_gb:.1f}GB free", True)
            
            if disk_free_gb < 5:
                self.add_warning("Low disk space. Recommended: 10GB+ free")
                
        except ImportError:
            self.add_warning("psutil not installed. Install with: pip install psutil")
            self.print_test("System resource check", False, "psutil not available")
    
    def generate_report(self):
        """Generate validation report"""
        self.print_section("Validation Summary")
        
        total_tests = len(self.validation_results)
        passed_tests = sum(1 for r in self.validation_results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✓")
        print(f"Failed: {failed_tests} ✗")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")
        
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")
        
        # Save report to file
        report_dir = Path(__file__).parent / "outputs"
        report_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = report_dir / f"validation_report_{timestamp}.json"
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total_tests": total_tests,
                "passed": passed_tests,
                "failed": failed_tests,
                "warnings": len(self.warnings),
                "errors": len(self.errors)
            },
            "results": self.validation_results,
            "warnings": self.warnings,
            "errors": self.errors
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\n📄 Full report saved to: {report_file}")
        
        # Overall status
        print("\n" + "="*70)
        if failed_tests == 0:
            print("✅ SERVICE VALIDATION PASSED")
            print("\nThe code executor service is properly configured and ready to use!")
        else:
            print("⚠️  SERVICE VALIDATION FAILED")
            print(f"\n{failed_tests} test(s) failed. Please fix the errors above.")
        print("="*70 + "\n")
        
        return failed_tests == 0
    
    def run_all_validations(self):
        """Run all validation checks"""
        print("\n" + "="*70)
        print("  CODE EXECUTOR SERVICE VALIDATION")
        print("="*70)
        print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.validate_python_environment()
        self.validate_docker()
        self.validate_file_structure()
        self.check_system_resources()
        self.validate_service_functionality()
        
        return self.generate_report()


def main():
    """Main function"""
    validator = ServiceValidator()
    success = validator.run_all_validations()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()



