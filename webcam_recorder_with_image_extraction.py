#!/usr/bin/env python3
"""
4K Webcam Recorder with Automatic Image Extraction
- Records video with precise timing
- Automatically extracts sample images from video after recording
- Saves images in organized folders
"""

import cv2
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import threading
import os
from datetime import datetime
import queue
import time


# ==================== CONFIGURATION ====================
WEBCAM_PORT = 2  # Your 4K webcam port
OUTPUT_FOLDER = "Recordings"
IMAGES_FOLDER = "Images"  # Main folder for extracted images

# Camera specifications
CAMERA_WIDTH = 3840       # 4K UHD width
CAMERA_HEIGHT = 2160      # 4K UHD height
VIDEO_FPS = 31.0          # Native frame rate

# Video codec
VIDEO_CODEC = 'XVID'      # XVID has reliable FPS control

# UI Preview settings
PREVIEW_WIDTH = 960       # 1/4 of 4K width
PREVIEW_HEIGHT = 540      # 1/4 of 4K height

# Buffer settings
BUFFER_SIZE = 3

# ========== IMAGE EXTRACTION SETTINGS ==========
# ADJUSTABLE: Number of images to extract from each video
NUM_IMAGES_TO_EXTRACT = 100  # Change this number as needed (e.g., 5, 10, 20, 50, 100)

# Image extraction method
# Options: 'evenly_spaced' or 'interval'
EXTRACTION_METHOD = 'evenly_spaced'  # Extract images evenly throughout video

# If using 'interval' method, extract one image every N frames
FRAME_INTERVAL = 30  # Extract image every 30 frames (used only if method is 'interval')

# Image quality (0-100, higher = better quality but larger files)
IMAGE_QUALITY = 95  # High quality for full resolution images
# =======================================================


