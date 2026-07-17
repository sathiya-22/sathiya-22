#!/usr/bin/env python3
"""Refresh the GitHub profile README with live AutoScout stats.

Reads AutoScout-Lab's and AutoScout-Engine's registries directly (both
public repos, no auth needed for that part) and the latest digest issue,
then rewrites README.md and commits only if the content actually changed.
"""

import json
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

GITHUB_API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"
OWNER = "sathiya-22"
LAB_REPO = "AutoScout-Lab"
ENGINE_REPO = "AutoScout-Engine"
START_DATE = date(2026, 7, 7)  # AutoScout-Lab's first generated repo


def _get_json(url: str, headers: dict | None = None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def _get_jsonl(url: str) -> list[dict]:
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise
    return [json.loads(line) for line in text.splitlines() if line.strip()]


def gather_stats() -> dict:
    lab_registry = _get_jsonl(f"{RAW}/{OWNER}/{LAB_REPO}/main/repos/registry.jsonl")
    engine_registry = _get_jsonl(f"{RAW}/{OWNER}/{ENGINE_REPO}/main/state/registry.jsonl")

    days_running = (date.today() - START_DATE).days + 1
    total_repos = len(lab_registry)
    gemini_passes = sum(e.get("iterations", 0) for e in lab_registry)
    groq_passes = sum(e.get("advancement_passes", 0) for e in engine_registry)

    # Public repo — listing issues works fine unauthenticated for this
    # low a call volume (once/day).
    issues = _get_json(
        f"{GITHUB_API}/repos/{OWNER}/{LAB_REPO}/issues?state=all&per_page=5"
        "&sort=created&direction=desc") or []
    digest_url = next((i["html_url"] for i in issues
                       if i.get("title", "").startswith("Activity — ")), None)

    return {
        "days_running": days_running,
        "total_repos": total_repos,
        "gemini_passes": gemini_passes,
        "groq_passes": groq_passes,
        "digest_url": digest_url,
        "updated": date.today().isoformat(),
    }


README_TEMPLATE = """\
<div align="center">

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:1a1b27,50:283457,100:7aa2f7&height=200&section=header&text=AutoScout&fontSize=60&fontColor=c0caf5&animation=fadeIn&fontAlignY=35&desc=Autonomous%20Agentic-AI%20Builder&descAlignY=55&descSize=20&descColor=7aa2f7" />

<a href="https://github.com/{owner}">
  <img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=500&size=22&duration=3000&pause=1000&color=7AA2F7&center=true&vCenter=true&width=650&lines=Scouting+real+problems+from+HN%2C+GitHub%2C+Stack+Overflow;Generating+%2B+advancing+projects+%E2%80%94+every+single+day;Gemini+%2B+Groq+powered%2C+running+while+I+sleep" alt="Typing SVG" />
</a>

</div>

### 🤖 AutoScout — a system that builds while I sleep

Every day, three independent processes run without me touching them:

1. **Scout** — pulls real pain points from Hacker News, GitHub, and Stack \
Overflow, filtered to agentic AI (agent orchestration, memory, evals, \
guardrails, MCP, multi-agent coordination).
2. **Generate** — builds a new prototype repo targeting the highest-signal \
problem, in whatever language/format actually fits it.
3. **Advance** — two independent engines each pick one existing repo per \
day and push it one genuine step further, backed by live research:
   - a Gemini-powered loop in [AutoScout-Lab](https://github.com/{owner}/{lab_repo})
   - a Groq-powered loop in [AutoScout-Engine](https://github.com/{owner}/{engine_repo})

**📊 Live stats** (auto-updated daily, last refreshed {updated}):

| | |
|---|---|
| Running since | 2026-07-07 ({days_running} days) |
| Repos generated | {total_repos} |
| Gemini maturation passes | {gemini_passes} |
| Groq advancement passes | {groq_passes} |
{digest_row}

🔗 [AutoScout-Lab](https://github.com/{owner}/{lab_repo}) (orchestrator + \
scout + generator) · [AutoScout-Engine](https://github.com/{owner}/{engine_repo}) \
(deep research-backed advancement)

<br>

<div align="center">

<img height="165em" src="https://github-stats-extended.vercel.app/api?username={owner}&show_icons=true&theme=tokyonight&hide_border=true&count_private=true&rank_icon=github" />
<img height="165em" src="https://streak-stats.demolab.com/?user={owner}&theme=tokyonight&hide_border=true" />

<img width="55%" src="https://github-stats-extended.vercel.app/api/top-langs/?username={owner}&layout=compact&theme=tokyonight&hide_border=true" />

</div>

<br>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake.svg" />
  <img alt="contribution snake animation" src="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake.svg" />
</picture>

</div>

<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:7aa2f7,50:283457,100:1a1b27&height=120&section=footer" />
"""


def render(stats: dict) -> str:
    digest_row = (f"| Today's activity | [→ digest]({stats['digest_url']}) |"
                 if stats["digest_url"] else "")
    return README_TEMPLATE.format(owner=OWNER, lab_repo=LAB_REPO,
                                  engine_repo=ENGINE_REPO,
                                  digest_row=digest_row, **stats)


def main() -> None:
    stats = gather_stats()
    content = render(stats)
    print(f"Stats: {stats}")

    readme_path = Path(__file__).parent.parent / "README.md"
    if readme_path.exists() and readme_path.read_text(encoding="utf-8") == content:
        print("No change.")
        return

    readme_path.write_text(content, encoding="utf-8")
    print("README.md updated.")


if __name__ == "__main__":
    main()
