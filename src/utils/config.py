import os
from pathlib import Path
from typing import Optional


class Config:
    """Configuration management for the application."""

    # Project paths
    PROJECT_ROOT = Path(__file__).parent.parent.parent
    MODELS_DIR = PROJECT_ROOT / "models"
    UPLOADS_DIR = PROJECT_ROOT / "uploads"

    # Model settings
    DEFAULT_MODEL_NAME = "yolo11n.pt"
    DEFAULT_ONNX_MODEL = "yolo11n.onnx"
    DEFAULT_CONF_THRESHOLD = 0.25
    DEFAULT_IOU_THRESHOLD = 0.45
    DEFAULT_INPUT_SIZE = 640

    # KServe settings
    KSERVE_ENDPOINT = os.getenv("KSERVE_ENDPOINT", "http://localhost:8080")
    MODEL_NAME = os.getenv("MODEL_NAME", "yolo11-person-detection")

    # Video processing
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov', '.mkv']
    SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.bmp']

    # Detection settings
    PERSON_CLASS_ID = 0  # COCO dataset person class

    @classmethod
    def get_model_path(cls, model_name: Optional[str] = None) -> Path:
        """Get full path to model file."""
        if model_name is None:
            model_name = cls.DEFAULT_MODEL_NAME
        return cls.MODELS_DIR / model_name

    @classmethod
    def get_onnx_model_path(cls, model_name: Optional[str] = None) -> Path:
        """Get full path to ONNX model file."""
        if model_name is None:
            model_name = cls.DEFAULT_ONNX_MODEL
        return cls.MODELS_DIR / model_name

    @classmethod
    def ensure_directories(cls):
        """Ensure required directories exist."""
        cls.MODELS_DIR.mkdir(parents=True, exist_ok=True)
        cls.UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def is_video_file(cls, filename: str) -> bool:
        """Check if file is a supported video format."""
        return Path(filename).suffix.lower() in cls.SUPPORTED_VIDEO_FORMATS

    @classmethod
    def is_image_file(cls, filename: str) -> bool:
        """Check if file is a supported image format."""
        return Path(filename).suffix.lower() in cls.SUPPORTED_IMAGE_FORMATS
