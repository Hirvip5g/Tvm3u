import os
import re
import json
import urllib.request

# URL de donde se extraerá el archivo HTML con los tokens actualizados
HTML_URL = "https://bestleague.life/tok.html"

# Lista de archivos JSON de tu repositorio que deseas actualizar
JSON_FILES = ["agenda.json", "04.json"]  # Agrega aquí todos tus archivos JSON

def fetch_html_content(url):
    """Descarga el contenido HTML de la página web."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    with urllib.request.urlopen(req) as response:
        return response.read().decode("utf-8")

def extract_tokens_from_html(html_content):
    """
    Extrae un diccionario de mapeo {cdn_name: token} desde el array 'mt' en el HTML.
    Ejemplo: {'edge-live22-sl': 'tok_eyJhbG...', ...}
    """
    tokens_map = {}
    
    # Expresión regular para capturar los bloques cdn y token dentro del array mt del JS
    pattern = re.compile(r'cdn:\s*"([^"]+)",\s*token:\s*"([^"]+)"')
    matches = pattern.findall(html_content)
    
    for cdn, token in matches:
        tokens_map[cdn] = token
        
    return tokens_map

def replace_token_in_url(url, new_token):
    """
    Reemplaza únicamente la sección del token en una URL de CDN estilo Flow/Edge 
    sin tocar la estructura restante de la URL.
    Ejemplo de URL: https://edge-live22-sl.cvattv.com.ar/tok_VIEJOTOKEN/live/...
    """
    if not url or "cvattv.com.ar" not in url:
        return url
        
    # Patrón para encontrar el segmento del token (ej. /tok_.../)
    # Buscamos la estructura /tok_<token>/ y la reescribimos con el nuevo token
    pattern = re.compile(r'(https?://[^/]+\.cvattv\.com\.ar/)tok_[^/]+(/.*)')
    match = pattern.match(url)
    
    if match:
        base_domain = match.group(1)
        path_remainder = match.group(2)
        return f"{base_domain}{new_token}{path_remainder}"
        
    return url

def update_json_data(data, tokens_map):
    """
    Recorre recursivamente estructuras JSON (listas o diccionarios) buscando claves 'url' 
    para actualizar el token del CDN correspondiente.
    """
    changed = False
    
    if isinstance(data, dict):
        # Si el diccionario tiene una estructura de servidor con cdn y url o similar
        # Verificamos si en este nivel manejamos cdn explícito o si la URL contiene el cdn
        current_cdn = data.get("cdn")
        
        for key, value in data.items():
            if key == "url" and isinstance(value, str):
                # Intentar adivinar el CDN desde la URL si no está explícito en 'cdn'
                target_cdn = current_cdn
                if not target_cdn:
                    for cdn_name in tokens_map.keys():
                        if cdn_name in value:
                            target_cdn = cdn_name
                            break
                
                if target_cdn and target_cdn in tokens_map:
                    new_token = tokens_map[target_cdn]
                    updated_url = replace_token_in_url(value, new_token)
                    if updated_url != value:
                        data[key] = updated_url
                        changed = True
            else:
                if update_json_data(value, tokens_map):
                    changed = True
                    
    elif isinstance(data, list):
        for item in data:
            if update_json_data(item, tokens_map):
                changed = True
                
    return changed

def main():
    print("Descargando HTML fuente...")
    try:
        html_content = fetch_html_content(HTML_URL)
    except Exception as e:
        print(f"Error al descargar la URL: {e}")
        return

    print("Extrayendo tokens del HTML...")
    tokens_map = extract_tokens_from_html(html_content)
    
    if not tokens_map:
        print("No se encontraron tokens en la página.")
        return
    
    print(f"Tokens encontrados para {len(tokens_map)} CDNs.")

    any_file_changed = False

    for json_file in JSON_FILES:
        if not os.path.exists(json_file):
            print(f"El archivo {json_file} no existe, se omite.")
            continue
            
        print(f"Procesando archivo: {json_file}")
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                content = json.load(f)
            except json.JSONDecodeError as e:
                print(f"Error al leer el JSON {json_file}: {e}")
                continue

        if update_json_data(content, tokens_map):
            # Guardar el archivo manteniendo formato compacto o legible según prefieras
            with open(json_file, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
            print(f"¡Tokens actualizados con éxito en {json_file}!")
            any_file_changed = True
        else:
            print(f"No se detectaron cambios necesarios en {json_file}.")

    # Indicador para GitHub Actions sobre si hubo cambios
    if any_file_changed:
        print("CAMBIOS_DETECTADOS=true")
    else:
        print("CAMBIOS_DETECTADOS=false")

if __name__ == "__main__":
    main()