#!/usr/bin/env python3
"""Generate simple placeholder PNG logos for energy platforms.
No external dependencies — uses only stdlib (zlib)."""
import zlib
import struct
import os

def create_png(width: int, height: int, bg_color: tuple, text: str) -> bytes:
    """Create a minimal PNG with colored background and white letter."""
    # Create raw pixel data (RGBA)
    raw = b''
    for y in range(height):
        raw += b'\x00'  # filter byte
        for x in range(width):
            raw += struct.pack('BBBB', *bg_color, 255)

    # Compress with zlib
    compressed = zlib.compress(raw)

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    ihdr = make_chunk(b'IHDR', ihdr_data)

    # IDAT chunk
    idat = make_chunk(b'IDAT', compressed)

    # IEND chunk
    iend = make_chunk(b'IEND', b'')

    return sig + ihdr + idat + iend

def make_chunk(chunk_type: bytes, data: bytes) -> bytes:
    chunk = chunk_type + data
    crc = struct.pack('>I', zlib.crc32(chunk) & 0xffffffff)
    return struct.pack('>I', len(data)) + chunk + crc

# Platform colors (dark background palette for consistency)
PLATFORMS = {
    "ergon":       ((20, 30, 50),   "E"),
    "feee":        ((50, 20, 30),   "F"),
    "feesaver":    ((30, 40, 20),   "FS"),
    "justlend_dao":((25, 25, 45),   "JL"),
    "mefree":      ((40, 20, 40),   "MF"),
    "refee":       ((20, 40, 40),   "RF"),
    "tofee":       ((45, 30, 20),   "TF"),
    "tronex":      ((30, 20, 40),   "TX"),
    "tronify":     ((20, 35, 35),   "TY"),
    "tronzap":     ((40, 35, 20),   "TZ"),
    "brutus":      ((35, 25, 25),   "BR"),
    "tronsave":    ((25, 35, 25),   "TS"),
}

def main():
    logos_dir = os.path.join(os.path.dirname(__file__), "logos")
    os.makedirs(logos_dir, exist_ok=True)

    for slug, (color, letter) in PLATFORMS.items():
        path = os.path.join(logos_dir, f"{slug}.png")
        if os.path.exists(path):
            print(f"Skip (exists): {slug}.png")
            continue
        png = create_png(200, 200, color, letter)
        with open(path, 'wb') as f:
            f.write(png)
        print(f"Created: {slug}.png")

if __name__ == "__main__":
    main()
