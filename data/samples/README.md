# Sample Data

This directory contains sample images and videos for testing the train occupancy detection system.

## Files

### Images
- `rame-with-person.jpeg` - Train car interior with person(s) present
  - Format: JPEG
  - Size: ~969 KB
  - Use case: Test person detection in train environment

### Videos
- `sample_video.mp4` - Video footage for testing frame-by-frame detection
  - Format: MP4
  - Size: ~35 MB
  - Duration: Multiple frames
  - Use case: Test video processing pipeline with API inference
  - **Note**: Not committed to Git (too large). Place your own video here.

## Usage

### In Notebooks

```python
# Use local sample image
image_path = "../../data/samples/rame-with-person.jpeg"

# Use local sample video
video_path = "../../data/samples/sample_video.mp4"
```

### Testing Detection

```python
from src.detection.yolo_detector import YOLODetector

detector = YOLODetector(model_path='models/yolo11n.pt')
annotated_img, detections = detector.process_image('data/samples/rame-with-person.jpeg')
print(f"Detected {len(detections)} persons")
```

## Adding Your Own Samples

Place your train images/videos in this directory:

```bash
# Add custom train footage
cp /path/to/your/train_video.mp4 data/samples/my_train_video.mp4
```

Then reference them in notebooks or scripts.
