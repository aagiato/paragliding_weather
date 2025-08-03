"""
Colorado Paragliding Site Finder (Optimized with SSL Fallback)

A desktop GUI tool to assess paragliding suitability at Colorado launch sites.
Uses Open-Meteo API with connection reuse, parallel requests, and HTTP fallback if SSL is unavailable.
"""
import tkinter as tk
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.exceptions import SSLError

# =============================================================================
# Configuration
# =============================================================================
SITES = [
    {"name": "Boulder Flying Park", "lat": 40.0500, "lon": -105.2800},
    {"name": "Junction Butte", "lat": 40.0200, "lon": -105.3500},
    {"name": "Lookout Mountain (Golden)", "lat": 39.7556, "lon": -105.2211},
    {"name": "Mt. Falcon (Morrison)", "lat": 39.6659, "lon": -105.2369},
    {"name": "Bear Peak (Boulder)", "lat": 39.9990, "lon": -105.2819},
    {"name": "Echo Mountain (Idaho Springs)", "lat": 39.7380, "lon": -105.5770},
    {"name": "Loveland Pass", "lat": 39.7136, "lon": -105.6650},
    {"name": "Kenosha Pass", "lat": 39.4250, "lon": -106.2190},
    {"name": "Bellyache Mountain (Eagle County)", "lat": 39.8000, "lon": -106.9000},
    {"name": "Pikes Peak", "lat": 38.8409, "lon": -105.0447},
    {"name": "Mt. Evans", "lat": 39.5883, "lon": -105.6438},
    {"name": "Longs Peak", "lat": 40.2549, "lon": -105.6160},
]

ACCEPTABLE_WEATHER_CODES = {0, 1, 2, 3}
_WEATHER_MAP = {
    0: "Clear", 1: "Clouds", 2: "Clouds", 3: "Clouds",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Rain",
    66: "Freezing Rain", 67: "Freezing Rain",
    71: "Snow Fall", 73: "Snow Fall", 75: "Snow Fall",
    77: "Snow Grains",
    80: "Rain Showers", 81: "Rain Showers", 82: "Rain Showers",
    85: "Snow Showers", 86: "Snow Showers",
    95: "Thunderstorm", 96: "Thunderstorm with Hail", 99: "Thunderstorm with Hail",
}
_DIRECTIONS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]

# Base URLs for HTTPS and HTTP fallback
BASE_URL_HTTPS = "https://api.open-meteo.com/v1/forecast"
BASE_URL_HTTP = "http://api.open-meteo.com/v1/forecast"
DEFAULT_PARAMS = {
    "current_weather": "true",
    "daily": "temperature_2m_max,precipitation_probability_max,windspeed_10m_max,"
             "winddirection_10m_dominant,weathercode",
    "timezone": "auto",
    "temperature_unit": "fahrenheit",
    "windspeed_unit": "mph",
}

# =============================================================================
# Utility Functions
# =============================================================================

def map_weather_code(code: int) -> str:
    return _WEATHER_MAP.get(code, "Unknown")


def degrees_to_cardinal(deg: float) -> str:
    ix = int((deg + 22.5) / 45) % 8
    return _DIRECTIONS[ix]

# =============================================================================
# Weather Fetch & Evaluation
# =============================================================================

