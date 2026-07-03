from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import fitz
from flask import Flask, abort, redirect, render_template, request, send_file, url_for
from PIL import Image
from werkzeug.utils import secure_filename


APP_ROOT = Path(__file__).resolve().parent
DEFAULT_LIBRARY = APP_ROOT / "pdfs_books"
LIBRARY_ROOT = Path(os.environ.get("PDF_LIBRARY_ROOT", DEFAULT_LIBRARY)).resolve()
THUMB_CACHE = APP_ROOT / ".cache" / "covers"
THUMB_CACHE.mkdir(parents=True, exist_ok=True)
LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class Book:
    id: str
    title: str
    path: Path
    relative_path: str
    page_count: int
    file_size: int

    @property
    def size_label(self) -> str:
        size_mb = self.file_size / (1024 * 1024)
        return f"{size_mb:.1f} MB"


app = Flask(__name__)
_BOOK_CACHE: dict[str, Book] = {}


def reset_book_cache() -> None:
    global _BOOK_CACHE
    _BOOK_CACHE = {}


def book_id_for(path: Path) -> str:
    return hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]


def clean_title(path: Path, metadata_title: str | None) -> str:
    if metadata_title and metadata_title.strip():
        return metadata_title.strip()
    stem = path.stem.replace("_", " ").replace("  ", " ").strip()
    return stem or path.name


def discover_books(root: Path) -> dict[str, Book]:
    books: dict[str, Book] = {}
    for pdf_path in sorted(root.rglob("*.pdf")):
        try:
            with fitz.open(pdf_path) as document:
                metadata = document.metadata or {}
                page_count = document.page_count
        except Exception:
            continue

        book = Book(
            id=book_id_for(pdf_path),
            title=clean_title(pdf_path, metadata.get("title")),
            path=pdf_path,
            relative_path=str(pdf_path.relative_to(root)),
            page_count=page_count,
            file_size=pdf_path.stat().st_size,
        )
        books[book.id] = book
    return books


def get_books() -> dict[str, Book]:
    global _BOOK_CACHE
    if not _BOOK_CACHE:
        _BOOK_CACHE = discover_books(LIBRARY_ROOT)
    return _BOOK_CACHE


def allowed_pdf(filename: str) -> bool:
    return filename.lower().endswith(".pdf")


def unique_destination(filename: str) -> Path:
    safe_name = secure_filename(filename) or "book.pdf"
    stem = Path(safe_name).stem or "book"
    suffix = Path(safe_name).suffix or ".pdf"
    candidate = LIBRARY_ROOT / f"{stem}{suffix}"
    counter = 1

    while candidate.exists():
        candidate = LIBRARY_ROOT / f"{stem}_{counter}{suffix}"
        counter += 1

    return candidate


def first_page_cover(document: fitz.Document) -> Image.Image:
    page = document.load_page(0)
    page_area = page.rect.width * page.rect.height
    largest_candidate: tuple[float, bytes] | None = None

    for image_info in page.get_images(full=True):
        xref = image_info[0]
        try:
            rects = page.get_image_rects(xref)
        except Exception:
            rects = []
        if not rects:
            continue

        largest_rect = max(rects, key=lambda rect: rect.width * rect.height)
        coverage = (largest_rect.width * largest_rect.height) / max(page_area, 1)
        if coverage < 0.45:
            continue

        try:
            extracted = document.extract_image(xref)
        except Exception:
            continue
        image_bytes = extracted.get("image")
        if not image_bytes:
            continue
        if largest_candidate is None or coverage > largest_candidate[0]:
            largest_candidate = (coverage, image_bytes)

    if largest_candidate:
        return Image.open(io.BytesIO(largest_candidate[1])).convert("RGB")

    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
    return Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")


def thumbnail_path(book: Book) -> Path:
    digest = hashlib.sha1(
        f"{book.path}:{book.path.stat().st_mtime_ns}".encode("utf-8")
    ).hexdigest()
    return THUMB_CACHE / f"{digest}.jpg"


def build_thumbnail(book: Book) -> Path:
    target = thumbnail_path(book)
    if target.exists():
        return target

    with fitz.open(book.path) as document:
        image = first_page_cover(document)

    image.thumbnail((420, 620))
    canvas = Image.new("RGB", (420, 620), "#f2eee7")
    offset_x = (420 - image.width) // 2
    offset_y = (620 - image.height) // 2
    canvas.paste(image, (offset_x, offset_y))
    canvas.save(target, format="JPEG", quality=88, optimize=True)
    return target


def book_list(books: Iterable[Book]) -> list[dict[str, str | int]]:
    items: list[dict[str, str | int]] = []
    for book in books:
        items.append(
            {
                "id": book.id,
                "title": book.title,
                "relative_path": book.relative_path,
                "page_count": book.page_count,
                "size_label": book.size_label,
                "cover_url": url_for("cover_image", book_id=book.id),
                "reader_url": url_for("reader", book_id=book.id),
            }
        )
    return items


@app.route("/")
def library() -> str:
    books = sorted(get_books().values(), key=lambda book: book.title.lower())
    upload_status = request.args.get("upload")
    return render_template(
        "library.html",
        books=book_list(books),
        library_root=str(LIBRARY_ROOT),
        book_count=len(books),
        has_books=bool(books),
        upload_status=upload_status,
    )


@app.route("/upload", methods=["POST"])
def upload_book():
    LIBRARY_ROOT.mkdir(parents=True, exist_ok=True)
    uploaded = request.files.get("pdf_file")
    if uploaded is None or not uploaded.filename:
        return redirect(url_for("library", upload="missing"))
    if not allowed_pdf(uploaded.filename):
        return redirect(url_for("library", upload="invalid"))

    destination = unique_destination(uploaded.filename)
    uploaded.save(destination)
    reset_book_cache()
    return redirect(url_for("library", upload="success"))


@app.route("/reader/<book_id>")
def reader(book_id: str) -> str:
    book = get_books().get(book_id)
    if not book:
        abort(404)
    return render_template(
        "reader.html",
        book={
            "id": book.id,
            "title": book.title,
            "relative_path": book.relative_path,
            "page_count": book.page_count,
            "size_label": book.size_label,
            "cover_url": url_for("cover_image", book_id=book.id),
            "pdf_url": url_for("pdf_file", book_id=book.id),
        },
    )


@app.route("/cover/<book_id>.jpg")
def cover_image(book_id: str):
    book = get_books().get(book_id)
    if not book:
        abort(404)
    return send_file(build_thumbnail(book), mimetype="image/jpeg", max_age=86400)


@app.route("/pdf/<book_id>")
def pdf_file(book_id: str):
    book = get_books().get(book_id)
    if not book:
        abort(404)
    return send_file(book.path, mimetype="application/pdf", download_name=book.path.name)


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
