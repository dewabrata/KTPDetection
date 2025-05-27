"""
KTP Validator Service
====================

Service untuk validasi tambahan KTP setelah analisis Gemini
"""

import re
from typing import Tuple, List, Dict, Any
from datetime import datetime
from PIL import Image

from app.models.ktp_model import KTPData, KTPValidationResult

class KTPValidator:
    """Service untuk validasi tambahan data KTP"""
    
    def __init__(self):
        """Initialize KTP validator"""
        self.valid_provinces = [
            "ACEH", "SUMATERA UTARA", "SUMATERA BARAT", "RIAU", "JAMBI",
            "SUMATERA SELATAN", "BENGKULU", "LAMPUNG", "KEPULAUAN BANGKA BELITUNG",
            "KEPULAUAN RIAU", "DKI JAKARTA", "JAWA BARAT", "JAWA TENGAH",
            "DI YOGYAKARTA", "JAWA TIMUR", "BANTEN", "BALI", "NUSA TENGGARA BARAT",
            "NUSA TENGGARA TIMUR", "KALIMANTAN BARAT", "KALIMANTAN TENGAH",
            "KALIMANTAN SELATAN", "KALIMANTAN TIMUR", "KALIMANTAN UTARA",
            "SULAWESI UTARA", "SULAWESI TENGAH", "SULAWESI SELATAN",
            "SULAWESI TENGGARA", "GORONTALO", "SULAWESI BARAT", "MALUKU",
            "MALUKU UTARA", "PAPUA", "PAPUA BARAT", "PAPUA SELATAN",
            "PAPUA TENGAH", "PAPUA PEGUNUNGAN", "PAPUA BARAT DAYA"
        ]
        
        self.valid_religions = [
            "ISLAM", "KRISTEN", "KATOLIK", "HINDU", "BUDDHA", "KONGHUCU"
        ]
        
        self.valid_genders = ["LAKI-LAKI", "PEREMPUAN"]
        
        self.valid_marital_status = [
            "BELUM KAWIN", "KAWIN", "CERAI HIDUP", "CERAI MATI"
        ]
    
    def validate_ktp_data(self, ktp_data: KTPData) -> Tuple[bool, List[str]]:
        """
        Validate KTP data dengan aturan bisnis Indonesia
        
        Args:
            ktp_data: KTPData object untuk divalidasi
            
        Returns:
            Tuple[bool, List[str]]: (is_valid, list_of_errors)
        """
        errors = []
        
        # Validate NIK
        nik_errors = self._validate_nik(ktp_data.nik)
        errors.extend(nik_errors)
        
        # Validate nama
        if not ktp_data.nama or len(ktp_data.nama.strip()) < 2:
            errors.append("Nama tidak valid atau terlalu pendek")
        
        # Validate tanggal lahir
        if ktp_data.tanggal_lahir:
            date_errors = self._validate_birth_date(ktp_data.tanggal_lahir)
            errors.extend(date_errors)
        
        # Validate jenis kelamin
        if ktp_data.jenis_kelamin and ktp_data.jenis_kelamin.value not in self.valid_genders:
            errors.append(f"Jenis kelamin tidak valid: {ktp_data.jenis_kelamin}")
        
        # Validate provinsi
        if ktp_data.provinsi:
            province_errors = self._validate_province(ktp_data.provinsi)
            errors.extend(province_errors)
        
        # Validate agama
        if ktp_data.agama and ktp_data.agama.upper() not in self.valid_religions:
            errors.append(f"Agama tidak valid: {ktp_data.agama}")
        
        # Validate status perkawinan
        if ktp_data.status_perkawinan and ktp_data.status_perkawinan.value not in self.valid_marital_status:
            errors.append(f"Status perkawinan tidak valid: {ktp_data.status_perkawinan}")
        
        # Validate RT/RW format
        if ktp_data.rt_rw and not self._validate_rt_rw_format(ktp_data.rt_rw):
            errors.append(f"Format RT/RW tidak valid: {ktp_data.rt_rw}")
        
        # Cross-validate NIK dengan tempat lahir dan tanggal lahir
        if ktp_data.nik and ktp_data.tanggal_lahir:
            cross_errors = self._cross_validate_nik_data(ktp_data)
            errors.extend(cross_errors)
        
        return len(errors) == 0, errors
    
    def _validate_nik(self, nik: str) -> List[str]:
        """
        Validate NIK dengan aturan NIK Indonesia
        
        Args:
            nik: NIK untuk divalidasi
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        if not nik:
            errors.append("NIK tidak boleh kosong")
            return errors
        
        # Check if NIK is exactly 16 digits
        if not re.match(r'^\d{16}$', nik):
            errors.append("NIK harus 16 digit angka")
            return errors
        
        # Validate kode wilayah (6 digit pertama)
        kode_wilayah = nik[:6]
        if not self._validate_region_code(kode_wilayah):
            errors.append(f"Kode wilayah NIK tidak valid: {kode_wilayah}")
        
        # Validate tanggal lahir dalam NIK (digit 7-12)
        tgl_lahir_nik = nik[6:12]
        if not self._validate_birth_date_in_nik(tgl_lahir_nik):
            errors.append(f"Tanggal lahir dalam NIK tidak valid: {tgl_lahir_nik}")
        
        # Validate nomor urut (4 digit terakhir)
        nomor_urut = nik[12:16]
        if nomor_urut == "0000":
            errors.append("Nomor urut NIK tidak boleh 0000")
        
        return errors
    
    def _validate_region_code(self, region_code: str) -> bool:
        """
        Validate kode wilayah NIK (basic validation)
        
        Args:
            region_code: 6 digit kode wilayah
            
        Returns:
            bool: True jika valid
        """
        # Basic validation - kode provinsi (2 digit pertama) tidak boleh 00
        if region_code[:2] == "00":
            return False
        
        # Kode kabupaten/kota (2 digit berikutnya) tidak boleh 00
        if region_code[2:4] == "00":
            return False
        
        # Kode kecamatan (2 digit terakhir) tidak boleh 00
        if region_code[4:6] == "00":
            return False
        
        return True
    
    def _validate_birth_date_in_nik(self, birth_date_str: str) -> bool:
        """
        Validate tanggal lahir dalam NIK (format DDMMYY)
        
        Args:
            birth_date_str: 6 digit tanggal lahir dalam NIK
            
        Returns:
            bool: True jika valid
        """
        try:
            day = int(birth_date_str[:2])
            month = int(birth_date_str[2:4])
            year = int(birth_date_str[4:6])
            
            # Adjust for female (tambah 40 pada tanggal)
            if day > 40:
                day -= 40
            
            # Validate day
            if day < 1 or day > 31:
                return False
            
            # Validate month
            if month < 1 or month > 12:
                return False
            
            # Year validation (assume 1900-2099 range)
            current_year = datetime.now().year
            if year <= (current_year - 1900) % 100:
                full_year = 2000 + year
            else:
                full_year = 1900 + year
            
            # Create date to validate
            test_date = datetime(full_year, month, day)
            
            # Check if date is not in the future
            if test_date > datetime.now():
                return False
                
            return True
            
        except (ValueError, IndexError):
            return False
    
    def _validate_birth_date(self, birth_date: str) -> List[str]:
        """
        Validate format tanggal lahir DD-MM-YYYY
        
        Args:
            birth_date: Tanggal lahir dalam format DD-MM-YYYY
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        try:
            # Parse DD-MM-YYYY
            day, month, year = birth_date.split('-')
            day, month, year = int(day), int(month), int(year)
            
            # Validate ranges
            if day < 1 or day > 31:
                errors.append(f"Tanggal tidak valid: {day}")
            
            if month < 1 or month > 12:
                errors.append(f"Bulan tidak valid: {month}")
            
            if year < 1900 or year > datetime.now().year:
                errors.append(f"Tahun tidak valid: {year}")
            
            # Validate actual date
            try:
                test_date = datetime(year, month, day)
                if test_date > datetime.now():
                    errors.append("Tanggal lahir tidak boleh di masa depan")
            except ValueError:
                errors.append(f"Tanggal tidak valid: {birth_date}")
                
        except (ValueError, IndexError):
            errors.append(f"Format tanggal lahir salah. Gunakan DD-MM-YYYY: {birth_date}")
        
        return errors
    
    def _validate_province(self, province: str) -> List[str]:
        """
        Validate nama provinsi
        
        Args:
            province: Nama provinsi
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        province_upper = province.upper().strip()
        
        # Check exact match
        if province_upper not in self.valid_provinces:
            # Check partial match
            matches = [p for p in self.valid_provinces if province_upper in p or p in province_upper]
            if not matches:
                errors.append(f"Provinsi tidak dikenali: {province}")
        
        return errors
    
    def _validate_rt_rw_format(self, rt_rw: str) -> bool:
        """
        Validate format RT/RW (contoh: 001/002)
        
        Args:
            rt_rw: String RT/RW
            
        Returns:
            bool: True jika format valid
        """
        # Pattern: XXX/XXX (3 digit / 3 digit)
        pattern = r'^\d{3}/\d{3}$'
        return bool(re.match(pattern, rt_rw))
    
    def _cross_validate_nik_data(self, ktp_data: KTPData) -> List[str]:
        """
        Cross-validate NIK dengan data lain
        
        Args:
            ktp_data: KTPData object
            
        Returns:
            List[str]: List of validation errors
        """
        errors = []
        
        try:
            # Extract info from NIK
            nik = ktp_data.nik
            tgl_lahir_nik = nik[6:12]
            
            # Parse tanggal lahir dari NIK
            day_nik = int(tgl_lahir_nik[:2])
            month_nik = int(tgl_lahir_nik[2:4])
            year_nik = int(tgl_lahir_nik[4:6])
            
            # Check if female (day > 40)
            is_female_nik = day_nik > 40
            if is_female_nik:
                day_nik -= 40
            
            # Cross-check dengan jenis kelamin
            if ktp_data.jenis_kelamin:
                is_female_data = ktp_data.jenis_kelamin.value == "PEREMPUAN"
                if is_female_nik != is_female_data:
                    errors.append("Jenis kelamin tidak sesuai dengan NIK")
            
            # Cross-check dengan tanggal lahir
            if ktp_data.tanggal_lahir:
                try:
                    day_data, month_data, year_data = ktp_data.tanggal_lahir.split('-')
                    day_data, month_data, year_data = int(day_data), int(month_data), int(year_data)
                    
                    # Adjust year from NIK (assume 1900-2099)
                    current_year = datetime.now().year
                    if year_nik <= (current_year - 1900) % 100:
                        year_nik_full = 2000 + year_nik
                    else:
                        year_nik_full = 1900 + year_nik
                    
                    # Compare dates
                    if (day_nik != day_data or 
                        month_nik != month_data or 
                        year_nik_full != year_data):
                        errors.append("Tanggal lahir tidak sesuai dengan NIK")
                        
                except (ValueError, IndexError):
                    # Tanggal lahir format salah, sudah divalidasi di tempat lain
                    pass
            
        except (ValueError, IndexError):
            # NIK format salah, sudah divalidasi di tempat lain
            pass
        
        return errors
    
    def validate_image_quality(self, image: Image.Image) -> Tuple[bool, List[str]]:
        """
        Validate kualitas gambar untuk OCR
        
        Args:
            image: PIL Image object
            
        Returns:
            Tuple[bool, List[str]]: (is_good_quality, list_of_issues)
        """
        issues = []
        
        width, height = image.size
        
        # Check resolution
        if width < 800 or height < 500:
            issues.append(f"Resolusi rendah: {width}x{height}. Disarankan minimal 800x500")
        
        # Check aspect ratio
        aspect_ratio = width / height
        expected_ratio = 1.586  # KTP ratio
        if abs(aspect_ratio - expected_ratio) > 0.5:
            issues.append(f"Rasio aspek tidak ideal: {aspect_ratio:.2f}. KTP ratio: {expected_ratio:.2f}")
        
        # Check if image is too dark or bright (basic check)
        # Convert to grayscale and check mean brightness
        try:
            import numpy as np
            gray_array = np.array(image.convert('L'))
            mean_brightness = np.mean(gray_array)
            
            if mean_brightness < 50:
                issues.append("Gambar terlalu gelap")
            elif mean_brightness > 200:
                issues.append("Gambar terlalu terang")
                
        except ImportError:
            # NumPy not available, skip brightness check
            pass
        
        return len(issues) == 0, issues
    
    def calculate_confidence_score(self, validation_result: KTPValidationResult, 
                                 image_quality_score: float = 1.0) -> float:
        """
        Calculate overall confidence score
        
        Args:
            validation_result: KTPValidationResult dari Gemini
            image_quality_score: Skor kualitas gambar (0.0-1.0)
            
        Returns:
            float: Overall confidence score (0.0-1.0)
        """
        base_score = validation_result.confidence_score
        
        # Penalty for validation errors
        if validation_result.validation_errors:
            error_penalty = min(0.3, len(validation_result.validation_errors) * 0.1)
            base_score -= error_penalty
        
        # Apply image quality factor
        final_score = base_score * image_quality_score
        
        return max(0.0, min(1.0, final_score))
    
    def get_validation_summary(self, is_valid: bool, errors: List[str]) -> Dict[str, Any]:
        """
        Generate validation summary
        
        Args:
            is_valid: Apakah data valid
            errors: List of validation errors
            
        Returns:
            Dict[str, Any]: Validation summary
        """
        return {
            "is_valid": is_valid,
            "error_count": len(errors),
            "errors": errors,
            "severity": "low" if len(errors) <= 2 else "medium" if len(errors) <= 5 else "high"
        }
