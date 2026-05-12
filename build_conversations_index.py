#!/usr/bin/env python3
"""从导出 zip（single/15390-*.txt）生成 对话索引.html。"""

from __future__ import annotations

import argparse
import html
import re
import zipfile
from pathlib import Path

AI_ID = "15390"
LINE_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (\d+) say to (\d+):\s*(.*)$"
)
FILE_RE = re.compile(r"^single/15390-(\d+)\.txt$")

HTML_SUFFIX = """<script>
(function() {
  const sections = Array.from(document.querySelectorAll("section.conv"));
  const q = document.getElementById("q");
  const onlyUser = document.getElementById("onlyUser");
  const stat = document.getElementById("stat");
  function norm(s) { return (s || "").toLowerCase(); }
  function apply() {
    const needle = norm(q.value.trim());
    const needUser = onlyUser.checked;
    let vis = 0;
    for (const s of sections) {
      const file = norm(s.dataset.file);
      const peer = norm(s.dataset.peer);
      let ok = !needle || file.includes(needle) || peer.includes(needle);
      const um = parseInt(s.dataset.um || "0", 10);
      if (needUser && !(um > 0)) ok = false;
      s.style.display = ok ? "" : "none";
      if (ok) vis++;
    }
    stat.textContent = "当前显示 " + vis + " / " + sections.length + " 个会话";
  }
  q.addEventListener("input", apply);
  onlyUser.addEventListener("change", apply);
  apply();
})();
</script>
</body>
</html>
"""


def e(s: str) -> str:
    return html.escape(s, quote=True)


def parse_file(z: zipfile.ZipFile, name: str) -> dict | None:
    m = FILE_RE.match(name.replace("\\", "/"))
    if not m:
        return None
    peer = m.group(1)
    base = Path(name).name
    raw = z.read(name).decode("utf-8", errors="replace")
    rows: list = []
    times: list[str] = []
    u_msg = 0
    ai_msg = 0

    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        match = LINE_RE.match(s)
        if match:
            ts, speaker, _target, msg = match.groups()
            times.append(ts)
            if speaker == AI_ID:
                ai_msg += 1
                rows.append(["ai", ts, msg])
            else:
                u_msg += 1
                rows.append(["user", ts, speaker, msg])
        else:
            if rows and rows[-1][0] in ("ai", "user"):
                rows[-1][-1] += "\n" + s
            else:
                rows.append(["bad", s])

    if not times:
        return None
    return {
        "file": base,
        "peer": peer,
        "first": min(times),
        "last": max(times),
        "um": u_msg,
        "am": ai_msg,
        "rows": rows,
    }


def row_tr(i: int, row: list) -> str:
    if row[0] == "bad":
        return (
            f'<tr class="row-bad"><td class="idx">{i}</td>'
            f'<td class="time mono"></td><td class="who">?</td>'
            f'<td class="msg raw">{e(row[1])}</td></tr>'
        )
    if row[0] == "ai":
        _, ts, msg = row
        return (
            f'<tr class="row-ai"><td class="idx">{i}</td>'
            f'<td class="time mono">{e(ts)}</td><td class="who">AI</td>'
            f'<td class="msg">{e(msg)}</td></tr>'
        )
    _, ts, uid, msg = row
    return (
        f'<tr class="row-user"><td class="idx">{i}</td>'
        f'<td class="time mono">{e(ts)}</td>'
        f'<td class="who">用户 ({e(uid)})</td>'
        f'<td class="msg">{e(msg)}</td></tr>'
    )


def section_html(idx: int, d: dict) -> str:
    n = len(d["rows"])
    tbody = "".join(row_tr(j, r) for j, r in enumerate(d["rows"], start=1))
    return (
        f'<section class="conv" id="c{idx}" data-file="{e(d["file"])}" '
        f'data-peer="{e(d["peer"])}" data-um="{d["um"]}">'
        f'<header class="ch"><div class="ch-row">'
        f'<span class="fn mono">{e(d["file"])}</span>'
        f'<span class="ch-meta">对方 <b>{e(d["peer"])}</b> · 首条 {e(d["first"])} · '
        f'末条 {e(d["last"])} · 共 <b>{n}</b> 行 · 用户 <b>{d["um"]}</b> / '
        f'AI <b>{d["am"]}</b></span></div></header>'
        f'<div class="tbwrap"><table><thead><tr>'
        f'<th class="idx">#</th><th class="time">时间</th>'
        f'<th class="who">谁</th><th class="msg">内容</th>'
        f'</tr></thead><tbody>{tbody}</tbody></table></div></section>'
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "zip_path",
        type=Path,
        help="export-log-*.zip 路径",
    )
    ap.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("对话索引.html"),
        help="输出 HTML（默认当前目录 对话索引.html）",
    )
    ap.add_argument(
        "--cutoff",
        default="2026-04-23 23:59:59",
        help='只保留末条时间严格大于该值的会话（默认 "2026-04-23 23:59:59"）',
    )
    args = ap.parse_args()
    cutoff: str = args.cutoff

    head = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>对话索引（4月23日后 · 新→旧）</title>
