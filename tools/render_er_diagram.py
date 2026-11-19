from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "electoraw-er-diagram.png"
W, H = 2800, 1900
BG, INK, LINE = "#fbfdfb", "#183b2a", "#344b3b"
GREEN, GREEN_DARK = "#dff1df", "#237a3a"
BLUE, BLUE_DARK = "#e5f0fa", "#226493"
YELLOW, YELLOW_DARK = "#fff1c9", "#946b00"
PINK, PINK_DARK = "#f9e1e1", "#9c3f45"


def font(size, bold=False):
    path = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    return ImageFont.truetype(path, size)


im = Image.new("RGB", (W, H), BG)
d = ImageDraw.Draw(im)
title, section_font, entity_font = font(42, True), font(27, True), font(23, True)
body, small, relation = font(17), font(16), font(18, True)


def text_center(x, y, value, face, fill=INK):
    bb = d.textbbox((0, 0), value, font=face)
    d.text((x - (bb[2] - bb[0]) / 2, y - (bb[3] - bb[1]) / 2), value, font=face, fill=fill)


def connect(points, color=LINE, width=3):
    d.line(points, fill=color, width=width, joint="curve")


def entity(x, y, w, h, label, fill=GREEN, outline=GREEN_DARK):
    d.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=fill, outline=outline, width=3)
    text_center(x + w / 2, y + h / 2, label, entity_font, outline)


def oval(x, y, label, outline=GREEN_DARK):
    bb = d.textbbox((0, 0), label, font=body)
    w, h = bb[2] - bb[0] + 34, max(42, bb[3] - bb[1] + 18)
    d.ellipse((x - w / 2, y - h / 2, x + w / 2, y + h / 2), fill="#ffffff", outline=outline, width=2)
    text_center(x, y, label, body)


def diamond(x, y, label, fill=YELLOW, outline=YELLOW_DARK, w=105, h=54):
    pts = [(x, y - h / 2), (x + w / 2, y), (x, y + h / 2), (x - w / 2, y)]
    d.polygon(pts, fill=fill, outline=outline)
    d.line(pts + [pts[0]], fill=outline, width=2)
    text_center(x, y, label, relation)


def section(y, heading, subtitle, color):
    d.line((70, y, W - 70, y), fill=color, width=2)
    d.text((78, y + 14), heading, font=section_font, fill=color)
    d.text((78, y + 49), subtitle, font=small, fill="#456451")
    d.line((70, y + 82, W - 70, y + 82), fill="#c9d7cc", width=1)


d.text((70, 28), "ELECTORaW — ENTITY RELATIONSHIP DIAGRAM", font=title, fill=INK)
d.text((W - 700, 44), "Chen-style view · current implementation", font=small, fill="#456451")

# MySQL workflow tables.
section(110, "OPERATIONAL WORKFLOW · MySQL", "Role-based election administration in the workflow_* tables", GREEN_DARK)
entity(150, 285, 235, 82, "USERS")
entity(760, 285, 245, 82, "ELECTIONS")
entity(1335, 285, 300, 82, "ELECTION_SEATS")
entity(1940, 285, 290, 82, "NOMINATIONS")
entity(2050, 660, 270, 82, "CERTIFICATES", PINK, PINK_DARK)
entity(460, 660, 230, 82, "AUDIT_LOG", BLUE, BLUE_DARK)
diamond(575, 326, "declares")
diamond(1175, 326, "includes")
diamond(1785, 326, "receives")
diamond(2135, 535, "earns", PINK, PINK_DARK)
diamond(790, 700, "records", BLUE, BLUE_DARK)
diamond(1420, 535, "submits")
connect([(385, 326), (493, 326)])
connect([(657, 326), (760, 326)])
connect([(1005, 326), (1134, 326)])
connect([(1216, 326), (1335, 326)])
connect([(1635, 326), (1744, 326)])
connect([(1826, 326), (1940, 326)])
connect([(2135, 367), (2135, 508)])
connect([(2135, 562), (2135, 660)])
connect([(575, 367), (575, 620), (790, 620), (790, 673)])
connect([(385, 326), (385, 535), (1420, 535)])
connect([(1420, 535), (1940, 367)])
for x, y, label in [(105, 245, "id"), (95, 405, "email"), (270, 430, "role"), (350, 215, "full_name"),
                    (690, 235, "id"), (720, 410, "year"), (1035, 230, "status"), (1035, 410, "declared_by"),
                    (1270, 235, "id"), (1260, 410, "state"), (1510, 425, "constituency"),
                    (1880, 230, "id"), (1810, 425, "candidate_name"), (2220, 235, "status"), (2310, 425, "is_winner"),
                    (2010, 805, "nomination_id"), (2350, 805, "issued_by"), (370, 805, "user_id"), (690, 805, "action")]:
    oval(x, y, label, PINK_DARK if x > 1900 else BLUE_DARK if y > 600 else GREEN_DARK)
