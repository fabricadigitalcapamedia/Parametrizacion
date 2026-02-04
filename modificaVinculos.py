import os
import re
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import threading
import time
from urllib.parse import urlparse, unquote
from tkinter import filedialog

# Configuración de rutas por defecto
DEFAULT_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SEARCH_DIR = os.path.join(DEFAULT_BASE_DIR, "docs", "PortalErrores")

# Extensiones permitidas (Whitelist)
ALLOWED_EXTENSIONS = ('.doc', '.docx', '.pdf')

class LinkManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Gestor de Vínculos de Portal Errores")
        self.root.geometry("1400x750")
        
        # Estilo premium
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        style.configure("Treeview", font=('Segoe UI', 10), rowheight=25)
        
        self.links_data = [] 
        self.search_dir = DEFAULT_SEARCH_DIR
        self.docs_dir = os.path.dirname(self.search_dir)
        
        self.create_widgets()
        
        # Iniciar escaneo automático al arranque si existe la ruta por defecto
        if os.path.exists(self.search_dir):
            self.root.after(100, self.start_scan_thread)
        else:
            self.status_var.set("Seleccione la carpeta de PortalErrores para comenzar.")

    def create_widgets(self):
        # --- Cabecera / Controles ---
        control_frame = tk.Frame(self.root, bg="#f3f4f6", pady=10)
        control_frame.pack(side=tk.TOP, fill=tk.X)

        title_lbl = tk.Label(control_frame, text="Modificación de Vínculos BK (Depurado)", 
                             font=("Segoe UI", 16, "bold"), bg="#f3f4f6", fg="#1f2937")
        title_lbl.pack(side=tk.LEFT, padx=20)

        self.btn_reload = tk.Button(control_frame, text="🔄 Recargar / Escanear", 
                                    command=self.start_scan_thread, 
                                    font=("Segoe UI", 10), bg="#ffffff", relief="flat", padx=10)
        self.btn_reload.pack(side=tk.RIGHT, padx=10)

        self.btn_edit = tk.Button(control_frame, text="✏️ Modificar Seleccionado", 
                                  command=self.edit_selected, 
                                  font=("Segoe UI", 10), bg="#e0f2fe", relief="flat", padx=10)
        self.btn_edit.pack(side=tk.RIGHT, padx=10)

        self.btn_folder = tk.Button(control_frame, text="📂 Seleccionar Carpeta", 
                                    command=self.select_folder, 
                                    font=("Segoe UI", 10), bg="#dcfce7", relief="flat", padx=10)
        self.btn_folder.pack(side=tk.RIGHT, padx=10)

        # --- Barra de Carpeta Seleccionada ---
        path_frame = tk.Frame(self.root, bg="#f9fafb", padx=20, pady=2)
        path_frame.pack(side=tk.TOP, fill=tk.X)
        self.path_var = tk.StringVar(value=f"Carpeta: {self.search_dir}")
        self.path_lbl = tk.Label(path_frame, textvariable=self.path_var, 
                                 font=("Segoe UI", 8, "italic"), anchor="w", bg="#f9fafb", fg="#6b7280")
        self.path_lbl.pack(side=tk.LEFT, fill=tk.X)

        # --- Barra de Progreso y Estado ---
        status_frame = tk.Frame(self.root, bg="#ffffff", padx=20, pady=5)
        status_frame.pack(side=tk.TOP, fill=tk.X)

        self.status_var = tk.StringVar(value="Esperando...")
        self.status_lbl = tk.Label(status_frame, textvariable=self.status_var, 
                                   font=("Segoe UI", 9), anchor="w", bg="#ffffff", fg="#4b5563")
        self.status_lbl.pack(side=tk.TOP, fill=tk.X)

        self.progress = ttk.Progressbar(status_frame, orient=tk.HORIZONTAL, mode='determinate')
        self.progress.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))

        # --- Tabla de Datos ---
        table_frame = tk.Frame(self.root, bg="#ffffff", padx=20, pady=20)
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("nombre", "url_real", "filename", "html_origen", "tipo")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings")
        
        self.tree.heading("nombre", text="Nombre del Vínculo")
        self.tree.heading("url_real", text="URL Real")
        self.tree.heading("filename", text="Nombre Archivo")
        self.tree.heading("html_origen", text="HTML Origen")
        self.tree.heading("tipo", text="Tipo")

        self.tree.column("nombre", width=350, anchor="w")
        self.tree.column("url_real", width=400, anchor="w")
        self.tree.column("filename", width=250, anchor="w")
        self.tree.column("html_origen", width=300, anchor="w")
        self.tree.column("tipo", width=80, anchor="center")

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbar
        yscroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=yscroll.set)

        self.tree.bind("<Double-1>", lambda e: self.edit_selected())

    def update_status(self, msg, progress_val=None):
        self.status_var.set(msg)
        if progress_val is not None:
            self.progress['value'] = progress_val
        self.root.update_idletasks()

    def start_scan_thread(self):
        self.btn_reload.config(state="disabled")
        self.btn_edit.config(state="disabled")
        self.progress['value'] = 0
        threading.Thread(target=self.scan_files, daemon=True).start()

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=self.search_dir, title="Seleccionar carpeta PortalErrores")
        if folder:
            self.search_dir = folder
            self.docs_dir = os.path.dirname(self.search_dir)
            self.path_var.set(f"Carpeta: {self.search_dir}")
            self.start_scan_thread()

    def scan_files(self):
        try:
            self.update_status("Iniciando escaneo de archivos...", 5)
            self.links_data = []
            
            if not os.path.exists(self.search_dir):
                self.root.after(0, lambda: messagebox.showerror("Error", f"No se encontró la carpeta: {self.search_dir}"))
                self.root.after(0, self.finish_scan)
                return

            html_files = []
            for root, dirs, files in os.walk(self.search_dir):
                for f in files:
                    if f.lower().endswith('.html'):
                        html_files.append(os.path.join(root, f))

            total_files = len(html_files)
            if total_files == 0:
                self.update_status("No se encontraron archivos HTML.", 100)
                self.root.after(0, self.finish_scan)
                return

            # Regex para encontrar etiquetas <a> que tengan un href
            # Captura el tag completo, el href y el contenido interno
            link_pattern = re.compile(r'(<a\s+[^>]*?href=["\']([^"\']+)["\'][^>]*>(.*?)</a>)', re.IGNORECASE | re.DOTALL)

            for idx, file_path in enumerate(html_files):
                rel_path = os.path.relpath(file_path, self.docs_dir).replace("\\", "/")
                self.update_status(f"Analizando: {rel_path}", 10 + (idx / total_files * 85))
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                        
                    matches = link_pattern.findall(content)
                    for full_tag, href, inner_content in matches:
                        # Limpiar inner_content de etiquetas HTML si las hay (ej. <b>...</b>)
                        clean_label = re.sub(r'<[^>]+>', '', inner_content).strip()
                        
                        # Detectar si apunta a un archivo permitido
                        path_part = urlparse(href).path
                        filename = os.path.basename(unquote(path_part))
                        
                        is_doc = any(filename.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS)
                        
                        # Lógica extendida para SharePoint/OneDrive
                        is_sharepoint = ".sharepoint.com" in href.lower() or "1drv.ms" in href.lower()
                        sp_marker = ""
                        
                        if not is_doc:
                            # Buscar extensiones en la URL completa (antes de ?)
                            if any(ext in href.lower().split('?')[0] for ext in ALLOWED_EXTENSIONS):
                                is_doc = True
                            # Marcadores de SharePoint (/:w:/ -> Word, /:b:/ -> PDF/Binary, etc.)
                            elif is_sharepoint:
                                if "/:w:/" in href.lower():
                                    is_doc = True
                                    sp_marker = "WORD"
                                elif "/:b:/" in href.lower():
                                    is_doc = True
                                    sp_marker = "PDF"
                                elif "/:x:/" in href.lower():
                                    is_doc = True
                                    sp_marker = "EXCEL"

                        if is_doc:
                            # Determinar el tipo
                            if sp_marker:
                                tipo = sp_marker
                            else:
                                ext_match = re.search(r'\.(doc|docx|pdf)', filename.lower() if filename else href.lower())
                                tipo = ext_match.group(1).upper() if ext_match else ("SP-DOC" if is_sharepoint else "OTRO")
                            
                            # Limpiar nombre de archivo si es un ID de SharePoint
                            display_filename = filename if (filename and "." in filename and len(filename) < 100) else "Documento SharePoint"
                            
                            self.links_data.append({
                                'full_tag': full_tag,
                                'nombre': clean_label,
                                'url_real': href,
                                'filename': display_filename,
                                'html_origen': rel_path,
                                'tipo': tipo,
                                'abs_path': file_path
                            })
                except Exception as e:
                    print(f"Error procesando {file_path}: {e}")

            self.update_status(f"Búsqueda finalizada. {len(self.links_data)} vínculos detectados.", 100)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error durante el escaneo: {e}"))
        finally:
            self.root.after(0, self.finish_scan)

    def finish_scan(self):
        self.btn_reload.config(state="normal")
        self.btn_edit.config(state="normal")
        self.refresh_table()

    def refresh_table(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        for link in self.links_data:
            self.tree.insert("", tk.END, values=(
                link['nombre'], 
                link['url_real'], 
                link['filename'], 
                link['html_origen'], 
                link['tipo']
            ))

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showwarning("Selección", "Por favor seleccione un vínculo de la tabla.")
            return
        
        item_idx = self.tree.index(selected[0])
        link_info = self.links_data[item_idx]
        
        dialog = EditDialog(self.root, link_info)
        self.root.wait_window(dialog.top)
        
        if dialog.result:
            self.apply_changes(link_info, dialog.result)

    def apply_changes(self, old_info, new_info):
        """Implementa la persistencia de los cambios en el archivo HTML."""
        file_path = old_info['abs_path']
        
        # Construir el nuevo tag <a> basado en el formato original si es posible
        # Pero lo más seguro es reconstruirlo limpio manteniendo los atributos críticos
        # Para mantener el estilo (class="bk-btn"), intentamos un reemplazo cuidadoso
        
        new_url = new_info['url_real']
        new_label = new_info['nombre']
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Buscamos exactamente el tag original capturado
            old_tag = old_info['full_tag']
            
            # Si el usuario modificó el nombre, debemos actualizar el contenido del tag
            # Si el usuario modificó la URL, el href
            
            # Reconstrucción del tag preservando atributos adicionales
            # Reemplazar href="..." con la nueva URL
            # Para esto usamos regex sobre el fragmento del tag capturado
            updated_tag = re.sub(r'href=["\'][^"\']+["\']', f'href="{new_url}"', old_tag)
            
            # Reemplazar el texto interno. El contenido está entre el primer > y el último </a>
            # Buscamos el primer cierre de tag de apertura
            tag_start_end = updated_tag.find('>')
            if tag_start_end != -1:
                prefix = updated_tag[:tag_start_end + 1]
                updated_tag = prefix + new_label + "</a>"
            
            # Aplicar al contenido total del archivo
            if old_tag in content:
                new_file_content = content.replace(old_tag, updated_tag)
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_content)
                
                messagebox.showinfo("Éxito", f"Vínculo actualizado en {old_info['html_origen']}")
                self.start_scan_thread() # Recargar para ver los cambios
            else:
                messagebox.showerror("Error", "No se pudo localizar el tag original en el archivo. ¿Fue modificado externamente?")
                
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {e}")

