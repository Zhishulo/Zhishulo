#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Forest Dream —— 治愈系自然森林像素短片生成器

参考《星露谷物语》《动物森友会》《吉卜力自然动画》的融合风格：
  · 清晨薄雾、阳光穿过树冠的柔和光束
  · 草叶/花朵/藤蔓/灌木随风摆动，露珠与湿润泥土
  · 蝴蝶、狐狸、小狗、兔子、小鸟依次出现，各有独立动作细节
  · 中段一场温柔阵雨（草叶/蘑菇/水面的水花与涟漪）
  · 雨后云开日出，蒸汽与发光粒子，树叶更清新
  · 无人物、无对话、无 UI、无文字

纯代码逐像素绘制，像素风、无缝循环。
用法:
    python make_forest_dream.py
输出:
    assets/forest-dream.gif        (成品)
    dist/forest-dream-preview.png  (预览网格)
"""

import numpy as np
from PIL import Image
import os

# ----------------------------------------------------------------------------
# 基本参数（基准画布 192x108，放大 7 倍 -> 1344x756）
# 72 帧 @ 12fps = 6 秒无缝循环
# ----------------------------------------------------------------------------
W, H = 192, 108
SCALE = 7
FRAMES = 72
FPS = 12
GROUND = 80          # 草地地面起始行
RNG = np.random.RandomState(20260812)


def hexrgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def blend(a, b, t):
    return tuple(int(int(a[i]) + (int(b[i]) - int(a[i])) * t) for i in range(3))


def clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# ----------------------------------------------------------------------------
# 调色板（低饱和自然色）
# ----------------------------------------------------------------------------
SKY_TOP = hexrgb("#a9c8d6")
SKY_MID = hexrgb("#c3d8d2")
SKY_LOW = hexrgb("#e0e6d2")
SUN = hexrgb("#fff2c8")
SUN_GLOW = hexrgb("#fbe8b8")
MIST = hexrgb("#dce8e6")

TREE_FAR = hexrgb("#7d9a8a")
TREE_FAR2 = hexrgb("#6b8a7d")
TRUNK = hexrgb("#7a5a3c")
TRUNK_DK = hexrgb("#5d4430")
LEAF_DK = hexrgb("#5f8f6a")
LEAF_MID = hexrgb("#7fb08a")
LEAF_LI = hexrgb("#9ec59a")
LEAF_HI = hexrgb("#bfd9ac")
VINE = hexrgb("#5d7f5a")

GRASS_DK = hexrgb("#6f9259")
GRASS = hexrgb("#86a86e")
GRASS_LI = hexrgb("#a8c78a")
GRASS_HI = hexrgb("#c6dda6")
SOIL = hexrgb("#4e5d42")
SOIL_DK = hexrgb("#3f4c38")
BUSH_DK = hexrgb("#567b52")
BUSH = hexrgb("#7aa06f")
BUSH_LI = hexrgb("#9cbc8a")
BERRY = hexrgb("#c96a52")

FLOWER_W = hexrgb("#f4f4ea")
FLOWER_Y = hexrgb("#f2d27a")
FLOWER_P = hexrgb("#b9a4d8")
FLOWER_PK = hexrgb("#e8b8c8")
CENTER = hexrgb("#e0a94a")

MUSH_CAP = hexrgb("#c96a52")
MUSH_CAP_DK = hexrgb("#a84e3c")
MUSH_DOT = hexrgb("#f4ece0")
MUSH_STEM = hexrgb("#e6d8b8")
STONE = hexrgb("#9aa296")
STONE_DK = hexrgb("#7d847a")

POND = hexrgb("#8fc0d8")
POND_DK = hexrgb("#6ba3c0")
POND_LI = hexrgb("#cfe8ee")
POND_EDGE = hexrgb("#5b7f6e")

FOX = hexrgb("#d08a4e")
FOX_LI = hexrgb("#f0b070")
FOX_DK = hexrgb("#7a4a2e")
FOX_W = hexrgb("#f2eee2")
FOX_K = hexrgb("#3a2a20")

PUP = hexrgb("#d9b58a")
PUP_DK = hexrgb("#b28a5e")
PUP_EAR = hexrgb("#8a6240")
PUP_K = hexrgb("#2e2418")

RAB = hexrgb("#b8b0a0")
RAB_DK = hexrgb("#8f8878")
RAB_PK = hexrgb("#e8b8c8")
RAB_K = hexrgb("#2a2420")

BIRD = hexrgb("#6fb7d0")
BIRD_LI = hexrgb("#9ad4e4")
BIRD_DK = hexrgb("#4e8fa8")
BEAK = hexrgb("#f0a840")

BFLY_B = hexrgb("#8fb8d8")
BFLY_O = hexrgb("#e8a85a")
BFLY_BODY = hexrgb("#3a3428")

RAIN = hexrgb("#cfe4ee")
SPLASH = hexrgb("#dff0f6")
DEW = hexrgb("#f2f8ff")
STEAM = hexrgb("#eef6f0")
SPARK = hexrgb("#fff7d8")


def RNG2(i, t):
    v = np.sin(i * 12.9898 + t * 78.233) * 43758.5453
    return v - np.floor(v)


# ----------------------------------------------------------------------------
# 天气时间线（平滑函数，保证首尾相接）
# ----------------------------------------------------------------------------
def weather(t):
    th = 2 * np.pi * t / FRAMES
    mist = 0.16 + 0.28 * (0.5 + 0.5 * np.cos(th))          # 首尾晨雾，中段散开
    rain = np.exp(-((t - 42) / 9.0) ** 2)                  # 中段阵雨
    after = np.exp(-((t - 58) / 7.0) ** 2)                 # 雨后放晴
    light = 1.0 - 0.42 * rain - 0.15 * mist + 0.16 * after
    light = clamp(light, 0.55, 1.10)
    drift = int(9 * np.sin(np.pi * t / FRAMES))            # 镜头缓慢前移并回转
    return mist, rain, after, light, drift


# ----------------------------------------------------------------------------
# 天空 / 太阳 / 光束
# ----------------------------------------------------------------------------
def draw_sky(img, t, light):
    for y in range(GROUND):
        if y < 34:
            tt = y / 34.0
            col = blend(SKY_TOP, SKY_MID, tt)
        else:
            tt = (y - 34) / float(GROUND - 34)
            col = blend(SKY_MID, SKY_LOW, tt)
        img[y, :, :] = col
    # 太阳（右上，柔和光晕）
    cx, cy = 168, 14
    for dy in range(-9, 10):
        for dx in range(-9, 10):
            d2 = dx * dx + dy * dy
            x, y = cx + dx, cy + dy
            if 0 <= x < W and 0 <= y < GROUND:
                if d2 <= 36:
                    img[y, x] = SUN
                elif d2 <= 64:
                    img[y, x] = blend(SUN_GLOW, tuple(img[y, x]), 0.35)
    # 阳光光束（透过树冠的柔和斜光）
    beams = [(66, -10, 5), (108, -6, 4), (146, -12, 6)]
    for bx, by0, bw in beams:
        sway = int(2 * np.sin(2 * np.pi * t / FRAMES + bx))
        for k in range(0, GROUND - by0, 2):
            y = by0 + k
            half = max(1, int(bw * 0.5 + k * 0.05))
            x0 = bx + sway + k // 3
            for x in range(x0 - half, x0 + half, 2):
                if 0 <= x < W and 0 <= y < GROUND:
                    img[y, x] = blend(tuple(img[y, x]), SUN_GLOW, 0.10)


def draw_far_treeline(img, t, drift):
    # 远处树线（低饱和蓝绿，薄雾感）
    base_y = 52
    strip = np.zeros((H, W, 3), dtype=np.uint8)
    x = -8
    while x < W + 8:
        bw = int(10 + RNG2(x, 3) * 12)
        bh = int(10 + RNG2(x + 40, 4) * 10)
        top = base_y - bh
        col = TREE_FAR if RNG2(x, 5) < 0.5 else TREE_FAR2
        for xx in range(x, x + bw):
            if 0 <= xx < W:
                strip[top:base_y, xx] = col
                # 树冠圆顶
                for dy in range(1, 4):
                    yy = top - dy
                    if 0 <= yy < H:
                        strip[yy, xx] = blend(col, SKY_MID, 0.25 * dy)
        x += bw + int(RNG2(x + 9, 6) * 6)
    rolled = np.roll(strip, drift, axis=1)
    mask = rolled[:, :, 0] != 0
    img[:base_y, :] = np.where(mask[:base_y, :, None], rolled[:base_y],
                               img[:base_y, :])
    # 远处飞鸟（两只，缓缓飞过）
    for b in range(2):
        bx = (t * 2 + b * 90) % (W + 20) - 10
        by = 30 + b * 6
        if 0 <= bx + 2 < W:
            img[by, bx] = TREE_FAR2
            img[by + 1, bx + 1] = TREE_FAR2
            img[by, bx + 2] = TREE_FAR2


# ----------------------------------------------------------------------------
# 中景树木（树干 + 树冠 + 藤蔓 + 枝干）
# ----------------------------------------------------------------------------
def draw_tree(img, tx, ty, trunk_w, canopy, t):
    """ty = 树冠顶；树干到 GROUND。canopy = [(ox, oy, r), ...] 树冠簇"""
    trunk = [trunk_w - 1, trunk_w]
    # 树干（微弯）
    for y in range(ty + 6, GROUND):
        w_ = trunk[0] if y < GROUND - 18 else trunk[1]
        x0 = tx - w_ // 2
        img[y, x0:x0 + w_] = TRUNK
        if y % 5 == 0:
            img[y, x0 + 1:x0 + w_ - 1] = TRUNK_DK
    # 树冠簇
    for ox, oy, r in canopy:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r:
                    x, y = tx + ox + dx, ty + oy + dy
                    if 0 <= x < W and 0 <= y < GROUND:
                        d2 = dx * dx + dy * dy
                        if d2 <= r * r * 0.35:
                            img[y, x] = LEAF_DK
                        elif d2 <= r * r * 0.75:
                            img[y, x] = LEAF_MID
                        else:
                            img[y, x] = LEAF_LI
    # 高光叶簇（随风轻摆）
    sway = int(1.2 * np.sin(2 * np.pi * t / FRAMES + tx * 0.3))
    for ox, oy, r in canopy[:2]:
        x, y = tx + ox + sway, ty + oy - r // 2
        if 0 <= x < W and 0 <= y < GROUND:
            img[y, x] = LEAF_HI
            if x + 1 < W:
                img[y + 1, x + 1] = LEAF_HI
    # 藤蔓
    for vx in (tx - trunk_w // 2 + 1, tx + trunk_w // 2 - 1):
        for k in range(10):
            y = ty + 8 + k * 2
            swayv = int(np.sin(2 * np.pi * t / FRAMES + vx + k * 0.4))
            xx = vx + swayv
            if 0 <= xx < W and 0 <= y < GROUND:
                img[y, xx] = VINE
                if k % 3 == 0 and 0 <= xx + 1 < W:
                    img[y, xx + 1] = LEAF_LI


def draw_branch(img, x0, y, w):
    """横向树枝（给小鸟站）"""
    for x in range(x0, x0 + w):
        if 0 <= x < W:
            img[y, x] = TRUNK_DK
            if x % 3 == 0:
                img[y - 1, x] = TRUNK


# ----------------------------------------------------------------------------
# 草地 / 花 / 灌木 / 蘑菇 / 石头 / 池塘
# ----------------------------------------------------------------------------
GRASS_TUFT = [
    "..g..",
    ".gGg.",
    ".gGg.",
    "gGGGg",
]
GRASS_TALL = [
    "..g...",
    ".gGg..",
    ".gGg..",
    "gGGGg.",
    "gGGGgg",
]
FLOWER_SPR = [
    ".wWw.",
    "wCcWw",
    ".WcW.",
]
BUSH_SPR = [
    "..bb...",
    ".bBbBb.",
    "bBBBBb.",
    "bBBBBbb",
]
MUSH_SPR = [
    ".rRr.",
    "rWRRr",
    ".SSS.",
    ".SSS.",
]
STONE_SPR = [
    ".ss.",
    "sSSs",
    "sSSs",
]


def sprite_arr(grid, colors):
    h = len(grid)
    w = max(len(r) for r in grid)
    arr = np.full((h, w, 3), -1, dtype=np.int16)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch in colors:
                arr[y, x] = colors[ch]
    return arr


def paste_sprite(img, spr, x, y):
    SH, SW = spr.shape[:2]
    xa, xb = max(0, x), min(W, x + SW)
    ya, yb = max(0, y), min(H, y + SH)
    if xa >= xb or ya >= yb:
        return
    sub = spr[ya - y:yb - y, xa - x:xb - x]
    mask = sub[:, :, 0] >= 0
    dst = img[ya:yb, xa:xb]
    img[ya:yb, xa:xb] = np.where(mask[:, :, None], sub, dst).astype(np.uint8)


def draw_meadow_back(img, t):
    """背景草线 + 花 / 灌木 / 蘑菇 / 石头（动物在其后穿过）"""
    sway = lambda ph: int(1.5 * np.sin(2 * np.pi * t / FRAMES + ph))
    # 地面基底（湿润泥土 + 草地）
    for y in range(GROUND, H):
        tt = (y - GROUND) / float(H - GROUND)
        img[y, :, :] = blend(GRASS_DK, SOIL, tt)
    for _ in range(70):
        y = GROUND + int(RNG2(_, 60) * (H - GROUND))
        x = int(RNG2(_ + 9, 61) * W)
        img[y, x] = blend(GRASS_DK, SOIL_DK, 0.6)
    # 草线（贴地）
    tuft = sprite_arr(GRASS_TUFT, {"g": GRASS_DK, "G": GRASS})
    for x in range(0, W, 5):
        if RNG2(x, 10) < 0.7:
            paste_sprite(img, tuft, x + sway(x), GROUND - 5)
    # 花朵
    flower_y = sprite_arr(FLOWER_SPR, {"w": FLOWER_W, "W": FLOWER_W, "c": CENTER, "C": FLOWER_Y})
    flower_p = sprite_arr(FLOWER_SPR, {"w": FLOWER_P, "W": FLOWER_PK, "c": CENTER, "C": FLOWER_Y})
    flowers = [(24, 1), (52, 0), (76, 1), (100, 0), (128, 1), (152, 0), (170, 1), (44, 2), (116, 2)]
    for fx, ph in flowers:
        spr = flower_y if int(RNG2(fx, 12) * 2) == 0 else flower_p
        paste_sprite(img, spr, fx + sway(fx + ph), GROUND - 4)
    # 灌木
    bush = sprite_arr(BUSH_SPR, {"b": BUSH_DK, "B": BUSH, "r": BERRY})
    for bx in (14, 60, 96, 150, 180):
        paste_sprite(img, bush, bx + sway(bx * 3), GROUND - 5)
    # 蘑菇
    mush = sprite_arr(MUSH_SPR, {"r": MUSH_CAP, "R": MUSH_CAP_DK, "W": MUSH_DOT, "S": MUSH_STEM})
    for mx, my in ((36, 77), (86, 78), (124, 76), (168, 78)):
        paste_sprite(img, mush, mx, my)
    # 石头
    stone = sprite_arr(STONE_SPR, {"s": STONE_DK, "S": STONE})
    for sx, sy in ((8, 77), (72, 76), (140, 77)):
        paste_sprite(img, stone, sx, sy)


def draw_meadow_front(img, t):
    """前景高草 / 花（动物在其后跑过，增加纵深）+ 池塘"""
    sway = lambda ph: int(2.0 * np.sin(2 * np.pi * t / FRAMES + ph))
    tall = sprite_arr(GRASS_TALL, {"g": GRASS, "G": GRASS_LI})
    for x in range(0, W, 6):
        if RNG2(x, 11) < 0.7:
            paste_sprite(img, tall, x + sway(x * 2), 100)
    flower_y = sprite_arr(FLOWER_SPR, {"w": FLOWER_W, "W": FLOWER_W, "c": CENTER, "C": FLOWER_Y})
    flower_p = sprite_arr(FLOWER_SPR, {"w": FLOWER_P, "W": FLOWER_PK, "c": CENTER, "C": FLOWER_Y})
    for fx, ph in ((30, 3), (88, 1), (118, 4), (178, 2)):
        spr = flower_y if int(RNG2(fx + 7, 12) * 2) == 0 else flower_p
        paste_sprite(img, spr, fx + sway(fx + ph), 101)
    # 大蘑菇（前景）
    big_mush = sprite_arr(MUSH_SPR, {"r": MUSH_CAP, "R": MUSH_CAP_DK, "W": MUSH_DOT, "S": MUSH_STEM})
    paste_sprite(img, big_mush, 54, 100)
    # 池塘（右下近景）
    draw_pond(img, t)


def draw_pond(img, t):
    """小水洼：天空倒影 + 阵雨涟漪"""
    px, py, pw, ph = 140, 97, 34, 7
    for dy in range(ph):
        y = py + dy
        half = int(pw * (1 - (dy / float(ph - 1)) ** 0.7) / 2)
        x0, x1 = px - half, px + half
        tcol = blend(POND, POND_DK, dy / float(ph))
        img[y, x0:x1] = tcol
        img[y, x0] = POND_EDGE
        img[y, x1 - 1] = POND_EDGE
    # 天空倒影亮带
    for k in range(2):
        yy = py + 2 + k * 2
        if yy < py + ph:
            img[yy, px - pw // 2 + 4:px + pw // 2 - 4] = POND_LI


# ----------------------------------------------------------------------------
# 动物精灵
# ----------------------------------------------------------------------------
FOX_FRAMES = [
    # 行走 0（前后腿分开）
    [".....oooooo",
     "....oOoOooo",
     "...oooooooo",
     "...ooooooko",
     "..o.oooooo.",
     "..wo.oo.o..",
     "..kd.od.od.",
     "..........."],
    # 行走 1（收腿）
    [".....oooooo",
     "....oOoOooo",
     "...oooooooo",
     "...ooooooko",
     "..o.oooooo.",
     "..wo.oo.o..",
     "..kd.o.do..",
     "..........."],
    # 行走 2（前后腿分开，反向）
    [".....oooooo",
     "....oOoOooo",
     "...oooooooo",
     "...ooooooko",
     "..o.oooooo.",
     "..wo.oo.o..",
     "..kd.od.od.",
     "..........."],
    # 行走 3（收腿反向）
    [".....oooooo",
     "....oOoOooo",
     "...oooooooo",
     "...ooooooko",
     "..o.oooooo.",
     "..wo.oo.o..",
     "..kd.do.o..",
     "..........."],
    # 回头张望（头朝左）
    ["oooooo.....",
     "oooOoOo....",
     "oooooooo...",
     "okoooooo...",
     ".oooooo.o..",
     ".oooo.owo..",
     ".od.od.kd..",
     "..........."],
]
FOX_COLORS = {"o": FOX, "O": FOX_LI, "d": FOX_DK, "w": FOX_W, "k": FOX_K}

PUP_FRAMES = [
    ["...ppppp..",
     "..pPpPpp..",
     "..pppppp..",
     ".pp.pp.pp.",
     "....pp.pp.",
     "....kk.kk."],
    ["...ppppp..",
     "..pPpPpp..",
     "..pppppp..",
     ".pp.pp.pp.",
     "...pp.pp..",
     "...kk.kk.."],
]
PUP_COLORS = {"p": PUP, "P": PUP_DK, "k": PUP_K}

RAB_FRAMES = [
    ["..RR..",
     "..RR..",
     "..rr..",
     ".rrrr.",
     ".rrrr.",
     "..rr..",
     "..dd.."],
    ["..RR..",
     "..rR..",
     "..rr..",
     ".rrrr.",
     ".rrrr.",
     "..rr..",
     "..dd.."],
]
RAB_COLORS = {"r": RAB, "R": RAB_DK, "d": RAB_PK}

BIRD_IDLE = [
    [".bb..",
     "bBbb.",
     "bBbb.",
     ".bb..",
     "....."],
]
BIRD_FLY = [
    [".b.b.",
     "bBbb.",
     ".bbb.",
     "..b..",
     "....."],
    [".....",
     "bBbb.",
     ".bbb.",
     ".b.b.",
     "....."],
]
BIRD_COLORS = {"b": BIRD, "B": BIRD_LI}

BFLY_FRAME_A = [
    ["w.w.",
     ".b..",
     "w.w."],
]
BFLY_FRAME_B = [
    ["...w",
     ".b..",
     "...w"],
]
BFLY_COLORS = {"b": BFLY_BODY, "w": BFLY_B}


def draw_fox(img, t):
    """狐狸：从左到右穿过草地，中段回头张望"""
    if t < 30:
        x = int(t * 3) - 26
        frame = (t // 2) % 4
    elif t < 35:
        x = 64 + (t - 30)
        frame = 4                      # 回头张望
    else:
        x = 69 + int((t - 35) * 4)
        frame = (t // 2) % 4
    if x < -14 or x > W:
        return
    spr = sprite_arr(FOX_FRAMES[frame], FOX_COLORS)
    paste_sprite(img, spr, x, GROUND - 9)


def draw_butterflies(img, t):
    """两只蝴蝶：一只绕野花盘旋，一只引着小狗跑"""
    th = 2 * np.pi * t / FRAMES
    # 蝴蝶 1：绕 (52, 68) 的野花画 8 字
    bx = 52 + int(9 * np.sin(2 * th + 0.6))
    by = 66 + int(5 * np.sin(th + 1.2))
    spr = sprite_arr(BFLY_FRAME_A if (t // 2) % 2 == 0 else BFLY_FRAME_B, BFLY_COLORS)
    paste_sprite(img, spr, bx, by)
    # 蝴蝶 2：绕 (128, 64) 飞，引导小狗
    bx2 = 122 + int(12 * np.sin(th * 2 + 2.0))
    by2 = 60 + int(6 * np.sin(th + 3.0))
    spr2 = sprite_arr(BFLY_FRAME_A if (t // 1) % 2 == 0 else BFLY_FRAME_B, BFLY_COLORS)
    paste_sprite(img, spr2, bx2, by2)
    return bx2, by2


def draw_puppy(img, t, butterfly):
    """小狗追蝴蝶：跟着蝴蝶的水平位置跑，跑动循环"""
    bx, by = butterfly
    px = clamp(bx + 8, 4, W - 12)
    frame = (t // 1) % 2
    spr = sprite_arr(PUP_FRAMES[frame], PUP_COLORS)
    paste_sprite(img, spr, int(px), GROUND - 7)


def draw_rabbit(img, t):
    """远处兔子：耳朵轻抖，偶尔小跳"""
    hop = 0
    if 18 <= t <= 19 or 52 <= t <= 53:
        hop = 2
    frame = (t // 4) % 2
    spr = sprite_arr(RAB_FRAMES[frame], RAB_COLORS)
    paste_sprite(img, spr, 150 + (1 if hop else 0), GROUND - 8 - hop)


def draw_bird(img, t):
    """枝头小鸟：整理羽毛，中段飞起绕弧线返回"""
    if 26 <= t <= 40:
        k = (t - 26) / 14.0
        bx = 78 + int(22 * np.sin(np.pi * k))
        by = 30 - int(20 * np.sin(np.pi * k))
        spr = sprite_arr(BIRD_FLY[(t // 1) % 2], BIRD_COLORS)
    else:
        bx, by = 78, 30
        spr = sprite_arr(BIRD_IDLE[0], BIRD_COLORS)
    paste_sprite(img, spr, bx, by)


# ----------------------------------------------------------------------------
# 雨 / 水花 / 涟漪 / 露珠 / 蒸汽 / 光尘
# ----------------------------------------------------------------------------
def draw_rain(img, t, rain):
    if rain < 0.05:
        return
    drops = int(rain * 70)
    for i in range(drops):
        x = int(RNG2(i, 20) * W)
        y = int((RNG2(i + 100, 21) * 70 + t * 2) % (GROUND - 4))
        if y < GROUND - 2:
            img[y:y + 4, x] = RAIN
            if y + 4 >= GROUND - 2:
                img[GROUND - 1, x] = SPLASH


def draw_ripples(img, t, rain):
    """雨滴落在池塘上的扩散涟漪"""
    if rain < 0.05:
        return
    for k in range(4):
        cx = 142 + k * 8
        cy = 100
        age = (t + k * 13) % 6
        if age < 1:
            continue
        r = age // 2 + 1
        for a in range(10):
            ax = cx + int(r * np.cos(a * np.pi / 5))
            ay = cy + int(r * np.sin(a * np.pi / 5) * 0.5)
            if 0 <= ax < W and 0 <= ay < H:
                img[ay, ax] = blend(tuple(img[ay, ax]), POND_LI, 0.55)


def draw_dew(img, t):
    """草叶上的露珠微光"""
    for i in range(24):
        x = int(RNG2(i, 30) * W)
        y = GROUND - 3 - int(RNG2(i + 5, 31) * 3)
        if (t + i) % 6 < 2:
            img[y, x] = blend(tuple(img[y, x]), DEW, 0.8)


def draw_steam(img, t, after):
    """雨后蒸汽与发光粒子"""
    n = int(after * 22)
    for i in range(n):
        x = int((RNG2(i, 40) * W + t * 1) % W)
        y = GROUND - 2 - int((t * 1.2 + RNG2(i, 41) * 8) % 14)
        if 0 <= y < GROUND:
            img[y, x] = blend(tuple(img[y, x]), STEAM, 0.55)


def draw_motes(img, t):
    """阳光里的光尘粒子"""
    for i in range(16):
        x = int((RNG2(i, 50) * W + t * 0.8) % W)
        y = int((RNG2(i + 7, 51) * 40 + t * 0.5) % 42)
        if (t + i) % 7 < 3:
            img[y, x] = blend(tuple(img[y, x]), SPARK, 0.65)


def apply_mist(img, t, mist):
    """晨雾与雨雾（水平流动）"""
    for band in (0, 18, 36):
        for y in range(band, band + 10):
            for x in range(W):
                f = 0.5 + 0.5 * np.sin(2 * np.pi * (x / 60.0 + t / 60.0 + band))
                amt = (mist * 0.55) * (0.55 + 0.45 * f)
                if y < GROUND:
                    img[y, x] = blend(tuple(img[y, x]), MIST, amt)


def apply_light(img, light):
    arr = img.astype(np.float32) * light
    img[:, :, :] = np.clip(arr, 0, 255).astype(np.uint8)


def soft_vignette(img):
    cx, cy = W / 2.0, H / 2.0
    maxd = np.hypot(cx, cy)
    for y in range(H):
        for x in range(W):
            d = np.hypot(x - cx, y - cy) / maxd
            if d > 0.55:
                img[y, x] = blend(tuple(img[y, x]), (150, 160, 150), 0.10 * (d - 0.55))


# ----------------------------------------------------------------------------
# 组帧
# ----------------------------------------------------------------------------
def build_frame(t):
    mist, rain, after, light, drift = weather(t)
    img = np.zeros((H, W, 3), dtype=np.uint8)
    draw_sky(img, t, light)
    draw_far_treeline(img, t, drift)
    # 中景树木（风吹叶摆）
    draw_tree(img, 34, 8, 4, [(0, 12, 10), (10, 8, 8), (-8, 9, 7)], t)
    draw_tree(img, 118, 10, 4, [(0, 13, 10), (9, 9, 8), (-7, 10, 7)], t)
    draw_tree(img, 178, 7, 5, [(0, 13, 11), (9, 8, 9), (-8, 9, 8)], t)
    draw_branch(img, 44, 34, 36)      # 供小鸟站立的树枝
    draw_meadow_back(img, t)
    # 动物
    butterfly = draw_butterflies(img, t)
    draw_puppy(img, t, butterfly)
    draw_fox(img, t)
    draw_rabbit(img, t)
    draw_bird(img, t)
    draw_meadow_front(img, t)
    # 天气与细节
    draw_dew(img, t)
    draw_rain(img, t, rain)
    draw_ripples(img, t, rain)
    draw_steam(img, t, after)
    draw_motes(img, t)
    apply_light(img, light)
    apply_mist(img, t, mist)
    soft_vignette(img)
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
        SKY_TOP, SKY_MID, SKY_LOW, SUN, SUN_GLOW, MIST,
        TREE_FAR, TREE_FAR2, TRUNK, TRUNK_DK, LEAF_DK, LEAF_MID, LEAF_LI,
        LEAF_HI, VINE,
        GRASS_DK, GRASS, GRASS_LI, GRASS_HI, BUSH_DK, BUSH, BUSH_LI, BERRY,
        SOIL, SOIL_DK,
        FLOWER_W, FLOWER_Y, FLOWER_P, FLOWER_PK, CENTER,
        MUSH_CAP, MUSH_CAP_DK, MUSH_DOT, MUSH_STEM, STONE, STONE_DK,
        POND, POND_DK, POND_LI, POND_EDGE,
        FOX, FOX_LI, FOX_DK, FOX_W, FOX_K,
        PUP, PUP_DK, PUP_EAR, PUP_K,
        RAB, RAB_DK, RAB_PK, RAB_K,
        BIRD, BIRD_LI, BIRD_DK, BEAK,
        BFLY_B, BFLY_O, BFLY_BODY,
        RAIN, SPLASH, DEW, STEAM, SPARK,
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
        if t % 12 == 0:
            previews.append(arr)
        print(f"frame {t + 1}/{FRAMES}")

    gif_path = os.path.join(assets_dir, "forest-dream.gif")
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
    grid = Image.new("RGB", (pw * n, ph), (200, 210, 200))
    for i, arr in enumerate(previews):
        tile = Image.fromarray(arr, "RGB").resize((pw, ph), Image.NEAREST)
        grid.paste(tile, (i * pw, 0))
    grid.save(os.path.join(dist_dir, "forest-dream-preview.png"))
    print("preview saved")


if __name__ == "__main__":
    main()
