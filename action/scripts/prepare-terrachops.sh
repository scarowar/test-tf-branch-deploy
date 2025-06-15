#!/bin/bash
#
# prepare-terrachops.sh
#
# This script parses the .terrachops.yml configuration file and dynamic
# parameters from a PR comment to build the final, safe command strings
# for all terraform operations.
#
# It enforces a strict priority model:
# 1. Defaults from .terrachops.yml (lowest)
# 2. Environment-specific settings from .terrachops.yml
# 3. Dynamic flags from PR comment (highest)
#
set -e
set -o pipefail

# --- INPUTS ---
DEFAULT_WORKING_DIR="$1"
ENV_NAME="$2"
DYNAMIC_PARAMS="$3"

# --- Helper Functions ---
# Safely exits with a formatted error message.
error_exit() {
  echo "::error::$1"
  exit 1
}

# Builds an argument string from a YAML list, validating the type first.
build_args_from_list() {
  local query_path="$1"
  local prefix="$2"
  local args=""

  # Validate that the path exists and is a list (array).
  if yq e "has($query_path)" .terrachops.yml | grep -q 'true'; then
    if [ "$(yq e "($query_path) | type" .terrachops.yml)" != "!!seq" ]; then
      error_exit "Configuration Error: '$query_path' in .terrachops.yml must be a list (e.g., using '- ...')."
    fi
    # Read the list, handle nulls, and output one item per line
    for item in $(yq e "$query_path | .[]" .terrachops.yml); do
      args+=" ${prefix}${item}"
    done
  fi
  echo "$args"
}

# Processes a configuration key, handling inheritance and merging.
process_list() {
  local key_name="$1"
  local arg_prefix="$2"
  local list_key="paths" # Default for var-files and backend-configs
  [[ "$key_name" == *"-args" ]] && list_key="args"

  # Check if the environment explicitly disables inheritance (defaults to true)
  inherit=$(yq e ".environments.$ENV_NAME.$key_name.inherit // true" .terrachops.yml)

  local default_args=""
  # If inheriting, get default values
  if [ "$inherit" == "true" ]; then
    default_args=$(build_args_from_list ".defaults.$key_name.$list_key" "$arg_prefix")
  fi

  # Get environment-specific values
  env_args=$(build_args_from_list ".environments.$ENV_NAME.$key_name.$list_key" "$arg_prefix")
  echo "${default_args}${env_args}" | xargs # xargs trims leading/trailing whitespace
}

# --- Main Logic ---
if [ ! -f ".terrachops.yml" ]; then
  echo "No .terrachops.yml found. Using action defaults."
  FINAL_WORKING_DIR=$DEFAULT_WORKING_DIR
  FINAL_INIT_ARGS=""
  FINAL_PLAN_ARGS=""
  FINAL_APPLY_ARGS=""
else
  echo "Found .terrachops.yml. Parsing configuration for environment: '$ENV_NAME'"

  # Validate that the specified environment exists in the config file
  if [ -n "$ENV_NAME" ] && [ "$ENV_NAME" != "production" ]; then
    if ! yq e "has(.environments.$ENV_NAME)" .terrachops.yml | grep -q 'true'; then
      error_exit "Configuration Error: Environment '$ENV_NAME' not found in .terrachops.yml."
    fi
  fi

  # Load all settings by processing each key using the new consistent structure
  FINAL_WORKING_DIR=$(yq e ".environments.$ENV_NAME.working-directory // \"$DEFAULT_WORKING_DIR\"" .terrachops.yml)

  BACKEND_CONFIGS=$(process_list "backend-configs" "-backend-config=")
  VAR_FILES=$(process_list "var-files" "-var-file=")
  INIT_ARGS_GENERIC=$(process_list "init-args" "")
  PLAN_ARGS_GENERIC=$(process_list "plan-args" "")
  APPLY_ARGS_GENERIC=$(process_list "apply-args" "")

  FINAL_INIT_ARGS=$(echo "${BACKEND_CONFIGS}${INIT_ARGS_GENERIC}" | xargs)
  FINAL_PLAN_ARGS=$(echo "${VAR_FILES}${PLAN_ARGS_GENERIC}" | xargs)
  FINAL_APPLY_ARGS=$(echo "${APPLY_ARGS_GENERIC}" | xargs)
fi

# --- Layer on dynamic flags from comment (highest priority) ---
SAFE_DYNAMIC_FLAGS=""
# Use a case statement for a scalable and secure whitelist of allowed flags
for param in $DYNAMIC_PARAMS; do
  case "$param" in
    --target=*)
      TARGET_VALUE=$(echo "$param" | cut -d'=' -f2)
      # Re-validate here to ensure no malicious characters are passed
      if [[ "$TARGET_VALUE" =~ ^[a-zA-Z0-9_.-]+\[?[0-9]*\]?$ ]]; then
         SAFE_DYNAMIC_FLAGS+=" --target=${TARGET_VALUE}"
      else
        error_exit "Invalid characters in dynamic --target value: $TARGET_VALUE"
      fi
      ;;
    # Add other whitelisted flags here, e.g.:
    # -var=*)
    #   ...
    #   ;;
    *)
      # Ignore any non-whitelisted flags
      echo "Warning: Ignoring unsupported dynamic parameter '$param'."
      ;;
  esac
done

# Combine static and dynamic flags for plan
FULL_PLAN_ARGS=$(echo "${FINAL_PLAN_ARGS} ${SAFE_DYNAMIC_FLAGS}" | xargs)

# --- Output final values ---
echo "working_dir=${FINAL_WORKING_DIR}" >> "$GITHUB_OUTPUT"
echo "init_args=${FINAL_INIT_ARGS}" >> "$GITHUB_OUTPUT"
echo "plan_args=${FULL_PLAN_ARGS}" >> "$GITHUB_OUTPUT"
echo "apply_args=${FINAL_APPLY_ARGS}" >> "$GITHUB_OUTPUT"
