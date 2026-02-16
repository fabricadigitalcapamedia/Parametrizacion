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
        self.root.geometry("750x850")
        
        # Variables de estado
        self.git_executable = None
        self.repo_path = tk.StringVar()
        self.git_portable_path = tk.StringVar()
        self.github_url = tk.StringVar()
        self.username = tk.StringVar()
        self.token = tk.StringVar()
        self.use_auth = tk.BooleanVar(value=False)
        self.is_running = False
        self.using_system_git = False

        # Configurar estilos
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=5)

        self._build_ui()
        self.root.after(200, self._initial_check)

    def _build_ui(self):
        # --- Marco 1: Configuración Local ---
        frame_config = ttk.LabelFrame(self.root, text="1. Configuración Local", padding=10)
        frame_config.pack(fill="x", padx=10, pady=5)

        # Selector Git Portable
        lbl_git = ttk.Label(frame_config, text="Carpeta Portable Git:")
        lbl_git.grid(row=0, column=0, sticky="w")
        
        self.entry_git = ttk.Entry(frame_config, textvariable=self.git_portable_path, width=50)
        self.entry_git.grid(row=0, column=1, padx=5)
        
        self.btn_browse_git = ttk.Button(frame_config, text="Examinar...", command=self._browse_git_path)
        self.btn_browse_git.grid(row=0, column=2)

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
        # Se ocultará hasta validar o clonar
        
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
        
        # Botón Clonar (Oculto por defecto)
        self.btn_clone = ttk.Button(self.frame_ops, text="CLONAR REPOSITORIO", command=lambda: self._run_thread(self._op_clone))
        
        # Botones Normales
        self.btn_pull = ttk.Button(self.frame_ops, text="1. PULL (Actualizar)", command=lambda: self._run_thread(self._op_pull))
        self.btn_status = ttk.Button(self.frame_ops, text="2. STATUS (Estado)", command=lambda: self._run_thread(self._op_status))
        self.btn_apply = ttk.Button(self.frame_ops, text="3. APPLY (Subir)", command=self._prompt_commit_msg)

        # Pack inicial de botones normales (deshabilitados hasta validar)
        self.btn_pull.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_status.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_apply.pack(side="left", fill="x", expand=True, padx=5)
        
        self._disable_ops()

        # --- Marco 4: Salida y Progreso ---
        frame_log = ttk.LabelFrame(self.root, text="Registro de Actividad", padding=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.console = scrolledtext.ScrolledText(frame_log, height=15, state='disabled', font=("Consolas", 9))
        self.console.pack(fill="both", expand=True)

        self.progress = ttk.Progressbar(frame_log, mode='indeterminate')
        self.progress.pack(fill="x", pady=5)

    def _disable_ops(self):
        for btn in [self.btn_pull, self.btn_status, self.btn_apply, self.btn_clone]:
            btn.configure(state='disabled')

    def _enable_normal_ops(self):
        self.btn_clone.pack_forget()
        self.btn_pull.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_status.pack(side="left", fill="x", expand=True, padx=5)
        self.btn_apply.pack(side="left", fill="x", expand=True, padx=5)
        
        self.btn_pull.configure(state='normal')
        self.btn_status.configure(state='normal')
        self.btn_apply.configure(state='normal')

    def _enable_clone_op(self):
        self.btn_pull.pack_forget()
        self.btn_status.pack_forget()
        self.btn_apply.pack_forget()
        
        self.btn_clone.pack(side="left", fill="x", expand=True, padx=20)
        self.btn_clone.configure(state='normal')

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

    def _detect_system_git(self):
        # 1. Intentar detectar si 'git' está en el PATH
        try:
            startupinfo = None
            if sys.platform.startswith("win"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            result = subprocess.run(["git", "--version"], capture_output=True, startupinfo=startupinfo, text=True)
            if result.returncode == 0:
                return "git" # Está en el PATH y funciona
        except:
            pass
        
        # 2. Buscar en rutas comunes de instalación en Windows
        common_paths = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
             os.path.expanduser(r"~\AppData\Local\Programs\Git\cmd\git.exe"),
        ]
        for p in common_paths:
            if os.path.exists(p):
                return p
        return None

    def _initial_check(self):
        system_git = self._detect_system_git()
        if system_git:
            msg = "Se ha detectado una instalación de Git en el sistema.\n\n" \
                  "¿Desea utilizar la versión instalada en lugar de buscar una versión Portable?"
            if messagebox.askyesno("Git Detectado", msg):
                self.using_system_git = True
                self.git_executable = system_git
                self.git_portable_path.set(f"GIT DEL SISTEMA ({system_git})")
                
                # Bloquear controles de Git Portable
                self.entry_git.configure(state='disabled')
                self.btn_browse_git.configure(state='disabled')
                
                self._log(f"Modo: Git instalado en sistema detectado ({system_git}).")
            else:
                self._log("Usuario optó por configurar Git Portable manualmente.")
        else:
            self._log("No se detectó Git instalado. Se requiere configurar Git Portable.")

    def _validate_setup(self):
        repo_path = self.repo_path.get()

        # Validación inicial de entradas
        if not self.using_system_git:
            if not self.git_portable_path.get():
                messagebox.showwarning("Faltan Datos", "Por favor seleccione la carpeta de Git Portable.")
                return
        
        if not repo_path:
            messagebox.showwarning("Faltan Datos", "Por favor seleccione la carpeta del Repositorio Local.")
            return

        self._log("Validando configuración...")
        
        # 1. Validar Git Executable
        if self.using_system_git:
            # Si usamos sistema, ya confiamos en lo detectado, pero verificamos integridad básica si es ruta completa
            self._log(f"Usando Git (Sistema): {self.git_executable}")
        else:
            git_path = self.git_portable_path.get()
            exe = self._find_git_exe(git_path)
            if not exe:
                self._log(f"No se encontró git.exe en {git_path}", error=True)
                messagebox.showerror("Error", "No se encontró git.exe en la carpeta portable.")
                return
            self.git_executable = exe
            self._log(f"Git (Portable): {exe}")

        # 2. Validar Repositorio
        if not os.path.isdir(repo_path):
            self._log("La ruta del repositorio no existe.", error=True)
            return

        try:
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
                self._enable_normal_ops()
                
                # Intentar obtener URL
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
                # NO es repo git -> Ofrecer clonar
                self._log("La carpeta seleccionada NO es un repositorio Git.", error=True)
                if messagebox.askyesno("Repositorio No Encontrado", 
                                       "La carpeta local seleccionada NO es un repositorio Git válido.\n\n"
                                       "¿Desea CLONAR un repositorio de GitHub en esta ubicación?"):
                    self.frame_remote.pack(fill="x", padx=10, pady=5)
                    self.frame_ops.pack(fill="x", padx=10, pady=5)
                    self._enable_clone_op()
                    self._log("Modo Clonación activado. Ingrese URL y Credenciales.")
                else:
                    self._disable_ops()

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
            
            if url.startswith("https://") and "@" not in url:
                clean_url = url.replace("https://", "")
                return f"https://{user}:{token}@{clean_url}"
            return url 
        return url

    def _run_git(self, args, description, cwd=None):
        if not self.git_executable:
            return False, "Configuración incompleta."
        
        run_cwd = cwd if cwd else self.repo_path.get()

        try:
            # En modo clonación, args[0] es 'clone'. 
            # Si usuario puso credenciales, la URL va impresa en log... 
            # DEBEMOS OCULTAR CREDENCIALES EN LOG
            cmd_str_log = f"{description}"
            
            cmd = [self.git_executable] + args
            self._log(f"Ejecutando: {cmd_str_log}...")
            
            startupinfo = None
            if sys.platform.startswith("win"):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                cmd, cwd=run_cwd, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                text=True, startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            
            if stdout:
                self._log(stdout)
            if stderr:
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
        if self.is_running: return
        self.is_running = True
        self.progress.start(10)
        
        # Deshabilitar botones durante operación
        for btn in [self.btn_pull, self.btn_status, self.btn_apply, self.btn_clone, self.btn_validate]:
            try:
                btn.configure(state='disabled')
            except: pass

        def wrapper():
            try:
                target_func(*args)
            except Exception as e:
                self._log(f"Error inesperado: {e}", True)
            finally:
                self.root.after(0, self._finish_thread)

        threading.Thread(target=wrapper, daemon=True).start()

    def _finish_thread(self):
        self.progress.stop()
        self.is_running = False
        self.btn_validate.configure(state='normal')
        
        # Restaurar estado botones según contexto (si es clone mode o normal)
        # Check si se activó el modo normal via validación posterior
        # Simplemente re-validamos visualmente
        if self.btn_clone.winfo_ismapped():
            self.btn_clone.configure(state='normal')
        else:
            self.btn_pull.configure(state='normal')
            self.btn_status.configure(state='normal')
            self.btn_apply.configure(state='normal')

    # --- OPERACIONES ---

    def _op_clone(self):
        url = self._get_remote_url_with_auth()
        if not url:
            self._show_msg("Error", "URL de GitHub requerida.", True)
            return
        
        # Confirmación
        confirm = messagebox.askyesno(
            "Confirmar Clonación", 
            f"Se clonará el repositorio desde:\n{self.github_url.get()}\n\nHacia la carpeta:\n{self.repo_path.get()}\n\n¿Desea continuar?"
        )
        if not confirm: return

        # Clonar en directorio actual (.)
        # git clone <url> .
        # Requiere carpeta vacía usualmente.
        cmd = ["clone", url, "."]
        
        success, _ = self._run_git(cmd, "Clonando Repositorio")
        
        if success:
            self._show_msg("Éxito", "Repositorio clonado correctamente.")
            # Auto-revalidar para cambiar a modo normal
            self.root.after(0, self._validate_setup)
        else:
            self._show_msg("Error", "Falló la clonación. Revise que la carpeta esté vacía y las credenciales sean correctas.", True)

    def _op_pull(self):
        # Confirmación
        if not messagebox.askyesno("Confirmar Pull", "Esta acción descargará los cambios del repositorio remoto (GitHub) y los fusionará con su versión local.\n\n¿Desea continuar?"):
            return

        url = self._get_remote_url_with_auth()
        if not url:
            self._show_msg("Error", "URL de GitHub requerida.", True)
            return

        cmd = ["pull", url, "main"]
        success, _ = self._run_git(cmd, "Pull desde Main")
        
        if success:
            self._show_msg("Éxito", "Repositorio actualizado correctamente (Pull).")
        else:
            self._show_msg("Error", "Falló la operación Pull. Revise el registro.", True)

    def _op_status(self):
        # Confirmación
        if not messagebox.askyesno("Confirmar Status", "Esta acción verificará el estado del repositorio local y buscará diferencias con la versión remota (GitHub).\n\n¿Desea continuar?"):
            return

        url = self._get_remote_url_with_auth()
        if not url:
            self._show_msg("Error", "URL de GitHub requerida.", True)
            return
        
        cmd_fetch = ["fetch", url, "main"]
        ok_fetch, _ = self._run_git(cmd_fetch, "Fetch Remote Main")
        
        if not ok_fetch:
            self._show_msg("Error", "No se pudo conectar con el repositorio remoto (Fetch falló).", True)
            return

        self._run_git(["status"], "Estado Local")
        self._log("--- DIFERENCIAS CON REMOTO (main) ---")
        self._run_git(["diff", "--stat", "HEAD", "FETCH_HEAD"], "Calculando diferencias")

        self._show_msg("Status", "Revisión completada. Ver registro.")

    def _prompt_commit_msg(self):
        if not self.github_url.get():
             messagebox.showwarning("Falta URL", "Primero debe validar y configurar la URL.")
             return
        
        # Confirmación Previa
        if not messagebox.askyesno("Confirmar Apply", "Esta acción preparará todos los cambios locales, creará un Commit y los subirá (Push) a GitHub.\n\n¿Desea continuar?"):
            return

        msg = simpledialog.askstring("Confirmar Cambios", "Ingrese el mensaje del Commit:")
        if msg:
            self._run_thread(self._op_apply, msg)

    def _op_apply(self, message):
        url = self._get_remote_url_with_auth()
        
        ok_add, output = self._run_git(["add", "."], "Stage (git add .)")
        if not ok_add: 
            self._show_msg("Error", "Falló git add.", True)
            return

        status_ok, status_out = self._run_git(["status", "--porcelain"], "Verificando cambios")
        if not status_out.strip():
            self._log("No hay cambios pendientes para commit.")
        else:
            ok_commit, _ = self._run_git(["commit", "-m", message], "Creando Commit")
            if not ok_commit: 
                self._show_msg("Error", "Falló git commit.", True)
                return

        cmd_push = ["push", url, "main"]
        ok_push, _ = self._run_git(cmd_push, "Push a GitHub Main")
        
        if ok_push:
            self._show_msg("Éxito", "Cambios aplicados y sincronizados correctamente.")
        else:
            self._show_msg("Error", "Error al subir cambios a GitHub (Push).", True)

if __name__ == "__main__":
    if sys.platform.startswith('win'):
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass
            
    root = tk.Tk()
    app = GitSyncApp(root)
    root.mainloop()