def check_site(session: requests.Session, site: dict) -> dict:
    """
    Fetch weather data for a site and evaluate today's and tomorrow's fly suitability.
    Falls back to HTTP if SSL is unavailable.
    """
    params = DEFAULT_PARAMS.copy()
    params.update({"latitude": site["lat"], "longitude": site["lon"]})
    
    try:
        response = session.get(BASE_URL_HTTPS, params=params, timeout=10)
    except SSLError:
        response = session.get(BASE_URL_HTTP, params=params, timeout=10)

    response.raise_for_status()
    data = response.json()

    def eval_conditions(speed: float, code: int, pop: float = None) -> (bool, list):
        reasons = []
        if speed < 5:
            reasons.append("Wind too calm")
        elif speed > 20:
            reasons.append("Wind too strong")
        if code not in ACCEPTABLE_WEATHER_CODES:
            reasons.append(f"Weather not ideal: {map_weather_code(code)}")
        if pop is not None and pop > 10:
            reasons.append("Precipitation too high")
        return (len(reasons) == 0, reasons)

    cur = data.get("current_weather", {})
    cur_ok, cur_reasons = eval_conditions(cur.get("windspeed", 0), cur.get("weathercode", 0))
    current = {
        "temp": cur.get("temperature"),
        "wind": f"{cur.get('windspeed',0)} mph ({degrees_to_cardinal(cur.get('winddirection',0))})",
        "weather": map_weather_code(cur.get("weathercode", 0)),
        "ok": cur_ok,
        "reasons": cur_reasons,
    }

    dly = data.get("daily", {})
    idx = 1 if len(dly.get("time", [])) > 1 else 0
    tom_speed = dly.get("windspeed_10m_max", [0])[idx]
    tom_code = dly.get("weathercode", [0])[idx]
    tom_pop = dly.get("precipitation_probability_max", [0])[idx]
    tom_wind_dir = dly.get("winddirection_10m_dominant", [0])[idx]
    tom_ok, tom_reasons = eval_conditions(tom_speed, tom_code, tom_pop)
    forecast = {
        "temp": dly.get("temperature_2m_max", [0])[idx],
        "wind": f"{tom_speed} mph ({degrees_to_cardinal(tom_wind_dir)})",
        "weather": map_weather_code(tom_code),
        "pop": tom_pop,
        "ok": tom_ok,
        "reasons": tom_reasons,
    }

    return {"name": site["name"], "current": current, "forecast": forecast}

# =============================================================================
# GUI Functions
# =============================================================================

def refresh_sites():
    results_text.delete("1.0", tk.END)
    results_text.insert(tk.END, "Fetching weather data for candidate sites...\n\n")

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(check_site, session, s): s for s in SITES}
        for future in as_completed(futures):
            site = futures[future]
            try:
                data = future.result()
                lines = [
                    f"{data['name']}:",
                    (f"  Today: Temp {data['current']['temp']}°F, Wind {data['current']['wind']}, "
                     f"Weather {data['current']['weather']}, Status {'✔' if data['current']['ok'] else '✘'}")
                ]
                if data['current']['reasons']:
                    lines.append(f"    Reasons: {', '.join(data['current']['reasons'])}")
                lines.append(
                    (f"  Tomorrow: Temp {data['forecast']['temp']}°F, Wind {data['forecast']['wind']}, "
                     f"Weather {data['forecast']['weather']}, Precip {data['forecast']['pop']}%, "
                     f"Status {'✔' if data['forecast']['ok'] else '✘'}")
                )
                if data['forecast']['reasons']:
                    lines.append(f"    Reasons: {', '.join(data['forecast']['reasons'])}")
                results_text.insert(tk.END, "\n".join(lines) + "\n\n")
            except Exception as err:
                results_text.insert(tk.END, f"{site['name']}: Error: {err}\n\n")
    results_text.insert(tk.END, "Done.\n")

# =============================================================================
# App Initialization
# =============================================================================

if __name__ == "__main__":
    session = requests.Session()
    root = tk.Tk()
    root.title("Colorado Paragliding Site Finder")

    frame = tk.Frame(root, padx=10, pady=10)
    frame.pack(fill=tk.BOTH, expand=True)

    # Top disclaimer in red bold
    disclaimer_text = (
        "Disclaimer: This tool is for informational purposes only and should NEVER replace your own judgment, formal training, or official weather briefings. Always exercise caution and use certified sources before flying."
    )
    disclaimer_label = tk.Label(
        frame,
        text=disclaimer_text,
        fg="red",
        font=("Helvetica", 10, "bold"),
        wraplength=800,
        justify="left"
    )
    disclaimer_label.pack(pady=(0, 10))

    # Refresh button
    refresh_btn = tk.Button(frame, text="Refresh Sites", command=refresh_sites)
    refresh_btn.pack(pady=(0, 10))

    # Results display
    results_text = tk.Text(frame, width=90, height=30, wrap=tk.WORD)
    results_text.pack(fill=tk.BOTH, expand=True)

    scrollbar = tk.Scrollbar(frame, command=results_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    results_text.config(yscrollcommand=scrollbar.set)

    root.mainloop()
