# Em style_config.py
from tkinter import ttk

def configure_styles():
    """
    Configura e aplica um tema personalizado para os widgets ttk.
    Retorna um dicionário com cores para widgets não-ttk.
    """
    # --- Paleta de Cores (Escuro e Verde) ---
    dark_bg = "#1e1e2f"
    light_bg = "#28283d"
    text_primary = "#f0f0f0"
    text_secondary = "#a0a0b0"
    accent_green = "#caf729"
    progress_bar_green = "#79dd7e"
    border_color = "#40405a"

    style = ttk.Style()
    style.theme_use("clam")

    # --- Configuração dos Estilos TTK ---
    style.configure("TFrame", background=dark_bg)
    
    style.configure("TLabel", background=dark_bg, foreground=text_secondary, font=("Segoe UI", 12))
    style.configure("Header.TLabel", foreground=text_primary, font=("Segoe UI", 18, "bold"))

    style.configure("TButton",
                    background=accent_green,
                    foreground=dark_bg,
                    font=("Segoe UI", 12, "bold"),
                    bordercolor=accent_green)
    style.map("TButton", background=[("active", accent_green)])

    style.configure("TCombobox",
                    fieldbackground=dark_bg,        # Fundo do campo de texto
                    background=accent_green,      # Fundo do BOTÃO da seta
                    foreground=text_primary,      # Cor do texto principal no campo
                    arrowcolor=dark_bg,           # Cor da SETA (escura para contrastar)
                    selectbackground=light_bg,    # Cor de fundo dos itens na lista dropdown
                    selectforeground=accent_green,# Cor do texto dos itens na lista dropdown
                    bordercolor=border_color,
                    font=("Segoe UI", 12))
    
    # Garante que o texto dentro do campo seja branco quando não estiver focado
    style.map('TCombobox', 
              fieldbackground=[('readonly', dark_bg)], 
              foreground=[('readonly', text_primary)])

    style.configure("TProgressbar",
                    troughcolor=border_color,
                    background=progress_bar_green,
                    thickness=20,
                    borderwidth=0)

    # Retorna cores para widgets que não são ttk
    return {
        "log_bg": light_bg,
        "log_fg": text_primary,
        "cursor_color": accent_green
    }