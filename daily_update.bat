@echo off
REM Mukten daily fetch (for Task Scheduler, no prompt, no pause)
cd /d "C:\Users\jun\Documents\01웹페이지\sung-food-map"
C:\ProgramData\Anaconda3\python.exe updater\fetch_mukten.py >> updater\daily.log 2>&1
