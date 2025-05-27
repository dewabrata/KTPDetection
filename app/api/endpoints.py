"""
API Endpoints
=============

REST API endpoints untuk KTP Detection service
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
import time
import logging
from typing import Optional

from app.services.gemini_service import GeminiKTPService
from app.services.database_service import DatabaseService
from app.services.image_processor import ImageProcessor
from app.services.ktp_validator import KTPValidator
from app.models.ktp_model import (
    KTPValidationResult, 
    KTPSearchRequest, 
    KTPListResponse,
    ErrorResponse,
    ProcessingStatus
)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Dependency untuk services
def get_gemini_service():
    """Dependency untuk GeminiKTPService"""
    try:
        return GeminiKTPService()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initializing Gemini service: {str(e)}")

def get_database_service():
    """Dependency untuk DatabaseService"""
    return DatabaseService()

def get_image_processor():
    """Dependency untuk ImageProcessor"""
    return ImageProcessor()

def get_ktp_validator():
    """Dependency untuk KTPValidator"""
    return KTPValidator()

@router.post("/verify-ktp", response_model=KTPValidationResult)
async def verify_ktp(
    file: UploadFile = File(..., description="File gambar KTP (JPG, PNG, etc.)"),
    gemini_service: GeminiKTPService = Depends(get_gemini_service),
    database_service: DatabaseService = Depends(get_database_service),
    image_processor: ImageProcessor = Depends(get_image_processor),
    ktp_validator: KTPValidator = Depends(get_ktp_validator)
):
    """
    Endpoint utama untuk verifikasi dan ekstraksi data KTP dengan face detection
    
    Flow:
    1. Validate dan process gambar
    2. Analisis dengan Gemini Flash 2.5 (text + face)
    3. Validasi data dengan business rules
    4. Simpan ke database jika valid (termasuk foto wajah)
    5. Return hasil
    """
    start_time = time.time()
    
    try:
        logger.info(f"Starting KTP verification with face detection for file: {file.filename}")
        
        # 1. Process dan validate gambar
        processed_image = await image_processor.process_upload(file)
        
        # Validate image quality
        image_quality_valid, quality_issues = ktp_validator.validate_image_quality(processed_image)
        image_quality_score = 0.8 if not image_quality_valid else 1.0
        
        # Get file size untuk logging - FIX: Use read() instead of seek()
        content = await file.read()
        file_size = len(content)
        await file.seek(0)  # Reset to beginning
        
        # 2. Analisis dengan Gemini Flash 2.5 (include face detection)
        logger.info("Analyzing image with Gemini Flash 2.5 (text + face detection)")
        analysis_result = gemini_service.analyze_ktp_with_face(processed_image, save_face=True)
        
        # 3. Validasi tambahan jika KTP valid
        if analysis_result.is_valid_ktp and analysis_result.extracted_data:
            logger.info("Performing additional validation")
            
            # Validate KTP data dengan business rules
            data_valid, validation_errors = ktp_validator.validate_ktp_data(analysis_result.extracted_data)
            
            # Update result dengan validation errors
            if not data_valid:
                analysis_result.validation_errors.extend(validation_errors)
                if len(validation_errors) > 3:  # Too many errors, mark as invalid
                    analysis_result.is_valid_ktp = False
            
            # Calculate final confidence score
            final_confidence = ktp_validator.calculate_confidence_score(
                analysis_result, 
                image_quality_score
            )
            analysis_result.confidence_score = final_confidence
        
        processing_time = int((time.time() - start_time) * 1000)
        
        # 4. Simpan ke database jika valid (dengan face data)
        if analysis_result.is_valid_ktp and analysis_result.extracted_data:
            try:
                # Check if NIK already exists
                nik_exists = await database_service.check_nik_exists(analysis_result.extracted_data.nik)
                
                if nik_exists:
                    # NIK already exists, don't save but return warning
                    analysis_result.processing_notes = f"NIK {analysis_result.extracted_data.nik} sudah terdaftar"
                    analysis_result.validation_errors.append("NIK sudah terdaftar dalam database")
                else:
                    # Prepare face data untuk database
                    face_data = None
                    if analysis_result.face_detection and analysis_result.face_detection.found:
                        face_data = {
                            "face_image_path": analysis_result.face_detection.face_image_path,
                            "confidence": analysis_result.face_detection.confidence,
                            "quality_notes": analysis_result.face_detection.quality_notes
                        }
                        logger.info(f"Face detected and saved: {analysis_result.face_detection.face_image_path}")
                    
                    # Save to database dengan face data
                    db_result = await database_service.save_ktp_data(
                        analysis_result.extracted_data,
                        analysis_result.confidence_score,
                        face_data
                    )
                    analysis_result.database_id = db_result.get("id")
                    logger.info(f"KTP data saved to database with ID: {analysis_result.database_id}")
                
                # Log successful processing
                await database_service.log_processing({
                    "filename": file.filename,
                    "file_size": file_size,
                    "status": ProcessingStatus.SUCCESS.value,
                    "error": None,
                    "confidence": analysis_result.confidence_score,
                    "time_ms": processing_time
                })
                
            except Exception as db_error:
                logger.error(f"Database error: {str(db_error)}")
                analysis_result.processing_notes = f"Data valid tapi gagal disimpan: {str(db_error)}"
                
                # Log database error
                await database_service.log_processing({
                    "filename": file.filename,
                    "file_size": file_size,
                    "status": ProcessingStatus.FAILED.value,
                    "error": f"Database error: {str(db_error)}",
                    "confidence": analysis_result.confidence_score,
                    "time_ms": processing_time
                })
        else:
            # Log invalid KTP
            await database_service.log_processing({
                "filename": file.filename,
                "file_size": file_size,
                "status": ProcessingStatus.INVALID_KTP.value,
                "error": "; ".join(analysis_result.validation_errors),
                "confidence": analysis_result.confidence_score,
                "time_ms": processing_time
            })
        
        # Add image quality issues to processing notes
        if quality_issues:
            quality_note = f"Image quality issues: {', '.join(quality_issues)}"
            if analysis_result.processing_notes:
                analysis_result.processing_notes += f"; {quality_note}"
            else:
                analysis_result.processing_notes = quality_note
        
        # Add face detection notes
        if analysis_result.face_detection:
            if analysis_result.face_detection.found:
                face_note = f"Face detected (confidence: {analysis_result.face_detection.confidence:.2f})"
            else:
                face_note = "No face detected"
                
            if analysis_result.processing_notes:
                analysis_result.processing_notes += f"; {face_note}"
            else:
                analysis_result.processing_notes = face_note
        
        logger.info(f"KTP verification completed in {processing_time}ms. Valid: {analysis_result.is_valid_ktp}, Face: {analysis_result.face_detection.found if analysis_result.face_detection else False}")
        
        return analysis_result
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error in verify_ktp: {str(e)}")
        
        # Log processing error
        try:
            processing_time = int((time.time() - start_time) * 1000)
            await database_service.log_processing({
                "filename": file.filename if file and file.filename else "unknown",
                "file_size": 0,
                "status": ProcessingStatus.FAILED.value,
                "error": str(e),
                "confidence": 0.0,
                "time_ms": processing_time
            })
        except:
            pass  # Don't fail if logging fails
        
        raise HTTPException(status_code=500, detail=f"Error processing KTP: {str(e)}")

@router.post("/extract-face", summary="Extract face from KTP")
async def extract_face_only(
    file: UploadFile = File(..., description="File gambar KTP"),
    gemini_service: GeminiKTPService = Depends(get_gemini_service),
    image_processor: ImageProcessor = Depends(get_image_processor)
):
    """
    Endpoint khusus untuk ekstraksi foto wajah dari KTP
    """
    try:
        logger.info(f"Starting face extraction for file: {file.filename}")
        
        # Process gambar
        processed_image = await image_processor.process_upload(file)
        
        # Extract face menggunakan Gemini
        face_result = gemini_service.extract_face_from_ktp(processed_image)
        
        return {
            "success": face_result.found,
            "face_detection": face_result
        }
        
    except Exception as e:
        logger.error(f"Error extracting face: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error extracting face: {str(e)}")

@router.get("/ktp/{nik}", summary="Get KTP by NIK")
async def get_ktp_by_nik(
    nik: str,
    database_service: DatabaseService = Depends(get_database_service)
):
    """
    Mendapatkan data KTP berdasarkan NIK
    
    Args:
        nik: NIK (16 digit) yang dicari
    """
    try:
        # Validate NIK format
        if not nik.isdigit() or len(nik) != 16:
            raise HTTPException(status_code=400, detail="NIK harus 16 digit angka")
        
        # Get data from database
        ktp_data = await database_service.get_ktp_by_nik(nik)
        
        if not ktp_data:
            raise HTTPException(status_code=404, detail=f"NIK {nik} tidak ditemukan")
        
        return ktp_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting KTP by NIK {nik}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving KTP data: {str(e)}")

@router.get("/ktp/{nik}/face", summary="Get face image by NIK")
async def get_face_by_nik(
    nik: str,
    database_service: DatabaseService = Depends(get_database_service)
):
    """
    Mendapatkan foto wajah berdasarkan NIK
    
    Args:
        nik: NIK (16 digit) yang dicari
    """
    try:
        # Validate NIK format
        if not nik.isdigit() or len(nik) != 16:
            raise HTTPException(status_code=400, detail="NIK harus 16 digit angka")
        
        # Get data from database
        ktp_data = await database_service.get_ktp_by_nik(nik)
        
        if not ktp_data:
            raise HTTPException(status_code=404, detail=f"NIK {nik} tidak ditemukan")
        
        # Check if face image exists
        foto_wajah_path = ktp_data.get("foto_wajah_path")
        if not foto_wajah_path:
            raise HTTPException(status_code=404, detail="Foto wajah tidak ditemukan untuk NIK ini")
        
        return {
            "nik": nik,
            "foto_wajah_path": foto_wajah_path,
            "face_confidence": ktp_data.get("face_confidence"),
            "face_quality_notes": ktp_data.get("face_quality_notes")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting face by NIK {nik}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving face data: {str(e)}")

@router.post("/search-ktp", response_model=KTPListResponse, summary="Search KTP records")
async def search_ktp(
    search_request: KTPSearchRequest,
    database_service: DatabaseService = Depends(get_database_service)
):
    """
    Pencarian data KTP dengan filter
    
    Body:
        - nik: NIK untuk pencarian exact match (optional)
        - nama: Nama untuk pencarian partial match (optional)
        - limit: Limit hasil (default: 10, max: 100)
        - offset: Offset untuk pagination (default: 0)
    """
    try:
        # Validate search parameters
        if not search_request.nik and not search_request.nama:
            raise HTTPException(status_code=400, detail="Minimal salah satu parameter nik atau nama harus diisi")
        
        # If NIK search, use get_ktp_by_nik
        if search_request.nik:
            ktp_data = await database_service.get_ktp_by_nik(search_request.nik)
            if ktp_data:
                return KTPListResponse(
                    total=1,
                    data=[ktp_data],
                    limit=search_request.limit,
                    offset=search_request.offset
                )
            else:
                return KTPListResponse(
                    total=0,
                    data=[],
                    limit=search_request.limit,
                    offset=search_request.offset
                )
        
        # Name search
        if search_request.nama:
            result = await database_service.search_ktp(
                nama=search_request.nama,
                limit=search_request.limit,
                offset=search_request.offset
            )
            
            return KTPListResponse(
                total=result["total"],
                data=result["data"],
                limit=result["limit"],
                offset=result["offset"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching KTP: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error searching KTP: {str(e)}")

@router.get("/stats", summary="Get processing statistics")
async def get_processing_stats(
    database_service: DatabaseService = Depends(get_database_service)
):
    """
    Mendapatkan statistik processing KTP
    
    Returns:
        - total_processed: Total file yang diproses
        - success_rate: Persentase sukses
        - status_breakdown: Breakdown berdasarkan status
        - performance_metrics: Metrik performa
    """
    try:
        stats = await database_service.get_processing_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting processing stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")

@router.get("/health", summary="Health check")
async def health_check():
    """
    Health check endpoint untuk monitoring
    """
    try:
        # Test services
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {}
        }
        
        # Test Gemini service
        try:
            gemini_service = GeminiKTPService()
            gemini_healthy = gemini_service.test_connection()
            health_status["services"]["gemini"] = "healthy" if gemini_healthy else "unhealthy"
        except Exception as e:
            health_status["services"]["gemini"] = f"error: {str(e)}"
        
        # Test Database service (basic initialization)
        try:
            database_service = DatabaseService()
            health_status["services"]["database"] = "healthy"
        except Exception as e:
            health_status["services"]["database"] = f"error: {str(e)}"
        
        # Test image processor
        try:
            image_processor = ImageProcessor()
            health_status["services"]["image_processor"] = "healthy"
        except Exception as e:
            health_status["services"]["image_processor"] = f"error: {str(e)}"
        
        # Determine overall health
        unhealthy_services = [
            service for service, status in health_status["services"].items() 
            if status != "healthy"
        ]
        
        if unhealthy_services:
            health_status["status"] = "unhealthy"
            health_status["issues"] = unhealthy_services
        
        return health_status
        
    except Exception as e:
        logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@router.post("/test-gemini", summary="Test Gemini connection")
async def test_gemini_connection(
    gemini_service: GeminiKTPService = Depends(get_gemini_service)
):
    """
    Test endpoint untuk memverifikasi koneksi Gemini
    """
    try:
        is_connected = gemini_service.test_connection()
        return {
            "gemini_connected": is_connected,
            "message": "Gemini Flash 2.5 connected successfully" if is_connected else "Gemini connection failed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error testing Gemini connection: {str(e)}")

@router.post("/init-database", summary="Initialize database")
async def initialize_database(
    database_service: DatabaseService = Depends(get_database_service)
):
    """
    Initialize database dan create tables
    """
    try:
        success = await database_service.initialize_database()
        
        if success:
            return {
                "status": "success",
                "message": "Database initialized successfully"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to initialize database")
            
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error initializing database: {str(e)}")
