#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对分易自动签到程序 v5.28.1 — Neo-Cyber 设计版
基于 liuzhijie443/duifene_auto_sign
"""

import configparser
import os.path
import re
import random
import sys
import ctypes
from datetime import datetime

import tkinter as tk
from tkinter import messagebox, ttk
import requests
import urllib3
from bs4 import BeautifulSoup

# ============ DPI 感知 ============
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def get_dpi_scale():
    try:
        monitor = ctypes.windll.user32.MonitorFromPoint((0, 0), 2)
        dpi_x = ctypes.c_uint()
        dpi_y = ctypes.c_uint()
        ctypes.windll.shcore.GetDpiForMonitor(
            monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
        )
        return dpi_x.value / 96.0
    except Exception:
        return 1.0


# ============ 常量 ============
VERSION = "5.28.1"
APP_NAME = "对分易签到"
HOST = "https://www.duifene.com"
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) '
      'Mobile/15E148 MicroMessenger/8.0.40(0x1800282a) NetType/WIFI Language/zh_CN')

urllib3.disable_warnings()

# ============ 全局状态 ============
x = requests.Session()
x.headers['User-Agent'] = UA
x.verify = False

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
filename = os.path.join(BASE_DIR, 'duifenyi.ini')
config = configparser.ConfigParser()


class Course:
    id = '0'
    class_id = '0'
    flag = True
    check_list = []
    class_list = []


# ============ Neo-Cyber 色彩系统 ============
C = {
    "bg0":       "#080c14",   # 最深背景
    "bg1":       "#0d1321",   # 主背景
    "bg2":       "#141b2d",   # 面板背景
    "bg3":       "#1c253c",   # 卡片/控件背景
    "surface":   "#1e2a45",   # 输入框表面
    "border":    "#263353",   # 边框
    "border_lt": "#31416a",   # 亮边框
    "cyan":      "#22d3ee",   # 青色主色
    "cyan_dim":  "#155e75",   # 青色暗
    "cyan_bg":   "#0a2a3a",   # 青色背景
    "blue":      "#3b82f6",   # 蓝
    "green":     "#10b981",   # 绿
    "green_dim": "#064e3b",   # 绿暗
    "red":       "#ef4444",   # 红
    "orange":    "#f59e0b",   # 橙
    "gold":      "#fbbf24",   # 金色
    "text":      "#e8edf5",   # 主文字
    "text2":     "#94a3b8",   # 次要文字
    "text3":     "#475569",   # 辅助文字
    "font_ui":   "Microsoft YaHei",
    "font_mono": "Consolas",
}


# ============ 工具函数 ============

def save_cookie(resp):
    cookie_str = '; '.join([f'{c.name}={c.value}' for c in x.cookies])
    config['INFO'] = {'cookie': cookie_str}
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            config.write(f)
    except Exception:
        pass


def get_user_id():
    try:
        _r = x.get(url=HOST + "/_UserCenter/MB/index.aspx", timeout=15)
        if _r.status_code == 200:
            soup = BeautifulSoup(_r.text, "lxml")
            stu_id = soup.find(id="hidUID")
            if stu_id:
                return stu_id.get("value")
    except Exception:
        pass
    return ""


def is_login():
    try:
        headers = {
            "Referer": "https://www.duifene.com/_UserCenter/PC/CenterStudent.aspx",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        _r = x.get(HOST + "/AppCode/LoginInfo.ashx", data="Action=checklogin",
                   headers=headers, timeout=15)
        if _r.status_code == 200:
            return _r.json().get("msg") == "1"
    except Exception:
        pass
    return False


def get_class_list():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.duifene.com/_UserCenter/PC/CenterStudent.aspx"
    }
    params = "action=getstudentcourse&classtypeid=2"
    try:
        _r = x.post(url=HOST + "/_UserCenter/CourseInfo.ashx", data=params,
                    headers=headers, timeout=15)
        if _r.status_code == 200:
            _json = _r.json()
            if _json is not None:
                if isinstance(_json, dict) and "msgbox" in _json:
                    return False, _json["msgbox"]
                return True, _json
    except Exception:
        pass
    return False, None


# ============ 签到逻辑 ============

def sign_code_sign(sign_code, text_callback=None):
    student_id = get_user_id()
    if not student_id:
        return False
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.duifene.com/_CheckIn/MB/CheckInStudent.aspx?moduleid=16&pasd="
    }
    params = f"action=studentcheckin&studentid={student_id}&checkincode={sign_code}"
    try:
        _r = x.post(url=HOST + "/_CheckIn/CheckIn.ashx", data=params,
                    headers=headers, timeout=15)
        if _r.status_code == 200:
            result = _r.json()
            msg = result.get("msgbox", "")
            if text_callback:
                text_callback(f"\t{msg}\n\n")
            return msg == "签到成功！"
    except Exception as e:
        if text_callback:
            text_callback(f"\t签到请求异常: {str(e)}\n")
    return False


def sign_qrcode(checkin_id, text_callback=None):
    try:
        _r = x.get(url=HOST + "/_CheckIn/MB/QrCodeCheckOK.aspx?state=" + checkin_id, timeout=15)
        if _r.status_code == 200:
            soup = BeautifulSoup(_r.text, "lxml")
            div_ok = soup.find(id="DivOK")
            if div_ok:
                msg = div_ok.get_text(strip=True)
                if "签到成功" in msg:
                    if text_callback:
                        text_callback(f"\t{msg}\n\n")
                else:
                    if text_callback:
                        text_callback(f"\t非微信链接登录，二维码无法签到\n\n")
                return True
    except Exception as e:
        if text_callback:
            text_callback(f"\t二维码签到异常: {str(e)}\n")
    return False


def sign_location(longitude, latitude, text_callback=None):
    longitude = str(round(float(longitude) + random.uniform(-0.000089, 0.000089), 8))
    latitude = str(round(float(latitude) + random.uniform(-0.000089, 0.000089), 8))
    student_id = get_user_id()
    if not student_id:
        return False
    headers = {
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Referer": "https://www.duifene.com/_CheckIn/MB/CheckInStudent.aspx?moduleid=16&pasd="
    }
    params = f"action=signin&sid={student_id}&longitude={longitude}&latitude={latitude}"
    try:
        _r = x.post(url=HOST + "/_CheckIn/CheckInRoomHandler.ashx", data=params,
                    headers=headers, timeout=15)
        if _r.status_code == 200:
            result = _r.json()
            msg = result.get("msgbox", "")
            if text_callback:
                text_callback(f"\t{msg}\n\n")
            return msg == "签到成功！"
    except Exception as e:
        if text_callback:
            text_callback(f"\t定位签到异常: {str(e)}\n")
    return False


# ============ Neo-Cyber GUI ============

class DuifeneApp:
    def __init__(self):
        self.SF = get_dpi_scale()

        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.configure(bg=C["bg0"])
        self.root.resizable(False, False)
        # 移除窗口装饰，使用自定义标题栏
        self.root.overrideredirect(True)
        # 窗口初始尺寸
        self._win_w = self._s(1020)
        self._win_h = self._s(700)
        self.root.geometry(f"{self._win_w}x{self._win_h}")

        # 状态变量
        self._monitoring = False
        self._monitor_after_id = None
        self._logged_in = False
        self._sign_code_threshold = 10
        self._show_password = False

        self._build_ui()
        self._init_app()

    def _s(self, n):
        if n == 0:
            return 0
        return max(1, round(n * self.SF))

    # ===== 自定义按钮 =====

    def _make_btn(self, parent, text, command, accent=None, **kw):
        """创建 Neo-Cyber 风格按钮."""
        ac = accent or C["cyan"]
        btn = tk.Button(
            parent, text=text, command=command,
            bg=C["bg3"], fg=ac,
            font=(C["font_ui"], self._s(10), "bold"),
            borderwidth=0, relief="flat",
            activebackground=ac, activeforeground="#fff",
            cursor="hand2", padx=self._s(16), pady=self._s(6),
            **kw
        )
        # hover 效果
        btn.bind("<Enter>", lambda e, b=btn, c=ac: b.configure(bg=c, fg="#fff"))
        btn.bind("<Leave>", lambda e, b=btn, c=ac, bg=C["bg3"]: b.configure(bg=bg, fg=c))
        return btn

    # ===== UI 构建 =====

    def _build_ui(self):
        root = self.root
        s = self._s

        # ========== 自定义标题栏 ==========
        title_bg = C["bg0"]
        title_h = s(44)
        title_bar = tk.Frame(root, bg=title_bg, height=title_h)
        title_bar.pack(fill="x")
        title_bar.pack_propagate(False)

        # 拖拽移动窗口
        title_bar.bind("<Button-1>", self._drag_start)
        title_bar.bind("<B1-Motion>", self._drag_move)

        # 左上: 品牌标识
        brand = tk.Label(
            title_bar, text="◈ 对分易 · 签到",
            fg=C["cyan"], bg=title_bg,
            font=(C["font_ui"], s(12), "bold"),
        )
        brand.pack(side="left", padx=(s(14), 0))
        brand.bind("<Button-1>", self._drag_start)
        brand.bind("<B1-Motion>", self._drag_move)

        # 版本标签
        ver_lbl = tk.Label(
            title_bar, text=f"v{VERSION}",
            fg=C["text3"], bg=title_bg,
            font=(C["font_mono"], s(8)),
        )
        ver_lbl.pack(side="left", padx=(s(6), 0))

        # 右侧: 窗口控制按钮
        btn_frame = tk.Frame(title_bar, bg=title_bg)
        btn_frame.pack(side="right", padx=(0, s(10)))

        for btn_data in [
            ("─", self._iconify, C["text2"]),
            ("✕", self._on_close, C["red"]),
        ]:
            b = tk.Label(
                btn_frame, text=btn_data[0],
                fg=btn_data[2], bg=title_bg,
                font=(C["font_ui"], s(12)),
                cursor="hand2", padx=s(8), pady=0,
            )
            b.pack(side="right")
            b.bind("<Button-1>", lambda e, cb=btn_data[1]: cb())
            b.bind("<Enter>", lambda e, lb=b, c=btn_data[2]: lb.configure(fg="#fff"))
            b.bind("<Leave>", lambda e, lb=b, c=btn_data[2]: lb.configure(fg=c))

        # 标题栏底部分隔线
        sep = tk.Frame(root, bg=C["border"], height=1)
        sep.pack(fill="x")

        # ========== 主容器 ==========
        main = tk.Frame(root, bg=C["bg1"])
        main.pack(fill="both", expand=True, padx=s(1), pady=(0, 1))

        # -- 左侧面板: 登录 --
        left = tk.Frame(main, bg=C["bg2"], width=s(340))
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        # Tab 切换 (自制)
        self._build_left_tabs(left)

        # -- 右侧面板: 课程 + 日志 --
        right = tk.Frame(main, bg=C["bg1"])
        right.pack(side="right", fill="both", expand=True)

        self._build_right_panel(right)

        # -- 底部状态栏 --
        self._build_statusbar(root)

        # 窗口圆角遮罩 (Win11 风格)
        self._round_corners()

    def _build_left_tabs(self, parent):
        """自制 Tab 切换 (替代 ttk.Notebook)."""
        s = self._s
        # Tab 按钮行
        tab_bar = tk.Frame(parent, bg=C["bg2"])
        tab_bar.pack(fill="x")

        self._tab_btns = []
        for i, (label, tip) in enumerate([
            ("微信链接", "支持二维码和签到码"),
            ("账号密码", "不支持二维码签到"),
        ]):
            btn = tk.Label(
                tab_bar, text=label,
                bg=C["bg2"], fg=C["text3"],
                font=(C["font_ui"], s(10)),
                cursor="hand2", padx=s(16), pady=s(8),
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, idx=i: self._switch_tab(idx))
            btn.bind("<Enter>", lambda e, b=btn: (
                b.configure(bg=C["bg3"]) if b["bg"] != C["cyan_bg"] else None
            ))
            btn.bind("<Leave>", lambda e, b=btn, bg=C["bg2"]: (
                b.configure(bg=bg) if b["bg"] != C["cyan_bg"] else None
            ))
            self._tab_btns.append(btn)

        # Tab 内容容器
        self._tab_contents = tk.Frame(parent, bg=C["bg2"])
        self._tab_contents.pack(fill="both", expand=True, padx=s(12), pady=(s(8), s(12)))

        # --- Tab 0: 微信链接登录 ---
        self.tab0_frame = tk.Frame(self._tab_contents, bg=C["bg2"])

        tk.Label(
            self.tab0_frame, text="支持二维码和签到码",
            fg=C["text2"], bg=C["bg2"],
            font=(C["font_ui"], s(9)),
        ).pack(pady=(s(16), s(2)))

        tk.Label(
            self.tab0_frame, text="从微信复制链接粘贴到下方",
            fg=C["text3"], bg=C["bg2"],
            font=(C["font_ui"], s(8)),
        ).pack(pady=(0, s(12)))

        tk.Label(
            self.tab0_frame, text="登录链接",
            fg=C["cyan"], bg=C["bg2"],
            font=(C["font_mono"], s(9)),
        ).pack(anchor="w", pady=(0, s(4)))

        entry_bg = C["surface"]
        self.link_entry = tk.Entry(
            self.tab0_frame,
            font=(C["font_ui"], s(10)),
            bg=entry_bg, fg=C["text"],
            insertbackground=C["cyan"],
            borderwidth=0, relief="flat",
            highlightthickness=1,
            highlightbackground=C["border"],
            highlightcolor=C["cyan"],
        )
        self.link_entry.pack(fill="x", ipady=s(6))
        self.link_entry.bind("<FocusIn>", lambda e: self.link_entry.configure(
            highlightbackground=C["cyan"]))
        self.link_entry.bind("<FocusOut>", lambda e: self.link_entry.configure(
            highlightbackground=C["border"]))

        self._make_btn(self.tab0_frame, "登  录", self._on_login_link, C["cyan"])\
            .pack(pady=(s(12), 0))

        # --- Tab 1: 账号密码登录 ---
        self.tab1_frame = tk.Frame(self._tab_contents, bg=C["bg2"])

        tk.Label(
            self.tab1_frame, text="⚠ 不支持二维码签到",
            fg=C["orange"], bg=C["bg2"],
            font=(C["font_ui"], s(9)),
        ).pack(pady=(s(16), s(8)))

        for label_text, var_attr in [("账号", "username_entry"), ("密码", "password_entry")]:
            tk.Label(
                self.tab1_frame, text=label_text,
                fg=C["text2"], bg=C["bg2"],
                font=(C["font_ui"], s(9)),
            ).pack(anchor="w", pady=(s(8), s(2)))

            entry = tk.Entry(
                self.tab1_frame,
                font=(C["font_ui"], s(10)),
                bg=entry_bg, fg=C["text"],
                insertbackground=C["cyan"],
                borderwidth=0, relief="flat",
                highlightthickness=1,
                highlightbackground=C["border"],
                highlightcolor=C["cyan"],
                show="*" if label_text == "密码" else "",
            )
            entry.pack(fill="x", ipady=s(6))
            entry.bind("<FocusIn>", lambda e, en=entry: en.configure(
                highlightbackground=C["cyan"]))
            entry.bind("<FocusOut>", lambda e, en=entry: en.configure(
                highlightbackground=C["border"]))

            setattr(self, var_attr, entry)

        # 倒计时 + 登录按钮行
        row = tk.Frame(self.tab1_frame, bg=C["bg2"])
        row.pack(fill="x", pady=(s(12), 0))

        tk.Label(
            row, text="倒计时 ≤", fg=C["text3"], bg=C["bg2"],
            font=(C["font_ui"], s(9)),
        ).pack(side="left")

        self.seconds_entry = tk.Entry(
            row, font=(C["font_mono"], s(10)), width=4,
            bg=entry_bg, fg=C["cyan"],
            insertbackground=C["cyan"],
            borderwidth=0, relief="flat",
            highlightthickness=1,
            highlightbackground=C["border"],
            justify="center",
        )
        self.seconds_entry.insert(0, "10")
        self.seconds_entry.pack(side="left", padx=s(4), ipady=s(2))

        tk.Label(
            row, text="秒后签到", fg=C["text3"], bg=C["bg2"],
            font=(C["font_ui"], s(9)),
        ).pack(side="left")

        self._make_btn(self.tab1_frame, "登  录", self._on_login_pwd, C["cyan"])\
            .pack(pady=(s(12), 0))

        # 默认显示 tab0
        self._current_tab = 0
        self.tab0_frame.pack(fill="both", expand=True)

    def _build_right_panel(self, parent):
        s = self._s

        # -- 工具栏 --
        toolbar = tk.Frame(parent, bg=C["bg2"])
        toolbar.pack(fill="x")

        tk.Label(
            toolbar, text="选择课程",
            fg=C["text2"], bg=C["bg2"],
            font=(C["font_ui"], s(9)),
        ).pack(side="left", padx=(s(12), s(6)), pady=s(8))

        self.combo_var = tk.StringVar()
        self.combo = ttk.Combobox(
            toolbar, textvariable=self.combo_var,
            state="readonly",
            font=(C["font_ui"], s(9)),
            width=20,
        )
        self.combo.bind("<<ComboboxSelected>>", self._on_course_change)
        self.combo.pack(side="left", pady=s(8))

        self.monitor_btn = self._make_btn(
            toolbar, "▶ 开始监听", self._on_toggle_monitor, C["green"]
        )
        self.monitor_btn.pack(side="right", padx=(s(6), s(12)), pady=s(6))

        # -- 日志输出框 --
        log_bg = C["bg0"]
        self.text_box = tk.Text(
            parent,
            width=90, height=22,
            font=(C["font_mono"], s(9)),
            bg=log_bg, fg=C["text"],
            insertbackground=C["cyan"],
            borderwidth=0, relief="flat",
            padx=s(10), pady=s(8),
            highlightthickness=1,
            highlightbackground=C["border"],
            state="normal",
        )
        self.text_box.pack(fill="both", expand=True, padx=s(8), pady=(s(4), s(8)))

        # 配色
        for tag, color in [
            ("cyan", C["cyan"]), ("green", C["green"]),
            ("orange", C["orange"]), ("red", C["red"]),
            ("dim", C["text3"]), ("gold", C["gold"]),
        ]:
            self.text_box.tag_configure(tag, foreground=color)

    def _build_statusbar(self, parent):
        s = self._s
        bar = tk.Frame(parent, bg=C["bg0"], height=s(26))
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # 上部分隔线
        tk.Frame(bar, bg=C["border"], height=1).pack(fill="x")

        inner = tk.Frame(bar, bg=C["bg0"])
        inner.pack(fill="x", expand=True)

        self.status_label = tk.Label(
            inner, text="就绪", fg=C["text3"], bg=C["bg0"],
            font=(C["font_mono"], s(8)), anchor="w",
        )
        self.status_label.pack(side="left", padx=s(10))

        self.login_status_label = tk.Label(
            inner, text="● 未登录", fg=C["red"], bg=C["bg0"],
            font=(C["font_mono"], s(8)),
        )
        self.login_status_label.pack(side="right", padx=s(10))

    # ===== 窗口控制 =====

    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        x = self.root.winfo_x() + event.x - self._drag_x
        y = self.root.winfo_y() + event.y - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _iconify(self):
        self.root.iconify()

    def _on_close(self):
        if self._monitoring:
            self._stop_monitor()
        self.root.destroy()

    def _round_corners(self):
        """Win11 圆角效果."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            DWMWA_WINDOW_CORNER_PREFERENCE = 33
            DWM_WCP_ROUND = 2
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE,
                ctypes.byref(ctypes.c_int(DWM_WCP_ROUND)),
                ctypes.sizeof(ctypes.c_int)
            )
        except Exception:
            pass

    # ===== Tab 切换 =====

    def _switch_tab(self, idx):
        if idx == self._current_tab:
            return
        self._current_tab = idx
        # 更新 tab 按钮样式
        for i, btn in enumerate(self._tab_btns):
            if i == idx:
                btn.configure(bg=C["cyan_bg"], fg=C["cyan"])
            else:
                btn.configure(bg=C["bg2"], fg=C["text3"])

        # 切换内容
        self.tab0_frame.pack_forget()
        self.tab1_frame.pack_forget()
        target = [self.tab0_frame, self.tab1_frame][idx]
        target.pack(fill="both", expand=True)

        # 写入说明到日志
        self.text_box.delete("1.0", "end")
        if idx == 0:
            help_text = (
                "        1、打开电脑端微信，复制如下链接到文件传输助手并发送\n\n"
                "        【https://open.weixin.qq.com/connect/oauth2/authorize"
                "?appid=wx1b5650884f657981&redirect_uri=https://www.duifene.com"
                "/_FileManage/PdfView.aspx?file=https%3A%2F%2Ffs.duifene.com"
                "%2Fres%2Fr2%2Fu6106199%2F%E5%AF%B9%E5%88%86%E6%98%93%E7%99%BB"
                "%E5%BD%95_876c9d439ca68ead389c.pdf&response_type=code"
                "&scope=snsapi_userinfo&connect_redirect=1#wechat_redirect】\n\n"
                "        2、点击进入链接，点击微信浏览器窗口右上角三个点，"
                "点击复制链接，并把微信链接粘贴到左侧输入框。\n"
            )
            self._insert_log(help_text)

    # ===== 课程选择 =====

    def _on_course_change(self, event):
        class_name = self.combo_var.get()
        for c in Course.class_list:
            if c["CourseName"] == class_name:
                Course.id = c["CourseID"]
                Course.class_id = c["TClassID"]
                self._insert_log(f"已选择课程: {class_name}\n", "cyan")

    # ===== 登录逻辑 =====

    def _on_login_link(self):
        link = self.link_entry.get().strip()
        code_match = re.search(r"(?<=code=)\S{32}", link)
        if code_match:
            code = code_match[0]
            x.cookies.clear()
            try:
                _r = x.get(url=HOST + f"/P.aspx?authtype=1&code={code}&state=1", timeout=15)
                if _r.status_code == 200:
                    ok, data = get_class_list()
                    if ok:
                        save_cookie(_r)
                        self._populate_courses(data)
                        self._set_login_status(True)
                        self._insert_log("✓ 登录成功！\n", "green")
                    else:
                        self._insert_log(f"✗ 登录失败: {data}\n", "red")
                else:
                    messagebox.showerror("错误", "登录请求失败")
            except Exception as e:
                messagebox.showerror("错误", f"网络异常: {str(e)}")
        else:
            messagebox.showerror("错误", "链接格式有误")

    def _on_login_pwd(self):
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": "https://www.duifene.com/AppGate.aspx"
        }
        params = (f'action=loginmb&loginname={self.username_entry.get()}'
                  f'&password={self.password_entry.get()}')
        x.cookies.clear()
        try:
            x.get(HOST, timeout=15)
            _r = x.post(url=HOST + "/AppCode/LoginInfo.ashx", data=params,
                        headers=headers, timeout=15)
            if _r.status_code == 200:
                self.text_box.delete("1.0", "end")
                result = _r.json()
                msg = result.get("msgbox", "")
                self._insert_log(f"\n{msg}\n")
                if msg == "登录成功":
                    ok, data = get_class_list()
                    if ok:
                        save_cookie(_r)
                        self._populate_courses(data)
                        self._set_login_status(True)
                        self._insert_log("✓ 登录成功！\n", "green")
                elif msg:
                    self._insert_log(f"✗ 登录失败: {msg}\n", "red")
            else:
                messagebox.showerror("错误提示", "登录失败")
        except Exception as e:
            messagebox.showerror("错误提示", f"网络异常: {str(e)}")

    def _populate_courses(self, course_list):
        names = [c["CourseName"] for c in course_list]
        self.combo['values'] = tuple(names)
        if names:
            self.combo.set(names[0])
            Course.id = course_list[0]['CourseID']
            Course.class_id = course_list[0]["TClassID"]
            Course.class_list = course_list
            self._insert_log(f"已加载 {len(names)} 门课程\n", "cyan")

    # ===== 监控逻辑 =====

    def _on_toggle_monitor(self):
        if self._monitoring:
            self._stop_monitor()
        else:
            self._start_monitor()

    def _start_monitor(self):
        if not self._logged_in:
            messagebox.showerror("错误提示", "请先登录")
            return
        if not self.combo.get():
            messagebox.showerror("错误提示", "请先登录")
            return

        headers = {"Referer": "https://www.duifene.com/_UserCenter/MB/index.aspx"}
        try:
            _r = x.get(url=HOST + "/_UserCenter/MB/Module.aspx?data=" + Course.id,
                       headers=headers, timeout=15)
            if _r.status_code == 200 and Course.id in _r.text:
                self.text_box.delete("1.0", "end")
                soup = BeautifulSoup(_r.text, "lxml")
                cn = soup.find(id="CourseName")
                name = cn.text if cn else "未知"
                self._insert_log(f"正在监听【{name}】的签到活动\n\n", "cyan")
            else:
                self._insert_log("无法进入课程页面\n", "red")
                return
        except Exception as e:
            self._insert_log(f"进入课程失败: {str(e)}\n", "red")
            return

        try:
            self._sign_code_threshold = int(self.seconds_entry.get())
        except ValueError:
            self._sign_code_threshold = 10

        self._monitoring = True
        self.monitor_btn.configure(text="■ 停止监听", fg=C["red"])
        self.monitor_btn.unbind("<Enter>")
        self.monitor_btn.unbind("<Leave>")
        self.monitor_btn.bind("<Enter>", lambda e: self.monitor_btn.configure(bg=C["red"], fg="#fff"))
        self.monitor_btn.bind("<Leave>", lambda e: self.monitor_btn.configure(bg=C["bg3"], fg=C["red"]))
        self._set_status("监听运行中", C["green"])
        Course.flag = True
        self._monitor_cycle()

    def _stop_monitor(self):
        self._monitoring = False
        Course.flag = False
        if self._monitor_after_id:
            self.root.after_cancel(self._monitor_after_id)
            self._monitor_after_id = None
        self.monitor_btn.configure(text="▶ 开始监听", fg=C["green"])
        self.monitor_btn.unbind("<Enter>")
        self.monitor_btn.unbind("<Leave>")
        self.monitor_btn.bind("<Enter>", lambda e: self.monitor_btn.configure(bg=C["green"], fg="#fff"))
        self.monitor_btn.bind("<Leave>", lambda e: self.monitor_btn.configure(bg=C["bg3"], fg=C["green"]))
        self._set_status("已停止", C["orange"])
        self._insert_log("\n——— 监听已停止 ———\n", "orange")

    def _monitor_cycle(self):
        if not self._monitoring or not Course.flag:
            return
        try:
            self._do_check()
        except Exception as e:
            self._insert_log(f"\n监控异常: {str(e)}\n", "red")
        if self._monitoring and Course.flag:
            self._monitor_after_id = self.root.after(1000, self._monitor_cycle)

    def _do_check(self):
        if not is_login():
            self._insert_log("登录状态失效，请重新登录\n", "red")
            x.cookies.clear()
            Course.flag = False
            self._set_login_status(False)
            self._stop_monitor()
            return

        line_count = int(self.text_box.index('end-1c').split('.')[0])
        ct = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.text_box.delete(f"{line_count}.0", f"{line_count}.end")
        self._insert_log(f"持续监控：{ct}")

        try:
            _r = x.get(
                url=(f"{HOST}/_CheckIn/MB/TeachCheckIn.aspx?"
                     f"classid={Course.class_id}&temps=0&checktype=1"
                     f"&isrefresh=0&timeinterval=0&roomid=0&match="),
                timeout=15
            )
        except Exception:
            return

        if _r.status_code != 200 or "HFChecktype" not in _r.text:
            return

        soup = BeautifulSoup(_r.text, "lxml")
        try:
            HFSeconds = soup.find(id="HFSeconds").get("value")
            HFChecktype = soup.find(id="HFChecktype").get("value")
            HFCheckInID = soup.find(id="HFCheckInID").get("value")
            HFClassID = soup.find(id="HFClassID").get("value")
        except AttributeError:
            return
        if None in (HFChecktype, HFCheckInID, HFClassID, HFSeconds):
            return

        if Course.class_id not in HFClassID:
            self._insert_log("\t检测到非本班签到\n", "dim")
            return
        if HFCheckInID in Course.check_list:
            return
        if int(HFSeconds) > self._sign_code_threshold:
            return

        status = False
        ct = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        if HFChecktype == '1':
            sc = soup.find(id="HFCheckCodeKey")
            if sc is None:
                return
            sc = sc.get("value")
            self._insert_log(f"\n\n{ct} 签到ID：{HFCheckInID} 开始签到\t签到码：{sc}\n", "cyan")
            status = sign_code_sign(sc, text_callback=self._insert_log)
        elif HFChecktype == '2':
            if not HFCheckInID:
                return
            self._insert_log(f"\n\n{ct} 签到ID：{HFCheckInID} 开始签到\t二维码签到\n", "cyan")
            status = sign_qrcode(HFCheckInID, text_callback=self._insert_log)
        elif HFChecktype == '3':
            lon = soup.find(id="HFRoomLongitude")
            lat = soup.find(id="HFRoomLatitude")
            if lon is None or lat is None:
                return
            self._insert_log(f"\n\n{ct} 签到ID：{HFCheckInID} 开始签到\t定位签到\n", "cyan")
            status = sign_location(lon.get("value"), lat.get("value"),
                                  text_callback=self._insert_log)

        if status:
            Course.check_list.append(HFCheckInID)
            self._set_status(f"签到成功: {HFCheckInID}", C["green"])
        else:
            self._set_status(f"签到失败: {HFCheckInID}", C["red"])

    # ===== UI 辅助 =====

    def _insert_log(self, text, tag=None):
        self.text_box.insert(tk.END, text, tag if tag else ())
        self.text_box.see(tk.END)

    def _set_status(self, text, color=None):
        self.status_label.configure(text=text)
        if color:
            self.status_label.configure(fg=color)

    def _set_login_status(self, logged_in):
        self._logged_in = logged_in
        if logged_in:
            self.login_status_label.configure(text="● 已登录", fg=C["green"])
        else:
            self.login_status_label.configure(text="● 未登录", fg=C["red"])

    # ===== 初始化 =====

    def _init_app(self):
        try:
            if not os.path.exists(filename):
                config['INFO'] = {'cookie': '1=1'}
                with open(filename, 'w', encoding='utf-8') as f:
                    config.write(f)
                x.get(HOST, timeout=15)
            else:
                try:
                    config.read(filename, encoding='utf-8')
                    cookie = config.get('INFO', 'cookie')
                    cookies = {}
                    for pair in cookie.split('; '):
                        if '=' in pair:
                            k, v = pair.split('=', 1)
                            cookies[k] = v
                    x.cookies.update(cookies)
                    ok, data = get_class_list()
                    if ok:
                        self._populate_courses(data)
                        self._set_login_status(True)
                    else:
                        self._set_login_status(False)
                except Exception:
                    pass
        except (requests.ConnectionError, requests.Timeout):
            messagebox.showwarning("网络状态", "未检测到互联网连接。")
            self.root.destroy()

    def run(self):
        self.root.mainloop()


# ============ 入口 ============

if __name__ == '__main__':
    app = DuifeneApp()
    app.run()
