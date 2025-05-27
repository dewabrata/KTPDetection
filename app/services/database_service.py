"""
Database Service
================

Service untuk berinteraksi dengan MariaDB/MySQL menggunakan SQLAlchemy async
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Date, Enum, Integer, DECIMAL, TIMESTAMP, func, select, insert, update, delete
from decouple import config

from app.models.ktp_model import KTPData, ProcessingStatus

logger = logging.getLogger(__name__)

# Database Models
class Base(DeclarativeBase):
    pass

class KTPRecord(Base):
    __tablename__ = "ktp_records"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nik: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    nama: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    tempat_lahir: Mapped[Optional[str]] = mapped_column(String(255))
    tanggal_lahir: Mapped[Optional[datetime]] = mapped_column(Date)
    jenis_kelamin: Mapped[Optional[str]] = mapped_column(Enum('LAKI-LAKI', 'PEREMPUAN', name='gender_enum'))
    alamat: Mapped[Optional[str]] = mapped_column(Text)
    rt_rw: Mapped[Optional[str]] = mapped_column(String(10))
    kelurahan: Mapped[Optional[str]] = mapped_column(String(255))
    kecamatan: Mapped[Optional[str]] = mapped_column(String(255))
    kabupaten_kota: Mapped[Optional[str]] = mapped_column(String(255))
    provinsi: Mapped[Optional[str]] = mapped_column(String(255))
    agama: Mapped[Optional[str]] = mapped_column(String(50))
    status_perkawinan: Mapped[Optional[str]] = mapped_column(String(50))
    pekerjaan: Mapped[Optional[str]] = mapped_column(String(255))
    kewarganegaraan: Mapped[Optional[str]] = mapped_column(String(10), default='WNI')
    berlaku_hingga: Mapped[Optional[str]] = mapped_column(String(50))
    confidence_score: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2))
    image_path: Mapped[Optional[str]] = mapped_column(String(500))
    foto_wajah_path: Mapped[Optional[str]] = mapped_column(String(500))
    face_confidence: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2))
    face_quality_notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, 
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

class ProcessingLog(Base):
    __tablename__ = "processing_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[Optional[str]] = mapped_column(String(255))
    file_size: Mapped[Optional[int]] = mapped_column(Integer)
    processing_status: Mapped[str] = mapped_column(
        Enum('SUCCESS', 'FAILED', 'INVALID_KTP', name='processing_status_enum')
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    confidence_score: Mapped[Optional[float]] = mapped_column(DECIMAL(3, 2))
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())

class DatabaseService:
    """Service untuk berinteraksi dengan database menggunakan SQLAlchemy async"""
    
    def __init__(self):
        """Initialize database service"""
        self.db_host = config("DB_HOST", default="localhost")
        self.db_port = config("DB_PORT", default=3306, cast=int)
        self.db_name = config("DB_NAME", default="ktp_detection")
        self.db_user = config("DB_USER")
        self.db_password = config("DB_PASSWORD")
        
        # Create database URL
        self.database_url = f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        
        # Create async engine
        self.engine = create_async_engine(
            self.database_url,
            echo=config("DEBUG", default=False, cast=bool),
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
    
    async def initialize_database(self) -> bool:
        """
        Initialize database dan create tables jika belum ada
        
        Returns:
            bool: True jika berhasil initialize
        """
        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("Database tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False
    
    @asynccontextmanager
    async def get_session(self):
        """Context manager untuk database session"""
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def save_ktp_data(self, ktp_data: KTPData, confidence_score: float = 0.0, face_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Save extracted KTP data to database with face information
        
        Args:
            ktp_data: KTPData object dengan informasi KTP
            confidence_score: Skor confidence dari analisis
            face_data: Dictionary dengan informasi face detection
            
        Returns:
            Dict[str, Any]: Result dengan ID record yang dibuat
        """
        try:
            async with self.get_session() as session:
                # Convert date format DD-MM-YYYY to datetime
                tanggal_lahir_date = self._convert_date_format(ktp_data.tanggal_lahir)
                
                # Create KTP record
                ktp_record = KTPRecord(
                    nik=ktp_data.nik,
                    nama=ktp_data.nama,
                    tempat_lahir=ktp_data.tempat_lahir,
                    tanggal_lahir=tanggal_lahir_date,
                    jenis_kelamin=ktp_data.jenis_kelamin.value if ktp_data.jenis_kelamin else None,
                    alamat=ktp_data.alamat,
                    rt_rw=ktp_data.rt_rw,
                    kelurahan=ktp_data.kelurahan,
                    kecamatan=ktp_data.kecamatan,
                    kabupaten_kota=ktp_data.kabupaten_kota,
                    provinsi=ktp_data.provinsi,
                    agama=ktp_data.agama,
                    status_perkawinan=ktp_data.status_perkawinan.value if ktp_data.status_perkawinan else None,
                    pekerjaan=ktp_data.pekerjaan,
                    kewarganegaraan=ktp_data.kewarganegaraan,
                    berlaku_hingga=ktp_data.berlaku_hingga,
                    confidence_score=confidence_score,
                    # Face data
                    foto_wajah_path=face_data.get("face_image_path") if face_data else None,
                    face_confidence=face_data.get("confidence", 0.0) if face_data else None,
                    face_quality_notes=face_data.get("quality_notes") if face_data else None
                )
                
                session.add(ktp_record)
                await session.flush()  # Get the ID
                
                return {
                    "id": ktp_record.id,
                    "status": "success",
                    "message": "KTP data berhasil disimpan"
                }
                
        except Exception as e:
            logger.error(f"Error saving KTP data: {str(e)}")
            raise Exception(f"Gagal menyimpan data KTP: {str(e)}")
    
    async def check_nik_exists(self, nik: str) -> bool:
        """
        Check if NIK already exists in database
        
        Args:
            nik: NIK yang akan dicek
            
        Returns:
            bool: True jika NIK sudah ada
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(func.count(KTPRecord.id)).where(KTPRecord.nik == nik)
                )
                count = result.scalar()
                return count > 0
                
        except Exception as e:
            logger.error(f"Error checking NIK existence: {str(e)}")
            return False
    
    async def get_ktp_by_nik(self, nik: str) -> Optional[Dict[str, Any]]:
        """
        Get KTP record by NIK
        
        Args:
            nik: NIK yang dicari
            
        Returns:
            Optional[Dict[str, Any]]: Data KTP jika ditemukan
        """
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    select(KTPRecord).where(KTPRecord.nik == nik)
                )
                ktp_record = result.scalar_one_or_none()
                
                if ktp_record:
                    return {
                        "id": ktp_record.id,
                        "nik": ktp_record.nik,
                        "nama": ktp_record.nama,
                        "tempat_lahir": ktp_record.tempat_lahir,
                        "tanggal_lahir": ktp_record.tanggal_lahir.strftime("%d-%m-%Y") if ktp_record.tanggal_lahir else None,
                        "jenis_kelamin": ktp_record.jenis_kelamin,
                        "alamat": ktp_record.alamat,
                        "rt_rw": ktp_record.rt_rw,
                        "kelurahan": ktp_record.kelurahan,
                        "kecamatan": ktp_record.kecamatan,
                        "kabupaten_kota": ktp_record.kabupaten_kota,
                        "provinsi": ktp_record.provinsi,
                        "agama": ktp_record.agama,
                        "status_perkawinan": ktp_record.status_perkawinan,
                        "pekerjaan": ktp_record.pekerjaan,
                        "kewarganegaraan": ktp_record.kewarganegaraan,
                        "berlaku_hingga": ktp_record.berlaku_hingga,
                        "confidence_score": float(ktp_record.confidence_score) if ktp_record.confidence_score else 0.0,
                        "created_at": ktp_record.created_at.isoformat(),
                        "updated_at": ktp_record.updated_at.isoformat()
                    }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting KTP by NIK: {str(e)}")
            return None
    
    async def search_ktp(self, nama: str = None, limit: int = 10, offset: int = 0) -> Dict[str, Any]:
        """
        Search KTP records by nama
        
        Args:
            nama: Nama yang dicari (optional)
            limit: Limit hasil pencarian
            offset: Offset untuk pagination
            
        Returns:
            Dict[str, Any]: Results dengan data dan pagination info
        """
        try:
            async with self.get_session() as session:
                # Build query
                query = select(KTPRecord)
                count_query = select(func.count(KTPRecord.id))
                
                if nama:
                    search_condition = KTPRecord.nama.like(f"%{nama}%")
                    query = query.where(search_condition)
                    count_query = count_query.where(search_condition)
                
                # Get total count
                total_result = await session.execute(count_query)
                total = total_result.scalar()
                
                # Get data dengan pagination
                query = query.order_by(KTPRecord.created_at.desc()).limit(limit).offset(offset)
                result = await session.execute(query)
                records = result.scalars().all()
                
                # Convert to dict
                data = []
                for record in records:
                    data.append({
                        "id": record.id,
                        "nik": record.nik,
                        "nama": record.nama,
                        "tempat_lahir": record.tempat_lahir,
                        "tanggal_lahir": record.tanggal_lahir.strftime("%d-%m-%Y") if record.tanggal_lahir else None,
                        "jenis_kelamin": record.jenis_kelamin,
                        "alamat": record.alamat,
                        "provinsi": record.provinsi,
                        "confidence_score": float(record.confidence_score) if record.confidence_score else 0.0,
                        "created_at": record.created_at.isoformat()
                    })
                
                return {
                    "total": total,
                    "data": data,
                    "limit": limit,
                    "offset": offset
                }
                
        except Exception as e:
            logger.error(f"Error searching KTP: {str(e)}")
            return {"total": 0, "data": [], "limit": limit, "offset": offset}
    
    async def log_processing(self, log_data: Dict[str, Any]) -> None:
        """
        Log processing attempt
        
        Args:
            log_data: Dictionary dengan data log
        """
        try:
            async with self.get_session() as session:
                log_record = ProcessingLog(
                    original_filename=log_data.get("filename", ""),
                    file_size=log_data.get("file_size", 0),
                    processing_status=log_data.get("status", "FAILED"),
                    error_message=log_data.get("error"),
                    confidence_score=log_data.get("confidence", 0.0),
                    processing_time_ms=log_data.get("time_ms", 0)
                )
                
                session.add(log_record)
                
        except Exception as e:
            logger.error(f"Error logging processing: {str(e)}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics
        
        Returns:
            Dict[str, Any]: Processing statistics
        """
        try:
            async with self.get_session() as session:
                # Get stats by status
                result = await session.execute(
                    select(
                        ProcessingLog.processing_status,
                        func.count(ProcessingLog.id).label('count'),
                        func.avg(ProcessingLog.confidence_score).label('avg_confidence'),
                        func.avg(ProcessingLog.processing_time_ms).label('avg_processing_time')
                    ).group_by(ProcessingLog.processing_status)
                )
                
                stats_rows = result.all()
                
                # Process results into more readable format
                stats = {
                    "total_processed": 0,
                    "success_rate": 0.0,
                    "average_confidence": 0.0,
                    "average_processing_time": 0.0,
                    "status_breakdown": {}
                }
                
                total = 0
                success_count = 0
                
                for row in stats_rows:
                    status = row.processing_status
                    count = row.count
                    stats["status_breakdown"][status] = {
                        "count": count,
                        "avg_confidence": float(row.avg_confidence) if row.avg_confidence else 0.0,
                        "avg_processing_time": float(row.avg_processing_time) if row.avg_processing_time else 0.0
                    }
                    
                    total += count
                    if status == "SUCCESS":
                        success_count = count
                
                stats["total_processed"] = total
                stats["success_rate"] = (success_count / total * 100) if total > 0 else 0.0
                
                return stats
                
        except Exception as e:
            logger.error(f"Error getting processing stats: {str(e)}")
            return {"total_processed": 0, "success_rate": 0.0}
    
    def _convert_date_format(self, date_str: str) -> Optional[datetime]:
        """
        Convert DD-MM-YYYY to datetime
        
        Args:
            date_str: Date string in DD-MM-YYYY format
            
        Returns:
            Optional[datetime]: datetime object or None
        """
        if not date_str:
            return None
        try:
            # Parse DD-MM-YYYY
            day, month, year = date_str.split('-')
            return datetime(int(year), int(month), int(day))
        except:
            return None
    
    async def close(self):
        """Close database connections"""
        await self.engine.dispose()
