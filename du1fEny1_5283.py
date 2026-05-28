#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对分易自动签到程序 v5.28.3 — 新拟物设计版 (WebView)
"""

import configparser, os.path, re, random, sys, ctypes, base64, json, threading
from datetime import datetime

import requests, urllib3
from bs4 import BeautifulSoup

# ===== DPI =====
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except:
    try: ctypes.windll.user32.SetProcessDPIAware()
    except: pass

# ===== Constants =====
VERSION = "5.28.3"
APP_NAME = "对分易签到"
HOST = "https://www.duifene.com"
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
      'AppleWebKit/605.1.15 Mobile/15E148 MicroMessenger/8.0.40 NetType/WIFI Language/zh_CN')
urllib3.disable_warnings()

# ===== Global State =====
x = requests.Session()
x.headers['User-Agent'] = UA
x.verify = False
BASE_DIR = os.path.dirname(sys.executable) if getattr(sys,'frozen',False) else os.path.dirname(os.path.abspath(__file__))
ini_path = os.path.join(BASE_DIR, 'duifenyi.ini')
cfg = configparser.ConfigParser()

class Course:
    id = '0'; class_id = '0'; flag = True; check_list = []; class_list = []

# ===== Backend Functions =====

def save_cookie(resp):
    cfg['INFO'] = {'cookie': '; '.join(f'{c.name}={c.value}' for c in x.cookies)}
    try:
        with open(ini_path, 'w', encoding='utf-8') as f: cfg.write(f)
    except: pass

def save_password(username, password):
    try:
        cfg['INFO']['password'] = base64.b64encode(password.encode()).decode()
        cfg['INFO']['username'] = username
        with open(ini_path, 'w', encoding='utf-8') as f: cfg.write(f)
    except: pass

def load_password():
    try:
        e = cfg.get('INFO','password',fallback='')
        return base64.b64decode(e.encode()).decode() if e else ''
    except: return ''

def load_username():
    return cfg.get('INFO','username',fallback='')

def get_user_id():
    try:
        r = x.get(HOST+'/_UserCenter/MB/index.aspx', timeout=15)
        if r.status_code==200:
            s = BeautifulSoup(r.text,'lxml').find(id="hidUID")
            return s.get("value") if s else ''
    except: pass
    return ''

def is_login():
    try:
        h = {"Referer":"https://www.duifene.com/_UserCenter/PC/CenterStudent.aspx",
             "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8"}
        r = x.get(HOST+'/AppCode/LoginInfo.ashx', data="Action=checklogin", headers=h, timeout=15)
        return r.json().get("msg")=="1" if r.status_code==200 else False
    except: return False

def get_class_list():
    try:
        h = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
             "Referer":"https://www.duifene.com/_UserCenter/PC/CenterStudent.aspx"}
        r = x.post(HOST+'/_UserCenter/CourseInfo.ashx', data="action=getstudentcourse&classtypeid=2", headers=h, timeout=15)
        if r.status_code==200 and r.json() is not None:
            j = r.json()
            if isinstance(j,dict) and "msgbox" in j: return False, j["msgbox"]
            return True, j
    except: pass
    return False, None

def sign_code(sign_code):
    uid = get_user_id()
    if not uid: return False, ""
    try:
        h = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
             "Referer":"https://www.duifene.com/_CheckIn/MB/CheckInStudent.aspx?moduleid=16&pasd="}
        r = x.post(HOST+'/_CheckIn/CheckIn.ashx',
                   data=f"action=studentcheckin&studentid={uid}&checkincode={sign_code}", headers=h, timeout=15)
        if r.status_code==200:
            m = r.json().get("msgbox","")
            return m=="签到成功！", m
    except Exception as e: return False, str(e)
    return False, ""

def sign_qrcode(cid):
    try:
        r = x.get(HOST+'/_CheckIn/MB/QrCodeCheckOK.aspx?state='+cid, timeout=15)
        if r.status_code==200:
            d = BeautifulSoup(r.text,'lxml').find(id="DivOK")
            if d:
                m = d.get_text(strip=True)
                return "签到成功" in m, m if "签到成功" in m else "非微信登录，二维码无法签到"
    except Exception as e: return False, str(e)
    return False, ""

def sign_location(lon, lat):
    lon = str(round(float(lon)+random.uniform(-8.9e-5,8.9e-5),8))
    lat = str(round(float(lat)+random.uniform(-8.9e-5,8.9e-5),8))
    uid = get_user_id()
    if not uid: return False, ""
    try:
        h = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
             "Referer":"https://www.duifene.com/_CheckIn/MB/CheckInStudent.aspx?moduleid=16&pasd="}
        r = x.post(HOST+'/_CheckIn/CheckInRoomHandler.ashx',
                   data=f"action=signin&sid={uid}&longitude={lon}&latitude={lat}", headers=h, timeout=15)
        if r.status_code==200:
            m = r.json().get("msgbox","")
            return m=="签到成功！", m
    except Exception as e: return False, str(e)
    return False, ""

# ===== HTML UI =====

HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>对分易签到</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
:root {
  --bg: #dee5ed;
  --bg-light: #e8eef6;
  --bg-dark: #cdd5e0;
  --shadow-dk: #b0bac8;
  --shadow-lt: #ffffff;
  --primary: #5b8def;
  --primary-d: #4a7ad6;
  --green: #2ecc71;
  --red: #e74c3c;
  --orange: #f39c12;
  --text: #2d3436;
  --text2: #636e72;
  --radius: 14px;
  --radius-sm: 10px;
}
body {
  font-family: "HarmonyOS Sans", "HarmonyOS Sans SC", -apple-system, "Microsoft YaHei", "Segoe UI", "PingFang SC", "Noto Sans CJK SC", sans-serif;
  background: var(--bg); color: var(--text); height: 100vh; overflow: hidden;
  display: flex; flex-direction: column;
  -webkit-user-select: none; user-select: none;
  font-size: 15px;
}

/* ===== Title Bar ===== */
.title-bar {
  display: flex; align-items: center; padding: 0 18px; height: 44px;
  background: var(--bg); flex-shrink: 0;
}
.title-bar .brand { font-weight: 800; font-size: 17px; color: var(--primary); }
.title-bar .ver { font-size: 12px; font-weight: 600; color: var(--text2); margin-left: 8px; }
.title-bar .spacer { flex: 1; }
.title-bar .win-btn {
  width: 36px; height: 28px; border: none; background: var(--bg);
  color: var(--text2); font-size: 14px; cursor: pointer; border-radius: 6px;
  box-shadow: none; margin-left: 4px;
}
.title-bar .win-btn:hover { background: var(--bg-dark); }

/* ===== Main Layout ===== */
.main { display: flex; flex: 1; padding: 0 10px 10px; gap: 10px; overflow: hidden; }

/* ===== Left Panel ===== */
.left-panel { width: 320px; flex-shrink: 0; display: flex; flex-direction: column; }

/* ===== Neu Card ===== */
.neu-card {
  background: var(--bg); border-radius: var(--radius);
  box-shadow: 5px 5px 12px var(--shadow-dk), -5px -5px 12px var(--shadow-lt);
  padding: 18px; margin-bottom: 10px;
}
.neu-card-inset {
  background: var(--bg); border-radius: var(--radius-sm);
  box-shadow: inset 3px 3px 7px var(--shadow-dk), inset -3px -3px 7px var(--shadow-lt);
}

/* ===== Tabs ===== */
.tab-bar { display: flex; gap: 6px; margin-bottom: 14px; }
.tab-btn {
  flex: 1; padding: 10px 0; text-align: center; border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text2); font-size: 14px; font-weight: 600; cursor: pointer;
  box-shadow: 3px 3px 6px var(--shadow-dk), -3px -3px 6px var(--shadow-lt);
  transition: all .15s; border: none;
}
.tab-btn.active {
  color: var(--primary); font-weight: 600;
  box-shadow: inset 3px 3px 6px var(--shadow-dk), inset -3px -3px 6px var(--shadow-lt);
}

/* ===== Form Elements ===== */
.neu-input {
  width: 100%; padding: 10px 14px; border: none; outline: none;
  background: var(--bg); color: var(--text); font-size: 14px; font-weight: 500; border-radius: var(--radius-sm);
  box-shadow: inset 3px 3px 7px var(--shadow-dk), inset -3px -3px 7px var(--shadow-lt);
  font-family: inherit; margin-bottom: 8px;
}
.neu-input:focus { box-shadow: inset 3px 3px 7px var(--shadow-dk), inset -3px -3px 7px var(--shadow-lt), 0 0 0 2px var(--primary); }

.neu-btn {
  padding: 10px 24px; border: none; border-radius: var(--radius-sm);
  background: var(--bg); color: var(--primary); font-size: 14px; font-weight: 700;
  cursor: pointer; font-family: inherit;
  box-shadow: 4px 4px 8px var(--shadow-dk), -4px -4px 8px var(--shadow-lt);
  transition: all .12s; margin-top: 8px;
}
.neu-btn:hover { box-shadow: 2px 2px 4px var(--shadow-dk), -2px -2px 4px var(--shadow-lt); }
.neu-btn:active { box-shadow: inset 3px 3px 6px var(--shadow-dk), inset -3px -3px 6px var(--shadow-lt); }
.neu-btn.green { color: var(--green); }
.neu-btn.red { color: var(--red); }

/* ===== Input Group ===== */
.input-group { margin-bottom: 6px; }
.input-group label { display: block; font-size: 13px; font-weight: 600; color: var(--text2); margin-bottom: 4px; padding-left: 4px; }

/* ===== Checkbox ===== */
.check-row { display: flex; align-items: center; gap: 6px; margin: 6px 0; font-size: 13px; font-weight: 500; color: var(--text2); cursor: pointer; }
.check-row input { width: 16px; height: 16px; cursor: pointer; accent-color: var(--primary); }

/* ===== Right Panel ===== */
.right-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; }

/* ===== Toolbar ===== */
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.toolbar label { font-size: 13px; font-weight: 600; color: var(--text2); white-space: nowrap; }
.toolbar select {
  flex: 1; padding: 8px 12px; border: none; border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text); font-size: 13px; font-weight: 500; font-family: inherit;
  box-shadow: inset 3px 3px 6px var(--shadow-dk), inset -3px -3px 6px var(--shadow-lt);
  outline: none; cursor: pointer;
  font-weight: 500;
}

/* ===== Log Console ===== */
.log-area {
  flex: 1; padding: 14px 16px; border-radius: var(--radius-sm); overflow-y: auto;
  background: var(--bg); color: var(--text); font-size: 13px; font-weight: 500; font-family: 'Consolas', monospace;
  box-shadow: inset 3px 3px 7px var(--shadow-dk), inset -3px -3px 7px var(--shadow-lt);
  line-height: 1.6; white-space: pre-wrap; word-break: break-all;
}
.log-area .cyan { color: var(--primary); }
.log-area .green { color: var(--green); }
.log-area .orange { color: var(--orange); }
.log-area .red { color: var(--red); }
.log-area .dim { color: var(--text2); }

/* ===== Status Bar ===== */
.status-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 16px; height: 30px; font-size: 12px; font-weight: 600; color: var(--text2); flex-shrink: 0;
  background: var(--bg);
  box-shadow: 0 -2px 6px rgba(0,0,0,0.04);
}
.status-bar .dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.status-bar .dot.green { background: var(--green); }
.status-bar .dot.red { background: var(--red); }
.status-bar .dot.gray { background: var(--text2); }

/* ===== Help text ===== */
.help-text { font-size: 13px; font-weight: 500; color: var(--text2); line-height: 1.8; }
.help-text .link { color: var(--primary); word-break: break-all; font-size: 11px; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--shadow-dk); border-radius: 3px; }

/* ===== Notification toast ===== */
.toast {
  position: fixed; top: 110px; right: 20px; padding: 10px 28px; border-radius: var(--radius-sm);
  background: var(--bg); color: var(--text); font-size: 14px; font-weight: 600; z-index: 999;
  box-shadow: 5px 5px 15px var(--shadow-dk), -5px -5px 15px var(--shadow-lt);
  opacity: 0; transform: translateX(40px); transition: all .3s ease; white-space: nowrap;
}
.toast.show { opacity: 1; transform: translateX(0); }
.toast.success { color: var(--green); }
.toast.error { color: var(--red); }
</style>
</head>
<body>

<div class="title-bar">
  <span class="brand">◈ 对分易 · 签到</span>
  <span class="ver">v5.28.3</span>
  <div class="spacer"></div>
  <button class="win-btn" onclick="iconify()">─</button>
  <button class="win-btn" onclick="exitApp()">✕</button>
</div>

<div class="main">
  <!-- Left Panel -->
  <div class="left-panel">
    <!-- Login Tab -->
    <div class="neu-card" style="flex:1; display:flex; flex-direction:column;">
      <div class="tab-bar" id="tabBar">
        <button class="tab-btn active" data-tab="0">微信链接</button>
        <button class="tab-btn" data-tab="1">账号密码</button>
      </div>

      <!-- Tab 0: WeChat Link -->
      <div id="tab0" class="tab-content">
        <div style="text-align:center;margin-bottom:8px;">
          <div style="font-size:12px;color:var(--text2);">支持二维码和签到码</div>
          <div style="font-size:11px;color:var(--text2);opacity:.7;">从微信复制链接粘贴到下方</div>
        </div>
        <div class="input-group">
          <label>登录链接</label>
          <input class="neu-input" id="linkInput" placeholder="粘贴微信链接...">
        </div>
        <button class="neu-btn" id="loginLinkBtn" onclick="loginLink()" style="width:100%;">登 录</button>
      </div>

      <!-- Tab 1: Password -->
      <div id="tab1" class="tab-content" style="display:none;">
        <div style="font-size:12px;color:var(--orange);margin-bottom:10px;">⚠ 不支持二维码签到</div>
        <div class="input-group"><label>账号</label><input class="neu-input" id="usernameInput" placeholder="请输入账号"></div>
        <div class="input-group"><label>密码</label><input class="neu-input" id="passwordInput" type="password" placeholder="请输入密码"></div>
        <div style="display:flex;align-items:center;gap:6px;margin:4px 0;">
          <span style="font-size:12px;color:var(--text2);">倒计时 ≤</span>
          <input class="neu-input" id="secondsInput" value="10" style="width:50px;padding:6px;text-align:center;margin:0;font-family:monospace;">
          <span style="font-size:12px;color:var(--text2);">秒后签到</span>
        </div>
        <label class="check-row"><input type="checkbox" id="rememberPwd"> 记住密码（支持自动重登）</label>
        <button class="neu-btn" onclick="loginPwd()" style="width:100%;">登 录</button>
      </div>
    </div>
  </div>

  <!-- Right Panel -->
  <div class="right-panel">
    <div class="neu-card" style="padding:12px 16px;margin-bottom:10px;">
      <div class="toolbar">
        <label>选择课程</label>
        <select id="courseSelect"><option value="">请先登录</option></select>
        <button class="neu-btn green" id="monitorBtn" onclick="toggleMonitor()" style="margin:0;padding:8px 16px;white-space:nowrap;">▶ 开始监听</button>
      </div>
    </div>
    <div class="neu-card" style="flex:1; display:flex; flex-direction:column; padding:10px;">
      <div class="log-area" id="logArea"></div>
    </div>
  </div>
</div>

<div class="status-bar">
  <span id="statusText"><span class="dot gray"></span>就绪</span>
  <span id="loginStatus"><span class="dot red"></span>未登录</span>
</div>

<div class="toast" id="toast"></div>

<script>
// ===== DPI自适应缩放 =====
(function() {
  var dpr = window.devicePixelRatio || 1;
  // Windows缩放比例: 100%=1.0, 125%=1.25, 150%=1.5, 175%=1.75, 200%=2.0
  if (dpr > 1.25) {
    var scale = Math.min(dpr / 1.25, 1.6);  // 限制最大缩放1.6x
    document.body.style.fontSize = (15 * scale) + 'px';
  }
})();

// ===== JS API =====
function log(text, cls) {
  const el = document.getElementById('logArea');
  if (cls) el.innerHTML += `<span class="${cls}">${text}</span>`;
  else el.innerHTML += text;
  el.scrollTop = el.scrollHeight;
}

function setStatus(text, color) {
  document.getElementById('statusText').innerHTML = `<span class="dot ${color||'gray'}"></span>${text}`;
}

function setLoginStatus(logged) {
  const el = document.getElementById('loginStatus');
  if (logged) el.innerHTML = '<span class="dot green"></span>已登录';
  else el.innerHTML = '<span class="dot red"></span>未登录';
}

function showToast(msg, cls) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.className = 'toast ' + (cls||'');
  setTimeout(() => t.classList.add('show'), 10);
  setTimeout(() => t.classList.remove('show'), 3000);
}

function clearLog() {
  document.getElementById('logArea').innerHTML = '';
}

// ===== Tabs =====
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', function() {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    document.getElementById('tab0').style.display = this.dataset.tab === '0' ? '' : 'none';
    document.getElementById('tab1').style.display = this.dataset.tab === '1' ? '' : 'none';
    if (this.dataset.tab === '0') showHelp();
  });
});

function showHelp() {
  clearLog();
  log('        1、打开电脑端微信，复制如下链接到文件传输助手并发送\n\n');
  log('        【https://open.weixin.qq.com/connect/oauth2/authorize?appid=wx1b5650884f657981&redirect_uri=https://www.duifene.com/_FileManage/PdfView.aspx?file=https%3A%2F%2Ffs.duifene.com%2Fres%2Fr2%2Fu6106199%2F%E5%AF%B9%E5%88%86%E6%98%93%E7%99%BB%E5%BD%95_876c9d439ca68ead389c.pdf&response_type=code&scope=snsapi_userinfo&connect_redirect=1#wechat_redirect】\n\n');
  log('        2、点击进入链接，点击微信浏览器窗口右上角三个点，点击复制链接，并把微信链接粘贴到左侧输入框。\n');
}

// ===== Login =====
async function loginLink() {
  const link = document.getElementById('linkInput').value;
  if (!link) { showToast('请输入登录链接', 'error'); return; }
  const result = await pywebview.api.login_link(link);
  if (result.success) {
    showToast('登录成功!', 'success');
    setLoginStatus(true);
    setStatus('已登录', 'green');
    updateCourses(result.courses);
  } else {
    showToast(result.error, 'error');
  }
}

async function loginPwd() {
  const u = document.getElementById('usernameInput').value;
  const p = document.getElementById('passwordInput').value;
  if (!u || !p) { showToast('请输入账号和密码', 'error'); return; }
  const remember = document.getElementById('rememberPwd').checked;
  const secs = document.getElementById('secondsInput').value || '10';
  const result = await pywebview.api.login_pwd(u, p, remember, secs);
  if (result.success) {
    showToast('登录成功!', 'success');
    setLoginStatus(true);
    setStatus('已登录', 'green');
    updateCourses(result.courses);
  } else {
    showToast(result.error, 'error');
  }
}

function updateCourses(courses) {
  const sel = document.getElementById('courseSelect');
  sel.innerHTML = '';
  courses.forEach((c, i) => {
    const opt = document.createElement('option');
    opt.value = i; opt.textContent = c.CourseName;
    sel.appendChild(opt);
  });
}

// ===== Monitor =====
var monitoring = false;

async function toggleMonitor() {
  const btn = document.getElementById('monitorBtn');
  if (monitoring) {
    await pywebview.api.stop_monitor();
    monitoring = false;
    btn.textContent = '▶ 开始监听';
    btn.className = 'neu-btn green';
    setStatus('已停止', 'orange');
    log('\n——— 监听已停止 ———\n', 'orange');
  } else {
    const sel = document.getElementById('courseSelect');
    if (!sel.value) { showToast('请先登录', 'error'); return; }
    const idx = parseInt(sel.value);
    const result = await pywebview.api.start_monitor(idx);
    if (result.success) {
      monitoring = true;
      btn.textContent = '■ 停止监听';
      btn.className = 'neu-btn red';
      setStatus('监听运行中', 'green');
      log('正在监听【' + result.courseName + '】的签到活动\n\n', 'cyan');
    } else {
      showToast(result.error, 'error');
    }
  }
}

// ===== Window Controls =====
function iconify() { pywebview.api.iconify(); }
function exitApp() { pywebview.api.exit_app(); }
function quitApp() { pywebview.api.quit_app(); }

// ===== Python callbacks (called from Python thread) =====
function pushLog(text, cls) { log(text, cls); }
function pushStatus(text, color) { setStatus(text, color); }
function pushLoginStatus(logged) { setLoginStatus(logged); }
function pushToast(msg, cls) { showToast(msg, cls); }

// Init
window.addEventListener('pywebviewready', function() {
  pywebview.api.init_app().then(function() {
    // loaded
  });
});
</script>
</body>
</html>"""