<style>
body {{ font-family: system-ui, -apple-system, "Segoe UI", Roboto, "PingFang SC", "Microsoft YaHei", sans-serif;
  margin: 0; padding: 16px; background: #eef1f6; color: #1a1a1a; }}
.toolbar {{
  position: sticky; top: 0; z-index: 20; background: #eef1f6; padding: 10px 0 14px;
  border-bottom: 1px solid #d8dee8; margin-bottom: 16px; }}
h1 {{ font-size: 1.2rem; margin: 0 0 8px; }}
p.meta {{ color: #555; margin: 0 0 10px; font-size: 0.9rem; line-height: 1.45; }}
.rowf {{ display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }}
input#q {{
  flex: 1; min-width: 220px; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 8px; font-size: 14px; }}
label.chk {{ font-size: 14px; color: #334155; display: inline-flex; gap: 6px; align-items: center; user-select: none; }}
#stat {{ font-size: 13px; color: #475569; white-space: nowrap; }}
.conv {{
  margin: 0 0 18px; border: 1px solid #d8dee8; border-radius: 10px; background: #fff;
  box-shadow: 0 1px 3px rgba(15,23,42,.06); overflow: hidden; }}
.ch {{ padding: 10px 14px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; }}
.ch-row {{ display: flex; flex-wrap: wrap; gap: 8px 14px; align-items: baseline; }}
.fn {{ font-weight: 600; color: #0f172a; }}
.ch-meta {{ font-size: 13px; color: #475569; }}
.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
.tbwrap {{ overflow: auto; max-width: 100%; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; min-width: 640px; }}
th, td {{ border-bottom: 1px solid #eef2f7; padding: 8px 10px; text-align: left; vertical-align: top; }}
th {{ background: #fafafa; font-weight: 600; white-space: nowrap; }}
.idx {{ width: 42px; text-align: right; color: #64748b; font-variant-numeric: tabular-nums; }}
.time {{ white-space: nowrap; font-size: 12px; color: #334155; }}
.who {{ white-space: nowrap; font-size: 13px; width: 140px; }}
.msg {{ line-height: 1.5; word-break: break-word; }}
.row-ai td.msg {{ background: #f8fbff; }}
.row-user td.msg {{ background: #f6fff9; }}
.row-ai .who {{ color: #1e40af; font-weight: 600; }}
.row-user .who {{ color: #047857; font-weight: 600; }}
.row-bad td.msg {{ background: #fffbeb; }}
.raw {{ font-family: ui-monospace, Menlo, monospace; font-size: 12px; color: #b45309; }}
</style>
</head>
<body>
<div class="toolbar">
  <h1>对话索引（4月23日后 · 末条从新到旧）</h1>
  <p class="meta">数据源：<code>{e(str(args.zip_path))}</code>。仅展示<strong>末条时间晚于 {e(cutoff)}</strong>的会话；列表按<strong>末条时间从新到旧</strong>；会话内消息仍为导出文件中的顺序（续行已并入上一条）。共 <b>__COUNT__</b> 个会话文件。重新生成：<code>python3 build_conversations_index.py …</code></p>
  <div class="rowf">
    <input id="q" type="search" placeholder="按文件名或对方用户ID筛选…" autocomplete="off"/>
    <label class="chk"><input type="checkbox" id="onlyUser"/>只显示有用户发言的会话</label>
    <span id="stat"></span>
  </div>
</div>
<div id="all">
"""

    with zipfile.ZipFile(args.zip_path, "r") as z:
        names = sorted(
            n for n in z.namelist() if FILE_RE.match(n.replace("\\", "/"))
        )
        parsed: list[tuple[str, dict]] = []
        for name in names:
            d = parse_file(z, name)
            if d is None:
                continue
            if d["last"] <= cutoff:
                continue
            parsed.append((d["last"], d))
        parsed.sort(key=lambda x: x[0], reverse=True)

    out_parts = [head.replace("__COUNT__", str(len(parsed))), "\n"]
    for i, (_last, d) in enumerate(parsed):
        out_parts.append(section_html(i, d))
    out_parts.append("\n</div>\n")
    out_parts.append(HTML_SUFFIX)
    args.output.write_text("".join(out_parts), encoding="utf-8")
    print(f"Wrote {args.output} ({len(parsed)} conversations)")


if __name__ == "__main__":
    main()
