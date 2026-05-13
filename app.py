from __future__ import annotations

import json
import math
import os
import random
import re
import sqlite3
import uuid
from datetime import date, datetime, timedelta
from functools import wraps
from pathlib import Path
from textwrap import dedent
from urllib.error import URLError
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

from flask import Flask, Response, abort, flash, g, jsonify, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "bookverse.db"
APP_SECRET = "bookverse-ai-premium-secret"
ADMIN_EMAIL = "admin@bookverse.ai"
ADMIN_PASSWORD = "admin123"
CATALOG_TARGET = 520
FRONTEND_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:5500,http://localhost:5500,http://127.0.0.1:3000,http://localhost:3000",
    ).split(",")
    if origin.strip()
]

app = Flask(__name__)
app.secret_key = APP_SECRET
if os.environ.get("CROSS_SITE_SESSION", "0") == "1":
    app.config["SESSION_COOKIE_SAMESITE"] = "None"
    app.config["SESSION_COOKIE_SECURE"] = True


MANUAL_BOOKS = [
    {
        "source_id": "local-midnight-atlas",
        "source_name": "local",
        "title": "Midnight Atlas",
        "author": "Aarav Sen",
        "genre": "Fiction",
        "price": 499,
        "rating": 4.8,
        "language": "English",
        "pages": 312,
        "stock": 18,
        "cover_palette": "#1d3557,#457b9d,#a8dadc",
        "cover_url": "",
        "description": "A lyrical adventure through secret cities that appear only after sunset.",
        "summary": "A mapmaker discovers a night-bound atlas that rewrites every destination according to the reader's deepest longing.",
        "mood_tags": "weekend,adventure,fiction,imaginative",
        "excerpt": "The city only unfolded after midnight, when street lamps blinked twice and the river began reflecting places no one had built.",
        "text_url": "",
        "featured": 1,
        "new_arrival": 1,
        "best_seller": 1,
        "trending": 1,
    },
    {
        "source_id": "local-rank-1-reasoning",
        "source_name": "local",
        "title": "Rank 1 Reasoning",
        "author": "Dr. Kabir Mehta",
        "genre": "Competitive Exam",
        "price": 599,
        "rating": 4.5,
        "language": "English",
        "pages": 540,
        "stock": 31,
        "cover_palette": "#0f172a,#38bdf8,#e0f2fe",
        "cover_url": "",
        "description": "High-intensity reasoning drills with timed mock patterns for bank and SSC exams.",
        "summary": "Structured practice sets, score ladders, and revision sprints tuned for exam preparation.",
        "mood_tags": "exam,productive,student,reasoning",
        "excerpt": "Speed is born from pattern recognition, not panic.",
        "text_url": "",
        "featured": 0,
        "new_arrival": 0,
        "best_seller": 1,
        "trending": 1,
    },
    {
        "source_id": "local-logic-ladder-mastery",
        "source_name": "local",
        "title": "Logic Ladder Mastery",
        "author": "Prof. Neeraj Sethi",
        "genre": "Competitive Exam",
        "price": 649,
        "rating": 4.7,
        "language": "English",
        "pages": 512,
        "stock": 34,
        "cover_palette": "#14213d,#00b4d8,#caf0f8",
        "cover_url": "",
        "description": "A reasoning workbook with solved arrangements, coding-decoding drills, syllogism tricks, and timed mixed sets.",
        "summary": "Built for SSC, Bank, CAT, and campus aptitude prep with chapter-wise methods, solved examples, and shortcut notes.",
        "mood_tags": "exam,productive,student,reasoning",
        "excerpt": "A good reasoning answer feels inevitable only after you have arranged the chaos correctly.",
        "text_url": "",
        "featured": 0,
        "new_arrival": 1,
        "best_seller": 1,
        "trending": 1,
    },
]

MANUAL_READER_CONTENT = {
    "Rank 1 Reasoning": [
        "Unit 1: Direction Sense Basics\n\nQuestion: Ravi starts from his school gate and walks 12 metres north. He turns right, walks 8 metres, turns right again, and walks 12 metres. He is now facing south. How far is he from the starting point?\n\nMethod: Draw the path as a rectangle. The north-south distance cancels out. Only the eastward movement of 8 metres remains.\n\nAnswer: 8 metres east of the starting point.",
        "Unit 2: Coding-Decoding\n\nQuestion: In a certain code, PLAN is written as SODQ and RISE is written as ULVH. How will BOOK be written?\n\nMethod: Each letter moves three places forward in the alphabet. B to E, O to R, O to R, K to N.\n\nAnswer: ERRN.\n\nShortcut: Always test whether the shift is uniform before looking for alternating patterns.",
        "Unit 3: Syllogism\n\nStatements: All poets are dreamers. Some dreamers are teachers. No teacher is careless.\n\nConclusions:\n1. Some poets are teachers.\n2. Some dreamers are not careless.\n\nConclusion 1 does not follow. Conclusion 2 follows because some dreamers are teachers and no teacher is careless.",
        "Unit 4: Seating Arrangement\n\nEight friends A, B, C, D, E, F, G, and H sit around a circular table facing the centre. A sits second to the left of D. B sits opposite A. C is not a neighbour of D. E sits between G and H.\n\nApproach: Fix D first, place A second to the left, place B opposite A, then build the E-G-H block and solve remaining positions by elimination.",
        "Unit 5: Blood Relation\n\nPointing to a photograph, Nisha says, 'She is the daughter of the only son of my grandfather.'\n\nBreakdown: The only son of Nisha's grandfather is Nisha's father. The daughter of Nisha's father is Nisha or Nisha's sister.\n\nMost direct answer in standard reasoning form: the girl is Nisha's sister.",
        "Unit 6: Inequalities\n\nGiven: P > Q >= R < S <= T and T < U.\n\nQuestion: Which of the following is definitely true?\n\nObservation: R < S and S <= T, so R < T. Also T < U, so R < U.\n\nRule: Chain the inequalities and conclude only what remains strict after every link.",
        "Unit 7: Input-Output Pattern\n\nInput: 42, 17, 63, 28, 35, 14\n\nStep 1 rearranges numbers in ascending order at odd positions and descending order at even positions.\n\nWorking: Odd positions become 14, 28, 42. Even positions become 63, 35, 17.\n\nOutput: 14, 63, 28, 35, 42, 17.",
        "Unit 8: Puzzle Practice Set\n\nFive students P, Q, R, S, and T scored distinct marks. Q scored more than only T. P scored less than R but more than S. T did not score the least.\n\nA workable order is S < T < Q < P < R. The trick is to convert clues into a clean ranking line before testing alternatives.",
        "Unit 9: Mixed Practice Drill\n\n1. Number series: 3, 8, 18, 38, 78, ?\nPattern: multiply by 2 and add 2. Next term = 158.\n\n2. Alphabet series: A, D, H, M, ?\nPattern: +3, +4, +5, next +6. Answer = S.\n\n3. Odd one out: Square, Rectangle, Triangle, Rhombus.\nAnswer: Triangle, because the others are quadrilaterals.",
        "Unit 10: Final Revision Sheet\n\nRule 1: Draw direction and arrangement problems.\nRule 2: Mark definite conclusions only.\nRule 3: In coding, test simple shifts before complex mapping.\nRule 4: In puzzles, convert language into positions, not stories.\nRule 5: Leave overlong questions for the second round.\n\nSpeed booster: accuracy first, speed second, panic never.",
    ],
    "Logic Ladder Mastery": [
        "Lesson 1: Alphanumeric Series\n\nFind the next term: Z1, X2, U4, Q7, L11, ?\n\nPattern: Letters move backward by 2, 3, 4, 5. Numbers increase by 1, 2, 3, 4. Next letter moves back by 6 from L to F. Next number becomes 16.\n\nAnswer: F16.",
        "Lesson 2: Statement and Assumption\n\nStatement: The school introduced a weekly logic lab for all Class 10 students.\n\nAssumptions:\n1. Students can improve reasoning through regular practice.\n2. Logic matters only for board examinations.\n\nOnly assumption 1 is implicit.",
        "Lesson 3: Ranking Test\n\nIn a row of 40 students, Anya is 12th from the left and Kabir is 9th from the right. If they interchange places, Anya becomes 18th from the left.\n\nKabir's original position from the left is therefore 18th.",
        "Lesson 4: Data Sufficiency\n\nQuestion: Is M taller than N?\nStatement 1: M is taller than P.\nStatement 2: P is not taller than N.\n\nCombined, the data is still insufficient because M > P and P <= N do not guarantee M > N.",
        "Lesson 5: Analytical Puzzle\n\nFour bookshelves contain History, Physics, Reasoning, and Literature in no particular order. The blue shelf is not used for Literature. Reasoning is above Physics. The green shelf is below the red shelf.\n\nBest method: build vertical positions first, then apply color constraints.",
        "Lesson 6: Cause and Effect\n\n1. The city introduced free evening library memberships.\n2. Student footfall in community reading halls doubled in three months.\n\nA reasonable cause-effect relation exists because access and usage are directly linked, though external factors may also contribute.",
        "Lesson 7: Non-Verbal Logic in Words\n\nImagine a figure rotated 90 degrees clockwise twice. The final figure is equivalent to a 180-degree rotation from the original.\n\nShortcut: reduce repeated rotations to total angular change before comparing mirror images.",
        "Lesson 8: Machine Input Example\n\nInput: brave cloud apple ember stone\n\nStep 1 arranges words by ascending length and then alphabetically within equal length.\n\nOutput: apple brave cloud ember stone.\n\nTrack the rule, not just the final order.",
        "Lesson 9: High-Speed Revision Quiz\n\nQuestion 1: If all cams are jols and all jols are nims, then all cams are definitely nims.\nQuestion 2: If EAST is coded as 45 using letter positions and digit sums, test the same rule on WEST before answering.\nQuestion 3: In family-tree questions, rewrite every relation around one common person.",
        "Lesson 10: Ladder Summary\n\nReasoning improves when each chapter becomes a checklist: identify pattern, convert wording into structure, eliminate impossible cases, and lock the answer only after verifying every clue.\n\nPractice turns confusion into sequence.",
    ],
}

USER_SEEDS = [
    ("Aanya", "aanya_reads", "Fiction,Classics,Thriller", 18, "Bookworm"),
    ("Vihaan", "vihaan.studydeck", "Academic,Competitive Exam,Self-Help", 27, "Scholar"),
    ("Leena", "leena.afterhours", "Thriller,Fiction,Classics", 12, "Speed Reader"),
    ("Rohan", "rohan.weekendstack", "Novel,Self-Help,Fiction", 9, "Bookworm"),
]

CLUB_SEEDS = [
    ("Midnight Margins", "Night readers dissecting thrillers and literary fiction.", "Every Friday 9:00 PM"),
    ("Exam Legends", "Focused accountability club for aptitude, bank, and campus prep.", "Daily 7:00 AM"),
    ("Founders & Folios", "Business, psychology, and leadership picks with startup debriefs.", "Sunday 11:00 AM"),
]


def get_db() -> sqlite3.Connection:
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None) -> None:
    db = g.pop("db", None)
    if db is not None:
        db.close()


def query_db(query: str, args: tuple = (), one: bool = False):
    cur = get_db().execute(query, args)
    rows = cur.fetchall()
    cur.close()
    return (rows[0] if rows else None) if one else rows


def execute_db(statement: str, args: tuple = ()) -> None:
    db = get_db()
    db.execute(statement, args)
    db.commit()


def fetch_json(url: str) -> dict:
    request_obj = Request(url, headers={"User-Agent": "BOOKVERSE-AI/1.0"})
    with urlopen(request_obj, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str) -> str:
    request_obj = Request(url, headers={"User-Agent": "BOOKVERSE-AI/1.0"})
    with urlopen(request_obj, timeout=25) as response:
        payload = response.read()
    for encoding in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return payload.decode("utf-8", errors="ignore")


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.lower()).strip("-")
    return cleaned or uuid.uuid4().hex[:10]


