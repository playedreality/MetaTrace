"""
Photo Metadata Investigator
Forensic EXIF analysis tool using ExifTool + Streamlit
Requirements: streamlit, folium, streamlit-folium, plotly, pandas, pillow, pyexiftool
Install: pip install streamlit folium streamlit-folium plotly pandas Pillow PyExifTool
Also requires ExifTool installed on your system: https://exiftool.org
"""

import streamlit as st
import subprocess
import json
import os
import tempfile
import pandas as pd
import folium
from streamlit_folium import st_folium
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from PIL import Image
import io
import re

# ── Page Config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Photo Metadata Investigator",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Rajdhani:wght@400;600;700&display=swap');

    /* Dark forensic theme */
    .stApp {
        background-color: #0a0c0f;
        color: #c8d8e8;
        font-family: 'Rajdhani', sans-serif;
    }

    .stApp > header { background-color: transparent; }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f1318;
        border-right: 1px solid #1e3a4a;
    }
    [data-testid="stSidebar"] * { color: #8ab4c8 !important; }

    /* Title */
    h1 {
        font-family: 'Share Tech Mono', monospace !important;
        color: #00d4ff !important;
        letter-spacing: 4px;
        text-transform: uppercase;
        font-size: 1.8rem !important;
        border-bottom: 1px solid #1e3a4a;
        padding-bottom: 0.5rem;
    }
    h2, h3 {
        font-family: 'Share Tech Mono', monospace !important;
        color: #00a8cc !important;
        letter-spacing: 2px;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: #0f1318;
        border: 1px solid #1e3a4a;
        border-radius: 4px;
        padding: 8px;
    }
    [data-testid="stMetricValue"] {
        color: #00d4ff !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    [data-testid="stMetricLabel"] { color: #6a8a9a !important; }

    /* Dataframe */
    .stDataFrame { border: 1px solid #1e3a4a; }

    /* Warning/alert boxes */
    .flag-box {
        background: #1a0a0a;
        border-left: 3px solid #ff4444;
        padding: 8px 12px;
        margin: 4px 0;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
        color: #ff8888;
    }
    .info-box {
        background: #0a1a0a;
        border-left: 3px solid #00cc44;
        padding: 8px 12px;
        margin: 4px 0;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.85rem;
        color: #88cc88;
    }
    .tag-chip {
        display: inline-block;
        background: #1e3a4a;
        color: #00d4ff;
        padding: 2px 8px;
        border-radius: 2px;
        font-family: 'Share Tech Mono', monospace;
        font-size: 0.75rem;
        margin: 2px;
    }

    /* Buttons */
    .stButton button {
        background: #0f1318 !important;
        color: #00d4ff !important;
        border: 1px solid #00d4ff !important;
        border-radius: 2px !important;
        font-family: 'Share Tech Mono', monospace !important;
        letter-spacing: 2px;
        text-transform: uppercase;
    }
    .stButton button:hover {
        background: #00d4ff !important;
        color: #0a0c0f !important;
    }

    /* File uploader */
    [data-testid="stFileUploader"] {
        border: 1px dashed #1e3a4a !important;
        background: #0f1318 !important;
        border-radius: 4px;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background: #0f1318 !important;
        color: #00a8cc !important;
        font-family: 'Share Tech Mono', monospace !important;
    }

    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        background: #0f1318;
        border-bottom: 1px solid #1e3a4a;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6a8a9a !important;
        font-family: 'Share Tech Mono', monospace !important;
    }
    .stTabs [aria-selected="true"] {
        color: #00d4ff !important;
        border-bottom: 2px solid #00d4ff !important;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: #0a0c0f; }
    ::-webkit-scrollbar-thumb { background: #1e3a4a; }
</style>
""", unsafe_allow_html=True)


# ── Helper Functions ────────────────────────────────────────────────────────────

def check_exiftool():
    """Verify ExifTool is installed."""
    try:
        result = subprocess.run(["exiftool", "-ver"], capture_output=True, text=True)
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        return False, None


def extract_metadata(file_paths):
    """Run ExifTool on a list of file paths and return parsed JSON."""
    cmd = ["exiftool", "-json", "-a", "-u", "-G1", "-c", "%.6f"] + file_paths
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        st.error(f"ExifTool error: {result.stderr}")
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def dms_to_decimal(dms_str, ref):
    """Convert DMS string to decimal degrees."""
    try:
        parts = re.split(r"[°'\"\s]+", dms_str.strip())
        parts = [p for p in parts if p]
        d = float(parts[0]) if len(parts) > 0 else 0
        m = float(parts[1]) if len(parts) > 1 else 0
        s = float(parts[2]) if len(parts) > 2 else 0
        decimal = d + m / 60 + s / 3600
        if ref in ("S", "W"):
            decimal = -decimal
        return decimal
    except Exception:
        return None


def parse_gps(record):
    """Extract lat/lon from an ExifTool record — checks all known key variants."""

    # 1. Search all keys for anything lat/lon related (catches any group prefix)
    lat_val = lon_val = lat_ref = lon_ref = None
    for k, v in record.items():
        kl = k.lower()
        if "gpslatitude" in kl and "ref" not in kl and lat_val is None:
            lat_val = v
        if "gpslongitude" in kl and "ref" not in kl and lon_val is None:
            lon_val = v
        if "gpslatituderef" in kl:
            lat_ref = str(v).strip()
        if "gpslongituderef" in kl:
            lon_ref = str(v).strip()

    if lat_val is None or lon_val is None:
        return None, None

    lat_ref = lat_ref or "N"
    lon_ref = lon_ref or "E"

    def to_float(val, ref):
        s = str(val).strip()
        # Normalize ref — handle full words like "North", "South", "East", "West"
        ref_upper = ref.upper()
        is_negative = ref_upper in ("S", "W", "SOUTH", "WEST")
        try:
            f = float(s)
            if is_negative and f > 0:
                f = -f
            return f
        except ValueError:
            pass
        # DMS string
        short_ref = "S" if "SOUTH" in ref_upper else ("W" if "WEST" in ref_upper else ref[0].upper())
        return dms_to_decimal(s, short_ref)

    lat_f = to_float(lat_val, lat_ref)
    lon_f = to_float(lon_val, lon_ref)
    return lat_f, lon_f


def parse_datetime(record):
    """Try multiple date fields and return a datetime object."""
    fields = [
        "ExifIFD:DateTimeOriginal",
        "EXIF:DateTimeOriginal",
        "Composite:SubSecDateTimeOriginal",
        "Composite:DateTimeOriginal",
        "ExifIFD:CreateDate",
        "EXIF:CreateDate",
        "IFD0:ModifyDate",
        "XMP:DateCreated",
        "System:FileModifyDate",
        "File:FileModifyDate",
    ]
    for f in fields:
        val = record.get(f)
        if val:
            for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y:%m:%d %H:%M:%S%z"):
                try:
                    return datetime.strptime(str(val)[:19], fmt[:len(str(val)[:19])])
                except ValueError:
                    continue
    return None


def detect_flags(record):
    """Return a list of investigative flags for a record."""
    flags = []
    orig = record.get("EXIF:DateTimeOriginal") or record.get("Composite:DateTimeOriginal")
    mod = record.get("File:FileModifyDate")
    if orig and mod:
        try:
            dt_orig = datetime.strptime(str(orig)[:19], "%Y:%m:%d %H:%M:%S")
            dt_mod = datetime.strptime(str(mod)[:19], "%Y:%m:%d %H:%M:%S")
            diff = abs((dt_mod - dt_orig).total_seconds())
            if diff > 86400:
                flags.append(f"⚠ Date mismatch: original vs file-modified differ by {int(diff//3600)}h")
        except Exception:
            pass

    software = record.get("EXIF:Software") or record.get("XMP:CreatorTool") or ""
    editing_apps = ["photoshop", "lightroom", "gimp", "affinity", "snapseed", "facetune",
                    "pixelmator", "acdsee", "darktable", "capture one", "rawtherapee"]
    if any(app in str(software).lower() for app in editing_apps):
        flags.append(f"⚠ Edited with: {software}")

    gps_lat, _ = parse_gps(record)
    if gps_lat is None:
        flags.append("ℹ No GPS data embedded")

    thumbnail = record.get("EXIF:ThumbnailLength")
    if thumbnail:
        flags.append("ℹ Embedded thumbnail present (may differ from main image)")

    serial = record.get("EXIF:SerialNumber") or record.get("EXIF:CameraSerialNumber")
    if serial:
        flags.append(f"ℹ Camera serial: {serial}")

    return flags


def build_summary_record(record, filename):
    """Flatten a record into a summary dict for the DataFrame."""
    lat, lon = parse_gps(record)
    dt = parse_datetime(record)
    return {
        "Filename": filename,
        "Date/Time": dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "Unknown",
        "_datetime_obj": dt,
        "Latitude": lat,
        "Longitude": lon,
        "Has GPS": lat is not None,
        "Make": record.get("EXIF:Make", ""),
        "Model": record.get("EXIF:CameraModelName") or record.get("EXIF:Model", ""),
        "Software": record.get("EXIF:Software") or record.get("XMP:CreatorTool", ""),
        "Dimensions": f"{record.get('EXIF:ImageWidth') or record.get('File:ImageWidth','')} x "
                      f"{record.get('EXIF:ImageHeight') or record.get('File:ImageHeight','')}",
        "Orientation": record.get("EXIF:Orientation", ""),
        "ISO": record.get("EXIF:ISO", ""),
        "Focal Length": record.get("EXIF:FocalLength", ""),
        "Exposure": record.get("EXIF:ExposureTime", ""),
        "Flash": record.get("EXIF:Flash", ""),
        "GPS Altitude": record.get("GPS:GPSAltitude") or record.get("Composite:GPSAltitude", ""),
        "GPS Direction": record.get("GPS:GPSImgDirection", ""),
        "File Size": record.get("File:FileSize", ""),
        "File Type": record.get("File:FileType", ""),
    }


def build_map(df_gps):
    """Build a Folium map from rows with GPS coordinates."""
    center_lat = df_gps["Latitude"].mean()
    center_lon = df_gps["Longitude"].mean()

    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=10,
        tiles="CartoDB dark_matter",
    )

    # Color by date order
    df_sorted = df_gps.dropna(subset=["_datetime_obj"]).sort_values("_datetime_obj")
    total = len(df_sorted)

    for i, (_, row) in enumerate(df_gps.iterrows()):
        color = "#00d4ff"
        if pd.notna(row.get("_datetime_obj")) and total > 1:
            idx = df_sorted.index.get_loc(row.name) if row.name in df_sorted.index else 0
            ratio = idx / max(total - 1, 1)
            r = int(255 * ratio)
            b = int(255 * (1 - ratio))
            color = f"#{r:02x}88{b:02x}"

        popup_html = f"""
        <div style="font-family:monospace;font-size:12px;min-width:200px">
            <b style="color:#00d4ff">{row['Filename']}</b><br>
            📅 {row['Date/Time']}<br>
            📍 {row['Latitude']:.6f}, {row['Longitude']:.6f}<br>
            📷 {row['Make']} {row['Model']}<br>
            💾 {row['File Size']}
        </div>
        """

        folium.CircleMarker(
            location=[row["Latitude"], row["Longitude"]],
            radius=8,
            color=color,
            fill=True,
            fill_color=color,
            fill_opacity=0.8,
            popup=folium.Popup(popup_html, max_width=280),
            tooltip=row["Filename"],
        ).add_to(m)

    # Draw path if sorted by time
    if len(df_sorted) > 1:
        points = [[r["Latitude"], r["Longitude"]] for _, r in df_sorted.iterrows()
                  if pd.notna(r["Latitude"])]
        if len(points) > 1:
            folium.PolyLine(points, color="#00d4ff", weight=1.5,
                            opacity=0.4, dash_array="5 5").add_to(m)

    return m


# ── Main App ───────────────────────────────────────────────────────────────────

st.title("🔍 Photo Metadata Investigator")
st.markdown('<p style="color:#6a8a9a;font-family:\'Share Tech Mono\',monospace;font-size:0.85rem;margin-top:-12px;">Forensic EXIF Analysis & Geolocation Tool</p>', unsafe_allow_html=True)

# ExifTool check
et_ok, et_ver = check_exiftool()
if not et_ok:
    st.error("⛔ ExifTool not found. Please install it from https://exiftool.org and ensure it's in your PATH.")
    st.stop()
else:
    st.sidebar.markdown(f'<span class="tag-chip">ExifTool v{et_ver}</span>', unsafe_allow_html=True)

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.markdown("## Upload Photos")
uploaded_files = st.sidebar.file_uploader(
    "Drop images here",
    type=["jpg", "jpeg", "png", "tiff", "tif", "heic", "heif", "cr2", "nef", "arw", "dng", "mp4", "mov"],
    accept_multiple_files=True,
    label_visibility="collapsed",
)

st.sidebar.markdown("---")
st.sidebar.markdown("## Filters")
show_no_gps = st.sidebar.checkbox("Show photos without GPS", value=True)
show_flags_only = st.sidebar.checkbox("Show flagged only", value=False)

st.sidebar.markdown("---")
st.sidebar.markdown("## Export")
export_csv = st.sidebar.button("📥 Export CSV")

# ── Process Files ──────────────────────────────────────────────────────────────
if not uploaded_files:
    st.markdown("""
    <div style="text-align:center;padding:60px 20px;color:#2a4a5a;font-family:'Share Tech Mono',monospace;">
        <div style="font-size:4rem;margin-bottom:16px">📂</div>
        <div style="font-size:1.1rem;letter-spacing:3px">UPLOAD PHOTOS TO BEGIN ANALYSIS</div>
        <div style="font-size:0.8rem;margin-top:8px;color:#1e3a4a">Supports JPEG · PNG · TIFF · HEIC · RAW · MP4 · MOV</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Save uploaded files to temp dir and run ExifTool
with tempfile.TemporaryDirectory() as tmpdir:
    file_paths = []
    file_data = {}
    for uf in uploaded_files:
        fpath = os.path.join(tmpdir, uf.name)
        with open(fpath, "wb") as f:
            f.write(uf.read())
        file_paths.append(fpath)
        file_data[uf.name] = uf

    with st.spinner("🔎 Extracting metadata..."):
        raw_records = extract_metadata(file_paths)

# Build summary DataFrame
all_records = []
all_flags = {}
raw_lookup = {}

for record in raw_records:
    src = record.get("SourceFile", "")
    fname = os.path.basename(src)
    summary = build_summary_record(record, fname)
    flags = detect_flags(record)
    all_records.append(summary)
    all_flags[fname] = flags
    raw_lookup[fname] = record

df = pd.DataFrame(all_records)

# Apply filters
df_view = df.copy()
if not show_no_gps:
    df_view = df_view[df_view["Has GPS"]]
if show_flags_only:
    df_view = df_view[df_view["Filename"].apply(lambda x: len(all_flags.get(x, [])) > 0)]

# ── Top Metrics ────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Photos", len(df))
col2.metric("With GPS", int(df["Has GPS"].sum()))
col3.metric("Unique Devices", df["Model"].nunique())
flagged = sum(1 for f in all_flags.values() if f)
col4.metric("Flagged", flagged)

st.markdown("---")

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_map, tab_timeline, tab_table, tab_detail, tab_flags = st.tabs([
    "🗺 Map", "📅 Timeline", "📋 Data Table", "🔬 Detail View", "⚠ Flags"
])

# MAP TAB
with tab_map:
    df_gps = df_view[df_view["Has GPS"] & df_view["Latitude"].notna()].copy()
    if df_gps.empty:
        st.info("No GPS data found in the uploaded photos.")
    else:
        st.markdown(f"*Showing {len(df_gps)} geotagged photo(s). Blue→Red path follows chronological order.*")
        m = build_map(df_gps)
        st_folium(m, use_container_width=True, height=520)

# TIMELINE TAB
with tab_timeline:
    df_time = df_view[df_view["_datetime_obj"].notna()].copy()
    if df_time.empty:
        st.info("No parseable date/time data found.")
    else:
        df_time["_dt"] = pd.to_datetime(df_time["_datetime_obj"])
        df_time_sorted = df_time.sort_values("_dt")

        fig = px.scatter(
            df_time_sorted,
            x="_dt",
            y="Filename",
            color="Has GPS",
            hover_data=["Make", "Model", "Software", "Date/Time"],
            color_discrete_map={True: "#00d4ff", False: "#ff6644"},
            template="plotly_dark",
            title="Photo Timeline",
        )
        fig.update_layout(
            paper_bgcolor="#0a0c0f",
            plot_bgcolor="#0f1318",
            font_family="Share Tech Mono",
            title_font_color="#00d4ff",
            xaxis_title="Date / Time",
            yaxis_title="",
            showlegend=True,
            legend_title_text="Has GPS",
            margin=dict(l=20, r=20, t=40, b=20),
        )
        fig.update_traces(marker=dict(size=12, symbol="diamond"))
        st.plotly_chart(fig, use_container_width=True)

        # Hourly distribution
        df_time["Hour"] = df_time["_dt"].dt.hour
        hour_counts = df_time["Hour"].value_counts().sort_index().reset_index()
        hour_counts.columns = ["Hour", "Count"]
        fig2 = px.bar(
            hour_counts, x="Hour", y="Count",
            template="plotly_dark",
            title="Photos by Hour of Day",
            color="Count",
            color_continuous_scale=[[0, "#1e3a4a"], [1, "#00d4ff"]],
        )
        fig2.update_layout(
            paper_bgcolor="#0a0c0f",
            plot_bgcolor="#0f1318",
            font_family="Share Tech Mono",
            title_font_color="#00d4ff",
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)

# DATA TABLE TAB
with tab_table:
    display_cols = ["Filename", "Date/Time", "Has GPS", "Latitude", "Longitude",
                    "Make", "Model", "Software", "Dimensions", "File Size", "File Type"]
    st.dataframe(
        df_view[display_cols],
        use_container_width=True,
        hide_index=True,
        height=460,
    )
    if export_csv:
        csv = df_view[display_cols].to_csv(index=False)
        st.download_button("Download CSV", csv, "metadata_export.csv", "text/csv")

# DETAIL VIEW TAB
with tab_detail:
    selected = st.selectbox("Select a photo", df_view["Filename"].tolist())
    if selected:
        col_img, col_meta = st.columns([1, 2])
        with col_img:
            if selected in file_data:
                try:
                    file_data[selected].seek(0)
                    img = Image.open(file_data[selected])
                    img.thumbnail((400, 400))
                    st.image(img, use_container_width=True)
                except Exception:
                    st.markdown("*(Preview unavailable)*")

        with col_meta:
            raw = raw_lookup.get(selected, {})
            gps_keys = {k: v for k, v in raw.items() if "gps" in k.lower()}
            if gps_keys:
                with st.expander("📡 GPS Fields Found", expanded=True):
                    for k, v in gps_keys.items():
                        st.markdown(f'<div class="info-box"><b>{k}</b>: {v}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="flag-box">⚠ No GPS fields detected in this photo\'s metadata</div>', unsafe_allow_html=True)
            st.markdown("**All Metadata Fields**")
            meta_rows = []
            for k, v in sorted(raw.items()):
                if k != "SourceFile":
                    meta_rows.append({"Field": k, "Value": str(v)})
            st.dataframe(pd.DataFrame(meta_rows), use_container_width=True, hide_index=True, height=360)

# FLAGS TAB
with tab_flags:
    st.markdown("*Investigative flags are automatically detected based on metadata anomalies.*")
    any_flags = False
    for fname, flags in sorted(all_flags.items()):
        if fname not in df_view["Filename"].values:
            continue
        row = df_view[df_view["Filename"] == fname].iloc[0] if not df_view[df_view["Filename"] == fname].empty else None
        if flags or not show_flags_only:
            with st.expander(f"{'🔴' if any(f.startswith('⚠') for f in flags) else '🔵'} {fname}", expanded=bool(flags)):
                if flags:
                    any_flags = True
                    for flag in flags:
                        if flag.startswith("⚠"):
                            st.markdown(f'<div class="flag-box">{flag}</div>', unsafe_allow_html=True)
                        else:
                            st.markdown(f'<div class="info-box">{flag}</div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="info-box">✓ No anomalies detected</div>', unsafe_allow_html=True)

    if not any_flags and show_flags_only:
        st.info("No flagged photos found.")
