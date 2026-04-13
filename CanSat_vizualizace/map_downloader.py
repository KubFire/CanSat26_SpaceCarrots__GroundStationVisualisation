import os
import requests
import mercantile
from pathlib import Path

# --- CONFIGURATION ---
# Coordinates we've been using (Moravská Třebová area)
LAT_MIN, LAT_MAX = 49.78, 49.82
LON_MIN, LON_MAX = 16.67, 16.72
ZOOM_LEVELS = [14, 15, 16] # Higher zoom = more detail = more files

download_dir = Path(os.path.expanduser("~/Downloads/CanSat_Tiles"))

def download_tiles():
    print(f"Starting download to {download_dir}...")
    for zoom in ZOOM_LEVELS:
        # Get list of tiles for this area
        tiles = list(mercantile.tiles(LON_MIN, LAT_MIN, LON_MAX, LAT_MAX, [zoom]))
        
        for t in tiles:
            # Create directory structure: z/x/y.png
            tile_dir = download_dir / str(t.z) / str(t.x)
            tile_dir.mkdir(parents=True, exist_ok=True)
            
            tile_path = tile_dir / f"{t.y}.png"
            if tile_path.exists(): continue # Skip already downloaded
            
            # OpenStreetMap URL
            url = f"https://tile.openstreetmap.org/{t.z}/{t.x}/{t.y}.png"
            
            try:
                # User-Agent is required by OSM to prevent 403 errors
                response = requests.get(url, headers={'User-Agent': 'CanSatGroundStation/1.0'})
                if response.status_code == 200:
                    with open(tile_path, "wb") as f:
                        f.write(response.content)
                    print(f"Downloaded: {t.z}/{t.x}/{t.y}")
                else:
                    print(f"Error {response.status_code} for tile {t}")
            except Exception as e:
                print(f"Failed {t}: {e}")

if __name__ == "__main__":
    download_tiles()
    print("Done! You can now point your GroundStation to this folder.")