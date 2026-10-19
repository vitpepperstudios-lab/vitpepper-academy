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

# 1b) Ekip listesi (export klasörünün yanında team/list.json varsa)
team_file = EXPORT_DIR.parent / "team" / "list.json"
if team_file.exists():
    t = json.loads(team_file.read_text(encoding="utf-8"))
    members = [m for m in t.get("members", [])]
    mt = re.search(r"const DEFAULT_TEAM = \[[\s\S]*?\n\];", src)
    assert mt, "DEFAULT_TEAM bulunamadı"
    src = src[:mt.start()] + "const DEFAULT_TEAM = " + json.dumps(members, ensure_ascii=False, indent=1) + ";" + src[mt.end():]

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

# 5) Şifre kapısı (isteğe bağlı): PASSWORD ortam değişkeni verilirse sayfa gövdesi şifrelenir,
#    ziyaretçi önce logo + şifre alanı görür; doğru şifreyle içerik tarayıcıda çözülür.
import os, base64, secrets
PASSWORD = os.environ.get("ACADEMY_PASSWORD", "").strip()
if PASSWORD:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import hashlib
    salt = secrets.token_bytes(16); iv = secrets.token_bytes(12); ITER = 200000
    key = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode("utf-8"), salt, ITER, dklen=32)
    ct = AESGCM(key).encrypt(iv, body_part.encode("utf-8"), None)
    b64 = lambda b: base64.b64encode(b).decode("ascii")
    mark_inline = (OUT / "favicon.svg").read_text(encoding="utf-8") if (OUT / "favicon.svg").exists() else ""
    gate_css = '''
<style>
#gate{position:fixed;inset:0;z-index:100;background:var(--bg);color:var(--fg);display:grid;place-items:center;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
#gate .card{display:grid;justify-items:center;gap:26px;width:min(360px,100%)}
#gate .logo{display:grid;justify-items:center;gap:10px}
#gate .logo svg{width:96px;height:96px}
#gate .logo .wm{font-family:var(--font-display);font-weight:800;font-size:22px;letter-spacing:-.01em}
#gate .logo .wm em{font-style:normal;font-weight:400;color:var(--cream);letter-spacing:.14em;font-size:12px;margin-left:4px}
#gate form{display:grid;gap:10px;width:100%}
#gate input{font-family:var(--font-mono);font-size:18px;letter-spacing:.2em;text-align:center;color:var(--fg);background:var(--bg-2);border:1px solid var(--line);border-radius:4px;padding:14px 16px;width:100%}
#gate input:focus{outline:none;border-color:var(--red)}
#gate button{font-family:var(--font-body);font-weight:600;font-size:15px;color:#fff;background:var(--red);border:0;border-radius:999px;padding:13px 18px;cursor:pointer}
#gate button:hover{background:var(--red-2)}
#gate .msg{font-size:13px;color:var(--muted);text-align:center;min-height:1.4em}
#gate.err .card{animation:shake .4s}
#gate.err .msg{color:var(--red-2)}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-8px)}75%{transform:translateX(8px)}}
</style>'''
    gate_html = f'''
<div id="gate">
  <div class="card">
    <div class="logo">{mark_inline}<div class="wm">vitpepper<em>ACADEMY</em></div></div>
    <form id="gate-form" autocomplete="off">
      <input id="gate-pass" type="password" inputmode="numeric" placeholder="password" aria-label="Password" autofocus>
      <button type="submit">Giriş</button>
      <div class="msg" id="gate-msg"></div>
    </form>
  </div>
</div>
<script>
(function(){{
  const SALT="{b64(salt)}", IV="{b64(iv)}", CT="{b64(ct)}", ITER={ITER};
  const b2a = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  async function unlock(pw){{
    const km = await crypto.subtle.importKey("raw", new TextEncoder().encode(pw), "PBKDF2", false, ["deriveKey"]);
    const key = await crypto.subtle.deriveKey({{name:"PBKDF2", salt:b2a(SALT), iterations:ITER, hash:"SHA-256"}}, km, {{name:"AES-GCM", length:256}}, false, ["decrypt"]);
    const plain = await crypto.subtle.decrypt({{name:"AES-GCM", iv:b2a(IV)}}, key, b2a(CT));
    return new TextDecoder().decode(plain);
  }}
  function mount(html){{
    const tpl = document.createElement("template"); tpl.innerHTML = html;
    const frag = tpl.content; const scripts = [...frag.querySelectorAll("script")];
    scripts.forEach(s => s.remove());
    document.getElementById("gate").remove();
    document.body.appendChild(frag);
    scripts.forEach(s => {{ const n = document.createElement("script"); n.textContent = s.textContent; document.body.appendChild(n); }});
  }}
  const form = document.getElementById("gate-form"), inp = document.getElementById("gate-pass"), msg = document.getElementById("gate-msg"), gate = document.getElementById("gate");
  async function tryPw(pw, silent){{
    try {{ const html = await unlock(pw); try {{ sessionStorage.setItem("vpa-key", pw); }} catch(e){{}} mount(html); }}
    catch(e) {{ if (silent) return; gate.classList.remove("err"); void gate.offsetWidth; gate.classList.add("err"); msg.textContent = "Yanlış şifre"; inp.value = ""; inp.focus(); }}
  }}
  form.addEventListener("submit", e => {{ e.preventDefault(); msg.textContent = ""; tryPw(inp.value, false); }});
  try {{ const saved = sessionStorage.getItem("vpa-key"); if (saved) tryPw(saved, true); }} catch(e){{}}
}})();
</script>'''
    html = html.replace(f"<body>\n{body_part}\n</body>", "<body>" + gate_css + gate_html + "\n</body>")
    html = html.replace('<meta name="description" content="{desc}">'.format(desc=desc), '<meta name="robots" content="noindex,nofollow">')
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "index.html").write_text(html, encoding="utf-8")
(OUT / "404.html").write_text(html, encoding="utf-8")
(OUT / "CNAME").write_text(DOMAIN + "\n", encoding="utf-8")
(OUT / ".nojekyll").write_text("", encoding="utf-8")
print(f"ok — {len(areas)} alan, {sum(len(a.get('lessons', [])) for a in areas)} ders → {OUT}")
