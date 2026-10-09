import html, json, os, sys, urllib.request

API = "https://api.github.com/graphql"
USER = os.environ.get("GH_USER", "ygttncy")
ORGS = [o.strip() for o in os.environ.get("GH_ORGS", "Viora-Software").split(",") if o.strip()]
TOKEN = os.environ.get("GH_TOKEN", "")
OUT = os.environ.get("OUT", "profile/stats.svg")

if not TOKEN:
    sys.exit("GH_TOKEN gerekli (repo, read:org, read:user yetkili token).")


def gql(query, **variables):
    req = urllib.request.Request(
        API,
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"Bearer {TOKEN}", "User-Agent": "stats-card-generator"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if data.get("errors"):
        sys.exit(f"GraphQL error: {data['errors']}")
    return data["data"]


def total_commits():
    """Tüm yıllardaki commit'ler (private katkılar dahil)."""
    years = gql("""query($u:String!){user(login:$u){contributionsCollection{contributionYears}}}""",
                u=USER)["user"]["contributionsCollection"]["contributionYears"]
    total = 0
    for y in years:
        c = gql("""query($u:String!,$f:DateTime!,$t:DateTime!){user(login:$u){
                   contributionsCollection(from:$f,to:$t){totalCommitContributions}}}""",
                u=USER, f=f"{y}-01-01T00:00:00Z", t=f"{y}-12-31T23:59:59Z")["user"]["contributionsCollection"]
        total += c["totalCommitContributions"]
    return total


def stars():
    """Kendi repoların + organizasyon repolarının toplam yıldızı (fork'lar hariç)."""
    total, seen = 0, set()
    owners = [("user", USER)] + [("organization", o) for o in ORGS]
    for kind, login in owners:
        cursor = None
        while True:
            d = gql(f"""query($l:String!,$c:String){{{kind}(login:$l){{
                       repositories(first:100,after:$c,isFork:false,ownerAffiliations:OWNER){{
                         nodes{{nameWithOwner stargazerCount}} pageInfo{{hasNextPage endCursor}}}}}}}}""",
                    l=login, c=cursor)[kind]["repositories"]
            for n in d["nodes"]:
                if n["nameWithOwner"] not in seen:
                    seen.add(n["nameWithOwner"])
                    total += n["stargazerCount"]
            if not d["pageInfo"]["hasNextPage"]:
                break
            cursor = d["pageInfo"]["endCursor"]
    return total


def counts():
    u = gql("""query($u:String!){user(login:$u){
               pullRequests{totalCount}
               issues{totalCount}
               repositoriesContributedTo(contributionTypes:[COMMIT,ISSUE,PULL_REQUEST,REPOSITORY]){totalCount}
             }}""", u=USER)["user"]
    return u["pullRequests"]["totalCount"], u["issues"]["totalCount"], u["repositoriesContributedTo"]["totalCount"]


ICONS = {
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25zm0 2.445L6.615 5.5a.75.75 0 01-.564.41l-3.097.45 2.24 2.184a.75.75 0 01.216.664l-.528 3.084 2.769-1.456a.75.75 0 01.698 0l2.77 1.456-.53-3.084a.75.75 0 01.216-.664l2.24-2.183-3.096-.45a.75.75 0 01-.564-.41L8 2.694v.001z",
    "commit": "M1.643 3.143L.427 1.927A.25.25 0 000 2.104V5.75c0 .138.112.25.25.25h3.646a.25.25 0 00.177-.427L2.715 4.215a6.5 6.5 0 11-1.18 4.458.75.75 0 10-1.493.154 8.001 8.001 0 101.6-5.684zM7.75 4a.75.75 0 01.75.75v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5A.75.75 0 017.75 4z",
    "pr": "M7.177 3.073L9.573.677A.25.25 0 0110 .854v4.792a.25.25 0 01-.427.177L7.177 3.427a.25.25 0 010-.354zM3.75 2.5a.75.75 0 100 1.5.75.75 0 000-1.5zm-2.25.75a2.25 2.25 0 113 2.122v5.256a2.251 2.251 0 11-1.5 0V5.372A2.25 2.25 0 011.5 3.25zM11 2.5h-1V4h1a1 1 0 011 1v5.628a2.251 2.251 0 101.5 0V5A2.5 2.5 0 0011 2.5zm1 10.25a.75.75 0 111.5 0 .75.75 0 01-1.5 0zM3.75 12a.75.75 0 100 1.5.75.75 0 000-1.5z",
    "issue": "M8 1.5a6.5 6.5 0 100 13 6.5 6.5 0 000-13zM0 8a8 8 0 1116 0A8 8 0 010 8zm9 3a1 1 0 11-2 0 1 1 0 012 0zm-.25-6.25a.75.75 0 00-1.5 0v3.5a.75.75 0 001.5 0v-3.5z",
    "repo": "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8zM5 12.25v3.25a.25.25 0 00.4.2l1.45-1.087a.25.25 0 01.3 0L8.6 15.7a.25.25 0 00.4-.2v-3.25a.25.25 0 00-.25-.25h-3.5a.25.25 0 00-.25.25z",
}


def render(rows):
    W, H = 304, 195
    items = ""
    for i, (icon, label, value) in enumerate(rows):
        items += (f'<g transform="translate(25,{i * 25})"><g class="stagger" style="animation-delay:{450 + i * 150}ms">'
                  f'<svg class="icon" viewBox="0 0 16 16" width="16" height="16"><path fill-rule="evenodd" d="{ICONS[icon]}"/></svg>'
                  f'<text class="stat" x="25" y="12.5">{html.escape(label)}</text>'
                  f'<text class="stat" x="224" y="12.5">{value:,}</text></g></g>')
    desc = html.escape(", ".join(f"{l} {v}" for _, l, v in rows))
    return f'''<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="titleId descId">
<title id="titleId">{html.escape(USER)}'s GitHub Stats</title>
<desc id="descId">{desc}</desc>
<style>
.header{{font:600 18px 'Segoe UI',Ubuntu,Sans-Serif;fill:#FF6B1A;animation:fade .8s ease-in-out forwards}}
@supports(-moz-appearance:auto){{.header{{font-size:15.5px}}}}
.stat{{font:700 14px 'Segoe UI',Ubuntu,'Helvetica Neue',Sans-Serif;fill:#FAFAFA}}
@supports(-moz-appearance:auto){{.stat{{font-size:12px}}}}
.icon{{fill:#FF6B1A}}
.stagger{{opacity:0;animation:fade .3s ease-in-out forwards}}
@keyframes fade{{from{{opacity:0}}to{{opacity:1}}}}
</style>
<rect x="0.5" y="0.5" rx="10" width="{W - 1}" height="{H - 1}" fill="#111111" stroke="#2A2A2A"/>
<text x="25" y="35" class="header">{html.escape(USER)}'s GitHub Stats</text>
<g transform="translate(0,55)">{items}</g>
</svg>
'''


def main():
    prs, issues, contributed = counts()
    rows = [
        ("star", "Total Stars Earned:", stars()),
        ("commit", "Total Commits:", total_commits()),
        ("pr", "Total PRs:", prs),
        ("issue", "Total Issues:", issues),
        ("repo", "Contributed to (last year):", contributed),
    ]
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(rows))
    print("stats:", {l: v for _, l, v in rows})


if __name__ == "__main__":
    main()
