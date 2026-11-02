#!/usr/bin/env python3
"""Refreshes the profile README and the animated stat SVGs from the GitHub API.

Usage:
  python scripts/update_profile.py          # live run (needs GH_TOKEN)
  python scripts/update_profile.py --demo   # offline placeholder using a few verified facts
"""
import json, os, re, sys, urllib.request
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape as esc

USER = os.environ.get("GH_USER", "AmlanShanker")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
ROOT = Path(os.environ.get("PROFILE_ROOT", Path(__file__).resolve().parent.parent))
FONT = '"Palatino Linotype","Book Antiqua",Palatino,Georgia,serif'

REPO_FIELDS = """name description url homepageUrl stargazerCount forkCount isFork isArchived
  pushedAt createdAt primaryLanguage{name color}
  languages(first:6,orderBy:{field:SIZE,direction:DESC}){edges{size node{name color}}}
  repositoryTopics(first:6){nodes{topic{name}}}"""
CONTRIB = """contributionsCollection{totalCommitContributions totalPullRequestContributions
  totalIssueContributions totalRepositoryContributions
  contributionCalendar{totalContributions weeks{firstDay contributionDays{contributionCount}}}}"""
QUERY = """query($login:String!){user(login:$login){name login bio location company websiteUrl
  createdAt followers{totalCount} following{totalCount} starredRepositories{totalCount}
  repositories(first:100,ownerAffiliation:OWNER,privacy:PUBLIC,orderBy:{field:PUSHED_AT,direction:DESC})
  {totalCount nodes{%s}} %s}}"""


def gql(with_contrib=True):
    q = QUERY % (REPO_FIELDS, CONTRIB if with_contrib else "")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": q, "variables": {"login": USER}}).encode(),
        headers={"Authorization": "bearer " + TOKEN, "Content-Type": "application/json", "User-Agent": "profile-updater"},
    )
    with urllib.request.urlopen(req, timeout=40) as r:
        d = json.load(r)
    if d.get("errors") or not (d.get("data") or {}).get("user"):
        raise RuntimeError(d.get("errors"))
    return d["data"]["user"]


def fetch():
    try:
        return gql(True)
    except Exception as e:
        print("contribution query failed, retrying without it:", e)
        return gql(False)


def demo_user():
    """Only facts read from the public profile page. Everything else stays unknown."""
    pins = [
        ("GenZenius-AI-powered-SAAS", "GenZenius is an AI-powered SaaS platform with Article Generation, Blog Title Suggestions, Image Generation, Background Removal, Object Removal, and Resume tools.", "JavaScript"),
        ("MERN-Stack-Finance-Dashboard-App", "A Finance Dashboard Created Using MERN Stack", "JavaScript"),
        ("Expense-Tracker-MERN-Stack", "An Expense Tracker Created Using MERN Stack", "JavaScript"),
        ("Social-Media-MERN-Stack", "A Social Media dynamic application created using MERN Stack", "JavaScript"),
        ("NotesApp", "A Notes App created in Android Studio using Kotlin and XML", "Kotlin"),
        ("Movie-ticket-booking-system", "A responsive and interactive web application that simplifies the movie ticket booking process.", "HTML"),
    ]
    nodes = [{"name": n, "description": d, "url": "https://github.com/%s/%s" % (USER, n), "homepageUrl": None,
              "stargazerCount": 1, "forkCount": 0, "isFork": False, "isArchived": False, "pushedAt": None, "createdAt": None,
              "primaryLanguage": {"name": l, "color": None}, "languages": {"edges": []}, "repositoryTopics": {"nodes": []}}
             for n, d, l in pins]
    return {"name": "Amlan Shanker", "login": USER, "bio": None, "location": None, "company": None, "websiteUrl": None,
            "createdAt": None, "followers": {"totalCount": 1}, "following": {"totalCount": 0},
            "starredRepositories": {"totalCount": 8}, "repositories": {"totalCount": 25, "nodes": nodes}}


def fmt(n):
    return "\u2014" if n is None else "{:,}".format(n)


def when(s, f="%b %Y"):
    if not s:
        return "\u2014"
    return datetime.strptime(s[:10], "%Y-%m-%d").strftime(f)


