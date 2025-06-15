#!/bin/bash

set -e
set -o pipefail

# --- INPUTS ---
DEFAULT_WORKING_DIR="$1"
ENV_NAME="$2"
DYNAMIC_PARAMS="$3"

# --- Helper Functions ---
error_exit() {
  echo "::error::$1"
  exit 1
}

# --- Main Logic ---
if [ ! -f ".terrachops.yml" ]; then
  echo "No .terrachops.yml found. Using action defaults."
  FINAL_WORKING_DIR=$DEFAULT_WORKING_DIR
  FINAL_INIT_ARGS=""
  FINAL_PLAN_ARGS=""
  FINAL_APPLY_ARGS=""
else
  echo "✅ Found .terrachops.yml. Parsing configuration for environment: '$ENV_NAME'"

  if [ -n "$ENV_NAME" ] && [ "$ENV_NAME" != "production" ] && [[ "$(yq e ".environments.$ENV_NAME" .terrachops.yml)" == "null" ]]; then
    error_exit "Configuration Error: Environment '$ENV_NAME' not found in .terrachops.yml."
  fi

  # --- Determine Final Working Directory ---
  FINAL_WORKING_DIR=$(yq e ".environments.$ENV_NAME.working-directory // \"$DEFAULT_WORKING_DIR\"" .terrachops.yml | xargs)

  # --- Build Argument Strings ---
  process_args() {
    local key_name="$1"
    local arg_prefix="$2"
    local list_key="paths"
    [[ "$key_name" == *"-args" ]] && list_key="args"
    local final_args=""

    # 1. Process default arguments
    inherit=$(yq e ".environments.$ENV_NAME.$key_name.inherit // true" .terrachops.yml)
    if [ "$inherit" == "true" ]; then
      for item in $(yq e ".defaults.$key_name.$list_key[]?" .terrachops.yml); do
        # For paths, calculate relative path from working dir. For args, use as-is.
        if [[ "$list_key" == "paths" ]]; then
          # Ensure file exists before calculating path
          [ ! -f "$item" ] && error_exit "Configuration Error: Default file '$item' not found in repository root."
          item=$(realpath --relative-to="$FINAL_WORKING_DIR" "$item")
        fi
        final_args+=" ${arg_prefix}${item}"
      done
    fi

    # 2. Process environment-specific arguments
    for item in $(yq e ".environments.$ENV_NAME.$key_name.$list_key[]?" .terrachops.yml); do
        # For paths, calculate relative path. For args, use as-is.
        if [[ "$list_key" == "paths" ]]; then
          # Ensure file exists before calculating path
          [ ! -f "$item" ] && error_exit "Configuration Error: Environment file '$item' not found in repository root."
          item=$(realpath --relative-to="$FINAL_WORKING_DIR" "$item")
        fi
        final_args+=" ${arg_prefix}${item}"
    done

    echo "$final_args"
  }

  FINAL_INIT_ARGS="$(process_args 'backend-configs' '-backend-config=') $(process_args 'init-args' '')"
  FINAL_PLAN_ARGS="$(process_args 'var-files' '-var-file=') $(process_args 'plan-args' '')"
  FINAL_APPLY_ARGS="$(process_args 'apply-args' '')"
fi

# --- Securely Parse & Append Dynamic Flags ---
SAFE_DYNAMIC_FLAGS=""
# Read params into an array to handle quoted values correctly
read -r -a DYNAMIC_PARAMS_ARRAY <<< "$DYNAMIC_PARAMS"
for param in "${DYNAMIC_PARAMS_ARRAY[@]}"; do
  case "$param" in
    --target=*)
      # Allow multiple --target flags
      SAFE_DYNAMIC_FLAGS+=" $param"
      ;;
    -var=*)
      # Allow multiple -var flags
      SAFE_DYNAMIC_FLAGS+=" $param"
      ;;
    *)
      echo "::warning::Ignoring unsupported dynamic parameter '$param'."
      ;;
  esac
done

FULL_PLAN_ARGS="${FINAL_PLAN_ARGS}${SAFE_DYNAMIC_FLAGS}"

# --- Output final, trimmed values ---
echo "working_dir=$(echo "$FINAL_WORKING_DIR" | xargs)" >> "$GITHUB_OUTPUT"
echo "init_args=$(echo "$FINAL_INIT_ARGS" | xargs)" >> "$GITHUB_OUTPUT"
echo "plan_args=$(echo "$FULL_PLAN_ARGS" | xargs)" >> "$GITHUB_OUTPUT"
echo "apply_args=$(echo "$FINAL_APPLY_ARGS" | xargs)" >> "$GITHUB_OUTPUT"
