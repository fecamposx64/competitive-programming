#!/usr/bin/env python3
"""Baixa, de modo rastreável, materiais de provas do histórico da Maratona SBC.

O site histórico não segue um único padrão entre todas as edições. Por isso, o
script descobre páginas e arquivos a partir dos links publicados no próprio
domínio, em vez de adivinhar nomes de arquivos. Use --dry-run primeiro.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin, urlparse, urlunparse
from urllib.request import Request, urlopen


BASE = "https://maratona.sbc.org.br"
HISTORY_URL = f"{BASE}/hist/"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = ROOT / "simulados-sbc"
ALLOWED_HOSTS = {"maratona.sbc.org.br", "www.maratona.sbc.org.br"}
ARTIFACT_EXTENSIONS = {".pdf", ".tar", ".tgz", ".gz", ".zip", ".rar", ".7z"}
STAGE_TOKENS = {
    "primeira-fase": ("primeira", "fase", "primfase", "subbr", "regional"),
    "final": ("final",),
}


@dataclass(frozen=True)
class Link:
    url: str
    text: str


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[Link] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href:
            self.links.append(Link(self._href, " ".join(self._parts).strip()))
            self._href = None
            self._parts = []


def fetch(url: str) -> tuple[bytes, str]:
    """Fetch one official URL, with a clear user agent and bounded retries."""
    if urlparse(url).hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Refusing non-official URL: {url}")
    request = Request(url, headers={"User-Agent": "cp-study-sbc-fetcher/1.0 (personal study)"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:  # nosec B310: host is allowlisted above
                return response.read(), response.headers.get_content_type()
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            time.sleep(1 + attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def links_from(html: bytes, page_url: str) -> list[Link]:
    parser = LinkParser()
    parser.feed(html.decode("utf-8", errors="replace"))
    links: list[Link] = []
    for link in parser.links:
        absolute = urljoin(page_url, link.url)
        parsed = urlparse(absolute)
        absolute = urlunparse(parsed._replace(path=quote(parsed.path, safe="/%:@")))
        if urlparse(absolute).hostname in ALLOWED_HOSTS:
            links.append(Link(absolute, link.text))
    return links


def year_pages(year: int) -> list[Link]:
    page_url = f"{BASE}/hist/{year}/index.html"
    try:
        html, _ = fetch(page_url)
    except RuntimeError:
        history, _ = fetch(HISTORY_URL)
        candidates = [link for link in links_from(history, HISTORY_URL)
                      if str(year) in link.text and f"/hist/{year}/" in urlparse(link.url).path]
        if not candidates:
            raise
        page_url = candidates[0].url
        html, _ = fetch(page_url)
    candidates = [Link(page_url, "index")]
    for link in links_from(html, page_url):
        path = urlparse(link.url).path.lower()
        noise = ("report", "resultado", "score", "runs", "statistic", "clarification")
        if (path.endswith((".html", ".htm")) and f"/hist/{year}/" in path
                and not any(token in path for token in noise)):
            candidates.append(link)
    unique: dict[str, Link] = {link.url: link for link in candidates}
    return list(unique.values())


def page_matches_stage(link: Link, stage: str) -> bool:
    if stage == "all":
        return True
    haystack = f"{link.url} {link.text}".lower()
    return any(token in haystack for token in STAGE_TOKENS[stage])


def classify(link: Link) -> str | None:
    haystack = f"{link.url} {link.text}".lower()
    if any(token in haystack for token in ("editorial", "solu", "solution")):
        return "editorial"
    if any(token in haystack for token in ("package", "testset", "tests", "entradas", "saídas", "saidas", "input", "output")):
        return "packages"
    if any(token in haystack for token in ("aquec", "warmup", "warm-up")):
        return "warmup"
    if any(token in haystack for token in ("informa", "info_")):
        return "info"
    if any(token in haystack for token in ("contest", "maratona", "problema", "prova", "task")):
        return "contest"
    return None


def artifact_links(page: Link, include: set[str], pdf_only: bool) -> Iterable[tuple[Link, str]]:
    html, content_type = fetch(page.url)
    if content_type != "text/html":
        return []
    selected: list[tuple[Link, str]] = []
    for link in links_from(html, page.url):
        suffix = Path(urlparse(link.url).path).suffix.lower()
        if suffix not in ARTIFACT_EXTENSIONS:
            continue
        if pdf_only and suffix != ".pdf":
            continue
        haystack = f"{link.url} {link.text}".lower()
        if any(token in haystack for token in ("placar", "score", "statistic", "runs", "clarification")):
            continue
        kind = classify(link)
        # Arquivos compactados vinculados por páginas antigas nem sempre dizem
        # "package" no texto (por exemplo, warmup_2010.zip). No histórico SBC,
        # eles são pacotes de testes, não enunciados.
        if suffix != ".pdf" and kind in (None, "contest", "warmup"):
            kind = "packages"
        if kind is not None and kind in include:
            selected.append((link, kind))
    return selected


def safe_name(url: str) -> str:
    name = Path(urlparse(url).path).name
    return re.sub(r"[^A-Za-z0-9._-]", "_", name) or "download"


def stage_dir_name(page: Link) -> str:
    text = f"{page.text} {Path(urlparse(page.url).path).stem}".lower()
    if any(token in text for token in STAGE_TOKENS["primeira-fase"]):
        return "primeira-fase"
    if "final" in text:
        return "final"
    return re.sub(r"[^a-z0-9]+", "-", Path(urlparse(page.url).path).stem.lower()).strip("-")


def save(year: int, page: Link, items: Iterable[tuple[Link, str]], dry_run: bool, refresh: bool) -> int:
    destination = OUTPUT_ROOT / str(year) / stage_dir_name(page)
    downloads = destination / "downloads"
    records: list[dict[str, str | int]] = []
    count = 0
    for link, kind in items:
        target = downloads / safe_name(link.url)
        print(f"[{year}/{stage_dir_name(page)}] {kind:9} {link.url}")
        count += 1
        if dry_run:
            continue
        if target.exists() and not refresh:
            content = target.read_bytes()
        else:
            time.sleep(0.8)
            content, _ = fetch(link.url)
            downloads.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        records.append({
            "kind": kind,
            "source_url": link.url,
            "path": str(target.relative_to(destination)),
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    if records:
        destination.mkdir(parents=True, exist_ok=True)
        manifest = {
            "year": year,
            "page": page.url,
            "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
            "artifacts": records,
        }
        (destination / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return count


def list_years() -> list[int]:
    html, _ = fetch(HISTORY_URL)
    years = {int(match) for match in re.findall(r"/hist/(19\d{2}|20\d{2})/", html.decode("utf-8", errors="ignore"))}
    return sorted(years)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, action="append", help="Edição a baixar; pode repetir.")
    parser.add_argument("--stage", choices=("all", "primeira-fase", "final"), default="all")
    parser.add_argument("--include", default="contest,warmup,editorial,packages,info",
                        help="Categorias: contest,warmup,editorial,packages,info")
    parser.add_argument("--dry-run", action="store_true", help="Mostra os downloads sem gravar arquivos.")
    parser.add_argument("--pdf-only", action="store_true", help="Baixa somente PDFs; ignora pacotes e outros formatos.")
    parser.add_argument("--refresh", action="store_true", help="Baixa novamente arquivos já existentes.")
    parser.add_argument("--list-years", action="store_true", help="Lista anos disponíveis no histórico e sai.")
    args = parser.parse_args()

    if args.list_years:
        print(" ".join(map(str, list_years())))
        return 0
    if not args.year:
        parser.error("informe ao menos um --year (ou use --list-years)")
    include = {part.strip() for part in args.include.split(",") if part.strip()}
    valid = {"contest", "warmup", "editorial", "packages", "info"}
    invalid = include - valid
    if invalid:
        parser.error(f"categorias inválidas: {', '.join(sorted(invalid))}")

    found = 0
    for year in args.year:
        try:
            pages = [page for page in year_pages(year) if page_matches_stage(page, args.stage)]
        except Exception as error:  # A missing legacy page must not stop later years.
            print(f"Aviso: não foi possível listar {year}: {error}", file=sys.stderr)
            continue
        if not pages:
            print(f"Nenhuma página de fase encontrada para {year} ({args.stage}).", file=sys.stderr)
            continue
        seen_artifacts: set[str] = set()
        for page in pages:
            time.sleep(0.8)
            try:
                items = [(link, kind) for link, kind in artifact_links(page, include, args.pdf_only)
                         if link.url not in seen_artifacts]
            except Exception as error:  # Historical links occasionally point to malformed/removed pages.
                print(f"Aviso: ignorando {page.url}: {error}", file=sys.stderr)
                continue
            seen_artifacts.update(link.url for link, _ in items)
            found += save(year, page, items, args.dry_run, args.refresh)
    print(f"{found} arquivo(s) {'encontrado(s)' if args.dry_run else 'processado(s)'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
