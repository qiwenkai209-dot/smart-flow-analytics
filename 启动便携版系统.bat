@echo off
chcp 65001 >nul
title Smart Flow Analytics
echo 正在启动 Smart Flow Analytics 便携版...
cd /d "%~dp0dist\SmartFlowAnalytics"
start "" "%~dp0dist\SmartFlowAnalytics\SmartFlowAnalytics.exe"
exit
