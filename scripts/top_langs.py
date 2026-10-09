import html, json, os, sys, urllib.error, urllib.request

API = "https://api.github.com"
USER = os.environ.get("GH_USER", "ygttncy")
ORGS = [o.strip() for o in os.environ.get("GH_ORGS", "Viora-Software").split(",") if o.strip()]
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "profile/top-langs.svg")
TOP_N = min(int(os.environ.get("TOP_N", "8")), 8)  # kart 2x4 = en fazla 8 dil
split = lambda k: {x.strip().lower() for x in os.environ.get(k, "").split(",") if x.strip()}
EXCLUDE_LANGS, EXCLUDE_REPOS = split("EXCLUDE_LANGS"), split("EXCLUDE_REPOS")
INCLUDE_FORKS = os.environ.get("INCLUDE_FORKS", "false").lower() == "true"

COLORS = {
    "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "C#": "#178600", "PHP": "#4F5D95",
    "Java": "#b07219", "CSS": "#663399", "SCSS": "#c6538c", "HTML": "#e34c26", "Go": "#00ADD8",
    "Python": "#3572A5", "Shell": "#89e051", "Dockerfile": "#384d54", "Blade": "#f7523f",
    "Vue": "#41b883", "PLpgSQL": "#e38c00", "Razor": "#512bd4", "Dart": "#00B4AB",
    "Kotlin": "#A97BFF", "C": "#555555", "C++": "#f34b7d", "Batchfile": "#C1F12E",
    "Handlebars": "#f7931e", "MDX": "#fcb32c", "Astro": "#ff5a03", "Svelte": "#ff3e00",
}


def get(url):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "top-langs-generator"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as r:
        return json.load(r)


def paged(url):
    page, sep = 1, "&" if "?" in url else "?"
    while True:
        data = get(f"{url}{sep}per_page=100&page={page}")
        yield from data
        if len(data) < 100:
            return
        page += 1


def collect_repos():
    owners = {USER.lower(), *[o.lower() for o in ORGS]}
    repos = {}
    if TOKEN:
        url = f"{API}/user/repos?affiliation=owner,collaborator,organization_member"
        for r in paged(url):
            if r["owner"]["login"].lower() in owners:
                repos[r["full_name"]] = r
    else:
        sources = [f"{API}/users/{USER}/repos?type=owner"] + [f"{API}/orgs/{o}/repos?type=public" for o in ORGS]
        for url in sources:
            try:
                for r in paged(url):
                    repos[r["full_name"]] = r
            except urllib.error.HTTPError as e:
                print(f"warn: {url} -> HTTP {e.code}", file=sys.stderr)
    return repos


def render(rows):
    W, H, BW = 304, 195, 254
    total = sum(b for _, b in rows) or 1
    rows = [(n, b, b / total * 100) for n, b in rows]
    bars, x = "", 0.0
    for n, _, p in rows:
        w = round(p * BW / 100, 2)
        bars += f'<rect mask="url(#m)" x="{round(x, 2)}" y="0" width="{w}" height="8" fill="{COLORS.get(n, "#8b949e")}"/>'
        x += w
    legend = ""
    for i, (n, _, p) in enumerate(rows):
        cx, ry = (0, i * 25) if i < 4 else (150, (i - 4) * 25)
        legend += (f'<g transform="translate({cx},{ry})"><g class="stagger" style="animation-delay:{450 + i * 150}ms">'
                   f'<circle cx="5" cy="6" r="5" fill="{COLORS.get(n, "#8b949e")}"/>'
                   f'<text class="lang-name" x="15" y="10">{html.escape(n)} {p:.2f}%</text></g></g>')
    desc = html.escape(", ".join(f"{n} {p:.2f}%" for n, _, p in rows))
    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="titleId descId">
<title id="titleId">Most Used Languages</title>
<desc id="descId">{desc}</desc>
<style>
.header{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:#FF6B1A;animation:fade .8s ease-in-out forwards}}
@supports(-moz-appearance:auto){{.header{{font-size:15.5px}}}}
.lang-name{{font:400 11px 'Segoe UI',Ubuntu,Sans-Serif;fill:#FAFAFA}}
.stagger{{opacity:0;animation:fade .3s ease-in-out forwards}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
</style>
<rect x="0.5" y="0.5" rx="10" width="{W - 1}" height="{H - 1}" fill="#111111" stroke="#2A2A2A"/>
<text x="25" y="35" class="header">Most Used Languages</text><g transform="translate(25,55)"><mask id="m"><rect x="0" y="0" width="{BW}" height="8" rx="5" fill="white"/></mask>{bars}<g transform="translate(0,25)">{legend}</g></g>
</svg>
'''


def main():
    repos = collect_repos()
    totals, counted = {}, {}
    for full, r in repos.items():
        if (r["fork"] and not INCLUDE_FORKS) or r["name"].lower() in EXCLUDE_REPOS or full.lower() in EXCLUDE_REPOS:
            continue
        owner = r["owner"]["login"]
        counted[owner] = counted.get(owner, 0) + 1
        try:
            langs = get(r["languages_url"])
        except urllib.error.HTTPError as e:
            print(f"warn: {full} languages -> HTTP {e.code}", file=sys.stderr)
            continue
        for lang, size in langs.items():
            if lang.lower() not in EXCLUDE_LANGS:
                totals[lang] = totals.get(lang, 0) + size
    top = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[:TOP_N]
    if not top:
        sys.exit("No language data found; check GH_USER / GH_ORGS / GH_TOKEN.")
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(top))
    print("repos counted per owner:", counted)
    print("languages:", [n for n, _ in top])


if __name__ == "__main__":
    main()
