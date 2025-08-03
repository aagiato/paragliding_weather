# Colorado Paragliding Site Finder

A desktop GUI tool to assess paragliding suitability at popular Colorado launch sites.  
It fetches both current conditions and next-day forecasts from the free Open-Meteo API, then applies simple “fly / no-fly” rules.

---

## Features

- **Predefined Sites**  
  12 well-known take-off points (e.g. Boulder Flying Park, Pikes Peak, Lookout Mountain).

- **Current & Forecast**  
  - **Current**: temperature, wind speed & direction, weather code  
  - **Tomorrow**: max temperature, max wind, precipitation probability

- **Suitability Rules**  
  - Wind between **5–20 mph**  
  - Weather codes **0–3** (clear or cloudy)  
  - Precipitation probability ≤ 10% (forecast only)

- **Responsive GUI**  
  - Parallel API calls so the UI never locks up  
  - ✔/✘ status indicators with concise reasons  
  - Single “Refresh Sites” button to re-evaluate all locations

- **SSL Fallback**  
  Automatically retries over plain HTTP if HTTPS fails (for environments without SSL support).

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/paragliding-site-finder.git
   cd paragliding-site-finder
