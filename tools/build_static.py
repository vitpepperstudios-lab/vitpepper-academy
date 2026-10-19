#!/usr/bin/env python3
"""Vitpepper Academy — canlı site derleyici.
Kaynak: vitpepper-academy.html (Claude artifact sürümü) + veritabanı dışa aktarımı (areas/*.json)
Çıktı: repo klasörüne index.html, 404.html, CNAME, .nojekyll, favicon.svg
"""
import json, re, sys, pathlib

TEMPLATE = pathlib.Path(sys.argv[1])          # vitpepper-academy.html
EXPORT_DIR = pathlib.Path(sys.argv[2])        # klasör: areas/*.json
OUT = pathlib.Path(sys.argv[3])               # repo klasörü
DOMAIN = "vitpepperacademy.com"

src = TEMPLATE.read_text(encoding="utf-8")

# 1) Alan verisini veritabanı dışa aktarımıyla değiştir
areas = []
for f in sorted(EXPORT_DIR.glob("*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    d = {k: v for k, v in d.items() if not k.startswith("__")}
    d["id"] = f.stem
    areas.append(d)
areas.sort(key=lambda a: a.get("order", 99))
m = re.search(r"const DEFAULT_AREAS = \[[\s\S]*?\n\];", src)
assert m, "DEFAULT_AREAS bulunamadı"
src = src[:m.start()] + "const DEFAULT_AREAS = " + json.dumps(areas, ensure_ascii=False, indent=1) + ";" + src[m.end():]

# 2) Canlı sitede YouTube / Vimeo gömülü oynasın
embed_js = r'''
function embedFor(url){
  let m;
  if ((m = url.match(/(?:youtu\.be\/|youtube\.com\/(?:watch\?(?:.*&)?v=|shorts\/|embed\/))([A-Za-z0-9_-]{6,})/))) return "https://www.youtube-nocookie.com/embed/" + m[1] + "?rel=0&modestbranding=1";
  if ((m = url.match(/vimeo\.com\/(?:video\/)?(\d+)/))) return "https://player.vimeo.com/video/" + m[1] + "?dnt=1";
  return null;
}
'''
src = src.replace("/* ====== DURUM ====== */", embed_js + "\n/* ====== DURUM ====== */", 1)
old_url_branch = '''  } else if (l.video && l.video.type === "url" && l.video.url){
    slate.hidden = false; note.textContent = "Video dış kaynakta (YouTube/Vimeo). Yeni sekmede açılır.";
    link.href = l.video.url; link.hidden = false; link.textContent = "Videoyu aç";'''
new_url_branch = '''  } else if (l.video && l.video.type === "url" && l.video.url){
    const emb = embedFor(l.video.url);
    if (emb) {
      const f = document.createElement("iframe"); f.src = emb; f.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"; f.allowFullscreen = true; f.setAttribute("title", l.title); f.className = "embed";
      player.appendChild(f); slate.hidden = true;
    } else {
      slate.hidden = false; note.textContent = "Video dış kaynakta. Yeni sekmede açılır.";
      link.href = l.video.url; link.hidden = false; link.textContent = "Videoyu aç";
    }'''
assert old_url_branch in src, "video url dalı bulunamadı"
src = src.replace(old_url_branch, new_url_branch)
src = src.replace('const old = player.querySelector("video"); if (old) old.remove();',
                  'player.querySelectorAll("video, iframe.embed").forEach(x => x.remove());')
src = src.replace(".player video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;z-index:2;background:#000}",
                  ".player video,.player iframe.embed{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;z-index:2;background:#000;border:0}")

# 3) Yüklenen (asset) videolar canlı sitede yok — yer tutucu göster
src = src.replace('if (l.video && l.video.type === "asset" && l.video.id){',
                  'if (false){')

# 4) Tam HTML iskeleti
head_end = src.index("<header>")
head_part, body_part = src[:head_end], src[head_end:]
_mark = pathlib.Path(__file__).parent.parent / "logo" / "vitpepper-academy-mark.svg"
if _mark.exists() and not (OUT / "favicon.svg").exists():
    (OUT / "favicon.svg").write_text(_mark.read_text(encoding="utf-8"), encoding="utf-8")
first_area = next((a for a in areas if not a.get("soon")), areas[0]) if areas else None
desc = "Vitpepper Studios'un yeni ekip arkadaşları için kısa, videolu ders serisi: Sinematografi, Senaryo ve Hikâye Anlatıcılığı."
html = f'''<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="description" content="{desc}">
<meta property="og:title" content="Vitpepper Academy">
<meta property="og:description" content="Yeni Biberlere, Temel Bilgiler.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://{DOMAIN}/">
<meta name="theme-color" content="#141112">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="canonical" href="https://{DOMAIN}/">
<style>[hidden]{{display:none!important}} img{{max-width:100%}} html,body{{margin:0}}</style>
{head_part.strip()}
</head>
<body>
{body_part}
</body>
</html>
'''
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(html, encoding="utf-8")
(OUT / "404.html").write_text(html, encoding="utf-8")
(OUT / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
print(f"ok — {len(areas)} alan, {sum(len(a.get('lessons', [])) for a in areas)} ders → {OUT}")
