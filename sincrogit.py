import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk, simpledialog
import subprocess
import os
import threading
import sys

# =============================================================================
# INSTRUCCIONES DE EMPAQUETADO (PyInstaller)
# Para convertir este script en un ejecutable de Windows (.exe) autocontenido:
# 1. Instalar PyInstaller: pip install pyinstaller
# 2. Ejecutar comando:     pyinstaller --onefile --noconsole sincrogit.py
# =============================================================================

class GitSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SincroGit - Sincronizador de Repositorios")
        self.root.geometry("750x800")
        
        # Variables de estado
        self.git_executable = None
        self.repo_path = tk.StringVar()
        self.git_portable_path = tk.StringVar()
        self.github_url = tk.StringVar()
        self.username = tk.StringVar()
        self.token = tk.StringVar()
        self.use_auth = tk.BooleanVar(value=False)
        self.is_running = False

        # Configurar estilos
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=5)

        self._build_ui()

    def _build_ui(self):
        # --- Marco 1: Configuración Local ---
        frame_config = ttk.LabelFrame(self.root, text="1. Configuración Local", padding=10)
        frame_config.pack(fill="x", padx=10, pady=5)

        # Selector Git Portable
        lbl_git = ttk.Label(frame_config, text="Carpeta Portable Git:")
        lbl_git.grid(row=0, column=0, sticky="w")
        
        entry_git = ttk.Entry(frame_config, textvariable=self.git_portable_path, width=50)
        entry_git.grid(row=0, column=1, padx=5)
        
        btn_browse_git = ttk.Button(frame_config, text="Examinar...", command=self._browse_git_path)
        btn_browse_git.grid(row=0, column=2)

        # Selector Repositorio Local
        lbl_repo = ttk.Label(frame_config, text="Carpeta Repositorio Local:")
        lbl_repo.grid(row=1, column=0, sticky="w", pady=5)
        
        entry_repo = ttk.Entry(frame_config, textvariable=self.repo_path, width=50)
        entry_repo.grid(row=1, column=1, padx=5, pady=5)
        
        btn_browse_repo = ttk.Button(frame_config, text="Examinar...", command=self._browse_repo_path)
        btn_browse_repo.grid(row=1, column=2, pady=5)

        # Botón Validar
        self.btn_validate = ttk.Button(frame_config, text="Conectar y Validar", command=self._validate_setup)
        self.btn_validate.grid(row=2, column=1, pady=10)

        # --- Marco 2: Configuración Remota (GitHub) ---
        self.frame_remote = ttk.LabelFrame(self.root, text="2. Configuración GitHub", padding=10)
        # Se ocultará hasta validar
        
        lbl_url = ttk.Label(self.frame_remote, text="URL Repositorio GitHub:")
        lbl_url.grid(row=0, column=0, sticky="w")
        entry_url = ttk.Entry(self.frame_remote, textvariable=self.github_url, width=55)
        entry_url.grid(row=0, column=1, padx=5, columnspan=2)

        # Credenciales
        chk_auth = ttk.Checkbutton(self.frame_remote, text="Usar Credenciales (Si el repo es privado)", variable=self.use_auth, command=self._toggle_auth)
        chk_auth.grid(row=1, column=0, columnspan=3, sticky="w", pady=5)

        self.frame_auth = ttk.Frame(self.frame_remote)
        self.frame_auth.grid(row=2, column=0, columnspan=3, sticky="ew")
        
        ttk.Label(self.frame_auth, text="Usuario:").grid(row=0, column=0, sticky="w")
        ttk.Entry(self.frame_auth, textvariable=self.username, width=20).grid(row=0, column=1, padx=5)
        
        ttk.Label(self.frame_auth, text="Personal Access Token:").grid(row=0, column=2, sticky="w")
        entry_token = ttk.Entry(self.frame_auth, textvariable=self.token, width=25, show="*")
        entry_token.grid(row=0, column=3, padx=5)
        
        self._toggle_auth() # Inicializar estado

        # --- Marco 3: Operaciones ---
        self.frame_ops = ttk.LabelFrame(self.root, text="3. Operaciones", padding=10)
        
        btn_pull = ttk.Button(self.frame_ops, text="PULL (Actualizar)", command=lambda: self._run_thread(self._op_pull))
        btn_pull.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_status = ttk.Button(self.frame_ops, text="STATUS (Estado)", command=lambda: self._run_thread(self._op_status))
        btn_status.pack(side="left", fill="x", expand=True, padx=5)
        
        btn_apply = ttk.Button(self.frame_ops, text="APPLY (Guardar y Subir)", command=self._prompt_commit_msg)
        btn_apply.pack(side="left", fill="x", expand=True, padx=5)

        # --- Marco 4: Salida y Progreso ---
        frame_log = ttk.LabelFrame(self.root, text="Registro de Actividad", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(frame_log, height=15, state='disabled', font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

        self.progress = ttk.Progressbar(frame_log, mode='indeterminate')
        self.progress.pack(fill="x", pady=5)

    def _browse_git_path(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta Portable Git (Ej: D:\\PortableGit)")
        if path:
            self.git_portable_path.set(path)

    def _browse_repo_path(self):
        path = filedialog.askdirectory(title="Seleccionar Carpeta del Repositorio Local")
        if path:
            self.repo_path.set(path)

    def _toggle_auth(self):
        if self.use_auth.get():
            for child in self.frame_auth.winfo_children():
                child.configure(state='normal')
        else:
            for child in self.frame_auth.winfo_children():
                child.configure(state='disabled')

    def _log(self, message, error=False):
        # UI Update debe ser en main thread
        self.root.after(0, lambda: self._val_log(message, error))

    def _val_log(self, message, error):
        self.console.configure(state='normal')
        tag = "ERROR" if error else "INFO"
        self.console.insert(tk.END, f"[{tag}] {message}\n")
        self.console.see(tk.END)
        self.console.configure(state='disabled')

    def _show_msg(self, title, msg, is_error=False):
        if is_error:
            self.root.after(0, lambda: messagebox.showerror(title, msg))
        else:
            self.root.after(0, lambda: messagebox.showinfo(title, msg))

    def _find_git_exe(self, base_path):
        # Buscar git.exe en ubicaciones comunes dentro de la carpeta portable
        possible_paths = [
            os.path.join(base_path, "bin", "git.exe"),
            os.path.join(base_path, "cmd", "git.exe"),
            os.path.join(base_path, "mingw64", "bin", "git.exe"),
            os.path.join(base_path, "git.exe")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                return p
        return None

    def _validate_setup(self):
        git_path = self.git_portable_path.get()
        repo_path = self.repo_path.get()

        if not git_path or not repo_path:
            messagebox.showwarning("Faltan Datos", "Por favor seleccione ambas carpetas.")
            return

        self._log("Validando configuración...")
        
        # 1. Validar Git Executable
        exe = self._find_git_exe(git_path)
        if not exe:
            self._log(f"No se encontró git.exe en {git_path}", error=True)
            messagebox.showerror("Error", "No se encontró el ejecutable de git (git.exe) en la carpeta seleccionada.\nAsegúrese de seleccionar la raíz de PortableGit.")
            return
        self.git_executable = exe
        self._log(f"Git validado en: {exe}")

        # 2. Validar Repositorio
        if not os.path.isdir(repo_path):
            self._log("La ruta del repositorio no existe.", error=True)
            return

        # Verificar si es un repo git con el binario encontrado
        try:
            # CREATE_NO_WINDOW es flag específico de Windows
            startupinfo = None
            if sys.platform.startswith("win"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(
                [self.git_executable, "rev-parse", "--is-inside-work-tree"],
                cwd=repo_path, capture_output=True, text=True, startupinfo=startupinfo
            )
            
            if result.returncode == 0 and result.stdout.strip() == "true":
                self._log("Repositorio Git válido detectado.")
                self.frame_remote.pack(fill="x", padx=10, pady=5)
                self.frame_ops.pack(fill="x", padx=10, pady=5)
                
                # Intentar obtener URL existente para pre-llenar
                try:
                    res_url = subprocess.run(
                        [self.git_executable, "config", "--get", "remote.origin.url"],
                        cwd=repo_path, capture_output=True, text=True, startupinfo=startupinfo
                    )
                    detected_url = res_url.stdout.strip()
                    if detected_url and not self.github_url.get():
                        self.github_url.set(detected_url)
                        self._log(f"URL remota detectada: {detected_url}")
                except:
                    pass
            else:
                self._log("La carpeta seleccionada NO es un repositorio Git válido.", error=True)
                messagebox.showerror("Error Validacion", "La carpeta seleccionada no es un repositorio Git válido.")
        except Exception as e:
            self._log(f"Error al validar: {str(e)}", error=True)

    def _get_remote_url_with_auth(self):
        url = self.github_url.get().strip()
        if not url:
            return None
        
        if self.use_auth.get():
            user = self.username.get().strip()
            token = self.token.get().strip()
            if not user or not token:
                return None
            
            # Insertar credenciales en la URL si es HTTPS
            if url.startswith("https://") and "@" not in url:
                clean_url = url.replace("https://", "")
                return f"https://{user}:{token}@{clean_url}"
            return url 
        return url

    def _run_git(self, args, description):
        """Ejecuta comando git y retorna (éxito:bool, salida:str)"""
        if not self.git_executable or not self.repo_path.get():
            return False, "Configuración incompleta."

        try:
            cmd = [self.git_executable] + args
            self._log(f"Ejecutando: {description}...")
            
            startupinfo = None
            if sys.platform.startswith("win"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, cwd=self.repo_path.get(), 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            
            if stdout:
                self._log(stdout)
            if stderr:
                # Git usa stderr para mensajes informativos a veces, pero lo logueamos
                self._log(stderr, error=False) 
            
            if process.returncode == 0:
                self._log(f"EXITOSO: {description}")
                return True, stdout
            else:
                self._log(f"FALLÓ: {description} (Código {process.returncode})", error=True)
                return False, stderr
        except Exception as e:
            msg = f"Excepción ejecutando comando: {str(e)}"
            self._log(msg, error=True)
            return False, msg

    def _run_thread(self, target_func, *args):
        if self.is_running:
            return
        self.is_running = True
        self.progress.start(10)
        
        # Deshabilitar controles UI
        for child in self.frame_ops.winfo_children():
            child.configure(state='disabled')
        self.btn_validate.configure(state='disabled')

        def wrapper():
            try:
                target_func(*args)
            except Exception as e:
                self._log(f"Error inesperado en hilo: {e}", True)
            finally:
                self.root.after(0, self._finish_thread)

        threading.Thread(target=wrapper, daemon=True).start()

    def _finish_thread(self):
        self.progress.stop()
        self.is_running = False
        # Habilitar botones
        for child in self.frame_ops.winfo_children():
            child.configure(state='normal')
        self.btn_validate.configure(state='normal')

    # --- OPERACIONES ---

    def _op_pull(self):
        url = self._get_remote_url_with_auth()
        if not url:
            self._show_msg("Error", "URL de GitHub requerida.", True)
            return

        # git pull <url> main
        # Ojo: si la rama local se llama master, esto tratará de fusionar main en master.
        # Asumimos que el usuario trabaja en main o quiere traer main.
        # Para ser más seguro, usamos: git pull origin main (si el remoto está configurado)
        # O git pull URL main.
        
        cmd = ["pull", url, "main"]
        success, _ = self._run_git(cmd, "Pull desde Main")
        
        if success:
            self._show_msg("Éxito", "Repositorio actualizado correctamente (Pull).")
        else:
            self._show_msg("Error", "Falló la operación Pull. Revise el registro.", True)

    def _op_status(self):
        url = self._get_remote_url_with_auth()
        if not url:
            self._show_msg("Error", "URL de GitHub requerida.", True)
            return
        
        # 1. Fetch para actualizar referencias
        cmd_fetch = ["fetch", url, "main"]
        ok_fetch, _ = self._run_git(cmd_fetch, "Fetch Remote Main")
        
        if not ok_fetch:
            self._show_msg("Error", "No se pudo conectar con el repositorio remoto (Fetch falló).", True)
            return

        # 2. Status Local
        self._run_git(["status"], "Estado Local")

        # 3. Diferencias
        # Mostramos qué cambiaría si fusionamos: git diff HEAD...FETCH_HEAD
        # FETCH_HEAD es donde apuntó el último fetch.
        self._log("--- DIFERENCIAS CON REMOTO (main) ---")
        self._run_git(["diff", "--stat", "HEAD", "FETCH_HEAD"], "Calculando diferencias (Local vs Remoto)")

        self._show_msg("Status", "Revisión completada. Ver registro.")

    def _prompt_commit_msg(self):
        if not self.github_url.get():
             messagebox.showwarning("Falta URL", "Primero debe validar y configurar la URL.")
             return
        msg = simpledialog.askstring("Confirmar Cambios", "Ingrese el mensaje del Commit:")
        if msg:
            self._run_thread(self._op_apply, msg)

    def _op_apply(self, message):
        url = self._get_remote_url_with_auth()
        
        # 1. Add
        ok_add, output = self._run_git(["add", "."], "Stage (git add .)")
        if not ok_add: 
            self._show_msg("Error", "Falló git add.", True)
            return

        # 2. Commit
        # Verificamos si hay algo que commitear
        status_ok, status_out = self._run_git(["status", "--porcelain"], "Verificando cambios")
        if not status_out.strip():
            self._log("No hay cambios pendientes para commit.")
        else:
            ok_commit, _ = self._run_git(["commit", "-m", message], "Creando Commit")
            if not ok_commit: 
                self._show_msg("Error", "Falló git commit.", True)
                return

        # 3. Push
        cmd_push = ["push", url, "main"]
        ok_push, _ = self._run_git(cmd_push, "Push a GitHub Main")
        
        if ok_push:
            self._show_msg("Éxito", "Cambios aplicados y sincronizados correctamente.")
        else:
            self._show_msg("Error", "Error al subir cambios a GitHub (Push). Revise credenciales o conflictos.", True)

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            # Mejorar resolución DPI en Windows
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
    root = tk.Tk()
    app = GitSyncApp(root)
    root.mainloop()
