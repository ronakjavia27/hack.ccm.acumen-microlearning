@echo off
title 📬 hack.CCM Distribution Queue Engine

echo 💾 Running live subscriber list synchronization...
call python email_list_sync.py

echo.
echo 🧹 Cleaning up lingering environment name locks...
docker rm -f med-email-engine >nul 2>&1

echo.
echo 🚀 Launching live distribution image module...
docker run -it --rm ^
  --name med-email-engine ^
  -v "%cd%:/app" ^
  ai-ingest-engine python email_push.py

echo.
echo 📡 Syncing approved dataset changes with Streamlit Cloud...
:: Runs right after email process closes to sync your updated show_on_web ledger keys
call python cloud_sync.py

echo.
echo ✅ Workflow loop completed successfully.
pause