# LIROS DATA STRATEGY AND SCHEMAS

1. THE SUNSHINE STORY OBJECT
Every news item must follow this structure to ensure the UI renders correctly.

FIELD: emoji
TYPE: A single Unicode emoji
EXAMPLE: green_heart

FIELD: headline
TYPE: A title under 60 characters
EXAMPLE: Local Forest Growth Hits 10-Year High

FIELD: body
TYPE: 2 to 3 sentences of context
EXAMPLE: Community efforts in the region have successfully restored 500 acres of native woodland.

FIELD: impact
TYPE: A short stat used in the impact chip
EXAMPLE: 500 Acres Restored

FIELD: date
TYPE: Month and Year
EXAMPLE: April 2026

FIELD: source
TYPE: String (Publisher name)
EXAMPLE: The Guardian

FIELD: url
TYPE: String (Full article link)
EXAMPLE: https://www.theguardian.com/environment/positive-news

FIELD: region_code
TYPE: ISO 3166-1 alpha-2 country code
EXAMPLE: US

2. GEOGRAPHIC HIERARCHY
The system resolves location in three stages.

STAGE 1: Primary matches the exact country code returned by the Nominatim API.
STAGE 2: Secondary uses continentStories if the country has no stories or the click is in water.
STAGE 3: Tertiary uses global default stories for cleanup or health milestones.

3. DATABASE ARCHITECTURE
Proposed model for the full web stack.

STORY MODEL:
id: Unique Identifier
createdAt: Date added
emoji: String icon
headline: String title
body: Text description
impact: String stat
displayDate: String date
countryCode: String 2-letter code
continent: String name
source: String
url: String
isApproved: Boolean status

4. API RESPONSE FORMAT
The backend should return an array of up to 5 stories per coordinate. These should be shuffled to ensure the user sees different content on subsequent clicks.
