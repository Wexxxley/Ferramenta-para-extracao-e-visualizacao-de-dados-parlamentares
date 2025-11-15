# 🚀 Analisador Parlamentar

Este projeto apresenta uma prova de conceito (POC) de uma arquitetura de software distribuída como um aplicativo executável, projetada para simplificar a coleta, tratamento, armazenamento e a análise de dados abertos da Câmara dos Deputados do Brasil.

Uma ferramenta para processar, analisar e visualizar dados de despesas da Câmara dos Deputados do Brasil.

Este é um projeto híbrido que utiliza uma interface desktop (criada com Tkinter) para orquestrar o processamento de dados e o lançamento de um backend de API (FastAPI). O backend, por sua vez, serve os dados processados para um frontend de visualização (HTML/JS) que é aberto no navegador.

## ✨ Funcionalidades

  * **Painel de Controle Desktop:** Uma interface simples para selecionar o ano e iniciar o processamento.
  * **Processamento de Dados:** Rotinas para baixar (se necessário), limpar e preparar os dados de despesas parlamentares.
  * **API Local:** Um servidor FastAPI é iniciado localmente em uma porta livre para servir os dados processados ao frontend.
  * **Visualização Web:** Uma interface web (frontend) que consome a API local e exibe os dados de forma interativa.

## 💻 Tecnologias Utilizadas

  * **Painel de Controle:** Python + Tkinter
  * **Backend (API):** Python + FastAPI + Uvicorn
  * **Processamento:** Python (com bibliotecas como `requests`, `sqlmodel`)
  * **Frontend:** HTML, CSS, JavaScript

-----

## ⚙️ Pré-requisitos

Antes de começar, garanta que você tenha os seguintes softwares instalados:

1.  **[Python 3](https://www.python.org/downloads/)** (versão 3.9 ou superior)
2.  **[Git](https://www.google.com/search?q=https://git-scm.com/downloads)** (para clonar o repositório)

### 🐧 **Atenção Usuários de Linux\!**

Este projeto usa `Tkinter`, que **não** é instalado pelo `pip`. Você precisa instalá-lo manualmente pelo gerenciador de pacotes do seu sistema.

Para sistemas baseados em Debian/Ubuntu (como o Linux Mint), rode:

```bash
sudo apt install python3-tk
```

-----

## 🏃 Como Executar o Projeto

Foi criado scripts automáticos para facilitar a instalação e execução.

### 1\. Clone o Repositório

```bash
git clone https://github.com/Wexxxley/Ferramenta-para-extra-o-e-visualiza-o-de-dados-parlamentares.git
cd Ferramenta-para-extra-o-e-visualiza-o-de-dados-parlamentares
```

### 2\. Execute o Script de Instalação

Os scripts irão criar um ambiente virtual (`venv`), instalar todas as dependências do `requirements.txt` e, por fim, iniciar o painel de controle.

#### 🪟 No Windows:

1.  Encontre o arquivo `run.bat` na pasta.
2.  Dê dois cliques nele.
3.  O terminal será aberto, o processo de instalação começará e, ao final, a janela do painel de controle aparecerá.

#### 🐧 No Linux ou MacOS:

1.  Abra um terminal na pasta do projeto.
2.  Dê permissão de execução ao script (apenas na primeira vez):
    ```bash
    chmod +x run.sh
    ```
3.  Execute o script:
    ```bash
    ./run.sh
    ```
4.  O processo de instalação começará no terminal e, ao final, a janela do painel de controle aparecerá.

### 3\. Use a Aplicação

1.  Com o painel de controle (janela Tkinter) aberto, **selecione o ano** que deseja analisar.
2.  Clique em **"Iniciar Processamento"**.
3.  Acompanhe o progresso pela caixa de "Log de Atividades".
4.  Ao final, a aplicação irá **iniciar o servidor da API** e **abrir a interface de visualização** automaticamente no seu navegador padrão.