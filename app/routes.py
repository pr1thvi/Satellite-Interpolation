from flask import Blueprint, render_template, request, jsonify, send_file
from .wms_handler import WMSImageFetcher
from .interpolator import FrameInterpolator, RIFEInterpolator
from datetime import datetime, timedelta
import os
import uuid
import numpy as np

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    return render_template('index.html')

@main_bp.route('/generate-video', methods=['POST'])
def generate_video():
    """
    Generate interpolated video from satellite images.
    
    Request JSON:
    {
        "bbox": [minx, miny, maxx, maxy],
        "time_start": "YYYY-MM-DDThh:mm:ssZ",
        "time_end": "YYYY-MM-DDThh:mm:ssZ",
        "interval_minutes": 60
    }
    
    Returns:
        str: URL path to generated video
    """
    data = request.json
    
    # Initialize WMS fetcher
    wms_fetcher = WMSImageFetcher(
        wms_url='https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
        layer_name='MODIS_Terra_CorrectedReflectance_TrueColor'
    )
    
    # Get images
    images = wms_fetcher.get_image_sequence(
        bbox=data['bbox'],
        size=(800, 600),  # Adjust size as needed
        time_start=datetime.fromisoformat(data['time_start'].replace('Z', '+00:00')),
        time_end=datetime.fromisoformat(data['time_end'].replace('Z', '+00:00')),
        interval_minutes=60  # Adjust interval as needed
    )
    
    # Initialize interpolator
    interpolator = FrameInterpolator()
    
    # Generate interpolated frames
    interpolated_frames = interpolator.interpolate_sequence(images)
    
    # Create video
    output_path = os.path.join('app', 'static', 'videos', 'output.mp4')
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    interpolator.create_video(interpolated_frames, output_path)
    
    return '/static/videos/output.mp4'

@main_bp.route('/generate-daily-video', methods=['POST'])
def generate_daily_video():
    """
    Generate interpolated video from all satellite images for a specific day.
    
    Request JSON:
    {
        "bbox": [minx, miny, maxx, maxy],
        "date": "YYYY-MM-DD",
        "fps": 10
    }
    
    Returns:
        str: URL path to generated video
    """
    data = request.json
    
    # Initialize WMS fetcher
    wms_fetcher = WMSImageFetcher(
        wms_url='https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
        layer_name='MODIS_Terra_CorrectedReflectance_TrueColor'
    )
    
    # Parse the date
    selected_date = data['date']  # Pass the date string directly
    
    # Generate a unique filename for the video
    date_str = selected_date.replace('-', '')
    video_filename = f"daily_video_{date_str}_{uuid.uuid4().hex[:8]}.mp4"
    video_path = os.path.join('app', 'static', 'videos', video_filename)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    # Generate the daily video
    wms_fetcher.get_daily_video(
        bbox=data['bbox'],
        size=(800, 600),  # Adjust size as needed
        date=selected_date,
        output_path=video_path,
        fps=data.get('fps', 10)
    )
    
    # Return the URL to the video
    video_url = f"/static/videos/{video_filename}"
    return jsonify({"video_url": video_url})

@main_bp.route('/videos/<filename>')
def serve_video(filename):
    """Serve the generated video file"""
    return send_file(
        os.path.join('app', 'static', 'videos', filename),
        mimetype='video/mp4',
        as_attachment=False
    )

