@echo off
ECHO "Bem-vindo ao Analisador Parlamentar!"

set VENV_DIR=venv

REM 1. Verifica se o Python está instalado
python --version > NUL 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo "ERRO: Python nao encontrado. Por favor, instale o Python 3."
    pause
    exit /b 1
)

REM 2. Cria o ambiente virtual (se ainda não existir)
if not exist "%VENV_DIR%" (
    echo "Criando ambiente virtual (venv)..."
    python -m venv %VENV_DIR%
)

REM 3. Ativa o ambiente virtual e instala dependências
echo "Ativando venv e instalando dependencias..."
call %VENV_DIR%\Scripts\activate.bat
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo "ERRO: Falha ao instalar dependencias."
    pause
    exit /b 1
)

REM 4. Inicia o aplicativo principal (o painel Tkinter)
echo "##################################################"
echo "  Instalacao concluida!"
echo "  Abrindo o painel de controle..."
echo "##################################################"

python main_app.py

pause