@echo off
chcp 65001 >nul
title Smart Flow Analytics - 仿真演示
echo 正在以仿真演示模式启动 Smart Flow Analytics...
cd /d "%~dp0dist\SmartFlowAnalytics"
start "" "%~dp0dist\SmartFlowAnalytics\SmartFlowAnalytics.exe" --demo
exit
