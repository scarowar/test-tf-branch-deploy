#!/usr/bin/env python3

import sys
import os
import yaml
from pathlib import Path
import logging

# --- Setup Logging ---
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')

def error_exit(message):
    """Prints a GitHub Actions-formatted error message and exits."""
    logging.error(message)
    print(f"::error::{message}")
    sys.exit(1)

def process_args(config, env_name, key_name, arg_prefix):
    """Processes a list of arguments, handling inheritance and validating types."""
    final_args = []
    inherit = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("inherit", True)

    if inherit:
        default_items = config.get("defaults", {}).get(key_name, {}).get("args", [])
        if not isinstance(default_items, list):
            error_exit(f"Configuration Error: '.defaults.{key_name}.args' must be a list.")
        final_args.extend([f"{arg_prefix}{item}" for item in default_items])

    env_items = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("args", [])
    if not isinstance(env_items, list):
        error_exit(f"Configuration Error: '.environments.{env_name}.{key_name}.args' must be a list.")
    final_args.extend([f"{arg_prefix}{item}" for item in env_items])

    return final_args

def process_paths(config, env_name, key_name, arg_prefix, working_dir):
    """Processes a list of file paths, handling inheritance and making paths relative."""
    final_paths = []
    inherit = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("inherit", True)

    if inherit:
        default_items = config.get("defaults", {}).get(key_name, {}).get("paths", [])
        if not isinstance(default_items, list):
            error_exit(f"Configuration Error: '.defaults.{key_name}.paths' must be a list.")
        for item in default_items:
            p = Path(item)
            if not p.exists():
                error_exit(f"Configuration Error: Default file '{item}' specified in .terrachops.yml not found in repository root.")
            relative_path = os.path.relpath(p, working_dir)
            final_paths.append(f"{arg_prefix}{relative_path}")

    env_items = config.get("environments", {}).get(env_name, {}).get(key_name, {}).get("paths", [])
    if not isinstance(env_items, list):
        error_exit(f"Configuration Error: '.environments.{env_name}.{key_name}.paths' must be a list.")
    for item in env_items:
        p = Path(item)
        if not p.exists():
            error_exit(f"Configuration Error: Environment file '{item}' specified in .terrachops.yml not found in repository root.")
        relative_path = os.path.relpath(p, working_dir)
        final_paths.append(f"{arg_prefix}{relative_path}")

    return final_paths


def main():
    # --- Robust Input Validation ---
    if len(sys.argv) != 4:
        error_exit(f"Usage: {sys.argv[0]} <default_working_dir> <env_name> <dynamic_params_str>")

    default_working_dir, env_name, dynamic_params_str = sys.argv[1:4]

    # --- GITHUB_OUTPUT Validation ---
    output_path = os.getenv("GITHUB_OUTPUT")
    if not output_path or not Path(output_path).parent.exists():
        error_exit("GITHUB_OUTPUT environment variable not set or invalid.")

    # --- Load Config ---
    config_path = Path(".terrachops.yml")
    config = {}
    if config_path.is_file():
        logging.info(f"✅ Found .terrachops.yml. Parsing configuration for environment: '{env_name}'")
        with open(config_path, 'r') as f:
            try:
                config = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                error_exit(f"Error parsing .terrachops.yml: {e}")
    else:
        logging.info("No .terrachops.yml found. Using action defaults.")

    # --- Validate Environment ---
    if env_name and env_name != "production" and env_name not in config.get("environments", {}):
        error_exit(f"Configuration Error: Environment '{env_name}' not found in .terrachops.yml.")

    # --- Determine Working Directory FIRST ---
    working_dir = config.get("environments", {}).get(env_name, {}).get("working-directory", default_working_dir)

    # --- Build Arguments ---
    init_args = process_paths(config, env_name, "backend-configs", "-backend-config=", working_dir)
    init_args.extend(process_args(config, env_name, "init-args", ""))

    plan_args = process_paths(config, env_name, "var-files", "-var-file=", working_dir)
    plan_args.extend(process_args(config, env_name, "plan-args", ""))

    apply_args = process_args(config, env_name, "apply-args", "")

    # --- Layer on dynamic flags from comment ---
    allowed_dynamic_flags = ["--target", "-var"]
    dynamic_flags = []
    for param in dynamic_params_str.split():
        for allowed in allowed_dynamic_flags:
            if param.startswith(allowed):
                dynamic_flags.append(param)

    plan_args.extend(dynamic_flags)

    # --- Write final values to GitHub Actions Output ---
    final_init_args = ' '.join(init_args)
    final_plan_args = ' '.join(plan_args)
    final_apply_args = ' '.join(apply_args)

    with open(output_path, "a") as f:
        f.write(f"working_dir={working_dir}\n")
        f.write(f"init_args={final_init_args}\n")
        f.write(f"plan_args={final_plan_args}\n")
        f.write(f"apply_args={final_apply_args}\n")

    logging.info("--- Final Configuration ---")
    logging.info(f"Working Directory: {working_dir}")
    logging.info(f"Init Args: {final_init_args}")
    logging.info(f"Plan Args: {final_plan_args}")
    logging.info(f"Apply Args: {final_apply_args}")
    logging.info("---------------------------")

if __name__ == "__main__":
    main()
