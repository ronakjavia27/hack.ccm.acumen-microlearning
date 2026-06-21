@echo off
title 📬 hack.CCM Distribution Queue Engine

echo 💾 Running live subscriber list synchronization...
call python email_list_sync.py

echo.
echo 🧹 Cleaning up lingering environment name locks...
:: Forces any background ghost container with this name to release its lock cleanly
docker rm -f med-email-engine >nul 2>&1

echo.
echo 🚀 Launching live distribution image module...
docker run -it --rm ^
  --name med-email-engine ^
  -v "%cd%:/app" ^
  ai-ingest-engine python email_push.py

echo.
echo ✅ Distribution routine finalized cleanly.
pause