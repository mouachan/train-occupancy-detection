from pydantic import BaseModel, Field
from typing import List, Optional, Any


class Detection(BaseModel):
    """Represents a single person detection."""
    bbox: List[float] = Field(..., description="Bounding box coordinates [x1, y1, x2, y2]")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Detection confidence score")
    class_id: int = Field(..., description="Class ID (0 for person in COCO)")
    class_name: str = Field(default="person", description="Class name")


class KServeInferenceInput(BaseModel):
    """KServe V2 inference input format."""
    name: str = Field(..., description="Input tensor name")
    shape: List[int] = Field(..., description="Input tensor shape")
    datatype: str = Field(..., description="Data type (e.g., FP32, INT64)")
    data: List[Any] = Field(..., description="Flattened input data")


class KServeInferenceOutput(BaseModel):
    """KServe V2 inference output format."""
    name: str = Field(..., description="Output tensor name")
    shape: List[int] = Field(..., description="Output tensor shape")
    datatype: str = Field(..., description="Data type")
    data: List[Any] = Field(..., description="Flattened output data")


class KServeInferenceRequest(BaseModel):
    """KServe V2 inference request."""
    inputs: List[KServeInferenceInput] = Field(..., description="List of input tensors")
    parameters: Optional[dict] = Field(default=None, description="Optional inference parameters")


class KServeInferenceResponse(BaseModel):
    """KServe V2 inference response."""
    model_name: str = Field(..., description="Name of the model")
    model_version: Optional[str] = Field(default=None, description="Model version")
    outputs: List[KServeInferenceOutput] = Field(..., description="List of output tensors")
    parameters: Optional[dict] = Field(default=None, description="Optional response parameters")


class DetectionResult(BaseModel):
    """Processed detection result."""
    detections: List[Detection] = Field(..., description="List of detected persons")
    inference_time_ms: float = Field(..., description="Inference time in milliseconds")
    image_shape: List[int] = Field(..., description="Original image shape [height, width]")
    model_name: Optional[str] = Field(default=None, description="Model name")


class ModelMetadata(BaseModel):
    """Model metadata from KServe."""
    name: str = Field(..., description="Model name")
    platform: str = Field(..., description="Model platform/framework")
    inputs: List[dict] = Field(..., description="Model input specifications")
    outputs: List[dict] = Field(..., description="Model output specifications")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Health status (live, ready, etc.)")
    model_name: Optional[str] = Field(default=None, description="Model name")
