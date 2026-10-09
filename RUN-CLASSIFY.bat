@echo off
cd /d "%~dp0"
echo ============================================
echo   Health-app review analysis - LLM classification
echo ============================================
echo.
echo Free key: https://aistudio.google.com/apikey   (Gemini, slow but free)
echo Claude:   set ANTHROPIC_API_KEY before running instead (faster; LABEL_DECODER_MODEL=claude-haiku-4-5 is cheapest)
echo Key is used for this run only and never saved.
echo.
set /p GEMINI_API_KEY=Paste a Gemini key and press Enter:
set PYTHONIOENCODING=utf-8
echo.
echo --- Step 1: the 300 validation reviews (1-2 min) ---
python src\classify.py --mode llm --only-validation
echo.
echo --- Step 2: agreement with your hand labels (needs validation\to_label.csv filled) ---
python src\validate.py
echo.
set /p FULL=Classify all 120,000 reviews now? Gemini free tier: several hours, resumable. (Y/N):
if /i "%FULL%"=="Y" (
    python src\classify.py --mode llm
    python src\run_queries.py --classifier llm
    python src\report.py
)
echo.
echo Done. Outputs in output\ (findings.md, charts\, validation_report.md)
pause
