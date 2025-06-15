#!/bin/bash
#
# setup_test_infra.sh
#
# This script creates the complete directory structure and all necessary
# configuration and Terraform files for testing the Terrachops v0.1.0 release.
# Run this script from the root of your 'terrachops' repository.

set -e

echo "🚀 Starting setup of Terrachops test infrastructure..."

# 1. Create the common.tfvars file
echo "📝 Creating common.tfvars..."
cat > common.tfvars << 'EOF'
# This file can be empty. Its presence is enough for testing.
common_var = "default"
EOF

# 2. Create the environment directories
echo "📁 Creating directory structure: terraform/dev and terraform/prod..."
mkdir -p terraform/dev
mkdir -p terraform/prod

# 3. Create files for the 'dev' environment
echo "DEV: Creating main.tf, dev.tfvars, and dev.s3.tfbackend..."
cat > terraform/dev/main.tf << 'EOF'
resource "null_resource" "dev_test" {}
EOF

cat > terraform/dev/dev.tfvars << 'EOF'
# This file can be empty.
dev_var = "development"
EOF

cat > terraform/dev/dev.s3.tfbackend << 'EOF'
# Dummy backend config for dev
bucket = "my-dev-bucket"
key    = "terraform.tfstate"
region = "us-east-1"
EOF

# 4. Create files for the 'prod' environment
echo "PROD: Creating main.tf, prod.tfvars, secrets.prod.tfvars, and prod.s3.tfbackend..."
cat > terraform/prod/main.tf << 'EOF'
resource "null_resource" "prod_test" {}
EOF

cat > terraform/prod/prod.tfvars << 'EOF'
# This file can be empty.
prod_var = "production"
EOF

cat > terraform/prod/secrets.prod.tfvars << 'EOF'
# This file can be empty.
secret_var = "prod-secret"
EOF

cat > terraform/prod/prod.s3.tfbackend << 'EOF'
# Dummy backend config for prod
bucket = "my-prod-bucket"
key    = "terraform.tfstate"
region = "us-east-1"
EOF

echo "✅ Test infrastructure setup complete!"
