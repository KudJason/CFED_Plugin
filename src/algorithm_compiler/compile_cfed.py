#!/usr/bin/env python3
"""
Script to compile algorithms with CFED protection
"""
import subprocess
import os
import sys
import argparse
import glob
import time
import shutil

def print_separator(title=""):
    """Print a separator with optional title"""
    width = 80
    if title:
        print("\n" + "=" * 10 + f" {title} " + "=" * (width - len(title) - 12) + "\n")
    else:
        print("\n" + "=" * width + "\n")

def inspect_file(file_path, function_name):
    """Inspect a C++ file to verify function exists"""
    if not os.path.exists(file_path):
        print(f"ERROR: File {file_path} does not exist")
        return False
    
    print(f"Inspecting file: {file_path}")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            
            # Simple heuristic to find function definition
            for i, line in enumerate(lines):
                if function_name in line and '(' in line and ')' in line and '{' in line:
                    print(f"Found potential function definition at line {i+1}:")
                    print(f"  {line}")
                    return True
                elif function_name in line and '(' in line and ')' in line:
                    next_line = lines[i+1] if i+1 < len(lines) else ""
                    if '{' in next_line:
                        print(f"Found potential function definition at lines {i+1}-{i+2}:")
                        print(f"  {line}")
                        print(f"  {next_line}")
                        return True
            
            print(f"WARNING: Could not find function '{function_name}' in file")
            return False
    except Exception as e:
        print(f"ERROR reading file: {e}")
        return False

def check_environment():
    """Check if required tools and files exist"""
    print_separator("Environment Check")
    
    # Check makefile
    makefile_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "makefile")
    if os.path.exists(makefile_path):
        print(f"✓ Makefile found: {makefile_path}")
    else:
        print(f"✗ ERROR: Makefile not found at {makefile_path}")
        return False
    
    # Check if plugin commands exists
    plugin_commands_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plugin_commands.mak")
    if os.path.exists(plugin_commands_path):
        print(f"✓ Plugin commands file found: {plugin_commands_path}")
    else:
        print(f"✗ ERROR: Plugin commands file not found at {plugin_commands_path}")
        return False
    
    # Check CFED plugin path
    cfed_plugin_path = "/workspace/cfed_basic/cfed_plugin"
    if os.path.exists(cfed_plugin_path):
        print(f"✓ CFED plugin path exists: {cfed_plugin_path}")
        # Check for plugin file
        plugin_file = os.path.join(cfed_plugin_path, "CFED_plugin64.so")
        if os.path.exists(plugin_file):
            print(f"✓ CFED plugin found: {plugin_file}")
        else:
            print(f"✗ WARNING: CFED plugin file not found at {plugin_file}")
            # Try to find it
            plugin_files = glob.glob(os.path.join(cfed_plugin_path, "*.so"))
            if plugin_files:
                print(f"  Found these plugin files instead:")
                for pf in plugin_files:
                    print(f"  - {pf}")
    else:
        print(f"✗ ERROR: CFED plugin path does not exist: {cfed_plugin_path}")
        return False
    
    return True

