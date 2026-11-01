#!/usr/bin/env python3
"""Ejecuta el cliente oficial del proyecto local y valida el JSON resultante."""
import json
import os
import subprocess
import sys
from pathlib import Path

script = Path(__file__).with_name("obtener_canales_xuper.js")
output = Path(os.getenv("OUTPUT_FILE", "canales_xuper.json"))

if not script.is_file():
    print(f"No se encuentra {script}", file=sys.stderr)
    raise SystemExit(1)

# El protocolo cifrado del portal está implementado en el módulo JavaScript del proyecto.
# Python solo coordina la ejecución; no guarda tokens ni URLs de reproducción.
try:
    subprocess.run(["node", str(script)], check=True, timeout=900)
    data = json.loads(output.read_text(encoding="utf-8"))
    print(f"OK: {data.get('channelCount', 0)} canales, "
          f"{data.get('categoryCount', 0)} categorías.")
except subprocess.CalledProcessError as exc:
    print(f"Falló la consulta al portal (código {exc.returncode}).", file=sys.stderr)
    raise SystemExit(exc.returncode)
except subprocess.TimeoutExpired:
    print("La consulta excedió 15 minutos.", file=sys.stderr)
    raise SystemExit(1)
except (OSError, json.JSONDecodeError) as exc:
    print(f"No se pudo leer el resultado: {exc}", file=sys.stderr)
    raise SystemExit(1)
