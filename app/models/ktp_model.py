"""
KTP Data Models
===============

Pydantic models untuk data KTP dan validasi
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class JenisKelamin(str, Enum):
    LAKI_LAKI = "LAKI-LAKI"
    PEREMPUAN = "PEREMPUAN"

class StatusPerkawinan(str, Enum):
    BELUM_KAWIN = "BELUM KAWIN"
    KAWIN = "KAWIN"
    CERAI_HIDUP = "CERAI HIDUP"
    CERAI_MATI = "CERAI MATI"

class ProcessingStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INVALID_KTP = "INVALID_KTP"

class KTPData(BaseModel):
    """Model untuk data KTP yang diekstrak"""
    nik: str = Field(..., min_length=16, max_length=16, description="Nomor Induk Kependudukan (16 digit)")
    nama: str = Field(..., min_length=1, max_length=255, description="Nama lengkap")
    tempat_lahir: Optional[str] = Field(None, max_length=255, description="Tempat lahir")
    tanggal_lahir: Optional[str] = Field(None, description="Tanggal lahir format DD-MM-YYYY")
    jenis_kelamin: Optional[JenisKelamin] = Field(None, description="Jenis kelamin")
    alamat: Optional[str] = Field(None, description="Alamat lengkap")
    rt_rw: Optional[str] = Field(None, max_length=10, description="RT/RW")
    kelurahan: Optional[str] = Field(None, max_length=255, description="Kelurahan/Desa")
    kecamatan: Optional[str] = Field(None, max_length=255, description="Kecamatan")
    kabupaten_kota: Optional[str] = Field(None, max_length=255, description="Kabupaten/Kota")
    provinsi: Optional[str] = Field(None, max_length=255, description="Provinsi")
    agama: Optional[str] = Field(None, max_length=50, description="Agama")
    status_perkawinan: Optional[StatusPerkawinan] = Field(None, description="Status perkawinan")
    pekerjaan: Optional[str] = Field(None, max_length=255, description="Pekerjaan")
    kewarganegaraan: Optional[str] = Field("WNI", max_length=10, description="Kewarganegaraan")
    berlaku_hingga: Optional[str] = Field(None, max_length=50, description="Berlaku hingga")

    @validator('nik')
    def validate_nik(cls, v):
        if not v.isdigit():
            raise ValueError('NIK harus berupa angka')
        if len(v) != 16:
            raise ValueError('NIK harus 16 digit')
        return v

    @validator('tanggal_lahir')
    def validate_tanggal_lahir(cls, v):
        if v and not cls._is_valid_date_format(v):
            raise ValueError('Format tanggal lahir harus DD-MM-YYYY')
        return v

    @staticmethod
    def _is_valid_date_format(date_str: str) -> bool:
        """Validasi format tanggal DD-MM-YYYY"""
        try:
            parts = date_str.split('-')
            if len(parts) != 3:
                return False
            day, month, year = parts
            return (len(day) == 2 and len(month) == 2 and len(year) == 4 and
                    day.isdigit() and month.isdigit() and year.isdigit() and
                    1 <= int(day) <= 31 and 1 <= int(month) <= 12)
        except:
            return False

class FaceDetectionResult(BaseModel):
    """Model untuk hasil deteksi wajah"""
    found: bool = Field(..., description="Apakah wajah ditemukan")
    bounding_box: Optional[dict] = Field(None, description="Koordinat bounding box wajah")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Confidence score deteksi wajah")
    quality_notes: Optional[str] = Field(None, description="Catatan kualitas foto wajah")
    face_image_path: Optional[str] = Field(None, description="Path file foto wajah yang di-crop")

class KTPValidationResult(BaseModel):
    """Model untuk hasil validasi KTP"""
    is_valid_ktp: bool = Field(..., description="Apakah gambar adalah KTP yang valid")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Skor confidence (0.0 - 1.0)")
    extracted_data: Optional[KTPData] = Field(None, description="Data yang diekstrak jika valid")
    face_detection: Optional[FaceDetectionResult] = Field(None, description="Hasil deteksi wajah")
    validation_errors: List[str] = Field(default_factory=list, description="List error validasi")
    processing_notes: Optional[str] = Field(None, description="Catatan tambahan processing")
    database_id: Optional[int] = Field(None, description="ID record di database jika berhasil disimpan")

class ProcessingLog(BaseModel):
    """Model untuk log processing"""
    original_filename: str = Field(..., description="Nama file asli")
    file_size: int = Field(..., description="Ukuran file dalam bytes")
    processing_status: ProcessingStatus = Field(..., description="Status processing")
    error_message: Optional[str] = Field(None, description="Pesan error jika ada")
    confidence_score: float = Field(0.0, ge=0.0, le=1.0, description="Skor confidence")
    processing_time_ms: int = Field(..., description="Waktu processing dalam milidetik")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="Waktu pembuatan log")

class KTPSearchRequest(BaseModel):
    """Model untuk request pencarian KTP"""
    nik: Optional[str] = Field(None, min_length=16, max_length=16, description="NIK untuk pencarian")
    nama: Optional[str] = Field(None, min_length=1, description="Nama untuk pencarian")
    limit: int = Field(10, ge=1, le=100, description="Limit hasil pencarian")
    offset: int = Field(0, ge=0, description="Offset untuk pagination")

class KTPListResponse(BaseModel):
    """Model untuk response list KTP"""
    total: int = Field(..., description="Total record")
    data: List[KTPData] = Field(..., description="List data KTP")
    limit: int = Field(..., description="Limit yang digunakan")
    offset: int = Field(..., description="Offset yang digunakan")

class ErrorResponse(BaseModel):
    """Model untuk error response"""
    error: str = Field(..., description="Pesan error")
    detail: Optional[str] = Field(None, description="Detail error")
    status_code: int = Field(..., description="HTTP status code")