@main_bp.route('/generate-multi-day-video', methods=['POST'])
def generate_multi_day_video():
    """
    Generate interpolated video from satellite images across multiple days.
    
    Request JSON:
    {
        "bbox": [minx, miny, maxx, maxy],
        "start_date": "YYYY-MM-DD",
        "end_date": "YYYY-MM-DD",
        "fps": 10
    }
    
    Returns:
        str: URL path to generated video
    """
    data = request.json
    
    # Initialize WMS fetcher
    wms_fetcher = WMSImageFetcher(
        wms_url='https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
        layer_name='MODIS_Terra_CorrectedReflectance_TrueColor'
    )
    
    # Generate a unique filename for the video
    start_date_str = data['start_date'].replace('-', '')
    end_date_str = data['end_date'].replace('-', '')
    video_filename = f"multi_day_video_{start_date_str}_{end_date_str}_{uuid.uuid4().hex[:8]}.mp4"
    video_path = os.path.join('app', 'static', 'videos', video_filename)
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    # Generate the multi-day video
    wms_fetcher.get_multi_day_video(
        bbox=data['bbox'],
        size=(800, 600),  # Adjust size as needed
        start_date=data['start_date'],
        end_date=data['end_date'],
        output_path=video_path,
        fps=data.get('fps', 10)
    )
    
    # Return the URL to the video
    video_url = f"/static/videos/{video_filename}"
    return jsonify({"video_url": video_url})

@main_bp.route('/generate-rife-animation', methods=['POST'])
def generate_rife_animation():
    """Generate smooth animation using RIFE interpolation"""
    data = request.json
    
    # Initialize WMS fetcher and RIFE interpolator
    wms_fetcher = WMSImageFetcher(
        wms_url='https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi',
        layer_name='VIIRS_SNPP_CorrectedReflectance_TrueColor'
    )
    
    interpolator = RIFEInterpolator()
    
    # Get start and end dates
    start_date = datetime.strptime(data['start_date'], '%Y-%m-%d')
    end_date = datetime.strptime(data['end_date'], '%Y-%m-%d')
    
    # Fetch satellite images
    images = wms_fetcher.get_image_sequence(
        bbox=data['bbox'],
        size=data['size'],
        time_start=start_date,
        time_end=end_date,
        interval_minutes=1440  # Daily images
    )
    
    # Ensure images are in correct format
    processed_images = []
    for img in images:
        if img is not None:
            try:
                if img.dtype == np.float64 or img.dtype == np.float32:
                    img = (img * 255).astype(np.uint8)
                processed_images.append(img)
            except Exception as e:
                print(f"Error processing image: {e}")
                continue
    
    if not processed_images:
        return jsonify({"error": "No valid images found for the selected dates"}), 400
    
    # Generate interpolated frames between each pair of images
    all_frames = []
    frames_between = 15  # Increased number of frames for smoother transitions
    
    print(f"Processing {len(processed_images)} images")
    
    for i in range(len(processed_images) - 1):
        print(f"Interpolating between frames {i} and {i+1}")
        frames = interpolator.interpolate_frames(
            processed_images[i], 
            processed_images[i + 1],
            frames_between
        )
        if not frames:
            print(f"No frames generated for pair {i}")
            continue
        all_frames.extend(frames[:-1])  # Exclude last frame except for final pair
    all_frames.append(processed_images[-1])  # Add final frame
    
    if not all_frames:
        return jsonify({"error": "Failed to generate any frames"}), 400
    
    print(f"Total frames generated: {len(all_frames)}")
    
    # Generate unique filename
    video_filename = f"rife_animation_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.mp4"
    video_path = os.path.join('app', 'static', 'videos', video_filename)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(video_path), exist_ok=True)
    
    # Create video with higher FPS
    interpolator.create_video(all_frames, video_path, fps=data.get('fps', 60))
    
    # Return video URL
    return jsonify({"video_url": f"/static/videos/{video_filename}"})

    video_path = None
    try:
        # ... existing code ...
        
        video_filename = f"rife_animation_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}.mp4"
        video_path = os.path.join('app', 'static', 'videos', video_filename)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(video_path), exist_ok=True)
        
        # Create video
        interpolator.create_video(all_frames, video_path, fps=data.get('fps', 30))
        
        # Return video URL
        return jsonify({"video_url": f"/static/videos/{video_filename}"})
    except Exception as e:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        return jsonify({"error": str(e)}), 500 