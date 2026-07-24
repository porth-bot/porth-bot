#!/usr/bin/env python3
"""Pull the GitHub contribution calendar for a user and cache it to JSON.

Needs a token in GITHUB_TOKEN (or GH_TOKEN). The default Actions token works;
so does a classic PAT. Only public contribution counts are read.

    python scripts/fetch_contributions.py --login porth-bot
"""

import argparse
import json
import os
import sys
from pathlib import Path

import requests

API = "https://api.github.com/graphql"

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          firstDay
          contributionDays {
            date
            weekday
            contributionCount
          }
        }
      }
    }
  }
}
"""


def token():
    for name in ("GITHUB_TOKEN", "GH_TOKEN"):
        value = os.environ.get(name)
        if value:
            return value
    sys.exit("no token found: set GITHUB_TOKEN or GH_TOKEN")


def fetch(login):
    response = requests.post(
        API,
        json={"query": QUERY, "variables": {"login": login}},
        headers={
            "Authorization": f"bearer {token()}",
            "Accept": "application/vnd.github+json",
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if "errors" in payload:
        sys.exit(f"graphql error: {payload['errors']}")
    user = payload["data"]["user"]
    if user is None:
        sys.exit(f"no such user: {login}")
    return user["contributionsCollection"]["contributionCalendar"]


def flatten(calendar):
    """Weeks of dicts -> a flat, date-ordered list plus the week grid."""
    weeks = []
    days = []
    for week in calendar["weeks"]:
        column = [None] * 7
        for day in week["contributionDays"]:
            entry = {"date": day["date"], "count": day["contributionCount"]}
            column[day["weekday"]] = entry
            days.append(entry)
        weeks.append(column)
    return weeks, days


def streaks(days):
    """Longest run of active days, and the run ending at the last active day."""
    longest = run = 0
    for day in days:
        run = run + 1 if day["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    for day in reversed(days):
        if day["count"] > 0:
            current += 1
        elif current:
            break
        # a zero on the trailing edge (today, not committed yet) is forgiven
    return current, longest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", default="porth-bot")
    parser.add_argument("--out", default="scripts/contrib.json")
    args = parser.parse_args()

    calendar = fetch(args.login)
    weeks, days = flatten(calendar)
    current, longest = streaks(days)
    busiest = max(days, key=lambda d: d["count"])

    data = {
        "login": args.login,
        "total": calendar["totalContributions"],
        "start": days[0]["date"],
        "end": days[-1]["date"],
        "max": busiest["count"],
        "busiest": busiest,
        "current_streak": current,
        "longest_streak": longest,
        "weeks": weeks,
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1) + "\n")
    print(
        f"{args.login}: {data['total']} contributions "
        f"{data['start']} to {data['end']}, "
        f"streak {current} (longest {longest}), busiest {busiest['count']}"
    )


if __name__ == "__main__":
    main()
