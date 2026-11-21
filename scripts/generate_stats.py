#!/usr/bin/env python3
"""Generate dark & light GitHub profile stats SVG cards via the GitHub GraphQL API.

Zero external Python dependencies. Designed for scheduled GitHub Actions runs
using the built-in GITHUB_TOKEN.
"""

from __future__ import annotations

import datetime as dt
import html
import json
import math
import os
import pathlib
import subprocess
import sys
import urllib.request
from typing import Any


GRAPHQL_URL = "https://api.github.com/graphql"
FONT_STACK = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES: dict[str, dict[str, str]] = {
    "dark": {
        "bg1": "#161b22",
        "bg2": "#1a1b27",
        "border": "#30363d",
        "title": "#70a5fd",
        "accent": "#bf91f3",
        "accent2": "#38bdae",
        "text": "#c9d1d9",
        "strong": "#f0f6fc",
        "muted": "#8b949e",
        "track": "#21262d",
        "divider": "#262c36",
        "pill_bg": "#21262d",
        "flame": "#ff9e64",
        "dot_stroke": "#161b22",
    },
    "light": {
        "bg1": "#ffffff",
        "bg2": "#f6f8fa",
        "border": "#d0d7de",
        "title": "#0969da",
        "accent": "#8250df",
        "accent2": "#1a7f37",
        "text": "#24292f",
        "strong": "#1f2328",
        "muted": "#656d76",
        "track": "#eaeef2",
        "divider": "#d8dee4",
        "pill_bg": "#eaeef2",
        "flame": "#bc4c00",
        "dot_stroke": "#ffffff",
    },
}


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token.strip()
    try:
        out = subprocess.check_output(["gh", "auth", "token"], text=True, stderr=subprocess.DEVNULL)
        if out.strip():
            return out.strip()
    except Exception:
        pass
    raise SystemExit("Error: GITHUB_TOKEN environment variable is required.")


def graphql(token: str, query: str, variables: dict[str, Any]) -> dict[str, Any]:
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "CmdSuv-Profile-Stats/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    if "errors" in body:
        raise RuntimeError(f"GraphQL errors: {body['errors']}")
    return body["data"]


