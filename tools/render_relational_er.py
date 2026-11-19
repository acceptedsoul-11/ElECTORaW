from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "electoraw-relational-er.png"
W, H = 3800, 2600
BG = "#f8fbf8"
INK = "#183b2a"
LINE = "#334b3b"
GREEN = "#dcefdc"
GREEN_EDGE = "#237a3a"
BLUE = "#e2eff9"
BLUE_EDGE = "#216493"
YELLOW = "#fff0c7"
YELLOW_EDGE = "#936800"
PINK = "#f7dfdf"
PINK_EDGE = "#9b3f46"


def f(size: int, bold: bool = False):
    return ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf", size)


img = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(img)
title = f(46, True)
section = f(29, True)
entity_font = f(20, True)
rel_font = f(17, True)
attr_font = f(15)
small = f(16)


def centered(x, y, value, face, fill=INK):
    bb = d.textbbox((0, 0), value, font=face)
    d.text((x - (bb[2] - bb[0]) / 2, y - (bb[3] - bb[1]) / 2), value, font=face, fill=fill)


def line(points, color=LINE, width=2):
    d.line(points, fill=color, width=width, joint="curve")


def rect(x, y, w, h, label, fill, edge):
    d.rectangle((x, y, x + w, y + h), fill=fill, outline=edge, width=3)
    face = entity_font
    if len(label) > 24:
        face = f(16, True)
    elif len(label) > 19:
        face = f(18, True)
    centered(x + w / 2, y + h / 2, label, face, edge)
    return (x, y, w, h)


def oval(x, y, label, edge, dashed=False, underline=False):
    bb = d.textbbox((0, 0), label, font=attr_font)
    w, h = bb[2] - bb[0] + 30, max(38, bb[3] - bb[1] + 16)
    if dashed:
        for a in range(0, 360, 16):
            import math
            b = a + 8
            d.arc((x - w / 2, y - h / 2, x + w / 2, y + h / 2), a, b, fill=edge, width=2)
    else:
        d.ellipse((x - w / 2, y - h / 2, x + w / 2, y + h / 2), fill="#ffffff", outline=edge, width=2)
    centered(x, y, label, attr_font)
    if underline:
        d.line((x - w / 3, y + 10, x + w / 3, y + 10), fill=INK, width=2)
    return (x, y, w / 2, h / 2)


def diamond(x, y, label, edge=YELLOW_EDGE, fill=YELLOW, w=120, h=58):
    pts = [(x, y - h / 2), (x + w / 2, y), (x, y + h / 2), (x - w / 2, y)]
    d.polygon(pts, fill=fill, outline=edge)
    d.line(pts + [pts[0]], fill=edge, width=2)
    centered(x, y, label, rel_font)


def section_rule(y, label, subtitle, color):
    d.line((80, y, W - 80, y), fill=color, width=2)
    d.text((90, y + 13), label, font=section, fill=color)
    d.text((90, y + 51), subtitle, font=small, fill="#456451")
    d.line((80, y + 87, W - 80, y + 87), fill="#c8d8cc", width=1)


def attrs(entity_box, labels, edge, top=True):
    x, y, w, h = entity_box
    sizes = []
    for item in labels:
        label = item[0] if isinstance(item, tuple) else item
        bb = d.textbbox((0, 0), label, font=attr_font)
        sizes.append(max(38, bb[2] - bb[0] + 30))
    gap = 18
    total = sum(sizes) + gap * (len(labels) - 1)
    cursor = x + w / 2 - total / 2
    for item, oval_w in zip(labels, sizes):
        label, pk, optional = item if isinstance(item, tuple) else (item, False, False)
        ax = cursor + oval_w / 2
        ay = y - 55 if top else y + h + 55
        oval(ax, ay, label, edge, dashed=optional, underline=pk)
        line([(x + w / 2, y if top else y + h), (ax, ay + (20 if top else -20))], edge, 1)
        cursor += oval_w + gap


d.text((80, 32), "ELECTORaW — RELATIONAL ENTITY RELATIONSHIP DIAGRAM", font=title, fill=INK)
d.text((W - 720, 52), "Chen notation · MySQL electoraw database", font=small, fill="#456451")

