LiRoS Project Roadmap: The Journey to Global Sunshine
Phase 1: Interactive Foundation (COMPLETED)
Core Mapping: Established a high-performance Leaflet.js map with CartoDB Voyager tiles.

Regional Intelligence: Implemented a dual-layer news retrieval system (Specific Country -> Continent Fallback -> Global Default).

Dynamic Geocoding: Integrated Nominatim Reverse Geocoding to identify regions from coordinates.

Brand Identity: Developed the "Sunshine" UI with a warm color palette, custom animations, and a responsive sidebar.

Phase 2: The "Daily Refresh" Engine (IN PROGRESS)
Backend Integration: Transition from the current static newsByRegion object to a modern full-stack backend.

Automated Aggregation: Implement a Node.js cron job to scrape or fetch positive news from verified APIs daily.

AI Content Pipeline: Use LLMs to summarize long-form articles into the standardized LiRoS format (Emoji, Headline, Impact, Date).

Database Migration: Store stories in a PostgreSQL database using Prisma to allow for historical filtering.

Phase 3: Community & Interaction (PLANNED)
"Share Your Sunshine": Create a submission portal for users to pin their own local positive stories to the map.

Social Amplification: Add one-click "Spread the Joy" buttons to share specific news cards to social media.

Positivity Heatmap: Visualize "Sunshine Density" on the map based on the volume of good news in specific regions.

Mobile App: Package the web experience for iOS and Android to replace "Doom-scrolling" with "Sun-scrolling."

Phase 4: Scaling & Impact
Multilingual Support: Auto-translate news stories to allow global users to read sunshine in their native language.

Impact Verification: Partner with NGOs to link news stories to direct donation or volunteer opportunities.