def compile_with_cfed(algorithm_path, function_name, project_name, technique="CFCSS", technique_type="SigMon", selective_level=0, verbose=True):
    """
    Compiles the given algorithm with CFED protection using makefile
    
    Args:
        algorithm_path: Path to the algorithm source file
        function_name: Name of the function to protect
        project_name: Base name for the project (without extension)
        verbose: Enable verbose output
    """
    # Get current working directory for makefile
    makefile_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Extract just the base name without extension
    if project_name:
        project_base = os.path.splitext(os.path.basename(project_name))[0]
    else:
        if algorithm_path:
            project_base = os.path.splitext(os.path.basename(algorithm_path))[0]
        else:
            project_base = "project"
    
    print_separator("Compilation Configuration")
    print(f"Starting compilation with CFED protection:")
    print(f"  Algorithm Path: {algorithm_path}")
    print(f"  Function Name: {function_name}")
    print(f"  Project Name: {project_base}")
    print(f"  Working Directory: {makefile_dir}")
    
    # Check environment first
    if not check_environment():
        return False
    
    # Verify source file exists and contains the function
    if not inspect_file(algorithm_path, function_name):
        print(f"WARNING: Function inspection failed. Continuing anyway...")
    
    try:
        # Run make clean first to remove BUILD directory
        print_separator("Cleaning Previous Build")
        clean_cmd = ['make', '-C', makefile_dir, 'clean']
        subprocess.run(clean_cmd, check=False, capture_output=True, text=True)
        
        # Make temporary copy of makefiles to inspect
        print("Creating backup copies of makefiles for inspection...")
        makefile_backup = os.path.join(makefile_dir, "makefile.bak")
        plugin_commands_backup = os.path.join(makefile_dir, "plugin_commands.mak.bak")
        shutil.copy(os.path.join(makefile_dir, "makefile"), makefile_backup)
        shutil.copy(os.path.join(makefile_dir, "plugin_commands.mak"), plugin_commands_backup)
        
        # Build common parameters for make
        common_params = [
            'CFED=1',  # Enable CFED compilation
            f'ALGORITHM_PATH={algorithm_path}',
            f'FUNCTION={function_name}', 
            'CROSS=SIJIE',  # Use SIJIE cross compiler
            f'PROJECT={project_base}',
            f'TECHNIQUE={technique}',  
            f'TECHNIQUE_TYPE={technique_type}', 
            f'SELECTIVE_LEVEL={selective_level}',  
        ]
        
        # Now run the actual compilation
        print_separator("Running Compilation")
        
        # First create the BUILD directory
        make_dir_cmd = ['make', '-C', makefile_dir] + common_params + ['-p', '$(OBJDIR)']
        subprocess.run(make_dir_cmd, check=False, capture_output=True, text=True)
        
        # Now explicitly compile each step
        compile_cmds = [
            # First compile the main object
            ['make', '-C', makefile_dir] + common_params + [f'{project_base}.o'],
            # Then compile other necessary files
            ['make', '-C', makefile_dir] + common_params + ['DETECTOR_compare.o', 'system_LPC17xx.o', 'startup_LPC17xx.o'],
            # Then link to create the output ELF
            ['make', '-C', makefile_dir] + common_params + [f'{project_base}.elf'],
            # Final step to create disassembly
            ['make', '-C', makefile_dir] + common_params + [f'{project_base}.disasm']
        ]
        
        print("Running compilation steps:")
        success = True
        for i, cmd in enumerate(compile_cmds):
            print(f"\nStep {i+1}: {' '.join(cmd)}")
            if verbose:
                # Run with output shown in real-time
                result = subprocess.run(cmd, check=False)
                step_success = result.returncode == 0
            else:
                # Capture output and display afterward
                result = subprocess.run(cmd, check=False, capture_output=True, text=True)
                step_success = result.returncode == 0
                print(f"Output: {result.stdout[:200]}...")
                
                if not step_success:
                    print(f"Error: {result.stderr}")
            
            success = success and step_success
            if not step_success:
                print(f"Step {i+1} failed! Continuing anyway...")
        
        if success:
            print_separator("Build Successful")
            print("Compile_with_CFED : Compilation successful!")
            
            # Check if output files were generated in BUILD directory
            build_dir = os.path.join(makefile_dir, 'BUILD')
            
            print_separator("Verifying Output Files")
            
            # Check each expected output file
            output_files = {
                'ELF': os.path.join(build_dir, f'{project_base}.elf'),
                'BIN': os.path.join(build_dir, f'{project_base}.bin'),
                'DISASM': os.path.join(build_dir, f'{project_base}.disasm')
            }
            
            # Check for plugin output directory
            plugin_dir = os.path.join(build_dir, 'GCC_Plugin_Output')
            
            missing_files = []
            for file_type, file_path in output_files.items():
                if os.path.exists(file_path):
                    print(f"✓ {file_type} file found: {os.path.basename(file_path)}")
                else:
                    print(f"✗ {file_type} file NOT found: {os.path.basename(file_path)}")
                    missing_files.append(file_path)
            
            if missing_files:
                print("\nWARNING: Some output files are missing!")
                for file in missing_files:
                    print(f"  - {file}")
                print("\nAvailable files in BUILD directory:")
                if os.path.exists(build_dir):
                    files = os.listdir(build_dir)
                    if files:
                        for f in files:
                            print(f"  - {f}")
                    else:
                        print("  (empty directory)")
                else:
                    print("  (directory does not exist)")
                success = False
            
            # Check for plugin output
            if not os.path.exists(plugin_dir):
                print("\n✗ WARNING: Plugin output directory does not exist!")
                success = False
            else:
                # Only check if the directory contains any files or directories
                if not any(os.scandir(plugin_dir)):
                    print("\n✗ WARNING: Plugin output directory is empty")
                    success = False
                else:
                    print("\n✓ Plugin output directory contains files or directories")
                    success = True
            
            # Clean up backup files
            try:
                os.remove(makefile_backup)
                os.remove(plugin_commands_backup)
            except Exception as e:
                print(f"Warning: Could not remove backup files: {e}")
            
            if not success:
                print_separator("Build Failed")
                print("Compile_with_CFED : Compilation failed - missing output files or plugin output!")
            
            return success
            
        else:
            print_separator("Build Failed")
            print("Compile_with_CFED : Compilation failed!")
            
            # Debug output
            print("\nDumping makefile contents for debugging...")
            try:
                with open(makefile_backup, 'r') as f:
                    print("\n--- makefile ---")
                    print(f.read()[:500] + "... (truncated)")
                    
                with open(plugin_commands_backup, 'r') as f:
                    print("\n--- plugin_commands.mak ---")
                    print(f.read())
            except Exception as e:
                print(f"Error reading backup files: {e}")
            
            # Clean up backup files
            try:
                os.remove(makefile_backup)
                os.remove(plugin_commands_backup)
            except Exception as e:
                print(f"Warning: Could not remove backup files: {e}")
            
            return False
        
    except Exception as e:
        print(f"ERROR during compilation: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Compile algorithms with CFED protection')
    parser.add_argument('algorithm_path', help='Path to the algorithm source file')
    parser.add_argument('function_name', help='Name of the function to protect')
    parser.add_argument('--project-name', help='Project name (defaults to algorithm filename)')
    # parser.add_argument('--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    success = compile_with_cfed(
        args.algorithm_path,
        args.function_name,
        args.project_name,
        args.verbose
    )
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main() 