import time
import board
import digitalio
from adafruit_rgb_display import st7735
from PIL import Image, ImageDraw
from pathlib import Path
import random
import time

WIDTH    = 128
HEIGHT   = 160
BAUDRATE = 24_000_000

cs  = digitalio.DigitalInOut(board.D23)
dc  = digitalio.DigitalInOut(board.D24)
rst = digitalio.DigitalInOut(board.D25)

spi  = board.SPI()
disp = st7735.ST7735R(
    spi, cs=cs, dc=dc, rst=rst,
    width=WIDTH, height=HEIGHT, baudrate=BAUDRATE, rotation=90,
)

green = Image.new("RGB", (128, 160), (0, 255, 0))
red = Image.new("RGB", (128, 160), (255, 0, 0))

ASSETS = Path(__file__).resolve().parent.parent / "assets" / "display_images"
names = ["eye_open.jpeg", "eye_blink.jpeg"]

"""
try:
	frames = [Image.open(ASSETS / n) for n in names]
	while True:
		for f in frames:
			disp.image(f)
			time.sleep(0.5)       
except KeyboardInterrupt:
    pass
"""

W, H = 160, 128
BG        = (0, 0, 0)
SCLERA    = (255, 255, 255)
IRIS      = (60, 180, 230)
IRIS_DARK = (20, 80, 140)
PUPIL     = (10, 10, 15)
HIGHLIGHT = (255, 255, 255)

def render_eye(lid_pos=0.0, look=(0, -4)):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    cx, cy = W // 2, H // 2
    sw, sh = 140, 95
    d.ellipse((cx - sw//2, cy - sh//2, cx + sw//2, cy + sh//2), fill=SCLERA)
    ix, iy = cx + look[0], cy + look[1]
    ir, pr = 36, 15
    d.ellipse((ix - ir, iy - ir, ix + ir, iy + ir), fill=IRIS_DARK)
    d.ellipse((ix - ir+5, iy - ir+5, ix + ir-5, iy + ir-5), fill=IRIS)
    d.ellipse((ix - pr, iy - pr, ix + pr, iy + pr), fill=PUPIL)
    d.ellipse((ix - 18, iy - 20, ix - 2, iy - 4), fill=HIGHLIGHT)
    d.ellipse((ix + 7, iy + 5, ix + 12, iy + 10), fill=HIGHLIGHT)
    if lid_pos > 0:
        eye_top = cy - sh//2 - 5
        eye_bot = cy + sh//2 + 5
        base_y  = eye_top + (eye_bot - eye_top) * lid_pos
        dip = 10
        pts = [(W, 0), (0, 0)]
        for x in range(0, W + 1, 4):
            rel = (x - W/2) / (W/2)
            y = base_y + dip * (1 - rel * rel)
            pts.append((x, y))
        d.polygon(pts, fill=BG)
    return img

def blink(disp, look=(0, -6)):
    for i in range(1, 7):
        t = i / 6
        disp.image(render_eye(lid_pos=t * t, look=look))      # ease-in
    time.sleep(0.05)
    for i in range(1, 9):
        t = i / 8
        disp.image(render_eye(lid_pos=1 - t * (2 - t), look=look))  # ease-out

def idle_loop(disp):
    disp.image(render_eye(look=(0, -6)))
    while True:
        time.sleep(random.uniform(2.5, 6.0))
        blink(disp)
        if random.random() < 0.15:
            time.sleep(0.12)
            blink(disp)
import threading

def star_eye():
		threading.Thread(target=idle_loop, daemon=True).start()
if __name__ == "__main__":
	idle_loop(disp)
