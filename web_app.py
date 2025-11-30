import streamlit as st
from PIL import Image
import os
from pathlib import Path
import secrets
import hashlib
from datetime import datetime

# Security configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.gif', '.bmp']

# Session management
if 'session_token' not in st.session_state:
    st.session_state.session_token = secrets.token_urlsafe(32)
    st.session_state.user_id = secrets.token_hex(8)
    st.session_state.created = datetime.now()

if 'images' not in st.session_state:
    st.session_state.images = []
    st.session_state.current_index = 0

def validate_file_security(file):
    """Validate uploaded file for security"""
    # Check file extension
    file_ext = Path(file.name).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        return False, f"File type {file_ext} not allowed"
    
    # Check file size
    if file.size > MAX_FILE_SIZE:
        return False, f"File too large ({file.size / 1024 / 1024:.1f}MB > 50MB)"
    
    return True, "File is secure"

def main():
    # Modern styling
    st.set_page_config(
        page_title="Modern Image Viewer",
        page_icon="🖼️",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Custom CSS for modern look
    st.markdown("""
        <style>
        .main {
            background-color: #1a1a2e;
            color: #eee;
        }
        .stButton>button {
            background-color: #00d4ff;
            color: white;
            border-radius: 8px;
            padding: 10px 20px;
            border: none;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #00b8e6;
        }
        h1, h2, h3 {
            color: #00d4ff;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.title("🖼️ Modern Image Viewer")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("🎛️ Controls")
        
        # File upload
        uploaded_files = st.file_uploader(
            "📤 Upload Images",
            type=['png', 'jpg', 'jpeg', 'gif', 'bmp'],
            accept_multiple_files=True
        )
        
        if uploaded_files:
            valid_images = []
            for file in uploaded_files:
                is_valid, message = validate_file_security(file)
                if is_valid:
                    valid_images.append(file)
                else:
                    st.warning(f"Skipped {file.name}: {message}")
            
            if valid_images:
                st.session_state.images = valid_images
                st.session_state.current_index = 0
                st.success(f"✓ Loaded {len(valid_images)} images")
        
        st.markdown("---")
        
        # Security info
        st.subheader("🔒 Security")
        st.text(f"Session: {st.session_state.session_token[:16]}...")
        st.text(f"User ID: {st.session_state.user_id}")
        
        st.markdown("---")
        
        # Navigation
        if st.session_state.images:
            st.subheader("🧭 Navigation")
            
            # Image counter
            st.info(f"Image {st.session_state.current_index + 1} / {len(st.session_state.images)}")
            
            # Slider
            new_index = st.slider(
                "Position",
                0,
                len(st.session_state.images) - 1,
                st.session_state.current_index,
                key="image_slider"
            )
            st.session_state.current_index = new_index
            
            # Buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("◀ Previous"):
                    if st.session_state.current_index > 0:
                        st.session_state.current_index -= 1
                        st.rerun()
            
            with col2:
                if st.button("Next ▶"):
                    if st.session_state.current_index < len(st.session_state.images) - 1:
                        st.session_state.current_index += 1
                        st.rerun()
            
            col3, col4 = st.columns(2)
            with col3:
                if st.button("⏮️ First"):
                    st.session_state.current_index = 0
                    st.rerun()
            
            with col4:
                if st.button("Last ⏭️"):
                    st.session_state.current_index = len(st.session_state.images) - 1
                    st.rerun()
            
            if st.button("🆕 New Session"):
                st.session_state.images = []
                st.session_state.current_index = 0
                st.session_state.session_token = secrets.token_urlsafe(32)
                st.rerun()
    
    # Main content
    if st.session_state.images:
        # Display current image
        current_file = st.session_state.images[st.session_state.current_index]
        
        try:
            image = Image.open(current_file)
            
            # Display image
            col1, col2, col3 = st.columns([1, 3, 1])
            with col2:
                st.image(image, caption=current_file.name, use_column_width=True)
                
                # Image info
                st.markdown(f"""
                    **📄 Filename:** {current_file.name}  
                    **📏 Size:** {current_file.size / 1024:.1f} KB  
                    **🖼️ Dimensions:** {image.size[0]} × {image.size[1]}
                """)
        
        except Exception as e:
            st.error(f"Error loading image: {e}")
    
    else:
        # Welcome screen
        st.markdown("""
            <div style='text-align: center; padding: 50px;'>
                <h2>👋 Welcome to Modern Image Viewer</h2>
                <p style='font-size: 18px;'>Upload images using the sidebar to get started</p>
                <br>
                <p>✓ Secure file validation</p>
                <p>✓ Fast navigation</p>
                <p>✓ Modern interface</p>
            </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()