#!/usr/bin/env python3

import sys
import os
import yaml
from pathlib import Path
from typing import Any, Dict, List

# --- Logging Helpers ---
def log_info(msg: str) -> None:
    print(msg)

def log_section(title: str) -> None:
    print(f"\n{title}\n{'-' * len(title)}")

def error_exit(message: str) -> None:
    """
    Print a GitHub Actions-formatted error message and exit.
    Args:
        message (str): The error message to log and print.
    """
    print(f"::error::{message}")
    print(f"❌ {message}")
    sys.exit(1)

def process_args(
    config: Dict[str, Any], env_name: str, key_name: str, arg_prefix: str
) -> List[str]:
    """
    Process a list of arguments, handling inheritance and validating types.
    Args:
        config (Dict[str, Any]): The loaded YAML configuration.
        env_name (str): The environment name.
        key_name (str): The key to process (e.g., 'plan-args').
        arg_prefix (str): Prefix to prepend to each argument.
    Returns:
        List[str]: The processed argument list.
    """
    final_args: List[str] = []
    inherit: bool = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("inherit", True)

    if inherit:
        default_items = config.get("defaults", {}).get(key_name, {}).get("args", [])
        if not isinstance(default_items, list):
            error_exit(f"Configuration Error: '.defaults.{key_name}.args' must be a list.")
        for item in default_items:
            if not isinstance(item, str):
                error_exit(f"Configuration Error: Argument '{item}' in '.defaults.{key_name}.args' must be a string.")
            final_args.append(f"{arg_prefix}{item}")

    env_items = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("args", [])
    if not isinstance(env_items, list):
        error_exit(f"Configuration Error: '.environments.{env_name}.{key_name}.args' must be a list.")
    for item in env_items:
        if not isinstance(item, str):
            error_exit(f"Configuration Error: Argument '{item}' in '.environments.{env_name}.{key_name}.args' must be a string.")
        final_args.append(f"{arg_prefix}{item}")

    return final_args

def process_paths(
    config: Dict[str, Any], env_name: str, key_name: str, arg_prefix: str, working_dir: str
) -> List[str]:
    """
    Process a list of file paths, handling inheritance and making paths relative.
    Args:
        config (Dict[str, Any]): The loaded YAML configuration.
        env_name (str): The environment name.
        key_name (str): The key to process (e.g., 'var-files').
        arg_prefix (str): Prefix to prepend to each path.
        working_dir (str): The working directory for relative paths.
    Returns:
        List[str]: The processed path list.
    """
    final_paths: List[str] = []
    inherit: bool = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("inherit", True)

    if inherit:
        default_items = config.get("defaults", {}).get(key_name, {}).get("paths", [])
        if not isinstance(default_items, list):
            error_exit(f"Configuration Error: '.defaults.{key_name}.paths' must be a list.")
        for item in default_items:
            if not isinstance(item, str):
                error_exit(f"Configuration Error: Path '{item}' in '.defaults.{key_name}.paths' must be a string.")
            p = Path(item)
            if not p.exists():
                error_exit(f"Configuration Error: Default file '{item}' specified in .terraform-branch-deploy.yml not found in repository root.")
            relative_path = os.path.relpath(p, working_dir)
            final_paths.append(f"{arg_prefix}{relative_path}")

    env_items = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("paths", [])
    if not isinstance(env_items, list):
        error_exit(f"Configuration Error: '.environments.{env_name}.{key_name}.paths' must be a list.")
    for item in env_items:
        if not isinstance(item, str):
            error_exit(f"Configuration Error: Path '{item}' in '.environments.{env_name}.{key_name}.paths' must be a string.")
        p = Path(item)
        if not p.exists():
            error_exit(f"Configuration Error: Environment file '{item}' specified in .terraform-branch-deploy.yml not found in repository root.")
        relative_path = os.path.relpath(p, working_dir)
        final_paths.append(f"{arg_prefix}{relative_path}")

    return final_paths


