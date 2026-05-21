"""
Coletti OS — Geospatial Analysis Engine
Extracts US city/state location signals from transaction descriptions
and builds interactive Folium maps for court presentation.
"""

import re

import pandas as pd

try:
    import folium
    FOLIUM_AVAILABLE = True
except ImportError:
    FOLIUM_AVAILABLE = False

try:
    from geopy.geocoders import Nominatim
    from geopy.exc import GeocoderTimedOut
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False


# ── State reference data ──────────────────────────────────────────────────────

US_STATES = {
    'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas',
    'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware',
    'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho',
    'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas',
    'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland',
    'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi',
    'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada',
    'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York',
    'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma',
    'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina',
    'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah',
    'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia',
    'WI': 'Wisconsin', 'WY': 'Wyoming', 'DC': 'District of Columbia',
}

# Reverse map: full name → abbreviation
STATE_NAME_TO_ABBR = {v.lower(): k for k, v in US_STATES.items()}

# Approximate state centroids for mapping (lat, lon)
STATE_CENTROIDS = {
    'AL': (32.806671, -86.791130), 'AK': (61.370716, -152.404419),
    'AZ': (33.729759, -111.431221), 'AR': (34.969704, -92.373123),
    'CA': (36.116203, -119.681564), 'CO': (39.059811, -105.311104),
    'CT': (41.597782, -72.755371), 'DE': (39.318523, -75.507141),
    'FL': (27.766279, -81.686783), 'GA': (33.040619, -83.643074),
    'HI': (21.094318, -157.498337), 'ID': (44.240459, -114.478828),
    'IL': (40.349457, -88.986137), 'IN': (39.849426, -86.258278),
    'IA': (42.011539, -93.210526), 'KS': (38.526600, -96.726486),
    'KY': (37.668140, -84.670067), 'LA': (31.169960, -91.867805),
    'ME': (44.693947, -69.381927), 'MD': (39.063946, -76.802101),
    'MA': (42.230171, -71.530106), 'MI': (43.326618, -84.536095),
    'MN': (45.694454, -93.900192), 'MS': (32.741646, -89.678696),
    'MO': (38.456085, -92.288368), 'MT': (46.921925, -110.454353),
    'NE': (41.125370, -98.268082), 'NV': (38.313515, -117.055374),
    'NH': (43.452492, -71.563896), 'NJ': (40.298904, -74.521011),
    'NM': (34.840515, -106.248482), 'NY': (42.165726, -74.948051),
    'NC': (35.630066, -79.806419), 'ND': (47.528912, -99.784012),
    'OH': (40.388783, -82.764915), 'OK': (35.565342, -96.928917),
    'OR': (44.572021, -122.070938), 'PA': (40.590752, -77.209755),
    'RI': (41.680893, -71.511780), 'SC': (33.856892, -80.945007),
    'SD': (44.299782, -99.438828), 'TN': (35.747845, -86.692345),
    'TX': (31.054487, -97.563461), 'UT': (40.150032, -111.862434),
    'VT': (44.045876, -72.710686), 'VA': (37.769337, -78.169968),
    'WA': (47.400902, -121.490494), 'WV': (38.491226, -80.954453),
    'WI': (44.268543, -89.616508), 'WY': (42.755966, -107.302490),
    'DC': (38.897438, -77.026817),
}

# Entity color map for map markers
ENTITY_COLORS = {
    'Robert':     'red',
    'Petitioner': 'blue',
    None:         'gray',
}


def extract_location(description: str) -> dict | None:
    """
    Extract US state (and optionally city) from a transaction description.
    Returns {'state_abbr': 'TN', 'state_name': 'Tennessee', 'city': 'Nashville'} or None.
    """
    if not description:
        return None

    text = str(description)

    # Pattern: "CITY ST" at end of POS description (e.g. "WALMART NASHVILLE TN")
    pos_pattern = r'\b([A-Z][A-Za-z\s]+?)\s+(' + '|'.join(US_STATES.keys()) + r')\b'
    m = re.search(pos_pattern, text)
    if m:
        city = m.group(1).strip().title()
        abbr = m.group(2).upper()
        return {'state_abbr': abbr, 'state_name': US_STATES[abbr], 'city': city}

    # Pattern: full state name in description
    text_lower = text.lower()
    for name, abbr in STATE_NAME_TO_ABBR.items():
        if name in text_lower:
            return {'state_abbr': abbr, 'state_name': US_STATES[abbr], 'city': None}

    # Pattern: bare state abbreviation (2 caps, word boundary)
    abbr_pattern = r'\b(' + '|'.join(US_STATES.keys()) + r')\b'
    m = re.search(abbr_pattern, text)
    if m:
        abbr = m.group(1)
        return {'state_abbr': abbr, 'state_name': US_STATES[abbr], 'city': None}

    return None


