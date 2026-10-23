@echo off
chcp 65001 >nul
echo ========================================================
echo  DONG BO VA NAP DU LIEU LAPTOP VAO DATABASE (LOCAL)
echo ========================================================

echo.
echo [1/3] Dang keo du lieu moi nhat tu GitHub...
:: Tu dong bo qua thay doi file Excel cuc bo de tranh xung dot khi pull
git checkout -- *.xlsx 2>nul
git pull origin main
if %errorlevel% neq 0 (
    echo [LOI] Khong the pull du lieu tu Git!
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Dang nap du lieu vao bang raw_laptop_data...
python import_db.py
if %errorlevel% neq 0 (
    echo [LOI] Nap du lieu vao raw_laptop_data that bai!
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Dang lam sach va nap vao bang clean_laptop_data...
python clean_data.py
if %errorlevel% neq 0 (
    echo [LOI] Lam sach du lieu that bai!
    pause
    exit /b %errorlevel%
)

echo.
echo ========================================================
echo  HOAN TAT DONG BO VA NAP DU LIEU VAO POSTGRESQL!
echo ========================================================
pause
