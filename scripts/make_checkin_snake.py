#!/usr/bin/env python3
"""
签到蛇生成器：根据 GitHub 连续贡献天数（每日打卡），绘制一条越来越长的像素蛇。
用法（在 GitHub Actions 中）：
    GITHUB_TOKEN=... GITHUB_USER=Zhishulo python scripts/make_checkin_snake.py
输出：dist/checkin-snake.svg
"""

import json
import os
import sys
import urllib.request
from datetime import date, timedelta


TOKEN = os.environ.get("GITHUB_TOKEN", "")
LOGIN = os.environ.get("GITHUB_USER", "Zhishulo")
LOOKBACK_DAYS = 120


def fetch_contributions():
    """通过 GitHub GraphQL 拉取最近 N 天的贡献日历。"""
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks { contributionDays { date contributionCount } }
          }
        }
      }
    }"""
    today = date.today()
    frm = (today - timedelta(days=LOOKBACK_DAYS)).isoformat() + "T00:00:00Z"
    to = today.isoformat() + "T23:59:59Z"
    payload = json.dumps({
        "query": query,
        "variables": {"login": LOGIN, "from": frm, "to": to},
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        method="POST",
        headers={
            "Authorization": "Bearer " + TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "checkin-snake",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    days = {}
    try:
        weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        for week in weeks:
            for d in week["contributionDays"]:
                days[d["date"]] = int(d["contributionCount"])
    except Exception as exc:  # noqa: BLE001
        print("GraphQL 解析失败:", exc, file=sys.stderr)
    return days


def calc_streak(days):
    """连续签到天数：从今天（若今天未打卡则从昨天）向前数。"""
    d = date.today()
    if days.get(d.isoformat(), 0) == 0:
        d -= timedelta(days=1)
    n = 0
    while days.get(d.isoformat(), 0) > 0:
        n += 1
        d -= timedelta(days=1)
    return n


def winding_path(cols, rows):
    """蛇形遍历网格，返回 [(col, row), ...]。"""
    cells = []
    for r in range(rows):
        row = range(cols) if r % 2 == 0 else range(cols - 1, -1, -1)
        for c in row:
            cells.append((c, r))
    return cells


def lerp_color(a, b, t):
    return "#%02x%02x%02x" % tuple(
        round(a[i] + (b[i] - a[i]) * t) for i in range(3)
    )


def main():
    days = fetch_contributions()
    streak = calc_streak(days)
    today_count = days.get(date.today().isoformat(), 0)

    cols, rows, cell = 24, 5, 26
    path = winding_path(cols, rows)
    segs = min(streak, len(path))
    ox, oy = 76, 74

    tail = (111, 102, 163)
    mid1 = (0, 240, 255)
    mid2 = (168, 85, 247)
    head = (255, 47, 214)
    def seg_color(i):
        t = i / max(1, segs - 1)
        if t < 0.5:
            return lerp_color(tail, mid1, t * 2)
        return lerp_color(mid2, head, (t - 0.5) * 2)

    svg = []
    svg.append(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 300" '
        'width="760" height="300">'
    )
    svg.append(
        '<defs>'
        '<linearGradient id="t" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#00f0ff"/>'
        '<stop offset="50%" stop-color="#a855f7"/>'
        '<stop offset="100%" stop-color="#ff2fd6"/>'
        "</linearGradient>"
        "</defs>"
    )
    svg.append('<rect width="760" height="300" fill="#0a0518" rx="16"/>')
    svg.append(
        '<rect x="8" y="8" width="744" height="284" rx="12" fill="none" '
        'stroke="rgba(168,85,247,.45)" stroke-width="1"/>'
    )
    # 网格背景
    for c in range(cols):
        for r in range(rows):
            x, y = ox + c * cell, oy + r * cell
            svg.append(
                '<rect x="%d" y="%d" width="%d" height="%d" fill="#150b30" '
                'stroke="rgba(123,47,247,.16)" stroke-width="1"/>'
                % (x + 1, y + 1, cell - 2, cell - 2)
            )
    # 蛇身
    for i in range(segs):
        c, r = path[i]
        x, y = ox + c * cell + 2, oy + r * cell + 2
        svg.append(
            '<rect x="%d" y="%d" width="%d" height="%d" rx="5" fill="%s"/>'
            % (x, y, cell - 4, cell - 4, seg_color(i))
        )
    # 蛇头（眼睛）
    if segs > 0:
        c, r = path[segs - 1]
        hx, hy = ox + c * cell, oy + r * cell
        svg.append(
            '<circle cx="%d" cy="%d" r="4" fill="#ffffff"/>'
            '<circle cx="%d" cy="%d" r="2" fill="#12081f"/>'
            '<circle cx="%d" cy="%d" r="4" fill="#ffffff"/>'
            '<circle cx="%d" cy="%d" r="2" fill="#12081f"/>'
            % (hx + 7, hy + 8, hx + 8, hy + 8, hx + 19, hy + 8, hx + 18, hy + 8)
        )
        # 前方的"签到苹果"
        nxt = segs if segs < len(path) else segs - 1
        c2, r2 = path[nxt]
        ax, ay = ox + c2 * cell, oy + r2 * cell
        svg.append(
            '<circle cx="%d" cy="%d" r="6" fill="#ff2fd6"/>'
            '<rect x="%d" y="%d" width="3" height="7" fill="#7ae582"/>'
            % (ax + 13, ay + 12, ax + 12, ay + 4)
        )
    # 标题
    svg.append(
        '<text x="380" y="38" text-anchor="middle" font-family="Consolas, monospace" '
        'font-size="24" font-weight="700" fill="url(#t)" letter-spacing="5">'
        "CHECK-IN SNAKE</text>"
    )
    svg.append(
        '<text x="380" y="60" text-anchor="middle" font-family="Consolas, monospace" '
        'font-size="12" fill="#9d95c9" letter-spacing="3">DAILY CHECK-IN · '
        "AUTO UPDATED BY GITHUB ACTIONS</text>"
    )
    # 统计文字
    today_txt = "今日已打卡" if today_count > 0 else "今日待打卡"
    svg.append(
        '<text x="380" y="238" text-anchor="middle" font-family="Consolas, monospace" '
        'font-size="30" font-weight="700" fill="#e8e6ff">连续签到 '
        '<tspan fill="#00f0ff">%d</tspan> 天</text>' % streak
    )
    svg.append(
        '<text x="380" y="264" text-anchor="middle" font-family="Consolas, monospace" '
        'font-size="13" fill="%s">%s · 近 14 天打卡记录</text>'
        % ("#7ae582" if today_count > 0 else "#ff9f43", today_txt)
    )
    # 近 14 天小方块
    sx, sy, sq, gap = 300, 272, 10, 4
    for i in range(14):
        d = date.today() - timedelta(days=13 - i)
        cnt = days.get(d.isoformat(), 0)
        color = "#2a2350" if cnt == 0 else ("#4facfe" if cnt <= 3 else ("#00f0ff" if cnt <= 8 else "#ff2fd6"))
        svg.append(
            '<rect x="%d" y="%d" width="%d" height="%d" rx="2" fill="%s"/>'
            % (sx + i * (sq + gap), sy, sq, sq, color)
        )
    svg.append("</svg>")

    os.makedirs("dist", exist_ok=True)
    with open("dist/checkin-snake.svg", "w", encoding="utf-8") as f:
        f.write("\n".join(svg))
    print("checkin-snake.svg generated | streak = %d | today = %d" % (streak, today_count))


if __name__ == "__main__":
    main()
