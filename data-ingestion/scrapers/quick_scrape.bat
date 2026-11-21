@echo off
echo 🚀 VoYatra Hotel Scraper - Quick Run
echo =====================================
echo.

if "%1"=="" (
    echo Usage: %0 [city] [max_hotels] [reviews_per_hotel]
    echo.
    echo Examples:
    echo   %0 Mumbai 5 3
    echo   %0 Delhi 10 5
    echo   %0 Bangalore 8 4
    echo.
    echo Running default: Mumbai 5 3
    python run_hotel_scraper.py Mumbai 5 3
) else (
    echo Running: %1 %2 %3
    python run_hotel_scraper.py %1 %2 %3
)

echo.
echo ✅ Scraping completed!
pause