def tag_locations(df: pd.DataFrame) -> pd.DataFrame:
    """Add Location_State, Location_City columns to a transaction DataFrame."""
    df = df.copy()
    locations = df['Description'].apply(extract_location)
    df['Location_State'] = locations.apply(lambda x: x['state_abbr'] if x else None)
    df['Location_City']  = locations.apply(lambda x: x.get('city') if x else None)
    return df


def build_transaction_map(df: pd.DataFrame, entity_config: dict = None,
                          tour_route: list = None) -> str:
    """
    Build an interactive Folium map of transaction locations.
    Returns HTML string for embedding in Streamlit via st.components.v1.html().

    tour_route: optional list of state abbreviations representing the known tour schedule.
    """
    if not FOLIUM_AVAILABLE:
        return "<p>folium not installed. Run: pip install folium streamlit-folium</p>"

    df = tag_locations(df)
    has_locations = df['Location_State'].notna().any()

    # Center map on continental US
    m = folium.Map(location=[39.5, -98.35], zoom_start=4,
                   tiles='CartoDB positron')

    # Tour route highlight layer
    if tour_route:
        for abbr in tour_route:
            if abbr in STATE_CENTROIDS:
                lat, lon = STATE_CENTROIDS[abbr]
                folium.Circle(
                    location=[lat, lon],
                    radius=150000,
                    color='orange', fill=True, fill_opacity=0.15,
                    tooltip=f"Tour Route: {US_STATES.get(abbr, abbr)}",
                ).add_to(m)

    # Transaction markers
    for _, row in df.iterrows():
        if pd.isna(row.get('Location_State')):
            continue
        abbr = row['Location_State']
        if abbr not in STATE_CENTROIDS:
            continue
        lat, lon = STATE_CENTROIDS[abbr]

        # Jitter so stacked markers are visible
        import random
        lat += random.uniform(-0.8, 0.8)
        lon += random.uniform(-0.8, 0.8)

        entity = row.get('Entity')
        color = ENTITY_COLORS.get(entity, 'gray')
        amount_str = f"${row['Amount']:,.2f}" if pd.notna(row.get('Amount')) else "Amt Unknown"
        city = row.get('Location_City') or abbr

        popup_html = f"""
        <b>{row['Description'][:60]}</b><br>
        <b>Amount:</b> {amount_str}<br>
        <b>Date:</b> {row['Date']}<br>
        <b>Location:</b> {city}, {US_STATES.get(abbr, abbr)}<br>
        <b>Entity:</b> {entity or 'Unattributed'}<br>
        <b>Method:</b> {row.get('Entity_Method') or '—'}
        """

        folium.CircleMarker(
            location=[lat, lon],
            radius=max(6, min(18, (row.get('Amount', 0) or 0) / 300)),
            color=color, fill=True, fill_color=color, fill_opacity=0.75,
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=f"{city} · {amount_str} · {entity or 'Unknown'}",
        ).add_to(m)

    # Legend
    legend_html = """
    <div style="position:fixed;bottom:30px;left:30px;z-index:1000;background:white;
                padding:12px;border-radius:8px;border:1px solid #ccc;font-size:13px;">
        <b>Entity Legend</b><br>
        <span style="color:red">●</span> Robert &nbsp;
        <span style="color:blue">●</span> Petitioner &nbsp;
        <span style="color:gray">●</span> Unattributed<br>
        <span style="color:orange">◯</span> Tour Route States<br>
        <i>Marker size ∝ transaction amount</i>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    if not has_locations:
        no_data_html = """
        <div style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);
                    background:rgba(0,0,0,0.7);color:white;padding:20px;border-radius:8px;
                    font-size:14px;z-index:9999;text-align:center;">
            No location data found in transaction descriptions.<br>
            POS descriptions like "WALMART NASHVILLE TN" are needed.
        </div>
        """
        m.get_root().html.add_child(folium.Element(no_data_html))

    return m._repr_html_()