# ---------------------------------------------------------------- stats.svg
def build_stats(u):
    own = [r for r in u["repositories"]["nodes"] if not r["isFork"]]
    stars = sum(r["stargazerCount"] for r in own)
    forks = sum(r["forkCount"] for r in own)
    cc = u.get("contributionsCollection")
    cal = cc["contributionCalendar"]["totalContributions"] if cc else None
    tiles = [
        ("REPOSITORIES", u["repositories"]["totalCount"]), ("FOLLOWERS", u["followers"]["totalCount"]),
        ("FOLLOWING", u["following"]["totalCount"]), ("STARS EARNED", stars), ("STARRED", u["starredRepositories"]["totalCount"]),
        ("CONTRIBUTIONS", cal), ("COMMITS", cc["totalCommitContributions"] if cc else None),
        ("PULL REQUESTS", cc["totalPullRequestContributions"] if cc else None),
        ("ISSUES", cc["totalIssueContributions"] if cc else None), ("FORKS EARNED", forks),
    ]
    langs = {}
    for r in own:
        for e in r["languages"]["edges"]:
            n = e["node"]
            langs.setdefault(n["name"], [0])[0] += e["size"]
    if not langs:
        for r in own:
            pl = r.get("primaryLanguage")
            if pl:
                langs.setdefault(pl["name"], [0])[0] += 1
    total = sum(v[0] for v in langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1][0])[:6]
    palette = ["#e08a3c", "#c9ab7c", "#a8703d", "#f0c27a", "#8a5230", "#6d4020"]
    W, H = 1000, 340
    o = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="GitHub statistics for %s">' % (W, H, W, H, esc(USER)),
         '<defs><linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c120b"/><stop offset="1" stop-color="#2b190d"/></linearGradient></defs>',
         '<rect width="%d" height="%d" rx="10" fill="url(#bg)" stroke="#5a3a1f"/>' % (W, H),
         '<g font-family=\'%s\'><text x="36" y="44" font-size="18" letter-spacing="6" fill="#ffc98a">GITHUB \u00b7 @%s</text>' % (FONT, esc(USER)),
         '<circle cx="964" cy="38" r="4" fill="#7bd88f"><animate attributeName="r" values="3;6;3" dur="2s" repeatCount="indefinite"/><animate attributeName="opacity" values="1;.3;1" dur="2s" repeatCount="indefinite"/></circle>']
    for i, (label, val) in enumerate(tiles):
        x = 36 + (i % 5) * 188
        y = 66 + (i // 5) * 86
        o.append('<g opacity="0"><animate attributeName="opacity" values="0;1" dur=".7s" begin="%.1fs" fill="freeze"/>'
                 '<animateTransform attributeName="transform" type="translate" values="0 14;0 0" dur=".7s" begin="%.1fs" fill="freeze"/>'
                 '<rect x="%d" y="%d" width="176" height="72" rx="6" fill="#241609" stroke="#4a3320"/><rect x="%d" y="%d" width="3" height="72" fill="#e08a3c"/>'
                 '<text x="%d" y="%d" font-size="30" fill="#f6ead6">%s</text><text x="%d" y="%d" font-size="10" letter-spacing="3" fill="#c9ab7c">%s</text></g>'
                 % (i * .1, i * .1, x, y, x, y, x + 18, y + 38, fmt(val), x + 18, y + 58, label))
    o.append('<text x="36" y="262" font-size="12" letter-spacing="4" fill="#c9ab7c">LANGUAGES BY CODE SIZE</text>')
    x = 36.0
    for i, (n, (sz,)) in enumerate(top):
        w = 928.0 * sz / total
        o.append('<rect x="%.1f" y="272" width="0" height="14" fill="%s"><animate attributeName="width" values="0;%.1f" dur="1.2s" begin="%.1fs" fill="freeze"/></rect>' % (x, palette[i], max(w - 2, 1), 1.0 + i * .15))
        x += w
    lx = 36
    for i, (n, (sz,)) in enumerate(top):
        label = "%s %.1f%%" % (n, 100.0 * sz / total)
        o.append('<rect x="%d" y="302" width="10" height="10" rx="2" fill="%s"/><text x="%d" y="311" font-size="12" fill="#f6ead6">%s</text>' % (lx, palette[i], lx + 16, esc(label)))
        lx += 34 + 7 * len(label)
    o.append("</g></svg>")
    return "".join(o)


# ---------------------------------------------------------------- dunes.svg
def build_dunes(u):
    cc = u.get("contributionsCollection")
    W, H = 1000, 270
    head = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d" role="img" aria-label="Contribution graph">' % (W, H, W, H),
            '<defs><linearGradient id="sk" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c120b"/><stop offset="1" stop-color="#7a4624"/></linearGradient>'
            '<linearGradient id="sd" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e8a45a"/><stop offset="1" stop-color="#6d4020"/></linearGradient>'
            '<radialGradient id="gl"><stop offset="0" stop-color="#ffdca4" stop-opacity=".8"/><stop offset="1" stop-color="#ffdca4" stop-opacity="0"/></radialGradient></defs>',
            '<rect width="%d" height="%d" rx="10" fill="url(#sk)" stroke="#5a3a1f"/>' % (W, H)]
    t = '<g font-family=\'%s\'>' % FONT
    if not cc:
        return "".join(head) + t + ('<text x="36" y="44" font-size="16" letter-spacing="6" fill="#ffc98a">CONTRIBUTIONS</text>'
            '<path d="M0,200 Q250,180 500,200 T1000,200 L1000,270 L0,270Z" fill="url(#sd)" opacity=".6"/>'
            '<text x="500" y="150" text-anchor="middle" font-size="15" letter-spacing="5" fill="#f6ead6">SYNC PENDING \u00b7 FILLS IN AFTER THE FIRST WORKFLOW RUN</text></g></svg>')
    weeks = cc["contributionCalendar"]["weeks"]
    vals = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in weeks]
    n = len(vals)
    mx = max(vals) or 1
    xs = [40 + i * 920.0 / max(n - 1, 1) for i in range(n)]
    ys = [210 - 120.0 * v / mx for v in vals]
    d = "M%.1f,%.1f" % (xs[0], ys[0])
    for i in range(1, n):
        mxp, myp = (xs[i - 1] + xs[i]) / 2, (ys[i - 1] + ys[i]) / 2
        d += " Q%.1f,%.1f %.1f,%.1f" % (xs[i - 1], ys[i - 1], mxp, myp)
    d += " L%.1f,%.1f" % (xs[-1], ys[-1])
    pk = vals.index(max(vals))
    o = list(head) + [t,
        '<text x="36" y="44" font-size="16" letter-spacing="6" fill="#ffc98a">CONTRIBUTIONS \u00b7 LAST 12 MONTHS</text>',
        '<text x="964" y="44" text-anchor="end" font-size="26" fill="#f6ead6">%s</text>' % fmt(cc["contributionCalendar"]["totalContributions"]),
        '<circle cx="%.1f" cy="%.1f" r="70" fill="url(#gl)"><animate attributeName="r" values="62;78;62" dur="5s" repeatCount="indefinite"/></circle>' % (xs[pk], ys[pk]),
        '<path d="%s L%.1f,270 L%.1f,270Z" fill="url(#sd)" opacity="0"><animate attributeName="opacity" values="0;.9" dur="1.6s" begin="1.2s" fill="freeze"/></path>' % (d, xs[-1], xs[0]),
        '<path d="%s" pathLength="1" fill="none" stroke="#ffd9a0" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="1" stroke-dashoffset="1"><animate attributeName="stroke-dashoffset" values="1;0" dur="2.6s" fill="freeze"/></path>' % d,
        '<circle cx="%.1f" cy="%.1f" r="4" fill="#fff4de"><animate attributeName="r" values="3;6;3" dur="2s" repeatCount="indefinite"/></circle>' % (xs[pk], ys[pk]),
        '<text x="%.1f" y="%.1f" text-anchor="middle" font-size="11" letter-spacing="2" fill="#fff4de">PEAK WEEK \u00b7 %d</text>' % (xs[pk], max(ys[pk] - 14, 60), vals[pk])]
    last = None
    for i, w in enumerate(weeks):
        m = w["firstDay"][5:7]
        if m != last:
            last = m
            o.append('<text x="%.1f" y="258" font-size="10" letter-spacing="2" fill="#f0d3a0">%s</text>' % (xs[i], datetime.strptime(w["firstDay"], "%Y-%m-%d").strftime("%b").upper()))
    o.append("</g></svg>")
    return "".join(o)


