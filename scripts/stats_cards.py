"""Build self-hosted GitHub stats, top-languages and streak SVG cards (no third-party services)."""
import datetime, json, os, sys, urllib.request

user = os.environ.get("GH_USER", "snowjug")
token = os.environ["GITHUB_TOKEN"]
outdir = sys.argv[1] if len(sys.argv) > 1 else "."

QUERY = """query($u:String!){user(login:$u){
 name followers{totalCount} following{totalCount}
 pullRequests{totalCount} issues{totalCount}
 repositoriesContributedTo(first:1,contributionTypes:[COMMIT,PULL_REQUEST,ISSUE,REPOSITORY]){totalCount}
 repositories(ownerAffiliations:OWNER,isFork:false,first:100,orderBy:{field:PUSHED_AT,direction:DESC}){
  totalCount nodes{stargazerCount languages(first:10,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}}}
 contributionsCollection{totalCommitContributions contributionCalendar{totalContributions weeks{contributionDays{contributionCount date}}}}
}}"""
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": QUERY, "variables": {"u": user}}).encode(),
    headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
)
resp = json.load(urllib.request.urlopen(req))
if resp.get("errors"):
    sys.exit(f"GraphQL error: {resp['errors']}")
u = resp["data"]["user"]

BG, FG, ACC, MUTED = "#0d1117", "#ccd6f6", "#64ffda", "#8892b0"
FONT = "font-family=\"Segoe UI, Arial, sans-serif\""

def card(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" {FONT}>'
            f'<rect width="{w}" height="{h}" rx="14" fill="{BG}" stroke="#233554"/>'
            f'<text x="24" y="34" fill="{ACC}" font-size="17" font-weight="700">{title}</text>{body}</svg>')

def write(name, svg):
    with open(os.path.join(outdir, name), "w") as f:
        f.write(svg)

# --- stats card ---
repos = u["repositories"]["nodes"]
stars = sum(r["stargazerCount"] for r in repos)
rows = [("Total Stars", stars), ("Commits (last year)", u["contributionsCollection"]["totalCommitContributions"]),
        ("Pull Requests", u["pullRequests"]["totalCount"]), ("Issues", u["issues"]["totalCount"]),
        ("Public Repos", u["repositories"]["totalCount"]), ("Contributed To", u["repositoriesContributedTo"]["totalCount"])]
body = "".join(
    f'<text x="24" y="{70+i*26}" fill="{FG}" font-size="14">{k}</text>'
    f'<text x="300" y="{70+i*26}" text-anchor="end" fill="{ACC}" font-size="14" font-weight="700">{v}</text>'
    for i, (k, v) in enumerate(rows))
write("stats.svg", card(325, 235, f"{u['name'] or user}'s GitHub Stats", body))

# --- top languages ---
sizes, colors = {}, {}
for r in repos:
    for e in r["languages"]["edges"]:
        n = e["node"]["name"]
        sizes[n] = sizes.get(n, 0) + e["size"]
        colors[n] = e["node"]["color"] or "#8892b0"
top = sorted(sizes.items(), key=lambda x: -x[1])[:6]
tot = sum(s for _, s in top) or 1
body, y = "", 62
for n, s in top:
    pct = s / tot * 100
    body += (f'<text x="24" y="{y}" fill="{FG}" font-size="13">{n}</text>'
             f'<text x="301" y="{y}" text-anchor="end" fill="{MUTED}" font-size="13">{pct:.1f}%</text>'
             f'<rect x="24" y="{y+7}" width="277" height="8" rx="4" fill="#233554"/>'
             f'<rect x="24" y="{y+7}" width="0" height="8" rx="4" fill="{colors[n]}">'
             f'<animate attributeName="width" to="{277*pct/100:.1f}" dur="1.2s" fill="freeze"/></rect>')
    y += 38
if not top:
    body = f'<text x="24" y="70" fill="{MUTED}" font-size="14">No language data yet</text>'
write("top-langs.svg", card(325, 270, "Most Used Languages", body))

# --- streak ---
days = sorted((d["date"], d["contributionCount"])
              for w in u["contributionsCollection"]["contributionCalendar"]["weeks"] for d in w["contributionDays"])
today = datetime.date.today().isoformat()
days = [d for d in days if d[0] <= today]
longest = cur = 0
for _, c in days:
    cur = cur + 1 if c else 0
    longest = max(longest, cur)
cur = 0
for i, (d, c) in enumerate(reversed(days)):
    if c: cur += 1
    elif i == 0: continue  # today may not have contributions yet
    else: break
total = u["contributionsCollection"]["contributionCalendar"]["totalContributions"]
cols = [(total, "Total Contributions"), (cur, "Current Streak"), (longest, "Longest Streak")]
body = "".join(
    f'<text x="{66+i*110}" y="80" text-anchor="middle" fill="{ACC if i==1 else FG}" font-size="28" font-weight="700">{v}</text>'
    f'<text x="{66+i*110}" y="106" text-anchor="middle" fill="{MUTED}" font-size="12">{l}</text>'
    for i, (v, l) in enumerate(cols))
write("streak.svg", card(400, 130, "Contribution Streak", body))
print("stats cards written to", outdir)
