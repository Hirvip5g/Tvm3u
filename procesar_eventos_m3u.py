import os
import json
import re
import urllib.parse
import requests
import unicodedata
from datetime import datetime

# Configuración de URLs y archivos
M3U_URL = "https://superflash.ovh:8080/get.php?username=Bzcarlosdelap160323&password=zN9Kn8FM9zHH&type=m3u_plus"
OUTPUT_JSON = "agenda.json"
BASE_LEAGUE_IMG_URL = "https://raw.githubusercontent.com/Configuracao/Vix/main/assets/ligas_fm"

MAPEO_DEPORTES = {
    "futbol": {"id": "football", "name": "Football", "icon": "⚽"},
    "fútbol": {"id": "football", "name": "Football", "icon": "⚽"},
    "eventos diarios": {"id": "football", "name": "Football", "icon": "⚽"},
    "agenda latina": {"id": "football", "name": "Football", "icon": "⚽"},
    "nba | mlb | nhl | nfl": {"id": "basketball", "name": "Basketball", "icon": "🏀"},
    "baloncesto": {"id": "basketball", "name": "Basketball", "icon": "🏀"},
    "fiba": {"id": "basketball", "name": "Basketball", "icon": "🏀"},
    "tennis": {"id": "other", "name": "Otros Deportes", "icon": "🎾"},
    "golf": {"id": "other", "name": "Otros Deportes", "icon": "⛳"},
    "nfl": {"id": "nfl", "name": "American Football", "icon": "🏈"},
    "motor": {"id": "motor", "name": "Motor", "icon": "🏎️"},
    "f1": {"id": "motor", "name": "Motor", "icon": "🏎️"}
}

def clasificar_deporte(group_title):
    gt_lower = group_title.lower()
    for key, val in MAPEO_DEPORTES.items():
        if key in gt_lower:
            return val
    return {"id": "football", "name": "Football", "icon": "⚽"}

def generar_agenda_m3u():
    print(f"Descargando lista M3U desde Xtream Codes...")
    
    # Cabeceras para evitar bloqueos por parte del panel IPTV
    headers = {
        "User-Agent": "VLC/3.0.16 LibVLC/3.0.16"
    }
    
    try:
        response = requests.get(M3U_URL, headers=headers, timeout=30)
        print(f"Status Code recibido: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Error: El servidor respondió con el código {response.status_code}")
            return
        
        content = response.text
        lines = content.split("\n")
        print(f"Líneas descargadas del M3U: {len(lines)}")
        
        sports_map = {}
        current_extinf = None
        order_counter = 1
        canales_procesados = 0

        for line in lines:
            line_str = line.strip()
            if line_str.startswith("#EXTINF:"):
                current_extinf = line_str
            elif current_extinf and line_str and not line_str.startswith("#"):
                stream_url = line_str
                upper_extinf = current_extinf.upper()
                
                # Filtrar VOD, películas y series
                if not any(k in upper_extinf for k in ['VOD', 'PELICULA', 'SERIE', 'MOVIE']):
                    canales_procesados += 1
                    
                    # Extraer group-title
                    group_match = re.search(r'group-title="([^"]*)"', current_extinf)
                    group_title = group_match.group(1) if group_match else "General"
                    
                    # Extraer logo
                    logo_match = re.search(r'tvg-logo="([^"]*)"', current_extinf)
                    channel_logo = logo_match.group(1) if logo_match else ""

                    # Extraer nombre del canal
                    parts = current_extinf.split(',')
                    channel_name = parts[-1].strip() if len(parts) > 1 else "Evento"

                    home_team, away_team = channel_name, ""
                    image_mode = "banner"
                    if " vs " in channel_name.lower():
                        teams = channel_name.split(" vs ")
                        if len(teams) == 2:
                            home_team = teams[0].strip()
                            away_team = teams[1].strip()
                            image_mode = "teams"

                    info_deporte = clasificar_deporte(group_title)
                    sport_id = info_deporte["id"]
                    sport_name = info_deporte["name"]
                    sport_icon = info_deporte["icon"]
                    
                    league_name = group_title
                    league_id = unicodedata.normalize('NFD', group_title).encode('ascii', 'ignore').decode('utf-8').strip().lower().replace(" ", "").replace("|", "")

                    if sport_id not in sports_map:
                        sports_map[sport_id] = {
                            "id": sport_id,
                            "name": sport_name,
                            "icon": sport_icon,
                            "leagues_dict": {}
                        }

                    if league_id not in sports_map[sport_id]["leagues_dict"]:
                        sports_map[sport_id]["leagues_dict"][league_id] = {
                            "name": league_name,
                            "logo": "",
                            "image": "",
                            "background": f"{BASE_LEAGUE_IMG_URL}/{league_id}.jpg",
                            "events": [],
                            "flagCode": "",
                            "flagUrl": "",
                            "leagueId": league_id
                        }

                    event_obj = {
                        "title": channel_name,
                        "league": league_name,
                        "code": league_id.upper()[:3],
                        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "timezone": "America/Lima",
                        "agendaOrder": order_counter,
                        "image": channel_logo,
                        "logo": channel_logo,
                        "homeTeam": home_team,
                        "awayTeam": away_team,
                        "homeLogo": "",
                        "awayLogo": "",
                        "imageMode": image_mode,
                        "duration": 130,
                        "extraTime": 0,
                        "status": "",
                        "note": "",
                        "servers": [
                            {
                                "name": channel_name,
                                "url": stream_url,
                                "type": "m3u8" if ".m3u8" in stream_url else "clearkey",
                                "quality": "",
                                "active": True,
                                "languages": [],
                                "customLanguages": "",
                                "channelLogo": channel_logo,
                                "clearkey": None,
                                "referer": "",
                                "origin": "",
                                "userAgent": ""
                            }
                        ],
                        "flagCode": "",
                        "flagUrl": "",
                        "homeCountryCode": "",
                        "awayCountryCode": "",
                        "leagueId": league_id,
                        "leagueBackground": f"{BASE_LEAGUE_IMG_URL}/{league_id}.jpg"
                    }

                    sports_map[sport_id]["leagues_dict"][league_id]["events"].append(event_obj)
                    order_counter += 1

                current_extinf = None

        print(f"Total de canales en vivo procesados: {canales_procesados}")

        final_sports_list = []
        for sport_id, sport_data in sports_map.items():
            leagues_list = list(sport_data["leagues_dict"].values())
            final_sports_list.append({
                "id": sport_data["id"],
                "name": sport_data["name"],
                "icon": sport_data["icon"],
                "leagues": leagues_list
            })

        output_data = {
            "sports": final_sports_list,
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=4)

        print(f"¡Archivo {OUTPUT_JSON} creado y guardado exitosamente!")

    except Exception as e:
        print(f"Excepción crítica procesando la lista M3U: {e}")

if __name__ == "__main__":
    generar_agenda_m3u()
