"""Copy the ISE technical-elective criteria from the department website into criteria.json.

Run by the weekly GitHub Action (.github/workflows/update-criteria.yml). The flowchart page
reads criteria.json when it is served from GitHub Pages and falls back to the copy built
into the HTML everywhere else. The file is rewritten only when the criteria text changes.
"""
import html
import json
import sys
import urllib.request
from datetime import date, timezone, datetime
from html.parser import HTMLParser

SOURCE = ("https://ise.kfupm.edu.sa/academics/undergraduate-program/degree-plan-new/"
          "list-of-technical-electives-for-ise-undergraduate-program/")
OUT = sys.argv[1] if len(sys.argv) > 1 else "criteria.json"
ALLOWED = {"p", "ul", "ol", "li", "b", "strong", "i", "em", "br", "a"}


class Extract(HTMLParser):
    """Collects the page <h1> and a sanitized copy of div.block-content."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title, self.in_h1 = "", False
        self.depth = 0          # div nesting depth inside block-content (0 = outside)
        self.out = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1" and not self.title:
            self.in_h1 = True
        if self.depth:
            if tag == "div":
                self.depth += 1
            elif tag in ALLOWED:
                if tag == "a":
                    href = a.get("href") or ""
                    if href.startswith("/"):
                        href = "https://ise.kfupm.edu.sa" + href
                    if href.startswith("https://"):
                        self.out.append(f'<a href="{html.escape(href)}">')
                    else:
                        self.out.append("<a>")
                else:
                    self.out.append(f"<{tag}>")
        elif tag == "div" and "block-content" in (a.get("class") or "").split():
            self.depth = 1

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_h1 = False
        if self.depth:
            if tag == "div":
                self.depth -= 1
            elif tag in ALLOWED and tag != "br":
                self.out.append(f"</{tag}>")

    def handle_data(self, data):
        if self.in_h1:
            self.title += data
        if self.depth:
            self.out.append(html.escape(data, quote=False))


def main():
    req = urllib.request.Request(SOURCE, headers={"User-Agent": "Mozilla/5.0 (criteria sync for ISE flowchart)"})
    with urllib.request.urlopen(req, timeout=30) as r:
        page = r.read().decode("utf-8", "replace")
    p = Extract()
    p.feed(page)
    body = "".join(p.out).replace("<p></p>", "").strip()
    title = " ".join(p.title.split())
    # Sanity checks so a redesign or error page never wipes out good data
    if "Course must" not in body or len(body) < 300:
        sys.exit("Criteria content not found on the page; leaving criteria.json unchanged.")

    try:
        old = json.load(open(OUT, encoding="utf-8"))
    except (OSError, ValueError):
        old = {}
    if old.get("html") == body and old.get("title") == title:
        print("Criteria unchanged.")
        return
    data = {"title": title, "source": SOURCE, "html": body,
            "updated": datetime.now(timezone.utc).date().isoformat()}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print("Criteria updated.")


if __name__ == "__main__":
    main()
