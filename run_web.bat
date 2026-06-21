@echo off

echo.
echo Launching User Interface Dashboard Panel...

docker rm -f ccm-frontend >nul 2>&1
docker run -it --name ccm-frontend -p 8501:8501 -v "%cd%/input_pdfs:/app/input_pdfs" ai-ingest-engine streamlit run web_app.py --server.port=8501 --server.address=0.0.0.0
pause