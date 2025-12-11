import streamlit as st
import cv2
import numpy as np
from pathlib import Path
import sys
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import requests
import urllib3
import time

from src.detection.yolo_detector import YOLODetector
from src.detection.visualizer import draw_detections, create_detection_summary, draw_summary_on_frame
from src.utils.config import Config
from src.utils.video_processor import VideoProcessor

# Disable SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Page configuration
st.set_page_config(
    page_title="Train Occupancy Detection System",
    page_icon="🚂",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 1rem 0;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'detector' not in st.session_state:
    st.session_state.detector = None
if 'detection_mode' not in st.session_state:
    st.session_state.detection_mode = None


def initialize_local_detector():
    """Initialize YOLOv11 local detector."""
    try:
        model_path = Config.get_model_path('yolo11n.pt')
        if not model_path.exists():
            st.error(f"Model file not found: {model_path}")
            st.info("Please download the model using: `from ultralytics import YOLO; YOLO('yolo11n.pt')`")
            return None

        detector = YOLODetector(
            model_path=str(model_path),
            conf_threshold=st.session_state.conf_threshold,
            device='cpu'
        )
        return detector
    except Exception as e:
        st.error(f"Error initializing detector: {e}")
        return None


def preprocess_image_for_api(image: np.ndarray, target_size=640):
    """Preprocess image for YOLO API inference."""
    img_resized = cv2.resize(image, (target_size, target_size))
    img_rgb = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
    img_normalized = img_rgb.astype(np.float32) / 255.0
    img_chw = np.transpose(img_normalized, (2, 0, 1))
    # Add batch dimension [3,640,640] -> [1,3,640,640]
    img_batch = np.expand_dims(img_chw, axis=0)
    return img_batch, image.shape[:2]


def postprocess_yolo_output(output_data, orig_shape, conf_threshold=0.25, input_size=640):
    """Postprocess YOLO output to extract person detections."""
    # Convert list to numpy array if needed
    if isinstance(output_data, list):
        output_data = np.array(output_data)

    # Reshape from flat array [705600] to [1, 84, 8400]
    if len(output_data.shape) == 1:
        output_data = output_data.reshape(1, 84, 8400)

    # Remove batch dimension [1, 84, 8400] -> [84, 8400]
    if len(output_data.shape) == 3:
        output_data = output_data[0]

    # Transpose to [8400, 84]
    if output_data.shape[0] == 84:
        output_data = output_data.T

    # Extract person detections (class 0)
    boxes = output_data[:, :4]  # [x_center, y_center, width, height]
    scores = output_data[:, 4:]  # [80 classes]
    person_scores = scores[:, 0]  # Class 0 = person

    # Filter by confidence
    mask = person_scores >= conf_threshold
    filtered_boxes = boxes[mask]
    filtered_scores = person_scores[mask]

    # Convert to Detection objects
    detections = []
    orig_h, orig_w = orig_shape
    scale_x = orig_w / input_size
    scale_y = orig_h / input_size

    for box, score in zip(filtered_boxes, filtered_scores):
        x_center, y_center, width, height = box

        # Convert to corner coordinates and scale back to original size
        x1 = int((x_center - width / 2) * scale_x)
        y1 = int((y_center - height / 2) * scale_y)
        x2 = int((x_center + width / 2) * scale_x)
        y2 = int((y_center + height / 2) * scale_y)

        # Clip to image boundaries
        x1 = max(0, min(x1, orig_w))
        y1 = max(0, min(y1, orig_h))
        x2 = max(0, min(x2, orig_w))
        y2 = max(0, min(y2, orig_h))

        # Create detection object
        class Detection:
            def __init__(self, bbox, confidence, class_name='person'):
                self.bbox = bbox
                self.confidence = confidence
                self.class_name = class_name

        detection = Detection(
            bbox=[x1, y1, x2, y2],
            confidence=float(score),
            class_name='person'
        )
        detections.append(detection)

    return detections


def initialize_api_client(endpoint_url: str, model_name: str):
    """Initialize API configuration and test connection."""
    try:
        # Build inference URL
        infer_url = f"{endpoint_url}/v2/models/{model_name}/infer"

        # Test health check
        health_url = f"{endpoint_url}/v2/health/live"
        response = requests.get(health_url, verify=False, timeout=5)

        if response.status_code != 200:
            st.warning(f"API health check returned status {response.status_code}")

        # Return config dict instead of client object
        return {
            'infer_url': infer_url,
            'endpoint_url': endpoint_url,
            'model_name': model_name
        }
    except Exception as e:
        st.error(f"Error connecting to API: {e}")
        return None


def process_image_local(image: np.ndarray, detector):
    """Process image with local detector."""
    detections = detector.detect_persons(image)
    annotated = draw_detections(image, detections)
    summary = create_detection_summary(detections)
    annotated = draw_summary_on_frame(annotated, summary)
    return annotated, detections, summary


def process_image_api(image: np.ndarray, api_config, conf_threshold=0.25):
    """Process image with API using direct HTTP calls."""
    try:
        # Preprocess
        img_data, orig_shape = preprocess_image_for_api(image)

        # Prepare KServe V2 request
        request_data = {
            "inputs": [{
                "name": "images",
                "shape": list(img_data.shape),
                "datatype": "FP32",
                "data": img_data.flatten().tolist()
            }]
        }

        # Send request
        response = requests.post(
            api_config['infer_url'],
            json=request_data,
            verify=False,
            timeout=30
        )

        # Handle errors
        if response.status_code != 200:
            st.error(f"API Error {response.status_code}: {response.text}")
            return None, [], {}

        # Parse response
        result = response.json()
        output_data = result["outputs"][0]["data"]

        # Postprocess
        detections = postprocess_yolo_output(output_data, orig_shape, conf_threshold)

        # Visualize
        annotated = draw_detections(image, detections)
        summary = create_detection_summary(detections)
        annotated = draw_summary_on_frame(annotated, summary)

        return annotated, detections, summary

    except Exception as e:
        st.error(f"Error during API inference: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None, [], {}


# Main header
st.markdown('<div class="main-header">🚂 Train Occupancy Detection System</div>', unsafe_allow_html=True)
st.markdown("---")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")

    # Detection mode selection
    detection_mode = st.radio(
        "Detection Mode",
        ["Local Model", "API Endpoint"],
        help="Choose between local embedded model or remote API"
    )

    st.session_state.detection_mode = detection_mode

    # Confidence threshold
    st.session_state.conf_threshold = st.slider(
        "Confidence Threshold",
        min_value=0.0,
        max_value=1.0,
        value=0.25,
        step=0.05,
        help="Minimum confidence score for detections"
    )

    # Mode-specific configuration
    if detection_mode == "API Endpoint":
        st.subheader("API Configuration")
        api_endpoint = st.text_input(
            "Endpoint URL",
            value="http://yolo11-person-detection:8080",
            help="KServe inference endpoint URL"
        )
        api_model_name = st.text_input(
            "Model Name",
            value="yolo11-person-detection",
            help="Name of the deployed model"
        )

    st.markdown("---")
    st.info("""
    **About this system:**

    Detect persons in train cars at final destination before parking in hangar.

    - **Local Mode**: Fast, embedded inference
    - **API Mode**: Scalable, cloud-based inference
    """)

# Main content
tab1, tab2, tab3 = st.tabs(["📹 Video Upload", "📊 Statistics", "ℹ️ About"])

with tab1:
    st.header("Upload and Process Video")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a video file",
        type=['mp4', 'avi', 'mov', 'mkv'],
        help="Upload a train video for person detection"
    )

    if uploaded_file is not None:
        # Display video info
        st.success(f"Uploaded: {uploaded_file.name} ({uploaded_file.size / (1024*1024):.2f} MB)")

        # Initialize detector based on mode
        if st.session_state.detection_mode == "Local Model":
            if st.session_state.detector is None or not isinstance(st.session_state.detector, YOLODetector):
                with st.spinner("Initializing local detector..."):
                    st.session_state.detector = initialize_local_detector()
            detector = st.session_state.detector
        else:
            if st.session_state.detector is None or not isinstance(st.session_state.detector, dict):
                with st.spinner("Connecting to API..."):
                    st.session_state.detector = initialize_api_client(api_endpoint, api_model_name)
            detector = st.session_state.detector

        if detector is None:
            st.error("Failed to initialize detector. Please check configuration.")
        else:
            # Process video button
            if st.button("🎬 Process Video", type="primary"):
                # Save uploaded file to temp
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                    tmp_file.write(uploaded_file.read())
                    video_path = tmp_file.name

                # Get video info
                try:
                    video_info = VideoProcessor.get_video_info(video_path)
                    st.info(f"Video: {video_info['width']}x{video_info['height']}, "
                           f"{video_info['fps']:.2f} FPS, {video_info['frame_count']} frames, "
                           f"{video_info['duration_seconds']:.2f}s")
                except Exception as e:
                    st.error(f"Error reading video: {e}")
                    st.stop()

                # Process video
                progress_bar = st.progress(0)
                status_text = st.empty()
                frame_placeholder = st.empty()

                col1, col2, col3 = st.columns(3)
                metric_persons = col1.empty()
                metric_frames = col2.empty()
                metric_fps = col3.empty()

                total_persons = 0
                frame_count = 0
                skip_frames = 2  # Process every 3rd frame for performance

                try:
                    if isinstance(detector, YOLODetector):
                        # Local processing
                        for frame, detections in detector.process_video(video_path, skip_frames=skip_frames):
                            frame_count += 1
                            total_persons += len(detections)

                            # Update progress
                            progress = frame_count / (video_info['frame_count'] // (skip_frames + 1))
                            progress_bar.progress(min(progress, 1.0))
                            status_text.text(f"Processing frame {frame_count}...")

                            # Annotate frame
                            annotated = draw_detections(frame, detections)
                            summary = create_detection_summary(detections)
                            annotated = draw_summary_on_frame(annotated, summary)

                            # Display every 10th frame
                            if frame_count % 10 == 0:
                                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                                frame_placeholder.image(frame_rgb, use_container_width=True)

                            # Update metrics
                            metric_persons.metric("Total Persons Detected", total_persons)
                            metric_frames.metric("Frames Processed", frame_count)
                            metric_fps.metric("Avg Persons/Frame", f"{total_persons/frame_count:.2f}")

                    else:
                        # API processing
                        for frame_num, frame in VideoProcessor.read_frames(video_path, skip_frames=skip_frames):
                            frame_count += 1

                            # Process frame with API
                            annotated, detections, summary = process_image_api(
                                frame,
                                detector,
                                conf_threshold=st.session_state.conf_threshold
                            )

                            if annotated is None:
                                st.error(f"Failed to process frame {frame_count}")
                                break

                            total_persons += len(detections)

                            # Update progress
                            progress = frame_count / (video_info['frame_count'] // (skip_frames + 1))
                            progress_bar.progress(min(progress, 1.0))
                            status_text.text(f"Processing frame {frame_count}...")

                            # Display every 10th frame
                            if frame_count % 10 == 0:
                                frame_rgb = cv2.cvtColor(annotated, cv2.COLOR_BGR2RGB)
                                frame_placeholder.image(frame_rgb, use_container_width=True)

                            # Update metrics
                            metric_persons.metric("Total Persons Detected", total_persons)
                            metric_frames.metric("Frames Processed", frame_count)
                            metric_fps.metric("Avg Persons/Frame", f"{total_persons/frame_count:.2f}")

                    progress_bar.progress(1.0)
                    status_text.text("✅ Processing complete!")
                    st.success(f"Processed {frame_count} frames, detected {total_persons} persons total")

                except Exception as e:
                    st.error(f"Error during processing: {e}")
                    import traceback
                    st.code(traceback.format_exc())

with tab2:
    st.header("Detection Statistics")
    st.info("Process a video to see statistics here.")

with tab3:
    st.header("About Train Occupancy Detection System")

    st.markdown("""
    ### Overview
    This system detects persons in train cars at the final destination before parking in the hangar.

    ### Features
    - **YOLOv11 Detection**: State-of-the-art person detection
    - **Dual Mode**: Local embedded model or remote API
    - **Real-time Visualization**: Bounding boxes and confidence scores
    - **Performance Metrics**: Detection statistics and summaries

    ### Technology Stack
    - **Model**: YOLOv11 (ONNX format for deployment)
    - **Framework**: Streamlit for web UI
    - **Deployment**: OpenShift AI (KServe) for model serving
    - **Backend**: Python, OpenCV, ONNX Runtime

    ### Usage
    1. Select detection mode (Local or API)
    2. Configure confidence threshold
    3. Upload train video
    4. Click "Process Video"
    5. View results with bounding boxes and statistics

    ### Contact
    For issues or questions, please refer to the project documentation.
    """)
