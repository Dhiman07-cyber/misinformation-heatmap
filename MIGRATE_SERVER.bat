@echo off
echo ========================================
echo Enhanced Fake News Detection Server
echo ========================================
echo Starting server with existing data...
echo Database size: ~185MB with processed articles
echo.
cd /d "D:\Project\Cloud Project"
python backend/main_application.py
echo.
echo Server stopped. Press any key to exit.
pause