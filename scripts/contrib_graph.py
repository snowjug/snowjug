"""Build an animated contribution-activity graph SVG from the GitHub GraphQL API."""
import json, os, sys, urllib.request

user = os.environ.get("GH_USER", "snowjug")
token = os.environ["GITHUB_TOKEN"]
out = sys.argv[1] if len(sys.argv) > 1 else "contribution-graph.svg"

query = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
totalContributions weeks{contributionDays{contributionCount date}}}}}}"""
req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=json.dumps({"query": query, "variables": {"u": user}}).encode(),
    headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
)
cal = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
total = cal["totalContributions"]

W, H, L, R, T, B = 800, 260, 50, 20, 50, 40
mx = max(max(weeks), 1)
step = (W - L - R) / max(len(weeks) - 1, 1)
pts = [(L + i * step, H - B - (v / mx) * (H - T - B)) for i, v in enumerate(weeks)]
line = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
area = f"{L},{H-B} {line} {pts[-1][0]:.1f},{H-B}"
grid = "".join(
    f'<line x1="{L}" x2="{W-R}" y1="{H-B-f*(H-T-B):.1f}" y2="{H-B-f*(H-T-B):.1f}" stroke="#233554" stroke-dasharray="4 4"/>'
    f'<text x="{L-8}" y="{H-B-f*(H-T-B)+4:.1f}" text-anchor="end" fill="#8892b0" font-size="11">{round(mx*f)}</text>'
    for f in (0, .25, .5, .75, 1)
)
dots = "".join(
    f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.5" fill="#64ffda" opacity="0"><animate attributeName="opacity" to="1" begin="{2+i*0.03:.2f}s" dur="0.3s" fill="freeze"/></circle>'
    for i, (x, y) in enumerate(pts) if weeks[i]
)
svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Segoe UI, Arial, sans-serif">
<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#64ffda" stop-opacity=".45"/><stop offset="1" stop-color="#64ffda" stop-opacity="0"/></linearGradient></defs>
<rect width="{W}" height="{H}" rx="14" fill="#0d1117"/>
<text x="{L}" y="30" fill="#64ffda" font-size="16" font-weight="700">{user}'s Contribution Graph</text>
<text x="{W-R}" y="30" text-anchor="end" fill="#8892b0" font-size="13">{total} contributions in the last year</text>
{grid}
<polygon points="{area}" fill="url(#g)" opacity="0"><animate attributeName="opacity" to="1" begin="1.5s" dur="1s" fill="freeze"/></polygon>
<polyline points="{line}" fill="none" stroke="#64ffda" stroke-width="2.5" stroke-linejoin="round" pathLength="1" stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" from="1" to="0" dur="2.5s" fill="freeze"/></polyline>
{dots}
<text x="{L}" y="{H-12}" fill="#8892b0" font-size="11">weekly contributions</text>
</svg>"""
open(out, "w").write(svg)
print("wrote", out, "weeks:", len(weeks), "total:", total)
