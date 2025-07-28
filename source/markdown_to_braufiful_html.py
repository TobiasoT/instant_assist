from __future__ import annotations

import re
import textwrap
import urllib.parse as _ulib
from typing import Iterable

import markdown
from bs4 import BeautifulSoup, NavigableString

# ─────────────────────────── link utilities ────────────────────────────────────
_URL_RE = re.compile(
    r'(?<!["\'=])'                  # not already inside a tag/attr
    r'('
    r'(?:https?|ftp)://[^\s<]+'     # absolute URLs
    r'|'
    r'www\.[^\s<]+\.[^\s<]+'        # www.foo.bar
    r')'
    r'(?=[\s<]|$)',                 # end of URL
    flags=re.I,
)

def _pretty_label(url: str, max_len: int = 60) -> str:
    """Strip scheme, ellipsize long paths."""
    p = _ulib.urlparse(url, scheme="https")
    disp = (p.netloc + p.path).lstrip("www.")
    if p.query and len(disp) < max_len - 10:
        disp += "?" + p.query
    if len(disp) > max_len:
        disp = textwrap.shorten(disp, width=max_len, placeholder="…")
    return disp


def _normalize_links(html: str) -> str:
    """
    1) Ensure every <a> has target="_blank" rel="noopener noreferrer",
       and prettify its text if it equals the href.
    2) Autolink any bare URLs Markdown missed.
    3) Return an HTML fragment (no <html>/<body> wrappers).
    """
    soup = BeautifulSoup(html, "lxml")

    # 1) normalize existing anchors
    for a in soup.find_all("a"):
        href = a.get("href")
        if not href:
            continue
        a["target"] = "_blank"
        a["rel"] = "noopener noreferrer"
        if (a.string or "").strip() == href.strip():
            a.string = _pretty_label(href)

    # 2) autolink bare URLs in text nodes
    def replace_in_text(text_node: NavigableString) -> None:
        parent = text_node.parent
        if parent and parent.name in {"a", "code", "pre", "script", "style"}:
            return  # skip
        pieces: list[str | NavigableString] = []
        last_end = 0
        text = str(text_node)
        for m in _URL_RE.finditer(text):
            start, end = m.span(1)
            url = m.group(1)
            if start > last_end:
                pieces.append(text[last_end:start])
            href = url if url.startswith(("http://", "https://")) else "http://" + url
            a_tag = soup.new_tag("a", href=href)
            a_tag["target"] = "_blank"
            a_tag["rel"] = "noopener noreferrer"
            a_tag.string = _pretty_label(href)
            pieces.append(a_tag)
            last_end = end
        if last_end < len(text):
            pieces.append(text[last_end:])
        if pieces:
            text_node.replace_with(*pieces)

    for txt in soup.find_all(string=True):
        replace_in_text(txt)

    # 3) return fragment only
    if soup.body:
        return soup.body.decode_contents()
    return str(soup)


# ─────────────────────────── fenced‑code normalizer ───────────────────────────
def _normalize_fences(md: str) -> str:
    """
    Make sure fenced code blocks follow CommonMark rules:
      - opening line:  ```lang
      - code starts on the next line
      - closing fence on its own line: ```
    Handles cases where code starts on the same line as the opening fence,
    or where the closing fence is tacked onto the end of a code line.
    """
    out_lines: list[str] = []
    in_fence = False
    fence_indent = ""
    fence_lang = ""

    for raw_line in md.splitlines():
        line = raw_line.rstrip("\n")
        stripped = line.lstrip()
        indent = line[: len(line) - len(stripped)]

        if not in_fence:
            if stripped.startswith("```"):
                after = stripped[3:]  # after the backticks
                # split into language (info string) and possible code stuck on the same line
                m = re.match(r"^([^\s`]*)\s*(.*)$", after)
                fence_lang = (m.group(1) or "").strip()
                same_line_code = (m.group(2) or "").rstrip()

                out_lines.append(f"{indent}```{fence_lang}".rstrip())
                if same_line_code:
                    out_lines.append(f"{indent}{same_line_code}")
                in_fence = True
                fence_indent = indent
            else:
                out_lines.append(line)
        else:
            # We are inside a fence. If the line contains ``` anywhere,
            # split it so the fence is alone on its own line.
            if "```" in stripped:
                before, _ticks, after = stripped.partition("```")
                if before:
                    out_lines.append(f"{indent}{before}".rstrip())
                out_lines.append(f"{fence_indent}```")
                in_fence = False
                fence_indent = fence_lang = ""
                if after.strip():
                    # Anything after closing ticks becomes a normal line
                    out_lines.append(f"{indent}{after}".rstrip())
            else:
                out_lines.append(line)

    # If an opening fence was never closed, close it at the end.
    if in_fence:
        out_lines.append(f"{fence_indent}```")

    return "\n".join(out_lines)


# ─────────────────────────── public API ───────────────────────────────────────
def convert_markdown_to_beautiful_html(markdown_text: str) -> str:
    """
    Convert Markdown to an HTML *fragment* suitable for client-side syntax
    highlighting (e.g., highlight.js).

    - Fixes malformed fenced code blocks.
    - Uses python-markdown with 'extra' + 'fenced_code'.
    - Does NOT include server-side Pygments/CodeHilite markup.
    - Normalizes links and returns fragment HTML.
    """
    fixed_md = _normalize_fences(markdown_text)

    html_body = markdown.markdown(
        fixed_md,
        extensions=[
            "extra",
            "fenced_code",      # explicit; don't rely solely on 'extra'
            "tables",
        ],
        output_format="xhtml1",  # stable <pre><code> output
    )
    return _normalize_links(html_body)
