#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neon City —— 高精度赛博朋克城市像素动画生成器

生成用于 GitHub 主页 README 的循环 GIF（替换旧版 Neon Alley）：
  · 雨夜城市街景，湿漉漉路面倒映霓虹
  · 摩天楼 + 动态全息广告 + 光锥体积雾
  · 雾中飞行的飞行载具（双向车流，无缝循环）
  · 穿过彩色灯光的雨 + 落地水花
  · 漂浮全息 UI / 街头终端等科技细节
  · 无人物，Blade Runner / Ghost in the Shell 氛围

纯代码逐像素绘制，像素风、无缝循环。
用法:
    python make_neon_city.py
输出:
    assets/neon-city.gif        (成品，1344x756)
    dist/neon-city-preview.png  (预览网格)
"""

import numpy as np
from PIL import Image
import os

# ----------------------------------------------------------------------------
# 基本参数（基准画布 192x108，放大 7 倍 -> 1344x756）
# 54 帧 @ 12fps = 4.5 秒无缝循环
# ----------------------------------------------------------------------------
W, H = 192, 108
SCALE = 7
FRAMES = 54
FPS = 12
GROUND = 74          # 路面起始行
RNG = np.random.RandomState(20260812)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(a, b, t):
    return tuple(int(int(a[i]) + (int(b[i]) - int(a[i])) * t) for i in range(3))


# ----------------------------------------------------------------------------
# 调色板
# ----------------------------------------------------------------------------
SKY_TOP = hexrgb("#03010d")
SKY_MID = hexrgb("#0d0730")
SKY_LOW = hexrgb("#1b0f45")
FOG_HI = hexrgb("#2c1e55")
FOG_TEAL = hexrgb("#12364a")
FOG_DARK = hexrgb("#1a1238")
HAZE = hexrgb("#3a2a66")
STAR = hexrgb("#9fb4e8")

MOON = hexrgb("#ff9fe0")
MOON_DK = hexrgb("#1b0f45")

TOWER_BACK = hexrgb("#0a0620")
TOWER_MID = hexrgb("#0d0930")
TOWER_FRONT = hexrgb("#0b0726")
FAR_BLDG = hexrgb("#171139")
FAR_BLDG2 = hexrgb("#110c2e")
MID_BODY = hexrgb("#0e0a2c")
MID_BODY_L = hexrgb("#16103a")
WIN_DIM = hexrgb("#1e2a4d")
WIN_CYAN = hexrgb("#4ec9ff")
WIN_AMBER = hexrgb("#ffcf5c")

WALL_BASE = hexrgb("#0d0a24")
WALL_DARK = hexrgb("#0a0720")
PANEL = hexrgb("#181244")
PIPE = hexrgb("#1b1740")
PIPE_HI = hexrgb("#2a2560")
TRIM_CYAN = hexrgb("#00f0ff")
TRIM_PINK = hexrgb("#ff2fd6")

LAMP = hexrgb("#ffe9c9")
LAMP_GLOW = hexrgb("#ffb347")
STORE_WARM = hexrgb("#ff9a3c")
STORE_DOOR = hexrgb("#ffd166")
AWING = hexrgb("#ff2fd6")

HOLO_BG = hexrgb("#0a4a55")
HOLO_A = hexrgb("#7b2ff7")
HOLO_B = hexrgb("#00f0ff")
HOLO_C = hexrgb("#ff2fd6")
HOLO_SCAN = hexrgb("#d8fbff")
HOLO_DOT = hexrgb("#7ff0ff")
HOLO_FAINT = hexrgb("#4a6a8a")

SIGN_PINK = hexrgb("#ff2fd6")
SIGN_PINK_HI = hexrgb("#ff7ae0")
SIGN_CYAN = hexrgb("#00f0ff")
SIGN_CYAN_HI = hexrgb("#7df8ff")
SIGN_GLYPH = hexrgb("#ffd9f2")

GROUND_BASE = hexrgb("#0b0818")
GROUND_BAND = hexrgb("#120c26")
WET = hexrgb("#1b1440")
PUDDLE = hexrgb("#241b55")
REFL_CYAN = hexrgb("#00b8d9")
REFL_PINK = hexrgb("#d61fae")
REFL_AMBER = hexrgb("#d98a2b")
REFL_WHT = hexrgb("#bfe9ff")

RAIN_FAR = hexrgb("#6fa8d8")
RAIN_MID = hexrgb("#8fd0f8")
RAIN_NEAR = hexrgb("#c8f2ff")
RAIN_CYAN = hexrgb("#6ff0ff")
RAIN_PINK = hexrgb("#ff8fe0")
SPLASH = hexrgb("#dff6ff")
SPLASH_DIM = hexrgb("#8fd8ff")

CAR_BODY = hexrgb("#28305f")
CAR_CANOPY = hexrgb("#aef6ff")
CAR_TAIL = hexrgb("#ff4fd8")
CAR_HEAD = hexrgb("#dff6ff")
CAR_GLOW = hexrgb("#3a5a9a")
TAXI_BODY = hexrgb("#202a55")
TAXI_SIGN = hexrgb("#ff2fd6")
TAXI_HEAD = hexrgb("#dff6ff")

KIOSK = hexrgb("#101a33")
KIOSK_SCREEN = hexrgb("#7ff0ff")
UI_BORDER = hexrgb("#00f0ff")
UI_BAR = hexrgb("#ff2fd6")
UI_BAR2 = hexrgb("#5ff0ff")
BALCONY = hexrgb("#0b0820")
RAIL = hexrgb("#2a2560")
PLANT = hexrgb("#4fae6a")
PLANT_DK = hexrgb("#2e7a4a")
LANTERN = hexrgb("#ffb347")
LANTERN_GLOW = hexrgb("#ff9a3c")

GRID_LINE = hexrgb("#241b55")
BEACON = hexrgb("#ff4fd8")
WARM_HI = hexrgb("#fff0c8")


def RNG2(i, t):
    v = np.sin(i * 12.9898 + t * 78.233) * 43758.5453
    return v - np.floor(v)


# ----------------------------------------------------------------------------
# 天空 / 远景
# ----------------------------------------------------------------------------
def make_sky(img):
    for y in range(GROUND):
        if y < 12:
            t = y / 12.0
            col = blend(SKY_TOP, SKY_MID, t)
        elif y < 34:
            t = (y - 12) / 22.0
            col = blend(SKY_MID, SKY_LOW, t)
        elif y < 56:
            t = (y - 34) / 22.0
            col = blend(SKY_LOW, FOG_HI, t)
        else:
            t = (y - 56) / float(GROUND - 56)
            col = blend(FOG_HI, HAZE, t)
        img[y, :, :] = col
    for _ in range(14):
        img[int(RNG.randint(0, 9)), int(RNG.randint(0, W))] = STAR


def draw_foggy_moon(img):
    cx, cy, r = 150, 13, 6
    for dy in range(-(r + 3), r + 4):
        for dx in range(-(r + 3), r + 4):
            d2 = dx * dx + dy * dy
            if d2 <= (r + 3) ** 2 and d2 > r * r:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < GROUND:
                    img[y, x] = MOON if (dx + dy) % 2 == 0 else FOG_HI
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy <= r * r:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < GROUND:
                    band = (dy + r) // 2
                    img[y, x] = MOON if band % 2 == 0 else MOON_DK


def build_towers(img, t):
    """三层楼群，参考《迷雾侦探》的远景处理：
    最远层偏亮虚化、稀疏亮点窗；中远景轮廓更硬；近景塔楼清晰窗格 +
    双面光影 + 屋顶装置 + 边缘霓虹光，让剪影从夜空里"浮"出来。"""
    # 第 1 层：最远，空气透视偏亮，窗户少而亮
    far1 = [
        (38, 48, 12), (66, 52, 9), (92, 46, 14), (120, 50, 10), (148, 46, 11),
        (34, 44, 8), (58, 42, 7), (104, 40, 8), (136, 42, 9),
    ]
    for tx, ty, tw in far1:
        img[ty:GROUND, tx:tx + tw] = FAR_BLDG
        for y in range(ty + 2, GROUND - 1, 7):
            if RNG2(tx + y * 3, 5) < 0.16:
                x = tx + 2 + int(RNG2(tx + y, 6) * (tw - 4))
                img[y, x] = WIN_AMBER if RNG2(tx + y, 7) < 0.35 else WIN_CYAN
        img[ty, tx:tx + tw] = blend(FAR_BLDG, WIN_DIM, 0.45)
    # 第 2 层：中远景，轮廓更硬，稀疏窗点 + 天线
    far2 = [(36, 36, 16), (60, 44, 12), (88, 34, 18), (112, 40, 16), (140, 38, 14)]
    for tx, ty, tw in far2:
        img[ty:GROUND, tx:tx + tw] = FAR_BLDG2
        for y in range(ty + 1, GROUND - 1, 4):
            for x in range(tx + 2, tx + tw - 2, 4):
                r = RNG2(x * 7 + y * 13, 8)
                if r < 0.08:
                    img[y, x] = WIN_DIM
                elif r < 0.11:
                    img[y, x] = WIN_CYAN
        if (tx + ty) % 40 < 16:
            img[ty - 3:ty, tx + tw // 2 - 1:tx + tw // 2 + 1] = FAR_BLDG2
    # 第 3 层：近景塔楼（清晰主体）
    towers_mid = [
        (34, 18, 20, 0), (56, 30, 16, 1), (72, 16, 20, 2),
        (94, 26, 16, 3), (110, 20, 24, 4), (136, 32, 16, 5),
    ]
    for tx, ty, tw, idx in towers_mid:
        # 左暗右亮（假体积光）
        for y in range(ty, GROUND):
            img[y, tx:tx + tw // 2] = MID_BODY
            img[y, tx + tw // 2:tx + tw] = MID_BODY_L
        # 窗格：1px 窗、4px 间距，稀疏点缀（少即是多）
        for y in range(ty + 2, GROUND - 2, 4):
            for x in range(tx + 2, tx + tw - 3, 4):
                r = RNG2(x * 17 + y * 13, 1)
                if r < 0.20:
                    img[y, x] = WIN_DIM
                elif r < 0.26:
                    img[y, x] = WIN_CYAN
                elif r < 0.29:
                    img[y, x] = WIN_AMBER
        # 顶部收边 + 右侧边缘霓虹光
        img[ty, tx:tx + tw] = blend(MID_BODY, WIN_DIM, 0.65)
        rim = TRIM_CYAN if idx % 2 == 0 else TRIM_PINK
        img[ty + 2:GROUND - 1, tx + tw - 1] = blend(rim, MID_BODY_L, 0.38)
        # 屋顶装置
        if idx % 3 == 0:      # 天线 + 闪烁信标
            img[ty - 5:ty, tx + tw // 2 - 1:tx + tw // 2 + 1] = MID_BODY_L
            img[ty - 6, tx + tw // 2 - 1:tx + tw // 2 + 1] = (
                BEACON if t % 6 < 3 else TRIM_CYAN)
        elif idx % 3 == 1:    # 水塔
            img[ty - 4:ty, tx + 3:tx + 8] = MID_BODY_L
            img[ty - 5, tx + 4:tx + 7] = WIN_DIM
            img[ty - 4, tx + 3:tx + 8] = blend(MID_BODY_L, WIN_DIM, 0.5)
        else:                 # 楼顶广告牌边缘
            img[ty - 2:ty, tx + 2:tx + tw - 2] = PANEL
            img[ty - 3, tx + 2:tx + tw - 2] = TRIM_PINK if idx % 2 else TRIM_CYAN
    # 中央最高的塔顶大天线
    img[8:16, 82:84] = MID_BODY_L
    img[6:8, 81:85] = hexrgb("#ff2fd6")
    img[8:16, 122:124] = MID_BODY_L
    img[6:8, 121:125] = hexrgb("#00f0ff")


def draw_holo_panel(img, x0, y0, w, h, t, content="ai", seed=0):
    """塔楼/墙面全息广告：渐变色 + 扫描带 + 故障条 + 内容图形"""
    img[y0:y0 + h, x0:x0 + w] = HOLO_BG
    phase = (t * 2 + seed) % 54
    top_col = HOLO_A if phase < 18 else (HOLO_B if phase < 36 else HOLO_C)
    bot_col = HOLO_C if phase < 18 else (HOLO_A if phase < 36 else HOLO_B)
    for i in range(h):
        img[y0 + i, x0:x0 + w] = blend(top_col, bot_col, i / float(h - 1))
    sy = y0 + (t * 3 + seed) % (h - 2)
    img[sy:sy + 1, x0:x0 + w] = HOLO_SCAN
    img[sy + 1, x0:x0 + w] = blend(HOLO_SCAN, HOLO_BG, 0.7)
    # 内容图形
    if content == "ai":
        glyph = [".XX.", "X..X", "XXXX", "X..X", "X..X"]
        gx = x0 + w // 2 - 2
        gy = y0 + h // 2 - 3
        for i, row in enumerate(glyph):
            for j, ch in enumerate(row):
                if ch == "X":
                    img[gy + i, gx + j] = HOLO_SCAN
    elif content == "arm":
        # 机械义肢图标
        cx = x0 + w // 2
        cy = y0 + h // 2
        img[cy - 2, cx - 3:cx + 4] = HOLO_SCAN
        img[cy - 1, cx + 2:cx + 4] = HOLO_DOT
        img[cy, cx + 3:cx + 6] = HOLO_SCAN
        img[cy + 1, cx + 5] = HOLO_DOT
        img[cy + 2, cx + 5:cx + 8] = HOLO_SCAN
        img[cy + 2, cx + 6] = HOLO_DOT
        img[cy - 1, cx - 3:cx - 1] = HOLO_DOT
        img[cy, cx - 4:cx - 1] = HOLO_SCAN
    else:
        # 数据条 / 条形码
        for k in range(w // 2):
            if int(RNG2(k + seed, t // 9)) % 3:
                img[y0 + 2, x0 + k * 2] = HOLO_SCAN
        for k in range(w // 3):
            if int(RNG2(k + 60, t // 7)) % 2:
                img[y0 + h - 3, x0 + k * 3] = HOLO_DOT
    # 故障条
    if (t + seed) % 13 in (3, 7):
        gy = y0 + (t * 5 + seed) % (h - 3)
        img[gy:gy + 2, x0:x0 + w] = HOLO_SCAN if t % 2 else HOLO_BG
    # 边框
    img[y0, x0:x0 + w] = HOLO_SCAN
    img[y0 + h - 1, x0:x0 + w] = HOLO_SCAN
    img[y0:y0 + h, x0] = HOLO_SCAN
    img[y0:y0 + h, x0 + w - 1] = HOLO_SCAN


def draw_light_cone(img, x0, w, y_top, t, color):
    """从全息广告射向路面的体积光锥"""
    cx = x0 + w // 2
    for i in range(GROUND - y_top):
        y = y_top + i
        half = int(w * 0.7 + i * 0.55)
        flick = 0.65 + 0.35 * np.sin(2 * np.pi * (t / FRAMES) + cx * 0.1)
        for x in range(cx - half, cx + half, 2):
            if 0 <= x < W:
                img[y, x] = blend(tuple(img[y, x]), color, 0.16 * flick)


# ----------------------------------------------------------------------------
# 前景建筑（街边立面 + 店铺）
# ----------------------------------------------------------------------------
def draw_foreground_buildings(img, t):
    # 左楼
    img[:, :34] = WALL_BASE
    for y in range(0, GROUND, 11):
        img[y, :34] = PANEL
    for x in range(2, 34, 9):
        img[:, x] = PANEL
    img[0, :34] = TRIM_PINK
    img[1, :34] = blend(TRIM_PINK, WALL_BASE, 0.5)
    # 左楼窗户
    for y in range(8, 52, 7):
        for x in range(5, 30, 8):
            r = RNG2(x * 13 + y * 7, 2)
            if r < 0.3:
                img[y:y + 4, x:x + 4] = WIN_DIM
            elif r < 0.42:
                if r < 0.37:
                    img[y:y + 4, x:x + 4] = WIN_AMBER
                    img[y + 1, x + 1:x + 3] = blend(WIN_AMBER, WARM_HI, 0.5)
                else:
                    img[y:y + 4, x:x + 4] = WIN_CYAN
    # 左楼雨棚
    img[56:58, 2:32] = AWING
    img[57, 2:32] = blend(AWING, WALL_BASE, 0.5)
    # 雨棚下的灯笼（暖光，轻微闪烁）
    for li, lx in enumerate((7, 13, 19, 25)):
        flick = (t + li) % 9 != 7
        img[58, lx] = LANTERN if flick else blend(LANTERN, WALL_BASE, 0.45)
        img[57, lx] = LANTERN_GLOW if flick else blend(LANTERN_GLOW, WALL_BASE, 0.55)
        if flick:
            img[58, lx - 1] = blend(LANTERN, WALL_BASE, 0.4)
            img[58, lx + 1] = blend(LANTERN, WALL_BASE, 0.4)
    # 店铺橱窗（暖光）
    img[60:72, 4:30] = hexrgb("#241231")
    for y in range(61, 71, 3):
        img[y, 5:29] = blend(STORE_WARM, hexrgb("#241231"), 0.25)
    img[60, 4:30] = STORE_DOOR
    img[71, 4:30] = STORE_DOOR
    # 店门（右侧）
    img[62:72, 24:29] = blend(STORE_WARM, hexrgb("#000000"), 0.2)
    img[62, 24:29] = STORE_DOOR
    # 街头终端（橱窗旁）
    img[64:72, 2:6] = KIOSK
    img[65:70, 3:5] = KIOSK_SCREEN
    # 右侧高楼
    img[:, 162:] = WALL_BASE
    for y in range(0, GROUND, 11):
        img[y, 162:] = PANEL
    for x in range(164, 192, 9):
        img[:, x] = PANEL
    img[0, 162:] = TRIM_CYAN
    img[1, 162:] = blend(TRIM_CYAN, WALL_BASE, 0.5)
    for y in range(8, 52, 7):
        for x in range(166, 190, 8):
            r = RNG2(x * 19 + y * 11, 3)
            if r < 0.3:
                img[y:y + 4, x:x + 4] = WIN_DIM
            elif r < 0.44:
                if r < 0.38:
                    img[y:y + 4, x:x + 4] = WIN_AMBER
                    img[y + 1, x + 1:x + 3] = blend(WIN_AMBER, WARM_HI, 0.5)
                else:
                    img[y:y + 4, x:x + 4] = WIN_CYAN
    # 右侧竖向霓虹灯管
    img[30:58, 166:168] = TRIM_CYAN
    img[30:58, 165] = blend(TRIM_CYAN, WALL_BASE, 0.55)
    img[30, 165:169] = TRIM_CYAN
    img[57, 165:169] = TRIM_CYAN
    # 右侧空调外机/管道
    for y in (18, 40):
        img[y:y + 6, 172:178] = PIPE
        img[y, 172:179] = PIPE_HI
        img[y + 5, 172:179] = PIPE_HI
    # 阳台 + 盆栽（生活感细节）
    for by in (26, 46):
        img[by:by + 2, 168:180] = BALCONY
        img[by + 2, 168:180] = RAIL
        img[by - 1, 170] = PLANT
        img[by - 1, 173] = PLANT_DK
        img[by - 1, 176] = PLANT


def draw_neon_kanji(img, x0, y0, glyph, color, hi, on):
    h = len(glyph)
    w = max(len(r) for r in glyph)
    img[y0 - 2:y0 + h + 2, x0 - 2:x0 + w + 2] = PANEL
    for i in range(h):
        row = glyph[i]
        for j in range(w):
            if j < len(row) and row[j] == "X":
                img[y0 + i, x0 + j] = hi if on else blend(color, PANEL, 0.55)
                if on:
                    for dy in (-1, 1):
                        for dx in (-1, 1):
                            yy, xx = y0 + i + dy, x0 + j + dx
                            if 0 <= yy < H and 0 <= xx < W:
                                img[yy, xx] = blend(color, WALL_BASE, 0.35)
    if on:
        img[y0 - 2, x0 - 2:x0 + w + 2] = color
        img[y0 + h + 1, x0 - 2:x0 + w + 2] = color
        img[y0 - 2:y0 + h + 2, x0 - 2] = color
        img[y0 - 2:y0 + h + 2, x0 + w + 1] = color


GLYPH_YE = [
    ".....X.....",
    ".....X.....",
    "XXXXXXXXXXX",
    ".....X.....",
    ".....X.....",
    "....XX.....",
    "X...X.X....",
    "X...X..X...",
    "XX..X...X..",
    ".XX.X....X.",
    "..X.XX...X.",
    "...X..XX.X.",
    "....X..X...",
    ".....XX....",
]


def draw_roof_sign(img, x0, y0, text, color, hi, on, ch_w=5):
    """横向霓虹招牌（挂在楼顶）"""
    w = len(text) * ch_w + (len(text) - 1)
    h = 6
    img[y0 - 1:y0 + h + 1, x0 - 2:x0 + w + 2] = PANEL
    chars = {
        "C": [".XXX.", "X...X", "X....", "X....", "X...X", ".XXX."],
        "Y": ["X...X", "X...X", ".X.X.", "..X..", "..X..", "..X.."],
        "B": ["XXXX.", "X...X", "XXXX.", "X...X", "X...X", "XXXX."],
        "E": ["XXXXX", "X....", "XXXX.", "X....", "X....", "XXXXX"],
        "R": ["XXXX.", "X...X", "XXXX.", "X.X..", "X..X.", "X...X"],
        "N": ["X...X", "XX..X", "X.X.X", "X..XX", "X...X", "X...X"],
        "O": [".XXX.", "X...X", "X...X", "X...X", "X...X", ".XXX."],
        "K": ["X...X", "X..X.", "XX...", "X..X.", "X..X.", "X...X"],
    }
    for ci, ch in enumerate(text):
        cx = x0 + ci * (ch_w + 1)
        for i in range(h):
            row = chars.get(ch, ["XXXXX"] * h)[i]
            for j in range(ch_w):
                if row[j] == "X":
                    img[y0 + i, cx + j] = hi if on else blend(color, PANEL, 0.55)
                    if on:
                        img[y0 + i, cx + j + 1] = blend(color, WALL_BASE, 0.4)
    if on:
        img[y0 - 1, x0 - 2:x0 + w + 2] = color
        img[y0 + h, x0 - 2:x0 + w + 2] = color
        img[y0 - 1:y0 + h + 1, x0 - 2] = color
        img[y0 - 1:y0 + h + 1, x0 + w + 1] = color


# ----------------------------------------------------------------------------
# 路面 / 倒影 / 雨 / 雾 / 载具 / 漂浮全息 UI
# ----------------------------------------------------------------------------
def draw_ground(img, t):
    img[GROUND:, :] = GROUND_BASE
    for y in range(GROUND + 3, H, 6):
        img[y, :] = GROUND_BAND
    for y in range(GROUND, H):
        img[y, :] = blend(tuple(img[y, 0]), WET, 0.28)
    # 车道网格线
    for x in range(36, 160, 28):
        img[GROUND + 4:GROUND + 7, x:x + 6] = GRID_LINE
    puddles = [
        (70, GROUND + 3, 40, 12, REFL_CYAN),
        (130, GROUND + 2, 46, 14, REFL_PINK),
        (46, GROUND + 6, 26, 9, REFL_AMBER),
    ]
    for px, py, pw, ph, col in puddles:
        for dy in range(ph):
            y = py + dy
            half = int(pw * (1 - (dy / float(ph - 1)) ** 0.7) / 2)
            img[y, px - half:px + half] = blend(PUDDLE, WET, dy / float(ph))
        for k in range(3):
            oy = (t * 2 + k * 4) % 14
            y = py + oy * ph // 14
            if y >= py + ph - 1:
                continue
            shift = int(2 * np.sin(2 * np.pi * (t / FRAMES + k / 3.0)))
            x0 = px - pw // 2 + shift
            x1 = px + pw // 2 + shift
            img[y, x0:x1] = blend(col, PUDDLE, 0.35)
            if k == 1:
                img[y + 1, x0:x1] = blend(REFL_WHT, PUDDLE, 0.5)


def draw_street_lamp(img, t):
    """街道灯柱 + 灯光光池"""
    px = 48
    img[56:74, px:px + 2] = PIPE_HI
    img[54:57, px - 3:px + 5] = LAMP
    flick = t % 17 != 9
    if flick:
        for y in range(60, GROUND):
            half = int((y - 56) * 0.35)
            img[y, px - half:px + half] = blend(
                tuple(img[y, px - half:px + half][0]), LAMP_GLOW, 0.18)
    return flick


def draw_fog(img, t):
    """水平流动体积雾 + 地面薄雾"""
    for band in (44, 56, 66):
        for y in range(band, band + 8):
            for x in range(W):
                f = 0.5 + 0.5 * np.sin(2 * np.pi * (x / 46.0 + t / 54.0 + band))
                amt = 0.06 + 0.07 * f
                img[y, x] = blend(tuple(img[y, x]), FOG_TEAL if band > 60 else FOG_HI, amt)
    # 地面薄雾
    for y in range(GROUND + 1, GROUND + 8):
        for x in range(W):
            f = 0.5 + 0.5 * np.sin(2 * np.pi * (x / 34.0 - t / 42.0))
            img[y, x] = blend(tuple(img[y, x]), FOG_TEAL, 0.10 + 0.08 * f)


def blit_block(img, y, x0, w, h, color):
    """带边界裁剪的色块绘制（避免负索引回绕）"""
    xs, xe = max(x0, 0), min(x0 + w, W)
    ys, ye = max(y, 0), min(y + h, H)
    if xs < xe and ys < ye:
        img[ys:ye, xs:xe] = color


def draw_flying_cars(img, t):
    """雾中飞车：多条车流、双向、带光轨，无缝循环"""
    cars = [
        # (y, speed, period, dir, size, bright)
        (19, -4, 216, -1, 2, 0.8),
        (28, 5, 270, 1, 2, 0.9),
        (39, -4, 216, -1, 3, 0.95),
        (48, 5, 270, 1, 4, 1.0),
    ]
    for y, sp, period, d, size, br in cars:
        v = abs(sp)
        k = (t * v) % period
        x = (k - 14) if sp > 0 else (period - k - 16)
        # 光轨（车尾）
        trail_len = 12 if size >= 3 else 8
        for k in range(1, trail_len + 1):
            tx = x - d * k * 2
            if 0 <= tx < W and y + size < H:
                fade = 0.80 - 0.055 * k
                img[y + size, tx] = blend(CAR_TAIL, SKY_LOW, fade)
                if size >= 3:
                    img[y + size - 1, tx] = blend(CAR_TAIL, SKY_LOW, fade + 0.12)
        if size <= 1:
            blit_block(img, y, x, 4, 1, CAR_BODY)
            blit_block(img, y, x + 1, 2, 1, CAR_CANOPY)
            blit_block(img, y, x + 3, 1, 1, CAR_HEAD if d > 0 else CAR_TAIL)
            blit_block(img, y, x, 1, 1, CAR_TAIL if d > 0 else CAR_HEAD)
        elif size == 2:
            blit_block(img, y, x, 6, 2, CAR_BODY)
            blit_block(img, y, x + 1, 4, 1, CAR_CANOPY)
            blit_block(img, y, x + 5, 1, 2, CAR_HEAD if d > 0 else CAR_TAIL)
            blit_block(img, y, x, 1, 2, CAR_TAIL if d > 0 else CAR_HEAD)
            blit_block(img, y + 1, x + 1, 4, 1, CAR_GLOW)
        else:
            sw = 8 if size == 3 else (10 if size == 4 else 13)
            sh = 3 if size == 3 else (4 if size == 4 else 5)
            blit_block(img, y, x, sw, sh, CAR_BODY)
            blit_block(img, y, x + 1, sw - 2, 1, CAR_CANOPY)
            blit_block(img, y, x + sw - 1, 1, sh, CAR_HEAD if d > 0 else CAR_TAIL)
            blit_block(img, y, x, 1, sh, CAR_TAIL if d > 0 else CAR_HEAD)
            blit_block(img, y + 1, x + 1, sw - 2, 1, CAR_GLOW)
            if size >= 5:
                blit_block(img, y + 3, x + 2, sw - 4, 1,
                           blend(CAR_TAIL, SKY_LOW, 0.35))
        # 前灯光束（朝行进方向）
        if size >= 3:
            sw2 = 8 if size == 3 else 10
            hx = x + sw2 if d > 0 else x - 1
            for k in range(1, 4):
                bx = hx + d * k * 2
                if 0 <= bx < W and y < H:
                    img[y, bx] = blend(CAR_HEAD, SKY_LOW, 0.6 - 0.12 * k)
        # 闪烁信标（大载具）
        if size >= 4 and t % 4 < 2:
            sw2 = 10
            bx = x + sw2 // 2
            if 0 <= bx < W and y >= 1:
                img[y - 1, bx] = HOLO_SCAN
                img[y, bx] = HOLO_SCAN
        # 车底霓虹辉光
        sw = 4 if size <= 1 else (6 if size == 2 else (8 if size == 3 else (10 if size == 4 else 13)))
        for k in range(sw - 2):
            gx = x + 1 + k
            if 0 <= gx < W and y + size < GROUND:
                img[y + size, gx] = blend(CAR_TAIL, SKY_LOW, 0.42)
        # 悬浮光束（大载具向下延伸的霓虹光柱）
        if size >= 4:
            sw2 = 10 if size == 4 else 13
            for k in range(3):
                gy = y + size + k
                if gy < GROUND:
                    blit_block(img, gy, x + 2, sw2 - 4, 1,
                               blend(CAR_TAIL, SKY_LOW, 0.5 - 0.08 * k))


def draw_street_taxi(img, t):
    """路面行驶的悬浮出租车（左→右，无缝回卷）"""
    period = 270
    x = int((t * 5) % period) - 14
    if x < 0 or x > W:
        return
    y = 66
    for k in range(1, 10):
        tx = x - k * 3
        if 0 <= tx < W:
            img[y + 2, tx] = blend(BEACON, GROUND_BASE, 0.7 - 0.05 * k)
    blit_block(img, y, x, 10, 4, TAXI_BODY)
    blit_block(img, y, x + 2, 5, 1, TAXI_SIGN)
    blit_block(img, y + 1, x + 2, 5, 1, hexrgb("#ff7ae0"))
    blit_block(img, y, x, 1, 4, BEACON)
    blit_block(img, y, x + 9, 1, 4, TAXI_HEAD)
    blit_block(img, y + 2, x + 1, 8, 1, CAR_GLOW)


def draw_holo_ui(img, t):
    """漂浮的全息界面面板（微微上下浮动 + 动态数据条）"""
    panels = [
        (42, 40, 10, 7, UI_BORDER, 0),
        (88, 42, 12, 8, UI_BORDER, 1),
        (150, 18, 9, 6, UI_BORDER, 2),
    ]
    for px, py, pw, ph, col, seed in panels:
        bob = int(2 * np.sin(2 * np.pi * (t / FRAMES + seed / 3.0)))
        y0 = py + bob
        for i in range(ph):
            for j in range(pw):
                x, y = px + j, y0 + i
                if 0 <= x < W and 0 <= y < GROUND:
                    base = tuple(img[y, x])
                    if i == 0 or i == ph - 1 or j == 0 or j == pw - 1:
                        img[y, x] = blend(base, col, 0.85)
                    else:
                        img[y, x] = blend(base, HOLO_BG, 0.55)
        # 数据条
        for k in range(ph - 2):
            wlen = 2 + int(3 * RNG2(k + seed * 7, t // 6))
            y = y0 + 1 + k
            for j in range(min(wlen, pw - 2)):
                img[y, px + 1 + j] = blend(
                    tuple(img[y, px + 1 + j]),
                    UI_BAR if k % 2 == 0 else UI_BAR2, 0.9)
        # 角标光标
        img[y0 + ph - 2, px + pw - 2] = HOLO_SCAN if t % 5 != 0 else HOLO_BG


def draw_rain(img, t):
    """三层稀疏雨 + 穿过彩色灯光被染色的雨 + 落地水花"""
    layers = [
        (6, 2, 3, RAIN_FAR, 0.75),
        (5, 4, 5, RAIN_MID, 0.9),
        (4, 6, 6, RAIN_NEAR, 1.0),
    ]
    for step, dy, length, col, br in layers:
        for x in range(0, W, step):
            seed = (x * 7 + step * 31) % (H - 4)
            y = (seed + t * dy) % H
            # 灯光染色：左霓虹区偏粉，右霓虹区偏青
            c = col
            if x < 42:
                c = RAIN_PINK if br > 0.85 else blend(RAIN_PINK, col, 0.55)
            elif x > 150:
                c = RAIN_CYAN if br > 0.85 else blend(RAIN_CYAN, col, 0.55)
            if y >= GROUND - 1:
                if y < GROUND + 6:
                    bright = SPLASH if (t + x) % 5 == 0 else SPLASH_DIM
                    img[GROUND, x:x + 2] = bright
                    if (t + x) % 7 == 0 and x + 3 < W:
                        img[GROUND + 1, x + 2] = SPLASH_DIM
                    if (t + x) % 8 == 0 and x - 2 >= 0:
                        img[GROUND + 1, x - 2] = SPLASH_DIM
                continue
            sway = int(np.sin(2 * np.pi * (t / FRAMES + (x % 9) / 9.0)) * 1.2)
            xx = min(max(x + sway, 0), W - 1)
            img[y:y + length, xx] = c
            if step == 4 and x % 8 == 0:
                xx2 = min(max(x + sway + 1, 0), W - 1)
                img[y, xx2] = blend(c, SPLASH, 0.6)


def film_grain(img, t):
    """轻微胶片颗粒（确定性，逐帧图案，循环安全）"""
    for _ in range(360):
        x = int(RNG2(_ * 3 + 11, t) * W)
        y = int(RNG2(_ * 7 + 13, t + 1) * H)
        v = RNG2(_ + 90, t + 2)
        if v < 0.5:
            img[y, x] = blend(tuple(img[y, x]), (0, 0, 0), 0.10)
        elif v < 0.55:
            img[y, x] = blend(tuple(img[y, x]), (230, 240, 255), 0.12)


def vignette(img):
    cx, cy = W / 2.0, H / 2.0
    maxd = np.hypot(cx, cy)
    for y in range(H):
        for x in range(W):
            d = np.hypot(x - cx, y - cy) / maxd
            if d > 0.5:
                img[y, x] = blend(tuple(img[y, x]), (0, 0, 0),
                                  0.24 * (d - 0.5) ** 1.3)


# ----------------------------------------------------------------------------
# 组帧
# ----------------------------------------------------------------------------
def build_frame(t):
    img = np.zeros((H, W, 3), dtype=np.uint8)
    make_sky(img)
    draw_foggy_moon(img)
    build_towers(img, t)
    # 中景全息广告（贴在大楼立面）
    draw_holo_panel(img, 60, 30, 12, 9, t, "ai", seed=0)
    draw_holo_panel(img, 100, 26, 10, 8, t, "arm", seed=9)
    draw_holo_panel(img, 122, 30, 12, 9, t, "data", seed=18)
    draw_holo_panel(img, 142, 36, 10, 7, t, "data", seed=27)
    draw_fog(img, t)
    draw_foreground_buildings(img, t)
    # 楼顶霓虹招牌 + 左墙汉字招牌
    roof_on = not (9 <= t <= 11 or t == 29 or 44 <= t <= 45)
    kanji_on = not (6 <= t <= 7 or t == 25 or 38 <= t <= 39)
    draw_roof_sign(img, (W - 29) // 2, 3, "CYBER", SIGN_CYAN, SIGN_CYAN_HI, roof_on)
    draw_neon_kanji(img, 10, 30, GLYPH_YE, SIGN_PINK, SIGN_PINK_HI, kanji_on)
    draw_light_cone(img, 60, 12, 39, t, HOLO_B)
    draw_light_cone(img, 122, 12, 39, t, HOLO_C)
    draw_light_cone(img, 142, 10, 43, t, HOLO_A)
    draw_street_lamp(img, t)
    draw_ground(img, t)
    draw_holo_ui(img, t)
    draw_rain(img, t)
    draw_flying_cars(img, t)
    draw_street_taxi(img, t)
    film_grain(img, t)
    vignette(img)
    return img


def make_palette_image(colors):
    pal = []
    for c_ in colors:
        pal.extend(c_)
    while len(pal) < 768:
        pal.extend([0, 0, 0])
    im = Image.new("P", (1, 1))
    im.putpalette(pal)
    return im


def main():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    assets_dir = os.path.join(base, "assets")
    dist_dir = os.path.join(base, "dist")
    os.makedirs(assets_dir, exist_ok=True)
    os.makedirs(dist_dir, exist_ok=True)

    all_colors = [
        SKY_TOP, SKY_MID, SKY_LOW, FOG_HI, FOG_TEAL, FOG_DARK, STAR,
        HAZE,
        MOON, MOON_DK,
        TOWER_BACK, TOWER_MID, TOWER_FRONT, WIN_DIM, WIN_CYAN, WIN_AMBER,
        FAR_BLDG, FAR_BLDG2, MID_BODY, MID_BODY_L,
        WALL_BASE, WALL_DARK, PANEL, PIPE, PIPE_HI, TRIM_CYAN, TRIM_PINK,
        LAMP, LAMP_GLOW, STORE_WARM, STORE_DOOR, AWING,
        HOLO_BG, HOLO_A, HOLO_B, HOLO_C, HOLO_SCAN, HOLO_DOT, HOLO_FAINT,
        SIGN_PINK, SIGN_PINK_HI, SIGN_CYAN, SIGN_CYAN_HI, SIGN_GLYPH,
        GROUND_BASE, GROUND_BAND, WET, PUDDLE, REFL_CYAN, REFL_PINK,
        REFL_AMBER, REFL_WHT,
        RAIN_FAR, RAIN_MID, RAIN_NEAR, RAIN_CYAN, RAIN_PINK, SPLASH, SPLASH_DIM,
        CAR_BODY, CAR_CANOPY, CAR_TAIL, CAR_HEAD, CAR_GLOW,
        TAXI_BODY, TAXI_SIGN, TAXI_HEAD,
        KIOSK, KIOSK_SCREEN, UI_BORDER, UI_BAR, UI_BAR2,
        GRID_LINE, BALCONY, RAIL, PLANT, PLANT_DK, LANTERN, LANTERN_GLOW,
        BEACON, WARM_HI,
    ]
    seen = set()
    colors = [c_ for c_ in all_colors if not (c_ in seen or seen.add(c_))]
    pal_img = make_palette_image(colors)

    frames = []
    previews = []
    for t in range(FRAMES):
        arr = build_frame(t)
        im = Image.fromarray(arr, "RGB").resize(
            (W * SCALE, H * SCALE), Image.NEAREST)
        im = im.quantize(palette=pal_img, dither=Image.Dither.NONE)
        frames.append(im)
        if t % 9 == 0:
            previews.append(arr)
        print(f"frame {t + 1}/{FRAMES}")

    gif_path = os.path.join(assets_dir, "neon-city.gif")
    frames[0].save(
        gif_path,
        save_all=True,
        append_images=frames[1:],
        duration=1000 // FPS,
        loop=0,
        optimize=True,
        disposal=2,
    )
    print("GIF size: %.2f MB" % (os.path.getsize(gif_path) / 1e6))

    n = len(previews)
    ph = H * 3
    pw = W * 3
    grid = Image.new("RGB", (pw * n, ph), (8, 5, 18))
    for i, arr in enumerate(previews):
        tile = Image.fromarray(arr, "RGB").resize((pw, ph), Image.NEAREST)
        grid.paste(tile, (i * pw, 0))
    grid.save(os.path.join(dist_dir, "neon-city-preview.png"))
    print("preview saved")


if __name__ == "__main__":
    main()