# ===== API Class (Exposed to JS) =====

class API:
    def __init__(self):
        self._monitoring = False
        self._monitor_after = None
        self._pwd_login = False
        self._saved_username = ''
        self._saved_password = ''
        self._secs_threshold = 10
        self._tray_icon = None
        self._window = None

    def set_window(self, w): self._window = w

    def _js(self, code):
        try:
            if self._window: self._window.evaluate_js(code)
        except: pass

    def _log(self, text, cls=None):
        t = text.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('"', '\\"')
        if cls: self._js(f"pushLog('{t}','{cls}')")
        else: self._js(f"pushLog('{t}')")

    def _status(self, text, color=None):
        t = text.replace("'", "\\'")
        c = color or 'gray'
        self._js(f"pushStatus('{t}','{c}')")

    def _login_status(self, v):
        self._js(f"pushLoginStatus({str(v).lower()})")

    def _toast(self, msg, cls=None):
        m = msg.replace("'", "\\'").replace('\n', '\\n')
        c = cls or ''
        self._js(f"pushToast('{m}','{c}')")

    def _populate_courses(self, data):
        if data and len(data) > 0:
            Course.class_list = data
            Course.id = data[0]["CourseID"]
            Course.class_id = data[0]["TClassID"]

    # ===== Init =====
    def init_app(self):
        try:
            if not os.path.exists(ini_path):
                cfg['INFO'] = {'cookie': '1=1'}
                with open(ini_path, 'w', encoding='utf-8') as f: cfg.write(f)
                x.get(HOST, timeout=15)
            else:
                try:
                    cfg.read(ini_path, encoding='utf-8')
                    ck = cfg.get('INFO','cookie','')
                    cookies = {}
                    for pair in ck.split('; '):
                        if '=' in pair:
                            k,v = pair.split('=',1)
                            cookies[k]=v
                    x.cookies.update(cookies)
                    ok, data = get_class_list()
                    if ok:
                        self._login_status(True)
                        return json.dumps({'ok':True, 'courses':data})
                        self._populate_courses(data)
                except: pass
                try:
                    pwd = load_password()
                    usr = load_username()
                    if usr and pwd:
                        self._saved_username = usr
                        self._saved_password = pwd
                        self._pwd_login = True
                except: pass
        except: pass
        self._log("系统启动 v" + VERSION + "\n", "green")
        return json.dumps({'ok':True})

    # ===== Login =====
    def login_link(self, link):
        code_match = re.search(r"(?<=code=)\S{32}", link)
        if not code_match:
            return {'success':False, 'error':'链接格式有误'}
        code = code_match[0]
        x.cookies.clear()
        try:
            r = x.get(HOST + f"/P.aspx?authtype=1&code={code}&state=1", timeout=15)
            if r.status_code == 200:
                ok, data = get_class_list()
                if ok:
                    save_cookie(r)
                    self._log("登录成功！\n", "green")
                    self._populate_courses(data)
                    return {'success':True, 'courses':data}
                else:
                    return {'success':False, 'error':str(data)}
            return {'success':False, 'error':'登录请求失败'}
        except Exception as e:
            return {'success':False, 'error':f'网络异常: {str(e)}'}

    def login_pwd(self, username, password, remember, secs):
        try: self._secs_threshold = int(secs)
        except: self._secs_threshold = 10
        headers = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
                   "Referer":"https://www.duifene.com/AppGate.aspx"}
        x.cookies.clear()
        try:
            x.get(HOST, timeout=15)
            r = x.post(HOST+"/AppCode/LoginInfo.ashx",
                       data=f"action=loginmb&loginname={username}&password={password}",
                       headers=headers, timeout=15)
            if r.status_code == 200:
                result = r.json()
                msg = result.get("msgbox","")
                if msg == "登录成功":
                    ok, data = get_class_list()
                    if ok:
                        save_cookie(r)
                        self._populate_courses(data)
                        self._log("登录成功！\n", "green")
                        if remember:
                            save_password(username, password)
                            self._saved_username = username
                            self._saved_password = password
                            self._pwd_login = True
                            self._log("密码已保存，支持自动重登\n", "dim")
                        return {'success':True, 'courses':data}
                return {'success':False, 'error':msg or '登录失败'}
            return {'success':False, 'error':'登录失败'}
        except Exception as e:
            return {'success':False, 'error':f'网络异常: {str(e)}'}

    # ===== Monitor =====
    def start_monitor(self, course_idx):
        if Course.class_list is None or course_idx >= len(Course.class_list):
            return {'success':False, 'error':'课程数据错误'}
        c = Course.class_list[course_idx]
        Course.id = c['CourseID']
        Course.class_id = c['TClassID']
        headers = {"Referer":"https://www.duifene.com/_UserCenter/MB/index.aspx"}
        try:
            r = x.get(HOST+"/_UserCenter/MB/Module.aspx?data="+Course.id, headers=headers, timeout=15)
            if r.status_code==200 and Course.id in r.text:
                cn = BeautifulSoup(r.text,'lxml').find(id="CourseName")
                name = cn.text if cn else '未知'
                Course.flag = True
                self._monitoring = True
                self._monitor_loop()
                return {'success':True, 'courseName':name}
            return {'success':False, 'error':'无法进入课程页面'}
        except Exception as e:
            return {'success':False, 'error':f'网络异常: {str(e)}'}

    def stop_monitor(self):
        self._monitoring = False
        Course.flag = False

    def _monitor_loop(self):
        if not self._monitoring or not Course.flag: return
        try: self._do_check()
        except Exception as e: self._log(f"\n监控异常: {str(e)}\n", "red")
        if self._monitoring and Course.flag:
            threading.Timer(1.0, self._monitor_loop).start()

    def _do_check(self):
        if not is_login():
            self._log("登录状态失效\n", "red")
            x.cookies.clear()
            self._login_status(False)
            if self._pwd_login and self._saved_username and self._saved_password:
                if self._auto_relogin(): pass
                else:
                    Course.flag=False; self._monitoring=False
                    self._toast("自动重登失败", "error")
                    return
            else:
                Course.flag=False; self._monitoring=False
                return
        # Fetch check-in page
        try:
            r = x.get(HOST+f"/_CheckIn/MB/TeachCheckIn.aspx?classid={Course.class_id}&temps=0&checktype=1&isrefresh=0&timeinterval=0&roomid=0&match=", timeout=15)
        except: return
        if r.status_code!=200 or "HFChecktype" not in r.text: return
        soup = BeautifulSoup(r.text,'lxml')
        try:
            HFSeconds = soup.find(id="HFSeconds").get("value")
            HFChecktype = soup.find(id="HFChecktype").get("value")
            HFCheckInID = soup.find(id="HFCheckInID").get("value")
            HFClassID = soup.find(id="HFClassID").get("value")
        except: return
        if None in (HFChecktype,HFCheckInID,HFClassID,HFSeconds): return
        if Course.class_id not in HFClassID: return
        if HFCheckInID in Course.check_list: return
        if int(HFSeconds) > self._secs_threshold: return
        ct = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        status = False
        if HFChecktype == '1':
            sc = soup.find(id="HFCheckCodeKey")
            if sc is None: return
            sc = sc.get("value")
            self._log(f"\n{ct} 签到ID:{HFCheckInID} 签到码:{sc}\n", "cyan")
            ok, msg = sign_code(sc)
            self._log(f"\t{msg}\n")
            status = ok
        elif HFChecktype == '2':
            if not HFCheckInID: return
            self._log(f"\n{ct} 签到ID:{HFCheckInID} 二维码签到\n", "cyan")
            ok, msg = sign_qrcode(HFCheckInID)
            self._log(f"\t{msg}\n")
            status = ok
        elif HFChecktype == '3':
            lon = soup.find(id="HFRoomLongitude")
            lat = soup.find(id="HFRoomLatitude")
            if lon is None or lat is None: return
            self._log(f"\n{ct} 签到ID:{HFCheckInID} 定位签到\n", "cyan")
            ok, msg = sign_location(lon.get("value"),lat.get("value"))
            self._log(f"\t{msg}\n")
            status = ok
        if status:
            Course.check_list.append(HFCheckInID)
            self._status(f"签到成功:{HFCheckInID}", "green")
        else:
            self._status(f"签到失败:{HFCheckInID}", "red")

    def _auto_relogin(self):
        self._log("尝试自动重登...\n", "orange")
        headers = {"Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
                   "Referer":"https://www.duifene.com/AppGate.aspx"}
        x.cookies.clear()
        try:
            x.get(HOST,timeout=15)
            r = x.post(HOST+"/AppCode/LoginInfo.ashx",
                       data=f"action=loginmb&loginname={self._saved_username}&password={self._saved_password}",
                       headers=headers,timeout=15)
            if r.status_code==200:
                j=r.json()
                if j.get("msgbox","")=="登录成功":
                    save_cookie(r)
                    ok,data=get_class_list()
                    if ok:
                        self._login_status(True)
                        self._log("自动重登成功!\n","green")
                        return True
            self._log(f"自动重登失败\n","red")
        except Exception as e:
            self._log(f"自动重登异常:{str(e)}\n","red")
        return False

    # ===== Window =====
    def iconify(self):
        if self._window: self._window.minimize()

    def exit_app(self):
        """✕ 按钮 → 隐藏到系统托盘."""
        if self._monitoring:
            self.stop_monitor()
        if self._window:
            self._window.hide()
        if self._tray_icon:
            try:
                self._tray_icon.notify("程序仍在后台运行", "双击托盘图标恢复窗口")
            except:
                pass

    def quit_app(self):
        """托盘退出 → 完全退出."""
        if self._monitoring:
            self.stop_monitor()
        os._exit(0)


