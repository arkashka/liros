# LiRoS (Little Ray of Sunshine) - Project Memory

## Project Context
LiRoS is a "Radical Positivity" web platform that allows users to explore uplifting global news via an interactive map. It counters "doom-scrolling" by visualizing good news geographically, using a daily-refresh logic to keep content timely and inspiring.

## Reference Index
Use these files for deep-dive context on specific project domains:
- **@STYLE_GUIDE.md**: Refer to this for exact hex codes, typography weights, and CSS animation keyframes to maintain the "Sunshine" aesthetic.
- **@ROADMAP.md**: Refer to this to see current progress (Phase 1) and the transition plan for Phase 2 (Backend/API integration).
- **@DATA_SCHEMA.md**: Refer to this for the required structure of "Sunshine Story" objects and the geographic fallback hierarchy.
- **@SYSTEM_PROMPTS.md**: Refer to this for the "Ray of Sunshine" editorial voice and instructions for summarizing news articles.

## Tech Stack & Architecture
- **Frontend:** HTML5, CSS3 (Flexbox/Grid), Vanilla JavaScript.
- **Mapping:** Leaflet.js with CartoDB Voyager tiles.
- **Geocoding:** Nominatim (OpenStreetMap) Reverse Geocoding API.
- **Data Structure:** - `newsByRegion`: ISO-3166 country-coded news objects (including source and url fields).
    - `continentStories`: Fallback news for maritime or non-specific land clicks.
- **UI Components:**
    - Interactive Map with Ripple effect.
    - Dynamic Sidebar (News Panel) with typewriter animation effects.
    - Responsive Header with "Hint Pill" for UX guidance.

## Core Development Standards
- **Visual Identity:** - Palette: `--sun` (#FFD166), `--coral` (#FF6B6B), `--mint` (#06D6A0), `--cream` (#FFFBF0).
    - Typography: 'Nunito', sans-serif (weights 400-900).
- **Code Patterns:**
    - **Vanilla First:** Use native DOM APIs and `fetch` (avoid heavy frameworks for the MVP).
    - **Animation:** Use CSS keyframes (`card-in`, `ripple`, `pulse-hint`) for high-performance motion.
    - **State Management:** Track `currentMarker` and `typingTimers` to prevent memory leaks or overlapping typewriter effects.
- **API Etiquette:** Include `User-Agent` headers (e.g., `LiRoS-HappyNews/1.0`) when calling Nominatim to comply with usage policies.

## Key Logic & Commands
- **Map Interaction:** Clicks trigger a ripple, a `circleMarker`, and a two-stage panel update (Immediate Continent Fallback -> Async Reverse Geocode).
- **News Logic:** `showPanel()` handles the transition from a loading spinner to shuffled news cards.
- **Typewriter Effect:** `typewriter(el, text, startDelay, speed)` uses recursive timeouts with `typingTimers` tracking for cleanup.

## Current Roadmap (@TODO.md)
- [x] Functional Map with Leaflet.js
- [x] Basic News Data & fallbacks
- [x] Reverse Geocoding for country/state detection
- [ ] Connect to real news API/Backend (Daily Refresh logic)
- [ ] Implement user submission form for "Sharing Sunshine"
- [ ] Mobile-responsive layout for the News Panel

## AI Instructions
- When suggesting UI changes, maintain the "Warm & Round" aesthetic (border-radius: 14px-22px).
- If adding news sources, ensure data objects include: `emoji`, `headline`, `body`, `impact`, `date`, `source`, and `url`.
- Always clear `typingTimers` before initiating new panel content to prevent text jumble.