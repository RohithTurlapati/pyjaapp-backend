#!/bin/bash
set -e

# This script packages the FastAPI app dependencies into a zip file for AWS Lambda.
# It uses 'uv' which provides incredible speed.
# It must be run on a Linux environment (like GitHub Actions ubuntu-latest) to ensure binary compatibility.

echo "Cleaning up old build artifacts..."
rm -rf package/ lambda_function.zip requirements.txt

echo "Creating package directory..."
mkdir package

echo "Exporting dependencies using uv..."
# For AWS Lambda, we only need the production dependencies directly from the pyproject configuration
uv export --no-dev --format requirements.txt > requirements.txt

echo "Installing Linux-compatible dependencies..."
uv pip install -r requirements.txt --target package

echo "Copying application code into package..."
cp -r app package/

echo "Creating lambda_function.zip..."
cd package
zip -r9 ../lambda_function.zip .
cd ..

echo "Build complete! lambda_function.zip created."
