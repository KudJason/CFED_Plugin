#!/bin/bash
set -e

# Parameters: project_name algorithm_path function_name [protection_type]
PROJECT=$1
ALGORITHM_PATH=$2
FUNCTION=$3
PROTECTION=$4

# Extract the algorithm name from the path
ALGORITHM=$(basename "$ALGORITHM_PATH" .cpp)

# Find the directory for the algorithm
ALGORITHM_CATEGORY=$(dirname "$ALGORITHM_PATH")
ALGORITHM_CATEGORY=$(basename "$ALGORITHM_CATEGORY")

# Set default protection if not provided
if [ -z "$PROTECTION" ]; then
    PROTECTION="NONE"
fi

echo "Building $PROJECT ($ALGORITHM::$FUNCTION) with protection: $PROTECTION"

# Create output directory
mkdir -p "../data/GCC_Plugin_Output/$PROJECT"

# Build command
if [ "$PROTECTION" == "RACFED" ]; then
    # Protected version
    make -f ../src/algorithm_compiler/compiler_set/universal.mak clean \
         ALGORITHM=$ALGORITHM \
         FUNCTION=$FUNCTION \
         PROJECT=$PROJECT \
         PROTECTION=$PROTECTION \
         SRC_DIR="../data/C-Plus-Plus/$ALGORITHM_CATEGORY"
    
    make -f ../src/algorithm_compiler/compiler_set/universal.mak all \
         ALGORITHM=$ALGORITHM \
         FUNCTION=$FUNCTION \
         PROJECT=$PROJECT \
         PROTECTION=$PROTECTION \
         SRC_DIR="../data/C-Plus-Plus/$ALGORITHM_CATEGORY"
else
    # Non-protected version
    make -f ../src/algorithm_compiler/compiler_set/universal.mak clean \
         ALGORITHM=$ALGORITHM \
         FUNCTION=$FUNCTION \
         PROJECT=$PROJECT \
         SRC_DIR="../data/C-Plus-Plus/$ALGORITHM_CATEGORY"
    
    make -f ../src/algorithm_compiler/compiler_set/universal.mak all \
         ALGORITHM=$ALGORITHM \
         FUNCTION=$FUNCTION \
         PROJECT=$PROJECT \
         SRC_DIR="../data/C-Plus-Plus/$ALGORITHM_CATEGORY"
fi

echo "Compilation completed for $PROJECT" 