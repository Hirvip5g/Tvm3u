from datetime import datetime
import json
import urllib.request
import zoneinfo

# URLs de origen
URL_EVENTOS = "https://streamxhd.sbs/eventos.json"
URL_CANALES = "https://streamxhd.sbs/canales/canales.json"

# Tu URL base del proxy (cuando lo subas a Render o Railway)
BASE_URL = "http://hirviptv.hirvip-5g.store/stream2.php?stream="
URL_PARAMS = "&key=FUERZA.SV&secreto=XTREAM.VIDEX.m3u8"


def extract_stream_code(url: str) -> str:
  if not url:
    return ""
  from urllib.parse import parse_qs, urlparse

  parsed = urlparse(url)
  if parsed.query:
    query_params = parse_qs(parsed.query)
    if "stream" in query_params:
      return query_params["stream"][0]
  return ""


def generar_m3u():
  try:
    with urllib.request.urlopen(URL_EVENTOS) as response:
      eventos_data = json.loads(response.read().decode())
  except Exception as e:
    print(f"# Error al cargar eventos: {e}")
    return

  try:
    with urllib.request.urlopen(URL_CANALES) as response:
      canales_data = json.loads(response.read().decode())
  except:
    canales_data = []

  m3u_output = ["#EXTM3U"]

  # ==========================================
  # SECCIÓN 1: EVENTOS DEPORTIVOS
  # ==========================================
  event_list = []
  sports = eventos_data.get("sports", [])

  for sport in sports:
    for league in sport.get("leagues", []):
      for event in league.get("events", []):
        title = event.get("title", "Evento sin título")
        raw_time = event.get("time", "")

        display_time = raw_time
        sort_key = "99:99"

        if raw_time:
          try:
            sort_key = raw_time[-5:] if len(raw_time) >= 5 else raw_time
            display_time = sort_key
          except Exception:
            display_time = raw_time
            sort_key = raw_time

        home_logo = event.get("homeLogo", "")
        away_logo = event.get("awayLogo", "")
        main_logo = event.get("logo") or home_logo

        for server in event.get("servers", []):
          if server.get("active") is False:
            continue

          raw_url = server.get("url", "")
          stream_code = extract_stream_code(raw_url)
          if not stream_code:
            continue

          final_url = f"{BASE_URL}{stream_code}{URL_PARAMS}"
          server_name = server.get("name", "Opción")
          display_name = f"{title} [{display_time}] - {server_name}"

          extinf = (
              f'#EXTINF:-1 tvg-logo="{main_logo}" tvg-logo2="{away_logo}"'
              f' group-title="Agenda Deportiva",{display_name}'
          )
          event_list.append({"sort_key": sort_key, "extinf": extinf, "url": final_url})

  event_list.sort(key=lambda x: x["sort_key"])

  for ev in event_list:
    m3u_output.append(ev["extinf"])
    m3u_output.append(ev["url"])

  # ==========================================
  # SECCIÓN 2: CANALES EN VIVO
  # ==========================================
  channels = (
      canales_data.get("channels", canales_data)
      if isinstance(canales_data, dict)
      else canales_data
  )

  for canal in channels:
    if canal.get("active") is False:
      continue

    name = canal.get("name", "Canal sin nombre")
    raw_url = canal.get("url", "")
    logo = canal.get("logo", "")
    category = canal.get("category") or "Canales TV"

    stream_code = extract_stream_code(raw_url)
    if stream_code:
      final_channel_url = f"{BASE_URL}{stream_code}{URL_PARAMS}"
    else:
      final_channel_url = raw_url

    if final_channel_url:
      m3u_output.append(
          f'#EXTINF:-1 tvg-logo="{logo}" group-title="{category}",{name}'
      )
      m3u_output.append(final_channel_url)

  with open("eventos_streamxhd.m3u", "w", encoding="utf-8") as f:
    f.write("\n".join(m3u_output))
  print("¡Archivo eventos_streamxhd.m3u generado con éxito!")


if __name__ == "__main__":
  generar_m3u()