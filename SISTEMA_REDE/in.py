import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import socket
from datetime import datetime
import os

# --- TENTATIVA DE IMPORTAR BIBLIOTECAS OPCIONAIS ---
try:
    from fpdf import FPDF
    FPDF_DISPONIVEL = True
except ImportError:
    FPDF_DISPONIVEL = False

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_DISPONIVEL = True
except ImportError:
    MATPLOTLIB_DISPONIVEL = False

# --- Configurações do Cliente de Rede ---
HOST = '127.0.0.1'
PORTA = 8080
ARQUIVO_USUARIOS = "usuarios.csv"

# --- Estilos e Cores ---
COR_FUNDO = "#2e2e2e"
COR_FUNDO_FRAME = "#3e3e3e"
COR_TEXTO = "#ffffff"
COR_DESTAQUE = "#007acc"
COR_BOTAO = "#5a5a5a"
FONTE_TITULO = ("Arial", 18, "bold")
FONTE_NORMAL = ("Arial", 10)
FONTE_LABEL = ("Arial", 11, "bold")

# --- Cliente de Rede e Funções de Login/Dados ---
class ClienteServidor:
    def enviar_comando(self, comando):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORTA))
                s.sendall(comando.encode('utf-8'))
                resposta = s.recv(4096).decode('utf-8')
                return resposta
        except ConnectionRefusedError:
            messagebox.showerror("Erro de Conexão", f"Não foi possível conectar ao servidor em {HOST}:{PORTA}.\nVerifique se o programa em C (servidor) está em execução.")
            return "ERRO;Falha na conexao"
        except Exception as e:
            return f"ERRO;{e}"

def processar_resposta_servidor(resposta):
    """Função centralizada para processar e validar todas as respostas do servidor."""
    if not resposta:
        messagebox.showerror("Erro de Comunicação", "O servidor retornou uma resposta vazia.")
        return None, None

    parts = resposta.split(";", 1)
    tipo = parts[0]
    dados_str = parts[1] if len(parts) > 1 else ""

    if tipo == "ERRO":
        messagebox.showerror("Erro do Servidor", dados_str or "Erro não especificado.")
        return None, None
    
    if tipo == "VAZIO":
        return tipo, []
    
    if tipo == "DADOS":
        if not dados_str: return tipo, []
        return tipo, [item.split(';') for item in dados_str.split('|')]
    
    if tipo in ["SUCESSO", "IA_RESULTADO"]:
        return tipo, dados_str

    messagebox.showwarning("Aviso", f"Resposta desconhecida do servidor: {resposta}")
    return None, None

def verificar_login_local(usuario, senha):
    if usuario == "admin" and senha == "admin":
        return "Admin", "ativo"
    
    if not os.path.exists(ARQUIVO_USUARIOS):
        return None, None
        
    with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
        for linha in f:
            try:
                partes = linha.strip().split(';')
                u, s, perfil, status = partes[0], partes[1], partes[2], partes[3]
                if u == usuario and s == senha:
                    return perfil, status
            except (ValueError, IndexError):
                continue
    return None, None

def registrar_usuario_local(usuario, senha, perfil, status="ativo"):
    if not os.path.exists(ARQUIVO_USUARIOS):
        with open(ARQUIVO_USUARIOS, "w", encoding="utf-8"): pass
    
    with open(ARQUIVO_USUARIOS, "r+", encoding="utf-8") as f:
        linhas = f.readlines()
        for linha in linhas:
            if linha.strip().split(';')[0] == usuario:
                return False, "Usuário já existe."
        f.write(f"{usuario};{senha};{perfil};{status}\n")
    return True, "Usuário registrado com sucesso."

def ler_usuarios_local():
    if not os.path.exists(ARQUIVO_USUARIOS):
        return []
    with open(ARQUIVO_USUARIOS, "r", encoding="utf-8") as f:
        usuarios = []
        for linha in f:
            if linha.strip():
                partes = linha.strip().split(';')
                while len(partes) < 4:
                    partes.append('ativo') 
                usuarios.append(partes)
        return usuarios

def excluir_usuario_local(usuario_para_excluir):
    usuarios = ler_usuarios_local()
    usuarios_atualizados = [u for u in usuarios if u[0] != usuario_para_excluir]
    
    with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
        for u in usuarios_atualizados:
            f.write(f"{';'.join(u)}\n")
    return True

def autorizar_usuario_local(usuario_para_autorizar):
    usuarios = ler_usuarios_local()
    for u in usuarios:
        if u[0] == usuario_para_autorizar:
            u[3] = "ativo"
            break
    
    with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
        for u in usuarios:
            f.write(f"{';'.join(u)}\n")
    return True

