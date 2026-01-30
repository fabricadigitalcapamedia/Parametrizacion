import re
import urllib.parse

file_path = r"d:\OneDrive\Documentos\Portalexa\Parametrizacion\docs\PortalErrores\bk.config.js"
base_url = "https://claromovilco.sharepoint.com/sites/coordinacion_lideresdeaplicaciones/Errores%20Parametrizacion/"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

def replace_url(match):
    filename = match.group(1)
    # Encode filename for URL
    encoded_filename = urllib.parse.quote(filename)
    new_url = base_url + encoded_filename
    return f'nombre: "{filename}",\n    url: "{new_url}"'

# Regex to match nombre and url pair
# Handles spaces and newlines around them
# Pattern looks for: nombre: "FILE", (newline+spaces) url: "OLD_URL"
pattern = r'nombre:\s*"([^"]+)",\s*url:\s*"[^"]*"'

new_content = re.sub(pattern, replace_url, content)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(new_content)

print("Updated URLs in bk.config.js")
