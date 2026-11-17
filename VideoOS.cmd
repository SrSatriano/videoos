@echo off
setlocal
title Video OS - Sistema de Edicao em Massa
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0VideoOS.ps1" %*
echo.
echo Pressione qualquer tecla para fechar.
pause >nul