# ---------------------------------------------------------------- README blocks
def facts_md(u):
    own = [r for r in u["repositories"]["nodes"] if not r["isFork"]]
    cc = u.get("contributionsCollection")
    rows = [("Name", u.get("name") or u["login"]), ("Username", "[@%s](https://github.com/%s)" % (u["login"], u["login"])),
            ("Bio", u.get("bio")), ("Location", u.get("location")), ("Company", u.get("company")),
            ("Website", u.get("websiteUrl")), ("Joined GitHub", when(u.get("createdAt")) if u.get("createdAt") else None),
            ("Public repositories", fmt(u["repositories"]["totalCount"])), ("Followers", fmt(u["followers"]["totalCount"])),
            ("Following", fmt(u["following"]["totalCount"])), ("Starred repositories", fmt(u["starredRepositories"]["totalCount"])),
            ("Stars earned", fmt(sum(r["stargazerCount"] for r in own)) if u["repositories"]["nodes"] else None),
            ("Contributions (12 months)", fmt(cc["contributionCalendar"]["totalContributions"]) if cc else None)]
    out = ["| Detail | Value |", "| :-- | :-- |"]
    out += ["| %s | %s |" % (k, str(v).replace("|", "\\|")) for k, v in rows if v not in (None, "", "\u2014")]
    return "\n".join(out)


