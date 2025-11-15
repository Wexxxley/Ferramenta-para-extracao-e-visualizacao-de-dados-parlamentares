from contextlib import closing
import socket
import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import queue
import os
import webbrowser
import time
import uvicorn
from api.tratamentoDados.processador import run_data_processing
from api.main import app as fastapi_app
from style_config import configure_styles

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Analisador Parlamentar")
        self.root.geometry("650x500")
        self.root.configure(bg="#1e1e2f") # Cor base da janela

        self.queue = queue.Queue()
        
        self.setup_styles()
        
        self.create_widgets()
        self.root.after(100, self.process_queue)

    def setup_styles(self):
        """Chama a configuração de estilo externa e armazena cores extras."""
        # A função configure_styles aplica os estilos ttk globalmente
        # e retorna as cores que precisamos para widgets customizados.
        self.widget_colors = configure_styles()

    def create_widgets(self):
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Header ---
        ttk.Label(main_frame, text="Analisador Parlamentar", style="Header.TLabel").pack(pady=(0, 10))

        # --- Seção de Input ---
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=5)
        ttk.Label(input_frame, text="Selecione o Ano:").pack(side=tk.LEFT, padx=(0, 5))
        self.year_combobox = ttk.Combobox(
            input_frame,
            values=[str(y) for y in range(2011, 2025)],
            state="readonly",
            width=10,
            style="TCombobox"
        )
        self.year_combobox.pack(side=tk.LEFT)
        self.year_combobox.current(0)
        self.start_button = ttk.Button(input_frame, text="Iniciar Processamento", command=self.start_process_thread)
        self.start_button.pack(side=tk.RIGHT, padx=(10, 0))

        # --- Seção de Progresso ---
        ttk.Label(main_frame, text="Progresso:").pack(anchor=tk.W, pady=(15, 0))
        self.progress_bar = ttk.Progressbar(main_frame, orient='horizontal', mode='determinate', length=400, style="TProgressbar", maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=4)

        # --- Seção de Log ---
        ttk.Label(main_frame, text="Log de Atividades:").pack(anchor=tk.W, pady=(15, 0))
        # Use as cores retornadas pela função de estilo
        self.log_area = scrolledtext.ScrolledText(
            main_frame, 
            wrap=tk.WORD, 
            height=15, 
            font=("Consolas", 11), 
            bg=self.widget_colors["log_bg"],
            fg=self.widget_colors["log_fg"],
            insertbackground=self.widget_colors["cursor_color"]
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, pady=2)
        self.log_area.configure(state='disabled')

    def log(self, message):
        self.log_area.configure(state='normal')
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state='disabled')

    def process_queue(self):
        try:
            while not self.queue.empty():
                message_type, data = self.queue.get_nowait()
                if message_type == 'log':
                    self.log(data)
                elif message_type == 'progress':
                    self.progress_bar['value'] = data
                elif message_type == 'done':
                    self.start_button.config(state="normal")
                    self.log(">>> PROCESSO FINALIZADO <<<")
        finally:
            self.root.after(100, self.process_queue)

    def start_process_thread(self):
        year_str = self.year_combobox.get()
        if not year_str.isdigit():
            self.log("Erro: Por favor, selecione um ano válido.")
            return

        self.start_button.config(state="disabled")
        self.progress_bar['value'] = 0
        self.progress_bar['maximum'] = 100  # Reset maximum for each run
        self.log_area.configure(state='normal')
        self.log_area.delete('1.0', tk.END)
        self.log_area.configure(state='disabled')

        threading.Thread(
            target=self.main_orchestrator,
            args=(int(year_str),),
            daemon=True
        ).start()


    def find_free_port(self):
            """Encontra e retorna uma porta TCP livre no localhost."""
            with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
                s.bind(('127.0.0.1', 0)) # O 0 pede ao SO uma porta livre
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                return s.getsockname()[1] # Retorna o número da porta alocada
            
    def main_orchestrator(self, year):
        def progress_callback(msg_type, data):
            self.queue.put((msg_type, data))

        try:
            success = run_data_processing(year, progress_callback)
            if not success:
                raise Exception("O processamento de dados falhou.")

            self.queue.put(('log', "Procurando uma porta livre para a API..."))
            free_port = self.find_free_port()

            self.queue.put(('log', "Iniciando servidor da API local..."))
            os.environ['DATABASE_YEAR'] = str(year)

            api_thread = threading.Thread(
                target=lambda: uvicorn.run(fastapi_app, host="127.0.0.1", port=free_port, log_level="warning"),
                daemon=True
            )
            api_thread.start()
            time.sleep(5) 

            self.queue.put(('log', f"API rodando em http://127.0.0.1:{free_port}"))

            self.queue.put(('log', "Abrindo a interface de visualização..."))
            html_file_path = os.path.join("frontend", "index.html")
            
            # Passa a porta para o frontend através da URL
            webbrowser.open(f'http://127.0.0.1:{free_port}/?year={year}&port={free_port}')


        except Exception as e:
            self.queue.put(('log', f"ERRO CRÍTICO: {e}"))
        finally:
            self.queue.put(('done', None))

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()