def main() -> None:
    """
    Main entry point for prepare_terrachops.py.
    Validates input, loads configuration, processes arguments and paths, and writes outputs for GitHub Actions.
    """
    # --- Robust Input Validation ---
    if len(sys.argv) != 4:
        error_exit(f"Usage: {sys.argv[0]} <default_working_dir> <env_name> <dynamic_params_str>")

    default_working_dir: str = sys.argv[1]
    env_name: str = sys.argv[2]
    dynamic_params_str: str = sys.argv[3]

    # Validate working directory
    if not isinstance(default_working_dir, str) or not default_working_dir.strip():
        error_exit("Invalid or empty working directory argument.")
    if not isinstance(env_name, str) or not env_name.strip():
        error_exit("Invalid or empty environment name argument.")
    if not isinstance(dynamic_params_str, str):
        error_exit("Invalid dynamic_params_str argument.")

    # --- GITHUB_OUTPUT Validation ---
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path or not Path(output_path).parent.exists():
        error_exit("GITHUB_OUTPUT environment variable not set or invalid.")
    # mypy: output_path is str here
    if not isinstance(output_path, str):
        error_exit("GITHUB_OUTPUT environment variable is not a string.")

    config_path = Path(".terraform-branch-deploy.yml")
    config: Dict[str, Any] = {}
    if config_path.is_file():
        log_info(f"✅ Found .terraform-branch-deploy.yml. Parsing configuration for environment: '{env_name}'")
        with open(config_path, 'r') as f:
            try:
                config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                error_exit(f"Error parsing .terraform-branch-deploy.yml: {e}")
    else:
        log_info("⚠️  No .terraform-branch-deploy.yml found. Using action defaults.")

    # --- Validate Environment ---
    if env_name and env_name != "production" and env_name not in config.get("environments", {}):
        error_exit(f"Configuration Error: Environment '{env_name}' not found in .terraform-branch-deploy.yml.")

    # --- Determine Working Directory FIRST ---
    working_dir: str = config.get("environments", {}).get(env_name, {}).get("working-directory", default_working_dir)
    if not isinstance(working_dir, str) or not working_dir.strip():
        error_exit("Invalid or empty working directory in configuration.")

    # Sanitize working_dir: Remove leading "./" if present
    if working_dir.startswith("./"):
        working_dir = working_dir[2:]
    # Also handle if it's just "."
    if working_dir == ".":
        working_dir = "" # Set to empty string if it's just ".", effectively making it the root of 'repo_checkout'

    # --- Build Arguments ---
    init_args: List[str] = process_paths(config, env_name, "backend-configs", "-backend-config=", working_dir)
    init_args.extend(process_args(config, env_name, "init-args", ""))

    plan_args: List[str] = process_paths(config, env_name, "var-files", "-var-file=", working_dir)
    plan_args.extend(process_args(config, env_name, "plan-args", ""))

    apply_args: List[str] = process_args(config, env_name, "apply-args", "")

    # --- Layer on dynamic flags from comment ---
    allowed_dynamic_flags: List[str] = ["--target", "-var"]
    dynamic_flags: List[str] = []
    for param in dynamic_params_str.split():
        for allowed in allowed_dynamic_flags:
            if param.startswith(allowed):
                # Only allow alphanumeric, dashes, underscores, equals, AND DOTS in dynamic flags
                if not all(c.isalnum() or c in "-_=. []" for c in param): # Added '.' to allowed characters
                    error_exit(f"Dynamic flag '{param}' contains invalid characters.")
                dynamic_flags.append(param)

    plan_args.extend(dynamic_flags)

    # --- Write final values to GitHub Actions Output ---
    final_init_args: str = ' '.join(init_args)
    final_plan_args: str = ' '.join(plan_args)
    final_apply_args: str = ' '.join(apply_args)

    try:
        with open(output_path, "a") as f:
            f.write(f"working_dir={working_dir}\n")
            f.write(f"init_args={final_init_args}\n")
            f.write(f"plan_args={final_plan_args}\n")
            f.write(f"apply_args={final_apply_args}\n")
    except Exception as e:
        error_exit(f"Failed to write to GITHUB_OUTPUT: {e}")

    log_section("📝 terraform-branch-deploy configuration summary:")
    log_info(f"    📁 Working Directory: {working_dir}")
    log_info(f"    🏗️  Init Args: {final_init_args}")
    log_info(f"    📋 Plan Args: {final_plan_args}")
    log_info(f"    🚀 Apply Args: {final_apply_args}")
    log_info("✅ Configuration prepared for Terraform execution.")

if __name__ == "__main__":
    main()
