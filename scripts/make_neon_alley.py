#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neon Alley —— 赛博朋克像素动画生成器

生成用于 GitHub 主页 README 的循环 GIF：
  霓虹小巷 · 雨夜 · 孤独的赛博武士 · 全息广告 · 水洼反光

纯代码逐像素绘制（无 AI 生图），像素风格、无缝循环。
用法:
    python make_neon_alley.py
输出:
    assets/neon-alley.gif         (成品，960x480)
    dist/neon-alley-preview.png   (预览网格，用于人工检查)
"""

import numpy as np
from PIL import Image
import os

# ----------------------------------------------------------------------------
# 基本参数（像素画基准画布 192x96，放大 5 倍 -> 960x480）
# ----------------------------------------------------------------------------
W, H = 192, 96
SCALE = 5
FRAMES = 48
FPS = 12
GROUND = 76          # 地面起始行
RNG = np.random.RandomState(20260812)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


# ----------------------------------------------------------------------------
# 调色板（像素风，全部颜色都在此表内，量化后零色偏）
# ----------------------------------------------------------------------------
SKY_TOP = hexrgb("#060113")
SKY_MID = hexrgb("#150b33")
SKY_LOW = hexrgb("#311354")
GLOW = hexrgb("#4a1e7a")
STAR = hexrgb("#b7c7ff")
STAR_DIM = hexrgb("#6f8fd0")

MOON_PINK = hexrgb("#ff2fd6")
MOON_CYAN = hexrgb("#00f0ff")
MOON_LPINK = hexrgb("#ff9ff0")
MOON_LCYAN = hexrgb("#8ff6ff")

SKY_FAR = hexrgb("#0b0724")
SKY_FAR2 = hexrgb("#0e0a2e")
SKY_NEAR = hexrgb("#070312")
WIN_LIT = hexrgb("#5ff0ff")
WIN_WARM = hexrgb("#ffd166")
WIN_DIM = hexrgb("#2a3560")

WALL_BASE = hexrgb("#0d0a24")
WALL_DARK = hexrgb("#0a0720")
PANEL = hexrgb("#181244")
PIPE = hexrgb("#1b1740")
PIPE_HI = hexrgb("#2a2560")
TRIM_CYAN = hexrgb("#00f0ff")
TRIM_PINK = hexrgb("#ff2fd6")

LAMP = hexrgb("#ffe9c9")
LAMP_GLOW = hexrgb("#ffb347")

HOLO_BG = hexrgb("#0a4a55")
HOLO_A = hexrgb("#7b2ff7")
HOLO_B = hexrgb("#00f0ff")
HOLO_C = hexrgb("#ff2fd6")
HOLO_SCAN = hexrgb("#d8fbff")
HOLO_DOT = hexrgb("#7ff0ff")

SIGN_PINK = hexrgb("#ff2fd6")
SIGN_PINK_HI = hexrgb("#ff7ae0")
SIGN_PINK_GLYPH = hexrgb("#ffd9f2")
SIGN_CYAN = hexrgb("#00f0ff")
SIGN_CYAN_HI = hexrgb("#7df8ff")
SIGN_CYAN_GLYPH = hexrgb("#d6ffff")

GROUND_BASE = hexrgb("#0b0818")
GROUND_BAND = hexrgb("#120c26")
WET = hexrgb("#1b1440")
PUDDLE = hexrgb("#241b55")
REFL_CYAN = hexrgb("#00b8d9")
REFL_PINK = hexrgb("#d61fae")
REFL_WHT = hexrgb("#bfe9ff")

RAIN_FAR = hexrgb("#7fb8e8")
RAIN_NEAR = hexrgb("#b9ecff")
SPLASH = hexrgb("#dff6ff")
SPLASH_DIM = hexrgb("#8fd8ff")

SP_HAT = hexrgb("#e6c079")
SP_HAT_DK = hexrgb("#9a7440")
SP_FACE = hexrgb("#d9a77e")
SP_FACE_DK = hexrgb("#8a5f44")
SP_EYE = hexrgb("#7df9ff")
SP_COAT = hexrgb("#161d3f")
SP_COAT_HI = hexrgb("#2a3a7a")
SP_TRIM = hexrgb("#00f0ff")
SP_SCARF = hexrgb("#ff2fd6")
SP_SCARF_HI = hexrgb("#ff7ae0")
SP_SCABB = hexrgb("#232a4d")
SP_BLADE = hexrgb("#6ff0ff")
SP_CORD = hexrgb("#ff2fd6")
SP_PANT = hexrgb("#0d1026")
SP_BOOT = hexrgb("#1b2140")
SP_SOLE = hexrgb("#05060f")


def blend(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def make_sky():
    sky = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(GROUND):
        if y < 30:
            t = y / 30.0
            col = blend(SKY_TOP, SKY_MID, t)
        elif y < 58:
            t = (y - 30) / 28.0
            col = blend(SKY_MID, SKY_LOW, t)
        else:
            t = (y - 58) / float(GROUND - 58)
            col = blend(SKY_LOW, GLOW, t)
        sky[y, :, :] = col
    # 星星
    for _ in range(34):
        x = int(RNG.randint(0, W))
        y = int(RNG.randint(0, 34))
        sky[y, x] = STAR if RNG.rand() < 0.55 else STAR_DIM
    return sky


def draw_synth_moon(img, t):
    cx, cy, r = 96, 24, 10
    # 外圈辉光
    for dy in range(-(r + 4), r + 5):
        for dx in range(-(r + 4), r + 5):
            d2 = dx * dx + dy * dy
            if d2 <= (r + 4) ** 2 and d2 > (r + 1) ** 2:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < GROUND:
                    img[y, x] = MOON_LPINK if (dx + dy) % 2 == 0 else MOON_LCYAN
    # 条纹圆（synthwave 太阳）
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            d2 = dx * dx + dy * dy
            if d2 <= r * r:
                x, y = cx + dx, cy + dy
                if 0 <= x < W and 0 <= y < GROUND:
                    band = (dy + r) // 3
                    if band % 2 == 0:
                        img[y, x] = MOON_PINK if dx >= 0 else MOON_CYAN
                    else:
                        img[y, x] = SKY_LOW


def skyline_layer(img, base_y, color, height_max, seed, lit, win_colors):
    r = np.random.RandomState(seed)
    x = 0
    while x < W:
        bw = int(r.randint(7, 15))
        bh = int(r.randint(height_max - 14, height_max))
        top = base_y - bh
        img[top:base_y, x:x + bw] = color
        # 楼顶天线
        if r.rand() < 0.35:
            ax = x + int(r.randint(0, bw - 1))
            img[top - 3:top, ax:ax + 1] = color
        # 窗户
        for wy in range(top + 2, base_y - 2, 4):
            for wx in range(x + 1, x + bw - 1, 3):
                if r.rand() < lit:
                    img[wy, wx] = win_colors[int(r.rand() * len(win_colors))]
        x += bw + int(r.randint(1, 3))


def draw_walls(img):
    lw, rw = 27, 27  # 左右墙宽
    img[:, :lw] = WALL_BASE
    img[:, W - rw:] = WALL_BASE
    # 面板分割线
    for y in range(0, GROUND, 12):
        img[y, :lw] = PANEL
        img[y, W - rw:] = PANEL
    for x in range(0, lw, 8):
        img[:, x] = PANEL
    for x in range(W - rw, W, 8):
        img[:, x] = PANEL
    # 砖块噪点
    for _ in range(160):
        img[int(RNG.randint(0, GROUND)), int(RNG.randint(0, lw - 1))] = WALL_DARK
        img[int(RNG.randint(0, GROUND)), int(RNG.randint(W - rw, W - 1))] = WALL_DARK
    # 顶部霓虹灯带
    img[0, :lw] = TRIM_CYAN
    img[1, :lw] = blend(TRIM_CYAN, WALL_BASE, 0.55)
    img[0, W - rw:] = TRIM_PINK
    img[1, W - rw:] = blend(TRIM_PINK, WALL_BASE, 0.55)
    # 右侧管道
    px = W - rw + 5
    for y in range(8, GROUND, 14):
        img[y:y + 3, px:px + 2] = PIPE
        img[y, px:px + 3] = PIPE_HI
    px2 = W - 9
    for y in range(4, GROUND, 18):
        img[y:y + 2, px2:px2 + 2] = PIPE_HI
    # 左侧通风口
    for gy in range(10, 24, 4):
        img[gy:gy + 2, 2:6] = PIPE
        img[gy:gy + 2, 2] = PIPE_HI
    # 右侧竖向霓虹灯管
    img[30:52, W - 8:W - 6] = TRIM_CYAN
    img[30:52, W - 9] = blend(TRIM_CYAN, WALL_BASE, 0.55)
    img[30, W - 9:W - 5] = TRIM_CYAN
    img[51, W - 9:W - 5] = TRIM_CYAN


def draw_neon_kanji(img, x0, y0, glyph, color, hi, on):
    """霓虹汉字招牌：glyph 为字符矩阵（空格=暗，X=亮）"""
    h = len(glyph)
    w = max(len(r) for r in glyph)
    # 招牌底框
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
    # 边框
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


def draw_text_sign(img, x0, y0, text, color, hi, on, ch_w=5):
    """横向霓虹字母招牌"""
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


def draw_holo(img, x0, y0, w, h, t):
    """全息广告面板：变色 + 扫描线 + 闪烁故障"""
    img[y0:y0 + h, x0:x0 + w] = HOLO_BG
    phase = (t * 2) % 48
    top_col = HOLO_A if phase < 16 else (HOLO_B if phase < 32 else HOLO_C)
    bot_col = HOLO_C if phase < 16 else (HOLO_A if phase < 32 else HOLO_B)
    for i in range(h):
        img[y0 + i, x0:x0 + w] = blend(top_col, bot_col, i / float(h - 1))
    # 扫描带
    sy = y0 + (t * 3) % (h - 2)
    img[sy:sy + 1, x0:x0 + w] = HOLO_SCAN
    img[sy + 1, x0:x0 + w] = blend(HOLO_SCAN, HOLO_BG, 0.7)
    # 数据点
    for i in range(14):
        dx = x0 + int(RNG2(i, t) * (w - 2)) + 1
        dy = y0 + int(RNG2(i + 50, t) * (h - 2)) + 1
        img[dy, dx] = HOLO_DOT
    # AI 字样
    ai = [".XX.", "X..X", "XXXX", "X..X", "X..X"]
    for i, row in enumerate(ai):
        for j, ch in enumerate(row):
            if ch == "X":
                img[y0 + 3 + i, x0 + w // 2 - 4 + j] = HOLO_SCAN
    # 随机故障横条
    if t % 11 == 3 or t % 17 == 9:
        gy = y0 + (t * 5) % (h - 3)
        img[gy:gy + 2, x0:x0 + w] = HOLO_SCAN if t % 2 else HOLO_BG
    img[y0, x0:x0 + w] = HOLO_SCAN
    img[y0 + h - 1, x0:x0 + w] = HOLO_SCAN
    img[y0:y0 + h, x0] = HOLO_SCAN
    img[y0:y0 + h, x0 + w - 1] = HOLO_SCAN


def RNG2(i, t):
    v = np.sin(i * 12.9898 + t * 78.233) * 43758.5453
    return v - np.floor(v)


def draw_ground(img, t):
    img[GROUND:, :] = GROUND_BASE
    for y in range(GROUND + 3, H, 6):
        img[y, :] = GROUND_BAND
    # 湿漉漉的路面高光
    for y in range(GROUND, H):
        img[y, :] = blend(tuple(img[y, 0]), WET, 0.25)
    # 水洼（左 cyan / 右 pink）
    puddles = [
        (34, GROUND + 3, 38, 10, REFL_CYAN),
        (118, GROUND + 2, 46, 12, REFL_PINK),
    ]
    for px, py, pw, ph, col in puddles:
        for dy in range(ph):
            y = py + dy
            half = int(pw * (1 - (dy / float(ph - 1)) ** 0.7) / 2)
            x0 = px - half
            x1 = px + half
            img[y, x0:x1] = blend(PUDDLE, WET, dy / float(ph))
        # 霓虹倒影（随帧闪烁移动）
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


def draw_rain(img, t, far=True):
    step = 3 if far else 2
    dy_speed = 4 if far else 6
    col = RAIN_FAR if far else RAIN_NEAR
    length = 3 if far else 5
    for x in range(0, W, step):
        seed = (x * 7 + (3 if far else 1) * 13) % (H - 6)
        y = (seed + t * dy_speed) % H
        if y >= GROUND - 1:
            # 落地水花
            if y < GROUND + 5:
                bright = SPLASH if (t + x) % 3 == 0 else SPLASH_DIM
                img[GROUND, x:x + 2] = bright
                if (t + x) % 4 == 0 and x + 3 < W:
                    img[GROUND + 1, x + 2] = SPLASH_DIM
                if (t + x) % 5 == 0 and x - 2 >= 0:
                    img[GROUND + 1, x - 2] = SPLASH_DIM
            continue
        sway = int(np.sin(2 * np.pi * (t / FRAMES + (x % 9) / 9.0)) * 1.2)
        xx = min(max(x + sway, 0), W - 1)
        img[y:y + length, xx] = col
        if not far and x % 6 == 0:
            xx2 = min(max(x + sway + 1, 0), W - 1)
            img[y, xx2] = blend(col, SPLASH, 0.6)


# ----------------------------------------------------------------------------
# 赛博武士（程序化像素小人，4 帧走路循环）
# 先在局部画布绘制，再带透明遮罩裁剪贴回主画布，保证任意位置不越界。
# ----------------------------------------------------------------------------
SW, SH = 44, 38
LFX, LFY = 22, 36   # 局部画布中“脚底中心”的坐标


def draw_samurai(img, fx, fy, t):
    ph = t % 4
    bob = [1, -1, 1, -1][ph]           # 身体起伏
    leg = [[-1, 1], [0, 1], [1, -1], [0, -1]][ph]  # 两腿前后
    arm = [[1, -1], [0, -1], [-1, 1], [0, 1]][ph]
    spr = np.full((SH, SW, 3), -1, dtype=np.int16)
    X = LFX
    Y = LFY
    # --- 斗笠（圆锥形蓑笠） ---
    top = Y - 30 + bob
    for i in range(8):
        y = top + i
        half = min(1 + i, 6)
        col = SP_HAT if i < 4 else SP_HAT_DK
        spr[y, X - half:X + half + 1] = col
    brim_y = top + 8
    spr[brim_y, X - 7:X + 8] = SP_HAT
    spr[brim_y + 1, X - 6:X + 7] = SP_HAT_DK
    # --- 脸（笠下阴影） ---
    fy0 = brim_y + 2
    spr[fy0, X - 2:X + 3] = SP_FACE_DK
    spr[fy0 + 1, X - 2:X + 3] = SP_FACE_DK
    # 发光的眼睛（面向右侧）
    spr[fy0, X + 1] = SP_EYE
    spr[fy0, X + 2] = SP_EYE
    # --- 围巾（向左飘动） ---
    sway = int(2 * np.sin(2 * np.pi * (t / FRAMES) + 1.3))
    spr[fy0 + 2, X - 3 + sway:X - 1 + sway] = SP_SCARF
    spr[fy0 + 3, X - 4 + sway:X - 1 + sway] = SP_SCARF_HI
    spr[fy0 + 5, X - 5 + sway:X - 2 + sway] = SP_SCARF
    spr[fy0 + 7, X - 4 + sway:X - 2 + sway] = SP_SCARF_HI
    # --- 武士刀（背在身后，斜向左上，刀刃泛光） ---
    spr[fy0 + 4, X - 4:X - 2] = SP_SCABB
    spr[fy0 + 3, X - 5:X - 3] = SP_SCABB
    spr[fy0 + 2, X - 6:X - 4] = SP_SCABB
    spr[fy0 + 1, X - 7:X - 5] = SP_SCABB
    spr[fy0 + 5, X - 3:X - 1] = SP_CORD
    spr[fy0, X - 8:X - 6] = SP_BLADE
    if (t + 1) % 5 == 0:
        spr[fy0, X - 9] = SP_BLADE
    # --- 身体（大衣） ---
    ty = fy0 + 8 + bob // 2
    spr[ty, X - 3:X + 4] = SP_COAT
    spr[ty + 1, X - 3:X + 4] = SP_COAT
    spr[ty + 2, X - 3:X + 4] = SP_COAT
    spr[ty + 3, X - 3:X + 4] = SP_COAT_HI
    spr[ty + 4, X - 3:X + 4] = SP_COAT
    spr[ty + 5, X - 3:X + 4] = SP_COAT
    spr[ty + 6, X - 3:X + 4] = SP_COAT_HI
    spr[ty + 7, X - 2:X + 3] = SP_COAT
    spr[ty:ty + 8, X + 3] = SP_TRIM
    spr[ty + 4, X - 3:X + 4] = SP_CORD
    # --- 手臂（随走路摆动） ---
    ay = ty + 2
    if arm[0] > 0:
        spr[ay, X + 4:X + 6] = SP_COAT_HI
        spr[ay + 2, X + 5] = SP_FACE_DK
    else:
        spr[ay + 2, X - 4:X - 2] = SP_COAT_HI
        spr[ay + 4, X - 4] = SP_FACE_DK
    # --- 腿 ---
    ly = ty + 8
    l0, l1 = leg
    spr[ly, X - 2 + l0:X + l0] = SP_PANT
    spr[ly + 1, X - 2 + l0:X + l0] = SP_PANT
    spr[ly, X + 1 + l1:X + 3 + l1] = SP_PANT
    spr[ly + 1, X + 1 + l1:X + 3 + l1] = SP_PANT
    # --- 靴子 ---
    spr[ly + 2, X - 2 + l0:X + 1 + l0] = SP_BOOT
    spr[ly + 3, X - 2 + l0:X + 1 + l0] = SP_SOLE
    spr[ly + 2, X + 1 + l1:X + 4 + l1] = SP_BOOT
    spr[ly + 3, X + 1 + l1:X + 4 + l1] = SP_SOLE
    # --- 裁剪贴回主画布 ---
    gx0 = fx - LFX
    gy0 = fy - LFY
    xa, xb = max(0, gx0), min(W, gx0 + SW)
    ya, yb = max(0, gy0), min(H, gy0 + SH)
    if xa >= xb or ya >= yb:
        return
    sub = spr[ya - gy0:yb - gy0, xa - gx0:xb - gx0]
    mask = sub[:, :, 0] >= 0
    dst = img[ya:yb, xa:xb]
    img[ya:yb, xa:xb] = np.where(mask[:, :, None], sub, dst).astype(np.uint8)


def vignette(img):
    mask = np.ones((H, W), dtype=np.float32)
    cx, cy = W / 2.0, H / 2.0
    maxd = np.hypot(cx, cy)
    for y in range(H):
        for x in range(W):
            d = np.hypot(x - cx, y - cy) / maxd
            mask[y, x] = 1.0 - 0.28 * max(0.0, d - 0.55) ** 1.5
    return (img * mask[:, :, None]).astype(np.uint8)


def build_frame(t):
    img = make_sky()
    draw_synth_moon(img, t)
    skyline_layer(img, 62, SKY_FAR, 24, 11, 0.10, [WIN_DIM, WIN_LIT])
    skyline_layer(img, 68, SKY_NEAR, 20, 29, 0.07, [WIN_DIM, WIN_WARM])
    draw_walls(img)
    draw_ground(img, t)
    # 全息广告（左墙）
    draw_holo(img, 3, 7, 21, 15, t)
    # 霓虹灯招牌：屋顶横跨招牌 + 左墙汉字招牌
    pink_on = not (7 <= t <= 9 or t == 23 or 40 <= t <= 41)
    cyan_on = not (12 <= t <= 13 or t == 31 or 44 <= t <= 45)
    draw_text_sign(img, (W - 33) // 2, 2, "CYBER", SIGN_CYAN, SIGN_CYAN_HI, cyan_on)
    draw_neon_kanji(img, 8, 28, GLYPH_YE, SIGN_PINK, SIGN_PINK_HI, pink_on)
    # 左侧暖色路灯
    img[34:37, 23:25] = LAMP
    img[37, 22:26] = LAMP_GLOW if t % 13 else LAMP
    # 雨
    draw_rain(img, t, far=True)
    # 赛博武士（从左侧走进，走出画面后无缝回卷）
    fx = -30 + ((t * 5) % 240)
    draw_samurai(img, fx, GROUND + 1, t)
    draw_rain(img, t, far=False)
    img = vignette(img)
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
        SKY_TOP, SKY_MID, SKY_LOW, GLOW, STAR, STAR_DIM,
        MOON_PINK, MOON_CYAN, MOON_LPINK, MOON_LCYAN,
        SKY_FAR, SKY_FAR2, SKY_NEAR, WIN_LIT, WIN_WARM, WIN_DIM,
        WALL_BASE, WALL_DARK, PANEL, PIPE, PIPE_HI, TRIM_CYAN, TRIM_PINK,
        LAMP, LAMP_GLOW,
        HOLO_BG, HOLO_A, HOLO_B, HOLO_C, HOLO_SCAN, HOLO_DOT,
        SIGN_PINK, SIGN_PINK_HI, SIGN_PINK_GLYPH, SIGN_CYAN, SIGN_CYAN_HI,
        SIGN_CYAN_GLYPH,
        GROUND_BASE, GROUND_BAND, WET, PUDDLE, REFL_CYAN, REFL_PINK, REFL_WHT,
        RAIN_FAR, RAIN_NEAR, SPLASH, SPLASH_DIM,
        SP_HAT, SP_HAT_DK, SP_FACE, SP_FACE_DK, SP_EYE, SP_COAT, SP_COAT_HI,
        SP_TRIM, SP_SCARF, SP_SCARF_HI, SP_SCABB, SP_BLADE, SP_CORD,
        SP_PANT, SP_BOOT, SP_SOLE,
    ]
    # 去重保序
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
        if t % 8 == 0:
            previews.append(arr)
        print(f"frame {t + 1}/{FRAMES}")

    gif_path = os.path.join(assets_dir, "neon-alley.gif")
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

    # 预览网格（4 帧拼图，放大 4 倍便于人工检查）
    n = len(previews)
    ph = H * 3
    pw = W * 3
    grid = Image.new("RGB", (pw * n, ph), (10, 6, 20))
    for i, arr in enumerate(previews):
        tile = Image.fromarray(arr, "RGB").resize((pw, ph), Image.NEAREST)
        grid.paste(tile, (i * pw, 0))
    grid.save(os.path.join(dist_dir, "neon-alley-preview.png"))
    print("preview saved")


if __name__ == "__main__":
    main()
