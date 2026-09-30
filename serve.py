#!/usr/bin/env python3
"""Threaded static server for site/ with HTTP Range support (needed for audio seeking / podcast clients).
Usage: serve.py [PORT]   (default 8787, binds 127.0.0.1; expose with `cloudflared tunnel --url http://127.0.0.1:PORT`)"""
import os, re, sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

SITE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")


class H(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map, ".xml": "application/rss+xml; charset=utf-8",
                      ".mp3": "audio/mpeg"}

    def end_headers(self):
        self.send_header("Accept-Ranges", "bytes")
        super().end_headers()

    def send_head(self):
        rng = self.headers.get("Range")
        path = self.translate_path(self.path)
        if not rng or not os.path.isfile(path):
            return super().send_head()
        m = re.match(r"bytes=(\d*)-(\d*)$", rng.strip())
        size = os.path.getsize(path)
        if not m:
            return super().send_head()
        a, b = m.groups()
        if a == "":
            start, end = max(0, size - int(b)), size - 1
        else:
            start, end = int(a), min(int(b) if b else size - 1, size - 1)
        if start >= size or start > end:
            self.send_response(416); self.send_header("Content-Range", f"bytes */{size}"); self.end_headers(); return None
        f = open(path, "rb"); f.seek(start)
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        self._remaining = end - start + 1
        return f

    def copyfile(self, src, dst):
        rem = getattr(self, "_remaining", None)
        if rem is None:
            return super().copyfile(src, dst)
        while rem > 0:
            buf = src.read(min(64 * 1024, rem))
            if not buf: break
            dst.write(buf); rem -= len(buf)
        self._remaining = None


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8787
    ThreadingHTTPServer(("127.0.0.1", port), partial(H, directory=SITE)).serve_forever()
