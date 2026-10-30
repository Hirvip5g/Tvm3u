import base64
import re
import urllib.parse
import httpx
from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import PlainTextResponse

app = FastAPI()

KEY_REQ = "FUERZA.SV"
SEC_REQ = "XTREAM.VIDEX.m3u8"


@app.get("/stream.php")
async def handle_stream(
    stream: str = Query("dsports"),
    ts: str = Query(None),
    key: str = Query(None),
    secreto: str = Query(None),
):
  if key != KEY_REQ or secreto != SEC_REQ:
    raise HTTPException(status_code=401, detail="Acceso no autorizado")

  headers = {
      "User-Agent": (
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
          " like Gecko) Chrome/122.0.0.0 Safari/537.36"
      ),
      "Accept": "*/*",
      "Referer": "https://streamxhd.sbs/",
      "Origin": "https://streamxhd.sbs",
  }

  async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
    if ts:
      ts_url = urllib.parse.unquote(ts)
      if ".m3u8" in ts_url:
        resp = await client.get(ts_url, headers=headers)
        sub_content = resp.text
        base_url = ts_url[: ts_url.rfind("/") + 1]
        auth = f"key={urllib.parse.quote(KEY_REQ)}&secreto={urllib.parse.quote(SEC_REQ)}"

        output = []
        for line in sub_content.splitlines():
          line = line.strip()
          if not line:
            continue
          if not line.startswith("#"):
            if not line.startswith("http"):
              line = base_url + line
            line = f"stream.php?ts={urllib.parse.quote(line)}&{auth}"
          output.append(line)

        return PlainTextResponse(
            "\n".join(output),
            media_type="application/vnd.apple.mpegurl",
            headers={"Access-Control-Allow-Origin": "*"},
        )

      resp = await client.get(ts_url, headers=headers)
      return Response(
          content=resp.content,
          media_type="video/mp2t",
          headers={"Access-Control-Allow-Origin": "*"},
      )

    clean_stream = re.sub(r"[^a-zA-Z0-9_\-]", "", stream)
    page_url = f"https://streamxhd.sbs/live1.php?stream={urllib.parse.quote(clean_stream)}"

    try:
      resp = await client.get(page_url, headers=headers)
      page_content = resp.text
    except:
      raise HTTPException(
          status_code=502, detail="No se pudo conectar con el sitio fuente."
      )

    matches_funcs = re.findall(
        r"function\s+[a-zA-Z0-9_]+\s*\(\)\s*\{\s*return\s+(\d+)\s*;\s*\}",
        page_content,
        re.IGNORECASE,
    )
    if not matches_funcs:
      matches_funcs = re.findall(r"return\s+(\d{5,7})\s*;", page_content)

    if len(matches_funcs) < 2:
      raise HTTPException(
          status_code=500, detail="No se pudieron extraer las constantes."
      )

    k = int(matches_funcs[0]) + int(matches_funcs[1])

    match_block = re.search(
        r"\[\s*\[\s*\d+\s*,\s*\"[A-Za-z0-9=\/+]+\"\s*\](?:.*?\]){10,}",
        page_content,
        re.DOTALL,
    )
    if not match_block:
      raise HTTPException(
          status_code=500, detail="No se encontró el bloque encriptado."
      )

    json_match = re.search(r"(\[\[.*\]\])", match_block.group(0), re.DOTALL)
    try:
      yr_data = json.loads(json_match.group(1))
    except:
      raise HTTPException(status_code=500, detail="Fallo al parsear datos.")

    yr_data.sort(key=lambda x: x[0])
    m3u8_url_parts = []
    for item in yr_data:
      decoded = base64.b64decode(item[1]).decode("utf-8", errors="ignore")
      numeric_only = re.sub(r"\D", "", decoded)
      if numeric_only:
        m3u8_url_parts.append(chr(int(numeric_only) - k))

    m3u8_url = "".join(m3u8_url_parts)
    if not m3u8_url:
      raise HTTPException(
          status_code=500, detail="No se pudo descifrar la URL del canal."
      )

    resp_m3u8 = await client.get(m3u8_url, headers=headers)
    if resp_m3u8.status_code != 200:
      raise HTTPException(
          status_code=502, detail="Error al descargar el m3u8 original."
      )

    base = m3u8_url[: m3u8_url.rfind("/") + 1]
    auth = f"key={urllib.parse.quote(KEY_REQ)}&secreto={urllib.parse.quote(SEC_REQ)}"

    output = []
    for line in resp_m3u8.text.splitlines():
      line = line.strip()
      if not line:
        continue
      if not line.startswith("#"):
        if not line.startswith("http"):
          line = base + line
        line = f"stream.php?ts={urllib.parse.quote(line)}&{auth}"
      output.append(line)

    return PlainTextResponse(
        "\n".join(output),
        media_type="application/vnd.apple.mpegurl",
        headers={"Access-Control-Allow-Origin": "*"},
    )