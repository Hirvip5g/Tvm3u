import os
import json
import re
import urllib.parse
import requests
import unicodedata
from datetime import datetime

# Configuración de URLs y archivos locales
AGENDA_URL = "https://streamxhd.sbs/eventos.json?"
LOCAL_CHANNELS_JSON = "04.json"
SOURCE_JSON = "source.json"
CLUB_JSON = "club.json"  # <-- Nuevo archivo para mapeo y alias de equipos
OUTPUT_JSON = "agenda.json"
BASE_IMG_URL = "https://raw.githubusercontent.com/Hirvip5g/Vix/refs/heads/main/assets/equipos_fm"
BASE_LEAGUE_IMG_URL = "https://raw.githubusercontent.com/Hirvip5g/Vix/main/assets/ligas_fm"

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

MAPEO_EQUIPOS = CaseInsensitiveDict({
    "puebla": "7847", "club puebla": "7847", "leon": "1841", "club León": "1841",
    "tigres": "8561", "tigres uanl": "8561", "toluca": "6618", "fc juarez": "649424",
    "juarez": "649424", "tijuana": "162418", "xolos": "162418", "queretaro": "1943",
    "queretaro fc": "1943", "atlante": "1942", "atlas": "6577", "chivas": "7807",
    "chivas guadalajara": "7807", "guadalajara": "7807", "cf america": "6576",
    "america": "6576", "club america": "6576", "monterrey": "7849", "rayados": "7849",
    "atletico de san luis": "6358", "atletico san luis": "6358", "san luis": "6358",
    "santos laguna": "7857", "pachuca": "7848", "necaxa": "1842", "pumas": "1946",
    "pumas unam": "1946", "cruz azul": "6578",
    "malaga": "9864", "espanyol": "8558", "rayo vallecano": "8370", "athletic club": "8315",
    "athletic bilbao": "8315", "deportivo alaves": "9866", "alaves": "9866",
    "atletico madrid": "9906", "atletico de madrid": "9906", "barcelona": "8634",
    "fc barcelona": "8634", "getafe": "8305", "real madrid": "8633", "villarreal": "10205",
    "elche": "10268", "celta vigo": "9910", "celta de vigo": "9910", "celta": "9910",
    "real sociedad": "8560", "deportivo a coruna": "9783", "real betis": "8603",
    "betis": "8603", "osasuna": "8371", "mallorca": "8661", "las palmas": "8306",
    "sevilla": "8302", "levante": "8581", "racing santander": "8696", "ceuta": "357259",
    "sabadell": "4033", "eldense": "8288", "cordoba": "7869", "girona": "7732",
    "arsenal": "9825", "leeds united": "8463", "aston villa": "10252", "brentford": "9937",
    "sunderland": "8472", "brighton & hove albion": "10204", "chelsea": "8455",
    "ipswich town": "9902", "fulham": "9879", "manchester united": "10260",
    "tottenham hotspur": "8586", "tottenham": "8586", "crystal palace": "9826",
    "nottingham forest": "10203", "hull city": "8667", "everton": "8668",
    "liverpool": "8650", "manchester city": "8456", "afc bournemouth": "8678",
    "bournemouth": "8678", "newcastle united": "10261",
    "borussia dortmund": "9789", "werder bremen": "8697", "paderborn": "8460",
    "stuttgart": "10269", "hoffenheim": "8226", "hamburger sv": "9790",
    "augsburg": "8406", "bayern munchen": "9823", "mainz 05": "9905",
    "bayer leverkusen": "8178", "union berlin": "8149", "elversberg": "8232",
    "rb leipzig": "178475", "eintracht frankfurt": "9810",
    "lens": "8588", "olympique lyonnais": "9748", "lille": "8639", "le havre": "9746",
    "lorient": "8689", "paris": "6379", "brest": "8521", "angers sco": "8121",
    "psg": "9847", "le mans": "8682", "monaco": "9829", "toulouse": "9941",
    "genoa": "10233", "fiorentina": "8535", "inter": "8636", "inter de milan": "8636", "parma": "10167",
    "napoli": "9875", "frosinone": "9891",
    "vasco da gama": "10276", "remo": "1626", "são paulo": "10277", "vitória": "7733",
    "boca juniors": "90006", "river plate": "90015", "Slavia Praha": "1901", "Al Qadisiya": "1902", "Fenerbahçe": "1903", "Sabah": "Sabah", "Deportivo La Coruña": "lacoruña", "Celta de Vigo II": "vigo2", "hamburg": "9790", "Durango": "durango", "Lyon": "133713", "Corea del Norte": "153610", "Japón": "153609", "Martinica": "140278", "Aruba": "140264", "Antigua y Barbuda": "140263", "Trinidad y Tobago": "140176", "Progreso": "138815", "Cerro Largo": "138817", "Estudiantes LP": "135160", "Independiente Rivadavia": "137777", "Atlético Morelia": "134190", "Leones Negros UdeG": "134622", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo",
})

