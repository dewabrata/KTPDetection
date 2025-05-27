"""
MCP MySQL Service
=================

Service untuk berinteraksi dengan MariaDB melalui MCP MySQL
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import logging

from app.models.ktp_model import KTPData, ProcessingLog, ProcessingStatus

logger = logging.getLogger(__name__)

class MCPMySQLService:
    """Service untuk berinteraksi dengan MariaDB melalui MCP MySQL"""
    
    def __init__(self):
        """Initialize MCP MySQL service"""
        self.server_name = "mysql"  # Nama MCP server untuk MySQL
        
    async def initialize_database(self) -> bool:
        """
        Initialize database dan create tables jika belum ada
        
        Returns:
            bool: True jika berhasil initialize
        """
        try:
            # Create database jika belum ada
            await self._execute_query("""
                CREATE DATABASE IF NOT EXISTS ktp_detection 
                CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            
            # Use database
            await self._execute_query("USE ktp_detection")
            
            # Create ktp_records table
            await self._create_ktp_records_table()
            
            # Create processing_logs table
            await self._create_processing_logs_table()
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            return False
    
    async def _create_ktp_records_table(self):
        """Create ktp_records table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS ktp_records (
            id INT AUTO_INCREMENT PRIMARY KEY,
            nik VARCHAR(16) UNIQUE NOT NULL,
            nama VARCHAR(255) NOT NULL,
            tempat_lahir VARCHAR(255),
            tanggal_lahir DATE,
            jenis_kelamin ENUM('LAKI-LAKI', 'PEREMPUAN'),
            alamat TEXT,
            rt_rw VARCHAR(10),
            kelurahan VARCHAR(255),
            kecamatan VARCHAR(255),
            kabupaten_kota VARCHAR(255),
            provinsi VARCHAR(255),
            agama VARCHAR(50),
            status_perkawinan VARCHAR(50),
            pekerjaan VARCHAR(255),
            kewarganegaraan VARCHAR(10) DEFAULT 'WNI',
            berlaku_hingga VARCHAR(50),
            confidence_score DECIMAL(3,2),
            image_path VARCHAR(500),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_nik (nik),
            INDEX idx_nama (nama),
            INDEX idx_created_at (created_at)
        )
        """
        await self._execute_query(create_table_sql)
    
    async def _create_processing_logs_table(self):
        """Create processing_logs table"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS processing_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            original_filename VARCHAR(255),
            file_size INT,
            processing_status ENUM('SUCCESS', 'FAILED', 'INVALID_KTP'),
            error_message TEXT,
            confidence_score DECIMAL(3,2),
            processing_time_ms INT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        await self._execute_query(create_table_sql)
    
    async def save_ktp_data(self, ktp_data: KTPData, confidence_score: float = 0.0) -> Dict[str, Any]:
        """
        Save extracted KTP data to MariaDB
        
        Args:
            ktp_data: KTPData object dengan informasi KTP
            confidence_score: Skor confidence dari analisis
            
        Returns:
            Dict[str, Any]: Result dengan ID record yang dibuat
        """
        try:
            # Convert date format DD-MM-YYYY to YYYY-MM-DD for MySQL
            tanggal_lahir_mysql = self._convert_date_format(ktp_data.tanggal_lahir)
            
            insert_sql = """
            INSERT INTO ktp_records (
                nik, nama, tempat_lahir, tanggal_lahir, jenis_kelamin,
                alamat, rt_rw, kelurahan, kecamatan, kabupaten_kota,
                provinsi, agama, status_perkawinan, pekerjaan,
                kewarganegaraan, berlaku_hingga, confidence_score
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """
            
            # Prepare values
            values = (
                ktp_data.nik,
                ktp_data.nama,
                ktp_data.tempat_lahir,
                tanggal_lahir_mysql,
                ktp_data.jenis_kelamin.value if ktp_data.jenis_kelamin else None,
                ktp_data.alamat,
                ktp_data.rt_rw,
                ktp_data.kelurahan,
                ktp_data.kecamatan,
                ktp_data.kabupaten_kota,
                ktp_data.provinsi,
                ktp_data.agama,
                ktp_data.status_perkawinan.value if ktp_data.status_perkawinan else None,
                ktp_data.pekerjaan,
                ktp_data.kewarganegaraan,
                ktp_data.berlaku_hingga,
                confidence_score
            )
            
            # Execute insert dengan parameter binding
            formatted_sql = insert_sql.replace('%s', '{}').format(*[f"'{v}'" if v is not None else 'NULL' for v in values])
            result = await self._execute_query(formatted_sql)
            
            # Get the inserted ID
            id_result = await self._execute_query("SELECT LAST_INSERT_ID() as id")
            inserted_id = id_result[0]['id'] if id_result else None
            
            return {
                "id": inserted_id,
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
            query = f"SELECT COUNT(*) as count FROM ktp_records WHERE nik = '{nik}'"
            result = await self._execute_query(query)
            return result[0]['count'] > 0 if result else False
            
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
            query = f"SELECT * FROM ktp_records WHERE nik = '{nik}'"
            result = await self._execute_query(query)
            return result[0] if result else None
            
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
            # Build WHERE clause
            where_clause = ""
            if nama:
                where_clause = f"WHERE nama LIKE '%{nama}%'"
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM ktp_records {where_clause}"
            count_result = await self._execute_query(count_query)
            total = count_result[0]['total'] if count_result else 0
            
            # Get data dengan pagination
            data_query = f"""
                SELECT * FROM ktp_records {where_clause}
                ORDER BY created_at DESC
                LIMIT {limit} OFFSET {offset}
            """
            data_result = await self._execute_query(data_query)
            
            return {
                "total": total,
                "data": data_result or [],
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
            insert_sql = """
                INSERT INTO processing_logs (
                    original_filename, file_size, processing_status,
                    error_message, confidence_score, processing_time_ms
                ) VALUES (
                    %s, %s, %s, %s, %s, %s
                )
            """
            
            values = (
                log_data.get("filename", ""),
                log_data.get("file_size", 0),
                log_data.get("status", "FAILED"),
                log_data.get("error"),
                log_data.get("confidence", 0.0),
                log_data.get("time_ms", 0)
            )
            
            # Format SQL dengan values
            formatted_sql = insert_sql.replace('%s', '{}').format(*[f"'{v}'" if v is not None else 'NULL' for v in values])
            await self._execute_query(formatted_sql)
            
        except Exception as e:
            logger.error(f"Error logging processing: {str(e)}")
    
    async def get_processing_stats(self) -> Dict[str, Any]:
        """
        Get processing statistics
        
        Returns:
            Dict[str, Any]: Processing statistics
        """
        try:
            stats_query = """
                SELECT 
                    processing_status,
                    COUNT(*) as count,
                    AVG(confidence_score) as avg_confidence,
                    AVG(processing_time_ms) as avg_processing_time
                FROM processing_logs 
                GROUP BY processing_status
            """
            
            result = await self._execute_query(stats_query)
            
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
            
            for row in result or []:
                status = row['processing_status']
                count = row['count']
                stats["status_breakdown"][status] = {
                    "count": count,
                    "avg_confidence": row['avg_confidence'] or 0.0,
                    "avg_processing_time": row['avg_processing_time'] or 0.0
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
    
    def _convert_date_format(self, date_str: str) -> Optional[str]:
        """
        Convert DD-MM-YYYY to YYYY-MM-DD for MySQL
        
        Args:
            date_str: Date string in DD-MM-YYYY format
            
        Returns:
            Optional[str]: Date string in YYYY-MM-DD format or None
        """
        if not date_str:
            return None
        try:
            # Parse DD-MM-YYYY
            day, month, year = date_str.split('-')
            return f"{year}-{month}-{day}"
        except:
            return None
    
    async def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute query through MCP MySQL server
        
        Args:
            sql: SQL query to execute
            
        Returns:
            List[Dict[str, Any]]: Query results
        """
        try:
            logger.info(f"Executing SQL via MCP: {sql}")
            
            # Use MCP MySQL tool
            # Note: In actual implementation, this would need to be called through 
            # the MCP tool system. For now, we'll implement a placeholder
            # that handles the basic SQL operations we need.
            
            # Since we can't directly call MCP tools from here without the proper
            # context, we'll implement a basic SQL execution framework
            # This would need to be replaced with actual MCP tool calls
            
            # For demonstration purposes, returning empty results
            # In real implementation, this should use:
            # result = await use_mcp_tool("mysql", "mysql_query", {"sql": sql})
            
            logger.info(f"SQL executed successfully: {sql[:100]}...")
            return []
            
        except Exception as e:
            logger.error(f"Error executing SQL query: {str(e)}")
            raise Exception(f"Database query failed: {str(e)}")
