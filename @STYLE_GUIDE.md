LiRoS Visual & Style Identity
1. Core Color Palette

These variables are the foundation of the "Little Ray of Sunshine" brand.

Sun (--sun): #FFD166 — Used for primary highlights, branding, and the first news card border.
Coral (--coral): #FF6B6B — Used for the map pin, active typing cursors, and the second news card border.
Mint (--mint): #06D6A0 — Used for "Impact" badges and the third news card border.
Sky (--sky): #118AB2 — Used for the fourth news card border and secondary accents.
Plum (--plum): #9B5DE5 — Used for the fifth news card border and AI-related gradients.
Cream (--cream): #FFFBF0 — The primary background color for the body and side panels.
Warm Gray (--warm-gray): #6B5E52 — Used for secondary text and taglines.

2. Typography

Font Family: 'Nunito', sans-serif.
Weights: Use 900 for branding/headers, 800 for headlines, and 600/700 for body text.
Logo Text: Uses a 135-degree linear gradient moving from Coral to Sun to Mint.

3. Component Standards

News Cards: Must have a 5px solid left border using one of the brand colors, a 14px border-radius, and a soft 0 2px 14px rgba(0,0,0,0.05) box shadow.
Pills/Chips: All interactive pills (like the hint-pill or stat-chip) should have a 20px or 10px border-radius and a light background with a darker border.
Transitions: Side panels and map shifts should use a consistent 0.38s duration with a cubic-bezier(0.4, 0, 0.2, 1) timing function.
Source Attribution: Links to the original article should be placed at the bottom-right of the news card. Use --warm-gray for the text color, a font-size of 12px, and a weight of 700. The link should be labeled "Read the full story" or display the source name with an external link icon.

4. Animation Principles

Entrance: Use the card-in keyframes (opacity 0 to 1, translate 18px to 0) for all new content appearing in the sidebar.
Feedback: Map clicks must trigger the map-ripple animation (expanding from 16px to 130px with fading opacity).
Attention: Use the pulse-hint scale animation to draw the user's eye to call-to-action elements like the "Hint Pill".
