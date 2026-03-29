@echo off
echo 🎭 Setting up DeepFace for Smart Attendance System
echo ================================================

echo.
echo 📦 Installing DeepFace and dependencies...
cd backend
python install_deepface.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ DeepFace setup completed successfully!
    echo.
    echo 🚀 Next steps:
    echo    1. Start the backend server: python -m backend.main
    echo    2. Start the frontend: cd frontend && npm run dev
    echo    3. Test DeepFace API: http://localhost:8000/api/v1/deepface/health
    echo.
) else (
    echo.
    echo ❌ DeepFace setup failed. Please check the errors above.
    echo.
)

pause