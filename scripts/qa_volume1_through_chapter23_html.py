#!/usr/bin/env python3
"""Replay the complete 51-route through-Chapter-23 offline reader in Chromium.

This is an owner-side admission input, not an admission decision.  It first
proves the finite materialized tree and every local link/fragment from bytes,
then serves those exact bytes over loopback and exercises every route at both
desktop and mobile viewports.  Browser automation uses Chromium's DevTools
Protocol through Node's built-in WebSocket implementation, so no Playwright,
Selenium, or external network dependency is required.

The default mode runs all checks and prints the prospective receipt.  Pass
``--write`` to install the passing receipt at the canonical QA path.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import html
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import threading
import time
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READER = ROOT / "output" / "fondasi-teori-ukuran-v1-through-chapter23-id" / "html"
BUILD_RECEIPT = ROOT / "qa" / "through-chapter23-html-build.json"
RECEIPT = ROOT / "qa" / "through-chapter23-html-browser-qa.json"
MODEL = "OpenAI Codex gpt-5.6-sol, Ultra"
CHECKED_AT = "2026-08-25"

EXPECTED_ROUTES = (
    "", "bagian-awal", "pendahuluan-umum", "pendahuluan-jilid-1",
    "11", "111", "112", "113", "114", "115", "12", "121", "122",
    "123", "13", "131", "132", "133", "134", "135", "136",
    "lampiran", "1A1", "1A2", "1A3", "konkordansi", "referensi", "indeks",
    "21", "211", "212", "213", "214", "215", "216",
    "22", "221", "222", "223", "224", "225", "226",
    "20", "02", "2", "23", "231", "232", "233", "234", "235",
)
VIEWPORTS = (
    {"label": "desktop", "width": 1440, "height": 1000, "mobile": False},
    # This is a responsive-layout viewport replay, matching the proven prior
    # in-app-browser method.  Device-mode shrink-to-fit would change innerWidth
    # in response to deliberately off-canvas accessibility skip links.
    {"label": "mobile", "width": 390, "height": 844, "mobile": False},
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_state(path: Path) -> dict[str, Any]:
    return {
        "path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256_path(path),
    }


def inventory(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    files = sorted(
        (
            path for path in root.rglob("*")
            if path.is_file() and path.name != "MANIFEST.tsv"
        ),
        key=lambda path: path.relative_to(root).as_posix(),
    )
    for path in files:
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_path(path),
        })
    return rows


def parse_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line:
            continue
        fields = line.split("\t")
        require(len(fields) == 3, f"malformed MANIFEST.tsv row {line_number}")
        relative, byte_text, digest = fields
        relative_path = Path(relative)
        require(
            not relative_path.is_absolute() and ".." not in relative_path.parts,
            f"unsafe MANIFEST.tsv path: {relative}",
        )
        require(len(digest) == 64 and all(char in "0123456789abcdef" for char in digest),
                f"malformed manifest hash: {relative}")
        rows.append({"path": relative, "bytes": int(byte_text), "sha256": digest})
    require(rows == sorted(rows, key=lambda row: row["path"]), "manifest rows are not sorted")
    require(len({row["path"] for row in rows}) == len(rows), "duplicate manifest path")
    return rows


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.references: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._capture(tag, attrs)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._capture(tag, attrs)

    def _capture(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if value is None:
                continue
            if name == "id":
                self.ids.append(value)
            if name in {"href", "src"}:
                self.references.append((tag, name, value))


def parse_page(path: Path) -> ReferenceParser:
    parser = ReferenceParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def resolve_local_reference(page: Path, value: str) -> tuple[Path, str | None] | None:
    split = urllib.parse.urlsplit(html.unescape(value))
    if split.scheme or split.netloc:
        require(split.scheme in {"http", "https", "mailto", "data"},
                f"unsupported reference scheme: {page.relative_to(READER)} -> {value}")
        return None
    decoded_path = urllib.parse.unquote(split.path)
    if decoded_path:
        target = (page.parent / decoded_path).resolve()
        if decoded_path.endswith("/"):
            target /= "index.html"
    else:
        target = page.resolve()
    if target.is_dir():
        target /= "index.html"
    try:
        target.relative_to(READER.resolve())
    except ValueError as exc:
        raise ValueError(
            f"local reference escapes reader: {page.relative_to(READER)} -> {value}"
        ) from exc
    fragment = urllib.parse.unquote(split.fragment) if split.fragment else None
    return target, fragment


def validate_static_tree() -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    require(READER.is_dir(), f"materialized reader is absent: {READER}")
    require(BUILD_RECEIPT.is_file(), f"HTML build receipt is absent: {BUILD_RECEIPT}")
    manifest_path = READER / "MANIFEST.tsv"
    require(manifest_path.is_file(), "reader MANIFEST.tsv is absent")

    expected_inventory = parse_manifest(manifest_path)
    actual_inventory = inventory(READER)
    require(expected_inventory == actual_inventory, "reader tree differs from MANIFEST.tsv")

    pages = sorted(READER.rglob("*.html"))
    routes = tuple(
        "" if page.parent == READER else page.parent.relative_to(READER).as_posix()
        for page in pages
        if page.name == "index.html"
    )
    require(len(pages) == len(EXPECTED_ROUTES), "unexpected auxiliary HTML page")
    require(len(EXPECTED_ROUTES) == 51, "internal expected route count differs")
    require(set(routes) == set(EXPECTED_ROUTES), f"route surface differs: {routes!r}")

    parsed: dict[Path, ReferenceParser] = {}
    local_links = fragment_links = external_links = 0
    math_source_wrapper_pairs = 0
    math_span_pattern = re.compile(
        r'<span class="math (inline|display)" data-source-tex="(.*?)">(.*?)</span>',
        re.DOTALL,
    )
    for page in pages:
        content = page.read_text(encoding="utf-8")
        math_spans = math_span_pattern.findall(content)
        require(
            len(math_spans) == content.count('data-source-tex="'),
            f"unrecognized static math span shape: {page.relative_to(READER)}",
        )
        for presentation, encoded_source, encoded_inner in math_spans:
            expected = html.unescape(encoded_source)
            inner = html.unescape(encoded_inner)
            opening, closing = (r"\[", r"\]") if presentation == "display" else (r"\(", r"\)")
            require(
                inner.startswith(opening) and inner.endswith(closing),
                f"math delimiter differs: {page.relative_to(READER)}",
            )
            actual = inner[len(opening):-len(closing)]
            require(
                bool(expected.strip()) and bool(actual.strip()),
                f"empty source or inner TeX: {page.relative_to(READER)}",
            )
            require(
                not any(0xE000 <= ord(char) <= 0xF8FF for char in actual),
                f"private-use renderer placeholder leaked into math: "
                f"{page.relative_to(READER)}: source={expected!r} inner={actual!r}",
            )
            math_source_wrapper_pairs += 1
        page_parser = parsed.setdefault(page.resolve(), parse_page(page))
        require(len(page_parser.ids) == len(set(page_parser.ids)),
                f"duplicate DOM ID: {page.relative_to(READER)}")
        for _tag, _attribute, value in page_parser.references:
            target_info = resolve_local_reference(page, value)
            if target_info is None:
                external_links += 1
                continue
            local_links += 1
            target, fragment = target_info
            require(target.is_file(), f"broken local reference: {page.relative_to(READER)} -> {value}")
            if fragment:
                fragment_links += 1
                target_parser = parsed.setdefault(target.resolve(), parse_page(target))
                require(fragment in target_parser.ids,
                        f"broken fragment: {page.relative_to(READER)} -> {value}")

    build = json.loads(BUILD_RECEIPT.read_text(encoding="utf-8"))
    require(build.get("pass") is True and build.get("status") == "pass",
            "deterministic HTML build receipt does not pass")
    require(build.get("checks", {}).get("routes") == 51, "build receipt route count differs")
    require(build.get("coverage", {}).get("official_pages_complete") == 239,
            "build receipt official-page accounting differs")
    require(build.get("coverage", {}).get("corpus_official_pages") == 672,
            "build receipt corpus-page accounting differs")

    static_state = {
        "routes": len(routes),
        "html_pages": len(pages),
        "manifest_rows": len(expected_inventory),
        "manifest_tree_exact": True,
        "duplicate_dom_ids": 0,
        "local_links": local_links,
        "fragment_links": fragment_links,
        "external_links_not_loaded": external_links,
        "all_local_links_and_fragments_close": True,
        "math_source_wrapper_pairs": math_source_wrapper_pairs,
        "data_source_and_nonempty_inner_tex_bound_every_formula": True,
        "private_use_renderer_placeholders_in_math": 0,
    }
    return static_state, expected_inventory, build


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        return

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()


@contextlib.contextmanager
def serve_reader() -> Any:
    def handler(*args: Any, **kwargs: Any) -> QuietHandler:
        return QuietHandler(*args, directory=str(READER), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def no_proxy_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}))


def http_bytes(url: str, *, method: str = "GET", timeout: float = 15) -> bytes:
    request = urllib.request.Request(url, method=method)
    with no_proxy_opener().open(request, timeout=timeout) as response:
        require(response.status == 200, f"loopback HTTP status differs: {url}: {response.status}")
        return response.read()


def replay_http_tree(base_url: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    replay_rows = rows + [{
        "path": "MANIFEST.tsv",
        "bytes": (READER / "MANIFEST.tsv").stat().st_size,
        "sha256": sha256_path(READER / "MANIFEST.tsv"),
    }]
    total = 0
    for row in replay_rows:
        quoted = urllib.parse.quote(row["path"], safe="/")
        data = http_bytes(f"{base_url}/{quoted}")
        require(len(data) == row["bytes"], f"loopback byte count differs: {row['path']}")
        require(hashlib.sha256(data).hexdigest() == row["sha256"],
                f"loopback hash differs: {row['path']}")
        total += len(data)
    return {
        "files_read_back": len(replay_rows),
        "bytes_read_back": total,
        "all_http_bytes_match_materialized_tree": True,
    }


def find_browser() -> Path:
    configured = os.environ.get("O007_BROWSER_EXECUTABLE")
    candidates = [Path(configured)] if configured else []
    candidates.extend([
        Path(os.environ.get("PROGRAMFILES", r"C:\Program Files"))
        / "Google/Chrome/Application/chrome.exe",
        Path(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"))
        / "Microsoft/Edge/Application/msedge.exe",
        Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/Application/chrome.exe",
    ])
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome", "msedge"):
        found = shutil.which(name)
        if found:
            candidates.append(Path(found))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise FileNotFoundError(
        "No Chromium executable found; set O007_BROWSER_EXECUTABLE to Chrome, Edge, or Chromium"
    )


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_debugger(port: int, process: subprocess.Popen[bytes]) -> dict[str, Any]:
    url = f"http://127.0.0.1:{port}/json/version"
    deadline = time.monotonic() + 20
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        require(process.poll() is None, "Chromium exited before DevTools became ready")
        try:
            return json.loads(http_bytes(url, timeout=2))
        except Exception as exc:  # bounded readiness polling
            last_error = exc
            time.sleep(0.1)
    raise TimeoutError(f"Chromium DevTools did not become ready: {last_error}")


NODE_CDP_SOURCE = r'''
const config = JSON.parse(process.env.O007_CDP_CONFIG);

class CDP {
  constructor(url) {
    this.url = url;
    this.ws = null;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = [];
  }
  async connect() {
    this.ws = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      this.ws.addEventListener('open', resolve, {once: true});
      this.ws.addEventListener('error', reject, {once: true});
    });
    this.ws.addEventListener('message', event => {
      const message = JSON.parse(event.data);
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        if (message.error) pending.reject(new Error(JSON.stringify(message.error)));
        else pending.resolve(message.result || {});
        return;
      }
      for (const listener of this.listeners) listener(message);
    });
  }
  call(method, params = {}) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, {resolve, reject});
      this.ws.send(JSON.stringify({id, method, params}));
    });
  }
  close() { if (this.ws) this.ws.close(); }
}

function timeout(promise, milliseconds, label) {
  let timer;
  const expiry = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`timeout: ${label}`)), milliseconds);
  });
  return Promise.race([promise, expiry]).finally(() => clearTimeout(timer));
}

const cdp = new CDP(config.webSocketDebuggerUrl);
await cdp.connect();
await cdp.call('Page.enable');
await cdp.call('Runtime.enable');
await cdp.call('Log.enable');
await cdp.call('Network.enable');
await cdp.call('Network.setCacheDisabled', {cacheDisabled: true});

const version = await cdp.call('Browser.getVersion');
let currentIssues = [];
let currentIgnoredBrowserRequests = [];
let loadResolver = null;
cdp.listeners.push(message => {
  if (message.method === 'Page.loadEventFired' && loadResolver) {
    const resolve = loadResolver;
    loadResolver = null;
    resolve();
  }
  if (message.method === 'Runtime.exceptionThrown') {
    currentIssues.push({kind: 'page-exception', detail: message.params.exceptionDetails.text || 'exception'});
  }
  if (message.method === 'Runtime.consoleAPICalled') {
    const type = message.params.type;
    if (type === 'warning' || type === 'error' || type === 'assert') {
      const detail = (message.params.args || []).map(arg => arg.value ?? arg.description ?? '').join(' ');
      currentIssues.push({kind: `console-${type}`, detail});
    }
  }
  if (message.method === 'Log.entryAdded') {
    const entry = message.params.entry;
    if (entry.level === 'warning' || entry.level === 'error') {
      let generatedFaviconProbe = false;
      try {
        generatedFaviconProbe = !!entry.url && new URL(entry.url).pathname === '/favicon.ico';
      } catch (_) {}
      if (generatedFaviconProbe) {
        currentIgnoredBrowserRequests.push({kind: 'browser-generated-favicon-probe'});
      } else {
        currentIssues.push({kind: `log-${entry.level}`, detail: entry.text || '', url: entry.url || ''});
      }
    }
  }
  if (message.method === 'Inspector.targetCrashed') {
    currentIssues.push({kind: 'target-crashed', detail: 'Chromium target crashed'});
  }
});

const evaluateSource = String.raw`(async () => {
  if (globalThis.MathJax && MathJax.startup && MathJax.startup.promise) {
    await MathJax.startup.promise;
  }
  if (document.fonts && document.fonts.ready) await document.fonts.ready;
  // The retained S113 diagrams intentionally use native lazy loading.  Move
  // only unloaded images into view, await their terminal load/error event, and
  // return to the top before measuring the reader.  This tests the actual
  // reader behavior without disabling lazy loading or rewriting the page.
  for (const image of [...document.images]) {
    if (!image.complete) {
      image.scrollIntoView({block: 'center'});
      await Promise.race([
        new Promise(resolve => {
          image.addEventListener('load', resolve, {once: true});
          image.addEventListener('error', resolve, {once: true});
        }),
        new Promise(resolve => setTimeout(resolve, 5000))
      ]);
    }
  }
  scrollTo(0, 0);
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  const source = [...document.querySelectorAll('.math[data-source-tex]')];
  const rendered = [...document.querySelectorAll('.math[data-source-tex] mjx-container')];
  const assistive = [...document.querySelectorAll('.math[data-source-tex] mjx-assistive-mml math')];
  const allRendered = [...document.querySelectorAll('mjx-container')];
  const allAssistive = [...document.querySelectorAll('mjx-assistive-mml math')];
  const missingRendered = source.filter(node => node.querySelectorAll('mjx-container').length !== 1).length;
  const missingAssistive = source.filter(node => node.querySelectorAll('mjx-assistive-mml math').length !== 1).length;
  const emptySource = source.filter(node => !(node.getAttribute('data-source-tex') || '').trim()).length;
  const mathErrorNodes = [...document.querySelectorAll('mjx-merror, .MathJax_Error')];
  const mathErrors = mathErrorNodes.length;
  const mathErrorDetails = mathErrorNodes.slice(0, 12).map(node => {
    const sourceNode = node.closest('.math[data-source-tex]');
    return {
      error: node.getAttribute('data-mjx-error') || node.textContent || '',
      sourceTex: sourceNode ? sourceNode.getAttribute('data-source-tex') : '',
      text: (node.textContent || '').slice(0, 160)
    };
  });
  const displays = source.filter(node => node.classList.contains('display'));
  const locallyScrollable = displays.filter(node => {
    const style = getComputedStyle(node);
    return node.scrollWidth > node.clientWidth + 1 && (style.overflowX === 'auto' || style.overflowX === 'scroll');
  }).length;
  const uncontainedDisplayOverflow = displays.filter(node => {
    const style = getComputedStyle(node);
    return node.scrollWidth > node.clientWidth + 1 && style.overflowX !== 'auto' && style.overflowX !== 'scroll';
  }).length;
  const doc = document.documentElement;
  const body = document.body;
  const locallyContained = node => {
    for (let parent = node.parentElement; parent && parent !== body; parent = parent.parentElement) {
      const style = getComputedStyle(parent);
      const rect = parent.getBoundingClientRect();
      if ((style.overflowX === 'auto' || style.overflowX === 'scroll') &&
          rect.left >= -1 && rect.right <= doc.clientWidth + 1) return true;
    }
    return false;
  };
  // Measure positive, visible-width overflow.  The keyboard skip link is
  // intentionally positioned far to the left until focused; that negative
  // accessibility surface is not rightward document widening.  Oversized
  // MathJax children are likewise accepted only when an in-viewport ancestor
  // owns horizontal scrolling.
  const overflowingElements = [...document.querySelectorAll('body *')].filter(node => {
    const rect = node.getBoundingClientRect();
    return rect.right > doc.clientWidth + 1 && !locallyContained(node);
  }).slice(0, 12).map(node => {
    const rect = node.getBoundingClientRect();
    return {
      tag: node.tagName.toLowerCase(),
      id: node.id || '',
      className: typeof node.className === 'string' ? node.className : '',
      left: Math.round(rect.left),
      right: Math.round(rect.right),
      clientWidth: node.clientWidth,
      scrollWidth: node.scrollWidth,
      text: (node.textContent || '').trim().slice(0, 80)
    };
  });
  const documentOverflow = overflowingElements.length > 0;
  const h1 = [...document.querySelectorAll('h1')];
  const main = [...document.querySelectorAll('main')];
  const mainRect = main.length === 1 ? main[0].getBoundingClientRect() : null;
  // clientWidth excludes the vertical scrollbar; innerWidth does not.  The
  // former is therefore the correct symmetric-layout surface for centering.
  const layoutWidth = doc.clientWidth;
  const gutterDelta = mainRect ? Math.abs(mainRect.left - (layoutWidth - mainRect.right)) : null;
  const brokenImages = [...document.images].filter(image => !image.complete || image.naturalWidth === 0).length;
  const navLinks = [...document.querySelectorAll('.reader-nav a')].filter(node => {
    const style = getComputedStyle(node);
    const rect = node.getBoundingClientRect();
    return style.visibility !== 'hidden' && style.display !== 'none' && rect.width > 0 && rect.height > 0;
  }).length;
  const texDiagnostics = [];
  if (location.pathname.endsWith('/231/')) {
    const variants = [
      ['baseline', '\\nu E+\\nu F'],
      ['prooflet-only', '\\prooflet{x}'],
      ['mskip-only', '\\mskip5mu=x'],
      ['prooflet-mskip', '\\prooflet{\\mskip5mu=x}'],
      ['identity-no-mskip', '\\nu E+\\nu F \\prooflet{=x}=y'],
      ['exact-first', '\\nu E+\\nu F\n\\prooflet{\\mskip5mu=\\nu E+\\nu(F\\setminus E)+\\nu(F\\cap E)}\n=\\nu(E\\cup F)+\\nu(E\\cap F)'],
      ['first-no-newline', '\\nu E+\\nu F \\prooflet{\\mskip5mu=\\nu E+\\nu(F\\setminus E)+\\nu(F\\cap E)} =\\nu(E\\cup F)+\\nu(E\\cap F)'],
      ['first-no-prooflet', '\\nu E+\\nu F \\mskip5mu=\\nu E+\\nu(F\\setminus E)+\\nu(F\\cap E) =\\nu(E\\cup F)+\\nu(E\\cap F)'],
      ['first-no-mskip', '\\nu E+\\nu F \\prooflet{=\\nu E+\\nu(F\\setminus E)+\\nu(F\\cap E)} =\\nu(E\\cup F)+\\nu(E\\cap F)']
    ];
    for (const [label, tex] of variants) {
      try {
        const node = await MathJax.tex2chtmlPromise(tex);
        const errors = [...node.querySelectorAll('mjx-merror')].map(error =>
          error.getAttribute('data-mjx-error') || error.textContent || '');
        texDiagnostics.push({label, errors});
      } catch (error) {
        texDiagnostics.push({label, rejected: String(error)});
      }
    }
  }
  return {
    url: location.href,
    title: document.title,
    lang: document.documentElement.lang,
    innerWidth,
    innerHeight,
    h1Count: h1.length,
    mainCount: main.length,
    h1Visible: h1.length === 1 && h1[0].getBoundingClientRect().height > 0,
    mainVisible: main.length === 1 && mainRect.height > 0,
    mainWithinViewport: !!mainRect && mainRect.left >= -1 && mainRect.right <= layoutWidth + 1,
    mainCentered: gutterDelta !== null && gutterDelta <= 3,
    navLinks,
    sourceCount: source.length,
    renderedCount: rendered.length,
    assistiveCount: assistive.length,
    allRenderedCount: allRendered.length,
    allAssistiveCount: allAssistive.length,
    missingRendered,
    missingAssistive,
    emptySource,
    mathErrors,
    mathErrorDetails,
    locallyScrollable,
    uncontainedDisplayOverflow,
    documentOverflow,
    documentClientWidth: doc.clientWidth,
    documentScrollWidth: doc.scrollWidth,
    bodyScrollWidth: body.scrollWidth,
    overflowingElements,
    brokenImages,
    texDiagnostics
  };
})()`;

const observations = [];
for (const viewport of config.viewports) {
  await cdp.call('Emulation.setDeviceMetricsOverride', {
    width: viewport.width,
    height: viewport.height,
    deviceScaleFactor: 1,
    mobile: viewport.mobile,
    screenWidth: viewport.width,
    screenHeight: viewport.height
  });
  for (const route of config.routes) {
    currentIssues = [];
    currentIgnoredBrowserRequests = [];
    const suffix = route ? `/${encodeURIComponent(route)}/` : '/';
    const url = config.baseUrl + suffix;
    const loaded = new Promise(resolve => { loadResolver = resolve; });
    const navigation = await cdp.call('Page.navigate', {url});
    if (navigation.errorText) throw new Error(`navigation failed: ${route}: ${navigation.errorText}`);
    await timeout(loaded, 30000, `load ${viewport.label} ${route || '/'}`);
    const evaluation = await timeout(cdp.call('Runtime.evaluate', {
      expression: evaluateSource,
      awaitPromise: true,
      returnByValue: true
    }), 60000, `evaluate ${viewport.label} ${route || '/'}`);
    if (evaluation.exceptionDetails) {
      throw new Error(`evaluation failed: ${route}: ${evaluation.exceptionDetails.text || 'exception'}`);
    }
    await new Promise(resolve => setTimeout(resolve, 40));
    observations.push({
      route,
      viewport: viewport.label,
      ...evaluation.result.value,
      issues: currentIssues,
      ignoredBrowserRequests: currentIgnoredBrowserRequests
    });
  }
}

const output = {
  product: version.product,
  protocolVersion: version.protocolVersion,
  userAgent: version.userAgent,
  observations
};
process.stdout.write(JSON.stringify(output));
try { await cdp.call('Browser.close'); } catch (_) {}
cdp.close();
process.exit(0);
'''


@contextlib.contextmanager
def chromium_target() -> Any:
    executable = find_browser()
    port = free_port()
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    with tempfile.TemporaryDirectory(
        prefix="o007-ch23-browser-", ignore_cleanup_errors=True,
    ) as profile:
        command = [
            str(executable),
            "--headless=new",
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={profile}",
            "--remote-allow-origins=*",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-features=MediaRouter,Translate",
            "--disable-sync",
            "--metrics-recording-only",
            "--mute-audio",
            "about:blank",
        ]
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags,
        )
        try:
            version = wait_for_debugger(port, process)
            request = urllib.request.Request(
                f"http://127.0.0.1:{port}/json/new?about%3Ablank",
                method="PUT",
            )
            with no_proxy_opener().open(request, timeout=10) as response:
                target = json.loads(response.read())
            require("webSocketDebuggerUrl" in target, "DevTools page target lacks WebSocket URL")
            yield executable, version, target
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=8)
            # Chromium child processes can release cache journals a fraction
            # after the browser process exits on Windows.  The temporary
            # directory remains recreatable and is never release evidence.
            time.sleep(0.25)


def run_browser(base_url: str) -> tuple[dict[str, Any], str]:
    node = shutil.which("node")
    require(node is not None, "Node.js is required for the dependency-free CDP client")
    with chromium_target() as (executable, _debugger_version, target):
        configuration = {
            "baseUrl": base_url,
            "webSocketDebuggerUrl": target["webSocketDebuggerUrl"],
            "routes": list(EXPECTED_ROUTES),
            "viewports": list(VIEWPORTS),
        }
        environment = os.environ.copy()
        environment["O007_CDP_CONFIG"] = json.dumps(configuration, ensure_ascii=False)
        completed = subprocess.run(
            [node, "--input-type=module", "-"],
            input=NODE_CDP_SOURCE,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=20 * 60,
            check=False,
            env=environment,
        )
    if completed.returncode != 0:
        diagnostics = completed.stderr.strip().splitlines()
        raise RuntimeError("Chromium CDP replay failed: " + " | ".join(diagnostics[-12:]))
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Chromium CDP replay did not return JSON") from exc
    return result, executable.name


def validate_browser_result(result: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    observations = result.get("observations")
    require(isinstance(observations, list), "browser observations are absent")
    require(len(observations) == len(EXPECTED_ROUTES) * len(VIEWPORTS),
            "browser observation count differs")
    indexed = {(row.get("route"), row.get("viewport")): row for row in observations}
    require(len(indexed) == len(observations), "duplicate route/viewport browser observation")

    route_evidence: list[dict[str, Any]] = []
    total_source_by_viewport = {viewport["label"]: 0 for viewport in VIEWPORTS}
    total_local_scroll_by_viewport = {viewport["label"]: 0 for viewport in VIEWPORTS}
    ignored_browser_favicon_probes = 0
    for route in EXPECTED_ROUTES:
        pair = []
        for viewport in VIEWPORTS:
            key = (route, viewport["label"])
            require(key in indexed, f"missing browser observation: {key}")
            row = indexed[key]
            pair.append(row)
            require(row.get("innerWidth") == viewport["width"], f"viewport width differs: {key}")
            require(row.get("innerHeight") == viewport["height"], f"viewport height differs: {key}")
            require(row.get("lang") == "id-ID", f"document language differs: {key}")
            require(row.get("h1Count") == 1 and row.get("mainCount") == 1,
                    f"heading/main structure differs: {key}")
            require(row.get("h1Visible") is True and row.get("mainVisible") is True,
                    f"heading/main is hidden: {key}")
            require(row.get("mainWithinViewport") is True and row.get("mainCentered") is True,
                    f"reader column is clipped or off-center: {key}")
            require(route == "" or row.get("navLinks", 0) > 0,
                    f"non-root route lacks visible local navigation: {key}")
            require(row.get("sourceCount") == row.get("renderedCount") == row.get("assistiveCount"),
                    f"source/rendered/assistive math parity differs: {key}")
            require(row.get("sourceCount") == row.get("allRenderedCount") == row.get("allAssistiveCount"),
                    f"document-wide MathJax count differs: {key}")
            require(row.get("missingRendered") == 0 and row.get("missingAssistive") == 0,
                    f"formula-local rendered/assistive node differs: {key}")
            require(row.get("emptySource") == 0 and row.get("mathErrors") == 0,
                    f"empty source TeX or MathJax error: {key}: {row.get('mathErrorDetails')!r}")
            require(row.get("uncontainedDisplayOverflow") == 0,
                    f"display math overflow is not locally contained: {key}")
            require(row.get("documentOverflow") is False,
                    f"document-wide horizontal overflow: {key}: {row.get('overflowingElements')!r}")
            require(row.get("brokenImages") == 0, f"broken image: {key}")
            require(row.get("issues") == [], f"console/page error: {key}: {row.get('issues')!r}")
            ignored = row.get("ignoredBrowserRequests", [])
            require(
                all(item == {"kind": "browser-generated-favicon-probe"} for item in ignored),
                f"unexpected ignored browser request: {key}: {ignored!r}",
            )
            ignored_browser_favicon_probes += len(ignored)
            total_source_by_viewport[viewport["label"]] += row["sourceCount"]
            total_local_scroll_by_viewport[viewport["label"]] += row["locallyScrollable"]
        require(pair[0]["title"] == pair[1]["title"], f"title differs by viewport: {route}")
        require(pair[0]["sourceCount"] == pair[1]["sourceCount"],
                f"source formula count differs by viewport: {route}")
        route_evidence.append({
            "route": route,
            "title": pair[0]["title"],
            "math_source_rendered_assistive_each_viewport": pair[0]["sourceCount"],
            "desktop_locally_scrollable_display_math": pair[0]["locallyScrollable"],
            "mobile_locally_scrollable_display_math": pair[1]["locallyScrollable"],
            "desktop_pass": True,
            "mobile_pass": True,
        })

    require(total_source_by_viewport["desktop"] == total_source_by_viewport["mobile"],
            "cumulative formula count differs by viewport")
    summary = {
        "route_viewport_observations": len(observations),
        "all_routes_loaded_at_both_viewports": True,
        "console_warning_error_or_page_exception_count": 0,
        "browser_generated_unlinked_favicon_probe_count": ignored_browser_favicon_probes,
        "favicon_probe_note": (
            "Chromium may request /favicon.ico without a document reference. Such probes are "
            "counted separately and are not reader resource errors; every authored href/src "
            "is independently closed and hash-replayed."
        ),
        "document_level_horizontal_overflow_count": 0,
        "uncontained_display_math_overflow_count": 0,
        "broken_image_count": 0,
        "mathjax_error_count": 0,
        "math_source_rendered_assistive_count_per_viewport": total_source_by_viewport["desktop"],
        "math_source_rendered_assistive_parity_exact": True,
        "locally_scrollable_display_math": total_local_scroll_by_viewport,
        "local_formula_scrolling_allowed_only_without_document_overflow": True,
        "reader_column_centered_and_within_viewport_every_route": True,
    }
    return route_evidence, summary


def build_receipt() -> dict[str, Any]:
    static_state, manifest_rows, _build = validate_static_tree()
    with serve_reader() as base_url:
        http_state = replay_http_tree(base_url, manifest_rows)
        browser_result, browser_name = run_browser(base_url)
    route_evidence, observations = validate_browser_result(browser_result)
    return {
        "schema": "o007-volume1-through-volume2-chapter23-html-browser-qa-v1",
        "status": "pass_pending_owner_admission",
        "checked_at": CHECKED_AT,
        "production_model": MODEL,
        "pass": True,
        "admitted": False,
        "publication_ready": False,
        "scope": {
            "locale": "id-ID",
            "included": [
                "Volume I complete",
                "Volume II front matter complete, official pages 1-11",
                "Volume II Chapters 21-23 complete, official pages 12-137",
            ],
            "excluded": ["Volume II Chapters 24-28 and appendices"],
            "official_source_page_accounting": "239 of 672 (Volume I 102 + Volume II pages 1-137)",
            "html_routes_in_materialized_tree": 51,
        },
        "inputs": {
            "html_manifest": file_state(READER / "MANIFEST.tsv"),
            "deterministic_html_build": file_state(BUILD_RECEIPT),
        },
        "static_integrity": static_state,
        "loopback_readback": http_state,
        "browser": {
            "surface": "headless Chromium through the Chrome DevTools Protocol",
            "executable": browser_name,
            "product": browser_result.get("product"),
            "protocol_version": browser_result.get("protocolVersion"),
            "external_network_required": False,
            "served_tree": "exact materialized HTML tree over isolated loopback HTTP",
        },
        "coverage": {
            "routes": list(EXPECTED_ROUTES),
            "unique_current_routes_with_desktop_and_mobile_evidence": 51,
            "route_viewport_observations": 102,
            "desktop_viewport": [1440, 1000],
            "mobile_viewport": [390, 844],
        },
        "route_evidence": route_evidence,
        "automated_observations": observations,
        "checks": {
            "exact_materialized_tree_served_and_read_back": True,
            "all_51_routes_exercised_at_desktop_and_mobile": True,
            "math_source_rendered_assistive_parity_every_route": True,
            "console_and_page_errors_absent": True,
            "all_local_links_and_fragments_close": True,
            "document_wide_horizontal_overflow_absent": True,
            "overflowing_display_math_locally_contained": True,
            "reader_column_centered_and_unclipped": True,
            "credentials_present": False,
            "absolute_filesystem_paths_present": False,
        },
        "next_gate": (
            "Canonical owner binds this passing receipt into the cumulative aggregate, "
            "Chapter 23 admission, deterministic release package, and publication."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="write the passing canonical receipt")
    args = parser.parse_args()
    receipt = build_receipt()
    encoded = (json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    if args.write:
        RECEIPT.parent.mkdir(parents=True, exist_ok=True)
        temporary = RECEIPT.with_name(RECEIPT.name + ".tmp")
        temporary.write_bytes(encoded)
        os.replace(temporary, RECEIPT)
        print(f"wrote {RECEIPT.relative_to(ROOT).as_posix()}")
        print(f"bytes={len(encoded)} sha256={hashlib.sha256(encoded).hexdigest()}")
    else:
        print(encoded.decode("utf-8"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
