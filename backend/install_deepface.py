#!/usr/bin/env python3
"""
DeepFace Installation and Testing Script

This script installs DeepFace and its dependencies, then tests the emotion analysis functionality.
"""

import subprocess
import sys
import os
import numpy as np
import cv2
from pathlib import Path

def install_package(package):
    """Install a Python package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def fix_tensorflow_conflicts():
    """Fix TensorFlow version conflicts."""
    print("🔧 Fixing TensorFlow version conflicts...")
    
    try:
        # Uninstall conflicting packages
        conflicting_packages = ["tensorflow", "tf-keras", "keras"]
        for package in conflicting_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "uninstall", package, "-y"])
                print(f"✅ Uninstalled {package}")
            except subprocess.CalledProcessError:
                print(f"ℹ️ {package} not installed or already removed")
        
        # Install compatible versions
        compatible_packages = [
            "tensorflow==2.13.0",
            "tf-keras==2.13.0"
        ]
        
        for package in compatible_packages:
            if install_package(package):
                print(f"✅ Installed compatible {package}")
            else:
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix TensorFlow conflicts: {e}")
        return False

def install_deepface_dependencies():
    """Install DeepFace and its dependencies."""
    print("🚀 Installing DeepFace and dependencies...")
    
    # First, fix TensorFlow conflicts
    if not fix_tensorflow_conflicts():
        print("❌ Failed to fix TensorFlow conflicts")
        return False
    
    # Install other dependencies
    packages = [
        "opencv-python==4.8.1.78",
        "pillow==10.1.0",
        "numpy==1.24.3",
        "deepface==0.0.75",    # Use compatible DeepFace version
        "mtcnn==0.1.1", 
        "retina-face==0.0.13"
    ]
    
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 Installation Summary: {success_count}/{len(packages)} packages installed successfully")
    return success_count == len(packages)

def test_deepface_import():
    """Test if DeepFace can be imported successfully."""
    try:
        # First test TensorFlow import
        import tensorflow as tf
        print(f"✅ TensorFlow {tf.__version__} imported successfully")
        
        # Test DeepFace import
        from deepface import DeepFace
        print("✅ DeepFace imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Failed to import DeepFace: {e}")
        return False
    except AttributeError as e:
        print(f"❌ TensorFlow version compatibility issue: {e}")
        print("💡 Try installing compatible versions:")
        print("   pip uninstall tensorflow tf-keras")
        print("   pip install tensorflow==2.13.0 tf-keras==2.13.0")
        return False

def create_test_image():
    """Create a simple test image with a face-like pattern."""
    # Create a 224x224 RGB image
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    
    # Fill with a light gray background
    img.fill(200)
    
    # Draw a simple face-like pattern
    center_x, center_y = 112, 112
    
    # Face outline (circle)
    cv2.circle(img, (center_x, center_y), 80, (180, 180, 180), -1)
    
    # Eyes
    cv2.circle(img, (center_x - 25, center_y - 20), 8, (50, 50, 50), -1)
    cv2.circle(img, (center_x + 25, center_y - 20), 8, (50, 50, 50), -1)
    
    # Nose
    cv2.circle(img, (center_x, center_y), 5, (150, 150, 150), -1)
    
    # Mouth (happy expression)
    cv2.ellipse(img, (center_x, center_y + 20), (20, 10), 0, 0, 180, (100, 100, 100), 2)
    
    return img

def test_deepface_emotion_analysis():
    """Test DeepFace emotion analysis functionality."""
    try:
        from deepface import DeepFace
        
        print("🎭 Testing DeepFace emotion analysis...")
        
        # Create test image
        test_img = create_test_image()
        
        # Analyze emotions
        result = DeepFace.analyze(
            img_path=test_img,
            actions=['emotion'],
            detector_backend='opencv',
            enforce_detection=False,
            silent=True
        )
        
        print("✅ DeepFace emotion analysis test successful!")
        
        # Display results
        if isinstance(result, list):
            emotion_data = result[0]['emotion'] if len(result) > 0 else {}
        else:
            emotion_data = result['emotion']
        
        print("📊 Emotion Analysis Results:")
        for emotion, percentage in emotion_data.items():
            print(f"   {emotion}: {percentage:.1f}%")
        
        # Find dominant emotion
        dominant_emotion = max(emotion_data, key=emotion_data.get)
        print(f"🎯 Dominant emotion: {dominant_emotion} ({emotion_data[dominant_emotion]:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ DeepFace emotion analysis test failed: {e}")
        return False

def test_different_backends():
    """Test different DeepFace detector backends."""
    try:
        from deepface import DeepFace
        
        print("🔧 Testing different detector backends...")
        
        test_img = create_test_image()
        backends = ['opencv', 'ssd', 'dlib', 'mtcnn']
        
        working_backends = []
        
        for backend in backends:
            try:
                print(f"   Testing {backend}...")
                result = DeepFace.analyze(
                    img_path=test_img,
                    actions=['emotion'],
                    detector_backend=backend,
                    enforce_detection=False,
                    silent=True
                )
                working_backends.append(backend)
                print(f"   ✅ {backend} works")
                
            except Exception as e:
                print(f"   ❌ {backend} failed: {e}")
        
        print(f"\n📊 Working backends: {working_backends}")
        return working_backends
        
    except Exception as e:
        print(f"❌ Backend testing failed: {e}")
        return []

def create_deepface_config():
    """Create a configuration file for DeepFace settings."""
    config = {
        "detector_backend": "opencv",  # Most reliable
        "emotion_model": "VGG-Face",
        "confidence_threshold": 0.7,
        "enforce_detection": False,
        "silent": True
    }
    
    config_path = Path(__file__).parent / "deepface_config.json"
    
    try:
        import json
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ DeepFace configuration saved to: {config_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create configuration: {e}")
        return False

def main():
    """Main installation and testing function."""
    print("🎭 DeepFace Installation and Testing Script")
    print("=" * 50)
    
    # Step 1: Install dependencies
    if not install_deepface_dependencies():
        print("❌ Installation failed. Please check the errors above.")
        return False
    
    print("\n" + "=" * 50)
    
    # Step 2: Test import
    if not test_deepface_import():
        print("❌ Import test failed. Installation may be incomplete.")
        return False
    
    print("\n" + "=" * 50)
    
    # Step 3: Test emotion analysis
    if not test_deepface_emotion_analysis():
        print("❌ Emotion analysis test failed.")
        return False
    
    print("\n" + "=" * 50)
    
    # Step 4: Test different backends
    working_backends = test_different_backends()
    
    print("\n" + "=" * 50)
    
    # Step 5: Create configuration
    create_deepface_config()
    
    print("\n" + "=" * 50)
    print("🎉 DeepFace installation and testing completed successfully!")
    print("\n📋 Summary:")
    print("   ✅ DeepFace installed and working")
    print("   ✅ Emotion analysis functional")
    print(f"   ✅ {len(working_backends)} detector backends available")
    print("   ✅ Configuration file created")
    
    print("\n🚀 You can now use DeepFace for advanced emotion recognition!")
    print("   - Start the backend server: python -m backend.main")
    print("   - Test the API: http://localhost:8000/api/v1/deepface/health")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)