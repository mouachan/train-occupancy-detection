import cv2
import numpy as np
from pathlib import Path
from typing import Generator, Tuple, Optional
import tempfile


class VideoProcessor:
    """Utilities for video file processing."""

    @staticmethod
    def get_video_info(video_path: str) -> dict:
        """
        Get information about a video file.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        info = {
            'frame_count': int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            'fps': cap.get(cv2.CAP_PROP_FPS),
            'width': int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            'height': int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            'duration_seconds': 0
        }

        if info['fps'] > 0:
            info['duration_seconds'] = info['frame_count'] / info['fps']

        cap.release()
        return info

    @staticmethod
    def read_frames(video_path: str, skip_frames: int = 0) -> Generator[Tuple[int, np.ndarray], None, None]:
        """
        Read frames from video file.

        Args:
            video_path: Path to video file
            skip_frames: Number of frames to skip between reads

        Yields:
            Tuple of (frame_number, frame)
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        frame_num = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                if skip_frames == 0 or frame_num % (skip_frames + 1) == 0:
                    yield frame_num, frame

                frame_num += 1

        finally:
            cap.release()

    @staticmethod
    def save_video(frames: list, output_path: str, fps: float = 30.0, codec: str = 'mp4v'):
        """
        Save list of frames as video file.

        Args:
            frames: List of frames (numpy arrays)
            output_path: Output video file path
            fps: Frames per second
            codec: Video codec fourcc code
        """
        if not frames:
            raise ValueError("No frames to save")

        height, width = frames[0].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*codec)

        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        try:
            for frame in frames:
                out.write(frame)
        finally:
            out.release()

    @staticmethod
    def extract_frame(video_path: str, frame_number: int) -> Optional[np.ndarray]:
        """
        Extract a specific frame from video.

        Args:
            video_path: Path to video file
            frame_number: Frame number to extract

        Returns:
            Frame as numpy array or None if frame not found
        """
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            raise ValueError(f"Could not open video file: {video_path}")

        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            ret, frame = cap.read()
            return frame if ret else None
        finally:
            cap.release()

    @staticmethod
    def create_temp_video_file(uploaded_file) -> str:
        """
        Create temporary video file from uploaded file (for Streamlit).

        Args:
            uploaded_file: Streamlit UploadedFile object

        Returns:
            Path to temporary video file
        """
        suffix = Path(uploaded_file.name).suffix
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        temp_file.write(uploaded_file.read())
        temp_file.close()
        return temp_file.name

    @staticmethod
    def resize_frame(frame: np.ndarray, max_width: int = 1280, max_height: int = 720) -> np.ndarray:
        """
        Resize frame while maintaining aspect ratio.

        Args:
            frame: Input frame
            max_width: Maximum width
            max_height: Maximum height

        Returns:
            Resized frame
        """
        h, w = frame.shape[:2]

        # Calculate scale
        scale = min(max_width / w, max_height / h, 1.0)

        if scale < 1.0:
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

        return frame