# ===== Main =====
if __name__ == '__main__':
    import webview
    api = API()
    window = webview.create_window(
        f"{APP_NAME} v{VERSION}",
        html=HTML,
        js_api=api,
        width=1020, height=700,
        resizable=False,
        easy_drag=False,
    )
    api.set_window(window)
    # Tray
    try:
        from PIL import Image, ImageDraw
        import pystray
        def tray_show(icon, item):
            window.show()
            window.on_top = True
            window.on_top = False
        def tray_exit(icon, item):
            os._exit(0)
        img = Image.new("RGBA",(64,64),(0,0,0,0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([8,8,56,56],fill="#5b8def")
        draw.ellipse([14,14,50,50],fill="#dee5ed")
        draw.polygon([(24,32),(30,40),(42,24)],fill="#5b8def")
        icon = pystray.Icon("du1fEny1", img, f"对分易签到 v{VERSION}",
                           pystray.Menu(pystray.MenuItem("显示窗口",tray_show,default=True),
                                        pystray.MenuItem("退出程序",tray_exit)))
        icon.run_detached()
        api.tray_icon = icon
    except:
        pass

    def on_closing():
        """点击原生关闭按钮 → 隐藏到托盘."""
        window.hide()
        return False  # 阻止销毁

    window.events.closing += on_closing
    webview.start(gui='edgechromium', debug=False)
