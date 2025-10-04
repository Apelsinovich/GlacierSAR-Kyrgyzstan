#!/bin/bash

# 🚀 QUICK START SCRIPT for SAR Glacier Monitoring
# Ala-Archa Glaciers - NASA Space Apps Challenge 2025

echo "================================================================================
🚀 SAR GLACIER MONITORING - QUICK START SCRIPT
================================================================================
"

# Check Python version
echo "📋 Step 1: Checking Python version..."
python3 --version
if [ $? -ne 0 ]; then
    echo "❌ Python 3 not found. Please install Python 3.8+"
    exit 1
fi
echo "✅ Python version OK"

# Check if we're in the right directory
if [ ! -f "sar_pipeline.py" ]; then
    echo "❌ Please run this script from the GlacierSAR-Kyrgyzstan directory"
    exit 1
fi

echo "
📦 Step 2: Installing dependencies..."
echo "Installing core libraries..."
pip3 install numpy matplotlib scipy rasterio geopandas pyyaml > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies. Try: pip3 install numpy matplotlib scipy rasterio geopandas pyyaml"
    exit 1
fi
echo "✅ Dependencies installed"

echo "
🧪 Step 3: Testing pipeline..."
python3 sar_pipeline.py > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Pipeline test failed. Check your installation."
    exit 1
fi
echo "✅ Pipeline test passed"

echo "
🎯 Step 4: Running examples..."
echo "This will create visualizations in output/visualizations/"
python3 example_workflow.py

echo "
================================================================================
✅ QUICK START COMPLETED SUCCESSFULLY!
================================================================================
"

echo "📁 Next steps:"
echo "1. 📥 Download real Sentinel-1 data from https://search.asf.alaska.edu/"
echo "   - Coordinates: 42.565, 74.5 (Ala-Archa)"
echo "   - Polarization: VV+VH (recommended)"
echo "   - Place files in: output/raw_data/"
echo ""
echo "2. 🔬 Analyze your data:"
echo "   python3 -c \"from sar_pipeline import SARGlacierPipeline; pipeline = SARGlacierPipeline('config.yaml'); print('Pipeline ready!')\""
echo ""
echo "3. 📊 Check results in: output/visualizations/"
echo ""
echo "4. 📖 Read documentation:"
echo "   - QUICK_START_CHECKLIST.md (10 min guide)"
echo "   - QUICK_START.md (detailed guide)"
echo "   - DEBRIS_CLASSIFICATION.md (ice vs rock classification)"
echo ""
echo "================================================================================
🎉 WELCOME TO SAR GLACIER MONITORING!
Team TengriSpacers | NASA Space Apps Challenge 2025
================================================================================
"