def repos_md(u):
    nodes = u["repositories"]["nodes"]
    own = [r for r in nodes if not r["isFork"]]
    out = ["| Repository | Description | Language | \u2605 | Forks | Last push |", "| :-- | :-- | :-- | :-: | :-: | :-- |"]
    for r in own:
        pl = (r.get("primaryLanguage") or {}).get("name", "\u2014")
        desc = (r.get("description") or "\u2014").replace("|", "\\|").replace("\n", " ")
        nm = "[**%s**](%s)%s" % (r["name"], r["url"], " (archived)" if r["isArchived"] else "")
        out.append("| %s | %s | %s | %d | %d | %s |" % (nm, desc, pl, r["stargazerCount"], r["forkCount"], when(r.get("pushedAt"))))
    forks = [r for r in nodes if r["isFork"]]
    if forks:
        out += ["", "<details><summary>Forked repositories (%d)</summary>" % len(forks), ""]
        out += ["- [%s](%s) \u2014 %s" % (r["name"], r["url"], (r.get("description") or "no description").replace("\n", " ")) for r in forks]
        out += ["", "</details>"]
    if u["repositories"]["totalCount"] > len(nodes):
        out.append("\n_Showing the %d most recently pushed of %d public repositories._" % (len(nodes), u["repositories"]["totalCount"]))
    return "\n".join(out)


def sub(text, tag, body):
    pat = re.compile(r"(<!--%s:START-->)(.*?)(<!--%s:END-->)" % (tag, tag), re.S)
    return pat.sub(lambda m: m.group(1) + "\n" + body + "\n" + m.group(3), text)


def main():
    demo = "--demo" in sys.argv
    if demo:
        u = demo_user()
    else:
        if not TOKEN:
            sys.exit("GH_TOKEN is not set")
        u = fetch()
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets" / "stats.svg").write_text(build_stats(u), encoding="utf-8")
    (ROOT / "assets" / "dunes.svg").write_text(build_dunes(u), encoding="utf-8")
    rd = ROOT / "README.md"
    t = rd.read_text(encoding="utf-8")
    t = sub(t, "FACTS", facts_md(u))
    t = sub(t, "REPOS", repos_md(u))
    rd.write_text(t, encoding="utf-8")
    print("updated for", u["login"], "(demo)" if demo else "")


if __name__ == "__main__":
    main()
