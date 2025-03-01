import torch
import numpy as np
import cv2
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model.RIFE.model.RIFE import Model
from PIL import Image
import io

class FrameInterpolator:
    def __init__(self):
        pass

    def interpolate_sequence(self, images, n_frames=7, progress_callback=None):
        """
        Interpolate between each pair of consecutive images
        
        Args:
            images (list): List of numpy arrays containing the images
            n_frames (int): Number of frames to generate between each pair
            progress_callback (function): Callback function to report progress
        
        Returns:
            list: List of interpolated frames
        """
        total_frames = (len(images) - 1) * (n_frames + 1)
        current_frame = 0
        
        interpolated_sequence = []
        
        for i in range(len(images) - 1):
            img1 = images[i]
            img2 = images[i + 1]
            
            interpolated_sequence.append(img1)
            
            for t in range(1, n_frames + 1):
                progress = t / (n_frames + 1)
                interpolated = cv2.addWeighted(img1, 1 - progress, img2, progress, 0)
                interpolated_sequence.append(interpolated)
            
            if progress_callback:
                progress = (current_frame / total_frames) * 100
                progress_callback(progress)
            current_frame += 1
        
        interpolated_sequence.append(images[-1])
        return interpolated_sequence

    def create_video(self, frames, output_path, fps=30):
        """
        Create video from frames
        
        Args:
            frames (list): List of numpy arrays containing the frames
            output_path (str): Path to save the video
            fps (int): Frames per second
        """
        if not frames:
            raise ValueError("No frames to create video from")
        
        height, width = frames[0].shape[:2]
        print(f"Creating video with dimensions: {width}x{height}, {len(frames)} frames")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Try different codecs in order of preference
            codecs = ['mp4v', 'avc1', 'XVID']
            out = None
            
            for codec in codecs:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                    if out.isOpened():
                        print(f"Successfully opened video writer with codec: {codec}")
                        break
                except Exception as e:
                    print(f"Failed to use codec {codec}: {str(e)}")
            
            if not out or not out.isOpened():
                raise Exception("Failed to open video writer with any codec")
            
            # Verify first frame
            first_frame = frames[0]
            if first_frame.max() <= 1.0:
                first_frame = (first_frame * 255).astype(np.uint8)
            
            # Debug frame info
            print(f"Frame shape: {first_frame.shape}, dtype: {first_frame.dtype}, range: [{first_frame.min()}, {first_frame.max()}]")
            
            for i, frame in enumerate(frames):
                # Ensure frame is in correct format
                if frame.dtype != np.uint8:
                    frame = (frame * 255).astype(np.uint8)
                
                # Ensure frame is in BGR format for OpenCV
                if frame.shape[-1] == 3:  # If RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                success = out.write(frame)
                if not success:
                    print(f"Failed to write frame {i}")
            
            # Verify video was created
            if os.path.getsize(output_path) == 0:
                raise Exception("Output video file is empty")
            
        finally:
            if out:
                out.release()
            print(f"Video saved to {output_path}")

class RIFEInterpolator:
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = Model()
        # Initialize model weights here if needed
        # self.model.load_state_dict(torch.load('path/to/weights.pth'))
        self.model.eval()
        self.model.to_device()

    def _preprocess_image(self, img):
        """Convert image to torch tensor"""
        # Convert image to uint8 if it's float
        if img.dtype == np.float64 or img.dtype == np.float32:
            img = (img * 255).astype(np.uint8)
        
        # Ensure image has 3 channels (RGB)
        if len(img.shape) == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2RGB)
        elif img.shape[2] != 3:
            raise ValueError(f"Unexpected number of channels: {img.shape[2]}")
        
        img = torch.from_numpy(img).permute(2, 0, 1).float() / 255.0
        return img.unsqueeze(0).to(self.device)

    def _postprocess_image(self, tensor):
        """Convert torch tensor back to numpy array"""
        return (tensor.squeeze(0).permute(1, 2, 0).cpu().numpy() * 255).astype(np.uint8)

    def interpolate_frames(self, img1, img2, num_frames):
        """Generate intermediate frames between two images"""
        print(f"Input image shapes: {img1.shape}, {img2.shape}")
        
        # Preprocess images
        # Ensure images have the same size
        if img1.shape != img2.shape:
            height = min(img1.shape[0], img2.shape[0])
            width = min(img1.shape[1], img2.shape[1])
            # Make dimensions divisible by 32
            height = ((height - 1) // 32 + 1) * 32
            width = ((width - 1) // 32 + 1) * 32
            img1 = cv2.resize(img1, (width, height))
            img2 = cv2.resize(img2, (width, height))
        
        # Ensure images are in correct format
        if img1.dtype != np.uint8:
            img1 = (img1 * 255).astype(np.uint8)
        if img2.dtype != np.uint8:
            img2 = (img2 * 255).astype(np.uint8)
        
        img1_tensor = self._preprocess_image(img1)
        img2_tensor = self._preprocess_image(img2)
        
        print(f"Preprocessed tensor shapes: {img1_tensor.shape}, {img2_tensor.shape}")
        
        # Generate intermediate frames
        frames = []
        # Add first frame
        frames.append(img1)
        
        # Generate intermediate frames with non-linear timesteps
        for i in range(1, num_frames + 1):
            # Use smooth step function for better transitions
            x = i / (num_frames + 1)
            t = x * x * (3 - 2 * x)  # Smooth step function
            
            with torch.no_grad():
                middle = self.model.inference(img1_tensor, img2_tensor, timestep=t)
                middle = self._postprocess_image(middle)
                frames.append(middle)
        
        # Add last frame
        frames.append(img2)
        
        # Verify frames
        for i, frame in enumerate(frames):
            if frame is None:
                print(f"Frame {i} is None")
            else:
                print(f"Frame {i} shape: {frame.shape}, dtype: {frame.dtype}, range: [{frame.min()}, {frame.max()}]")
        
        return frames

    def create_video(self, frames, output_path, fps=30):
        """Create video from frames"""
        if not frames:
            raise ValueError("No frames to create video from")
        
        height, width = frames[0].shape[:2]
        print(f"Creating video with dimensions: {width}x{height}, {len(frames)} frames")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        try:
            # Try different codecs in order of preference
            codecs = ['mp4v', 'avc1', 'XVID']
            out = None
            
            for codec in codecs:
                try:
                    fourcc = cv2.VideoWriter_fourcc(*codec)
                    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
                    if out.isOpened():
                        print(f"Successfully opened video writer with codec: {codec}")
                        break
                except Exception as e:
                    print(f"Failed to use codec {codec}: {str(e)}")
            
            if not out or not out.isOpened():
                raise Exception("Failed to open video writer with any codec")
            
            # Verify first frame
            first_frame = frames[0]
            if first_frame.max() <= 1.0:
                first_frame = (first_frame * 255).astype(np.uint8)
            
            # Debug frame info
            print(f"Frame shape: {first_frame.shape}, dtype: {first_frame.dtype}, range: [{first_frame.min()}, {first_frame.max()}]")
            
            for i, frame in enumerate(frames):
                # Ensure frame is in correct format
                if frame.dtype != np.uint8:
                    frame = (frame * 255).astype(np.uint8)
                
                # Ensure frame is in BGR format for OpenCV
                if frame.shape[-1] == 3:  # If RGB
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                success = out.write(frame)
                if not success:
                    print(f"Failed to write frame {i}")
            
            # Verify video was created
            if os.path.getsize(output_path) == 0:
                raise Exception("Output video file is empty")
            
        finally:
            if out:
                out.release()
            print(f"Video saved to {output_path}") 