MAPEO_LIGAS = CaseInsensitiveDict({
    "LaLiga": "laliga", "Premier League": "premier", "Serie A": "seriea",
    "Bundesliga": "bundesliga", "Ligue 1": "ligue1", "UEFA Champions League": "ucl",
    "Copa Libertadores": "libertadores", "Championship": "championship", "Liga 1": "Liga1",
    "LaLiga SmartBank": "smartbank", "Liga Ecuador": "ligaecuador", "Liga Profesional": "ligaprofesional",
    "Liga Uruguay": "ligauruguay", "MLB": "mlb", "Liga Paraguay": "ligaparaguay",
    "Brasileirão": "brasileirão", "NBA Pretemporada": "nba", "Copa de la Liga": "copadelaliga",
    "Liga MX": "ligamx", "Liga MX Femenil": "ligamx", "Liga de Expansión MX": "expamx", "MLS": "mls", "Super Lig": "superlig",
    "Eredivisie": "eredivisie", "Liga Colombia": "ligaco", "NFL": "nfl", "UFC": "ufc",
    "Saudi Pro League": "saudiproleague", "Primeira Liga": "primeiraligap", "NBA": "nba",
    "NHL": "nhl", "Liga Chile": "ligachile", "MotoGP": "motogp",
    "Copa del Rey": "copadelrey", "Copa Ecuador": "copaecuador", "Copa de Brasil": "copadebrasil", "Messi Cup U16": "nessicupu16", "Copa Colombia": "copacolombia", "AFC Champions League Elite": "championsarabe", "Primera División": "primeradivisión", "UEFA Conference League": "ueafaconferenceleague", "UEFA Europa League": "ueafeuropaleague", "ESPN KnockOut - BXSTRS": "espnknockout", "ATP": "atp", "Fútbol Sala": "futbolsala", "F1": "f1", "Champions League Femenina": "championsleaguefemenina", "Torneo de Reserva": "torneodereserva", "Liga de Naciones": "nationsleague", "Liga de Naciones de la CONCACAF": "cafnationsleague", "Amistoso Internacional": "amistosos", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo", "demo": "demo",
})

def limpiar_para_comparar(texto):
    """Elimina acentos, tildes y caracteres especiales dejando solo alfanuméricos en minúsculas."""
    if not texto:
        return ""
    texto_norm = unicodedata.normalize('NFD', texto).encode('ascii', 'ignore').decode('utf-8').lower()
    return re.sub(r'[^a-z0-9]', '', texto_norm)

def limpiar_nombre_equipo(nombre, liga_nombre=""):
    if not nombre:
        return ""
    return nombre.strip()

def buscar_imagen(equipo_val):
    if not equipo_val:
        return ""
    if equipo_val in MAPEO_EQUIPOS:
        return f"{BASE_IMG_URL}/{MAPEO_EQUIPOS[equipo_val]}.png"
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
                
            matches = re.findall(r"<a href='(/event/(\d+)-([^']+))'>", html_content)
            for full_path, event_id, event_slug in matches:
                event_url = f"https://www.thesportsdb.com{full_path}"
                clean_slug = urllib.parse.unquote(event_slug)
                eventos_dict[clean_slug] = event_url
    except Exception as e:
        print(f"Error al obtener datos web de TheSportsDB para {url}: {e}")
    return eventos_dict, league_logo