class EditDialog:
    def __init__(self, parent, link_info):
        self.top = tk.Toplevel(parent)
        self.top.title("Editar Vínculo")
        self.top.geometry("700x420")
        self.top.resizable(False, False)
        self.top.grab_set() # Modal
        
        self.result = None
        
        main_frame = tk.Frame(self.top, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Label: Origen
        tk.Label(main_frame, text=f"Archivo Origen: {link_info['html_origen']}", 
                 font=("Segoe UI", 9, "italic"), fg="#6b7280").pack(anchor="w", pady=(0,10))

        # Campo: Nombre del Vínculo
        tk.Label(main_frame, text="Nombre del Vínculo (Label):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.ent_nombre = tk.Entry(main_frame, font=("Segoe UI", 10), width=80)
        self.ent_nombre.insert(0, link_info['nombre'])
        self.ent_nombre.pack(fill=tk.X, pady=(0, 15))

        # Campo: URL Real
        tk.Label(main_frame, text="URL Real:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.ent_url = tk.Entry(main_frame, font=("Segoe UI", 10), width=80)
        self.ent_url.insert(0, link_info['url_real'])
        self.ent_url.pack(fill=tk.X, pady=(0, 15))

        # Campo Informativo: Nombre de Archivo Detectado (Solo lectura aquí, cambia con la URL)
        tk.Label(main_frame, text="Nombre de Archivo (Detectado):", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.lbl_filename = tk.Label(main_frame, text=link_info['filename'], font=("Segoe UI", 10), 
                                     fg="#374151", bg="#f9fafb", relief="sunken", anchor="w", padx=10, pady=5)
        self.lbl_filename.pack(fill=tk.X, pady=(0, 20))

        # Botones
        btn_frame = tk.Frame(main_frame)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        self.btn_cancel = tk.Button(btn_frame, text="Cancelar", command=self.top.destroy, 
                                    width=12, bg="#f3f4f6")
        self.btn_cancel.pack(side=tk.RIGHT, padx=5)

        self.btn_save = tk.Button(btn_frame, text="Guardar Cambios", command=self.save, 
                                  width=15, bg="#0ea5e9", fg="white", font=("Segoe UI", 10, "bold"))
        self.btn_save.pack(side=tk.RIGHT, padx=5)

    def save(self):
        self.result = {
            'nombre': self.ent_nombre.get().strip(),
            'url_real': self.ent_url.get().strip()
        }
        self.top.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    # Centrar ventana
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width / 2) - (1400 / 2)
    y = (screen_height / 2) - (750 / 2)
    root.geometry(f"1400x750+{int(x)}+{int(y)}")
    
    app = LinkManagerApp(root)
    root.mainloop()
