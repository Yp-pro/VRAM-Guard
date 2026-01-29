@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ==========================================
echo       ОТПРАВКА VRAM GUARD НА GITHUB
echo ==========================================
echo.

:: Проверка, инициализирован ли Git
if not exist ".git" (
    echo [1/4] Инициализация Git...
    git init
    echo [2/4] Привязка к удаленному репозиторию...
    git remote add origin https://github.com/Yp-pro/VRAM-Guard.git
) else (
    echo [!] Репозиторий уже инициализирован.
    :: На случай, если ссылка изменилась, обновляем её
    git remote set-url origin https://github.com/Yp-pro/VRAM-Guard.git
)

:: Добавляем файлы
echo [3/4] Добавление файлов...
:: Git автоматически проигнорирует папку venv и LibreHardwareMonitor, 
:: если ты создал файл .gitignore, как мы обсуждали раньше.
git add .

:: Создаем коммит
set /p msg="Введите описание изменений (или нажмите Enter для 'Update v1.1'): "
if "%msg%"=="" set msg=Update v1.1
git commit -m "%msg%"

:: Отправка
echo [4/4] Отправка на GitHub...
git branch -M main
git push -u origin main

echo.
echo ==========================================
echo             ВСЁ ГОТОВО!
echo ==========================================
pause