def fetch_profile_data(token: str, login: str) -> dict[str, Any]:
    profile_query = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        name
        login
        createdAt
        followers { totalCount }
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes {
            name
            stargazerCount
            forkCount
            languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
              edges {
                size
                node { name color }
              }
            }
          }
        }
        contributionsCollection {
          contributionYears
        }
      }
    }
    """
    repos: list[dict[str, Any]] = []
    cursor: str | None = None
    user_meta: dict[str, Any] = {}
    years: list[int] = []

    while True:
        data = graphql(token, profile_query, {"login": login, "cursor": cursor})
        user = data["user"]
        if not user_meta:
            user_meta = {
                "name": user.get("name") or user["login"],
                "login": user["login"],
                "createdAt": user["createdAt"],
                "followers": user["followers"]["totalCount"],
                "publicRepos": user["repositories"]["totalCount"],
            }
            years = sorted(set(user["contributionsCollection"]["contributionYears"]))
        repo_conn = user["repositories"]
        repos.extend(repo_conn["nodes"])
        if not repo_conn["pageInfo"]["hasNextPage"]:
            break
        cursor = repo_conn["pageInfo"]["endCursor"]

    total_stars = sum(r["stargazerCount"] for r in repos)
    lang_bytes: dict[str, int] = {}
    lang_colors: dict[str, str] = {}
    for r in repos:
        if r["name"].lower() == login.lower():
            continue
        for edge in r["languages"]["edges"]:
            lname = edge["node"]["name"]
            lang_bytes[lname] = lang_bytes.get(lname, 0) + edge["size"]
            if edge["node"].get("color"):
                lang_colors[lname] = edge["node"]["color"]

    year_query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
          totalPullRequestContributions
          totalIssueContributions
          contributionCalendar {
            weeks {
              contributionDays {
                date
                contributionCount
              }
            }
          }
        }
      }
    }
    """
    total_commits = 0
    total_prs = 0
    total_issues = 0
    daily: dict[str, int] = {}

    if not years:
        years = [dt.datetime.now(dt.timezone.utc).year]

    for y in years:
        ydata = graphql(
            token,
            year_query,
            {
                "login": login,
                "from": f"{y}-01-01T00:00:00Z",
                "to": f"{y}-12-31T23:59:59Z",
            },
        )
        cc = ydata["user"]["contributionsCollection"]
        total_commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]
        total_prs += cc["totalPullRequestContributions"]
        total_issues += cc["totalIssueContributions"]
        for week in cc["contributionCalendar"]["weeks"]:
            for day in week["contributionDays"]:
                d = day["date"]
                c = day["contributionCount"]
                daily[d] = max(daily.get(d, 0), c)

    today = dt.datetime.now(dt.timezone.utc).date()
    all_dates = sorted(d for d in daily if d <= today.isoformat())
    total_contributions = sum(daily[d] for d in all_dates)

    # Calculate longest streak (preferring most recent on tie)
    longest_len = 0
    longest_start: dt.date | None = None
    longest_end: dt.date | None = None
    run_len = 0
    run_start: dt.date | None = None
    prev_date: dt.date | None = None

    for ds in all_dates:
        d = dt.date.fromisoformat(ds)
        if daily[ds] > 0:
            if prev_date is not None and (d - prev_date).days == 1 and run_len > 0:
                run_len += 1
            else:
                run_len = 1
                run_start = d
            if run_len >= longest_len:
                longest_len = run_len
                longest_start = run_start
                longest_end = d
        else:
            run_len = 0
            run_start = None
        prev_date = d

    # Calculate current streak (anchor on today if > 0, else yesterday if > 0)
    cur_len = 0
    cur_start: dt.date | None = None
    cur_end: dt.date | None = None
    anchor = today if daily.get(today.isoformat(), 0) > 0 else today - dt.timedelta(days=1)
    if daily.get(anchor.isoformat(), 0) > 0:
        cur_end = anchor
        probe = anchor
        while daily.get(probe.isoformat(), 0) > 0:
            cur_len += 1
            cur_start = probe
            probe -= dt.timedelta(days=1)

    # Last 30 days activity window ending today (UTC)
    last_30: list[tuple[dt.date, int]] = []
    for offset in range(29, -1, -1):
        day = today - dt.timedelta(days=offset)
        last_30.append((day, daily.get(day.isoformat(), 0)))

    # Sort languages descending
    total_bytes = sum(lang_bytes.values()) or 1
    sorted_langs = sorted(lang_bytes.items(), key=lambda kv: kv[1], reverse=True)
    languages = [
        {
            "name": name,
            "bytes": size,
            "pct": (size / total_bytes) * 100.0,
            "color": lang_colors.get(name, "#8b949e"),
        }
        for name, size in sorted_langs[:8]
    ]

    created_date = dt.date.fromisoformat(user_meta["createdAt"][:10])

    return {
        "name": user_meta["name"],
        "login": user_meta["login"],
        "createdDate": created_date,
        "today": today,
        "followers": user_meta["followers"],
        "publicRepos": user_meta["publicRepos"],
        "totalStars": total_stars,
        "totalCommits": total_commits,
        "totalPRs": total_prs,
        "totalIssues": total_issues,
        "totalContributions": total_contributions,
        "currentStreak": cur_len,
        "currentStart": cur_start,
        "currentEnd": cur_end,
        "longestStreak": longest_len,
        "longestStart": longest_start,
        "longestEnd": longest_end,
        "languages": languages,
        "last30": last_30,
    }