# Analytical MySQL schema.
section_rule(125, "ANALYTICAL ELECTION SCHEMA · MySQL", "Official election facts, winners, constituency history, and import provenance", BLUE_EDGE)

states = rect(90, 330, 250, 64, "STATES", BLUE, BLUE_EDGE)
const = rect(520, 330, 300, 64, "CONSTITUENCIES", BLUE, BLUE_EDGE)
versions = rect(1010, 330, 360, 64, "CONSTITUENCY_VERSIONS", BLUE, BLUE_EDGE)
elections = rect(1570, 330, 260, 64, "ELECTIONS", BLUE, BLUE_EDGE)
contests = rect(2025, 330, 355, 64, "ELECTION_CONSTITUENCIES", BLUE, BLUE_EDGE)
results = rect(2560, 330, 300, 64, "CANDIDATE_RESULTS", BLUE, BLUE_EDGE)
candidates = rect(3040, 330, 240, 64, "CANDIDATES", BLUE, BLUE_EDGE)
parties = rect(3460, 330, 230, 64, "PARTIES", YELLOW, YELLOW_EDGE)

for x, label, width in [(430, "has", 90), (915, "versioned", 115), (1470, "defines", 100), (1925, "contains", 110), (2470, "records", 100), (2950, "contests", 105), (3370, "represents", 135)]:
    diamond(x, 362, label, BLUE_EDGE, BLUE, width)
for a, b in [(states, const), (const, versions), (versions, elections), (elections, contests), (contests, results), (results, candidates), (candidates, parties)]:
    ax = a[0] + a[2]
    bx = b[0]
    line([(ax, 362), (bx, 362)], BLUE_EDGE)

attrs(states, [("state_id", True, False), "state_name", "state_code"], BLUE_EDGE, True)
attrs(const, [("constituency_id", True, False), "state_id", "created_at"], BLUE_EDGE, False)
attrs(versions, [("version_id", True, False), "name", "delimitation"], BLUE_EDGE, True)
attrs(elections, [("election_id", True, False), "year", "type"], BLUE_EDGE, False)
attrs(contests, [("contest_id", True, False), "election_id", "turnout"], BLUE_EDGE, True)
attrs(results, [("result_id", True, False), "votes", "is_winner"], BLUE_EDGE, False)
attrs(candidates, [("candidate_id", True, False), "candidate_name", "gender"], BLUE_EDGE, True)
attrs(parties, [("party_id", True, False), "party_name", "symbol"], YELLOW_EDGE, False)

memberships = rect(3020, 780, 360, 64, "PARLIAMENTARY_MEMBERSHIPS", BLUE, BLUE_EDGE)
official = rect(2520, 780, 320, 64, "OFFICIAL_WINNERS", PINK, PINK_EDGE)
sources = rect(1510, 780, 240, 64, "DATA_SOURCES", BLUE, BLUE_EDGE)
batches = rect(2010, 780, 240, 64, "IMPORT_BATCHES", BLUE, BLUE_EDGE)

diamond(3160, 570, "has", BLUE_EDGE, BLUE)
line([(candidates[0] + candidates[2] / 2, candidates[1] + candidates[3]), (3160, 541), (3160, memberships[1])], BLUE_EDGE)
diamond(2710, 570, "confirms", PINK_EDGE, PINK, 125)
line([(results[0] + results[2] / 2, results[1] + results[3]), (2710, 541), (2710, official[1])], PINK_EDGE)
diamond(1450, 570, "documents", BLUE_EDGE, BLUE, 135)
line([(elections[0] + elections[2] / 2, elections[1] + elections[3]), (1450, 541), (sources[0] + sources[2] / 2, sources[1])], BLUE_EDGE)
diamond(1880, 812, "ingests", BLUE_EDGE, BLUE)
line([(sources[0] + sources[2], sources[1] + sources[3] / 2), (1880, 812), (batches[0], batches[1] + batches[3] / 2)], BLUE_EDGE)
attrs(memberships, [("membership_id", True, False), "status", "dates"], BLUE_EDGE, False)
attrs(official, [("winner_id", True, False), "winner_name", "match_status"], PINK_EDGE, True)
attrs(sources, [("source_id", True, False), "source_url", "election_id"], BLUE_EDGE, False)
attrs(batches, [("batch_id", True, False), "status", "rows_imported"], BLUE_EDGE, True)

