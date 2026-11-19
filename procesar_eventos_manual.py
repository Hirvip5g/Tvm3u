import os
import json
import re
import urllib.parse
import hashlib
import requests
import unicodedata
import pyrebase
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo

# Configuración de Firebase cargada dinámicamente desde variables de entorno (GitHub Secrets)
firebaseConfig = {
    "apiKey": os.environ.get("FIREBASE_API_KEY"),
    "authDomain": os.environ.get("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.environ.get("FIREBASE_DATABASE_URL"),
    "projectId": os.environ.get("FIREBASE_PROJECT_ID"),
    "storageBucket": os.environ.get("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.environ.get("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.environ.get("FIREBASE_APP_ID")
}

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

# Configuración de URLs y archivos locales
AGENDA_HTML_URL = "https://futbol-libre.app/agenda"
LOCAL_CHANNELS_JSON = "04.json"
SOURCE_JSON = "source.json"
CLUB_JSON = "club.json"
EQUIPOS_JSON = "equipos.json"
LIGAS_JSON = "ligas.json"
OUTPUT_JSON = "agenda.json"
HASH_FILE = ".eventos_hash.txt"
FECHA_FILE = ".ultima_actualizacion_dia.txt"

# Zona horaria destino (puedes cambiar a "America/El_Salvador" o "America/Lima")
ZONA_DESTINO = ZoneInfo("America/El_Salvador")


class CaseInsensitiveDict(dict):
    def __init__(self, data=None, **kwargs):
        super().__init__()
        if data:
            self.update(data)
        if kwargs:
            self.update(kwargs)

    def _normalize(self, key):
        if not isinstance(key, str):
            return key
        texto = unicodedata.normalize('NFD', key)
        texto = texto.encode('ascii', 'ignore').decode('utf-8')
        return texto.strip().lower()

    def __setitem__(self, key, value):
        super().__setitem__(self._normalize(key), value)

    def __getitem__(self, key):
        return super().__getitem__(self._normalize(key))

    def __contains__(self, key):
        return super().__contains__(self._normalize(key))

    def get(self, key, default=None):
        return super().get(self._normalize(key), default)

    def update(self, E=None, **F):
        if E is not None:
            if hasattr(E, 'keys'):
                for k in E:
                    super().__setitem__(self._normalize(k), E[k])
            else:
                for k, v in E:
                    super().__setitem__(self._normalize(k), v)
            for k in F:
                super().__setitem__(self._normalize(k), F[k])


MAPEO_CODIGOS_LIGA = CaseInsensitiveDict({
    "Liga MX": "LIGAMX", "MEX": "LIGAMX", "Serie A": "IT", "IT": "IT",
    "Liga Profesional": "AR", "AR": "AR", "Copa do Brasil": "BRA", "BRA": "BRA",
    "Liga Colombia": "COL", "Liga BetPlay": "COL", "COL": "COL",
    "Liga de Expansión MX": "MEX", "Eredivisie": "HOL", "HOL": "HOL",
    "FA Cup": "ENG", "Bundesliga 2": "ALE", "Premier League": "ENG", "ENG": "ENG",
    "LaLiga": "ESP", "ES": "ESP", "Ligue 1": "FRA", "FRA": "FRA",
    "Bundesliga": "ALE", "ALE": "ALE", "Liga Chile": "CH", "CHI": "CH",
    "Primera División": "CH", "Super Lig": "TUR", "TUR": "TUR", "NWSL": "NWSL",
    "Primeira Liga": "POR", "POR": "POR", "Superliga Grecia": "GRE",
    "Superliga de Grecia": "GRE", "GR": "GRE", "Liga Guatemala": "GUA",
    "NBA": "NBA", "NHL": "NHL", "MotoGP": "MOTOGP", "F1": "F1", "NFL": "NFL",
    "MLS": "MLS", "Brasileirão": "BRA", "Liga Uruguay": "URU"
})


def limpiar_para_comparar(texto):
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', texto_norm)


def limpiar_nombre_equipo(nombre, liga_nombre=""):
    if not nombre:
        return ""
    return nombre.strip()


def buscar_imagen(equipo_val, equipos_dict):
    if not equipo_val:
        return ""
    if equipo_val in equipos_dict:
        return equipos_dict[equipo_val]
    return ""


def obtener_datos_liga_thesportsdb(league_input):
    if league_input.startswith("http"):
        url = league_input
    else:
        url = f"https://www.thesportsdb.com/league/{league_input}"

    eventos_dict = {}
    league_logo = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html_content = response.text
            match_logo = re.search(r'<meta property="og:image" content="([^"]+)"', html_content)
            if match_logo:
                league_logo = match_logo.group(1)

            matches = re.findall(r'<a\s+href=["\'](/event/(\d+)-([^"\']+))["\']', html_content)
            for full_path, event_id, event_slug in matches:
                event_url = f"https://www.thesportsdb.com{full_path}"
                clean_slug = urllib.parse.unquote(event_slug)
                eventos_dict[clean_slug] = event_url
    except Exception as e:
        print(f"Error al obtener datos web de TheSportsDB para {url}: {e}")
    return eventos_dict, league_logo


def obtener_detalles_de_evento_web(event_url):
    thumb = ""
    home_logo_web = ""
    away_logo_web = ""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(event_url, headers=headers, timeout=5)
        if response.status_code == 200:
            html = response.text
            match_thumb = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', html)
            if match_thumb:
                thumb = match_thumb.group(1)

            matches_badges = re.findall(r'src=["\'](https://r2\.thesportsdb\.com/images/media/team/badge/[^"\']+\.png(?:/[a-z]+)?)["\']', html)
            if len(matches_badges) >= 2:
                home_logo_web = matches_badges[0]
                away_logo_web = matches_badges[1]
            elif len(matches_badges) == 1:
                home_logo_web = matches_badges[0]
    except Exception as e:
        print(f"Error al extraer detalles del evento web {event_url}: {e}")
    return thumb, home_logo_web, away_logo_web


def traducir_sesion(titulo):
    t = titulo.lower()
    if "práctica 1" in t or "practica 1" in t or "fp1" in t:
        return "practice1"
    if "práctica 2" in t or "practica 2" in t or "fp2" in t:
        return "practice2"
    if "práctica 3" in t or "practica 3" in t or "fp3" in t:
        return "practice3"
    if "clasificación" in t or "clasificacion" in t or "quali" in t or "q1" in t or "q2" in t:
        return "qualifying"
    if "sprint" in t:
        return "sprint"
    if "carrera" in t or "race" in t or "gp" in t or "grand prix" in t:
        return "gp"
    return ""


def obtener_alias_equipo(equipo_nombre, clubs_dict):
    palabras_clave = [limpiar_para_comparar(equipo_nombre)]
    if not clubs_dict:
        return palabras_clave

    nombre_clean = limpiar_para_comparar(equipo_nombre)
    for club_key, info in clubs_dict.items():
        key_clean = limpiar_para_comparar(club_key)
        aliases = info.get("aliases", []) if isinstance(info, dict) else []
        search_name = info.get("search_name", "") if isinstance(info, dict) else ""

        aliases_clean = [limpiar_para_comparar(a) for a in aliases]
        if search_name:
            aliases_clean.append(limpiar_para_comparar(search_name))

        if nombre_clean == key_clean or nombre_clean in aliases_clean:
            palabras_clave.append(key_clean)
            palabras_clave.extend(aliases_clean)
            break

    return list(set(filter(None, palabras_clave)))


def buscar_evento_web(league_name, original_title, home_team, away_team, web_events_dict, clubs_dict):
    if not web_events_dict:
        return ""

    ln_upper = league_name.upper()
    if "F1" in ln_upper or "FORMULA" in ln_upper or "MOTOGP" in ln_upper:
        sesion_buscada = traducir_sesion(original_title)
        keywords_extra = obtener_alias_equipo(original_title, clubs_dict)
        titulo_norm = limpiar_para_comparar(original_title)

        mejor_url = ""
        max_puntuacion = -1

        for web_slug, web_url in web_events_dict.items():
            web_slug_clean = limpiar_para_comparar(web_slug)
            puntuacion = 0

            if sesion_buscada and sesion_buscada in web_slug_clean:
                puntuacion += 10
            for kw in keywords_extra:
                if kw and kw in web_slug_clean and kw != sesion_buscada:
                    puntuacion += 5
            for palabra in titulo_norm.split():
                if len(palabra) > 3 and palabra in web_slug_clean and palabra != sesion_buscada:
                    puntuacion += 2

            if puntuacion > max_puntuacion:
                max_puntuacion = puntuacion
                mejor_url = web_url

        if mejor_url and max_puntuacion > 0:
            return mejor_url
        return ""
    else:
        home_keywords = obtener_alias_equipo(home_team, clubs_dict)
        away_keywords = obtener_alias_equipo(away_team, clubs_dict)

        for web_slug, web_url in web_events_dict.items():
            web_slug_clean = limpiar_para_comparar(web_slug)
            match_home = any(kw and kw in web_slug_clean for kw in home_keywords)
            match_away = any(kw and kw in web_slug_clean for kw in away_keywords)

            if match_home and match_away:
                return web_url
    return ""


def obtener_deporte_info(league_name, title_text=""):
    combined = f"{league_name} {title_text}".lower()
    if "nba" in combined or "basketball" in combined or "básquetbol" in combined or "ncaa mens basketball" in combined:
        return "basketball", "Basketball", "🏀"
    elif "ufc" in combined or "box" in combined or "boxing" in combined or "knockout" in combined:
        return "boxing", "Boxing", "🥊"
    elif "nfl" in combined or "football americano" in combined:
        return "american-football", "American Football", "🏈"
    elif "f1" in combined or "formula" in combined or "motogp" in combined:
        return "motor", "Motor", "🏎️"
    elif "nhl" in combined or "hockey" in combined:
        return "hockey", "Hockey", "🏒"
    else:
        return "football", "Football", "⚽"


def obtener_duracion_por_deporte(sport_id):
    if sport_id in ["basketball", "american-football", "nfl", "nba"]:
        return 180
    elif sport_id in ["hockey", "nhl"]:
        return 160
    elif sport_id in ["motor", "f1", "motogp"]:
        return 150
    return 130


def extraer_eventos_desde_html(html_content, base_url):
    soup = BeautifulSoup(html_content, "html.parser")
    eventos_extraidos = []

    for ev_div in soup.select(".source-agenda-event[data-agenda-event]"):
        instant_raw = (ev_div.get("data-source-instant") or "").strip()

        comp_el = ev_div.select_one(".source-agenda-competition")
        league_name = "Fútbol"
        if comp_el:
            league_name = comp_el.get_text(" ", strip=True).rstrip(":").strip() or "Fútbol"

        text_container = ev_div.select_one(".source-agenda-eventtext")
        raw_title = ""
        if text_container:
            # Clonamos o extraemos el texto sin repetir el nombre de la competición
            full_text = " ".join(text_container.get_text(" ", strip=True).split())
            if comp_el:
                comp_text = " ".join(comp_el.get_text(" ", strip=True).split())
                if full_text.startswith(comp_text):
                    raw_title = full_text[len(comp_text):].lstrip(":").strip()
                else:
                    raw_title = full_text.replace(comp_text, "", 1).lstrip(":").strip()
            else:
                raw_title = full_text

        count_el = ev_div.select_one(".source-agenda-count")
        count_text = count_el.get_text(strip=True) if count_el else ""
        status = "FT" if count_text.upper() == "FT" else ""

        canales = []
        for src_a in ev_div.select(".source-agenda-sources a.agenda-source-button"):
            href = (src_a.get("href") or "").strip()
            full_href = urllib.parse.urljoin(base_url, href) if href else ""

            small_el = src_a.select_one("small")
            span_el = src_a.select_one("span")

            canal_nombre = ""
            if small_el:
                canal_nombre = " ".join(small_el.get_text(" ", strip=True).split())
            if not canal_nombre and span_el:
                canal_nombre = " ".join(span_el.get_text(" ", strip=True).split())
            if not canal_nombre:
                canal_nombre = "Fuente"

            canales.append({
                "nombre": canal_nombre,
                "calidad": "",
                "url": full_href
            })

        eventos_extraidos.append({
            "instant_iso": instant_raw,
            "league": league_name,
            "title": raw_title,
            "status": status,
            "canales": canales
        })

    return eventos_extraidos


def procesar_agenda():
    print(f"Descargando agenda HTML desde {AGENDA_HTML_URL}...")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }
        response = requests.get(AGENDA_HTML_URL, headers=headers, timeout=15)
        if response.status_code != 200:
            print(f"Error al descargar el HTML. Código de estado: {response.status_code}")
            return

        html_content = response.text
        hoy_str = datetime.now(ZONA_DESTINO).strftime("%Y-%m-%d")
        nuevo_hash = hashlib.sha256(html_content.encode("utf-8")).hexdigest()

        hash_anterior = ""
        if os.path.exists(HASH_FILE):
            with open(HASH_FILE, "r", encoding="utf-8") as f:
                hash_anterior = f.read().strip()

        ultima_fecha_actualizada = ""
        if os.path.exists(FECHA_FILE):
            with open(FECHA_FILE, "r", encoding="utf-8") as f:
                ultima_fecha_actualizada = f.read().strip()

        # 1. Solo actualizar si el contenido del HTML cambió
        if nuevo_hash == hash_anterior:
            print("No hubo cambios en el HTML de la agenda. Se omite la actualización.")
            return

        # 2. Máximo 1 actualización por día aunque cambie varias veces hoy
        if ultima_fecha_actualizada == hoy_str:
            print(f"El HTML cambió, pero hoy ({hoy_str}) ya se realizó la actualización diaria. Se espera hasta mañana.")
            return

        raw_data = extraer_eventos_desde_html(html_content, AGENDA_HTML_URL)
        print(f"Eventos extraídos desde HTML: {len(raw_data)}")

    except Exception as e:
        print(f"Error al procesar {AGENDA_HTML_URL}: {e}")
        return

    # Cargar equipos.json
    equipos_dict = CaseInsensitiveDict()
    if os.path.exists(EQUIPOS_JSON):
        try:
            with open(EQUIPOS_JSON, "r", encoding="utf-8") as f:
                raw_eq = json.load(f)
                equipos_dict.update(raw_eq)
            print(f"Cargado {EQUIPOS_JSON} correctamente.")
        except Exception as e:
            print(f"Error al leer {EQUIPOS_JSON}: {e}")

    # Cargar ligas.json
    ligas_dict = CaseInsensitiveDict()
    if os.path.exists(LIGAS_JSON):
        try:
            with open(LIGAS_JSON, "r", encoding="utf-8") as f:
                raw_lg = json.load(f)
                ligas_dict.update(raw_lg)
            print(f"Cargado {LIGAS_JSON} correctamente.")
        except Exception as e:
            print(f"Error al leer {LIGAS_JSON}: {e}")

    # Cargar 04.json
    canales_04_dict = {}
    if os.path.exists(LOCAL_CHANNELS_JSON):
        try:
            with open(LOCAL_CHANNELS_JSON, "r", encoding="utf-8") as f:
                contenido_04 = json.load(f)
                if isinstance(contenido_04, list):
                    for c in contenido_04:
                        ch_key = c.get("channel", "").strip().lower()
                        if ch_key:
                            if ch_key not in canales_04_dict:
                                canales_04_dict[ch_key] = []
                            canales_04_dict[ch_key].append(c)
        except Exception as e:
            print(f"Error al leer {LOCAL_CHANNELS_JSON}: {e}")

    # Cargar club.json
    clubs_dict = {}
    if os.path.exists(CLUB_JSON):
        try:
            with open(CLUB_JSON, "r", encoding="utf-8") as f:
                clubs_dict = json.load(f)
            print(f"Cargado {CLUB_JSON} correctamente.")
        except Exception as e:
            print(f"Error al leer {CLUB_JSON}: {e}")

    sports_map = {}
    order_counter = 1

    for item in raw_data:
        league_name = item.get("league", "Fútbol").strip() or "Fútbol"
        raw_titulo = item.get("title", "").strip()
        instant_iso = item.get("instant_iso", "").strip()
        status = item.get("status", "")

        if instant_iso:
            try:
                dt_utc = datetime.fromisoformat(instant_iso)
                if dt_utc.tzinfo is None:
                    dt_utc = dt_utc.replace(tzinfo=ZoneInfo("UTC"))
                dt_local = dt_utc.astimezone(ZONA_DESTINO)
            except Exception:
                dt_local = datetime.now(ZONA_DESTINO)
        else:
            dt_local = datetime.now(ZONA_DESTINO)

        date_str = dt_local.strftime("%Y-%m-%d")
        time_val = dt_local.strftime("%H:%M")
        offset_raw = dt_local.strftime("%z")
        offset_fmt = f"{offset_raw[:3]}:{offset_raw[3:]}" if len(offset_raw) == 5 else "+00:00"
        full_time_str = f"{date_str}T{dt_local.strftime('%H:%M:%S')}{offset_fmt}"

        event_title = raw_titulo
        if ":" in raw_titulo:
            parts = raw_titulo.split(":", 1)
            potential_league = parts[0].strip()
            potential_title = parts[1].strip()
            codes_directos = ["nfl", "f1", "motogp", "nba", "ufc", "nhl", "mls", "sports"]
            if league_name.lower() in codes_directos and potential_title:
                if league_name.lower() == "sports" and potential_league:
                    league_name = potential_league
                event_title = potential_title

        home_team = ""
        away_team = ""
        # Soporta " vs ", " vs. " y " – " / " - " (evitando sesiones de motor)
        vs_match = re.split(r'\s+vs\.?\s+', event_title, maxsplit=1, flags=re.IGNORECASE)
        if len(vs_match) == 2:
            home_team = vs_match[0].strip()
            away_team = vs_match[1].strip()
            event_title = f"{home_team} vs {away_team}"
        elif not any(kw in event_title.lower() for kw in ["gp", "práctica", "practica", "clasificación", "clasificacion", "entrenamientos", "carrera", "on board"]):
            dash_match = re.split(r'\s+[–-]\s+', event_title, maxsplit=1)
            if len(dash_match) == 2:
                # Limpiar marcadores numéricos si vienen pegados, ej: "Always Ready 3" -> "Always Ready"
                home_team = re.sub(r'\s+\d+$', '', dash_match[0].strip()).strip()
                away_team = re.sub(r'^\d+\s+', '', dash_match[1].strip()).strip()

        sport_id, sport_name, sport_icon = obtener_deporte_info(league_name, event_title)

        if sport_id not in sports_map:
            sports_map[sport_id] = {
                "id": sport_id,
                "name": sport_name,
                "icon": sport_icon,
                "leagues_map": {}
            }

        leagues_in_sport = sports_map[sport_id]["leagues_map"]
        if league_name not in leagues_in_sport:
            leagues_in_sport[league_name] = {
                "name": league_name,
                "logo": "",
                "image": "",
                "background": "",
                "events_map": {}
            }

        event_key = (event_title, date_str, full_time_str)
        events_in_league = leagues_in_sport[league_name]["events_map"]

        if event_key not in events_in_league:
            events_in_league[event_key] = {
                "title": event_title,
                "league": league_name,
                "code": MAPEO_CODIGOS_LIGA.get(league_name, ""),
                "time": full_time_str,
                "timezone": str(ZONA_DESTINO),
                "agendaOrder": order_counter,
                "image": "",
                "logo": "",
                "homeTeam": home_team,
                "awayTeam": away_team,
                "homeLogo": "",
                "awayLogo": "",
                "imageMode": "",
                "duration": obtener_duracion_por_deporte(sport_id),
                "extraTime": 0,
                "status": status,
                "note": "",
                "servers": [],
                "flagCode": "",
                "flagUrl": "",
                "homeCountryCode": "",
                "awayCountryCode": ""
            }
            order_counter += 1

        for canal in item.get("canales", []):
            canal_nombre = canal.get("nombre", "").strip()
            canal_calidad = canal.get("calidad", "")
            link_limpio = canal.get("url", "")

            server_entry = {
                "name": canal_nombre,
                "url": link_limpio,
                "type": "iframe",
                "quality": canal_calidad,
                "active": True,
                "languages": [],
                "customLanguages": "",
                "channelLogo": ""
            }
            events_in_league[event_key]["servers"].append(server_entry)

    formatted_sports = []
    for s_id, s_data in sports_map.items():
        formatted_leagues = []
        for l_name, l_data in s_data["leagues_map"].items():
            formatted_leagues.append({
                "name": l_data["name"],
                "logo": l_data["logo"],
                "image": l_data["image"],
                "background": l_data["background"],
                "events": list(l_data["events_map"].values()),
                "flagCode": "",
                "flagUrl": "",
                "leagueId": ""
            })
        formatted_sports.append({
            "id": s_data["id"],
            "name": s_data["name"],
            "icon": s_data["icon"],
            "leagues": formatted_leagues
        })

    agenda_data = {
        "sports": formatted_sports,
        "updated": datetime.now(ZONA_DESTINO).strftime("%Y-%m-%d %H:%M:%S")
    }

    # Cargar source.json para logos/eventos de TheSportsDB
    sources_ligas = {}
    if os.path.exists(SOURCE_JSON):
        try:
            with open(SOURCE_JSON, "r", encoding="utf-8") as f:
                sources_ligas = json.load(f)
        except Exception as e:
            print(f"Error al leer {SOURCE_JSON}: {e}")

    web_events_por_liga = {}
    logos_liga_por_liga = {}

    for league_key, data in sources_ligas.items():
        if isinstance(data, dict):
            league_url = data.get("url", "")
            aliases = data.get("aliases", [league_key.lower()])
        else:
            league_url = data
            aliases = [league_key.lower()]

        if league_url and league_url != "demo":
            print(f"Obteniendo eventos y logo web de TheSportsDB para la liga '{league_key}'...")
            eventos_remotos, league_logo = obtener_datos_liga_thesportsdb(league_url)

            for alias in aliases:
                alias_clean = alias.lower().strip()
                web_events_por_liga[alias_clean] = eventos_remotos
                logos_liga_por_liga[alias_clean] = league_logo

            league_key_clean = league_key.lower().strip()
            web_events_por_liga[league_key_clean] = eventos_remotos
            logos_liga_por_liga[league_key_clean] = league_logo

    if "sports" in agenda_data:
        for sport in agenda_data["sports"]:
            for league in sport.get("leagues", []):
                league_name = league.get("name", "")

                liga_info = ligas_dict.get(league_name, {})
                if isinstance(liga_info, dict):
                    league["leagueId"] = liga_info.get("leagueId", "")
                    if not league.get("background"):
                        league["background"] = liga_info.get("background", "")

                web_events = {}
                league_logo_web = ""
                league_name_lower = league_name.lower().strip()

                if league_name_lower in web_events_por_liga:
                    web_events = web_events_por_liga[league_name_lower]
                    league_logo_web = logos_liga_por_liga.get(league_name_lower, "")
                else:
                    for alias_key, w_events in web_events_por_liga.items():
                        if alias_key in league_name_lower or league_name_lower in alias_key:
                            web_events = w_events
                            league_logo_web = logos_liga_por_liga.get(alias_key, "")
                            break

                if league_logo_web:
                    league["logo"] = league_logo_web

                for event in league.get("events", []):
                    home_raw = event.get("homeTeam", "")
                    away_raw = event.get("awayTeam", "")
                    original_title = event.get("title", "")

                    is_motor = league_name.upper() in ["F1", "MOTOGP"] or "GP " in home_raw or "Práctica" in away_raw or "Clasificación" in away_raw
                    is_match = bool(home_raw and away_raw) and not is_motor

                    if is_match:
                        home_team = limpiar_nombre_equipo(home_raw, league_name)
                        away_team = limpiar_nombre_equipo(away_raw, league_name)
                        event["homeTeam"] = home_team
                        event["awayTeam"] = away_team
                        event["title"] = f"{home_team} vs {away_team}"
                        event["homeLogo"] = event.get("homeLogo") or buscar_imagen(home_team, equipos_dict)
                        event["awayLogo"] = event.get("awayLogo") or buscar_imagen(away_team, equipos_dict)
                    else:
                        home_team = ""
                        away_team = ""
                        if not original_title:
                            original_title = f"{home_raw} - {away_raw}" if (home_raw and away_raw) else (home_raw or away_raw)
                        event["title"] = original_title
                        event["homeTeam"] = ""
                        event["awayTeam"] = ""
                        event["homeLogo"] = ""
                        event["awayLogo"] = ""

                    event_thumb = ""
                    web_home_logo = ""
                    web_away_logo = ""

                    if web_events:
                        encontrado_url = buscar_evento_web(league_name, original_title, home_team, away_team, web_events, clubs_dict)
                        if encontrado_url:
                            event["sourceEventUrl"] = encontrado_url
                            imagen_web, h_logo_web, a_logo_web = obtener_detalles_de_evento_web(encontrado_url)
                            if imagen_web and "android-icon" not in imagen_web and "/ico/" not in imagen_web:
                                event_thumb = imagen_web
                            if h_logo_web:
                                web_home_logo = h_logo_web
                            if a_logo_web:
                                web_away_logo = a_logo_web

                    if event_thumb:
                        event["image"] = event_thumb
                        event["imageMode"] = "banner"
                    else:
                        event["image"] = ""
                        event["imageMode"] = ""

                    if is_match:
                        if not event.get("homeLogo"):
                            event["homeLogo"] = web_home_logo or buscar_imagen(home_team, equipos_dict)
                        if not event.get("awayLogo"):
                            event["awayLogo"] = web_away_logo or buscar_imagen(away_team, equipos_dict)

                    canales_04_por_nombre = {}
                    for k_04, lista_canales in canales_04_dict.items():
                        for c_info in lista_canales:
                            c_nombre_raw = c_info.get("canal", "").strip()
                            if c_nombre_raw:
                                canales_04_por_nombre[c_nombre_raw.lower()] = c_info

                    nuevos_servidores = []
                    for server in event.get("servers", []):
                        server_url = server.get("url", "")
                        parsed_url = urllib.parse.urlparse(server_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)

                        channel_param = query_params.get("channel", [""])[0].strip().lower()
                        if not channel_param:
                            channel_param = query_params.get("stream", [""])[0].strip().lower()

                        server_name = server.get("name", "").strip()
                        server_name_lower = server_name.lower()
                        channel_param_lower = channel_param.lower()

                        if not server_name:
                            if channel_param:
                                server_name = channel_param.replace("-", " ").upper()
                            else:
                                path_part = parsed_url.path.split("/")[-1].replace(".html", "").replace(".php", "")
                                if path_part and path_part != "embedc":
                                    server_name = path_part.replace("-", " ").upper()
                                else:
                                    server_name = "SERVIDOR"

                        canal_exacto_04 = canales_04_por_nombre.get(server_name_lower)

                        if canal_exacto_04:
                            nuevos_servidores.append({
                                "name": canal_exacto_04.get("canal", server_name),
                                "url": canal_exacto_04.get("url", ""),
                                "type": canal_exacto_04.get("tipo", "clearkey"),
                                "quality": server.get("quality", ""),
                                "active": True,
                                "languages": server.get("languages", []),
                                "customLanguages": server.get("customLanguages", ""),
                                "channelLogo": canal_exacto_04.get("logo", server.get("channelLogo", "")),
                                "clearkey": canal_exacto_04.get("clearkey", None),
                                "referer": canal_exacto_04.get("referer", ""),
                                "origin": canal_exacto_04.get("origin", ""),
                                "userAgent": canal_exacto_04.get("userAgent", "")
                            })
                        else:
                            iframe_url = f"https://pruevon.blogspot.com/2026/04/embedc.html?r={urllib.parse.quote(server_url, safe='')}"
                            server_copy = dict(server)
                            server_copy["name"] = server_name
                            server_copy["url"] = iframe_url
                            server_copy["type"] = "iframe"
                            nuevos_servidores.append(server_copy)

                            canales_encontrados_lista = []
                            if channel_param in canales_04_dict:
                                canales_encontrados_lista.extend(canales_04_dict[channel_param])

                            for k_04, lista_canales in canales_04_dict.items():
                                for c_info in lista_canales:
                                    c_channel = c_info.get("channel", "").strip().lower()
                                    if server_name_lower == c_channel or channel_param_lower == c_channel:
                                        if c_info not in canales_encontrados_lista:
                                            canales_encontrados_lista.append(c_info)

                            for canal_info in canales_encontrados_lista:
                                nuevos_servidores.append({
                                    "name": canal_info.get("canal", server_name),
                                    "url": canal_info.get("url", ""),
                                    "type": canal_info.get("tipo", "clearkey"),
                                    "quality": server.get("quality", ""),
                                    "active": True,
                                    "languages": server.get("languages", []),
                                    "customLanguages": server.get("customLanguages", ""),
                                    "channelLogo": canal_info.get("logo", server.get("channelLogo", "")),
                                    "clearkey": canal_info.get("clearkey", None),
                                    "referer": canal_info.get("referer", ""),
                                    "origin": canal_info.get("origin", ""),
                                    "userAgent": canal_info.get("userAgent", "")
                                })

                    event["servers"] = nuevos_servidores

    # Guardar localmente
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(agenda_data, f, ensure_ascii=False, indent=4)
    print(f"Agenda procesada correctamente en {OUTPUT_JSON}.")

    # Enviar directamente a Firebase usando firebaseConfig
    try:
        print("Subiendo agenda procesada a Firebase Realtime Database...")
        db.child("config").child("ventanatv").child("agendaData").set(agenda_data)
        print("¡Agenda enviada y sincronizada en Firebase exitosamente!")

        with open(HASH_FILE, "w", encoding="utf-8") as f:
            f.write(nuevo_hash)
        with open(FECHA_FILE, "w", encoding="utf-8") as f:
            f.write(hoy_str)
    except Exception as e:
        print(f"Error al subir a Firebase: {e}")


if __name__ == "__main__":
    procesar_agenda()