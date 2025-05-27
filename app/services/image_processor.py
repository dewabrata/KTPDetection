"""
Image Processor Service
=======================

Service untuk memproses dan validasi gambar yang diupload
"""

from PIL import Image, ImageEnhance, ImageFilter
import io
import os
from typing import Tuple, Optional
from fastapi import UploadFile, HTTPException
from decouple import config
import cv2
import numpy as np

# Try to import magic, make it optional
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    print("Warning: python-magic not available, using basic file validation")

class ImageProcessor:
    """Service untuk memproses gambar KTP"""
    
    def __init__(self):
        """Initialize image processor"""
        self.allowed_extensions = config("ALLOWED_EXTENSIONS", default="jpg,jpeg,png,webp,bmp").split(",")
        self.max_file_size = config("MAX_FILE_SIZE", default=10485760, cast=int)  # 10MB
        self.upload_dir = config("UPLOAD_DIR", default="uploads/")
        
        # Ensure upload directory exists
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def process_upload(self, file: UploadFile) -> Image.Image:
        """
        Process uploaded file dan convert ke PIL Image
        
        Args:
            file: FastAPI UploadFile object
            
        Returns:
            Image.Image: Processed PIL Image
            
        Raises:
            HTTPException: Jika file tidak valid
        """
        # Validate file
        await self._validate_file(file)
        
        # Read file content
        content = await file.read()
        
        # Convert to PIL Image
        image = Image.open(io.BytesIO(content))
        
        # Basic processing
        processed_image = self._process_image(image)
        
        # Reset file pointer
        await file.seek(0)
        
        return processed_image
    
    async def _validate_file(self, file: UploadFile) -> None:
        """
        Validate uploaded file
        
        Args:
            file: FastAPI UploadFile object
            
        Raises:
            HTTPException: Jika file tidak valid
        """
        # Check if file exists
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="Tidak ada file yang diupload")
        
        # Check file size
        content = await file.read()
        if len(content) > self.max_file_size:
            raise HTTPException(
                status_code=413, 
                detail=f"File terlalu besar. Maksimal {self.max_file_size / 1024 / 1024:.1f}MB"
            )
        
        # Check file extension
        file_ext = file.filename.split('.')[-1].lower()
        if file_ext not in self.allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Format file tidak didukung. Gunakan: {', '.join(self.allowed_extensions)}"
            )
        
        # Check file type using python-magic (if available)
        if MAGIC_AVAILABLE:
            try:
                file_type = magic.from_buffer(content[:1024], mime=True)
                if not file_type.startswith('image/'):
                    raise HTTPException(
                        status_code=400,
                        detail="File bukan gambar yang valid"
                    )
            except Exception:
                # If magic fails, continue with basic validation
                print("Warning: Magic file type detection failed, using basic validation")
        
        # Reset file pointer
        await file.seek(0)
    
    def _process_image(self, image: Image.Image) -> Image.Image:
        """
        Process image untuk meningkatkan quality untuk OCR
        
        Args:
            image: Original PIL Image
            
        Returns:
            Image.Image: Processed image
        """
        # Convert to RGB if necessary
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Enhance image untuk OCR yang lebih baik
        enhanced_image = self._enhance_for_ocr(image)
        
        # Resize jika terlalu kecil atau terlalu besar
        resized_image = self._resize_optimal(enhanced_image)
        
        return resized_image
    
    def _enhance_for_ocr(self, image: Image.Image) -> Image.Image:
        """
        Enhance image untuk OCR yang lebih baik
        
        Args:
            image: Original image
            
        Returns:
            Image.Image: Enhanced image
        """
        try:
            # Convert PIL to OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            
            # Apply denoising
            denoised = cv2.fastNlMeansDenoisingColored(cv_image, None, 10, 10, 7, 21)
            
            # Improve contrast using CLAHE
            lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            # Convert back to PIL
            enhanced_pil = Image.fromarray(cv2.cvtColor(enhanced, cv2.COLOR_BGR2RGB))
            
            return enhanced_pil
            
        except Exception:
            # If OpenCV processing fails, use basic PIL enhancement
            return self._basic_enhance(image)
    
    def _basic_enhance(self, image: Image.Image) -> Image.Image:
        """
        Basic image enhancement using PIL
        
        Args:
            image: Original image
            
        Returns:
            Image.Image: Enhanced image
        """
        # Enhance sharpness
        enhancer = ImageEnhance.Sharpness(image)
        image = enhancer.enhance(1.2)
        
        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(1.1)
        
        # Enhance brightness slightly
        enhancer = ImageEnhance.Brightness(image)
        image = enhancer.enhance(1.05)
        
        return image
    
    def _resize_optimal(self, image: Image.Image) -> Image.Image:
        """
        Resize image ke ukuran optimal untuk processing
        
        Args:
            image: Image to resize
            
        Returns:
            Image.Image: Resized image
        """
        width, height = image.size
        
        # Target size untuk KTP (rasio ~1.586)
        target_width = 1200
        target_height = int(target_width / 1.586)
        
        # Jika image terlalu kecil, upscale
        if width < 800 or height < 500:
            # Calculate scale factor
            scale = max(800 / width, 500 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Jika image terlalu besar, downscale
        elif width > 2000 or height > 1500:
            # Calculate scale factor
            scale = min(2000 / width, 1500 / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        return image
    
    def validate_ktp_dimensions(self, image: Image.Image) -> Tuple[bool, str]:
        """
        Validate apakah dimensi image sesuai dengan KTP
        
        Args:
            image: Image untuk divalidasi
            
        Returns:
            Tuple[bool, str]: (is_valid, message)
        """
        width, height = image.size
        aspect_ratio = width / height
        
        # KTP Indonesia memiliki rasio ~1.586 (85.6mm x 53.98mm)
        expected_ratio = 1.586
        tolerance = 0.3  # 30% tolerance
        
        if abs(aspect_ratio - expected_ratio) > tolerance:
            return False, f"Rasio aspek tidak sesuai KTP. Rasio: {aspect_ratio:.2f}, diharapkan: {expected_ratio:.2f}"
        
        # Check minimum resolution
        if width < 400 or height < 250:
            return False, f"Resolusi terlalu rendah: {width}x{height}. Minimal 400x250"
        
        return True, "Dimensi image valid untuk KTP"
    
    def detect_ktp_orientation(self, image: Image.Image) -> Image.Image:
        """
        Detect dan correct orientasi KTP
        
        Args:
            image: Input image
            
        Returns:
            Image.Image: Corrected orientation image
        """
        try:
            # Convert to OpenCV
            cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_image, cv2.COLOR_BGR2GRAY)
            
            # Detect edges
            edges = cv2.Canny(gray, 50, 150, apertureSize=3)
            
            # Detect lines using HoughLines
            lines = cv2.HoughLines(edges, 1, np.pi/180, threshold=100)
            
            if lines is not None:
                angles = []
                for rho, theta in lines[:10]:  # Use top 10 lines
                    angle = theta * 180 / np.pi
                    angles.append(angle)
                
                # Find dominant angle
                if angles:
                    dominant_angle = np.median(angles)
                    
                    # If image is rotated, correct it
                    if abs(dominant_angle - 90) < abs(dominant_angle - 0):
                        # Rotate 90 degrees
                        image = image.rotate(90, expand=True)
                    elif abs(dominant_angle - 180) < 10:
                        # Rotate 180 degrees
                        image = image.rotate(180, expand=True)
            
            return image
            
        except Exception:
            # If orientation detection fails, return original
            return image
    
    async def save_image(self, image: Image.Image, filename: str) -> str:
        """
        Save processed image to upload directory
        
        Args:
            image: PIL Image to save
            filename: Filename untuk save
            
        Returns:
            str: Path to saved file
        """
        try:
            # Generate unique filename
            base_name = os.path.splitext(filename)[0]
            file_path = os.path.join(self.upload_dir, f"{base_name}_processed.jpg")
            
            # Ensure unique filename
            counter = 1
            while os.path.exists(file_path):
                file_path = os.path.join(self.upload_dir, f"{base_name}_processed_{counter}.jpg")
                counter += 1
            
            # Save image
            image.save(file_path, "JPEG", quality=95)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Error saving image: {str(e)}")
    
    def get_image_info(self, image: Image.Image) -> dict:
        """
        Get detailed information about image
        
        Args:
            image: PIL Image
            
        Returns:
            dict: Image information
        """
        return {
            "size": image.size,
            "mode": image.mode,
            "format": image.format,
            "aspect_ratio": image.size[0] / image.size[1],
            "megapixels": (image.size[0] * image.size[1]) / 1_000_000
        }