d.text((78, 865), "Only an accepted nomination can become a winner and receive one certificate.", font=small, fill="#456451")

# MySQL analytical facts.
section(930, "ANALYTICAL ELECTION FACTS · MySQL", "Normalized election results, historical constituency versions, provenance, and imports", BLUE_DARK)
for args in [(90, 1125, 190, 78, "STATES"), (430, 1125, 245, 78, "CONSTITUENCIES"),
             (825, 1125, 315, 78, "CONST. VERSIONS"), (1285, 1125, 210, 78, "ELECTIONS"),
             (1640, 1125, 265, 78, "ELECTION_CONTESTS"), (2050, 1125, 220, 78, "RESULTS"),
             (2415, 1125, 220, 78, "CANDIDATES")]:
    entity(*args, fill=BLUE, outline=BLUE_DARK)
entity(2420, 1430, 205, 78, "PARTIES", YELLOW, YELLOW_DARK)
entity(1990, 1430, 300, 78, "MEMBERSHIPS", BLUE, BLUE_DARK)
entity(970, 1430, 235, 78, "DATA_SOURCES", BLUE, BLUE_DARK)
entity(1370, 1430, 250, 78, "IMPORT_BATCHES", BLUE, BLUE_DARK)
for x, label, width in [(355, "has", 75), (750, "versioned as", 125), (1210, "contains", 105),
                         (1570, "contests", 100), (1970, "records", 95), (2340, "contested by", 135)]:
    diamond(x, 1164, label, BLUE, BLUE_DARK, width)
for pts in [[(280, 1164), (317, 1164)], [(393, 1164), (430, 1164)], [(675, 1164), (825, 1164)],
            [(1140, 1164), (1285, 1164)], [(1495, 1164), (1640, 1164)], [(1905, 1164), (2050, 1164)],
            [(2270, 1164), (2415, 1164)]]:
    connect(pts)
diamond(2390, 1320, "represents", YELLOW, YELLOW_DARK, 125)
connect([(2525, 1203), (2525, 1260), (2390, 1260), (2390, 1293)])
connect([(2390, 1347), (2390, 1430)])
diamond(1850, 1320, "has", BLUE, BLUE_DARK)
connect([(1770, 1164), (1770, 1260), (1850, 1260), (1850, 1293)])
connect([(1850, 1347), (1990, 1430)])
diamond(1290, 1320, "documents", BLUE, BLUE_DARK, 125)
connect([(1390, 1203), (1390, 1260), (1290, 1260), (1290, 1293)])
connect([(1290, 1347), (1087, 1430)])
diamond(1495, 1550, "ingests", BLUE, BLUE_DARK)
connect([(1205, 1469), (1370, 1469)])
for x, y, label in [(85, 1070, "state_id"), (300, 1270, "state_name"), (410, 1070, "constituency_id"),
                    (700, 1260, "created_at"), (825, 1070, "version_id"), (1030, 1260, "delimitation"),
                    (1250, 1070, "election_id"), (1430, 1260, "election_year"), (1570, 1070, "contest_id"),
                    (1790, 1260, "turnout"), (2010, 1070, "result_id"), (2180, 1260, "votes"),
                    (2400, 1070, "candidate_id"), (2620, 1260, "candidate_name"), (2360, 1535, "party_id"),
                    (2630, 1535, "party_name"), (1920, 1535, "membership_id"), (2240, 1535, "status"),
                    (930, 1535, "source_id"), (1170, 1535, "source_url"), (1320, 1535, "batch_id"), (1650, 1535, "rows_imported")]:
    oval(x, y, label, YELLOW_DARK if x > 2300 else BLUE_DARK)

# Logical non-relational stores.
d.rounded_rectangle((70, 1685, W - 70, 1835), radius=12, fill="#f3f7f3", outline="#b8cbbd", width=2)
d.text((95, 1700), "DOCUMENT + VECTOR STORES (logical relationships)", font=section_font, fill="#456451")
d.text((95, 1750), "MongoDB: workflow_users ↔ USERS · workflow_nominations ↔ NOMINATIONS · candidate_profiles ↔ candidate identity", font=small, fill=INK)
d.text((95, 1785), "ChromaDB: source documents → chunks + metadata → electoraw_corpus → grounded RAG answers", font=small, fill=INK)
d.text((W - 720, 1748), "■ Entity   ◆ Relationship   ◯ Attribute", font=small, fill=GREEN_DARK)

OUT.parent.mkdir(parents=True, exist_ok=True)
im.save(OUT)
print(OUT)