# --- Classe Principal da Aplicação ---
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cliente = ClienteServidor()
        self.title("ConectaPro - Sistema de Gestão Acadêmica")
        self.geometry("450x400")
        self.configure(bg=COR_FUNDO)

        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure("TFrame", background=COR_FUNDO)
        style.configure("TLabel", background=COR_FUNDO_FRAME, foreground=COR_TEXTO, font=FONTE_NORMAL)
        style.configure("TButton", background=COR_BOTAO, foreground=COR_TEXTO, font=FONTE_NORMAL, borderwidth=1, focusthickness=3, focuscolor=COR_DESTAQUE)
        style.map("TButton", background=[('active', COR_DESTAQUE)])
        style.configure("TEntry", fieldbackground=COR_BOTAO, foreground=COR_TEXTO, insertbackground=COR_TEXTO)
        style.configure("Treeview", background=COR_FUNDO_FRAME, foreground=COR_TEXTO, fieldbackground=COR_FUNDO_FRAME, font=FONTE_NORMAL, rowheight=25)
        style.map("Treeview", background=[('selected', COR_DESTAQUE)])
        style.configure("Treeview.Heading", background=COR_BOTAO, foreground=COR_TEXTO, font=("Arial", 10, "bold"))
        style.configure("TNotebook", background=COR_FUNDO, borderwidth=0)
        style.configure("TNotebook.Tab", background=COR_BOTAO, foreground=COR_TEXTO, padding=[10, 5], font=("Arial", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", COR_DESTAQUE)])
        style.configure("TLabelframe", background=COR_FUNDO_FRAME, foreground=COR_TEXTO, font=("Arial", 12))
        style.configure("TLabelframe.Label", background=COR_FUNDO_FRAME, foreground=COR_TEXTO)

        self.container = tk.Frame(self, bg=COR_FUNDO)
        self.container.pack(fill="both", expand=True)
        
        # --- Rodapé ---
        footer_frame = tk.Frame(self, bg=COR_FUNDO)
        footer_frame.pack(fill="x", side="bottom")
        tk.Label(
            footer_frame, 
            text="Copyright © 1997-2025 CON - CONECTAPRO. Todos os direitos reservados. Política de Privacidade", 
            font=("Arial", 8), 
            bg=COR_FUNDO, 
            fg=COR_TEXTO
        ).pack(pady=5)

        self._frame = None
        self.trocar_frame(TelaLogin)

    def trocar_frame(self, frame_class, dados_usuario=None):
        if self._frame is not None:
            self._frame.destroy()
        self._frame = frame_class(self.container, self, dados_usuario=dados_usuario)
        self._frame.pack(fill="both", expand=True)

# --- Telas de Login e Registro ---
class TelaLogin(tk.Frame):
    def __init__(self, parent, controller, dados_usuario=None):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        self.controller.geometry("450x400")
        
        main_frame = tk.Frame(self, bg=COR_FUNDO)
        main_frame.place(relx=0.5, rely=0.5, anchor="center")

        tk.Label(main_frame, text="Login - ConectaPro", font=FONTE_TITULO, bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=20)
        
        frame_login = tk.Frame(main_frame, bg=COR_FUNDO_FRAME, padx=30, pady=30, relief="ridge", borderwidth=2)
        frame_login.pack()

        tk.Label(frame_login, text="Usuário:", font=FONTE_LABEL, bg=COR_FUNDO_FRAME, fg=COR_TEXTO).grid(row=0, column=0, sticky="w", pady=5)
        self.usuario_entry = ttk.Entry(frame_login, width=30, font=FONTE_NORMAL)
        self.usuario_entry.grid(row=0, column=1, pady=5, padx=10)
        
        tk.Label(frame_login, text="Senha:", font=FONTE_LABEL, bg=COR_FUNDO_FRAME, fg=COR_TEXTO).grid(row=1, column=0, sticky="w", pady=5)
        self.senha_entry = ttk.Entry(frame_login, show="*", width=30, font=FONTE_NORMAL)
        self.senha_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Button(main_frame, text="Entrar", command=self.fazer_login, style="TButton", padding=10).pack(pady=20)
        
    def fazer_login(self):
        usuario = self.usuario_entry.get()
        senha = self.senha_entry.get()
        perfil, status = verificar_login_local(usuario, senha)

        if status == "pendente":
            messagebox.showwarning("Acesso Pendente", "Sua conta está aguardando autorização de um administrador.")
            return

        if status != "ativo":
            messagebox.showerror("Erro de Login", "Usuário ou senha inválidos.")
            return

        if perfil == "Admin":
            self.controller.trocar_frame(PainelAdmin)
        elif perfil == "Professor":
            self.controller.trocar_frame(PainelProfessor, dados_usuario={"nome": usuario})
        elif perfil == "Aluno":
            resposta = self.controller.cliente.enviar_comando("LISTAR_ALUNOS")
            tipo, alunos = processar_resposta_servidor(resposta)
            if tipo == "DADOS":
                for aluno in alunos:
                    if len(aluno) > 1 and aluno[1].lower() == usuario.lower():
                        dados_aluno = {"id": aluno[0], "nome": aluno[1], "turma_id": aluno[5]}
                        self.controller.trocar_frame(PainelAluno, dados_usuario=dados_aluno)
                        return
            messagebox.showerror("Erro", "Dados do aluno não encontrados no servidor.")
        else:
            messagebox.showerror("Erro de Login", "Usuário ou senha inválidos.")

# --- Painel do Administrador ---
class PainelAdmin(tk.Frame):
    def __init__(self, parent, controller, dados_usuario=None):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        self.controller.geometry("1024x768")
        tk.Label(self, text="ConectaPro - Painel do Administrador", font=FONTE_TITULO, bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame_dashboard = ttk.Frame(notebook)
        frame_gestao_academica = ttk.Frame(notebook)
        frame_gestao_usuarios = ttk.Frame(notebook)
        frame_visualizacao = ttk.Frame(notebook)
        frame_sistema = ttk.Frame(notebook)

        notebook.add(frame_dashboard, text="Dashboard")
        notebook.add(frame_gestao_academica, text="Gestão Acadêmica")
        notebook.add(frame_gestao_usuarios, text="Gestão de Usuários")
        notebook.add(frame_visualizacao, text="Visualizar Dados")
        notebook.add(frame_sistema, text="Sistema")

        tk.Button(self, text="Logout", command=lambda: self.controller.trocar_frame(TelaLogin), bg=COR_BOTAO, fg=COR_TEXTO, font=FONTE_NORMAL).pack(pady=10)
        
        self.criar_tela_dashboard(frame_dashboard)
        self.criar_tela_gestao_academica(frame_gestao_academica)
        self.criar_tela_gestao_usuarios(frame_gestao_usuarios)
        self.criar_tela_visualizar_dados(frame_visualizacao)
        self.criar_tela_sistema(frame_sistema)

        notebook.bind("<<NotebookTabChanged>>", self.on_tab_change)
        self.atualizar_dashboard()

    def on_tab_change(self, event):
        selected_tab = event.widget.tab(event.widget.index("current"), "text")
        if selected_tab == "Dashboard":
            self.atualizar_dashboard()

    def on_gestao_academica_tab_change(self, event):
        selected_tab = event.widget.tab(event.widget.index("current"), "text")
        if selected_tab == "Matérias":
            self.atualizar_materias()
        elif selected_tab == "Cursos":
            self.atualizar_cursos()
        elif selected_tab == "Turmas":
            self.atualizar_turmas()

    def criar_tela_dashboard(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=2)

        frame_stats = ttk.LabelFrame(parent, text="Estatísticas Rápidas")
        frame_stats.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        
        self.lbl_total_users = ttk.Label(frame_stats, text="Total de Usuários: ...", font=("Arial", 12))
        self.lbl_total_users.pack(pady=5, anchor="w", padx=10)
        self.lbl_professores = ttk.Label(frame_stats, text="Professores: ...", font=("Arial", 12))
        self.lbl_professores.pack(pady=5, anchor="w", padx=10)
        self.lbl_alunos_users = ttk.Label(frame_stats, text="Alunos (usuários): ...", font=("Arial", 12))
        self.lbl_alunos_users.pack(pady=5, anchor="w", padx=10)
        self.lbl_total_turmas = ttk.Label(frame_stats, text="Total de Turmas: ...", font=("Arial", 12))
        self.lbl_total_turmas.pack(pady=5, anchor="w", padx=10)
        
        ttk.Button(frame_stats, text="Atualizar Estatísticas", command=self.atualizar_dashboard).pack(pady=10)
        
        self.frame_grafico = ttk.LabelFrame(parent, text="Alunos por Turma")
        self.frame_grafico.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

    def atualizar_dashboard(self):
        usuarios = ler_usuarios_local()
        self.lbl_total_users.config(text=f"Total de Usuários: {len(usuarios)}")
        self.lbl_professores.config(text=f"Professores: {sum(1 for u in usuarios if len(u) > 2 and u[2] == 'Professor')}")
        self.lbl_alunos_users.config(text=f"Alunos (usuários): {sum(1 for u in usuarios if len(u) > 2 and u[2] == 'Aluno')}")

        resp_turmas = self.controller.cliente.enviar_comando("LISTAR_TURMAS")
        tipo, turmas = processar_resposta_servidor(resp_turmas)
        self.lbl_total_turmas.config(text=f"Total de Turmas: {len(turmas) if tipo else 0}")

        if MATPLOTLIB_DISPONIVEL:
            for widget in self.frame_grafico.winfo_children():
                widget.destroy()

            resp_alunos = self.controller.cliente.enviar_comando("LISTAR_ALUNOS")
            tipo_alunos, alunos = processar_resposta_servidor(resp_alunos)
            alunos_por_turma = {}
            if tipo_alunos == "DADOS":
                for aluno in alunos:
                    id_turma = aluno[5]
                    alunos_por_turma[id_turma] = alunos_por_turma.get(id_turma, 0) + 1
            
            if alunos_por_turma:
                fig = Figure(figsize=(5, 4), dpi=100, facecolor=COR_FUNDO_FRAME)
                ax = fig.add_subplot(111, facecolor=COR_FUNDO_FRAME)

                ax.bar(alunos_por_turma.keys(), alunos_por_turma.values(), color=COR_DESTAQUE)
                ax.set_title("Distribuição de Alunos por Turma", color=COR_TEXTO)
                ax.set_xlabel("ID da Turma", color=COR_TEXTO)
                ax.set_ylabel("Nº de Alunos", color=COR_TEXTO)
                ax.tick_params(axis='x', colors=COR_TEXTO)
                ax.tick_params(axis='y', colors=COR_TEXTO)
                fig.tight_layout()

                canvas = FigureCanvasTkAgg(fig, master=self.frame_grafico)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True)
            else:
                 ttk.Label(self.frame_grafico, text="Sem dados de alunos para gerar o gráfico.").pack()
    
    def criar_tela_gestao_academica(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        frame_cursos = ttk.Frame(notebook)
        frame_materias = ttk.Frame(notebook)
        frame_turmas = ttk.Frame(notebook)

        notebook.add(frame_cursos, text="Cursos")
        notebook.add(frame_materias, text="Matérias")
        notebook.add(frame_turmas, text="Turmas")

        self.criar_tela_cursos(frame_cursos)
        self.criar_tela_materias(frame_materias)
        self.criar_tela_turmas(frame_turmas)

        notebook.bind("<<NotebookTabChanged>>", self.on_gestao_academica_tab_change)

    def criar_tela_gestao_usuarios(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        frame_professores = ttk.Frame(notebook)
        frame_autorizacoes = ttk.Frame(notebook)

        notebook.add(frame_professores, text="Gerenciar Professores")
        notebook.add(frame_autorizacoes, text="Autorizações Pendentes")
        
        self.criar_tela_usuarios(frame_professores)
        self.criar_tela_autorizacoes(frame_autorizacoes)
    
    def criar_tela_visualizar_dados(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        frame_ver_alunos = ttk.Frame(notebook)
        frame_ver_atividades = ttk.Frame(notebook)
        frame_ver_notas = ttk.Frame(notebook)
        frame_ver_diarios = ttk.Frame(notebook)

        notebook.add(frame_ver_alunos, text="Alunos")
        notebook.add(frame_ver_atividades, text="Atividades")
        notebook.add(frame_ver_notas, text="Notas")
        notebook.add(frame_ver_diarios, text="Diários")

        self.criar_tela_visualizar_alunos(frame_ver_alunos)
        self.criar_tela_visualizar_atividades(frame_ver_atividades)
        self.criar_tela_visualizar_notas(frame_ver_notas)
        self.criar_tela_visualizar_diarios(frame_ver_diarios)

    def criar_tela_sistema(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill='both', expand=True, padx=5, pady=5)

        frame_ferramentas = ttk.Frame(notebook)
        frame_log = ttk.Frame(notebook)

        notebook.add(frame_ferramentas, text="Ferramentas")
        notebook.add(frame_log, text="Log de Atividades")
        
        self.criar_tela_ferramentas(frame_ferramentas)
        self.criar_tela_log(frame_log)

    def criar_tela_autorizacoes(self, parent):
        ttk.Label(parent, text="Alunos aguardando autorização para acessar o sistema.").pack(pady=10)
        
        list_frame = ttk.LabelFrame(parent, text="Registros Pendentes")
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)

        self.tree_autorizacoes = ttk.Treeview(list_frame, columns=("Usuário",), show="headings")
        self.tree_autorizacoes.heading("Usuário", text="Nome do Aluno")
        self.tree_autorizacoes.pack(fill="both", expand=True, side="left")
        
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(side="left", padx=10)
        
        ttk.Button(btn_frame, text="Autorizar Selecionado", command=self.autorizar_usuario).pack(pady=5)
        ttk.Button(btn_frame, text="Recusar Selecionado", command=self.recusar_usuario).pack(pady=5)

        self.atualizar_lista_autorizacoes()

    def atualizar_lista_autorizacoes(self):
        self.tree_autorizacoes.delete(*self.tree_autorizacoes.get_children())
        usuarios = ler_usuarios_local()
        for u in usuarios:
            if len(u) == 4 and u[2] == 'Aluno' and u[3] == 'pendente':
                self.tree_autorizacoes.insert("", "end", values=(u[0],))

    def autorizar_usuario(self):
        selecionado = self.tree_autorizacoes.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um usuário para autorizar.")
            return

        usuario_autorizar = self.tree_autorizacoes.item(selecionado, 'values')[0]
        
        usuarios = ler_usuarios_local()
        for u in usuarios:
            if u[0] == usuario_autorizar:
                u[3] = "ativo"
                break
        
        with open(ARQUIVO_USUARIOS, "w", encoding="utf-8") as f:
            for u in usuarios:
                f.write(f"{';'.join(u)}\n")
        
        self.controller.cliente.enviar_comando(f"LOG;Admin autorizou o acesso do aluno: {usuario_autorizar}")
        messagebox.showinfo("Sucesso", f"Usuário '{usuario_autorizar}' foi autorizado com sucesso.")
        self.atualizar_lista_autorizacoes()


    def recusar_usuario(self):
        selecionado = self.tree_autorizacoes.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um usuário para recusar.")
            return

        usuario_recusar = self.tree_autorizacoes.item(selecionado, 'values')[0]
        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja recusar e excluir o registro pendente de '{usuario_recusar}'?"):
            excluir_usuario_local(usuario_recusar)
            self.controller.cliente.enviar_comando(f"LOG;Admin recusou o acesso do aluno: {usuario_recusar}")
            messagebox.showinfo("Sucesso", "Registro pendente excluído.")
            self.atualizar_lista_autorizacoes()
    
    def criar_tela_usuarios(self, parent):
        form = ttk.LabelFrame(parent, text="Registrar Novo Professor")
        form.pack(pady=10, padx=10, fill="x")
        
        ttk.Label(form, text="Usuário (Professor):").grid(row=0, column=0, padx=5, pady=5)
        self.usuario_entry = ttk.Entry(form)
        self.usuario_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(form, text="Senha:").grid(row=1, column=0, padx=5, pady=5)
        self.senha_entry = ttk.Entry(form, show="*")
        self.senha_entry.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Button(form, text="Registrar Professor", command=self.registrar_usuario).grid(row=2, columnspan=2, pady=10)

        list_frame = ttk.LabelFrame(parent, text="Usuários Registrados (Ativos)")
        list_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        self.tree_usuarios = ttk.Treeview(list_frame, columns=("Usuário", "Perfil"), show="headings")
        self.tree_usuarios.heading("Usuário", text="Usuário"); self.tree_usuarios.heading("Perfil", text="Perfil")
        self.tree_usuarios.pack(fill="both", expand=True)
        ttk.Button(list_frame, text="Excluir Usuário Selecionado", command=self.excluir_usuario).pack(pady=5)

        self.atualizar_lista_usuarios()

    def registrar_usuario(self):
        sucesso, msg = registrar_usuario_local(self.usuario_entry.get(), self.senha_entry.get(), "Professor")
        if sucesso:
            self.controller.cliente.enviar_comando(f"LOG;Admin registrou o usuario (Professor): {self.usuario_entry.get()}")
            messagebox.showinfo("Sucesso", msg)
            self.usuario_entry.delete(0, 'end')
            self.senha_entry.delete(0, 'end')
            self.atualizar_lista_usuarios()
        else:
            messagebox.showerror("Erro", msg)
            
    def atualizar_lista_usuarios(self):
        self.tree_usuarios.delete(*self.tree_usuarios.get_children())
        usuarios = ler_usuarios_local()
        for u in usuarios:
            if len(u) == 4 and u[3] == 'ativo':
                self.tree_usuarios.insert("", "end", values=(u[0], u[2]))
            
    def excluir_usuario(self):
        selecionado = self.tree_usuarios.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione um usuário para excluir.")
            return
        
        usuario_excluir = self.tree_usuarios.item(selecionado, 'values')[0]
        if usuario_excluir == "admin":
            messagebox.showerror("Erro", "Não é possível excluir o administrador padrão.")
            return

        if messagebox.askyesno("Confirmar", f"Tem certeza que deseja excluir o usuário '{usuario_excluir}'?"):
            excluir_usuario_local(usuario_excluir)
            self.controller.cliente.enviar_comando(f"LOG;Admin excluiu o usuario: {usuario_excluir}")
            messagebox.showinfo("Sucesso", "Usuário excluído.")
            self.atualizar_lista_usuarios()

    def criar_tela_cursos(self, parent):
        form = ttk.LabelFrame(parent, text="Adicionar Novo Curso")
        form.pack(pady=10, padx=10, fill='x')
        ttk.Label(form, text="Nome do Curso:").pack(side='left', padx=5)
        self.curso_nome_entry = ttk.Entry(form, width=40)
        self.curso_nome_entry.pack(side='left', padx=5, fill='x', expand=True)
        ttk.Button(form, text="Adicionar", command=self.adicionar_curso).pack(side='left', padx=5)

        list_frame = ttk.LabelFrame(parent, text="Cursos Cadastrados")
        list_frame.pack(pady=10, padx=10, fill='both', expand=True)
        self.tree_cursos = ttk.Treeview(list_frame, columns=("ID", "Nome"), show='headings')
        self.tree_cursos.heading("ID", text="ID"); self.tree_cursos.heading("Nome", text="Nome do Curso")
        self.tree_cursos.pack(fill='both', expand=True)
        ttk.Button(list_frame, text="Excluir Curso Selecionado", command=self.excluir_curso).pack(pady=5)
        self.atualizar_cursos()

    def atualizar_cursos(self):
        self.tree_cursos.delete(*self.tree_cursos.get_children())
        tipo, cursos = processar_resposta_servidor(self.controller.cliente.enviar_comando("LISTAR_CURSOS"))
        if tipo == "DADOS":
            for curso in cursos:
                self.tree_cursos.insert("", "end", values=curso)

    def adicionar_curso(self):
        nome = self.curso_nome_entry.get()
        if nome:
            resp = self.controller.cliente.enviar_comando(f"CADASTRAR_CURSO;{nome}")
            tipo, dados = processar_resposta_servidor(resp)
            if tipo == "SUCESSO":
                self.log_action(f"adicionou o curso '{nome}'")
                messagebox.showinfo("Sucesso", dados)
                self.curso_nome_entry.delete(0, 'end')
                self.atualizar_cursos()

    def excluir_curso(self):
        selecionado = self.tree_cursos.focus()
        if selecionado:
            id_curso = self.tree_cursos.item(selecionado, 'values')[0]
            if messagebox.askyesno("Confirmar", f"Deseja excluir o curso ID {id_curso}? Matérias associadas podem impedir a exclusão."):
                resp = self.controller.cliente.enviar_comando(f"EXCLUIR_CURSO;{id_curso}")
                tipo, dados = processar_resposta_servidor(resp)
                if tipo == "SUCESSO":
                    self.log_action(f"excluiu o curso ID {id_curso}")
                    messagebox.showinfo("Sucesso", dados)
                    self.atualizar_cursos()

    def criar_tela_materias(self, parent):
        form = ttk.LabelFrame(parent, text="Adicionar Nova Matéria")
        form.pack(pady=10, padx=10, fill='x')
        
        ttk.Label(form, text="Nome da Matéria:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.materia_nome_entry = ttk.Entry(form, width=30)
        self.materia_nome_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(form, text="Curso Associado:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.materia_curso_combo = ttk.Combobox(form, state="readonly")
        self.materia_curso_combo.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(form, text="Professor Responsável:").grid(row=2, column=0, sticky='w', padx=5, pady=5)
        self.materia_prof_combo = ttk.Combobox(form, state="readonly")
        self.materia_prof_combo.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(form, text="Modalidade:").grid(row=3, column=0, sticky='w', padx=5, pady=5)
        self.materia_modalidade_combo = ttk.Combobox(form, values=["Online", "Presencial"], state="readonly")
        self.materia_modalidade_combo.grid(row=3, column=1, padx=5, pady=5)
        
        ttk.Button(form, text="Adicionar", command=self.adicionar_materia).grid(row=4, columnspan=2, pady=10)

        list_frame = ttk.LabelFrame(parent, text="Matérias Cadastradas")
        list_frame.pack(pady=10, padx=10, fill='both', expand=True)
        self.tree_materias = ttk.Treeview(list_frame, columns=("ID", "Nome", "ID Curso", "Professor", "Modalidade"), show='headings')
        for col in ("ID", "Nome", "ID Curso", "Professor", "Modalidade"): self.tree_materias.heading(col, text=col)
        self.tree_materias.pack(fill='both', expand=True)
        
        self.atualizar_materias()

    def atualizar_materias(self):
        # Popula comboboxes
        tipo_cursos, cursos = processar_resposta_servidor(self.controller.cliente.enviar_comando("LISTAR_CURSOS"))
        if tipo_cursos == "DADOS":
            self.materia_curso_combo['values'] = [f"{c[0]} - {c[1]}" for c in cursos]
        
        professores = [u[0] for u in ler_usuarios_local() if u[2] == "Professor"]
        self.materia_prof_combo['values'] = professores

        # Atualiza tabela
        self.tree_materias.delete(*self.tree_materias.get_children())
        tipo_materias, materias = processar_resposta_servidor(self.controller.cliente.enviar_comando("LISTAR_MATERIAS"))
        if tipo_materias == "DADOS":
            for materia in materias:
                self.tree_materias.insert("", "end", values=materia)

    def adicionar_materia(self):
        nome = self.materia_nome_entry.get()
        curso_selecionado = self.materia_curso_combo.get()
        prof_selecionado = self.materia_prof_combo.get()
        modalidade = self.materia_modalidade_combo.get()

        if nome and curso_selecionado and prof_selecionado and modalidade:
            id_curso = curso_selecionado.split(' - ')[0]
            cmd = f"CADASTRAR_MATERIA;{nome};{id_curso};{prof_selecionado};{modalidade}"
            resp = self.controller.cliente.enviar_comando(cmd)
            tipo, dados = processar_resposta_servidor(resp)
            if tipo == "SUCESSO":
                self.log_action(f"adicionou a matéria '{nome}'")
                messagebox.showinfo("Sucesso", dados)
                self.materia_nome_entry.delete(0, 'end')
                self.atualizar_materias()
    
    def criar_tela_turmas(self, parent):
        botoes = ttk.Frame(parent)
        botoes.pack(pady=5)
        ttk.Button(botoes, text="Adicionar Turma", command=self.adicionar_turma).pack(side='left', padx=5)
        ttk.Button(botoes, text="Excluir Turma", command=self.excluir_turma).pack(side='left', padx=5)

        self.tree_turmas = ttk.Treeview(parent, columns=("ID", "Data", "Professor"), show="headings")
        self.tree_turmas.heading("ID", text="ID"); self.tree_turmas.heading("Data", text="Data da Turma"); self.tree_turmas.heading("Professor", text="Professor Responsável")
        self.tree_turmas.pack(fill="both", expand=True, padx=10, pady=10)
        self.atualizar_turmas()
    
    def atualizar_turmas(self):
        self.tree_turmas.delete(*self.tree_turmas.get_children())
        resposta = self.controller.cliente.enviar_comando("LISTAR_TURMAS")
        tipo, turmas = processar_resposta_servidor(resposta)
        if tipo == "DADOS":
            for turma in turmas:
                self.tree_turmas.insert("", "end", values=turma)

    def adicionar_turma(self):
        dialog = AddTurmaDialog(self)
        if dialog.result:
            data, professor = dialog.result
            resposta = self.controller.cliente.enviar_comando(f"CADASTRAR_TURMA;{data};{professor}")
            tipo, dados = processar_resposta_servidor(resposta)
            if tipo == "SUCESSO":
                self.master.cliente.enviar_comando(f"LOG;Admin adicionou a turma de '{data}'")
                messagebox.showinfo("Sucesso", dados)
            self.atualizar_turmas()

    def excluir_turma(self):
        selecionado = self.tree_turmas.focus()
        if selecionado:
            id_turma = self.tree_turmas.item(selecionado, 'values')[0]
            resposta = self.controller.cliente.enviar_comando(f"EXCLUIR_TURMA;{id_turma}")
            tipo, dados = processar_resposta_servidor(resposta)
            if tipo == "SUCESSO":
                self.master.cliente.enviar_comando(f"LOG;Admin excluiu a turma ID: {id_turma}")
                messagebox.showinfo("Sucesso", dados)
            self.atualizar_turmas()

    def criar_tela_visualizar_alunos(self, parent):
        ttk.Label(parent, text="Lista de Todos os Alunos no Sistema").pack(pady=10)
        
        self.tree_ver_alunos = ttk.Treeview(parent, columns=("ID", "Nome", "Idade", "Matricula", "Email", "Turma ID"), show="headings")
        for col in ("ID", "Nome", "Idade", "Matricula", "Email", "Turma ID"):
            self.tree_ver_alunos.heading(col, text=col)
        self.tree_ver_alunos.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(parent, text="Atualizar Lista", command=self.atualizar_visualizacao_alunos).pack(pady=5)
        self.atualizar_visualizacao_alunos()

    def atualizar_visualizacao_alunos(self):
        self.tree_ver_alunos.delete(*self.tree_ver_alunos.get_children())
        resposta = self.controller.cliente.enviar_comando("LISTAR_ALUNOS")
        tipo, alunos = processar_resposta_servidor(resposta)
        if tipo == "DADOS":
            for aluno in alunos:
                self.tree_ver_alunos.insert("", "end", values=aluno)

    def criar_tela_visualizar_atividades(self, parent):
        ttk.Label(parent, text="Lista de Todas as Atividades no Sistema").pack(pady=10)
        self.tree_ver_atividades = ttk.Treeview(parent, columns=("ID", "ID Turma", "Título", "Data"), show="headings")
        for col in ("ID", "ID Turma", "Título", "Data"): self.tree_ver_atividades.heading(col, text=col)
        self.tree_ver_atividades.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(parent, text="Atualizar", command=self.atualizar_visualizacao_atividades).pack(pady=5)
        self.atualizar_visualizacao_atividades()

    def atualizar_visualizacao_atividades(self):
        self.tree_ver_atividades.delete(*self.tree_ver_atividades.get_children())
        tipo, atividades = processar_resposta_servidor(self.controller.cliente.enviar_comando("LISTAR_ATIVIDADES"))
        if tipo == "DADOS":
            for ativ in atividades: self.tree_ver_atividades.insert("", "end", values=ativ)

    def criar_tela_visualizar_notas(self, parent):
        ttk.Label(parent, text="Lista de Todas as Notas Lançadas").pack(pady=10)
        self.tree_ver_notas = ttk.Treeview(parent, columns=("ID Aluno", "ID Matéria", "Tipo", "Nota"), show="headings")
        for col in ("ID Aluno", "ID Matéria", "Tipo", "Nota"): self.tree_ver_notas.heading(col, text=col)
        self.tree_ver_notas.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(parent, text="Atualizar", command=self.atualizar_visualizacao_notas).pack(pady=5)
        self.atualizar_visualizacao_notas()

    def atualizar_visualizacao_notas(self):
        self.tree_ver_notas.delete(*self.tree_ver_notas.get_children())
        tipo, notas = processar_resposta_servidor(self.controller.cliente.enviar_comando("LISTAR_NOTAS_TODOS"))
        if tipo == "DADOS":
            for nota in notas: self.tree_ver_notas.insert("", "end", values=nota)
            
    def criar_tela_visualizar_diarios(self, parent):
        ttk.Label(parent, text="Visualizador de Diários de Turma").pack(pady=10)
        
        control_frame = ttk.Frame(parent)
        control_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(control_frame, text="ID da Turma:").pack(side='left')
        self.diario_turma_entry = ttk.Entry(control_frame, width=10)
        self.diario_turma_entry.pack(side='left', padx=5)
        ttk.Button(control_frame, text="Carregar Diário", command=self.atualizar_visualizacao_diario).pack(side='left')

        self.tree_ver_diario = ttk.Treeview(parent, columns=("Data", "Conteúdo", "Presentes"), show="headings")
        for col in ("Data", "Conteúdo", "Presentes"): self.tree_ver_diario.heading(col, text=col)
        self.tree_ver_diario.column("Conteúdo", width=400)
        self.tree_ver_diario.pack(fill="both", expand=True, padx=10, pady=10)

    def atualizar_visualizacao_diario(self):
        id_turma = self.diario_turma_entry.get()
        if not id_turma:
            messagebox.showwarning("Aviso", "Insira um ID de turma.")
            return
            
        self.tree_ver_diario.delete(*self.tree_ver_diario.get_children())
        resposta = self.controller.cliente.enviar_comando(f"LISTAR_DIARIO;{id_turma}")
        tipo, diario = processar_resposta_servidor(resposta)
        if tipo == "DADOS":
            for entrada in diario:
                if len(entrada) == 3:
                    self.tree_ver_diario.insert("", "end", values=entrada)

    def criar_tela_ferramentas(self, parent):
        frame = ttk.LabelFrame(parent, text="Operações do Sistema")
        frame.pack(pady=20, padx=20, fill="x")
        
        ttk.Button(frame, text="Realizar Backup do Servidor", command=self.realizar_backup).pack(pady=10, fill='x')

        ttk.Button(frame, text="Limpar Arquivo de Notas", command=lambda: self.limpar_arquivo("NOTAS")).pack(pady=5, fill='x')
        ttk.Button(frame, text="Limpar Mural de Avisos", command=lambda: self.limpar_arquivo("MENSAGENS")).pack(pady=5, fill='x')
        ttk.Button(frame, text="Limpar Log de Atividades", command=lambda: self.limpar_arquivo("LOGS")).pack(pady=5, fill='x')
    
    def realizar_backup(self):
        if messagebox.askyesno("Confirmar", "Deseja solicitar um backup de todos os dados do servidor? Esta ação não pode ser desfeita."):
            resposta = self.controller.cliente.enviar_comando("BACKUP")
            tipo, dados = processar_resposta_servidor(resposta)
            if tipo == "SUCESSO":
                self.controller.cliente.enviar_comando("LOG;Admin realizou um backup do sistema.")
                messagebox.showinfo("Sucesso", dados)

    def limpar_arquivo(self, tipo_arquivo):
        if messagebox.askyesno("Confirmar Exclusão", f"TEM CERTEZA que deseja apagar TODOS os dados de {tipo_arquivo}? Esta ação é IRREVERSÍVEL."):
            cmd = f"LIMPAR_{tipo_arquivo}"
            resposta = self.controller.cliente.enviar_comando(cmd)
            tipo, dados = processar_resposta_servidor(resposta)
            if tipo == "SUCESSO":
                self.controller.cliente.enviar_comando(f"LOG;Admin limpou o arquivo de {tipo_arquivo}.")
                messagebox.showinfo("Sucesso", dados)

    def criar_tela_log(self, parent):
        ttk.Label(parent, text="Log de Atividades do Sistema").pack(pady=10)
        self.tree_log = ttk.Treeview(parent, columns=("Data/Hora", "Ação"), show="headings")
        self.tree_log.heading("Data/Hora", text="Data e Hora")
        self.tree_log.heading("Ação", text="Ação Registrada")
        self.tree_log.column("Ação", width=600)
        self.tree_log.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(parent, text="Atualizar Log", command=self.atualizar_logs).pack(pady=5)
        self.atualizar_logs()

    def atualizar_logs(self):
        self.tree_log.delete(*self.tree_log.get_children())
        resposta = self.controller.cliente.enviar_comando("LISTAR_LOGS")
        tipo, logs = processar_resposta_servidor(resposta)
        if tipo == "DADOS":
            for log in reversed(logs):
                if len(log) == 2:
                    self.tree_log.insert("", "end", values=log)

    def log_action(self, action):
        log_msg = f"LOG;Admin {action}"
        self.controller.cliente.enviar_comando(log_msg)

# --- Painel do Professor ---
class PainelProfessor(tk.Frame):
    def __init__(self, parent, controller, dados_usuario=None):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        self.controller.geometry("900x700")
        self.dados_prof = dados_usuario
        nome_prof = self.dados_prof.get("nome", "Professor")
        tk.Label(self, text=f"ConectaPro - Painel do Professor: {nome_prof}", font=FONTE_TITULO, bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        abas = {"Alunos": self.criar_tela_alunos, "Atividades": self.criar_tela_atividades, "Notas": self.criar_tela_notas, "Mural": self.criar_tela_mural}
        for nome, construtor in abas.items():
            frame = ttk.Frame(notebook)
            notebook.add(frame, text=nome)
            construtor(frame)
        
        tk.Button(self, text="Logout", command=lambda: self.controller.trocar_frame(TelaLogin), bg=COR_BOTAO, fg=COR_TEXTO).pack(pady=5)
        
    def log_action(self, action):
        log_msg = f"LOG;Professor '{self.dados_prof['nome']}' {action}"
        self.controller.cliente.enviar_comando(log_msg)

    def criar_tela_alunos(self, parent):
        ttk.Button(parent, text="Adicionar Aluno", command=self.adicionar_aluno).pack(pady=5)
        self.tree_alunos = ttk.Treeview(parent, columns=("ID", "Nome", "Turma ID"), show="headings")
        self.tree_alunos.heading("ID", text="ID"); self.tree_alunos.heading("Nome", text="Nome"); self.tree_alunos.heading("Turma ID", text="Turma ID")
        self.tree_alunos.pack(fill="both", expand=True)
        self.atualizar_alunos()

    def adicionar_aluno(self):
        dialog = AddStudentDialog(self)
        if dialog.result:
            nome, idade, email, cpf, id_turma = dialog.result
            
            resposta_servidor = self.controller.cliente.enviar_comando(f"CADASTRAR_ALUNO;{nome};{idade};{email};{id_turma}")
            tipo, dados = processar_resposta_servidor(resposta_servidor)

            if tipo == "SUCESSO":
                senha_aluno = cpf[:6]
                sucesso_registro, msg_registro = registrar_usuario_local(nome, senha_aluno, "Aluno", status="pendente")
                
                if sucesso_registro:
                    self.log_action(f"cadastrou o aluno '{nome}' (acesso pendente).")
                    messagebox.showinfo("Sucesso", f"{dados}\n\nUsuário de login para o aluno criado.\nO acesso aguarda autorização do administrador.")
                else:
                    messagebox.showwarning("Aviso", f"Dados do aluno cadastrados no servidor, mas o usuário de login não foi criado: {msg_registro}")

                self.atualizar_alunos()

    def atualizar_alunos(self):
        self.tree_alunos.delete(*self.tree_alunos.get_children())
        resposta = self.controller.cliente.enviar_comando("LISTAR_ALUNOS")
        tipo, alunos = processar_resposta_servidor(resposta)
        if tipo == "DADOS":
            for aluno in alunos:
                self.tree_alunos.insert("", "end", values=(aluno[0], aluno[1], aluno[5]))
    
    def criar_tela_atividades(self, parent):
        form = ttk.LabelFrame(parent, text="Nova Atividade")
        form.pack(fill='x', pady=5)
        ttk.Label(form, text="ID Turma:").grid(row=0, column=0)
        self.ativ_id_turma_entry = ttk.Entry(form)
        self.ativ_id_turma_entry.grid(row=0, column=1)
        ttk.Label(form, text="Título:").grid(row=1, column=0)
        self.ativ_titulo_entry = ttk.Entry(form)
        self.ativ_titulo_entry.grid(row=1, column=1)
        ttk.Label(form, text="Data Entrega:").grid(row=2, column=0)
        self.ativ_data_entry = ttk.Entry(form)
        self.ativ_data_entry.grid(row=2, column=1)
        ttk.Button(form, text="Adicionar", command=self.adicionar_atividade).grid(row=3, columnspan=2)

        self.tree_atividades = ttk.Treeview(parent, columns=("ID", "Turma", "Título", "Data"), show="headings")
        self.tree_atividades.heading("ID", text="ID"); self.tree_atividades.heading("Turma", text="ID Turma"); self.tree_atividades.heading("Título", text="Título"); self.tree_atividades.heading("Data", text="Data Entrega")
        self.tree_atividades.pack(fill='both', expand=True, pady=5)
        self.atualizar_atividades()

    def adicionar_atividade(self):
        id_turma = self.ativ_id_turma_entry.get()
        titulo = self.ativ_titulo_entry.get()
        data = self.ativ_data_entry.get()
        if id_turma and titulo and data:
            cmd = f"CADASTRAR_ATIVIDADE;{id_turma};{titulo};{data}"
            resp = self.controller.cliente.enviar_comando(cmd)
            tipo, dados = processar_resposta_servidor(resp)
            if tipo == "SUCESSO":
                self.log_action(f"adicionou a atividade '{titulo}'")
                messagebox.showinfo("Sucesso", dados)
            self.atualizar_atividades()
    
    def atualizar_atividades(self):
        self.tree_atividades.delete(*self.tree_atividades.get_children())
        resp = self.controller.cliente.enviar_comando("LISTAR_ATIVIDADES")
        tipo, atividades = processar_resposta_servidor(resp)
        if tipo == "DADOS":
            for ativ in atividades:
                self.tree_atividades.insert("", "end", values=ativ)

    def criar_tela_notas(self, parent):
        ttk.Button(parent, text="Lançar/Editar Notas", command=self.lancar_nota).pack(pady=10)
    
    def lancar_nota(self):
        dialog = AddGradesDialog(self)

    def criar_tela_mural(self, parent):
        form = ttk.LabelFrame(parent, text="Postar Aviso no Mural")
        form.pack(fill='x', pady=5)

        ttk.Label(form, text="ID da Turma:").pack(side='left', padx=5)
        self.mural_id_turma_entry = ttk.Entry(form, width=10)
        self.mural_id_turma_entry.pack(side='left', padx=5)

        ttk.Label(form, text="Mensagem:").pack(side='left', padx=5)
        self.mural_msg_entry = ttk.Entry(form, width=50)
        self.mural_msg_entry.pack(side='left', padx=5, expand=True, fill='x')

        ttk.Button(form, text="Postar", command=self.postar_mensagem).pack(side='left', padx=5)

    def postar_mensagem(self):
        id_turma = self.mural_id_turma_entry.get()
        msg = self.mural_msg_entry.get()
        data = datetime.now().strftime("%d-%m-%Y")
        if id_turma and msg:
            cmd = f"POSTAR_MENSAGEM;{id_turma};{data};{msg}"
            resp = self.controller.cliente.enviar_comando(cmd)
            tipo, dados = processar_resposta_servidor(resp)
            if tipo == "SUCESSO":
                self.log_action(f"postou uma mensagem para a turma {id_turma}")
                messagebox.showinfo("Sucesso", dados)

# --- Painel do Aluno ---
class PainelAluno(tk.Frame):
    def __init__(self, parent, controller, dados_usuario=None):
        super().__init__(parent, bg=COR_FUNDO)
        self.controller = controller
        self.controller.geometry("800x600")
        self.dados_aluno = dados_usuario
        nome_aluno = self.dados_aluno.get("nome", "Aluno")
        tk.Label(self, text=f"ConectaPro - Painel do Aluno: {nome_aluno}", font=FONTE_TITULO, bg=COR_FUNDO, fg=COR_TEXTO).pack(pady=10)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        frame_boletim = ttk.Frame(notebook)
        frame_mural = ttk.Frame(notebook)
        notebook.add(frame_boletim, text="Meu Boletim")
        notebook.add(frame_mural, text="Mural de Avisos")
        tk.Button(self, text="Logout", command=lambda: self.controller.trocar_frame(TelaLogin), bg=COR_BOTAO, fg=COR_TEXTO).pack(pady=5)
        
        self.criar_tela_boletim(frame_boletim)
        self.criar_tela_mural(frame_mural)

    def criar_tela_boletim(self, parent):
        self.tree_boletim = ttk.Treeview(parent, columns=("Materia", "NP1", "NP2", "PIM", "Média", "Status"), show="headings")
        for col in ("Materia", "NP1", "NP2", "PIM", "Média", "Status"):
            self.tree_boletim.heading(col, text=col)
        self.tree_boletim.pack(fill="both", expand=True, padx=10, pady=10)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(pady=5)
        ttk.Button(btn_frame, text="Solicitar Exame", command=self.solicitar_exame).pack()

        self.atualizar_boletim()

    def atualizar_boletim(self):
        self.tree_boletim.delete(*self.tree_boletim.get_children())
        
        resp_notas = self.controller.cliente.enviar_comando("LISTAR_NOTAS_TODOS")
        resp_materias = self.controller.cliente.enviar_comando("LISTAR_MATERIAS")
        
        tipo_notas, notas = processar_resposta_servidor(resp_notas)
        tipo_materias, materias = processar_resposta_servidor(resp_materias)

        if tipo_notas is None or tipo_materias is None: return

        mapa_materias = {m[0]: m[1] for m in materias} 
        notas_aluno = {}

        for id_aluno, id_materia, tipo_nota, valor_nota in notas:
            if id_aluno == self.dados_aluno['id']:
                if id_materia not in notas_aluno:
                    notas_aluno[id_materia] = {}
                notas_aluno[id_materia][tipo_nota] = float(valor_nota.replace(',', '.'))
        
        for id_materia, grades in notas_aluno.items():
            np1 = grades.get("NP1", 0.0)
            np2 = grades.get("NP2", 0.0)
            pim = grades.get("PIM", 0.0)
            
            media = (np1 * 0.4) + (np2 * 0.4) + (pim * 0.2)
            
            status = "Cursando"
            if "PIM" in grades:
                if media >= 7.0:
                    status = "Aprovado"
                else:
                    exame = grades.get("EXAME")
                    if exame is not None:
                        media_final = (media + exame) / 2
                        status = "Aprovado (Exame)" if media_final >= 5.0 else "Reprovado (DP)"
                    else:
                        status = "Exame"
            
            nome_materia = mapa_materias.get(id_materia, f"Matéria ID {id_materia}")
            self.tree_boletim.insert("", "end", values=(nome_materia, f"{np1:.1f}", f"{np2:.1f}", f"{pim:.1f}", f"{media:.2f}", status))

    def solicitar_exame(self):
        selecionado = self.tree_boletim.focus()
        if not selecionado:
            messagebox.showwarning("Aviso", "Selecione uma matéria na tabela para solicitar o exame.")
            return
        
        status = self.tree_boletim.item(selecionado, 'values')[5]
        if status != "Exame":
            messagebox.showinfo("Informação", "Você só pode solicitar exame para matérias com status 'Exame'.")
            return
            
        materia = self.tree_boletim.item(selecionado, 'values')[0]
        if messagebox.askyesno("Confirmar", f"Deseja confirmar a solicitação de exame para a matéria '{materia}'?"):
            self.controller.cliente.enviar_comando(f"LOG;O aluno '{self.dados_aluno['nome']}' solicitou exame para '{materia}'")
            messagebox.showinfo("Sucesso", "Solicitação de exame registrada! Entre em contato com seu professor.")

    def criar_tela_mural(self, parent):
        self.tree_mural = ttk.Treeview(parent, columns=("Data", "Mensagem"), show="headings")
        self.tree_mural.heading("Data", text="Data"); self.tree_mural.heading("Mensagem", text="Mensagem")
        self.tree_mural.column("Mensagem", width=500)
        self.tree_mural.pack(fill="both", expand=True)
        self.atualizar_mural()

    def atualizar_mural(self):
        self.tree_mural.delete(*self.tree_mural.get_children())
        resp = self.controller.cliente.enviar_comando("LISTAR_MENSAGENS")
        tipo, mensagens = processar_resposta_servidor(resp)
        if tipo == "DADOS":
            for msg in mensagens:
                if msg[0] == self.dados_aluno["turma_id"]:
                    self.tree_mural.insert("", "end", values=(msg[1], msg[2]))

# --- Diálogos Personalizados ---

class AddStudentDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Adicionar Novo Aluno")
        
        labels = ["Nome Completo:", "Idade:", "Email:", "CPF (só números):", "Turma:"]
        self.entries = {}
        for i, text in enumerate(labels):
            ttk.Label(master, text=text).grid(row=i, column=0, padx=5, pady=5, sticky='w')
            if text != "Turma:":
                entry = ttk.Entry(master, width=30)
                entry.grid(row=i, column=1, padx=5, pady=5)
                self.entries[text] = entry
            else:
                self.turma_combo = ttk.Combobox(master, state="readonly", width=40)
                self.turma_combo.grid(row=i, column=1, padx=5, pady=5)
                self.popular_turmas()
        return self.entries[labels[0]]

    def popular_turmas(self):
        resp = self.master.controller.cliente.enviar_comando("LISTAR_TURMAS")
        tipo, turmas = processar_resposta_servidor(resp)
        if tipo == "DADOS":
            self.turma_combo['values'] = [f"{t[0]} - {t[1]} (Prof: {t[2]})" for t in turmas]

    def apply(self):
        nome = self.entries["Nome Completo:"].get()
        idade = self.entries["Idade:"].get()
        email = self.entries["Email:"].get()
        cpf = self.entries["CPF (só números):"].get()
        turma_selecionada = self.turma_combo.get()

        if not all([nome, idade, email, cpf, turma_selecionada]):
            messagebox.showwarning("Erro", "Todos os campos são obrigatórios.", parent=self)
            self.result = None
            return

        if not cpf.isdigit() or len(cpf) < 6:
            messagebox.showerror("Erro", "O CPF deve conter pelo menos 6 números.", parent=self)
            self.result = None
            return

        id_turma = turma_selecionada.split(' - ')[0]
        self.result = (nome, idade, email, cpf, id_turma)

class AddGradesDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Lançar/Editar Notas")
        
        ttk.Label(master, text="Aluno:").grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.aluno_combo = ttk.Combobox(master, state="readonly", width=40)
        self.aluno_combo.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(master, text="Matéria:").grid(row=1, column=0, padx=5, pady=5, sticky='w')
        self.materia_combo = ttk.Combobox(master, state="readonly", width=40)
        self.materia_combo.grid(row=1, column=1, padx=5, pady=5)

        self.grades = {}
        for i, nota_tipo in enumerate(["NP1", "NP2", "PIM", "EXAME"]):
            ttk.Label(master, text=f"{nota_tipo}:").grid(row=i+2, column=0, padx=5, pady=5, sticky='w')
            entry = ttk.Entry(master, width=10)
            entry.grid(row=i+2, column=1, padx=5, pady=5, sticky='w')
            self.grades[nota_tipo] = entry

        self.popular_combos()
        return self.aluno_combo

    def popular_combos(self):
        resp_alunos = self.master.controller.cliente.enviar_comando("LISTAR_ALUNOS")
        tipo_a, alunos = processar_resposta_servidor(resp_alunos)
        if tipo_a == "DADOS":
            self.aluno_combo['values'] = [f"{a[0]} - {a[1]}" for a in alunos]
        
        resp_materias = self.master.controller.cliente.enviar_comando("LISTAR_MATERIAS")
        tipo_m, materias = processar_resposta_servidor(resp_materias)
        if tipo_m == "DADOS":
            self.materia_combo['values'] = [f"{m[0]} - {m[1]}" for m in materias]

    def apply(self):
        aluno_sel = self.aluno_combo.get()
        materia_sel = self.materia_combo.get()
        if not aluno_sel or not materia_sel:
            messagebox.showwarning("Erro", "Selecione um aluno e uma matéria.", parent=self)
            return

        id_aluno = aluno_sel.split(" - ")[0]
        id_materia = materia_sel.split(" - ")[0]

        for tipo, entry in self.grades.items():
            valor = entry.get()
            if valor:
                cmd = f"CADASTRAR_NOTA;{id_aluno};{id_materia};{tipo};{valor}"
                resp = self.master.controller.cliente.enviar_comando(cmd)
                tipo_resp, dados = processar_resposta_servidor(resp)
                if tipo_resp != "SUCESSO":
                    messagebox.showerror("Erro no Servidor", f"Não foi possível salvar a nota {tipo}: {dados}", parent=self)
        
        messagebox.showinfo("Sucesso", "Notas enviadas para o servidor.", parent=self)

class AddTurmaDialog(simpledialog.Dialog):
    def body(self, master):
        self.title("Adicionar Nova Turma")
        
        ttk.Label(master, text="Data da Turma (ex: 2025-2):").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.data_entry = ttk.Entry(master, width=30)
        self.data_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(master, text="Professor Responsável:").grid(row=1, column=0, sticky='w', padx=5, pady=5)
        self.prof_combo = ttk.Combobox(master, state="readonly", width=30)
        self.prof_combo.grid(row=1, column=1, padx=5, pady=5)
        self.popular_professores()

        return self.data_entry

    def popular_professores(self):
        self.prof_combo['values'] = [u[0] for u in ler_usuarios_local() if u[2] == "Professor"]

    def apply(self):
        data = self.data_entry.get()
        prof = self.prof_combo.get()
        if data and prof:
            self.result = (data, prof)
        else:
            messagebox.showwarning("Erro", "Todos os campos são obrigatórios.", parent=self)
            self.result = None


if __name__ == "__main__":
    if not MATPLOTLIB_DISPONIVEL:
        print("Aviso: Matplotlib não encontrado. Os gráficos não serão exibidos.")
        print("Instale com: pip install matplotlib")
    app = App()
    app.mainloop()

