#!/usr/bin/env python3
"""
fetch_contributions.py
----------------------
Called by the GitHub Action (step 4) to pull live contribution data
from the GitHub GraphQL API and write contributions.json.

Requires:  GITHUB_TOKEN env var  (automatically provided in Actions)
"""

import json
import os
import sys
from datetime import datetime, timezone
from collections import defaultdict

try:
    import requests
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "-q"])
    import requests  # type: ignore

USERNAME = "antan2002"
TOKEN    = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")

if not TOKEN:
    print("WARNING: No GitHub token found. Keeping existing contributions.json.", file=sys.stderr)
    sys.exit(0)

# ---------------------------------------------------------------------------
# GraphQL query — contributions + pinned repos
# ---------------------------------------------------------------------------

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    avatarUrl
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          stargazerCount
          forkCount
          primaryLanguage { name color }
        }
      }
    }
  }
}
"""

now  = datetime.now(timezone.utc)
from_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
to_dt   = now

resp = requests.post(
    "https://api.github.com/graphql",
    headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    json={
        "query": QUERY,
        "variables": {
            "login": USERNAME,
            "from": from_dt.isoformat(),
            "to":   to_dt.isoformat(),
        },
    },
    timeout=20,
)

if resp.status_code != 200:
    print(f"GitHub API error {resp.status_code}: {resp.text}", file=sys.stderr)
    sys.exit(1)

data = resp.json()
if "errors" in data:
    print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
    sys.exit(1)

user = data["data"]["user"]

# ---------------------------------------------------------------------------
# Monthly contribution counts
# ---------------------------------------------------------------------------

days_by_month: dict[str, int] = defaultdict(int)
day_counts:    dict[str, int] = defaultdict(int)   # weekday → count

weeks = user["contributionsCollection"]["contributionCalendar"]["weeks"]
total_year = user["contributionsCollection"]["contributionCalendar"]["totalContributions"]

for week in weeks:
    for day in week["contributionDays"]:
        d   = datetime.fromisoformat(day["date"])
        key = d.strftime("%Y-%m")
        days_by_month[key] += day["contributionCount"]
        if day["contributionCount"] > 0:
            day_counts[d.strftime("%A")] += 1

months_sorted = sorted(days_by_month.items())[-12:]
months_list   = [{"month": k, "count": v} for k, v in months_sorted]

# Active days = weeks * days with count > 0
all_days = [d for w in weeks for d in w["contributionDays"]]
active_days = sum(1 for d in all_days if d["contributionCount"] > 0)

# Busiest day of the week
busiest_day = max(day_counts, key=day_counts.get) if day_counts else "Monday"

# ---------------------------------------------------------------------------
# Streak (naive: count backwards from today)
# ---------------------------------------------------------------------------

day_map = {d["date"]: d["contributionCount"] for w in weeks for d in w["contributionDays"]}
today_str = now.strftime("%Y-%m-%d")
streak = 0
for n in range(366):
    from datetime import timedelta
    check = (now - timedelta(days=n)).strftime("%Y-%m-%d")
    if day_map.get(check, 0) > 0:
        streak += 1
    elif n > 0:
        break

# ---------------------------------------------------------------------------
# Pinned repos
# ---------------------------------------------------------------------------

repos = []
for node in user.get("pinnedItems", {}).get("nodes", []):
    if not node:
        continue
    lang      = node.get("primaryLanguage") or {}
    lang_name = lang.get("name", "Unknown")
    repos.append({
        "name":        node["name"],
        "description": node.get("description") or "",
        "url":         node["url"],
        "stars":       node["stargazerCount"],
        "forks":       node["forkCount"],
        "language":    lang_name,
        "lang_color":  lang.get("color") or "#8b949e",
    })

# Fall back to hardcoded list if no pinned repos
if not repos:
    repos = [
        {
            "name": "AI-Trip-Generator",
            "description": "AI-powered travel itinerary generator with real-time suggestions",
            "url": "https://github.com/antan2002/AI-Trip-Generator",
            "stars": 0, "forks": 0,
            "language": "JavaScript", "lang_color": "#f7df1e",
        },
        {
            "name": "IntelliCart-Sparkathon",
            "description": "Smart retail cart system built for Sparkathon hackathon",
            "url": "https://github.com/antan2002/IntelliCart-Sparkathon",
            "stars": 1, "forks": 1,
            "language": "TypeScript", "lang_color": "#3178c6",
        },
        {
            "name": "assistance",
            "description": "AI-powered study assistant for smart learning and quick answers",
            "url": "https://github.com/antan2002/assistance",
            "stars": 1, "forks": 0,
            "language": "JavaScript", "lang_color": "#f7df1e",
        },
    ]

# ---------------------------------------------------------------------------
# Write output
# ---------------------------------------------------------------------------

output = {
    "username":               USERNAME,
    "avatar_url":             user["avatarUrl"],
    "months":                 months_list,
    "streak_days":            streak,
    "total_contributions_year": total_year,
    "active_days":            active_days,
    "busiest_day":            busiest_day,
    "repos":                  repos,
    "links": [
        {"label": "Portfolio", "url": "https://antanroy.vercel.app",    "icon": "globe"},
        {"label": "LinkedIn",  "url": "https://linkedin.com/in/antanroy","icon": "linkedin"},
        {"label": "LeetCode",  "url": "https://leetcode.com/u/antanroy", "icon": "code"},
    ],
}

with open("contributions.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print(f"contributions.json updated — {total_year} contributions this year, streak {streak}d.")
