#!/usr/bin/env python3
# Sinyal Pro tarayıcı: Binance Futures'ı tarar, yeni sinyalde telefona bildirim (ntfy) yollar,
# aynı Wi-Fi'daki telefondan açılan grafik panelini sunar. Ek kurulum gerekmez (sadece Python 3.8+).
import json, os, sys, time, threading, socket, secrets, urllib.request, urllib.error
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

DIR = os.path.dirname(os.path.abspath(__file__))
CFG_F, DATA_F, STATE_F = [os.path.join(DIR, x) for x in ("ayar.json", "sinyaller.json", "durum.json")]
F = "https://fapi.binance.com"
TFSEC = {"15m": 900, "1h": 3600, "4h": 14400}
HTF = {"15m": "1h", "1h": "4h", "4h": "1d"}
DEF = {"topic": "", "tfs": ["1h", "4h"], "top": 120, "adx_min": 25, "atr_mult": 1.5, "rr": 2.0, "fee": 0.0005,
       "sadece_guclu": True, "htf_zorunlu": True, "min_test_sinyal": 5, "min_pf": 1.2, "port": 8765, "sifre": "", "adres": ""}
SIFRE = ""
PAGE = r'''<!DOCTYPE html><html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><title>Sinyal Pro</title>
<style>
:root{--bg:#0e1419;--card:#16202a;--ink:#e6eef3;--mut:#8196a5;--line:#263544;--g:#2ebd85;--r:#f6465d;--acc:#5aa0f2;--w:#f0b04a}
@media(prefers-color-scheme:light){:root{--bg:#eef2f5;--card:#fff;--ink:#14212b;--mut:#5d6f7d;--line:#d3dde4;--g:#0b7a53;--r:#c23a2b;--acc:#1d4e89;--w:#a86400}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif;padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0)}
main{max-width:600px;margin:0 auto;padding:14px}h1{font-size:1.25rem;margin:0}
.m{color:var(--mut);font-size:.82rem}.top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.rb{display:flex;gap:10px;margin:10px 0}.rb label{font-size:.8rem;color:var(--mut)}.rb input{width:90px;font:inherit;padding:6px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
.card{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--line);border-radius:8px;padding:12px 14px;margin-bottom:10px;cursor:pointer}
.card.long{border-left-color:var(--g)}.card.short{border-left-color:var(--r)}
.sym{font-weight:700;font-size:1.05rem}.tag{font-weight:800;padding:6px 12px;border-radius:6px;color:#fff;background:var(--g)}.short .tag{background:var(--r)}
.lv{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:10px 0;font-weight:600}.lv span{display:block;color:var(--mut);font-size:.72rem;font-weight:400}
.ck{font-size:.85rem;margin:2px 0}.ok{color:var(--g)}.no{color:var(--r)}.na{color:var(--mut)}.conf{font-weight:700;margin:10px 0 2px}
.ov{position:fixed;inset:0;background:var(--bg);overflow:auto;z-index:20;padding:env(safe-area-inset-top,0) 0 env(safe-area-inset-bottom,0)}.ov[hidden]{display:none}
#cv{width:100%;height:470px;display:block;margin:6px 0;touch-action:pan-y}.cl{font:inherit;padding:6px 12px;border:1px solid var(--line);border-radius:6px;background:var(--card);color:var(--ink)}
small{display:block;color:var(--mut);font-size:.75rem;margin-top:14px}
</style></head><body><main>
<div class="top"><h1>Sinyal Pro</h1><span class="m" id="st"></span></div>
<div class="rb"><label>Bakiye $ <input id="bal" type="number" inputmode="decimal" oninput="setR()"></label><label>Risk % <input id="rk" type="number" inputmode="decimal" step="0.1" oninput="setR()"></label></div>
<div id="list"></div>
<small>Garanti vermez, yatırım tavsiyesi değildir. Önce demo hesapta dene. Geçmiş test komisyon dahil, funding ve kayma yok.</small>
</main><div class="ov" id="ov" hidden></div>
<script>
var K=new URLSearchParams(location.search).get("k")||"",D=[],bal=1000,rk=1,cur=null,hv=0;
try{var sv=JSON.parse(localStorage.getItem("sp"));if(sv){bal=+sv.b;rk=+sv.r}}catch(e){}
function $(i){return document.getElementById(i)}
function fp(x){return x>=100?x.toFixed(2):x>=1?x.toFixed(3):x.toFixed(5)}
function ago(t){var m=Math.round((Date.now()-t)/60000);return m<60?m+" dk önce":m<1440?Math.round(m/60)+" sa önce":Math.round(m/1440)+" gün önce"}
function risk(s){var d=Math.abs(s.e-s.st);if(!(bal>0&&rk>0))return"Bakiye ve risk gir";var rs=bal*rk/100,q=rs/d,nt=q*s.e;return"Risk $"+rs.toFixed(2)+" · pozisyon $"+nt.toFixed(0)+" · stop %"+(100*d/s.e).toFixed(2)+" · kaldıraç ≥"+(nt/bal).toFixed(1)+"x"}
function bt(s){var b=s.bt;return b.n<5?"Geçmiş test: "+b.n+" sinyal (yetersiz örnek)":"Geçmiş test: "+b.n+" sinyal · isabet %"+Math.round(100*b.w/b.n)+" · beklenti "+(b.exp>=0?"+":"")+b.exp.toFixed(2)+"R · PF "+b.pf}
function lvl(s){return'<div class="lv"><div><span>Giriş</span>'+fp(s.e)+'</div><div><span>Stop</span>'+fp(s.st)+'</div><div><span>Hedef</span>'+fp(s.tp)+'</div></div>'}
async function load(){try{var j=await(await fetch("sinyaller.json?k="+encodeURIComponent(K)+"&t="+Date.now())).json();D=j.signals||[];$("st").textContent="Tarama "+(j.scan?new Date(j.scan).toLocaleTimeString("tr-TR",{hour:"2-digit",minute:"2-digit"}):"-")+" · "+(j.watching||0)+" coin";draw()}catch(e){$("st").textContent="Tarayıcıya ulaşılamıyor"}}
function setR(){bal=+$("bal").value;rk=+$("rk").value;try{localStorage.setItem("sp",JSON.stringify({b:bal,r:rk}))}catch(e){}draw()}
function draw(){$("list").innerHTML=D.map(function(s,i){var L=s.d=="long";return'<div class="card '+(L?"long":"short")+'" onclick="openC('+i+')"><div class="top"><div><div class="sym">'+s.sym+'USDT · '+s.tf+'</div><div class="m">'+ago(s.ts)+' · Teyit: '+s.q+' ('+s.ok+'/'+s.av+')</div></div><div class="tag">'+(L?"AL · LONG":"SAT · SHORT")+'</div></div>'+lvl(s)+'<div class="m">'+risk(s)+'</div><div class="m">'+bt(s)+'</div></div>'}).join("")||'<div class="m">Henüz sinyal yok, tarayıcı bekliyor…</div>'}
function openC(i){cur=D[i];hv=cur.ch.c.length-1;var s=cur;
$("ov").innerHTML='<main><div class="top"><h1>'+s.sym+'USDT · '+s.tf+' · '+(s.d=="long"?"AL":"SAT")+'</h1><button class="cl" onclick="$(\'ov\').hidden=true">Kapat</button></div><div class="m" id="hi" style="min-height:2.6em"></div><canvas id="cv"></canvas>'+lvl(s)+'<div class="m">'+risk(s)+'</div><div class="conf">Teyit: '+s.q+' ('+s.ok+'/'+s.av+')</div>'+s.cks.map(function(c){return'<div class="ck '+(c[1]===null?"na":c[1]?"ok":"no")+'">'+(c[1]===null?"–":c[1]?"✓":"✗")+" "+c[0]+"</div>"}).join("")+'<div class="m" style="margin-top:8px">'+bt(s)+'</div></main>';
$("ov").hidden=false;$("ov").scrollTop=0;var cv=$("cv");
function mv(e){var t=e.touches?e.touches[0]:e,rc=cv.getBoundingClientRect(),n=cur.ch.c.length;hv=Math.max(0,Math.min(n-1,Math.floor((t.clientX-rc.left)/((rc.width-52)/n))));chart()}
cv.ontouchstart=cv.ontouchmove=cv.onmousemove=mv;chart()}
function chart(){
var s=cur,c=s.ch,N=c.c.length,cv=$("cv"),dp=window.devicePixelRatio||1,W=cv.clientWidth,Hh=470;cv.width=W*dp;cv.height=Hh*dp;
var g=cv.getContext("2d");g.scale(dp,dp);var cs=getComputedStyle(document.documentElement),col=function(n){return cs.getPropertyValue(n).trim()};
var pw=W-52,bw=pw/N,X=function(i){return i*bw+bw/2},lv=[s.e,s.st,s.tp];
var lo=Math.min.apply(null,c.l.concat(lv)),hi=Math.max.apply(null,c.h.concat(lv)),pd=(hi-lo)*.05;lo-=pd;hi+=pd;
var PT=6,PB=290,Y=function(v){return PB-(v-lo)/(hi-lo)*(PB-PT)};
g.font="10px sans-serif";g.lineWidth=1;g.strokeStyle=col("--line");g.fillStyle=col("--mut");
for(var q=0;q<=4;q++){var v=lo+(hi-lo)*q/4,y=Y(v);g.beginPath();g.moveTo(0,y);g.lineTo(pw,y);g.stroke();g.fillText(fp(v),pw+4,y+3)}
g.save();g.beginPath();g.rect(0,PT-4,pw,PB-PT+8);g.clip();
var vm=Math.max.apply(null,c.v);
for(var i=0;i<N;i++){var up=c.c[i]>=c.o[i];g.fillStyle=up?col("--g"):col("--r");g.globalAlpha=.25;g.fillRect(X(i)-bw*.35,PB-c.v[i]/vm*55,bw*.7,c.v[i]/vm*55);g.globalAlpha=1;
g.strokeStyle=g.fillStyle;g.beginPath();g.moveTo(X(i),Y(c.h[i]));g.lineTo(X(i),Y(c.l[i]));g.stroke();g.fillRect(X(i)-bw*.35,Math.min(Y(c.o[i]),Y(c.c[i])),bw*.7,Math.max(1,Math.abs(Y(c.o[i])-Y(c.c[i]))))}
g.strokeStyle=col("--w");g.lineWidth=1.5;g.beginPath();c.e.forEach(function(v,i){i?g.lineTo(X(i),Y(v)):g.moveTo(X(i),Y(v))});g.stroke();g.lineWidth=1;
var L=s.d=="long",ly=L?Y(c.l[N-1])+10:Y(c.h[N-1])-10;g.fillStyle=L?col("--g"):col("--r");g.beginPath();g.moveTo(X(N-1),L?ly-6:ly+6);g.lineTo(X(N-1)-6,L?ly+4:ly-4);g.lineTo(X(N-1)+6,L?ly+4:ly-4);g.fill();
g.restore();
[[s.e,"Giriş",col("--acc")],[s.st,"Stop",col("--r")],[s.tp,"Hedef",col("--g")]].forEach(function(l){g.strokeStyle=g.fillStyle=l[2];g.setLineDash([5,3]);g.beginPath();g.moveTo(0,Y(l[0]));g.lineTo(pw,Y(l[0]));g.stroke();g.setLineDash([]);g.fillText(l[1],pw+4,Y(l[0])+3)});
g.strokeStyle=col("--mut");g.globalAlpha=.6;g.beginPath();g.moveTo(X(hv),0);g.lineTo(X(hv),Hh);g.stroke();g.globalAlpha=1;
g.fillStyle=col("--w");g.fillText("EMA 200",4,PT+8);
var M0=305,M1=380,mx=Math.max.apply(null,c.hi.concat(c.m,c.sg).map(Math.abs))||1,MY=function(v){return(M0+M1)/2-v/mx*(M1-M0)/2};
g.fillStyle=col("--mut");g.fillText("MACD",4,M0+8);
for(var i=0;i<N;i++){g.fillStyle=c.hi[i]>=0?col("--g"):col("--r");g.globalAlpha=.7;var y0=MY(0),y1=MY(c.hi[i]);g.fillRect(X(i)-bw*.35,Math.min(y0,y1),bw*.7,Math.max(1,Math.abs(y1-y0)));g.globalAlpha=1}
[[c.m,col("--acc")],[c.sg,col("--w")]].forEach(function(a){g.strokeStyle=a[1];g.beginPath();a[0].forEach(function(v,i){i?g.lineTo(X(i),MY(v)):g.moveTo(X(i),MY(v))});g.stroke()});
var A0=392,A1=466,am=Math.max(50,Math.max.apply(null,c.adx.concat(c.dp,c.dm))),AY=function(v){return A1-v/am*(A1-A0)};
g.fillStyle=col("--mut");g.fillText("ADX / DI",4,A0+8);g.strokeStyle=col("--line");g.setLineDash([3,3]);g.beginPath();g.moveTo(0,AY(25));g.lineTo(pw,AY(25));g.stroke();g.setLineDash([]);g.fillText("25",pw+4,AY(25)+3);
[[c.dp,col("--g")],[c.dm,col("--r")],[c.adx,col("--acc")]].forEach(function(a){g.strokeStyle=a[1];g.lineWidth=a[1]==col("--acc")?2:1;g.beginPath();a[0].forEach(function(v,i){i?g.lineTo(X(i),AY(v)):g.moveTo(X(i),AY(v))});g.stroke()});g.lineWidth=1;
$("hi").textContent=new Date(c.t[hv]).toLocaleString("tr-TR",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"})+"  A "+fp(c.o[hv])+"  Y "+fp(c.h[hv])+"  D "+fp(c.l[hv])+"  K "+fp(c.c[hv])+"  ADX "+c.adx[hv].toFixed(1)}
$("bal").value=bal;$("rk").value=rk;load();setInterval(load,30000);
</script></body></html>
'''