def infer_genre(subjects: list[str], title: str) -> str:
    haystack = " ".join(subjects + [title]).lower()
    rules = [
        ("Thriller", ["mystery", "detective", "crime", "murder", "suspense", "thriller"]),
        ("Science Fiction", ["science fiction", "space", "alien", "future"]),
        ("Fantasy", ["fantasy", "fairy", "magic", "dragons"]),
        ("Romance", ["love stories", "romance", "courtship"]),
        ("History", ["history", "historical"]),
        ("Poetry", ["poetry", "poems", "verse"]),
        ("Drama", ["drama", "plays", "tragedies", "comedy"]),
        ("Adventure", ["adventure", "voyages", "sea stories", "pirates"]),
        ("Philosophy", ["philosophy", "ethics", "metaphysics"]),
        ("Academic", ["education", "science", "mathematics", "physics", "biology"]),
        ("Fiction", ["fiction", "novel", "short stories", "literature"]),
    ]
    for genre, keywords in rules:
        if any(keyword in haystack for keyword in keywords):
            return genre
    return "Classics"


def mood_tags_for_genre(genre: str) -> str:
    mapping = {
        "Thriller": "night,mysterious,weekend,thriller",
        "Science Fiction": "imaginative,weekend,curious,fiction",
        "Fantasy": "imaginative,weekend,fiction,escape",
        "Romance": "happy,weekend,romantic,fiction",
        "History": "reflective,serious,weekend,history",
        "Poetry": "reflective,calm,weekend,poetry",
        "Drama": "emotional,weekend,dramatic,fiction",
        "Adventure": "adventure,weekend,fiction,travel",
        "Philosophy": "serious,calm,weekday,thinking",
        "Academic": "student,exam,serious,learning",
        "Fiction": "fiction,weekend,happy,imaginative",
        "Classics": "classics,weekend,reflective,literary",
    }
    return mapping.get(genre, "weekend,fiction,curious")


def derive_price(source_numeric: int, genre: str) -> int:
    base = {
        "Academic": 699,
        "Philosophy": 499,
        "History": 549,
        "Thriller": 429,
        "Science Fiction": 479,
        "Fantasy": 469,
        "Adventure": 439,
        "Classics": 389,
        "Fiction": 449,
        "Romance": 399,
        "Poetry": 359,
        "Drama": 379,
    }.get(genre, 429)
    return base + (source_numeric % 6) * 40


def derive_rating(download_count: int) -> float:
    if download_count <= 0:
        return 4.1
    normalized = min(math.log10(download_count + 10) / 1.25, 1.0)
    return round(4.0 + normalized, 1)


def derive_stock(source_numeric: int) -> int:
    return 4 + (source_numeric % 17)


def derive_flags(source_numeric: int) -> tuple[int, int, int, int]:
    featured = 1 if source_numeric % 19 == 0 else 0
    new_arrival = 1 if source_numeric % 7 == 0 else 0
    best_seller = 1 if source_numeric % 9 == 0 else 0
    trending = 1 if source_numeric % 5 == 0 else 0
    return featured, new_arrival, best_seller, trending


def build_gutendex_payload(item: dict) -> dict | None:
    formats = item.get("formats", {})
    cover_url = formats.get("image/jpeg", "")
    text_url = ""
    for key, value in formats.items():
        if "text/plain" in key and isinstance(value, str) and value:
            text_url = value
            break
    if not cover_url or not text_url:
        return None

    source_numeric = int(item["id"])
    title = re.sub(r"\s+", " ", item.get("title", "").strip())
    if not title:
        return None
    authors = item.get("authors") or []
    author = authors[0]["name"] if authors else "Unknown Author"
    subjects = item.get("subjects") or []
    bookshelves = item.get("bookshelves") or []
    genre = infer_genre(subjects + bookshelves, title)
    language = (item.get("languages") or ["English"])[0].title()
    summary_bits = subjects[:4] or bookshelves[:4] or [genre, "Public domain edition", "Project Gutenberg"]
    description = f"Real public-domain edition of {title} by {author}, sourced from Project Gutenberg metadata."
    summary = "Subjects: " + ", ".join(summary_bits)
    excerpt = f"A readable {genre.lower()} preview sourced from Project Gutenberg text for {title}."
    featured, new_arrival, best_seller, trending = derive_flags(source_numeric)

    return {
        "source_id": f"gutendex-{source_numeric}",
        "source_name": "gutendex",
        "title": title[:180],
        "author": author[:180],
        "genre": genre,
        "price": derive_price(source_numeric, genre),
        "rating": derive_rating(item.get("download_count", 0)),
        "language": language,
        "pages": 10,
        "stock": derive_stock(source_numeric),
        "cover_palette": "#111827,#334155,#cbd5e1",
        "cover_url": cover_url,
        "description": description,
        "summary": summary[:420],
        "mood_tags": mood_tags_for_genre(genre),
        "excerpt": excerpt,
        "text_url": text_url,
        "featured": featured,
        "new_arrival": new_arrival,
        "best_seller": best_seller,
        "trending": trending,
    }


def build_openlibrary_payload(item: dict, query_tag: str) -> dict | None:
    cover_id = item.get("cover_i")
    title = re.sub(r"\s+", " ", (item.get("title") or "").strip())
    authors = item.get("author_name") or []
    author = authors[0].strip() if authors else ""
    if not cover_id or not title or not author:
        return None

    key = (item.get("key") or f"{title}-{author}").replace("/works/", "")
    subjects = item.get("subject") or []
    genre = infer_genre(subjects, title)
    year = item.get("first_publish_year")
    pages = item.get("number_of_pages_median") or 10
    price = derive_price(abs(hash(key)) % 10000, genre)
    rating = round(4.1 + ((abs(hash(title)) % 9) / 10), 1)
    stock = 4 + (abs(hash(author)) % 18)
    featured, new_arrival, best_seller, trending = derive_flags(abs(hash(key)) % 10000)
    subject_line = ", ".join(subjects[:4]) if subjects else f"{genre}, public library, classic reading"
    description = f"Real catalog record sourced from Open Library for {title} by {author}."
    if year:
        description += f" First published around {year}."

    return {
        "source_id": f"openlibrary-{key}",
        "source_name": "openlibrary",
        "title": title[:180],
        "author": author[:180],
        "genre": genre,
        "price": price,
        "rating": min(rating, 4.9),
        "language": "English",
        "pages": max(10, min(int(pages), 1400)),
        "stock": stock,
        "cover_palette": "#111827,#334155,#cbd5e1",
        "cover_url": f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg",
        "description": description[:420],
        "summary": f"Subjects: {subject_line}"[:420],
        "mood_tags": mood_tags_for_genre(genre),
        "excerpt": f"Catalog query source: {query_tag}. Open the reader to load a real preview when a public-domain text match is available.",
        "text_url": "",
        "featured": featured,
        "new_arrival": new_arrival,
        "best_seller": best_seller,
        "trending": trending,
    }


def ensure_catalog(cursor: sqlite3.Cursor) -> None:
    count = cursor.execute("SELECT COUNT(*) FROM books").fetchone()[0]
    existing = {row[0] for row in cursor.execute("SELECT source_id FROM books WHERE source_id IS NOT NULL")}
    imported = 0

    if count < CATALOG_TARGET:
        query_terms = [
            "fiction",
            "novel",
            "mystery",
            "fantasy",
            "romance",
            "history",
            "poetry",
            "adventure",
            "science fiction",
            "classic literature",
        ]

        for term in query_terms:
            for page in range(1, 3):
                if count + imported >= CATALOG_TARGET:
                    break
                try:
                    payload = fetch_json(f"https://openlibrary.org/search.json?q={quote(term)}&language=eng&limit=60&page={page}")
                except (URLError, TimeoutError, ValueError):
                    continue
                for item in payload.get("docs", []):
                    prepared = build_openlibrary_payload(item, term)
                    if not prepared or prepared["source_id"] in existing:
                        continue
                    cursor.execute(
                        """
                        INSERT INTO books (
                            source_id, source_name, title, author, genre, price, rating, language, pages, stock,
                            sold_count, cover_palette, cover_url, description, summary, mood_tags, excerpt, text_url,
                            featured, new_arrival, best_seller, trending
                        ) VALUES (
                            :source_id, :source_name, :title, :author, :genre, :price, :rating, :language, :pages, :stock,
                            0, :cover_palette, :cover_url, :description, :summary, :mood_tags, :excerpt, :text_url,
                            :featured, :new_arrival, :best_seller, :trending
                        )
                        """,
                        prepared,
                    )
                    existing.add(prepared["source_id"])
                    imported += 1
                    if count + imported >= CATALOG_TARGET:
                        break

    previewable = cursor.execute("SELECT COUNT(*) FROM books WHERE text_url <> ''").fetchone()[0]
    if previewable >= 260:
        return

    next_url = "https://gutendex.com/books?page=1"
    pages_checked = 0
    while next_url and previewable < 260 and pages_checked < 14:
        try:
            payload = fetch_json(next_url)
        except (URLError, TimeoutError, ValueError):
            break
        next_url = payload.get("next")
        pages_checked += 1
        for item in payload.get("results", []):
            prepared = build_gutendex_payload(item)
            if not prepared or prepared["source_id"] in existing:
                continue
            cursor.execute(
                """
                INSERT INTO books (
                    source_id, source_name, title, author, genre, price, rating, language, pages, stock,
                    sold_count, cover_palette, cover_url, description, summary, mood_tags, excerpt, text_url,
                    featured, new_arrival, best_seller, trending
                ) VALUES (
                    :source_id, :source_name, :title, :author, :genre, :price, :rating, :language, :pages, :stock,
                    0, :cover_palette, :cover_url, :description, :summary, :mood_tags, :excerpt, :text_url,
                    :featured, :new_arrival, :best_seller, :trending
                )
                """,
                prepared,
            )
            existing.add(prepared["source_id"])
            previewable += 1
            if previewable >= 260:
                break


def lookup_gutendex_text_url(book) -> str:
    search_term = quote(f"{book['title']} {book['author']}")
    try:
        payload = fetch_json(f"https://gutendex.com/books?search={search_term}")
    except (URLError, TimeoutError, ValueError):
        return ""

    for item in payload.get("results", []):
        formats = item.get("formats", {})
        text_url = ""
        for key, value in formats.items():
            if "text/plain" in key and isinstance(value, str) and value:
                text_url = value
                break
        if not text_url:
            continue
        execute_db("UPDATE books SET text_url = ? WHERE id = ?", (text_url, book["id"]))
        return text_url
    return ""


def add_manual_books(cursor: sqlite3.Cursor) -> None:
    for book in MANUAL_BOOKS:
        row = cursor.execute("SELECT id FROM books WHERE source_id = ?", (book["source_id"],)).fetchone()
        if row:
            cursor.execute(
                """
                UPDATE books
                SET source_name = :source_name,
                    title = :title,
                    author = :author,
                    genre = :genre,
                    price = :price,
                    rating = :rating,
                    language = :language,
                    pages = :pages,
                    stock = :stock,
                    cover_palette = :cover_palette,
                    cover_url = :cover_url,
                    description = :description,
                    summary = :summary,
                    mood_tags = :mood_tags,
                    excerpt = :excerpt,
                    text_url = :text_url,
                    featured = :featured,
                    new_arrival = :new_arrival,
                    best_seller = :best_seller,
                    trending = :trending
                WHERE source_id = :source_id
                """,
                book,
            )
        else:
            cursor.execute(
                """
                INSERT INTO books (
                    source_id, source_name, title, author, genre, price, rating, language, pages, stock,
                    sold_count, cover_palette, cover_url, description, summary, mood_tags, excerpt, text_url,
                    featured, new_arrival, best_seller, trending
                ) VALUES (
                    :source_id, :source_name, :title, :author, :genre, :price, :rating, :language, :pages, :stock,
                    0, :cover_palette, :cover_url, :description, :summary, :mood_tags, :excerpt, :text_url,
                    :featured, :new_arrival, :best_seller, :trending
                )
                """,
                book,
            )


