"""
Gemini KTP Service
==================

Service untuk analisis KTP menggunakan Google Gemini Flash 2.5
"""

import google.generativeai as genai
from PIL import Image
import json
import io
import base64
import os
from typing import Dict, Any, Tuple
from decouple import config

from app.models.ktp_model import KTPValidationResult, KTPData, FaceDetectionResult

class GeminiKTPService:
    """Service untuk menganalisis KTP menggunakan Gemini Flash 2.5"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini service
        
        Args:
            api_key: Google AI API key. Jika None, akan ambil dari environment
        """
        self.api_key = api_key or config("GEMINI_API_KEY")
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            raise ValueError("GEMINI_API_KEY belum dikonfigurasi di file .env")
            
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Create face images directory
        self.face_images_dir = "face_images"
        os.makedirs(self.face_images_dir, exist_ok=True)
        
    def analyze_ktp_with_face(self, image: Image.Image, save_face: bool = True) -> KTPValidationResult:
        """
        Analisis gambar KTP dengan face detection menggunakan Gemini Flash 2.5
        
        Args:
            image: PIL Image object dari foto KTP
            save_face: Apakah menyimpan foto wajah yang diekstrak
            
        Returns:
            KTPValidationResult: Hasil analisis KTP dengan face detection
        """
        try:
            # Optimize image untuk processing
            processed_image = self._optimize_image(image)
            
            # Create prompt untuk analisis KTP + face detection
            prompt = self._create_complete_analysis_prompt()
            
            # Generate content dengan Gemini
            response = self.model.generate_content([prompt, processed_image])
            
            # Parse response JSON
            result_dict = self._parse_response(response.text)
            
            # Process face detection hasil
            face_result = None
            if result_dict.get("face_detection"):
                face_result = self._process_face_detection(
                    result_dict["face_detection"], 
                    processed_image, 
                    save_face
                )
            
            # Convert ke KTPValidationResult
            return self._create_validation_result(result_dict, face_result)
            
        except Exception as e:
            return KTPValidationResult(
                is_valid_ktp=False,
                confidence_score=0.0,
                validation_errors=[f"Error processing dengan Gemini: {str(e)}"],
                processing_notes=f"Gemini API error: {type(e).__name__}"
            )
    
    def analyze_ktp(self, image: Image.Image) -> KTPValidationResult:
        """
        Analisis gambar KTP menggunakan Gemini Flash 2.5 (backward compatibility)
        
        Args:
            image: PIL Image object dari foto KTP
            
        Returns:
            KTPValidationResult: Hasil analisis KTP
        """
        return self.analyze_ktp_with_face(image, save_face=True)
    
    def extract_face_from_ktp(self, image: Image.Image) -> FaceDetectionResult:
        """
        Extract hanya foto wajah dari KTP
        
        Args:
            image: PIL Image object dari foto KTP
            
        Returns:
            FaceDetectionResult: Hasil deteksi wajah
        """
        try:
            # Optimize image untuk processing
            processed_image = self._optimize_image(image)
            
            # Create prompt khusus face detection
            prompt = self._create_face_detection_prompt()
            
            # Generate content dengan Gemini
            response = self.model.generate_content([prompt, processed_image])
            
            # Parse response JSON
            result_dict = self._parse_response(response.text)
            
            # Process face detection
            if result_dict.get("face_detection"):
                return self._process_face_detection(
                    result_dict["face_detection"], 
                    processed_image, 
                    save_face=True
                )
            else:
                return FaceDetectionResult(
                    found=False,
                    confidence=0.0,
                    quality_notes="Face detection gagal"
                )
                
        except Exception as e:
            return FaceDetectionResult(
                found=False,
                confidence=0.0,
                quality_notes=f"Error: {str(e)}"
            )
    
    def _optimize_image(self, image: Image.Image) -> Image.Image:
        """
        Optimize image untuk processing yang lebih baik
        
        Args:
            image: Original PIL Image
            
        Returns:
            Image.Image: Optimized image
        """
        # Convert ke RGB jika perlu
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Resize jika terlalu besar (max 1024x1024 untuk efisiensi)
        max_size = 1024
        if max(image.size) > max_size:
            ratio = max_size / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        return image
    
    def _create_complete_analysis_prompt(self) -> str:
        """
        Create comprehensive prompt untuk analisis KTP + face detection
        
        Returns:
            str: Prompt yang akan dikirim ke Gemini
        """
        return """
Analisis gambar ini sebagai KTP (Kartu Tanda Penduduk) Indonesia dengan sangat teliti:

INSTRUKSI ANALISIS:
1. Periksa apakah ini benar-benar KTP Indonesia yang VALID
2. Jika VALID: ekstrak SEMUA informasi yang terlihat dengan akurat
3. DETEKSI FOTO WAJAH: Temukan dan analisis foto wajah pada KTP
4. Jika TIDAK VALID: berikan alasan spesifik mengapa tidak valid

KRITERIA KTP INDONESIA YANG VALID:
- Ada logo Garuda Pancasila di pojok kiri atas
- Text "REPUBLIK INDONESIA" di bagian atas
- Layout dan format standar KTP Indonesia
- Field wajib: NIK (16 digit), Nama, Tempat/Tanggal Lahir, dll
- Background dan desain sesuai standar pemerintah
- Foto wajah pemegang KTP di sisi kiri

FIELD YANG HARUS DIEKSTRAK (jika valid):
- NIK: 16 digit angka
- Nama: Nama lengkap
- Tempat Lahir: Kota/kabupaten tempat lahir
- Tanggal Lahir: Format DD-MM-YYYY
- Jenis Kelamin: LAKI-LAKI atau PEREMPUAN
- Alamat: Alamat lengkap
- RT/RW: Format 000/000
- Kelurahan/Desa: Nama kelurahan
- Kecamatan: Nama kecamatan
- Kabupaten/Kota: Nama kabupaten/kota
- Provinsi: Nama provinsi
- Agama: Agama yang tertulis
- Status Perkawinan: BELUM KAWIN/KAWIN/CERAI HIDUP/CERAI MATI
- Pekerjaan: Jenis pekerjaan
- Kewarganegaraan: Biasanya WNI
- Berlaku Hingga: Tanggal berlaku atau SEUMUR HIDUP

DETEKSI FOTO WAJAH:
- Temukan area foto wajah pada KTP (biasanya di sebelah kiri)
- Berikan koordinat bounding box dalam pixel (x, y, width, height)
- Evaluasi kualitas foto (jelas/blur, pencahayaan, angle)
- Pastikan ini benar-benar foto wajah manusia
- Koordinat relatif terhadap ukuran gambar yang dianalisis

OUTPUT FORMAT (JSON STRICT):
{
    "is_valid_ktp": true/false,
    "confidence_score": 0.95,
    "extracted_data": {
        "nik": "3201234567890123",
        "nama": "NAMA LENGKAP",
        "tempat_lahir": "JAKARTA",
        "tanggal_lahir": "01-01-1990",
        "jenis_kelamin": "LAKI-LAKI",
        "alamat": "JL. CONTOH NO. 123",
        "rt_rw": "001/002",
        "kelurahan": "KELURAHAN CONTOH",
        "kecamatan": "KECAMATAN CONTOH",
        "kabupaten_kota": "KOTA JAKARTA SELATAN",
        "provinsi": "DKI JAKARTA",
        "agama": "ISLAM",
        "status_perkawinan": "BELUM KAWIN",
        "pekerjaan": "SWASTA",
        "kewarganegaraan": "WNI",
        "berlaku_hingga": "SEUMUR HIDUP"
    },
    "face_detection": {
        "found": true/false,
        "bounding_box": {
            "x": 50,
            "y": 80,
            "width": 120,
            "height": 150
        },
        "confidence": 0.92,
        "quality_notes": "Foto wajah jelas, pencahayaan baik, menghadap depan"
    },
    "validation_errors": ["list error jika tidak valid"],
    "processing_notes": "catatan tambahan jika ada"
}

PENTING:
- Berikan HANYA JSON yang valid, tanpa text tambahan
- Jika field tidak terlihat/tidak terbaca, beri nilai null
- Pastikan NIK adalah 16 digit angka
- Pastikan format tanggal DD-MM-YYYY
- Koordinat bounding box dalam pixel yang tepat
- Jika gambar blur/tidak jelas, turunkan confidence_score
- Jika bukan KTP, set is_valid_ktp: false dan jelaskan di validation_errors
        """
    
    def _create_face_detection_prompt(self) -> str:
        """
        Create prompt khusus untuk face detection saja
        
        Returns:
            str: Prompt untuk face detection
        """
        return """
Dalam gambar KTP Indonesia ini, fokus HANYA pada deteksi foto wajah:

INSTRUKSI:
1. Temukan area foto wajah pada KTP (biasanya di sebelah kiri)
2. Berikan koordinat bounding box yang tepat dalam pixel
3. Evaluasi kualitas foto wajah
4. Pastikan ini benar-benar foto wajah manusia, bukan logo atau gambar lain

ANALISIS FOTO WAJAH:
- Lokasi: Biasanya di sebelah kiri KTP
- Ukuran: Sekitar 3x4 cm pada KTP asli
- Kualitas: Jelas/blur, pencahayaan, angle wajah
- Validitas: Pastikan foto manusia, bukan ilustrasi

OUTPUT FORMAT (JSON STRICT):
{
    "face_detection": {
        "found": true/false,
        "bounding_box": {
            "x": 50,
            "y": 80,
            "width": 120,
            "height": 150
        },
        "confidence": 0.92,
        "quality_notes": "Foto wajah jelas, pencahayaan baik, menghadap depan"
    }
}

PENTING:
- Berikan HANYA JSON yang valid
- Koordinat dalam pixel yang tepat
- Confidence score berdasarkan kualitas deteksi
- Quality notes yang informatif
        """
    
    def _process_face_detection(self, face_data: Dict[str, Any], image: Image.Image, save_face: bool) -> FaceDetectionResult:
        """
        Process hasil face detection dari Gemini
        
        Args:
            face_data: Data face detection dari Gemini response
            image: Original image untuk cropping
            save_face: Apakah menyimpan foto wajah
            
        Returns:
            FaceDetectionResult: Processed face detection result
        """
        try:
            if not face_data.get("found", False):
                return FaceDetectionResult(
                    found=False,
                    confidence=face_data.get("confidence", 0.0),
                    quality_notes=face_data.get("quality_notes", "Wajah tidak ditemukan")
                )
            
            # Extract bounding box coordinates
            bbox = face_data.get("bounding_box", {})
            if not all(k in bbox for k in ["x", "y", "width", "height"]):
                return FaceDetectionResult(
                    found=False,
                    confidence=0.0,
                    quality_notes="Koordinat bounding box tidak lengkap"
                )
            
            # Crop face dari image
            face_image = None
            face_path = None
            
            if save_face:
                face_image, face_path = self._crop_and_save_face(image, bbox)
            
            return FaceDetectionResult(
                found=True,
                bounding_box=bbox,
                confidence=face_data.get("confidence", 0.0),
                quality_notes=face_data.get("quality_notes"),
                face_image_path=face_path
            )
            
        except Exception as e:
            return FaceDetectionResult(
                found=False,
                confidence=0.0,
                quality_notes=f"Error processing face: {str(e)}"
            )
    
    def _crop_and_save_face(self, image: Image.Image, bbox: Dict[str, int]) -> Tuple[Image.Image, str]:
        """
        Crop dan save foto wajah dari koordinat bounding box
        
        Args:
            image: Original image
            bbox: Bounding box coordinates {x, y, width, height}
            
        Returns:
            Tuple[Image.Image, str]: (cropped_image, file_path)
        """
        try:
            # Extract coordinates
            x = bbox["x"]
            y = bbox["y"]
            width = bbox["width"]
            height = bbox["height"]
            
            # Crop face area
            face_image = image.crop((x, y, x + width, y + height))
            
            # Resize to standard size (150x150)
            face_image = face_image.resize((150, 150), Image.Resampling.LANCZOS)
            
            # Generate unique filename
            import time
            timestamp = int(time.time())
            filename = f"face_{timestamp}.jpg"
            file_path = os.path.join(self.face_images_dir, filename)
            
            # Save face image
            face_image.save(file_path, "JPEG", quality=95)
            
            return face_image, file_path
            
        except Exception as e:
            raise Exception(f"Error cropping and saving face: {str(e)}")
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse response dari Gemini menjadi dictionary
        
        Args:
            response_text: Raw response dari Gemini
            
        Returns:
            Dict[str, Any]: Parsed JSON response
        """
        try:
            # Clean response text (remove markdown if any)
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]
            cleaned_text = cleaned_text.strip()
            
            # Parse JSON
            result = json.loads(cleaned_text)
            return result
            
        except json.JSONDecodeError as e:
            # Jika gagal parse JSON, return error format
            return {
                "is_valid_ktp": False,
                "confidence_score": 0.0,
                "validation_errors": [f"Error parsing Gemini response: {str(e)}"],
                "processing_notes": f"Raw response: {response_text[:200]}..."
            }
    
    def _create_validation_result(self, result_dict: Dict[str, Any], face_result: FaceDetectionResult = None) -> KTPValidationResult:
        """
        Convert dictionary result ke KTPValidationResult object
        
        Args:
            result_dict: Dictionary hasil parsing dari Gemini
            face_result: Face detection result
            
        Returns:
            KTPValidationResult: Validated result object
        """
        try:
            # Extract basic validation info
            is_valid = result_dict.get("is_valid_ktp", False)
            confidence = result_dict.get("confidence_score", 0.0)
            errors = result_dict.get("validation_errors", [])
            notes = result_dict.get("processing_notes")
            
            # Extract KTP data jika valid
            extracted_data = None
            if is_valid and "extracted_data" in result_dict:
                try:
                    ktp_data_dict = result_dict["extracted_data"]
                    extracted_data = KTPData(**ktp_data_dict)
                except Exception as e:
                    # Jika gagal create KTPData, mark as invalid
                    is_valid = False
                    errors.append(f"Error validating extracted data: {str(e)}")
            
            return KTPValidationResult(
                is_valid_ktp=is_valid,
                confidence_score=confidence,
                extracted_data=extracted_data,
                face_detection=face_result,
                validation_errors=errors,
                processing_notes=notes
            )
            
        except Exception as e:
            return KTPValidationResult(
                is_valid_ktp=False,
                confidence_score=0.0,
                validation_errors=[f"Error creating validation result: {str(e)}"],
                processing_notes="Failed to process Gemini response"
            )
    
    def test_connection(self) -> bool:
        """
        Test koneksi ke Gemini API
        
        Returns:
            bool: True jika koneksi berhasil
        """
        try:
            # Create simple test image
            test_image = Image.new('RGB', (100, 100), color='white')
            
            # Simple test prompt
            test_prompt = "Describe this image briefly."
            
            response = self.model.generate_content([test_prompt, test_image])
            return bool(response.text)
            
        except Exception:
            return False
