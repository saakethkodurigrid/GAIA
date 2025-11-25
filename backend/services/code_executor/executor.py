"""
Main code executor implementation
"""
import docker
import time
import uuid
import os
import json
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from .models import (
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    ExecutionMetrics,
    TestResult,
    Language
)
from .config import ExecutorConfig


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    Secure code executor using Docker containers
    """
    
    def __init__(self):
        """Initialize the executor"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise Exception(
                "Docker is not available. Please ensure Docker is installed and running."
            )
        
        ExecutorConfig.ensure_output_dir()
        self._pull_required_images()
    
    def _pull_required_images(self):
        """Pull required Docker images if not present"""
        for lang, image in ExecutorConfig.DOCKER_IMAGES.items():
            try:
                self.docker_client.images.get(image)
                logger.info(f"Docker image '{image}' already available")
            except docker.errors.ImageNotFound:
                logger.info(f"Pulling Docker image '{image}'...")
                try:
                    self.docker_client.images.pull(image)
                    logger.info(f"Successfully pulled '{image}'")
                except Exception as e:
                    logger.warning(f"Failed to pull '{image}': {e}")
    
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """
        Execute code with the given request
        
        Args:
            request: ExecutionRequest containing code and parameters
            
        Returns:
            ExecutionResult with execution details
        """
        execution_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        
        logger.info(f"[{execution_id}] Starting execution for {request.language.value}")
        
        try:
            # Get language configuration
            lang_config = ExecutorConfig.get_language_config(request.language.value)
            if not lang_config:
                raise ValueError(f"Unsupported language: {request.language.value}")
            
            # Prepare code file
            code_file = self._prepare_code_file(request.code, request.language, execution_id)
            
            # Compile if needed (for Java)
            compilation_output = None
            if lang_config.get("compile_command"):
                compilation_output, compile_success = self._compile_code(
                    code_file, lang_config, request, execution_id
                )
                if not compile_success:
                    return self._create_compilation_error_result(
                        compilation_output, execution_id, start_time
                    )
            
            # Execute code
            stdout, stderr, exec_time_ms, memory_mb = self._run_code(
                code_file, lang_config, request, execution_id
            )
            
            # Run test cases
            test_results = self._run_test_cases(
                code_file, lang_config, request, execution_id
            )
            
            # Calculate metrics
            total_time = (time.time() - start_time) * 1000
            metrics = ExecutionMetrics(
                total_execution_time_ms=total_time,
                memory_used_mb=memory_mb,
                cpu_time_ms=exec_time_ms,
                container_startup_time_ms=max(0, total_time - exec_time_ms),
                code_execution_time_ms=exec_time_ms
            )
            
            # Determine status
            status = ExecutionStatus.SUCCESS if not stderr else ExecutionStatus.FAILED
            if test_results and not all(tr.passed for tr in test_results):
                status = ExecutionStatus.FAILED
            
            # Create result
            result = ExecutionResult(
                status=status,
                stdout=stdout,
                stderr=stderr,
                test_results=test_results,
                metrics=metrics,
                compilation_output=compilation_output,
                execution_id=execution_id
            )
            
            # Save output
            self._save_execution_output(result, request, execution_id)
            
            logger.info(
                f"[{execution_id}] Execution completed: {status.value} "
                f"({metrics.total_execution_time_ms:.2f}ms)"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[{execution_id}] Execution failed: {e}", exc_info=True)
            return self._create_error_result(str(e), execution_id, start_time)
        
        finally:
            # Cleanup
            self._cleanup(execution_id)
    
    def _prepare_code_file(
        self, code: str, language: Language, execution_id: str
    ) -> Path:
        """Prepare code file for execution"""
        lang_config = ExecutorConfig.get_language_config(language.value)
        
        # Create temp directory
        temp_dir = Path(f"/tmp/code_exec_{execution_id}")
        temp_dir.mkdir(exist_ok=True)
        
        # Determine filename
        if language == Language.JAVA:
            filename = f"Main{lang_config['file_extension']}"
        else:
            filename = f"main{lang_config['file_extension']}"
        
        code_file = temp_dir / filename
        code_file.write_text(code)
        
        logger.info(f"[{execution_id}] Code file prepared: {code_file}")
        return code_file
    
    def _compile_code(
        self, code_file: Path, lang_config: dict, request: ExecutionRequest, execution_id: str
    ) -> tuple[str, bool]:
        """Compile code (for compiled languages like Java)"""
        logger.info(f"[{execution_id}] Compiling code...")
        
        try:
            container = self.docker_client.containers.run(
                image=lang_config["docker_image"],
                command=lang_config["compile_command"],
                volumes={
                    str(code_file.parent): {"bind": "/code", "mode": "rw"}
                },
                working_dir="/code",
                mem_limit=f"{request.memory_limit}m",
                memswap_limit=f"{request.memory_limit}m",
                nano_cpus=int(ExecutorConfig.DEFAULT_CPU_LIMIT * 1e9),
                network_disabled=ExecutorConfig.ENABLE_NETWORK is False,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True
            )
            
            output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            logger.info(f"[{execution_id}] Compilation successful")
            return output, True
            
        except docker.errors.ContainerError as e:
            logger.error(f"[{execution_id}] Compilation failed: {e.stderr.decode()}")
            return e.stderr.decode('utf-8'), False
        except Exception as e:
            logger.error(f"[{execution_id}] Compilation error: {e}")
            return str(e), False
    
    def _run_code(
        self, code_file: Path, lang_config: dict, request: ExecutionRequest, execution_id: str
    ) -> tuple[str, str, float, float]:
        """Run code in Docker container"""
        logger.info(f"[{execution_id}] Executing code...")
        
        start_time = time.time()
        
        try:
            container = self.docker_client.containers.run(
                image=lang_config["docker_image"],
                command=lang_config["run_command"],
                volumes={
                    str(code_file.parent): {"bind": "/code", "mode": "ro"}
                },
                working_dir="/code",
                mem_limit=f"{request.memory_limit}m",
                memswap_limit=f"{request.memory_limit}m",
                nano_cpus=int(ExecutorConfig.DEFAULT_CPU_LIMIT * 1e9),
                network_disabled=ExecutorConfig.ENABLE_NETWORK is False,
                remove=True,
                detach=False,
                stdout=True,
                stderr=True
            )
            
            exec_time_ms = (time.time() - start_time) * 1000
            
            output = container.decode('utf-8') if isinstance(container, bytes) else str(container)
            
            logger.info(f"[{execution_id}] Code executed successfully ({exec_time_ms:.2f}ms)")
            return output, "", exec_time_ms, 0.0
            
        except docker.errors.ContainerError as e:
            exec_time_ms = (time.time() - start_time) * 1000
            stdout = e.stderr.decode('utf-8') if e.stderr else ""
            logger.error(f"[{execution_id}] Runtime error: {stdout}")
            return "", stdout, exec_time_ms, 0.0
            
        except Exception as e:
            exec_time_ms = (time.time() - start_time) * 1000
            logger.error(f"[{execution_id}] Execution error: {e}")
            return "", str(e), exec_time_ms, 0.0
    
    def _run_test_cases(
        self, code_file: Path, lang_config: dict, request: ExecutionRequest, execution_id: str
    ) -> list[TestResult]:
        """Run test cases against the code"""
        if not request.test_cases:
            return []
        
        logger.info(f"[{execution_id}] Running {len(request.test_cases)} test cases...")
        
        test_results = []
        
        for idx, test_case in enumerate(request.test_cases):
            start_time = time.time()
            
            try:
                # Create test input file
                input_file = code_file.parent / f"input_{idx}.txt"
                input_file.write_text(test_case.input)
                
                # Run with input
                container = self.docker_client.containers.run(
                    image=lang_config["docker_image"],
                    volumes={
                        str(code_file.parent): {"bind": "/code", "mode": "ro"}
                    },
                    working_dir="/code",
                    mem_limit=f"{request.memory_limit}m",
                    memswap_limit=f"{request.memory_limit}m",
                    nano_cpus=int(ExecutorConfig.DEFAULT_CPU_LIMIT * 1e9),
                    network_disabled=True,
                    remove=True,
                    detach=False,
                    stdout=True,
                    stderr=True,
                    entrypoint="/bin/sh",
                    command=["-c", f"{lang_config['run_command']} < /code/input_{idx}.txt"]
                )
                
                exec_time_ms = (time.time() - start_time) * 1000
                
                actual_output = (
                    container.decode('utf-8').strip()
                    if isinstance(container, bytes)
                    else str(container).strip()
                )
                expected_output = test_case.expected_output.strip()
                
                passed = actual_output == expected_output
                
                test_results.append(TestResult(
                    test_id=test_case.test_id or idx,
                    input=test_case.input,
                    expected_output=expected_output,
                    actual_output=actual_output,
                    passed=passed,
                    execution_time_ms=exec_time_ms
                ))
                
                logger.info(
                    f"[{execution_id}] Test {idx + 1}: "
                    f"{'PASSED' if passed else 'FAILED'} ({exec_time_ms:.2f}ms)"
                )
                
            except Exception as e:
                logger.error(f"[{execution_id}] Test {idx + 1} error: {e}")
                test_results.append(TestResult(
                    test_id=test_case.test_id or idx,
                    input=test_case.input,
                    expected_output=test_case.expected_output,
                    actual_output="",
                    passed=False,
                    error=str(e),
                    execution_time_ms=(time.time() - start_time) * 1000
                ))
        
        passed_count = sum(1 for tr in test_results if tr.passed)
        logger.info(
            f"[{execution_id}] Test results: {passed_count}/{len(test_results)} passed"
        )
        
        return test_results
    
    def _create_compilation_error_result(
        self, compilation_output: str, execution_id: str, start_time: float
    ) -> ExecutionResult:
        """Create result for compilation error"""
        total_time = (time.time() - start_time) * 1000
        return ExecutionResult(
            status=ExecutionStatus.COMPILATION_ERROR,
            stdout="",
            stderr=compilation_output,
            test_results=[],
            metrics=ExecutionMetrics(
                total_execution_time_ms=total_time,
                memory_used_mb=0.0,
                cpu_time_ms=0.0,
                container_startup_time_ms=0.0,
                code_execution_time_ms=0.0
            ),
            compilation_output=compilation_output,
            error_message="Compilation failed",
            execution_id=execution_id
        )
    
    def _create_error_result(
        self, error_message: str, execution_id: str, start_time: float
    ) -> ExecutionResult:
        """Create result for general error"""
        total_time = (time.time() - start_time) * 1000
        return ExecutionResult(
            status=ExecutionStatus.ERROR,
            stdout="",
            stderr=error_message,
            test_results=[],
            metrics=ExecutionMetrics(
                total_execution_time_ms=total_time,
                memory_used_mb=0.0,
                cpu_time_ms=0.0,
                container_startup_time_ms=0.0,
                code_execution_time_ms=0.0
            ),
            error_message=error_message,
            execution_id=execution_id
        )
    
    def _save_execution_output(
        self, result: ExecutionResult, request: ExecutionRequest, execution_id: str
    ):
        """Save execution output to files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = Path(ExecutorConfig.OUTPUT_DIR) / f"execution_{timestamp}_{execution_id}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save code
        (output_dir / "code.txt").write_text(request.code)
        
        # Save stdout
        (output_dir / "output.txt").write_text(result.stdout)
        
        # Save stderr
        (output_dir / "errors.txt").write_text(result.stderr)
        
        # Save metrics and results as JSON
        (output_dir / "metrics.json").write_text(
            json.dumps(result.to_dict(), indent=2)
        )
        
        # Save logs
        log_content = f"""Execution ID: {execution_id}
Language: {request.language.value}
Status: {result.status.value}
Timestamp: {result.metrics.timestamp}

=== METRICS ===
Total Execution Time: {result.metrics.total_execution_time_ms:.2f}ms
Memory Used: {result.metrics.memory_used_mb:.2f}MB
CPU Time: {result.metrics.cpu_time_ms:.2f}ms

=== TEST RESULTS ===
Total Tests: {len(result.test_results)}
Passed: {result.tests_passed_count}
Failed: {result.tests_failed_count}

"""
        for tr in result.test_results:
            log_content += f"\nTest {tr.test_id}: {'PASSED' if tr.passed else 'FAILED'}\n"
            log_content += f"  Input: {tr.input}\n"
            log_content += f"  Expected: {tr.expected_output}\n"
            log_content += f"  Actual: {tr.actual_output}\n"
            if tr.error:
                log_content += f"  Error: {tr.error}\n"
        
        (output_dir / "logs.txt").write_text(log_content)
        
        logger.info(f"[{execution_id}] Output saved to: {output_dir}")
    
    def _cleanup(self, execution_id: str):
        """Cleanup temporary files"""
        try:
            temp_dir = Path(f"/tmp/code_exec_{execution_id}")
            if temp_dir.exists():
                import shutil
                shutil.rmtree(temp_dir)
                logger.info(f"[{execution_id}] Cleanup completed")
        except Exception as e:
            logger.warning(f"[{execution_id}] Cleanup failed: {e}")

