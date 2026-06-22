@echo off
chcp 65001 >nul
echo ===================================
echo  ISFプロジェクト セットアップ
echo ===================================
echo.
echo 依存パッケージをインストールします...
cd /d "%~dp0"
python -m pip install -r requirements.txt
echo.
echo セットアップが完了しました。
echo start.bat をダブルクリックして起動してください。
pause
