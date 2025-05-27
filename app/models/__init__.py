"""
Models Package
==============

Berisi Pydantic models dan database configurations
"""

from .ktp_model import KTPData, KTPValidationResult, ProcessingLog

__all__ = ["KTPData", "KTPValidationResult", "ProcessingLog"]