def fmt_num(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 10_000:
        return f"{n / 1_000:.1f}k"
    return f"{n:,}"


def fmt_short_date(d: dt.date, include_year: bool = False) -> str:
    return d.strftime("%b %-d, %Y" if include_year else "%b %-d")


def fmt_range(start: dt.date | None, end: dt.date | None, today: dt.date) -> str:
    if start is None or end is None:
        return fmt_short_date(today)
    if start == end:
        return fmt_short_date(start, include_year=(start.year != today.year))
    if start.year == end.year:
        return f"{fmt_short_date(start)} – {fmt_short_date(end)}"
    return f"{fmt_short_date(start, True)} – {fmt_short_date(end, True)}"


def render_stats_card(data: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    title = html.escape(f"{data['name']}'s GitHub Stats")
    handle = html.escape(f"@{data['login']}")

    rows = [
        (
            "Total Stars Earned",
            fmt_num(data["totalStars"]),
            # Star icon
            '<path d="M8 .25a.75.75 0 0 1 .673.418l1.882 3.815 4.21.612a.75.75 0 0 1 .416 1.279l-3.046 2.97.719 4.192a.751.751 0 0 1-1.088.791L8 12.347l-3.766 1.98a.75.75 0 0 1-1.088-.79l.72-4.194L.818 6.374a.75.75 0 0 1 .416-1.28l4.21-.611L7.327.668A.75.75 0 0 1 8 .25Z"/>',
        ),
        (
            "Total Commits",
            fmt_num(data["totalCommits"]),
            # Commit icon
            '<path d="M11.93 8.5a4.002 4.002 0 0 1-7.86 0H.75a.75.75 0 0 1 0-1.5h3.32a4.002 4.002 0 0 1 7.86 0h3.32a.75.75 0 0 1 0 1.5Zm-1.43-.75a2.5 2.5 0 1 0-5 0 2.5 2.5 0 0 0 5 0Z"/>',
        ),
        (
            "Total PRs",
            fmt_num(data["totalPRs"]),
            # PR icon
            '<path d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"/>',
        ),
        (
            "Public Repositories",
            fmt_num(data["publicRepos"]),
            # Repo icon
            '<path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 .75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5Zm10.5-1h-8a1 1 0 0 0-1 1v6.708A2.486 2.486 0 0 1 4.5 9h8Z"/>',
        ),
        (
            "Followers",
            fmt_num(data["followers"]),
            # People icon
            '<path d="M2 5.5a3.5 3.5 0 1 1 5.898 2.549 5.508 5.508 0 0 1 3.034 4.084.75.75 0 1 1-1.482.235 4 4 0 0 0-7.9 0 .75.75 0 0 1-1.482-.236A5.507 5.507 0 0 1 3.102 8.05 3.493 3.493 0 0 1 2 5.5ZM11 4a3.001 3.001 0 0 1 2.22 5.018 5.01 5.01 0 0 1 2.56 3.012.749.749 0 0 1-.885.954.752.752 0 0 1-.549-.514 3.507 3.507 0 0 0-2.522-2.372.75.75 0 0 1-.574-.73v-.352a.75.75 0 0 1 .416-.672A1.5 1.5 0 0 0 11 5.5.75.75 0 0 1 11 4Zm-5.5-.5a2 2 0 1 0-.001 3.999A2 2 0 0 0 5.5 3.5Z"/>',
        ),
    ]

    rows_svg: list[str] = []
    for idx, (label, value, icon_path) in enumerate(rows):
        y = 69 + idx * 25
        rows_svg.append(
            f'  <g transform="translate(24, {y - 12})">\n'
            f'    <svg width="15" height="15" viewBox="0 0 16 16" fill="{t["accent"]}">{icon_path}</svg>\n'
            f'    <text x="24" y="12" class="label">{html.escape(label)}</text>\n'
            f'    <text x="268" y="12" text-anchor="end" class="value">{html.escape(value)}</text>\n'
            f'  </g>'
        )

    # Ring shows smooth activity fill based on log-scaled contributions
    contribs = data["totalContributions"]
    ratio = min(0.92, max(0.18, math.log10(contribs + 10) / 3.2))
    r = 41.0
    circ = 2.0 * math.pi * r
    dash = circ * ratio

    return f"""<svg width="465" height="195" viewBox="0 0 465 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">
  <title>{title}</title>
  <defs>
    <linearGradient id="bg-{theme_name}" x1="0" y1="0" x2="465" y2="195" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['bg1']}"/>
      <stop offset="100%" stop-color="{t['bg2']}"/>
    </linearGradient>
    <linearGradient id="ring-{theme_name}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="{t['title']}"/>
      <stop offset="100%" stop-color="{t['accent']}"/>
    </linearGradient>
  </defs>
  <style>
    .title {{ font: 700 16.5px {FONT_STACK}; fill: {t['title']}; }}
    .handle {{ font: 600 11px {FONT_STACK}; fill: {t['muted']}; }}
    .label {{ font: 500 13px {FONT_STACK}; fill: {t['text']}; }}
    .value {{ font: 700 13.5px {FONT_STACK}; fill: {t['strong']}; }}
    .ring-num {{ font: 800 22px {FONT_STACK}; fill: {t['strong']}; }}
    .ring-sub {{ font: 600 9.5px {FONT_STACK}; fill: {t['muted']}; letter-spacing: 0.9px; }}
  </style>
  <rect x="0.75" y="0.75" width="463.5" height="193.5" rx="10" fill="url(#bg-{theme_name})" stroke="{t['border']}" stroke-width="1.2"/>
  <text x="24" y="34" class="title">{title}</text>
  <rect x="372" y="18" width="70" height="21" rx="10.5" fill="{t['pill_bg']}"/>
  <text x="407" y="32" text-anchor="middle" class="handle">{handle}</text>
  <line x1="24" y1="47" x2="441" y2="47" stroke="{t['divider']}" stroke-width="1"/>
{chr(10).join(rows_svg)}
  <g transform="translate(382, 118)">
    <circle cx="0" cy="0" r="{r:.1f}" stroke="{t['track']}" stroke-width="7" fill="none"/>
    <circle cx="0" cy="0" r="{r:.1f}" stroke="url(#ring-{theme_name})" stroke-width="7" fill="none"
            stroke-linecap="round" stroke-dasharray="{dash:.2f} {circ:.2f}" transform="rotate(-90)"/>
    <text x="0" y="3" text-anchor="middle" class="ring-num">{fmt_num(contribs)}</text>
    <text x="0" y="19" text-anchor="middle" class="ring-sub">CONTRIBS</text>
  </g>
</svg>
"""


def render_langs_card(data: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    langs = data["languages"]
    bar_x = 24.0
    bar_w = 302.0
    bar_y = 58.0
    bar_h = 10.0

    segments: list[str] = []
    cx = bar_x
    if langs:
        total_pct = sum(l["pct"] for l in langs) or 100.0
        for i, lang in enumerate(langs):
            w = bar_w * (lang["pct"] / total_pct)
            if i == len(langs) - 1:
                w = max(0.0, (bar_x + bar_w) - cx)
            if w > 0.2:
                segments.append(
                    f'    <rect x="{cx:.2f}" y="{bar_y:.1f}" width="{w:.2f}" height="{bar_h:.1f}" fill="{lang["color"]}"/>'
                )
            cx += w
    else:
        segments.append(
            f'    <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{t["track"]}"/>'
        )

    items: list[str] = []
    for idx, lang in enumerate(langs[:8]):
        col = idx % 2
        row = idx // 2
        x = 24 if col == 0 else 182
        y = 95 + row * 24
        lname = lang["name"]
        if len(lname) > 11:
            lname = lname[:10] + "…"
        pct_str = f"{lang['pct']:.1f}%"
        items.append(
            f'  <g transform="translate({x}, {y})">\n'
            f'    <circle cx="5" cy="-4" r="4.5" fill="{lang["color"]}"/>\n'
            f'    <text x="16" y="0" class="lang-name">{html.escape(lname)}</text>\n'
            f'    <text x="142" y="0" text-anchor="end" class="lang-pct">{pct_str}</text>\n'
            f'  </g>'
        )

    return f"""<svg width="350" height="195" viewBox="0 0 350 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Most Used Languages">
  <title>Most Used Languages</title>
  <defs>
    <linearGradient id="bg-l-{theme_name}" x1="0" y1="0" x2="350" y2="195" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['bg1']}"/>
      <stop offset="100%" stop-color="{t['bg2']}"/>
    </linearGradient>
    <clipPath id="bar-clip-{theme_name}">
      <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" rx="5"/>
    </clipPath>
  </defs>
  <style>
    .title {{ font: 700 16.5px {FONT_STACK}; fill: {t['title']}; }}
    .lang-name {{ font: 600 12.5px {FONT_STACK}; fill: {t['text']}; }}
    .lang-pct {{ font: 500 12px {FONT_STACK}; fill: {t['muted']}; }}
  </style>
  <rect x="0.75" y="0.75" width="348.5" height="193.5" rx="10" fill="url(#bg-l-{theme_name})" stroke="{t['border']}" stroke-width="1.2"/>
  <text x="24" y="34" class="title">Most Used Languages</text>
  <line x1="24" y1="47" x2="326" y2="47" stroke="{t['divider']}" stroke-width="1"/>
  <g clip-path="url(#bar-clip-{theme_name})">
    <rect x="{bar_x:.1f}" y="{bar_y:.1f}" width="{bar_w:.1f}" height="{bar_h:.1f}" fill="{t['track']}"/>
{chr(10).join(segments)}
  </g>
{chr(10).join(items)}
</svg>
"""


def smooth_svg_path(points: list[tuple[float, float]]) -> str:
    if not points:
        return ""
    if len(points) == 1:
        return f"M {points[0][0]:.2f} {points[0][1]:.2f}"
    parts = [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
    for i in range(len(points) - 1):
        p0 = points[i - 1] if i > 0 else points[i]
        p1 = points[i]
        p2 = points[i + 1]
        p3 = points[i + 2] if i + 2 < len(points) else p2
        # Monotonic-clamped Catmull-Rom control points so curves never dip below the baseline
        c1x = p1[0] + (p2[0] - p0[0]) / 6.0
        c1y = p1[1] + (p2[1] - p0[1]) / 6.0
        c2x = p2[0] - (p3[0] - p1[0]) / 6.0
        c2y = p2[1] - (p3[1] - p1[1]) / 6.0
        lo_y = min(p1[1], p2[1])
        hi_y = max(p1[1], p2[1])
        c1y = max(lo_y, min(hi_y, c1y))
        c2y = max(lo_y, min(hi_y, c2y))
        parts.append(f"C {c1x:.2f} {c1y:.2f}, {c2x:.2f} {c2y:.2f}, {p2[0]:.2f} {p2[1]:.2f}")
    return " ".join(parts)


def render_streak_and_activity_card(data: dict[str, Any], theme_name: str) -> str:
    t = THEMES[theme_name]
    today = data["today"]
    total_range = f"{fmt_short_date(data['createdDate'], True)} – Present"
    cur_range = fmt_range(data["currentStart"], data["currentEnd"], today)
    long_range = fmt_range(data["longestStart"], data["longestEnd"], today)

    # 30-day activity chart geometry (right half: x = 445..798, y = 52..156)
    last30 = data["last30"]
    chart_x0 = 456.0
    chart_x1 = 796.0
    chart_y0 = 56.0
    chart_y1 = 154.0
    max_val = max((c for _, c in last30), default=0)
    # Round up nicely to a clean grid ceiling
    if max_val <= 4:
        y_max = 4
    elif max_val <= 10:
        y_max = 10
    elif max_val <= 20:
        y_max = 20
    else:
        y_max = int(math.ceil(max_val / 10.0) * 10)

    pts: list[tuple[float, float]] = []
    n = len(last30)
    for i, (_, cnt) in enumerate(last30):
        px = chart_x0 + (chart_x1 - chart_x0) * (i / max(1, n - 1))
        py = chart_y1 - (chart_y1 - chart_y0) * (cnt / y_max)
        pts.append((px, py))

    line_d = smooth_svg_path(pts)
    area_d = f"{line_d} L {chart_x1:.2f} {chart_y1:.2f} L {chart_x0:.2f} {chart_y1:.2f} Z"

    # Horizontal gridlines (0, 50%, 100%)
    grid_svg: list[str] = []
    for frac, val in [(0.0, 0), (0.5, y_max // 2), (1.0, y_max)]:
        gy = chart_y1 - (chart_y1 - chart_y0) * frac
        grid_svg.append(
            f'  <line x1="{chart_x0:.1f}" y1="{gy:.1f}" x2="{chart_x1:.1f}" y2="{gy:.1f}" '
            f'stroke="{t["divider"]}" stroke-width="1" stroke-dasharray="3 3"/>'
        )
        grid_svg.append(
            f'  <text x="{chart_x0 - 8:.1f}" y="{gy + 3.5:.1f}" text-anchor="end" class="axis">{val}</text>'
        )

    # X-axis labels at 4 evenly spaced dates
    x_labels_svg: list[str] = []
    for idx in (0, 10, 20, 29):
        if idx < n:
            d, _ = last30[idx]
            px = pts[idx][0]
            anchor = "start" if idx == 0 else ("end" if idx == 29 else "middle")
            x_labels_svg.append(
                f'  <text x="{px:.1f}" y="{chart_y1 + 18:.1f}" text-anchor="{anchor}" class="axis">{d.strftime("%b %-d")}</text>'
            )

    # Highlight dots on days with > 0 contributions
    dots_svg: list[str] = []
    for (d, cnt), (px, py) in zip(last30, pts):
        if cnt > 0:
            dots_svg.append(
                f'  <circle cx="{px:.2f}" cy="{py:.2f}" r="3.4" fill="{t["accent"]}" stroke="{t["dot_stroke"]}" stroke-width="1.5"/>'
            )

    # Streak progress ring
    cur_s = data["currentStreak"]
    long_s = max(1, data["longestStreak"])
    s_ratio = 0.0 if cur_s == 0 else min(1.0, max(0.15, cur_s / long_s))
    sr = 34.0
    scirc = 2.0 * math.pi * sr
    sdash = scirc * s_ratio

    last30_total = sum(c for _, c in last30)

    return f"""<svg width="825" height="195" viewBox="0 0 825 195" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Contribution Streak and 30-Day Activity">
  <title>Contribution Streak and 30-Day Activity</title>
  <defs>
    <linearGradient id="bg-s-{theme_name}" x1="0" y1="0" x2="825" y2="195" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['bg1']}"/>
      <stop offset="100%" stop-color="{t['bg2']}"/>
    </linearGradient>
    <linearGradient id="area-{theme_name}" x1="0" y1="{chart_y0:.1f}" x2="0" y2="{chart_y1:.1f}" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['title']}" stop-opacity="0.34"/>
      <stop offset="100%" stop-color="{t['title']}" stop-opacity="0.02"/>
    </linearGradient>
    <linearGradient id="line-{theme_name}" x1="{chart_x0:.1f}" y1="0" x2="{chart_x1:.1f}" y2="0" gradientUnits="userSpaceOnUse">
      <stop offset="0%" stop-color="{t['title']}"/>
      <stop offset="100%" stop-color="{t['accent']}"/>
    </linearGradient>
  </defs>
  <style>
    .title {{ font: 700 15.5px {FONT_STACK}; fill: {t['title']}; }}
    .big {{ font: 800 28px {FONT_STACK}; fill: {t['strong']}; }}
    .streak-big {{ font: 800 26px {FONT_STACK}; fill: {t['flame']}; }}
    .sub {{ font: 600 12.5px {FONT_STACK}; fill: {t['text']}; }}
    .accent-sub {{ font: 600 12.5px {FONT_STACK}; fill: {t['flame']}; }}
    .date {{ font: 500 10.5px {FONT_STACK}; fill: {t['muted']}; }}
    .axis {{ font: 500 10px {FONT_STACK}; fill: {t['muted']}; }}
    .badge {{ font: 600 10.5px {FONT_STACK}; fill: {t['accent2']}; }}
  </style>
  <rect x="0.75" y="0.75" width="823.5" height="193.5" rx="10" fill="url(#bg-s-{theme_name})" stroke="{t['border']}" stroke-width="1.2"/>

  <!-- Panel 1: Total Contributions -->
  <g transform="translate(75, 0)">
    <text x="0" y="90" text-anchor="middle" class="big">{fmt_num(data['totalContributions'])}</text>
    <text x="0" y="118" text-anchor="middle" class="sub">Total Contributions</text>
    <text x="0" y="138" text-anchor="middle" class="date">{html.escape(total_range)}</text>
  </g>
  <line x1="150" y1="30" x2="150" y2="165" stroke="{t['divider']}" stroke-width="1"/>

  <!-- Panel 2: Current Streak -->
  <g transform="translate(222, 0)">
    <circle cx="0" cy="80" r="{sr:.1f}" stroke="{t['track']}" stroke-width="5.5" fill="none"/>
    <circle cx="0" cy="80" r="{sr:.1f}" stroke="{t['flame']}" stroke-width="5.5" fill="none"
            stroke-linecap="round" stroke-dasharray="{sdash:.2f} {scirc:.2f}" transform="rotate(-90 0 80)"/>
    <!-- Flame icon centered at top of ring -->
    <g transform="translate(-8, 36)">
      <circle cx="8" cy="10" r="10" fill="{t['bg1']}"/>
      <svg width="16" height="16" viewBox="0 0 16 16" fill="{t['flame']}" y="1">
        <path d="M8 1c.7 2.2 3.4 3.6 3.4 7a3.4 3.4 0 1 1-6.8 0c0-1.2.4-2.2 1-3.1.2 1.1.9 1.7 1.4 1.9C6.8 5 7.2 3.1 8 1Z"/>
      </svg>
    </g>
    <text x="0" y="90" text-anchor="middle" class="streak-big">{cur_s}</text>
    <text x="0" y="134" text-anchor="middle" class="accent-sub">Current Streak</text>
    <text x="0" y="152" text-anchor="middle" class="date">{html.escape(cur_range)}</text>
  </g>
  <line x1="294" y1="30" x2="294" y2="165" stroke="{t['divider']}" stroke-width="1"/>

  <!-- Panel 3: Longest Streak -->
  <g transform="translate(358, 0)">
    <text x="0" y="90" text-anchor="middle" class="big">{data['longestStreak']}</text>
    <text x="0" y="118" text-anchor="middle" class="sub">Longest Streak</text>
    <text x="0" y="138" text-anchor="middle" class="date">{html.escape(long_range)}</text>
  </g>
  <line x1="422" y1="22" x2="422" y2="173" stroke="{t['divider']}" stroke-width="1.2"/>

  <!-- Panel 4: 30-Day Activity Graph -->
  <text x="444" y="34" class="title">Last 30 Days Activity</text>
  <text x="796" y="34" text-anchor="end" class="badge">{fmt_num(last30_total)} contributions</text>
{chr(10).join(grid_svg)}
  <path d="{area_d}" fill="url(#area-{theme_name})"/>
  <path d="{line_d}" fill="none" stroke="url(#line-{theme_name})" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
{chr(10).join(dots_svg)}
{chr(10).join(x_labels_svg)}
</svg>
"""


def main() -> int:
    login = os.environ.get("GITHUB_USERNAME", "CmdSuv").strip()
    token = get_token()
    data = fetch_profile_data(token, login)

    out_dir = pathlib.Path(__file__).resolve().parent.parent / "assets"
    out_dir.mkdir(parents=True, exist_ok=True)

    for theme in ("dark", "light"):
        (out_dir / f"stats-{theme}.svg").write_text(render_stats_card(data, theme), encoding="utf-8")
        (out_dir / f"langs-{theme}.svg").write_text(render_langs_card(data, theme), encoding="utf-8")
        (out_dir / f"streak-{theme}.svg").write_text(render_streak_and_activity_card(data, theme), encoding="utf-8")

    print(
        f"Generated 6 SVG cards for @{login} in {out_dir} "
        f"(contribs={data['totalContributions']}, commits={data['totalCommits']}, "
        f"stars={data['totalStars']}, repos={data['publicRepos']}, "
        f"streak={data['currentStreak']}/{data['longestStreak']})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
