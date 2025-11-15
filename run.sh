#!/bin/bash

# Define o nome da pasta do venv
VENV_DIR="venv"

echo "Bem-vindo ao Analisador Parlamentar!"

# 1. Verifica se o Python 3 está instalado
if ! command -v python3 &> /dev/null
then
    echo "ERRO: Python 3 não encontrado. Por favor, instale o Python 3."
    exit 1
fi

# 2. Cria o ambiente virtual (se ainda não existir)
if [ ! -d "$VENV_DIR" ]
then
    echo "Criando ambiente virtual (venv)..."
    python3 -m venv $VENV_DIR
fi

# 3. Ativa o ambiente virtual
echo "Ativando venv..."
source $VENV_DIR/bin/activate

# 4. Instala as dependências
echo "Instalando dependências do requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERRO: Falha ao instalar dependências."
    deactivate
    exit 1
fi

# 5. Inicia o aplicativo principal (o painel Tkinter)
echo "##################################################"
echo "  Instalação concluída!"
echo "  Abrindo o painel de controle..."
echo "##################################################"

python3 main_app.py

# Desativa o venv ao sair
deactivate