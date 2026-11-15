 from flask import Flask, render_template_string, request, jsonify, send_file
import yt_dlp, imageio_ffmpeg, threading, time, uuid, urllib.request
from yt_dlp.utils import download_range_func
from pathlib import Path
from io import BytesIO

app = Flask(__name__)
DOWNLOAD_FOLDER = Path("web_downloads").resolve()
DOWNLOAD_FOLDER.mkdir(exist_ok=True)
TASKS = {}

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Pro Media Studio</title>
<style>
  *{box-sizing:border-box;font-family:'Segoe UI',sans-serif;scroll-behavior:smooth}
  body{margin:0;min-height:100vh;background:#050811;color:#fff;overflow-x:hidden}
  .bg{position:fixed;inset:0;z-index:-1;background:radial-gradient(circle at 20% 20%,#1e1b4b 0%,transparent 45%),radial-gradient(circle at 80% 80%,#311042 0%,transparent 45%),#050811;animation:pl 8s infinite alternate}
  @keyframes pl{to{filter:hue-rotate(35deg)}}
  .st{position:fixed;inset:0;z-index:-1;background-image:radial-gradient(#fff 1px,transparent 1px);background-size:45px 45px;opacity:.15;animation:dr 30s linear infinite}
  @keyframes dr{to{background-position:450px 450px}}
  header{background:rgba(15,23,42,.85);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid rgba(255,255,255,.1)}
  header h1{margin:0;font-size:20px;background:linear-gradient(90deg,#38bdf8,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
  .sites{text-align:center;margin:16px auto;max-width:1000px}
  .tag{display:inline-block;background:rgba(30,41,59,.8);padding:6px 14px;border-radius:20px;font-size:12px;margin:4px;color:#cbd5e1;border:1px solid rgba(255,255,255,.15);cursor:pointer;transition:.2s}
  .tag:hover,.tag.act{background:#6366f1;color:#fff;transform:translateY(-2px)}
  .main,.sec{max-width:1050px;margin:18px auto;padding:0 20px}
  .main{display:grid;grid-template-columns:1.1fr .9fr;gap:22px}
  @media(max-width:800px){.main{grid-template-columns:1fr}}
  .panel{background:rgba(15,23,42,.8);border:1px solid rgba(255,255,255,.1);border-radius:18px;padding:22px;box-shadow:0 15px 35px rgba(0,0,0,.5)}
  .row{display:flex;gap:10px;margin-top:10px}
  input{flex:1;padding:12px;border-radius:10px;border:1px solid #475569;background:#090d16;color:#fff;font-size:14px;outline:none}
  .btn{padding:12px 20px;border-radius:10px;border:none;background:linear-gradient(135deg,#6366f1,#8b5cf6);color:#fff;font-weight:700;cursor:pointer}
  .thumb img{width:100%;height:190px;object-fit:cover;border-radius:12px}
  .btn-th{display:block;width:100%;text-align:center;margin-top:10px;padding:9px;background:linear-gradient(135deg,#f59e0b,#d97706);color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-size:13px}
  .tl{margin-top:10px;background:#1e293b;padding:9px;border-radius:10px}
  .tr{height:6px;background:#334155;border-radius:6px;margin-top:5px;overflow:hidden}
  .tf{height:100%;width:100%;background:linear-gradient(90deg,#38bdf8,#ec4899)}
  .trim{background:rgba(30,41,59,.7);border:1px solid rgba(56,189,248,.3);padding:12px;border-radius:12px;margin-bottom:16px}
  .trim input{max-width:120px;text-align:center;padding:8px;font-weight:700;color:#38bdf8}
  .grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}
  @media(max-width:700px){.grid{grid-template-columns:1fr}}
  .qi{display:flex;justify-content:space-between;align-items:center;background:#1e293b;padding:10px 14px;border-radius:10px;margin-bottom:8px}
  .qb{padding:7px 14px;border-radius:8px;border:none;background:#6366f1;color:#fff;font-weight:700;cursor:pointer}
  .bb{width:100%;height:11px;background:#090d16;border-radius:10px;overflow:hidden;margin:8px 0}
  .bf{height:100%;width:0%;background:linear-gradient(90deg,#38bdf8,#10b981);transition:width .3s}
  video{width:100%;max-height:440px;border-radius:12px;background:#000;margin-top:10px}
</style>
</head>
<body>
<div class="bg"></div><div class="st"></div>
<header><h1>Video & Audio Download + Stream Studio</h1><span style="color:#34d399;font-size:13px">&bull; Live 24x7</span></header>
<div class="sites">
  <span class="tag act" onclick="setS(this,'YouTube')">YouTube</span><span class="tag" onclick="setS(this,'Instagram')">Instagram</span>
  <span class="tag" onclick="setS(this,'Facebook')">Facebook</span><span class="tag" onclick="setS(this,'X (Twitter)')">X</span>
  <span class="tag" onclick="setS(this,'Reddit')">Reddit</span><span class="tag" onclick="setS(this,'Vimeo')">Vimeo</span><span class="tag" onclick="setS(this,'SoundCloud')">SoundCloud</span>
</div>
<div class="main">
  <div class="panel">
    <div style="font-size:12px;color:#94a3b8;font-weight:700" id="sLbl">1. PASTE YOUTUBE LINK</div>
    <form method="POST" action="/" class="row">
      <input type="text" id="uInp" name="url" value="{{ url }}" placeholder="Link paste karke Fetch Link dabayein..." required>
      <button type="submit" class="btn">Fetch Link</button>
    </form>
    {% if error %}<div style="color:#f87171;margin-top:10px;font-size:13px">Error: {{ error }}</div>{% endif %}
    {% if info %}<div style="margin-top:14px;display:flex;gap:10px"><a href="#dlSec" style="padding:9px 15px;background:#ec4899;color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-size:13px">Download &darr;</a><a href="#stSec" style="padding:9px 15px;background:#0ea5e9;color:#fff;text-decoration:none;border-radius:10px;font-weight:700;font-size:13px">Stream &darr;</a></div>{% endif %}
  </div>
  <div class="panel">
    <div style="font-size:12px;color:#94a3b8;font-weight:700;margin-bottom:8px">LIVE PREVIEW & TIMELINE</div>
    {% if info %}
      <div class="thumb"><img src="{{ info.thumbnail }}"></div>
      <a href="/download_thumb?url={{ info.thumbnail | urlencode }}" class="btn-th">Save Thumbnail Photo (HD JPG) &darr;</a>
      <div style="font-weight:600;margin-top:8px">{{ info.title }}</div>
      <div class="tl"><div style="display:flex;justify-content:space-between;font-size:11px;color:#94a3b8"><span>00:00</span><span>{{ info.uploader }}</span><span>{{ info.duration }}</span></div><div class="tr"><div class="tf"></div></div></div>
    {% else %}
      <div style="padding:40px;text-align:center;color:#64748b;border:1px dashed #334155;border-radius:12px">Link paste karke <b>Fetch Link</b> dabayein.</div>
    {% endif %}
  </div>
</div>
{% if info %}
<div class="sec" id="dlSec"><div class="panel">
  <div style="font-size:15px;font-weight:700;margin-bottom:10px;color:#38bdf8">2. Custom Timeline Cutter & Download</div>
  <div class="trim">
    <div style="font-size:12px;color:#cbd5e1;margin-bottom:6px">Custom Duration (Optional - e.g. 00:30 to 01:45):</div>
    <input type="text" id="sT" placeholder="00:00"> <span style="color:#94a3b8">to</span> <input type="text" id="eT" placeholder="{{ info.duration }}">
  </div>
  <div class="grid">
    <div>
      <div style="font-size:12px;color:#94a3b8;font-weight:700;margin-bottom:8px">VIDEO QUALITIES (MP4)</div>
      <div class="qi"><span><b>1080p</b> Full HD</span><button class="qb" onclick="dl('1')">Download</button></div>
      <div class="qi"><span><b>720p</b> HD</span><button class="qb" onclick="dl('2')">Download</button></div>
      <div class="qi"><span><b>480p</b> Medium</span><button class="qb" onclick="dl('3')">Download</button></div>
      <div class="qi"><span><b>360p</b> Low Data</span><button class="qb" onclick="dl('4')">Download</button></div>
    </div>
    <div>
      <div style="font-size:12px;color:#34d399;font-weight:700;margin-bottom:8px">AUDIO / SONG SECTION</div>
      <div style="display:flex;gap:10px;align-items:center;background:#1e293b;padding:10px;border-radius:10px;margin-bottom:8px"><img src="{{ info.thumbnail }}" style="width:80px;height:55px;object-fit:cover;border-radius:6px"><div style="font-size:12px;font-weight:600">{{ info.title }}</div></div>
      <div class="qi"><span><b>Best Audio</b> (Song)</span><button class="qb" style="background:#10b981" onclick="dl('5')">Download Audio</button></div>
    </div>
  </div>
  <div id="pBox" style="display:none;background:#1e293b;padding:12px;border-radius:10px;margin-top:12px">
    <div style="display:flex;justify-content:space-between;font-size:12px"><span id="pSt">Preparing...</span><span id="pPc" style="color:#38bdf8;font-weight:700">0%</span></div>
    <div class="bb"><div class="bf" id="bFl"></div></div><div id="pSp" style="font-size:11px;color:#94a3b8">Speed: --</div>
  </div>
  <div id="lBox" style="display:none;background:rgba(16,185,129,.2);border:1px solid #10b981;padding:10px;border-radius:10px;margin-top:12px;font-size:12px"><b style="color:#34d399">Download Started!</b> File aapke device ke Downloads mein save ho rahi hai.</div>
</div></div>
<div class="sec" id="stSec" style="margin-bottom:40px"><div class="panel">
  <div style="font-size:15px;font-weight:700;color:#f472b6;margin-bottom:10px">3. Live Video Stream Player</div>
  <div id="playerBox"></div>
</div></div>
<script>
window.onload=()=>{
  document.getElementById('dlSec').scrollIntoView();
  const u="{{ url }}", box=document.getElementById('playerBox');
  const m=u.match(/(?:v=|youtu\.be\/|shorts\/)([a-zA-Z0-9_-]{11})/);
  if(m) box.innerHTML=`<iframe width="100%" height="420" style="border-radius:12px;border:none" src="https://youtube.com{m}" allowfullscreen></iframe>`;
  else if("{{ info.stream_url }}") box.innerHTML=`<video controls poster="{{ info.thumbnail }}"><source src="{{ info.stream_url }}" type="video/mp4"></video>`;
  else box.innerHTML=`<div style="padding:20px;color:#94a3b8">Stream available nahi hai.</div>`;
};
function dl(q){
  document.getElementById('pBox').style.display='block';document.getElementById('lBox').style.display='none';