# Operational workflow schema.
section_rule(1060, "OPERATIONAL WORKFLOW SCHEMA · MySQL workflow_* tables", "Registration, declarations, nominations, approvals, winners, certificates, and audit history", GREEN_EDGE)

users = rect(90, 1280, 260, 64, "WORKFLOW_USERS", GREEN, GREEN_EDGE)
w_elections = rect(520, 1280, 310, 64, "WORKFLOW_ELECTIONS", GREEN, GREEN_EDGE)
w_seats = rect(1010, 1280, 390, 64, "WORKFLOW_ELECTION_SEATS", GREEN, GREEN_EDGE)
noms = rect(1570, 1280, 350, 64, "WORKFLOW_NOMINATIONS", GREEN, GREEN_EDGE)
certs = rect(2100, 1280, 360, 64, "WORKFLOW_CERTIFICATES", PINK, PINK_EDGE)
audit = rect(2640, 1280, 280, 64, "WORKFLOW_AUDIT_LOG", BLUE, BLUE_EDGE)

for x, label, width in [(425, "declares", 105), (920, "opens", 90), (1480, "receives", 105), (2010, "earns", 90), (2550, "records", 100)]:
    diamond(x, 1312, label, GREEN_EDGE if label != "earns" else PINK_EDGE, GREEN if label != "earns" else PINK, width)
for a, b in [(users, w_elections), (w_elections, w_seats), (w_seats, noms), (noms, certs), (users, audit)]:
    if a is users and b is audit:
        line([(users[0] + users[2] / 2, users[1] + users[3]), (users[0] + users[2] / 2, 1510), (audit[0] + audit[2] / 2, 1510), (audit[0] + audit[2] / 2, audit[1])], BLUE_EDGE)
    else:
        line([(a[0] + a[2], 1312), (b[0], 1312)], GREEN_EDGE if b is not certs else PINK_EDGE)

attrs(users, [("id", True, False), "email", "role"], GREEN_EDGE, True)
attrs(w_elections, [("id", True, False), "year", "status"], GREEN_EDGE, False)
attrs(w_seats, [("id", True, False), "state", "constituency"], GREEN_EDGE, True)
attrs(noms, [("id", True, False), "candidate_name", "status"], GREEN_EDGE, False)
attrs(certs, [("id", True, False), "certificate_no", "issued_by"], PINK_EDGE, True)
attrs(audit, [("id", True, False), "action", "created_at"], BLUE_EDGE, False)

approved = diamond(1740, 1600, "approves", GREEN_EDGE, GREEN, 115)
winner = diamond(2270, 1600, "winner", PINK_EDGE, PINK, 100)
line([(noms[0] + noms[2] / 2, noms[1] + noms[3]), (1740, 1600), (1740, 1630)], GREEN_EDGE)
line([(1740, 1630), (2270, 1630), (2270, 1630)], PINK_EDGE)
line([(2270, 1570), (2270, 1344)], PINK_EDGE)
d.text((90, 1730), "Rules: pending → accepted/rejected; only accepted nominations can become winners; one certificate per nomination; one winner per declared seat.", font=small, fill="#456451")

# Compact legend in the style requested.
d.rounded_rectangle((80, 1870, W - 80, 1990), radius=10, fill="#eef5ef", outline="#b9cbbd", width=2)
d.text((105, 1890), "LEGEND", font=section, fill=INK)
rect(420, 1900, 150, 42, "ENTITY", GREEN, GREEN_EDGE)
diamond(760, 1921, "RELATIONSHIP", GREEN_EDGE, GREEN, 150, 48)
oval(1120, 1921, "ATTRIBUTE", GREEN_EDGE)
oval(1510, 1921, "OPTIONAL", GREEN_EDGE, dashed=True)
oval(1850, 1921, "PRIMARY KEY", GREEN_EDGE, underline=True)
d.text((2240, 1906), "All boxes and relationships shown here are relational MySQL structures.", font=small, fill="#456451")

OUT.parent.mkdir(parents=True, exist_ok=True)
img.save(OUT)
print(OUT)
