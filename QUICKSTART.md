# Quick Start Guide

This guide will help you get up and running with the Train Occupancy Detection System in 5 minutes.

## Step 1: Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# For Streamlit app, install additional dependencies
pip install -r requirements-streamlit.txt
```

## Step 2: Download YOLOv11 Model

```bash
# Download YOLOv11n model (will be saved to current directory)
python -c "from ultralytics import YOLO; model = YOLO('yolo11n.pt'); print('Model downloaded successfully')"

# Move to models directory
mkdir -p models
mv yolo11n.pt models/
```

## Step 3: Test Local Detection

### Option A: Using Test Script

```bash
# Download a sample image
curl -o test_image.jpg https://ultralytics.com/images/bus.jpg

# Run inference
python scripts/test_inference.py --mode yolo --model models/yolo11n.pt --image test_image.jpg

# Check output: test_image_yolo_result.jpg
```

### Option B: Using Jupyter Notebook

```bash
# Launch Jupyter
jupyter notebook

# Open notebooks/01_local_detection.ipynb
# Run all cells
```

## Step 4: Run Streamlit Application

```bash
# Launch Streamlit app
streamlit run streamlit_app/app.py

# Open browser to http://localhost:8501
# Upload a video and click "Process Video"
```

## Step 5: (Optional) Export to ONNX

```bash
# Export model to ONNX format for deployment
python scripts/export_to_onnx.py \
    --model models/yolo11n.pt \
    --output models/yolo11n.onnx
```

## Next Steps

### For Local Development
- Experiment with different confidence thresholds
- Try different YOLO model variants (yolo11s, yolo11m)
- Test with your own train videos

### For Production Deployment
1. Follow the [OpenShift AI deployment guide](README.md#deployment-on-openshift-ai)
2. Export model to ONNX
3. Upload to S3/MinIO
4. Deploy InferenceService
5. Deploy Streamlit app

## Troubleshooting

### Model Not Found
```bash
# Re-download the model
python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"
```

### ImportError
```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Permission Denied (Scripts)
```bash
# Make scripts executable
chmod +x scripts/*.py
```

## Common Commands

```bash
# Test ONNX inference
python scripts/test_inference.py --mode onnx --model models/yolo11n.onnx --image test.jpg

# Test API inference (requires deployed model)
python scripts/test_inference.py --mode api --endpoint http://localhost:8080 --image test.jpg

# Run tests
pytest tests/

# Format code
black src/
```

## What's Next?

1. Read the full [README.md](README.md) for detailed documentation
2. Explore the [notebooks](notebooks/) for interactive examples
3. Check [models/README.md](models/README.md) for model information
4. Review [OpenShift manifests](openshift/) for deployment configuration

## Getting Help

- Check [Troubleshooting section in README](README.md#troubleshooting)
- Review [YOLOv11 documentation](https://docs.ultralytics.com/models/yolo11/)
- Open an issue on GitHub

Happy detecting!