def load_json(p, d):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return d
def save_json(p, o):
    with open(p + ".tmp", "w", encoding="utf-8") as f: json.dump(o, f, ensure_ascii=False)
    os.replace(p + ".tmp", p)

def jget(path, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(F + path, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 451: sys.exit("Binance bu bölgeden erişime kapalı (451). VPN açıp tekrar dene.")
            if e.code in (418, 429): time.sleep(30 * (i + 1)); continue
            return None
        except Exception: time.sleep(2)
    return None

def ema(a, n):
    k = 2 / (n + 1); o = [a[0]]
    for x in a[1:]: o.append(x * k + o[-1] * (1 - k))
    return o
def rma(a, n):
    o = [a[0]]
    for x in a[1:]: o.append((o[-1] * (n - 1) + x) / n)
    return o

def calc(k, c):
    n = len(k); t = [int(x[0]) for x in k]
    O, H, L, C, V = [[float(x[j]) for x in k] for j in (1, 2, 3, 4, 5)]
    T = [H[0] - L[0]]; P = [0.0]; M = [0.0]
    for i in range(1, n):
        u = H[i] - H[i - 1]; d = L[i - 1] - L[i]
        T.append(max(H[i] - L[i], abs(H[i] - C[i - 1]), abs(L[i] - C[i - 1])))
        P.append(u if u > d and u > 0 else 0.0); M.append(d if d > u and d > 0 else 0.0)
    tr = rma(T, 14); atr = rma(T, 14)
    dp = [100 * v / x if x else 0 for v, x in zip(rma(P, 14), tr)]
    dm = [100 * v / x if x else 0 for v, x in zip(rma(M, 14), tr)]
    adx = rma([100 * abs(a - b) / (a + b) if a + b else 0 for a, b in zip(dp, dm)], 14)
    e12, e26 = ema(C, 12), ema(C, 26); mc = [a - b for a, b in zip(e12, e26)]; sg = ema(mc, 9); e200 = ema(C, 200)
    def flt(i, d):
        return (adx[i] > adx[i - 3] and V[i] > sum(V[i - 20:i]) / 20 and abs(C[i] - e200[i]) < 8 * atr[i]
                and (e200[i] > e200[i - 5] if d == "long" else e200[i] < e200[i - 5]))
    sig = []
    for i in range(201, n):
        up = mc[i] > sg[i] and mc[i - 1] <= sg[i - 1]; dn = mc[i] < sg[i] and mc[i - 1] >= sg[i - 1]
        d = None
        if up and adx[i] > c["adx_min"] and dp[i] > dm[i] and C[i] > e200[i] and flt(i, "long"): d = "long"
        elif dn and adx[i] > c["adx_min"] and dm[i] > dp[i] and C[i] < e200[i] and flt(i, "short"): d = "short"
        if d:
            av = sum(V[i - 20:i]) / 20
            sig.append({"i": i, "d": d, "vx": V[i] / av if av else 1})
    w = l = 0; sr = gw = gl = 0.0
    for s in sig:
        i = s["i"]; e = C[i]; r = atr[i] * c["atr_mult"]; L_ = s["d"] == "long"
        st = e - r if L_ else e + r; tp = e + r * c["rr"] if L_ else e - r * c["rr"]
        s.update(e=e, st=st, tp=tp, res="open"); cost = 2 * c["fee"] * e / r
        for j in range(i + 1, n):
            hs = L[j] <= st if L_ else H[j] >= st; ht = H[j] >= tp if L_ else L[j] <= tp
            if hs: s["res"] = "loss"; break
            if ht: s["res"] = "win"; break
        if s["res"] == "win": w += 1; sr += c["rr"] - cost; gw += c["rr"] - cost
        elif s["res"] == "loss": l += 1; sr -= 1 + cost; gl += 1 + cost
    return dict(t=t, O=O, H=H, L=L, C=C, V=V, adx=adx, dp=dp, dm=dm, mc=mc, sg=sg, e200=e200, sig=sig,
                w=w, l=l, sr=sr, gw=gw, gl=gl, n=n)

def trend(k):
    C = [float(x[4]) for x in k]; e50 = ema(C, 50); mc = [a - b for a, b in zip(ema(C, 12), ema(C, 26))]
    h = mc[-1] - ema(mc, 9)[-1]
    return "up" if C[-1] > e50[-1] and h > 0 else "down" if C[-1] < e50[-1] and h < 0 else "mix"

def push(cfg, title, msg, prio=4, tags=None, click=None):
    body = {"topic": cfg["topic"], "title": title, "message": msg, "priority": prio, "tags": tags or []}
    if click: body["click"] = click
    try:
        req = urllib.request.Request("https://ntfy.sh/", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).read()
    except Exception as e: print("Bildirim gönderilemedi:", e)

def fp(x): return f"{x:.2f}" if x >= 100 else f"{x:.3f}" if x >= 1 else f"{x:.5f}"
def sl(a, n): return [float(f"{x:.7g}") for x in a[-n:]]

def symbols(top):
    info = jget("/fapi/v1/exchangeInfo") or {"symbols": []}
    ok = {x["symbol"] for x in info["symbols"] if x["contractType"] == "PERPETUAL" and x["quoteAsset"] == "USDT" and x["status"] == "TRADING"}
    tk = [x for x in (jget("/fapi/v1/ticker/24hr") or []) if x["symbol"] in ok]
    tk.sort(key=lambda x: float(x["quoteVolume"]), reverse=True)
    return [x["symbol"][:-4] for x in tk[:top]]

def scan(tf, cfg, st, ip):
    print(time.strftime("%H:%M:%S"), tf, "taranıyor...")
    syms = symbols(cfg["top"]); now_ms = int(time.time() * 1000)
    fr = {x["symbol"]: float(x["lastFundingRate"]) * 100 for x in (jget("/fapi/v1/premiumIndex") or [])}
    for s in syms:
        time.sleep(0.12)
        k = jget(f"/fapi/v1/klines?symbol={s}USDT&interval={tf}&limit=1000")
        if not k or len(k) < 260: continue
        if int(k[-1][6]) > now_ms: k = k[:-1]
        r = calc(k, cfg)
        if not r["sig"] or r["sig"][-1]["i"] != r["n"] - 1: continue
        sg = r["sig"][-1]; key = f"{s}{tf}{r['t'][-1]}"
        if key in st["seen"]: continue
        st["seen"].append(key); L_ = sg["d"] == "long"
        tot = r["w"] + r["l"]; exp = r["sr"] / tot if tot else 0; pf = round(r["gw"] / r["gl"], 2) if r["gl"] else 99
        if tot >= cfg["min_test_sinyal"] and (exp <= 0 or pf < cfg["min_pf"]):
            print("  ", s, "elendi: geçmiş test zayıf"); continue
        h = None
        hk = jget(f"/fapi/v1/klines?symbol={s}USDT&interval={HTF[tf]}&limit=300")
        if hk and len(hk) > 60: h = trend(hk[:-1])
        w = None
        a = jget(f"/futures/data/topLongShortPositionRatio?symbol={s}USDT&period={tf}&limit=1")
        if a: w = float(a[0]["longAccount"]) * 100
        f_ = fr.get(s + "USDT")
        c1 = None if h is None else (h == "up" if L_ else h == "down")
        if cfg["htf_zorunlu"] and c1 is False: print("  ", s, "elendi: üst zaman dilimi ters"); continue
        c3 = None if w is None else (w >= 55 if L_ else w <= 45)
        c4 = None if f_ is None else (f_ < 0.05 if L_ else f_ > -0.05)
        cks = [[f"Üst zaman dilimi ({HTF[tf]}) trendi" + (" uyumlu" if c1 else " ters" if c1 is False else " bilinmiyor"), c1],
               [f"Hacim ortalamanın {sg['vx']:.1f} katı", sg["vx"] > 1],
               [("Büyük hesaplar " + ("Long" if L_ else "Short") + " ağırlıklı") + (f" (%{w:.0f} Long)" if w is not None else ""), c3],
               [("Funding %" + f"{f_:.3f}" if f_ is not None else "Funding verisi yok") + (" (aşırı değil)" if c4 else " (kalabalık bu yönde)" if c4 is False else ""), c4]]
        ok = sum(1 for x in cks if x[1] is True); av = sum(1 for x in cks if x[1] is not None)
        q = "Güçlü" if av >= 3 and ok / av >= 0.75 else "Orta" if av and ok / av >= 0.5 else "Zayıf"
        if cfg["sadece_guclu"] and q != "Güçlü": print("  ", s, "elendi:", q); continue
        N = 100; sl_ = slice(-N, None)
        ch = {"t": r["t"][sl_], "o": sl(r["O"], N), "h": sl(r["H"], N), "l": sl(r["L"], N), "c": sl(r["C"], N), "v": sl(r["V"], N),
              "e": sl(r["e200"], N), "hi": sl([a - b for a, b in zip(r["mc"], r["sg"])], N), "m": sl(r["mc"], N), "sg": sl(r["sg"], N),
              "adx": sl(r["adx"], N), "dp": sl(r["dp"], N), "dm": sl(r["dm"], N)}
        rec = {"sym": s, "tf": tf, "d": sg["d"], "ts": now_ms, "e": sg["e"], "st": sg["st"], "tp": sg["tp"], "q": q, "ok": ok, "av": av,
               "cks": cks, "bt": {"n": tot, "w": r["w"], "exp": round(exp, 2), "pf": pf}, "ch": ch}
        st["signals"].insert(0, rec); st["signals"] = st["signals"][:40]
        print("  >>> SİNYAL", s, tf, sg["d"], q)
        bts = f"test: {tot} sinyal, isabet %{round(100 * r['w'] / tot)}, PF {pf}" if tot else "test: örnek yok"
        push(cfg, f"{'AL' if L_ else 'SAT'} {s}USDT {tf} · {q}",
             f"Giriş {fp(sg['e'])} · Stop {fp(sg['st'])} · Hedef {fp(sg['tp'])}\nTeyit {ok}/{av} · {bts}",
             tags=["chart_with_upwards_trend" if L_ else "chart_with_downwards_trend"], click=f"http://{ip}:{cfg['port']}/?k={cfg['sifre']}")
    st["scan"] = int(time.time() * 1000); st["watching"] = len(syms)
    save_json(DATA_F, {"signals": st["signals"], "scan": st["scan"], "watching": st["watching"]})
    save_json(STATE_F, {"seen": st["seen"][-1500:]})

def lan_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
    except Exception: return "127.0.0.1"
    finally: s.close()

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if parse_qs(urlparse(self.path).query).get("k", [""])[0] != SIFRE:
            self.send_response(403); self.end_headers(); self.wfile.write(b"Erisim yok"); return
        if self.path.startswith("/sinyaller.json"):
            try: body = open(DATA_F, "rb").read()
            except Exception: body = b'{"signals":[]}'
            ct = "application/json"
        else: body = PAGE.encode(); ct = "text/html; charset=utf-8"
        self.send_response(200); self.send_header("Content-Type", ct); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)

def main():
    cfg = dict(DEF); cfg.update(load_json(CFG_F, {}))
    global SIFRE
    if not cfg["sifre"]: cfg["sifre"] = secrets.token_hex(4)
    SIFRE = cfg["sifre"]
    if not cfg["topic"]: cfg["topic"] = "sinyalpro-" + secrets.token_hex(5)
    save_json(CFG_F, cfg)
    d = load_json(DATA_F, {}); stt = load_json(STATE_F, {})
    st = {"signals": d.get("signals", []), "seen": stt.get("seen", []), "scan": 0, "watching": 0}
    ip = cfg["adres"] or lan_ip()
    try: srv = ThreadingHTTPServer(("0.0.0.0", cfg["port"]), H)
    except OSError: sys.exit(f"{cfg['port']} portu kullanımda. ayar.json içinden 'port' değerini değiştir.")
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("=" * 56, f"\n Bildirim konusu (ntfy): {cfg['topic']}\n Panel (telefondan aç): http://{ip}:{cfg['port']}/?k={cfg['sifre']}\n" + "=" * 56)
    push(cfg, "Sinyal Pro çalışıyor", "Bildirimler bu telefona gelecek. Yeni sinyal çıkınca haber vereceğim.", prio=3, tags=["white_check_mark"])
    last = {}
    while True:
        now = time.time()
        for tf in cfg["tfs"]:
            b = int(now // TFSEC[tf]) * TFSEC[tf]
            if last.get(tf) != b and now >= b + 8:
                last[tf] = b
                try: scan(tf, cfg, st, ip)
                except SystemExit: raise
                except Exception as e: print("Tarama hatası:", e)
        time.sleep(10)

if __name__ == "__main__":
    try: main()
    except KeyboardInterrupt: print("Kapatıldı.")
