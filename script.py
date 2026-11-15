import os
import requests

# URL de la página protegida que deseas extraer
URL = "https://ns1-app.competenciadeportiva.com/"

# Cabeceras necesarias para simular el WebView de la app oficial
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 14; SM-S901U Build/UP1A.231005.007; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/157.0.8103.50 Mobile Safari/537.36",
    "X-Requested-With": "com.deporagenda.ec",
    "Origin": "https://ns1-app.competenciadeportiva.com",
    "Referer": "https://ns1-app.competenciadeportiva.com/",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
}

def extraer_html():
    print("[-] Conectando y extrayendo el código HTML...")
    try:
        response = requests.get(URL, headers=HEADERS)
        
        if response.status_code == 200:
            print("[+] ¡Petición exitosa! El servidor devolvió el HTML.")
            
            # Nombre del archivo donde se guardará el código
            nombre_archivo = "evento.html"
            
            # Guardar el contenido HTML con codificación UTF-8
            with open(nombre_archivo, "w", encoding="utf-8") as f:
                f.write(response.text)
                
            print(f"[+] ¡Código HTML guardado correctamente en '{nombre_archivo}'!")
            print(f"[i] Tamaño del archivo: {len(response.text)} caracteres.")
        else:
            print(f"[!] Error: El servidor respondió con el código {response.status_code}")
            
    except Exception as e:
        print(f"[!] Ocurrió un error en la conexión: {e}")

if __name__ == "__main__":
    extraer_html()