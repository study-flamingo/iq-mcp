#!/usr/bin/env python3
"""
Test runner script for IQ-MCP Knowledge Graph Server.

This script provides convenient ways to run the test suite with different
configurations and options.
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd: list[str], env: dict = None) -> int:
    """
    Run a command and return its exit code.
    
    Args:
        cmd: Command and arguments to run
        env: Optional environment variables
        
    Returns:
        Exit code from the command
    """
    if env:
        run_env = os.environ.copy()
        run_env.update(env)
    else:
        run_env = None
    
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, env=run_env)
    return result.returncode


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(
        description="Test runner for IQ-MCP Knowledge Graph Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     # Run all tests
  %(prog)s --unit              # Run only unit tests
  %(prog)s --integration       # Run only integration tests
  %(prog)s --crud              # Run only CRUD tests
  %(prog)s --coverage          # Run with coverage report
  %(prog)s --file test_server_tools.py  # Run specific file
  %(prog)s --debug             # Run with debug logging
  %(prog)s --fast              # Skip slow tests
        """
    )
    
    # Test selection options
    parser.add_argument(
        "--unit",
        action="store_true",
        help="Run only unit tests"
    )
    parser.add_argument(
        "--integration", 
        action="store_true",
        help="Run only integration tests"
    )
    parser.add_argument(
        "--crud",
        action="store_true", 
        help="Run only CRUD operation tests"
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests"
    )
    
    # Output options
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Run with coverage report"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true", 
        help="Quiet output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    
    # Test specification
    parser.add_argument(
        "--file", "-f",
        help="Run specific test file"
    )
    parser.add_argument(
        "--test", "-t",
        help="Run specific test (format: file::class::method)"
    )
    
    # Environment options
    parser.add_argument(
        "--memory-path",
        help="Custom memory file path for tests"
    )
    
    args = parser.parse_args()
    
    # Build pytest command using uv run for proper environment
    cmd = ["uv", "run", "python", "-m", "pytest"]
    
    # Add test selection markers
    markers = []
    if args.unit:
        markers.append("unit")
    if args.integration:
        markers.append("integration") 
    if args.crud:
        markers.append("crud")
    if args.fast:
        markers.append("not slow")
    
    if markers:
        cmd.extend(["-m", " and ".join(markers)])
    
    # Add output options
    if args.verbose:
        cmd.append("-v")
    if args.quiet:
        cmd.append("-q")
    
    # Add coverage
    if args.coverage:
        cmd.extend([
            "--cov=src/mcp_knowledge_graph",
            "--cov-report=term-missing",
            "--cov-report=html"
        ])
    
    # Add specific test file or test
    if args.test:
        cmd.append(f"tests/{args.test}")
    elif args.file:
        if not args.file.startswith("test_"):
            args.file = f"test_{args.file}"
        if not args.file.endswith(".py"):
            args.file = f"{args.file}.py"
        cmd.append(f"tests/{args.file}")
    
    # Set up environment
    env = {}
    if args.debug:
        env["IQ_DEBUG"] = "true"
    if args.memory_path:
        env["MEMORY_FILE_PATH"] = args.memory_path
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent
    os.chdir(project_root)
    
    # Check if tests directory exists
    if not (project_root / "tests").exists():
        print("Error: tests directory not found")
        return 1
    
    # Run the tests
    exit_code = run_command(cmd, env)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main())