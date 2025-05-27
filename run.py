#!/usr/bin/env python3
"""
KTP Detection Application Runner
================================

Script untuk menjalankan aplikasi KTP Detection
"""

import uvicorn
import sys
import os
from decouple import config

def main():
    """Main function untuk menjalankan aplikasi"""
    
    # Get configuration from environment
    host = config("HOST", default="0.0.0.0")
    port = config("PORT", default=8000, cast=int)
    debug = config("DEBUG", default=True, cast=bool)
    
    print("🚀 Starting KTP Detection Application...")
    print(f"📍 Server: http://{host}:{port}")
    print(f"🐛 Debug Mode: {debug}")
    print(f"📚 API Docs: http://{host}:{port}/docs")
    print(f"💾 Health Check: http://{host}:{port}/api/health")
    print("-" * 50)
    
    # Check if required environment variables are set
    required_vars = ["GEMINI_API_KEY"]
    missing_vars = []
    
    for var in required_vars:
        if not config(var, default=None):
            missing_vars.append(var)
    
    if missing_vars:
        print("❌ Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables in your .env file")
        sys.exit(1)
    
    try:
        # Run the application
        uvicorn.run(
            "app.main:app",
            host=host,
            port=port,
            reload=debug,
            log_level="info" if debug else "warning"
        )
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