class WebcamRecorderWithExtraction:
    """
    Webcam recorder with automatic image extraction from recorded videos.
    """
    
    def __init__(self, window):
        self.window = window
        self.window.title("4K Webcam Recorder + Image Extractor")
        self.window.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Create output directories
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        os.makedirs(IMAGES_FOLDER, exist_ok=True)
        
        # Camera and recording state
        self.camera = None
        self.is_recording = False
        self.video_writer = None
        self.current_video_path = None
        self.current_video_timestamp = None
        
        # Threading components
        self.frame_queue = queue.Queue(maxsize=BUFFER_SIZE)
        self.running = True
        self.camera_lock = threading.Lock()
        
        # Frame timing control
        self.recording_start_time = None
        self.frames_recorded = 0
        
        # Camera properties
        self.full_width = None
        self.full_height = None
        self.actual_fps = None
        
        # Setup UI
        self.setup_ui()
        
        # Initialize camera
        self.initialize_camera()
        
        # Start preview thread
        self.preview_thread = threading.Thread(target=self.capture_frames, daemon=True)
        self.preview_thread.start()
        
        # Start UI update loop
        self.update_preview()
    
    
    def setup_ui(self):
        """Create the user interface components."""
        
        main_frame = ttk.Frame(self.window, padding="15")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="4K Webcam Recorder + Auto Image Extractor",
            font=("Arial", 14, "bold")
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=5)
        
        # Video preview label
        self.video_label = ttk.Label(main_frame, relief="solid", borderwidth=2)
        self.video_label.grid(row=1, column=0, columnspan=2, pady=10)
        
        # Camera info
        self.info_label = ttk.Label(
            main_frame,
            text="Camera: Initializing...",
            font=("Arial", 9),
            foreground="blue"
        )
        self.info_label.grid(row=2, column=0, columnspan=2, pady=2)
        
        # Extraction info
        extraction_info = f"Auto-Extract: {NUM_IMAGES_TO_EXTRACT} images per video"
        self.extraction_label = ttk.Label(
            main_frame,
            text=extraction_info,
            font=("Arial", 9),
            foreground="green"
        )
        self.extraction_label.grid(row=3, column=0, columnspan=2, pady=2)
        
        # Status label
        self.status_label = ttk.Label(
            main_frame, 
            text="Status: Initializing...", 
            font=("Arial", 10)
        )
        self.status_label.grid(row=4, column=0, columnspan=2, pady=5)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.record_button = ttk.Button(
            button_frame,
            text="⏺ Start Recording",
            command=self.toggle_recording,
            width=20
        )
        self.record_button.grid(row=0, column=0, padx=5)
        
        # Recording indicator
        self.indicator_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 12, "bold"),
            foreground="red"
        )
        self.indicator_label.grid(row=6, column=0, columnspan=2)
        
        # Stats label
        self.stats_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 9),
            foreground="gray"
        )
        self.stats_label.grid(row=7, column=0, columnspan=2, pady=5)
        
        # Progress label (for image extraction)
        self.progress_label = ttk.Label(
            main_frame,
            text="",
            font=("Arial", 9, "bold"),
            foreground="orange"
        )
        self.progress_label.grid(row=8, column=0, columnspan=2, pady=5)
    
    
    def initialize_camera(self):
        """Initialize the 4K webcam with optimized settings."""
        try:
            self.camera = cv2.VideoCapture(WEBCAM_PORT)
            
            if not self.camera.isOpened():
                raise Exception(f"Cannot open webcam at port {WEBCAM_PORT}")
            
            # Set format to MJPG for capture quality
            self.camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M','J','P','G'))
            
            # Set 4K resolution
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            
            # Set FPS
            self.camera.set(cv2.CAP_PROP_FPS, VIDEO_FPS)
            
            # Reduce buffer lag
            self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Read actual settings
            self.full_width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.full_height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            camera_info = f"Camera: {self.full_width}×{self.full_height} @ {self.actual_fps:.1f} FPS"
            self.info_label.configure(text=camera_info)
            
            print(f"✓ Camera initialized: {self.full_width}×{self.full_height} @ {self.actual_fps} FPS")
            self.update_status(f"Ready - 4K @ {self.actual_fps:.1f} FPS")
            
        except Exception as e:
            print(f"Camera error: {e}")
            self.update_status(f"Error: {e}")
    
    
    def capture_frames(self):
        """
        Capture frames with PRECISE timing control.
        """
        target_frame_time = 1.0 / VIDEO_FPS
        
        while self.running:
            if self.camera and self.camera.isOpened():
                frame_start = time.time()
                
                ret, frame = self.camera.read()
                
                if ret:
                    # Put frame in queue for preview
                    if not self.frame_queue.full():
                        try:
                            self.frame_queue.put_nowait(frame.copy())
                        except queue.Full:
                            pass
                    
                    # If recording, write frame
                    if self.is_recording and self.video_writer:
                        with self.camera_lock:
                            self.video_writer.write(frame)
                            self.frames_recorded += 1
                            
                            # Track actual recording FPS
                            if self.frames_recorded % 31 == 0:  # Every second
                                elapsed = time.time() - self.recording_start_time
                                actual_fps = self.frames_recorded / elapsed
                                self.window.after(0, lambda: self.stats_label.configure(
                                    text=f"Recording: {self.frames_recorded} frames | Actual FPS: {actual_fps:.2f}"
                                ))
                
                # Precise sleep to maintain exact FPS
                frame_end = time.time()
                frame_duration = frame_end - frame_start
                sleep_time = target_frame_time - frame_duration
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                time.sleep(0.1)
    
    
    def update_preview(self):
        """Update UI preview."""
        try:
            if not self.frame_queue.empty():
                frame = self.frame_queue.get_nowait()
                
                # Resize for preview
                preview_frame = cv2.resize(
                    frame, 
                    (PREVIEW_WIDTH, PREVIEW_HEIGHT),
                    interpolation=cv2.INTER_AREA
                )
                
                # Convert BGR to RGB
                rgb_frame = cv2.cvtColor(preview_frame, cv2.COLOR_BGR2RGB)
                
                # Convert to PhotoImage
                img = Image.fromarray(rgb_frame)
                imgtk = ImageTk.PhotoImage(image=img)
                
                # Update label
                self.video_label.imgtk = imgtk
                self.video_label.configure(image=imgtk)
        
        except queue.Empty:
            pass
        except Exception as e:
            print(f"Preview error: {e}")
        
        if self.running:
            self.window.after(16, self.update_preview)
    
    
    def toggle_recording(self):
        """Start or stop recording."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()
    
    
    def start_recording(self):
        """Start recording with PRECISE FPS control."""
        if not self.camera or not self.camera.isOpened():
            self.update_status("Error: Camera not available")
            return
        
        # Generate filename and timestamp
        self.current_video_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{self.current_video_timestamp}.avi"
        self.current_video_path = os.path.join(OUTPUT_FOLDER, filename)
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
        
        with self.camera_lock:
            self.video_writer = cv2.VideoWriter(
                self.current_video_path,
                fourcc,
                VIDEO_FPS,
                (self.full_width, self.full_height),
                True
            )
        
        if not self.video_writer.isOpened():
            self.update_status("Error: Could not create video file")
            return
        
        # Reset timing counters
        self.recording_start_time = time.time()
        self.frames_recorded = 0
        
        # Update state
        self.is_recording = True
        
        # Update UI
        self.record_button.configure(text="⏹ Stop Recording")
        self.indicator_label.configure(text="● RECORDING")
        self.update_status(f"Recording 4K @ {VIDEO_FPS} FPS")
        
        print(f"✓ Recording started: {filename}")
    
    
    def stop_recording(self):
        """Stop recording and extract images."""
        if not self.is_recording:
            return
        
        # Calculate statistics
        elapsed = time.time() - self.recording_start_time
        actual_fps = self.frames_recorded / elapsed if elapsed > 0 else 0
        
        # Update state
        self.is_recording = False
        
        # Release video writer
        with self.camera_lock:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
        
        # Update UI
        self.record_button.configure(text="⏺ Start Recording")
        self.indicator_label.configure(text="")
        self.update_status(f"Recording saved - Extracting images...")
        self.stats_label.configure(
            text=f"Video: {elapsed:.1f}s | {self.frames_recorded} frames | Avg FPS: {actual_fps:.2f}"
        )
        
        print(f"✓ Recording stopped")
        print(f"  Duration: {elapsed:.1f} seconds")
        print(f"  Frames: {self.frames_recorded}")
        print(f"  Average FPS: {actual_fps:.2f}")
        
        # Extract images from video (in separate thread to avoid UI freeze)
        extraction_thread = threading.Thread(
            target=self.extract_images_from_video,
            args=(self.current_video_path, self.current_video_timestamp),
            daemon=True
        )
        extraction_thread.start()
    
    
    def extract_images_from_video(self, video_path, timestamp):
        """
        Extract sample images from the recorded video.
        Saves images in: Images/video_timestamp/image_001.jpg, image_002.jpg, etc.
        """
        print(f"\n{'='*60}")
        print(f"Extracting {NUM_IMAGES_TO_EXTRACT} images from video...")
        print(f"{'='*60}")
        
        # Update UI
        self.window.after(0, lambda: self.progress_label.configure(
            text=f"⏳ Extracting images..."
        ))
        
        try:
            # Create folder for this video's images
            images_output_folder = os.path.join(IMAGES_FOLDER, f"video_{timestamp}")
            os.makedirs(images_output_folder, exist_ok=True)
            
            # Open the video file
            video_capture = cv2.VideoCapture(video_path)
            
            if not video_capture.isOpened():
                print(f"✗ Error: Could not open video file: {video_path}")
                self.window.after(0, lambda: self.progress_label.configure(text="✗ Error opening video"))
                return
            
            # Get video properties
            total_frames = int(video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = video_capture.get(cv2.CAP_PROP_FPS)
            
            print(f"Video info:")
            print(f"  Total frames: {total_frames}")
            print(f"  FPS: {video_fps}")
            
            # Calculate which frames to extract
            if EXTRACTION_METHOD == 'evenly_spaced':
                # Extract frames evenly spaced throughout the video
                if NUM_IMAGES_TO_EXTRACT >= total_frames:
                    # Extract all frames if requested more than available
                    frame_indices = list(range(total_frames))
                else:
                    # Calculate evenly spaced frame indices
                    frame_indices = [int(i * total_frames / NUM_IMAGES_TO_EXTRACT) 
                                   for i in range(NUM_IMAGES_TO_EXTRACT)]
            else:  # interval method
                # Extract one frame every N frames
                frame_indices = list(range(0, total_frames, FRAME_INTERVAL))[:NUM_IMAGES_TO_EXTRACT]
            
            num_images = len(frame_indices)
            print(f"Extracting {num_images} images at frame indices: {frame_indices[:5]}{'...' if len(frame_indices) > 5 else ''}")
            
            # Extract frames
            images_extracted = 0
            for idx, frame_number in enumerate(frame_indices):
                # Set video to specific frame
                video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
                ret, frame = video_capture.read()
                
                if ret:
                    # Save image with sequential numbering (001, 002, 003, etc.)
                    image_filename = f"image_{idx+1:03d}.jpg"
                    image_path = os.path.join(images_output_folder, image_filename)
                    
                    # Save with high quality
                    cv2.imwrite(image_path, frame, [cv2.IMWRITE_JPEG_QUALITY, IMAGE_QUALITY])
                    images_extracted += 1
                    
                    # Update progress
                    progress = (idx + 1) / num_images * 100
                    self.window.after(0, lambda p=progress, n=idx+1: self.progress_label.configure(
                        text=f"⏳ Extracting images: {n}/{num_images} ({p:.0f}%)"
                    ))
                    
                    print(f"  ✓ Extracted: {image_filename} (frame {frame_number})")
                else:
                    print(f"  ✗ Failed to read frame {frame_number}")
            
            # Release video
            video_capture.release()
            
            # Final summary
            print(f"\n{'='*60}")
            print(f"✓ Image extraction complete!")
            print(f"  Images extracted: {images_extracted}/{num_images}")
            print(f"  Saved to: {images_output_folder}")
            print(f"  Resolution: {self.full_width}×{self.full_height} (Full 4K)")
            print(f"{'='*60}\n")
            
            # Update UI
            self.window.after(0, lambda: self.progress_label.configure(
                text=f"✓ Extracted {images_extracted} images to: Images/video_{timestamp}/"
            ))
            self.window.after(0, lambda: self.update_status(
                f"Complete - Video saved & {images_extracted} images extracted"
            ))
            
        except Exception as e:
            print(f"✗ Error during image extraction: {e}")
            self.window.after(0, lambda: self.progress_label.configure(
                text=f"✗ Error: {str(e)}"
            ))
    
    
    def update_status(self, message):
        """Update status label."""
        self.status_label.configure(text=f"Status: {message}")
    
    
    def on_closing(self):
        """Clean up resources."""
        print("\nShutting down...")
        
        if self.is_recording:
            self.stop_recording()
            time.sleep(1)  # Give time for extraction to start
        
        self.running = False
        
        if self.camera:
            self.camera.release()
            print("✓ Camera released")
        
        if self.preview_thread and self.preview_thread.is_alive():
            self.preview_thread.join(timeout=1.0)
        
        self.window.destroy()
        print("✓ Closed")


# ==================== MAIN ====================
def main():
    """Application entry point."""
    print("=" * 70)
    print("4K Webcam Recorder with Automatic Image Extraction")
    print("=" * 70)
    print(f"Configuration:")
    print(f"  • Video Resolution: {CAMERA_WIDTH}×{CAMERA_HEIGHT} (4K)")
    print(f"  • Video FPS: {VIDEO_FPS}")
    print(f"  • Images to Extract: {NUM_IMAGES_TO_EXTRACT} per video")
    print(f"  • Extraction Method: {EXTRACTION_METHOD}")
    print(f"  • Image Quality: {IMAGE_QUALITY}%")
    print(f"  • Output Folders:")
    print(f"    - Videos: {OUTPUT_FOLDER}/")
    print(f"    - Images: {IMAGES_FOLDER}/video_TIMESTAMP/")
    print("=" * 70)
    
    root = tk.Tk()
    app = WebcamRecorderWithExtraction(root)
    root.mainloop()


if __name__ == "__main__":
    main()
