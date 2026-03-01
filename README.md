# MetaTrace
A forensic photo analysis tool that extracts EXIF metadata from images and maps GPS coordinates chronologically.

## Features
- Interactive map with chronological movement path (blue → red)
- Timeline visualization by date and hour
- Full metadata table with CSV export
- Auto-detection of anomalies and tampering flags
- Supports JPEG, PNG, TIFF, HEIC, RAW, MP4, MOV

## Important — Preserving Location Metadata
GPS and other metadata can be silently stripped depending on how photos are transferred or saved. To ensure location data is preserved:

- **Always transfer photos as original/unmodified files.** Use a USB cable, SD card reader, or direct file transfer rather than relying on photo apps to export them.
- **Avoid transferring via messaging apps or social media** (iMessage, WhatsApp, Telegram, Instagram, etc.) — these platforms strip GPS and other metadata before sending.
- **Do not use screenshots** of photos — screenshots contain no original metadata.
- **Avoid downloading photos from social media or email** as these sources almost always strip metadata before upload.
- For best results, work directly with the original files from the device's storage or a forensic extraction.
- Once you have the original files, save them to a dedicated folder before uploading to MetaTrace.

If a photo you know has location data isn't showing a pin on the map, it was likely transferred in a way that stripped the GPS metadata beforehand.

## Requirements
- Python 3
- ExifTool — https://exiftool.org
  - Mac: `brew install exiftool`
  - Windows: Download from exiftool.org and add to PATH
  - Linux: `sudo apt install libimage-exiftool-perl`

## Install Dependencies
```bash
pip install streamlit folium streamlit-folium plotly pandas Pillow PyExifTool
```

## Run
```bash
streamlit run photo_investigator.py
```
Then open http://localhost:8501 in your browser.

## Built With
- Python
- ExifTool
- Streamlit
- Folium
- Plotly