def obtener_thumb_de_evento_web(event_url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(event_url, headers=headers, timeout=5)
        if response.status_code == 200:
            match = re.search(r'<meta property="og:image" content="([^"]+)"', response.text)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error al extraer la imagen del evento web {event_url}: {e}")
    return ""

def traducir_sesion(titulo):
    t = titulo.lower()
    if "práctica 1" in t or "practica 1" in t or "fp1" in t: return "practice1"
    if "práctica 2" in t or "practica 2" in t or "fp2" in t: return "practice2"
    if "práctica 3" in t or "practica 3" in t or "fp3" in t: return "practice3"
    if "clasificación" in t or "clasificacion" in t or "quali" in t or "q1" in t or "q2" in t: return "qualifying"
    if "sprint" in t: return "sprint"
    if "carrera" in t or "race" in t or "gp" in t or "grand prix" in t: return "gp"
    return ""

def obtener_alias_equipo(equipo_nombre, clubs_dict):
    """Retorna una lista de palabras clave limpias para el equipo basándose en club.json"""
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
    """Busca coincidencia del evento web usando club.json o por sesión y palabras clave en motor"""
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

def procesar_agenda():
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

    # Cargar club.json si existe
    clubs_dict = {}
    if os.path.exists(CLUB_JSON):
        try:
            with open(CLUB_JSON, "r", encoding="utf-8") as f:
                clubs_dict = json.load(f)
            print(f"Cargado {CLUB_JSON} correctamente.")
        except Exception as e:
            print(f"Error al leer {CLUB_JSON}: {e}")

    print(f"Descargando JSON manual desde {AGENDA_URL}...")
    try:
        response = requests.get(AGENDA_URL, timeout=10)
        if response.status_code != 200:
            return
        agenda_data = response.json()
    except Exception as e:
        print(f"Error: {e}")
        return

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

        if league_url:
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
                league_id = MAPEO_LIGAS.get(league_name, "")
                league["leagueId"] = league_id

                if not league.get("background") and league_id:
                    league["background"] = f"{BASE_LEAGUE_IMG_URL}/{league_id}.jpg"

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
                        event["homeLogo"] = event.get("homeLogo") or buscar_imagen(home_team)
                        event["awayLogo"] = event.get("awayLogo") or buscar_imagen(away_team)
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
                    
                    if web_events:
                        encontrado_url = buscar_evento_web(league_name, original_title, home_team, away_team, web_events, clubs_dict)
                        if encontrado_url:
                            event["sourceEventUrl"] = encontrado_url
                            imagen_web = obtener_thumb_de_evento_web(encontrado_url)
                            if imagen_web and "android-icon" not in imagen_web and "/ico/" not in imagen_web:
                                event_thumb = imagen_web

                    if event_thumb:
                        event["image"] = event_thumb
                        event["imageMode"] = "banner"
                    else:
                        event["image"] = ""
                        event["imageMode"] = ""

                    nuevos_servidores = []
                    for server in event.get("servers", []):
                        server_url = server.get("url", "")
                        parsed_url = urllib.parse.urlparse(server_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        
                        channel_param = query_params.get("channel", [""])[0].strip().lower()
                        if not channel_param:
                            channel_param = query_params.get("stream", [""])[0].strip().lower()

                        iframe_url = f"https://pruevon.blogspot.com/2026/04/embedc.html?r={urllib.parse.quote(server_url, safe='')}"
                        server_copy = dict(server)
                        server_copy["url"] = iframe_url
                        server_copy["type"] = "iframe"
                        nuevos_servidores.append(server_copy)

                        if channel_param and channel_param in canales_04_dict:
                            for canal_info in canales_04_dict[channel_param]:
                                nuevos_servidores.append({
                                    "name": canal_info.get("canal", server.get("name", channel_param.upper())),
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

    if "updated" not in agenda_data or not agenda_data["updated"]:
        agenda_data["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(agenda_data, f, ensure_ascii=False, indent=4)

    print(f"Agenda procesada correctamente en {OUTPUT_JSON}.")

if __name__ == "__main__":
    procesar_agenda()