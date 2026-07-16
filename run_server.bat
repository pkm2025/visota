@echo off
cd /d C:\mmm\visota
start "" /B .venv\Scripts\python.exe manage.py runserver 0.0.0.0:8903 --noreload
