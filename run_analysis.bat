@echo off
cd /d "C:\Users\jeffr\OneDrive\Documents\VS Code\Keltner Channels and Bollinger Bands"
echo.
echo ========================================
echo FLNG Technical Analysis - Manual Run
echo ========================================
echo.
echo Running analysis...
python fetch_flng_data.py
echo.
echo ========================================
echo Analysis complete!
echo ========================================
echo.
echo View results:
echo   S3: s3://flng-trading-data/
echo.
pause
