@echo off 
cd /d "%%~dp0" 
python -m PyInstaller --noconfirm --clean --onefile --windowed --name SIPSI --add-data "static;static" --add-data "questions_600.json;." --hidden-import flask --hidden-import jinja2 --hidden-import werkzeug --hidden-import license_core --hidden-import scoring_enterprise --collect-all webview app.py 
if errorlevel 1 ( echo BUILD GAGAL & pause & exit /b 1 ) 
copy /Y questions_600.json dist\ 
copy /Y questions_600.json dist\ 
copy /Y scoring_enterprise.py dist\ 
copy /Y license_core.py dist\ 
if not exist dist\static mkdir dist\static 
copy /Y static\logo.png dist\static\ 
if exist sipsi.lic copy /Y sipsi.lic dist\ 
if exist sipsi.lic.sig copy /Y sipsi.lic.sig dist\ 
echo. 
