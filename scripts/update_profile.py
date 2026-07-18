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

<img width="100%" height="120" src="https://capsule-render.vercel.app/api?type=rect&color=0:1a1b27,100:283457" />

</div>

<h1 align="center">AutoScout</h1>
<p align="center">An autonomous system that scouts real problems in agentic AI and builds solutions for them — every day, without me touching it.</p>

<div align="center">
<img src="https://readme-typing-svg.demolab.com/?font=Fira+Code&weight=400&size=15&duration=3000&pause=1200&color=7AA2F7&center=true&vCenter=true&width=520&lines=Scouting+HN%2C+GitHub%2C+Stack+Overflow;Building+%2B+advancing+projects+daily;Gemini+%2B+Groq%2C+running+while+I+sleep" alt="Typing SVG" />
</div>

<br>

Three processes run independently, every day. **Scout** pulls real pain points from the agentic-AI community — agent orchestration, memory, evals, guardrails, MCP. **Generate** builds a new prototype targeting the strongest signal, in whatever language actually fits it. **Advance** — two separate engines, a Gemini-powered one in [AutoScout-Lab](https://github.com/{owner}/{lab_repo}) and a Groq-powered one in [AutoScout-Engine](https://github.com/{owner}/{engine_repo}) — each push one existing repo a genuine step further, grounded in live research.

<br>

<div align="center">

<table>
<tr><td align="center"><b>{days_running}</b><br><sub>days running</sub></td>
<td align="center"><b>{total_repos}</b><br><sub>repos generated</sub></td>
<td align="center"><b>{gemini_passes}</b><br><sub>Gemini passes</sub></td>
<td align="center"><b>{groq_passes}</b><br><sub>Groq passes</sub></td></tr>
</table>

<sub>auto-updated daily · last refreshed {updated}{digest_suffix}</sub>

</div>

<br>

<div align="center">

![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Gemini](https://img.shields.io/badge/-Gemini-8E75B2?style=flat-square&logo=googlegemini&logoColor=white)
![Groq](https://img.shields.io/badge/-Groq-F55036?style=flat-square&logoColor=white)
![Pydantic](https://img.shields.io/badge/-Pydantic-E92063?style=flat-square&logo=pydantic&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/-GitHub%20Actions-2088FF?style=flat-square&logo=githubactions&logoColor=white)

</div>

<br>

<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake.svg" />
  <img alt="contribution snake animation" src="https://raw.githubusercontent.com/{owner}/{owner}/output/github-contribution-grid-snake.svg" />
</picture>

</div>

<br>

<div align="center">

<a href="https://www.linkedin.com/in/sathiyasendinath/"><img src="https://img.shields.io/badge/-LinkedIn-0A66C2?style=flat-square&logo=linkedin&logoColor=white" /></a>
<a href="mailto:sendilnathsathiya@gmail.com"><img src="https://img.shields.io/badge/-Email-D14836?style=flat-square&logo=gmail&logoColor=white" /></a>

</div>

<br>

<div align="center">
<img width="100%" height="80" src="https://capsule-render.vercel.app/api?type=rect&color=0:283457,100:1a1b27" />
</div>
"""


def render(stats: dict) -> str:
    digest_suffix = (f" · [today's activity]({stats['digest_url']})"
                     if stats["digest_url"] else "")
    return README_TEMPLATE.format(owner=OWNER, lab_repo=LAB_REPO,
                                  engine_repo=ENGINE_REPO,
                                  digest_suffix=digest_suffix, **stats)


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