def ensure_columns(cursor: sqlite3.Cursor, table: str, definitions: dict[str, str]) -> None:
    existing = {row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()}
    for column, ddl in definitions.items():
        if column not in existing:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def backfill_orders(cursor: sqlite3.Cursor) -> None:
    rows = cursor.execute("SELECT * FROM orders ORDER BY id").fetchall()
    for row in rows:
        order_number = row["order_number"] or f"BV-{row['placed_on'].replace('-', '')}-{row['id']:04d}"
        tracking_number = row["tracking_number"] or f"TRK{row['id']:06d}"
        subtotal = row["subtotal"] or row["total"]
        items_count = row["items_count"] or 0
        if items_count == 0 and row["items_json"]:
            try:
                items_count = sum(item.get("qty", 1) for item in json.loads(row["items_json"]))
            except (TypeError, ValueError):
                items_count = 0
        expected_delivery = row["expected_delivery"] or str(date.fromisoformat(row["placed_on"]) + timedelta(days=3))
        cursor.execute(
            """
            UPDATE orders
            SET order_number = ?, tracking_number = ?, subtotal = ?, items_count = ?, payment_status = ?, expected_delivery = ?
            WHERE id = ?
            """,
            (order_number, tracking_number, subtotal, items_count, row["payment_status"] or "Paid", expected_delivery, row["id"]),
        )
        existing_items = cursor.execute("SELECT COUNT(*) FROM order_items WHERE order_id = ?", (row["id"],)).fetchone()[0]
        if existing_items == 0 and row["items_json"]:
            try:
                parsed_items = json.loads(row["items_json"])
            except (TypeError, ValueError):
                parsed_items = []
            for item in parsed_items:
                title = item.get("title", "Book")
                qty = item.get("qty", 1)
                book = cursor.execute("SELECT * FROM books WHERE title = ? LIMIT 1", (title,)).fetchone()
                if not book:
                    continue
                cursor.execute(
                    """
                    INSERT INTO order_items (order_id, book_id, title, author, cover_url, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row["id"],
                        book["id"],
                        book["title"],
                        book["author"],
                        book["cover_url"] or f"/cover/{book['id']}.svg",
                        book["price"],
                        qty,
                        book["price"] * qty,
                    ),
                )


def init_db() -> None:
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT,
            source_name TEXT DEFAULT 'local',
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            genre TEXT NOT NULL,
            price INTEGER NOT NULL,
            rating REAL NOT NULL,
            language TEXT NOT NULL,
            pages INTEGER NOT NULL DEFAULT 10,
            stock INTEGER NOT NULL DEFAULT 0,
            sold_count INTEGER NOT NULL DEFAULT 0,
            cover_palette TEXT NOT NULL DEFAULT '#111827,#334155,#cbd5e1',
            cover_url TEXT DEFAULT '',
            description TEXT NOT NULL DEFAULT '',
            summary TEXT NOT NULL DEFAULT '',
            mood_tags TEXT NOT NULL DEFAULT '',
            excerpt TEXT NOT NULL DEFAULT '',
            text_url TEXT DEFAULT '',
            featured INTEGER NOT NULL DEFAULT 0,
            new_arrival INTEGER NOT NULL DEFAULT 0,
            best_seller INTEGER NOT NULL DEFAULT 0,
            trending INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            handle TEXT NOT NULL,
            favorite_genres TEXT NOT NULL,
            streak INTEGER NOT NULL,
            badge TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            reviewer TEXT NOT NULL,
            rating REAL NOT NULL,
            comment TEXT NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            meeting_time TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT DEFAULT '',
            tracking_number TEXT DEFAULT '',
            customer_name TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            address TEXT DEFAULT '',
            city TEXT DEFAULT '',
            state TEXT DEFAULT '',
            pincode TEXT DEFAULT '',
            items_json TEXT DEFAULT '',
            items_count INTEGER NOT NULL DEFAULT 0,
            subtotal INTEGER NOT NULL DEFAULT 0,
            discount INTEGER NOT NULL DEFAULT 0,
            total INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'Confirmed',
            payment_status TEXT NOT NULL DEFAULT 'Paid',
            placed_on TEXT NOT NULL,
            expected_delivery TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            book_id INTEGER,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            cover_url TEXT DEFAULT '',
            price INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            line_total INTEGER NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id)
        );

        CREATE TABLE IF NOT EXISTS borrow_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member_name TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            issue_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            returned INTEGER NOT NULL DEFAULT 0,
            fine INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS wishlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_name TEXT NOT NULL,
            book_id INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS reader_cache (
            book_id INTEGER PRIMARY KEY,
            pages_json TEXT NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(id)
        );

        CREATE TABLE IF NOT EXISTS visitor_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            visitor_key TEXT NOT NULL,
            path TEXT NOT NULL,
            viewed_on TEXT NOT NULL,
            viewed_at TEXT NOT NULL
        );
        """
    )

    ensure_columns(
        cursor,
        "books",
        {
            "source_id": "TEXT",
            "source_name": "TEXT DEFAULT 'local'",
            "sold_count": "INTEGER NOT NULL DEFAULT 0",
            "cover_url": "TEXT DEFAULT ''",
            "text_url": "TEXT DEFAULT ''",
        },
    )
    ensure_columns(
        cursor,
        "orders",
        {
            "order_number": "TEXT DEFAULT ''",
            "tracking_number": "TEXT DEFAULT ''",
            "email": "TEXT DEFAULT ''",
            "phone": "TEXT DEFAULT ''",
            "address": "TEXT DEFAULT ''",
            "city": "TEXT DEFAULT ''",
            "state": "TEXT DEFAULT ''",
            "pincode": "TEXT DEFAULT ''",
            "items_count": "INTEGER NOT NULL DEFAULT 0",
            "subtotal": "INTEGER NOT NULL DEFAULT 0",
            "discount": "INTEGER NOT NULL DEFAULT 0",
            "payment_status": "TEXT NOT NULL DEFAULT 'Paid'",
            "expected_delivery": "TEXT DEFAULT ''",
        },
    )

    add_manual_books(cursor)
    ensure_catalog(cursor)
    backfill_orders(cursor)

    if cursor.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO users (name, handle, favorite_genres, streak, badge) VALUES (?, ?, ?, ?, ?)",
            USER_SEEDS,
        )

    if cursor.execute("SELECT COUNT(*) FROM clubs").fetchone()[0] == 0:
        cursor.executemany(
            "INSERT INTO clubs (name, description, meeting_time) VALUES (?, ?, ?)",
            CLUB_SEEDS,
        )

    if cursor.execute("SELECT COUNT(*) FROM reviews").fetchone()[0] == 0:
        reviewed_books = cursor.execute("SELECT id, title FROM books ORDER BY rating DESC LIMIT 5").fetchall()
        review_rows = []
        demo_reviews = [
            ("Riya", 5, "Strong pacing, beautiful object design, and a genuinely readable preview."),
            ("Advik", 4.5, "Feels like a premium store listing, not a throwaway sample."),
            ("Neel", 4.4, "Loved the real cover treatment and readable page layout."),
            ("Mahi", 4.7, "Clean checkout and polished reader experience."),
            ("Yash", 4.9, "The tracking and admin order view are surprisingly complete."),
        ]
        for idx, row in enumerate(reviewed_books):
            name, rating, comment = demo_reviews[idx % len(demo_reviews)]
            review_rows.append((row["id"], name, rating, comment))
        cursor.executemany(
            "INSERT INTO reviews (book_id, reviewer, rating, comment) VALUES (?, ?, ?, ?)",
            review_rows,
        )

    if cursor.execute("SELECT COUNT(*) FROM wishlist").fetchone()[0] == 0:
        top_books = cursor.execute("SELECT id FROM books ORDER BY rating DESC LIMIT 3").fetchall()
        cursor.executemany("INSERT INTO wishlist (user_name, book_id) VALUES (?, ?)", [("Aanya", row["id"]) for row in top_books])

    if cursor.execute("SELECT COUNT(*) FROM borrow_records").fetchone()[0] == 0:
        today = date.today()
        sample_books = cursor.execute("SELECT id FROM books ORDER BY id LIMIT 3").fetchall()
        borrow_rows = []
        if len(sample_books) >= 3:
            borrow_rows = [
                ("S. Patel", sample_books[0]["id"], str(today - timedelta(days=4)), str(today + timedelta(days=10)), 0, 0),
                ("N. George", sample_books[1]["id"], str(today - timedelta(days=14)), str(today - timedelta(days=2)), 0, 80),
                ("A. Khan", sample_books[2]["id"], str(today - timedelta(days=20)), str(today - timedelta(days=5)), 1, 50),
            ]
        cursor.executemany(
            """
            INSERT INTO borrow_records (member_name, book_id, issue_date, due_date, returned, fine)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            borrow_rows,
        )

    if cursor.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0:
        top_books = cursor.execute("SELECT * FROM books ORDER BY rating DESC LIMIT 4").fetchall()
        if len(top_books) >= 3:
            seed_orders = [
                {
                    "customer_name": "Aanya",
                    "email": "aanya@example.com",
                    "phone": "9876500011",
                    "address": "14 Palm Residency, Sector 62",
                    "city": "Noida",
                    "state": "Uttar Pradesh",
                    "pincode": "201301",
                    "status": "Shipped",
                    "payment_status": "Paid",
                    "placed_on": str(date.today() - timedelta(days=2)),
                    "expected_delivery": str(date.today() + timedelta(days=1)),
                    "items": [top_books[0], top_books[1]],
                },
                {
                    "customer_name": "Vihaan",
                    "email": "vihaan@example.com",
                    "phone": "9811100012",
                    "address": "88 Lake Road",
                    "city": "Kolkata",
                    "state": "West Bengal",
                    "pincode": "700029",
                    "status": "Delivered",
                    "payment_status": "Paid",
                    "placed_on": str(date.today() - timedelta(days=5)),
                    "expected_delivery": str(date.today() - timedelta(days=1)),
                    "items": [top_books[2]],
                },
            ]
            for idx, order in enumerate(seed_orders, start=1):
                order_number = f"BV-{date.today():%Y%m%d}-{idx:04d}"
                tracking_number = f"TRK{date.today():%y%m%d}{idx:04d}"
                subtotal = sum(item["price"] for item in order["items"])
                items_json = json.dumps([{"title": item["title"], "qty": 1} for item in order["items"]])
                cursor.execute(
                    """
                    INSERT INTO orders (
                        order_number, tracking_number, customer_name, email, phone, address, city, state, pincode,
                        items_json, items_count, subtotal, discount, total, status, payment_status, placed_on, expected_delivery
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_number,
                        tracking_number,
                        order["customer_name"],
                        order["email"],
                        order["phone"],
                        order["address"],
                        order["city"],
                        order["state"],
                        order["pincode"],
                        items_json,
                        len(order["items"]),
                        subtotal,
                        0,
                        subtotal,
                        order["status"],
                        order["payment_status"],
                        order["placed_on"],
                        order["expected_delivery"],
                    ),
                )
                order_id = cursor.lastrowid
                for book in order["items"]:
                    cover = book["cover_url"] or f"/cover/{book['id']}.svg"
                    cursor.execute(
                        """
                        INSERT INTO order_items (order_id, book_id, title, author, cover_url, price, qty, line_total)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (order_id, book["id"], book["title"], book["author"], cover, book["price"], 1, book["price"]),
                    )
                    cursor.execute("UPDATE books SET sold_count = sold_count + 1 WHERE id = ?", (book["id"],))

    db.commit()
    db.close()


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "admin":
            flash("Admin login required.")
            return redirect(url_for("auth"))
        return view_func(*args, **kwargs)

    return wrapper


def get_book(book_id: int):
    return query_db("SELECT * FROM books WHERE id = ?", (book_id,), one=True)


def get_cart() -> dict[str, int]:
    return session.setdefault("cart", {})


def is_authenticated_customer() -> bool:
    return bool(session.get("user_email") or session.get("user_phone")) and session.get("role") != "admin"


def queue_post_auth_redirect(book_id: int | None = None) -> None:
    session["post_auth_redirect"] = request.referrer or url_for("store")
    if book_id is not None:
        session["pending_cart_book_id"] = book_id
    session.modified = True


def complete_post_auth_flow():
    pending_cart_book_id = session.pop("pending_cart_book_id", None)
    redirect_target = session.pop("post_auth_redirect", None)
    if pending_cart_book_id is not None:
        book = get_book(int(pending_cart_book_id))
        if book and book["stock"] > 0:
            cart = get_cart()
            key = str(book["id"])
            cart[key] = min(cart.get(key, 0) + 1, book["stock"])
            session.modified = True
            flash(f"{book['title']} added to cart.")
            return redirect(url_for("cart"))
    return redirect(redirect_target or url_for("store"))


def cart_books():
    cart = get_cart()
    items = []
    total = 0
    for book_id, qty in cart.items():
        book = get_book(int(book_id))
        if not book:
            continue
        available_qty = min(qty, max(book["stock"], 0))
        subtotal = book["price"] * available_qty
        total += subtotal
        items.append({"book": book, "qty": available_qty, "subtotal": subtotal})
    return items, total


def clean_gutenberg_text(text: str) -> str:
    start_markers = [
        "*** START OF THE PROJECT GUTENBERG EBOOK",
        "*** START OF THIS PROJECT GUTENBERG EBOOK",
    ]
    end_markers = [
        "*** END OF THE PROJECT GUTENBERG EBOOK",
        "*** END OF THIS PROJECT GUTENBERG EBOOK",
    ]
    for marker in start_markers:
        if marker in text:
            text = text.split(marker, 1)[1]
            break
    for marker in end_markers:
        if marker in text:
            text = text.split(marker, 1)[0]
            break
    lines = [line.strip() for line in text.splitlines()]
    paragraphs = []
    chunk = []
    for line in lines:
        if not line:
            if chunk:
                paragraph = " ".join(chunk).strip()
                if len(paragraph) > 50:
                    paragraphs.append(paragraph)
                chunk = []
            continue
        if line.startswith("Produced by") or line.startswith("Distributed Proofreaders"):
            continue
        chunk.append(re.sub(r"\s+", " ", line))
    if chunk:
        paragraph = " ".join(chunk).strip()
        if len(paragraph) > 50:
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs[:280])


def paginate_reader_text(text: str, page_count: int = 10, target_chars: int = 1800) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 30]
    pages: list[str] = []
    current = []
    current_len = 0

    for paragraph in paragraphs:
        projected = current_len + len(paragraph)
        if projected > target_chars and current and len(pages) < page_count - 1:
            pages.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len = projected

    if current:
        pages.append("\n\n".join(current))

    if len(pages) > page_count:
        pages = pages[: page_count - 1] + ["\n\n".join(pages[page_count - 1 :])]

    if len(pages) < page_count and pages:
        tail = pages[-1]
        sentences = re.split(r"(?<=[.!?])\s+", tail)
        while len(pages) < page_count and len(sentences) > 6:
            midpoint = max(3, len(sentences) // 2)
            pages[-1] = " ".join(sentences[:midpoint]).strip()
            pages.append(" ".join(sentences[midpoint:]).strip())
            sentences = re.split(r"(?<=[.!?])\s+", pages[-1])

    while len(pages) < page_count:
        pages.append("Preview continues in the full edition. This 10-page reader is intentionally capped for store demo use.")

    return [page.strip() for page in pages[:page_count]]


def reader_pages(book) -> list[str]:
    if book["title"] in MANUAL_READER_CONTENT:
        return MANUAL_READER_CONTENT[book["title"]]

    cached = query_db("SELECT pages_json FROM reader_cache WHERE book_id = ?", (book["id"],), one=True)
    if cached:
        return json.loads(cached["pages_json"])

    pages: list[str]
    text_url = book["text_url"] or lookup_gutendex_text_url(book)
    if text_url:
        try:
            raw_text = fetch_text(text_url)
            cleaned = clean_gutenberg_text(raw_text)
            if len(cleaned) > 500:
                pages = paginate_reader_text(cleaned)
            else:
                pages = []
        except (URLError, TimeoutError, ValueError):
            pages = []
    else:
        pages = []

    if not pages:
        pages = [
            f"{book['title']}\n\n{book['summary']}\n\n{book['description']}\n\nThis title does not currently have a readable public-domain text source, so BOOKVERSE AI is showing a metadata preview instead."
            for _ in range(10)
        ]

    execute_db(
        "INSERT OR REPLACE INTO reader_cache (book_id, pages_json) VALUES (?, ?)",
        (book["id"], json.dumps(pages)),
    )
    return pages


def infer_order_status(placed_on: str, current_status: str) -> str:
    if current_status == "Delivered":
        return current_status
    days = max((date.today() - date.fromisoformat(placed_on)).days, 0)
    if days >= 3:
        return "Delivered"
    if days == 2:
        return "Out for Delivery"
    if days == 1:
        return "Shipped"
    return "Confirmed"


def tracking_steps(order) -> list[dict]:
    steps = ["Confirmed", "Packed", "Shipped", "Out for Delivery", "Delivered"]
    status = infer_order_status(order["placed_on"], order["status"])
    cursor = steps.index(status) if status in steps else 0
    return [{"label": step, "done": idx <= cursor} for idx, step in enumerate(steps)]


def get_order(order_id: int):
    return query_db("SELECT * FROM orders WHERE id = ?", (order_id,), one=True)


def get_order_by_number(order_number: str):
    return query_db("SELECT * FROM orders WHERE order_number = ?", (order_number,), one=True)


def order_items(order_id: int):
    return query_db("SELECT * FROM order_items WHERE order_id = ? ORDER BY id", (order_id,))


def build_order_payload(items, form) -> dict:
    name = form.get("name", "").strip() or "Guest Reader"
    email = form.get("email", "").strip() or session.get("user_email", "")
    phone = form.get("phone", "").strip()
    address = form.get("address", "").strip()
    city = form.get("city", "").strip()
    state = form.get("state", "").strip()
    pincode = form.get("pincode", "").strip()
    coupon = form.get("coupon", "").strip().upper()
    discount = 150 if coupon == "BOOKVERSE150" else 0
    subtotal = sum(item["subtotal"] for item in items)
    total = max(subtotal - discount, 0)
    order_number = f"BV-{date.today():%Y%m%d}-{uuid.uuid4().hex[:6].upper()}"
    tracking_number = f"TRK{date.today():%y%m%d}{uuid.uuid4().hex[:5].upper()}"
    return {
        "order_number": order_number,
        "tracking_number": tracking_number,
        "customer_name": name,
        "email": email,
        "phone": phone,
        "address": address,
        "city": city,
        "state": state,
        "pincode": pincode,
        "items_json": json.dumps([{"title": item["book"]["title"], "qty": item["qty"]} for item in items]),
        "items_count": sum(item["qty"] for item in items),
        "subtotal": subtotal,
        "discount": discount,
        "total": total,
        "status": "Confirmed",
        "payment_status": "Paid",
        "placed_on": str(date.today()),
        "expected_delivery": str(date.today() + timedelta(days=3)),
    }


def cover_src(book) -> str:
    return book["cover_url"] or url_for("cover_art", book_id=book["id"])


def filter_books(args):
    query = "SELECT * FROM books WHERE 1=1"
    params = []
    search = args.get("search", "").strip()
    genre = args.get("genre", "").strip()
    author = args.get("author", "").strip()
    language = args.get("language", "").strip()
    rating = args.get("rating", "").strip()
    price = args.get("price", "").strip()
    availability = args.get("availability", "").strip()

    if search:
        like = f"%{search}%"
        query += " AND (title LIKE ? OR author LIKE ? OR genre LIKE ?)"
        params.extend([like, like, like])
    if genre:
        query += " AND genre = ?"
        params.append(genre)
    if author:
        query += " AND author = ?"
        params.append(author)
    if language:
        query += " AND language = ?"
        params.append(language)
    if rating:
        query += " AND rating >= ?"
        params.append(float(rating))
    if price:
        ceilings = {"400": 400, "600": 600, "800": 800, "1200": 1200}
        if price in ceilings:
            query += " AND price <= ?"
            params.append(ceilings[price])
    if availability == "in":
        query += " AND stock > 0"
    if availability == "out":
        query += " AND stock = 0"

    query += " ORDER BY stock = 0 ASC, (text_url = '') ASC, sold_count DESC, trending DESC, rating DESC, id DESC"
    return query_db(query, tuple(params))


def recommendation_groups(books):
    groups = {
        "Happy reads": [],
        "Thrillers tonight": [],
        "Exam prep mode": [],
        "Weekend reads": [],
    }
    for book in books:
        tags = book["mood_tags"].lower()
        if "happy" in tags or "romantic" in tags:
            groups["Happy reads"].append(book)
        if "thriller" in tags or "mysterious" in tags or "night" in tags:
            groups["Thrillers tonight"].append(book)
        if "exam" in tags or "student" in tags or "learning" in tags:
            groups["Exam prep mode"].append(book)
        if "weekend" in tags or "fiction" in tags or "adventure" in tags:
            groups["Weekend reads"].append(book)
    return groups


def booksoul_matches():
    users = query_db("SELECT * FROM users ORDER BY streak DESC")
    books = query_db("SELECT genre, title FROM books ORDER BY rating DESC LIMIT 40")
    shelf = {book["genre"]: book["title"] for book in books}
    matches = []
    for idx, user in enumerate(users):
        partner = users[(idx + 1) % len(users)]
        overlap = set(user["favorite_genres"].split(",")) & set(partner["favorite_genres"].split(","))
        compatibility = 76 + len(overlap) * 8 + min(user["streak"], partner["streak"]) // 10
        genre = next(iter(overlap), "Fiction")
        matches.append(
            {
                "reader": user,
                "partner": partner,
                "compatibility": min(99, compatibility),
                "bond": ", ".join(sorted(overlap)) or "Curiosity",
                "spark_title": shelf.get(genre, "A rich reading overlap"),
            }
        )
    return matches


def analytics_summary():
    total_visitors = query_db("SELECT COUNT(DISTINCT visitor_key) AS total FROM visitor_log", one=True)["total"] or 0
    today = str(date.today())
    today_visitors = query_db("SELECT COUNT(DISTINCT visitor_key) AS total FROM visitor_log WHERE viewed_on = ?", (today,), one=True)["total"] or 0
    page_views = query_db("SELECT COUNT(*) AS total FROM visitor_log", one=True)["total"] or 0
    orders = query_db("SELECT * FROM orders ORDER BY placed_on DESC")
    total_orders = len(orders)
    today_orders = len([order for order in orders if order["placed_on"] == today])
    books_sold = query_db("SELECT COALESCE(SUM(qty), 0) AS total FROM order_items", one=True)["total"] or 0
    today_books_sold = query_db(
        """
        SELECT COALESCE(SUM(order_items.qty), 0) AS total
        FROM order_items
        JOIN orders ON orders.id = order_items.order_id
        WHERE orders.placed_on = ?
        """,
        (today,),
        one=True,
    )["total"] or 0
    revenue = query_db("SELECT COALESCE(SUM(total), 0) AS total FROM orders", one=True)["total"] or 0
    today_revenue = query_db("SELECT COALESCE(SUM(total), 0) AS total FROM orders WHERE placed_on = ?", (today,), one=True)["total"] or 0
    inventory_units = query_db("SELECT COALESCE(SUM(stock), 0) AS total FROM books", one=True)["total"] or 0
    out_of_stock = query_db("SELECT COUNT(*) AS total FROM books WHERE stock = 0", one=True)["total"] or 0
    return {
        "total_visitors": total_visitors,
        "today_visitors": today_visitors,
        "page_views": page_views,
        "total_orders": total_orders,
        "today_orders": today_orders,
        "books_sold": books_sold,
        "today_books_sold": today_books_sold,
        "revenue": revenue,
        "today_revenue": today_revenue,
        "inventory_units": inventory_units,
        "out_of_stock": out_of_stock,
    }


@app.before_request
def track_visits():
    if request.method != "GET":
        return
    if request.endpoint in {"static", "cover_art", "author_avatar"}:
        return
    visitor_key = session.setdefault("visitor_key", uuid.uuid4().hex)
    db = get_db()
    db.execute(
        "INSERT INTO visitor_log (visitor_key, path, viewed_on, viewed_at) VALUES (?, ?, ?, ?)",
        (visitor_key, request.path, str(date.today()), datetime.now().isoformat(timespec="seconds")),
    )
    db.commit()


@app.context_processor
def inject_globals():
    items, total = cart_books()
    user_role = session.get("role", "guest")
    return {
        "cart_count": sum(item["qty"] for item in items),
        "wishlist_count": len(query_db("SELECT * FROM wishlist WHERE user_name = 'Aanya'")),
        "current_year": datetime.now().year,
        "cart_total": total,
        "is_admin": user_role == "admin",
        "is_customer": user_role == "customer",
        "current_user_name": session.get("user_name", "Guest"),
        "current_user_phone": session.get("user_phone", ""),
        "current_user_email": session.get("user_email", ""),
        "current_user_role": user_role,
        "my_orders_count": len(session.get("recent_orders", [])),
    }


def api_response(payload, status: int = 200):
    return jsonify(payload), status


def current_origin() -> str:
    return request.headers.get("Origin", "").rstrip("/")


def origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    if origin in FRONTEND_ORIGINS:
        return True
    if origin.startswith("http://localhost:") or origin.startswith("http://127.0.0.1:"):
        return True
    return origin.endswith(".netlify.app")


def absolute_url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return f"{request.host_url.rstrip('/')}{path}"


def cover_api_src(book) -> str:
    return absolute_url(book["cover_url"] or url_for("cover_art", book_id=book["id"]))


def current_wishlist_owner() -> str:
    return session.get("user_name") or "Aanya"


def session_payload() -> dict:
    items, _total = cart_books()
    return {
        "authenticated": is_authenticated_customer() or session.get("role") == "admin",
        "role": session.get("role", "guest"),
        "user": {
            "name": session.get("user_name", "Guest"),
            "email": session.get("user_email", ""),
            "phone": session.get("user_phone", ""),
        },
        "cart_count": sum(item["qty"] for item in items),
        "wishlist_count": query_db(
            "SELECT COUNT(*) AS total FROM wishlist WHERE user_name = ?",
            (current_wishlist_owner(),),
            one=True,
        )["total"],
        "my_orders_count": len(session.get("recent_orders", [])),
        "is_admin": session.get("role") == "admin",
    }


def serialize_book(book, detail: bool = False) -> dict:
    payload = {
        "id": book["id"],
        "title": book["title"],
        "author": book["author"],
        "genre": book["genre"],
        "price": book["price"],
        "rating": book["rating"],
        "language": book["language"],
        "pages": book["pages"],
        "stock": book["stock"],
        "sold_count": book["sold_count"],
        "cover": cover_api_src(book),
        "description": book["description"],
        "summary": book["summary"],
        "mood_tags": [tag.strip() for tag in book["mood_tags"].split(",") if tag.strip()],
        "excerpt": book["excerpt"],
        "preview_ready": bool(book["text_url"] or book["title"] in MANUAL_READER_CONTENT),
        "featured": bool(book["featured"]),
        "new_arrival": bool(book["new_arrival"]),
        "best_seller": bool(book["best_seller"]),
        "trending": bool(book["trending"]),
    }
    if detail:
        payload["subjects"] = [segment.strip() for segment in book["summary"].split(",") if segment.strip()]
    return payload


def serialize_review(review) -> dict:
    return {
        "id": review["id"],
        "reviewer": review["reviewer"],
        "rating": review["rating"],
        "comment": review["comment"],
    }


def serialize_order_item(item) -> dict:
    return {
        "id": item["id"],
        "book_id": item["book_id"],
        "title": item["title"],
        "author": item["author"],
        "qty": item["qty"],
        "price": item["price"],
        "line_total": item["line_total"],
        "cover": absolute_url(item["cover_url"]),
    }


def serialize_order(order, include_items: bool = False) -> dict:
    payload = {
        "id": order["id"],
        "order_number": order["order_number"],
        "tracking_number": order["tracking_number"],
        "customer_name": order["customer_name"],
        "email": order["email"],
        "phone": order["phone"],
        "address": order["address"],
        "city": order["city"],
        "state": order["state"],
        "pincode": order["pincode"],
        "items_count": order["items_count"],
        "subtotal": order["subtotal"],
        "discount": order["discount"],
        "total": order["total"],
        "status": infer_order_status(order["placed_on"], order["status"]),
        "payment_status": order["payment_status"],
        "placed_on": order["placed_on"],
        "expected_delivery": order["expected_delivery"],
        "steps": tracking_steps(order),
        "print_url": absolute_url(url_for("print_order", order_id=order["id"])),
    }
    if include_items:
        payload["items"] = [serialize_order_item(item) for item in order_items(order["id"])]
    return payload


def serialize_cart():
    items, total = cart_books()
    return {
        "items": [
            {
                "qty": item["qty"],
                "subtotal": item["subtotal"],
                "book": serialize_book(item["book"]),
            }
            for item in items
        ],
        "total": total,
        "count": sum(item["qty"] for item in items),
    }


def ensure_api_customer():
    if is_authenticated_customer():
        return None
    return api_response({"ok": False, "message": "Sign in to continue.", "login_required": True}, 401)


def ensure_api_admin():
    if session.get("role") == "admin":
        return None
    return api_response({"ok": False, "message": "Admin access required."}, 403)


def serialize_booksoul_match(match: dict) -> dict:
    return {
        "reader": dict(match["reader"]),
        "partner": dict(match["partner"]),
        "compatibility": match["compatibility"],
        "bond": match["bond"],
        "spark_title": match["spark_title"],
    }


@app.route("/")
def home():
    books = query_db("SELECT * FROM books ORDER BY stock = 0 ASC, rating DESC, sold_count DESC LIMIT 48")
    featured = query_db("SELECT * FROM books WHERE featured = 1 AND stock > 0 ORDER BY rating DESC LIMIT 4")
    if not featured:
        featured = books[:4]
    trending = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY sold_count DESC, trending DESC, rating DESC LIMIT 8")
    arrivals = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY id DESC LIMIT 8")
    best_sellers = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY sold_count DESC, rating DESC LIMIT 4")
    authors = query_db("SELECT author, AVG(rating) AS rating, COUNT(*) AS titles FROM books GROUP BY author ORDER BY titles DESC, rating DESC LIMIT 6")
    genres = query_db("SELECT genre, COUNT(*) AS count FROM books GROUP BY genre ORDER BY count DESC LIMIT 8")
    return render_template(
        "home.html",
        featured=featured,
        trending=trending,
        arrivals=arrivals,
        best_sellers=best_sellers,
        authors=authors,
        genres=genres,
        books=books,
        catalog_size=query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"],
        recommendation_groups=recommendation_groups(books),
        matches=booksoul_matches()[:3],
    )


@app.route("/store")
def store():
    books = filter_books(request.args)
    facets = {
        "genres": query_db("SELECT DISTINCT genre FROM books ORDER BY genre"),
        "authors": query_db("SELECT DISTINCT author FROM books ORDER BY author LIMIT 200"),
        "languages": query_db("SELECT DISTINCT language FROM books ORDER BY language"),
    }
    counts = {
        "titles": query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"],
        "inventory": query_db("SELECT COALESCE(SUM(stock), 0) AS total FROM books", one=True)["total"],
        "out_of_stock": query_db("SELECT COUNT(*) AS total FROM books WHERE stock = 0", one=True)["total"],
    }
    return render_template("store.html", books=books, facets=facets, counts=counts)


@app.route("/book/<int:book_id>")
def book_detail(book_id: int):
    book = get_book(book_id)
    if not book:
        return redirect(url_for("store"))
    reviews = query_db("SELECT * FROM reviews WHERE book_id = ? ORDER BY id DESC", (book_id,))
    related = query_db(
        "SELECT * FROM books WHERE genre = ? AND id != ? ORDER BY rating DESC, sold_count DESC LIMIT 4",
        (book["genre"], book_id),
    )
    author_books = query_db("SELECT * FROM books WHERE author = ? ORDER BY rating DESC LIMIT 4", (book["author"],))
    return render_template("book_detail.html", book=book, reviews=reviews, related=related, author_books=author_books)


@app.route("/reader/<int:book_id>")
def reader(book_id: int):
    book = get_book(book_id)
    if not book:
        return redirect(url_for("store"))
    pages = reader_pages(book)
    return render_template("reader.html", book=book, reader_pages=pages)


@app.route("/genres")
def genres():
    groups = query_db(
        "SELECT genre, COUNT(*) AS total, AVG(rating) AS avg_rating, MIN(price) AS min_price FROM books GROUP BY genre ORDER BY total DESC"
    )
    return render_template("genres.html", groups=groups)


@app.route("/authors")
def authors():
    writers = query_db(
        "SELECT author, AVG(rating) AS rating, COUNT(*) AS total, SUM(stock) AS stock FROM books GROUP BY author ORDER BY total DESC, rating DESC LIMIT 60"
    )
    return render_template("authors.html", writers=writers)


@app.route("/community")
def community():
    top_readers = query_db("SELECT * FROM users ORDER BY streak DESC")
    challenges = [
        {"name": "30-Day Streak Sprint", "participants": 284, "progress": 72},
        {"name": "Read 12 Books in 12 Weeks", "participants": 131, "progress": 54},
        {"name": "Thriller After Dark", "participants": 89, "progress": 81},
    ]
    discussions = [
        {"topic": "Best plot twists that still feel fair", "replies": 43, "club": "Midnight Margins"},
        {"topic": "What is your exam revision stack this month?", "replies": 28, "club": "Exam Legends"},
        {"topic": "Which public-domain classic actually holds up?", "replies": 36, "club": "Founders & Folios"},
    ]
    return render_template("community.html", top_readers=top_readers, challenges=challenges, discussions=discussions)


@app.route("/clubs")
def clubs():
    club_rows = query_db("SELECT * FROM clubs ORDER BY id")
    return render_template("book_clubs.html", clubs=club_rows)


@app.route("/wishlist")
def wishlist():
    entries = query_db(
        """
        SELECT wishlist.id, wishlist.user_name, books.*
        FROM wishlist
        JOIN books ON books.id = wishlist.book_id
        WHERE wishlist.user_name = 'Aanya'
        ORDER BY wishlist.id DESC
        """
    )
    return render_template("wishlist.html", entries=entries)


@app.post("/wishlist/add/<int:book_id>")
def add_to_wishlist(book_id: int):
    execute_db("INSERT INTO wishlist (user_name, book_id) VALUES ('Aanya', ?)", (book_id,))
    flash("Added to wishlist.")
    return redirect(request.referrer or url_for("store"))


@app.post("/cart/add/<int:book_id>")
def add_to_cart(book_id: int):
    book = get_book(book_id)
    if not book:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "message": "Book not found."}), 404
        return redirect(url_for("store"))
    if not is_authenticated_customer():
        queue_post_auth_redirect(book_id)
        login_url = url_for("auth")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "login_required": True, "redirect": login_url, "message": "Sign in to continue with cart and checkout."}), 401
        flash("Sign in to continue with cart and checkout.")
        return redirect(login_url)
    if book["stock"] <= 0:
        message = "This title is out of stock right now."
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"ok": False, "message": message, "cart_count": sum(item["qty"] for item in cart_books()[0])}), 409
        flash("This title is out of stock right now.")
        return redirect(request.referrer or url_for("store"))
    cart = get_cart()
    key = str(book_id)
    next_qty = cart.get(key, 0) + 1
    cart[key] = min(next_qty, book["stock"])
    session.modified = True
    cart_count = sum(item["qty"] for item in cart_books()[0])
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify(
            {
                "ok": True,
                "message": f"{book['title']} added to cart.",
                "cart_count": cart_count,
                "book_id": book["id"],
                "stock": book["stock"],
            }
        )
    flash("Book added to cart.")
    return redirect(request.referrer or url_for("cart"))


@app.post("/api/cart/add/<int:book_id>")
def api_add_to_cart(book_id: int):
    return add_to_cart(book_id)


@app.route("/cart")
def cart():
    if not is_authenticated_customer():
        queue_post_auth_redirect()
        flash("Sign in to view your cart.")
        return redirect(url_for("auth"))
    items, total = cart_books()
    blind_date = query_db(
        "SELECT * FROM books WHERE genre IN ('Thriller', 'Novel', 'Fiction', 'Classics') AND stock > 0 ORDER BY RANDOM() LIMIT 1",
        one=True,
    )
    return render_template("cart.html", items=items, total=total, blind_date=blind_date)


@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if not is_authenticated_customer():
        queue_post_auth_redirect()
        flash("Sign in to continue to checkout.")
        return redirect(url_for("auth"))
    items, total = cart_books()
    if request.method == "POST" and items:
        payload = build_order_payload(items, request.form)
        if not payload["address"] or not payload["phone"] or not payload["city"] or not payload["pincode"]:
            flash("Please fill name, phone, shipping address, city, state, and pincode.")
            return render_template("checkout.html", items=items, total=total, form=request.form)

        db = get_db()
        db.execute("BEGIN")
        try:
            for item in items:
                latest = db.execute("SELECT stock FROM books WHERE id = ?", (item["book"]["id"],)).fetchone()
                if not latest or latest["stock"] < item["qty"]:
                    raise ValueError(f"{item['book']['title']} is no longer available in the requested quantity.")

            db.execute(
                """
                INSERT INTO orders (
                    order_number, tracking_number, customer_name, email, phone, address, city, state, pincode,
                    items_json, items_count, subtotal, discount, total, status, payment_status, placed_on, expected_delivery
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["order_number"],
                    payload["tracking_number"],
                    payload["customer_name"],
                    payload["email"],
                    payload["phone"],
                    payload["address"],
                    payload["city"],
                    payload["state"],
                    payload["pincode"],
                    payload["items_json"],
                    payload["items_count"],
                    payload["subtotal"],
                    payload["discount"],
                    payload["total"],
                    payload["status"],
                    payload["payment_status"],
                    payload["placed_on"],
                    payload["expected_delivery"],
                ),
            )
            order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            for item in items:
                book = item["book"]
                db.execute(
                    """
                    INSERT INTO order_items (order_id, book_id, title, author, cover_url, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        order_id,
                        book["id"],
                        book["title"],
                        book["author"],
                        book["cover_url"] or f"/cover/{book['id']}.svg",
                        book["price"],
                        item["qty"],
                        item["subtotal"],
                    ),
                )
                db.execute(
                    "UPDATE books SET stock = stock - ?, sold_count = sold_count + ? WHERE id = ?",
                    (item["qty"], item["qty"], book["id"]),
                )
            db.commit()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            flash(str(exc))
            return render_template("checkout.html", items=items, total=total, form=request.form)

        session["cart"] = {}
        session.setdefault("recent_orders", []).append(order_id)
        session["recent_orders"] = session["recent_orders"][-20:]
        session["last_order_number"] = payload["order_number"]
        session["user_email"] = payload["email"]
        session["user_name"] = payload["customer_name"]
        session["role"] = session.get("role", "customer")
        session.modified = True
        flash(f"Payment successful. Order {payload['order_number']} has been placed.")
        return redirect(url_for("track_order", order_number=payload["order_number"]))

    return render_template("checkout.html", items=items, total=total, form={})


@app.route("/my-orders")
def my_orders():
    if not is_authenticated_customer():
        flash("Sign in to view your orders.")
        return redirect(url_for("auth"))
    order_ids = session.get("recent_orders", [])
    rows = []
    for order_id in order_ids:
        order = get_order(order_id)
        if order:
            rows.append(order)
    return render_template("my_orders.html", order_rows=rows)


@app.route("/track/<order_number>")
def track_order(order_number: str):
    order = get_order_by_number(order_number)
    if not order:
        flash("Order not found.")
        return redirect(url_for("my_orders"))
    items = order_items(order["id"])
    return render_template("track_order.html", order=order, items=items, steps=tracking_steps(order))


@app.route("/library")
def library():
    borrow_rows = query_db(
        """
        SELECT borrow_records.*, books.title, books.author
        FROM borrow_records
        JOIN books ON books.id = borrow_records.book_id
        ORDER BY returned ASC, due_date ASC
        """
    )
    members = query_db("SELECT * FROM users ORDER BY streak DESC")
    books = query_db("SELECT * FROM books ORDER BY title LIMIT 120")
    return render_template("library.html", borrow_rows=borrow_rows, members=members, books=books, today=str(date.today()))


@app.post("/library/issue")
def issue_book():
    member = request.form.get("member_name", "Walk-in Member").strip() or "Walk-in Member"
    book_id = int(request.form.get("book_id"))
    issue_date = date.today()
    due_date = issue_date + timedelta(days=14)
    execute_db(
        "INSERT INTO borrow_records (member_name, book_id, issue_date, due_date, returned, fine) VALUES (?, ?, ?, ?, 0, 0)",
        (member, book_id, str(issue_date), str(due_date)),
    )
    flash("Library issue created.")
    return redirect(url_for("library"))


@app.post("/library/return/<int:record_id>")
def return_book(record_id: int):
    row = query_db("SELECT * FROM borrow_records WHERE id = ?", (record_id,), one=True)
    if row:
        overdue_days = max((date.today() - date.fromisoformat(row["due_date"])).days, 0)
        fine = overdue_days * 20
        execute_db("UPDATE borrow_records SET returned = 1, fine = ? WHERE id = ?", (fine, record_id))
        flash("Book return processed.")
    return redirect(url_for("library"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    stats = analytics_summary()
    books = query_db("SELECT * FROM books ORDER BY stock ASC, sold_count DESC LIMIT 8")
    recent_orders = query_db("SELECT * FROM orders ORDER BY placed_on DESC, id DESC LIMIT 6")
    chart_books = query_db("SELECT title, sold_count FROM books ORDER BY sold_count DESC, rating DESC LIMIT 6")
    chart_labels = [book["title"][:24] for book in chart_books]
    chart_sales = [book["sold_count"] for book in chart_books]
    visitor_series = query_db(
        """
        SELECT viewed_on, COUNT(DISTINCT visitor_key) AS total
        FROM visitor_log
        GROUP BY viewed_on
        ORDER BY viewed_on DESC
        LIMIT 7
        """
    )
    visitor_labels = [row["viewed_on"] for row in reversed(visitor_series)]
    visitor_values = [row["total"] for row in reversed(visitor_series)]
    return render_template(
        "dashboard.html",
        stats=stats,
        low_stock=[book for book in books if book["stock"] < 5],
        recent_orders=recent_orders,
        chart_labels=chart_labels,
        chart_sales=chart_sales,
        visitor_labels=visitor_labels,
        visitor_values=visitor_values,
    )


@app.route("/admin/inventory", methods=["GET", "POST"])
@admin_required
def inventory():
    db = get_db()
    if request.method == "POST":
        payload = {key: request.form.get(key, "").strip() for key in ["title", "author", "genre", "language", "description", "summary", "mood_tags", "excerpt", "cover_palette", "cover_url", "text_url"]}
        payload.update(
            {
                "source_id": f"manual-{slugify(payload['title'])}",
                "source_name": "manual",
                "price": int(request.form.get("price") or 0),
                "rating": float(request.form.get("rating") or 4),
                "pages": 10,
                "stock": int(request.form.get("stock") or 10),
                "featured": 1 if request.form.get("featured") else 0,
                "new_arrival": 1 if request.form.get("new_arrival") else 0,
                "best_seller": 1 if request.form.get("best_seller") else 0,
                "trending": 1 if request.form.get("trending") else 0,
            }
        )
        db.execute(
            """
            INSERT INTO books (
                source_id, source_name, title, author, genre, price, rating, language, pages, stock, sold_count,
                cover_palette, cover_url, description, summary, mood_tags, excerpt, text_url,
                featured, new_arrival, best_seller, trending
            ) VALUES (
                :source_id, :source_name, :title, :author, :genre, :price, :rating, :language, :pages, :stock, 0,
                :cover_palette, :cover_url, :description, :summary, :mood_tags, :excerpt, :text_url,
                :featured, :new_arrival, :best_seller, :trending
            )
            """,
            payload,
        )
        db.commit()
        flash("Inventory updated with a new title.")
        return redirect(url_for("inventory"))

    books = query_db("SELECT * FROM books ORDER BY id DESC LIMIT 120")
    total_titles = query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"]
    inventory_units = query_db("SELECT COALESCE(SUM(stock), 0) AS total FROM books", one=True)["total"]
    return render_template("inventory.html", books=books, total_titles=total_titles, inventory_units=inventory_units)


@app.post("/admin/inventory/delete/<int:book_id>")
@admin_required
def delete_book(book_id: int):
    execute_db("DELETE FROM books WHERE id = ?", (book_id,))
    flash("Book removed from inventory.")
    return redirect(url_for("inventory"))


@app.route("/admin/orders")
@admin_required
def orders():
    order_rows = query_db("SELECT * FROM orders ORDER BY placed_on DESC, id DESC LIMIT 80")
    enriched = []
    for order in order_rows:
        enriched.append({"order": order, "line_items": order_items(order["id"]), "steps": tracking_steps(order)})
    return render_template("orders.html", order_rows=enriched)


@app.route("/admin/orders/<int:order_id>/print")
@admin_required
def print_order(order_id: int):
    order = get_order(order_id)
    if not order:
        abort(404)
    items = order_items(order_id)
    return render_template("print_order.html", order=order, items=items)


@app.route("/login", methods=["GET", "POST"])
@app.route("/register", methods=["GET", "POST"])
def auth():
    if request.method == "POST":
        mode = request.form.get("auth_mode", "login").strip().lower()
        identifier = request.form.get("identifier", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        name = request.form.get("name", "").strip() or "Reader"
        phone = request.form.get("phone", "").strip()

        admin_identifier = identifier.lower() if identifier else email
        if admin_identifier == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session["role"] = "admin"
            session["user_name"] = "Bookverse Admin"
            session["user_email"] = ADMIN_EMAIL
            session["user_phone"] = phone or "+91 90000 00000"
            flash("Admin login successful.")
            return redirect(url_for("admin_dashboard"))

        if mode == "register":
            session["role"] = "customer"
            session["user_name"] = name
            session["user_email"] = email
            session["user_phone"] = phone
            flash("Account created. You can continue with your cart.")
            return complete_post_auth_flow()

        normalized_identifier = identifier or email or phone
        inferred_email = normalized_identifier if "@" in normalized_identifier else session.get("user_email", "")
        inferred_phone = normalized_identifier if normalized_identifier.isdigit() else phone or session.get("user_phone", "")
        session["role"] = "customer"
        session["user_name"] = session.get("user_name") or "Reader"
        session["user_email"] = inferred_email
        session["user_phone"] = inferred_phone
        flash("Signed in successfully.")
        return complete_post_auth_flow()

    mode = "register" if request.path.endswith("register") else "login"
    return render_template("auth.html", mode=mode, admin_email=ADMIN_EMAIL, admin_password=ADMIN_PASSWORD)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out.")
    return redirect(url_for("home"))


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/cover/<int:book_id>.svg")
def cover_art(book_id: int):
    book = get_book(book_id)
    if not book:
        return Response(status=404)
    if book["cover_url"]:
        return redirect(book["cover_url"])

    colors = [c.strip() for c in book["cover_palette"].split(",")]
    line_one = " ".join(book["title"].split()[:2])
    line_two = " ".join(book["title"].split()[2:4]) or book["genre"]
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="480" height="720" viewBox="0 0 480 720">
      <defs>
        <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="{colors[0]}"/>
          <stop offset="50%" stop-color="{colors[1] if len(colors) > 1 else colors[0]}"/>
          <stop offset="100%" stop-color="{colors[2] if len(colors) > 2 else colors[0]}"/>
        </linearGradient>
      </defs>
      <rect width="480" height="720" rx="28" fill="url(#g)"/>
      <circle cx="390" cy="120" r="86" fill="rgba(255,255,255,0.12)"/>
      <path d="M70 610 C140 470, 240 500, 340 360" stroke="rgba(255,255,255,0.4)" stroke-width="12" fill="none"/>
      <rect x="52" y="48" width="190" height="34" rx="17" fill="rgba(255,255,255,0.18)"/>
      <text x="68" y="71" fill="white" font-size="18" font-family="Georgia, serif">{escape(book['genre'].upper())}</text>
      <text x="52" y="260" fill="white" font-size="46" font-weight="700" font-family="Georgia, serif">{escape(line_one)}</text>
      <text x="52" y="318" fill="white" font-size="42" font-family="Georgia, serif">{escape(line_two)}</text>
      <text x="52" y="598" fill="white" font-size="24" font-family="Segoe UI, sans-serif">{escape(book['author'])}</text>
      <text x="52" y="640" fill="rgba(255,255,255,0.9)" font-size="18" font-family="Segoe UI, sans-serif">BOOKVERSE AI EDITION</text>
    </svg>
    """
    return Response(dedent(svg), mimetype="image/svg+xml")


@app.route("/author/<name>.svg")
def author_avatar(name: str):
    safe = escape(name.replace("-", " "))
    initials = "".join(part[0] for part in safe.split()[:2]).upper()
    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
      <defs>
        <linearGradient id="a" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0%" stop-color="#f59e0b"/>
          <stop offset="100%" stop-color="#0f766e"/>
        </linearGradient>
      </defs>
      <rect width="320" height="320" rx="160" fill="url(#a)"/>
      <circle cx="160" cy="120" r="52" fill="rgba(255,255,255,0.25)"/>
      <path d="M80 254c18-42 52-66 80-66s62 24 80 66" fill="rgba(255,255,255,0.25)"/>
      <text x="160" y="290" text-anchor="middle" fill="white" font-size="42" font-family="Segoe UI, sans-serif">{initials}</text>
    </svg>
    """
    return Response(dedent(svg), mimetype="image/svg+xml")


@app.post("/api/mood-match")
def mood_match():
    mood = request.json.get("mood", "").lower()
    books = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY sold_count DESC, rating DESC LIMIT 80")
    matches = [book for book in books if mood and mood in book["mood_tags"].lower()]
    if not matches:
        matches = books[:3]
    payload = [
        {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "reason": f"Fits a {mood or 'curious'} reading vibe with tags: {book['mood_tags'].replace(',', ', ')}.",
        }
        for book in matches[:3]
    ]
    return jsonify(payload)


@app.get("/api/booksoul")
def booksoul():
    return jsonify(booksoul_matches())


@app.post("/api/companion")
def companion():
    prompt = request.json.get("prompt", "")
    book_id = int(request.json.get("book_id", 1))
    book = get_book(book_id)
    if not book:
        return jsonify({"answer": "Book not found."})
    answer = f"{book['title']} is best understood through its core subjects: {book['summary'].lower()}."
    if "summary" in prompt.lower():
        answer = f"60-second summary: {book['summary']}"
    elif "character" in prompt.lower():
        answer = f"This edition is being previewed from a real text source, so use the reader pages as the primary ground truth. For {book['title']}, the emotional pull sits in the themes signaled by its genre and opening pages."
    elif "what is this book about" in prompt.lower():
        answer = book["description"]
    return jsonify({"answer": answer})


@app.post("/api/store-assistant")
def store_assistant():
    prompt = request.json.get("prompt", "").strip()
    if not prompt:
        return jsonify({"message": "Type a book topic, title, or subject first.", "books": []}), 400

    tokens = [token for token in re.split(r"\s+", prompt.lower()) if token]
    books = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY (text_url = '') ASC, sold_count DESC, rating DESC LIMIT 300")
    matches = []
    for book in books:
        haystack = " ".join(
            [
                book["title"].lower(),
                book["author"].lower(),
                book["genre"].lower(),
                book["summary"].lower(),
                book["description"].lower(),
                book["mood_tags"].lower(),
            ]
        )
        score = sum(1 for token in tokens if token in haystack)
        if score > 0:
            matches.append((score, book))

    matches.sort(key=lambda item: (item[0], item[1]["rating"], item[1]["sold_count"]), reverse=True)
    top_books = [book for _, book in matches[:6]]
    if not top_books:
        top_books = books[:4]
        message = f"I could not find a direct match for '{prompt}', but here are some strong available options in the store."
    else:
        message = f"Yes, we have available options for '{prompt}'. Here are some strong matches with brief details and ratings."

    payload = [
        {
            "id": book["id"],
            "title": book["title"],
            "author": book["author"],
            "genre": book["genre"],
            "price": book["price"],
            "rating": book["rating"],
            "stock": book["stock"],
            "summary": book["summary"][:180],
            "cover": cover_api_src(book),
        }
        for book in top_books
    ]
    return jsonify({"message": message, "books": payload})


@app.after_request
def apply_api_cors(response):
    if request.path.startswith("/api/"):
        origin = current_origin()
        if origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Vary"] = "Origin"
    return response


@app.route("/api/<path:_path>", methods=["OPTIONS"])
def api_options(_path: str):
    return ("", 204)


@app.get("/api/session")
def api_session():
    return api_response(session_payload())


@app.post("/api/auth/login")
def api_login():
    payload = request.get_json(silent=True) or {}
    identifier = (payload.get("identifier") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    phone = (payload.get("phone") or "").strip()

    admin_identifier = identifier.lower() if identifier else email
    if admin_identifier == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        session["role"] = "admin"
        session["user_name"] = "Bookverse Admin"
        session["user_email"] = ADMIN_EMAIL
        session["user_phone"] = phone or "+91 90000 00000"
        session.modified = True
        return api_response({"ok": True, "message": "Admin login successful.", "session": session_payload()})

    normalized_identifier = identifier or email or phone
    inferred_email = normalized_identifier if "@" in normalized_identifier else session.get("user_email", "")
    inferred_phone = normalized_identifier if normalized_identifier.isdigit() else phone or session.get("user_phone", "")
    session["role"] = "customer"
    session["user_name"] = session.get("user_name") or "Reader"
    session["user_email"] = inferred_email
    session["user_phone"] = inferred_phone
    session.modified = True
    return api_response({"ok": True, "message": "Signed in successfully.", "session": session_payload()})


@app.post("/api/auth/register")
def api_register():
    payload = request.get_json(silent=True) or {}
    session["role"] = "customer"
    session["user_name"] = (payload.get("name") or "Reader").strip() or "Reader"
    session["user_email"] = (payload.get("email") or "").strip().lower()
    session["user_phone"] = (payload.get("phone") or "").strip()
    session.modified = True
    return api_response({"ok": True, "message": "Account created.", "session": session_payload()})


@app.post("/api/auth/logout")
def api_logout():
    session.clear()
    return api_response({"ok": True, "message": "Signed out."})


@app.get("/api/home")
def api_home():
    books = query_db("SELECT * FROM books ORDER BY stock = 0 ASC, rating DESC, sold_count DESC LIMIT 48")
    featured = query_db("SELECT * FROM books WHERE featured = 1 AND stock > 0 ORDER BY rating DESC LIMIT 4")
    if not featured:
        featured = books[:4]
    trending = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY sold_count DESC, trending DESC, rating DESC LIMIT 8")
    arrivals = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY id DESC LIMIT 8")
    best_sellers = query_db("SELECT * FROM books WHERE stock > 0 ORDER BY sold_count DESC, rating DESC LIMIT 4")
    authors = query_db("SELECT author, AVG(rating) AS rating, COUNT(*) AS titles FROM books GROUP BY author ORDER BY titles DESC, rating DESC LIMIT 6")
    genres = query_db("SELECT genre, COUNT(*) AS count FROM books GROUP BY genre ORDER BY count DESC LIMIT 8")
    rec_groups = {}
    for label, group in recommendation_groups(books).items():
        rec_groups[label] = [serialize_book(book) for book in group[:4]]
    return api_response(
        {
            "featured": [serialize_book(book) for book in featured],
            "trending": [serialize_book(book) for book in trending],
            "arrivals": [serialize_book(book) for book in arrivals],
            "best_sellers": [serialize_book(book) for book in best_sellers],
            "authors": [{"author": row["author"], "rating": round(row["rating"] or 0, 1), "titles": row["titles"]} for row in authors],
            "genres": [{"genre": row["genre"], "count": row["count"]} for row in genres],
            "catalog_size": query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"],
            "recommendation_groups": rec_groups,
            "matches": [serialize_booksoul_match(match) for match in booksoul_matches()[:3]],
        }
    )


@app.get("/api/store")
def api_store():
    books = filter_books(request.args)
    facets = {
        "genres": [row["genre"] for row in query_db("SELECT DISTINCT genre FROM books ORDER BY genre")],
        "authors": [row["author"] for row in query_db("SELECT DISTINCT author FROM books ORDER BY author LIMIT 200")],
        "languages": [row["language"] for row in query_db("SELECT DISTINCT language FROM books ORDER BY language")],
    }
    counts = {
        "titles": query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"],
        "inventory": query_db("SELECT COALESCE(SUM(stock), 0) AS total FROM books", one=True)["total"],
        "out_of_stock": query_db("SELECT COUNT(*) AS total FROM books WHERE stock = 0", one=True)["total"],
    }
    return api_response({"books": [serialize_book(book) for book in books], "facets": facets, "counts": counts})


@app.get("/api/books/<int:book_id>")
def api_book_detail(book_id: int):
    book = get_book(book_id)
    if not book:
        return api_response({"ok": False, "message": "Book not found."}, 404)
    reviews = query_db("SELECT * FROM reviews WHERE book_id = ? ORDER BY id DESC", (book_id,))
    related = query_db(
        "SELECT * FROM books WHERE genre = ? AND id != ? ORDER BY rating DESC, sold_count DESC LIMIT 4",
        (book["genre"], book_id),
    )
    author_books = query_db("SELECT * FROM books WHERE author = ? ORDER BY rating DESC LIMIT 4", (book["author"],))
    return api_response(
        {
            "book": serialize_book(book, detail=True),
            "reviews": [serialize_review(review) for review in reviews],
            "related": [serialize_book(row) for row in related],
            "author_books": [serialize_book(row) for row in author_books],
        }
    )


@app.get("/api/books/<int:book_id>/reader")
def api_book_reader(book_id: int):
    book = get_book(book_id)
    if not book:
        return api_response({"ok": False, "message": "Book not found."}, 404)
    return api_response({"book": serialize_book(book, detail=True), "pages": reader_pages(book)})


@app.get("/api/genres")
def api_genres():
    groups = query_db(
        "SELECT genre, COUNT(*) AS total, AVG(rating) AS avg_rating, MIN(price) AS min_price FROM books GROUP BY genre ORDER BY total DESC"
    )
    return api_response(
        {
            "genres": [
                {
                    "genre": row["genre"],
                    "total": row["total"],
                    "avg_rating": round(row["avg_rating"] or 0, 1),
                    "min_price": row["min_price"],
                }
                for row in groups
            ]
        }
    )


@app.get("/api/authors")
def api_authors():
    writers = query_db(
        "SELECT author, AVG(rating) AS rating, COUNT(*) AS total, SUM(stock) AS stock FROM books GROUP BY author ORDER BY total DESC, rating DESC LIMIT 60"
    )
    return api_response(
        {
            "authors": [
                {
                    "author": row["author"],
                    "rating": round(row["rating"] or 0, 1),
                    "total": row["total"],
                    "stock": row["stock"] or 0,
                    "avatar": absolute_url(url_for("author_avatar", name=slugify(row["author"]))),
                }
                for row in writers
            ]
        }
    )


@app.get("/api/community")
def api_community():
    top_readers = query_db("SELECT * FROM users ORDER BY streak DESC")
    challenges = [
        {"name": "30-Day Streak Sprint", "participants": 284, "progress": 72},
        {"name": "Read 12 Books in 12 Weeks", "participants": 131, "progress": 54},
        {"name": "Thriller After Dark", "participants": 89, "progress": 81},
    ]
    discussions = [
        {"topic": "Best plot twists that still feel fair", "replies": 43, "club": "Midnight Margins"},
        {"topic": "What is your exam revision stack this month?", "replies": 28, "club": "Exam Legends"},
        {"topic": "Which public-domain classic actually holds up?", "replies": 36, "club": "Founders & Folios"},
    ]
    return api_response(
        {
            "top_readers": [dict(row) for row in top_readers],
            "challenges": challenges,
            "discussions": discussions,
            "matches": [serialize_booksoul_match(match) for match in booksoul_matches()],
        }
    )


@app.get("/api/clubs")
def api_clubs():
    return api_response({"clubs": [dict(row) for row in query_db("SELECT * FROM clubs ORDER BY id")]})


@app.get("/api/wishlist")
def api_wishlist():
    guard = ensure_api_customer()
    if guard:
        return guard
    entries = query_db(
        """
        SELECT wishlist.id AS wishlist_id, books.*
        FROM wishlist
        JOIN books ON books.id = wishlist.book_id
        WHERE wishlist.user_name = ?
        ORDER BY wishlist.id DESC
        """,
        (current_wishlist_owner(),),
    )
    return api_response({"entries": [{"wishlist_id": row["wishlist_id"], "book": serialize_book(row)} for row in entries]})


@app.post("/api/wishlist/add/<int:book_id>")
def api_add_wishlist(book_id: int):
    guard = ensure_api_customer()
    if guard:
        return guard
    execute_db("INSERT INTO wishlist (user_name, book_id) VALUES (?, ?)", (current_wishlist_owner(), book_id))
    return api_response({"ok": True, "message": "Added to wishlist."})


@app.get("/api/cart")
def api_cart():
    guard = ensure_api_customer()
    if guard:
        return guard
    blind_date = query_db(
        "SELECT * FROM books WHERE genre IN ('Thriller', 'Novel', 'Fiction', 'Classics') AND stock > 0 ORDER BY RANDOM() LIMIT 1",
        one=True,
    )
    payload = serialize_cart()
    payload["blind_date"] = serialize_book(blind_date) if blind_date else None
    return api_response(payload)


@app.post("/api/cart/remove/<int:book_id>")
def api_remove_cart(book_id: int):
    guard = ensure_api_customer()
    if guard:
        return guard
    cart = get_cart()
    cart.pop(str(book_id), None)
    session.modified = True
    return api_response({"ok": True, "message": "Removed from cart.", "cart": serialize_cart()})


@app.post("/api/checkout")
def api_checkout():
    guard = ensure_api_customer()
    if guard:
        return guard
    items, total = cart_books()
    if not items:
        return api_response({"ok": False, "message": "Your cart is empty."}, 400)

    payload_json = request.get_json(silent=True) or {}
    form = {key: str(payload_json.get(key, "")).strip() for key in ["name", "email", "phone", "address", "city", "state", "pincode", "coupon"]}
    payload = build_order_payload(items, form)
    if not payload["address"] or not payload["phone"] or not payload["city"] or not payload["pincode"]:
        return api_response({"ok": False, "message": "Fill shipping address, phone, city, state, and pincode."}, 400)

    db = get_db()
    db.execute("BEGIN")
    try:
        for item in items:
            latest = db.execute("SELECT stock FROM books WHERE id = ?", (item["book"]["id"],)).fetchone()
            if not latest or latest["stock"] < item["qty"]:
                raise ValueError(f"{item['book']['title']} is no longer available in the requested quantity.")
        db.execute(
            """
            INSERT INTO orders (
                order_number, tracking_number, customer_name, email, phone, address, city, state, pincode,
                items_json, items_count, subtotal, discount, total, status, payment_status, placed_on, expected_delivery
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload["order_number"],
                payload["tracking_number"],
                payload["customer_name"],
                payload["email"],
                payload["phone"],
                payload["address"],
                payload["city"],
                payload["state"],
                payload["pincode"],
                payload["items_json"],
                payload["items_count"],
                payload["subtotal"],
                payload["discount"],
                payload["total"],
                payload["status"],
                payload["payment_status"],
                payload["placed_on"],
                payload["expected_delivery"],
            ),
        )
        order_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        for item in items:
            book = item["book"]
            db.execute(
                """
                INSERT INTO order_items (order_id, book_id, title, author, cover_url, price, qty, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    book["id"],
                    book["title"],
                    book["author"],
                    book["cover_url"] or f"/cover/{book['id']}.svg",
                    book["price"],
                    item["qty"],
                    item["subtotal"],
                ),
            )
            db.execute("UPDATE books SET stock = stock - ?, sold_count = sold_count + ? WHERE id = ?", (item["qty"], item["qty"], book["id"]))
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        return api_response({"ok": False, "message": str(exc)}, 400)

    session["cart"] = {}
    session.setdefault("recent_orders", []).append(order_id)
    session["recent_orders"] = session["recent_orders"][-20:]
    session["last_order_number"] = payload["order_number"]
    session["user_email"] = payload["email"]
    session["user_name"] = payload["customer_name"]
    session["role"] = session.get("role", "customer")
    session.modified = True
    order = get_order(order_id)
    return api_response({"ok": True, "message": "Payment successful. Order placed.", "order": serialize_order(order, include_items=True)})


@app.get("/api/orders/mine")
def api_orders_mine():
    guard = ensure_api_customer()
    if guard:
        return guard
    rows = []
    for order_id in session.get("recent_orders", []):
        order = get_order(order_id)
        if order:
            rows.append(serialize_order(order, include_items=True))
    return api_response({"orders": rows})


@app.get("/api/orders/track/<order_number>")
def api_track_order(order_number: str):
    order = get_order_by_number(order_number)
    if not order:
        return api_response({"ok": False, "message": "Order not found."}, 404)
    return api_response({"order": serialize_order(order, include_items=True)})


@app.get("/api/admin/dashboard")
def api_admin_dashboard():
    guard = ensure_api_admin()
    if guard:
        return guard
    stats = analytics_summary()
    books = query_db("SELECT * FROM books ORDER BY stock ASC, sold_count DESC LIMIT 8")
    recent_orders = query_db("SELECT * FROM orders ORDER BY placed_on DESC, id DESC LIMIT 6")
    chart_books = query_db("SELECT title, sold_count FROM books ORDER BY sold_count DESC, rating DESC LIMIT 6")
    visitor_series = query_db(
        """
        SELECT viewed_on, COUNT(DISTINCT visitor_key) AS total
        FROM visitor_log
        GROUP BY viewed_on
        ORDER BY viewed_on DESC
        LIMIT 7
        """
    )
    return api_response(
        {
            "stats": stats,
            "low_stock": [serialize_book(book) for book in books if book["stock"] < 5],
            "recent_orders": [serialize_order(order) for order in recent_orders],
            "sales_chart": {
                "labels": [row["title"][:24] for row in chart_books],
                "values": [row["sold_count"] for row in chart_books],
            },
            "visitor_chart": {
                "labels": [row["viewed_on"] for row in reversed(visitor_series)],
                "values": [row["total"] for row in reversed(visitor_series)],
            },
        }
    )


@app.route("/api/admin/inventory", methods=["GET", "POST"])
def api_admin_inventory():
    guard = ensure_api_admin()
    if guard:
        return guard
    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        payload = {
            "source_id": f"manual-{slugify(body.get('title', 'manual-book'))}",
            "source_name": "manual",
            "title": str(body.get("title", "")).strip(),
            "author": str(body.get("author", "")).strip() or "Unknown Author",
            "genre": str(body.get("genre", "")).strip() or "Fiction",
            "language": str(body.get("language", "")).strip() or "English",
            "description": str(body.get("description", "")).strip(),
            "summary": str(body.get("summary", "")).strip(),
            "mood_tags": str(body.get("mood_tags", "weekend,fiction")).strip(),
            "excerpt": str(body.get("excerpt", "")).strip(),
            "cover_palette": str(body.get("cover_palette", "#111827,#334155,#cbd5e1")).strip(),
            "cover_url": str(body.get("cover_url", "")).strip(),
            "text_url": str(body.get("text_url", "")).strip(),
            "price": int(body.get("price") or 0),
            "rating": float(body.get("rating") or 4.2),
            "pages": int(body.get("pages") or 10),
            "stock": int(body.get("stock") or 10),
            "featured": 1 if body.get("featured") else 0,
            "new_arrival": 1 if body.get("new_arrival") else 0,
            "best_seller": 1 if body.get("best_seller") else 0,
            "trending": 1 if body.get("trending") else 0,
        }
        get_db().execute(
            """
            INSERT INTO books (
                source_id, source_name, title, author, genre, price, rating, language, pages, stock, sold_count,
                cover_palette, cover_url, description, summary, mood_tags, excerpt, text_url,
                featured, new_arrival, best_seller, trending
            ) VALUES (
                :source_id, :source_name, :title, :author, :genre, :price, :rating, :language, :pages, :stock, 0,
                :cover_palette, :cover_url, :description, :summary, :mood_tags, :excerpt, :text_url,
                :featured, :new_arrival, :best_seller, :trending
            )
            """,
            payload,
        )
        get_db().commit()
        return api_response({"ok": True, "message": "Inventory updated."})

    books = query_db("SELECT * FROM books ORDER BY id DESC LIMIT 120")
    return api_response(
        {
            "books": [serialize_book(book) for book in books],
            "total_titles": query_db("SELECT COUNT(*) AS total FROM books", one=True)["total"],
            "inventory_units": query_db("SELECT COALESCE(SUM(stock), 0) AS total FROM books", one=True)["total"],
        }
    )


@app.post("/api/admin/inventory/delete/<int:book_id>")
def api_admin_delete_book(book_id: int):
    guard = ensure_api_admin()
    if guard:
        return guard
    execute_db("DELETE FROM books WHERE id = ?", (book_id,))
    return api_response({"ok": True, "message": "Book removed."})


@app.get("/api/admin/orders")
def api_admin_orders():
    guard = ensure_api_admin()
    if guard:
        return guard
    order_rows = query_db("SELECT * FROM orders ORDER BY placed_on DESC, id DESC LIMIT 80")
    return api_response({"orders": [serialize_order(order, include_items=True) for order in order_rows]})


@app.errorhandler(404)
def not_found(_error):
    return redirect(url_for("home"))


init_db()


if __name__ == "__main__":
    app.run(debug=True)
