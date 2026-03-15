# -*- coding: utf-8 -*-
"""
杀戮尖塔2 地图绘制工具
SlayTheSpire2 Map Painter
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
import pyautogui
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
import threading
import time
import sys
from collections import deque
from pynput import mouse

# 配置
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0


class RegionSelector:
    """区域选择器 - 使用tkinter在原窗口画布上选择"""

    def __init__(self, title, image):
        self.image = image.copy()
        self.selection = None
        self.title = title

    def select_with_canvas(self, root, canvas):
        """在已有的canvas上进行选择"""
        # 获取canvas尺寸
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()

        # 缩放图片以适应canvas
        img_h, img_w = self.image.shape[:2]
        scale = min(canvas_w / img_w, canvas_h / img_h)
        display_w = int(img_w * scale)
        display_h = int(img_h * scale)

        display_img = cv2.resize(self.image, (display_w, display_h))
        display_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(display_rgb)
        self.tk_img = ImageTk.PhotoImage(pil_img)

        # 在canvas上显示图片
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        # 选框变量
        rect_id = None
        start_x = None
        start_y = None
        selection_done = [False]  # 用列表以便在内部函数中修改

        def on_mouse_down(event):
            nonlocal start_x, start_y, rect_id
            start_x = event.x
            start_y = event.y
            rect_id = canvas.create_rectangle(
                start_x, start_y, start_x, start_y, outline="red", width=3
            )

        def on_mouse_move(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)

        def on_mouse_up(event):
            nonlocal rect_id, start_x, start_y
            if rect_id:
                end_x = event.x
                end_y = event.y

                x1 = int(min(start_x, end_x))
                x2 = int(max(start_x, end_x))
                y1 = int(min(start_y, end_y))
                y2 = int(max(start_y, end_y))

                if x2 - x1 > 5 and y2 - y1 > 5:
                    # 转换回原始图片坐标
                    orig_x1 = int(x1 / scale)
                    orig_x2 = int(x2 / scale)
                    orig_y1 = int(y1 / scale)
                    orig_y2 = int(y2 / scale)
                    self.selection = (orig_x1, orig_y1, orig_x2, orig_y2)

                selection_done[0] = True

        canvas.bind("<Button-1>", on_mouse_down)
        canvas.bind("<B1-Motion>", on_mouse_move)
        canvas.bind("<ButtonRelease-1>", on_mouse_up)

        # 等待选择完成
        (
            root.wait_var(selection_done[0])
            if hasattr(root, "wait_var")
            else time.sleep(0.1)
        )

        # 恢复原始图片显示
        self._restore_canvas(canvas)

        return self.selection

    def _restore_canvas(self, canvas):
        """恢复canvas显示原始图片"""
        # 重新显示边缘图像
        display_rgb = cv2.cvtColor(self.image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(display_rgb)
        self.tk_restore = ImageTk.PhotoImage(pil_img)
        canvas.delete("all")
        canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_restore)

    def select(self):
        """创建独立选框窗口 - 使用简单方式"""
        # 获取图片尺寸
        img_h, img_w = self.image.shape[:2]

        # 限制最大尺寸
        max_w, max_h = 800, 700
        scale = min(max_w / img_w, max_h / img_h, 1.0)
        display_w = int(img_w * scale)
        display_h = int(img_h * scale)

        # 缩放图片
        if scale < 1:
            display_img = cv2.resize(self.image, (display_w, display_h))
        else:
            display_img = self.image

        # 创建选框窗口
        select_win = tk.Toplevel()
        select_win.title(self.title)
        select_win.geometry(f"{display_w}x{display_h}")
        select_win.resizable(False, False)

        # 转换图片
        display_rgb = cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(display_rgb)
        tk_img = ImageTk.PhotoImage(pil_img)

        # 创建画布
        canvas = tk.Canvas(select_win, width=display_w, height=display_h)
        canvas.pack()
        canvas.create_image(0, 0, anchor=tk.NW, image=tk_img)

        # 选框变量
        rect_id = None
        start_pos = [None, None]

        def start_draw(event):
            start_pos[0] = event.x
            start_pos[1] = event.y
            nonlocal rect_id
            rect_id = canvas.create_rectangle(
                event.x, event.y, event.x, event.y, outline="red", width=2
            )

        def move_draw(event):
            nonlocal rect_id
            if rect_id:
                canvas.coords(rect_id, start_pos[0], start_pos[1], event.x, event.y)

        def end_draw(event):
            nonlocal rect_id
            if rect_id and start_pos[0]:
                x1 = int(min(start_pos[0], event.x))
                x2 = int(max(start_pos[0], event.x))
                y1 = int(min(start_pos[1], event.y))
                y2 = int(max(start_pos[1], event.y))

                if x2 - x1 > 5 and y2 - y1 > 5:
                    # 转回原始坐标
                    self.selection = (
                        int(x1 / scale),
                        int(y1 / scale),
                        int(x2 / scale),
                        int(y2 / scale),
                    )
            select_win.destroy()

        canvas.bind("<Button-1>", start_draw)
        canvas.bind("<B1-Motion>", move_draw)
        canvas.bind("<ButtonRelease-1>", end_draw)

        # ESC取消
        def cancel(event):
            select_win.destroy()

        select_win.bind("<Escape>", cancel)

        # 等待窗口关闭
        select_win.grab_set()
        select_win.wait_window()

        return self.selection


class SlayTheSpireMapPainter:
    def __init__(self, root):
        self.root = root
        self.root.title("杀戮尖塔2 地图绘制工具 v2.0")
        self.root.geometry("1200x900")
        self.root.configure(bg="#1a1a2e")

        # 样式配置
        self.bg_color = "#1a1a2e"
        self.fg_color = "#eaeaea"
        self.accent_color = "#e94560"
        self.secondary_color = "#16213e"

        # 变量
        self.original_image = None
        self.edge_image = None
        self.tk_original = None
        self.tk_edge = None

        self.image_region = None  # (x1, y1, x2, y2)
        self.game_region = None  # (x1, y1, x2, y2)

        self.is_drawing = False
        self.draw_thread = None

        # 右键监听器
        self.mouse_listener = None
        self._right_click_received = False

        # 断点续绘状态
        self.saved_paths = None
        self.current_path_index = 0
        self.current_point_index = 0
        self.is_resume_mode = False

        # 边缘检测参数
        self.low_threshold = 50
        self.high_threshold = 150

        # 绘制速度 (越小越快)
        self.draw_speed = 0.001

        self.setup_ui()
        self.log("程序已启动，请导入图片")

    def setup_ui(self):
        # 主框架
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 左侧：图像显示区域
        left_frame = tk.Frame(main_frame, bg=self.bg_color)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 标题
        title_label = tk.Label(
            left_frame,
            text="⚔️ 杀戮尖塔2 地图绘制工具",
            font=("Microsoft YaHei", 20, "bold"),
            bg=self.bg_color,
            fg=self.accent_color,
        )
        title_label.pack(pady=10)

        # 按钮框架（移到左侧上方）
        btn_frame = tk.Frame(left_frame, bg=self.bg_color)
        btn_frame.pack(pady=5)

        btn_style = {
            "bg": self.secondary_color,
            "fg": self.fg_color,
            "font": ("Microsoft YaHei", 10),
            "relief": "flat",
            "padx": 15,
            "pady": 8,
            "cursor": "hand2",
        }

        self.btn_load = tk.Button(
            btn_frame, text="📂 选择图片", command=self.load_image, **btn_style
        )
        self.btn_load.pack(side=tk.TOP, padx=5, pady=2, fill=tk.X)

        self.btn_preview = tk.Button(
            btn_frame,
            text="🔄 刷新预览",
            command=self.process_edge,
            state=tk.DISABLED,
            **btn_style,
        )
        self.btn_preview.pack(side=tk.TOP, padx=5, pady=2, fill=tk.X)

        self.btn_select_image = tk.Button(
            btn_frame,
            text="📐 框选图像区域",
            command=self.select_image_region,
            state=tk.DISABLED,
            **btn_style,
        )
        self.btn_select_image.pack(side=tk.TOP, padx=5, pady=2, fill=tk.X)

        self.btn_select_game = tk.Button(
            btn_frame,
            text="🎮 框选绘制区域",
            command=self.select_game_region,
            state=tk.DISABLED,
            **btn_style,
        )
        self.btn_select_game.pack(side=tk.TOP, padx=5, pady=2, fill=tk.X)

        # 图像显示区域
        img_frame = tk.Frame(left_frame, bg=self.bg_color)
        img_frame.pack(pady=10)

        # 原始图像
        self.org_frame = tk.LabelFrame(
            img_frame,
            text="原始图像",
            bg=self.secondary_color,
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
        )
        self.org_frame.grid(row=0, column=0, padx=10)
        # 增大显示区域以适应大图片
        self.lbl_original = tk.Label(self.org_frame, bg="#0f0f23", width=50, height=25)
        self.lbl_original.pack(padx=5, pady=5)

        # 箭头
        arrow_label = tk.Label(
            img_frame,
            text="➜",
            font=("Arial", 28),
            bg=self.bg_color,
            fg=self.accent_color,
        )
        arrow_label.grid(row=0, column=1, padx=10)

        # 边缘检测图像
        self.edge_frame = tk.LabelFrame(
            img_frame,
            text="边缘检测效果 (框=选中区域)",
            bg=self.secondary_color,
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
        )
        self.edge_frame.grid(row=0, column=2, padx=10)
        self.lbl_edge = tk.Label(self.edge_frame, bg="#0f0f23", width=50, height=25)
        self.lbl_edge.pack(padx=5, pady=5)

        # 右侧：参数和控制区域
        right_frame = tk.Frame(main_frame, bg=self.bg_color, width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))

        # 参数调节区域
        param_frame = tk.LabelFrame(
            right_frame,
            text="参数调节",
            bg=self.secondary_color,
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
        )
        param_frame.pack(pady=10, fill=tk.X)

        # 边缘阈值
        tk.Label(
            param_frame, text="边缘检测阈值:", bg=self.secondary_color, fg=self.fg_color
        ).grid(row=0, column=0, padx=10, pady=8, sticky=tk.W)

        self.threshold_frame = tk.Frame(param_frame, bg=self.secondary_color)
        self.threshold_frame.grid(row=0, column=1, padx=10, pady=8, sticky=tk.W)

        tk.Label(
            self.threshold_frame, text="低:", bg=self.secondary_color, fg="#888"
        ).pack(side=tk.LEFT)
        self.scale_low = tk.Scale(
            self.threshold_frame,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            bg=self.secondary_color,
            fg=self.fg_color,
            highlightthickness=0,
            length=100,
            resolution=1,
        )
        self.scale_low.set(50)
        self.scale_low.pack(side=tk.LEFT, padx=5)

        tk.Label(
            self.threshold_frame, text="高:", bg=self.secondary_color, fg="#888"
        ).pack(side=tk.LEFT, padx=(15, 0))
        self.scale_high = tk.Scale(
            self.threshold_frame,
            from_=0,
            to=255,
            orient=tk.HORIZONTAL,
            bg=self.secondary_color,
            fg=self.fg_color,
            highlightthickness=0,
            length=100,
            resolution=1,
        )
        self.scale_high.set(150)
        self.scale_high.pack(side=tk.LEFT, padx=5)

        # 绘制速度
        tk.Label(
            param_frame, text="绘制速度:", bg=self.secondary_color, fg=self.fg_color
        ).grid(row=1, column=0, padx=10, pady=8, sticky=tk.W)

        self.speed_frame = tk.Frame(param_frame, bg=self.secondary_color)
        self.speed_frame.grid(row=1, column=1, padx=10, pady=8, sticky=tk.W)

        tk.Label(self.speed_frame, text="慢", bg=self.secondary_color, fg="#888").pack(
            side=tk.LEFT
        )
        self.scale_speed = tk.Scale(
            self.speed_frame,
            from_=1,
            to=10,
            orient=tk.HORIZONTAL,
            bg=self.secondary_color,
            fg=self.fg_color,
            highlightthickness=0,
            length=150,
        )
        self.scale_speed.set(5)  # 降低默认速度以提高精度
        self.scale_speed.pack(side=tk.LEFT, padx=5)
        tk.Label(self.speed_frame, text="快", bg=self.secondary_color, fg="#888").pack(
            side=tk.LEFT
        )

        # 状态显示区域
        status_frame = tk.LabelFrame(
            right_frame,
            text="操作说明",
            bg=self.secondary_color,
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
        )
        status_frame.pack(pady=10, fill=tk.X)

        self.lbl_instruction = tk.Label(
            status_frame,
            text="1. 点击「选择图片」加载图片 (线稿效果最佳)\n"
            "2. 调整边缘阈值，或直接点击「框选图像区域」\n"
            "3. 框选图像后，点击「框选绘制区域」在游戏窗口选择\n"
            "4. 点击「开始绘制」后切换到游戏窗口等待自动绘制",
            bg=self.secondary_color,
            fg="#aaa",
            font=("Microsoft YaHei", 9),
            justify=tk.LEFT,
            anchor=tk.W,
        )
        self.lbl_instruction.pack(padx=10, pady=10, fill=tk.X)

        # 绘制预览区域
        preview_frame = tk.LabelFrame(
            right_frame,
            text="绘制预览",
            bg=self.secondary_color,
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
        )
        preview_frame.pack(pady=10, fill=tk.X)

        self.lbl_preview = tk.Label(
            preview_frame,
            bg="#0f0f23",
            text="选择区域后显示预览",
            fg="#888",
            font=("Microsoft YaHei", 9),
        )
        self.lbl_preview.pack(padx=5, pady=5, fill=tk.BOTH, expand=True)

        # 控制按钮
        ctrl_frame = tk.Frame(right_frame, bg=self.bg_color)
        ctrl_frame.pack(pady=10)

        self.btn_start = tk.Button(
            ctrl_frame,
            text="🖌️ 开始绘制",
            command=self.start_drawing,
            bg=self.accent_color,
            fg="white",
            font=("Microsoft YaHei", 12, "bold"),
            relief="flat",
            padx=25,
            pady=12,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.btn_start.pack(pady=5, fill=tk.X)

        self.btn_resume = tk.Button(
            ctrl_frame,
            text="▶️ 继续绘画",
            command=self.resume_drawing,
            bg="#28a745",
            fg="white",
            font=("Microsoft YaHei", 11),
            relief="flat",
            padx=20,
            pady=10,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.btn_resume.pack(pady=5, fill=tk.X)

        self.btn_stop = tk.Button(
            ctrl_frame,
            text="⏹ 停止绘制",
            command=self.stop_drawing,
            bg="#d63031",
            fg="white",
            font=("Microsoft YaHei", 11),
            relief="flat",
            padx=20,
            pady=10,
            state=tk.DISABLED,
            cursor="hand2",
        )
        self.btn_stop.pack(pady=5, fill=tk.X)

        self.btn_exit = tk.Button(
            ctrl_frame,
            text="❌ 退出",
            command=self.on_closing,
            bg="#333",
            fg="white",
            font=("Microsoft YaHei", 11),
            relief="flat",
            padx=20,
            pady=10,
            cursor="hand2",
        )
        self.btn_exit.pack(pady=5, fill=tk.X)

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("等待操作...")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#0f3460",
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
            anchor=tk.W,
            padx=10,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))

        # 状态栏
        self.status_var = tk.StringVar()
        self.status_var.set("等待操作...")
        self.status_bar = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#0f3460",
            fg=self.fg_color,
            font=("Microsoft YaHei", 10),
            anchor=tk.W,
            padx=10,
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 8))

    def log(self, message):
        self.status_var.set(message)
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def load_image(self):
        file_path = filedialog.askopenfilename(
            title="选择图片",
            filetypes=[
                ("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif"),
                ("所有文件", "*.*"),
            ],
        )
        if file_path:
            try:
                # 使用PIL读取图片
                pil_img = Image.open(file_path)
                # 转换为OpenCV格式
                self.original_image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

                # 重置断点续绘状态
                self.saved_paths = None
                self.current_path_index = 0
                self.current_point_index = 0
                self.is_resume_mode = False
                self.btn_resume.config(state=tk.DISABLED)

                # 重置预览
                self.lbl_preview.config(image="", text="选择区域后显示预览")

                # 不进行缩放，保留原始尺寸，只在显示时自适应缩放
                # 这样可以保证图片不会变小

                # 显示原始图像
                self.display_image(self.original_image, self.lbl_original)

                # 自动进行边缘检测
                self.process_edge()

                # 根据图片大小自动调整窗口宽度
                self._adjust_window_size()

                self.btn_preview.config(state=tk.NORMAL)
                self.btn_select_image.config(state=tk.NORMAL)

                h, w = self.original_image.shape[:2]
                self.log(f"图片已加载: {file_path} (尺寸: {w}x{h})")
                self.log("调整好阈值后，点击「框选图像区域」")
            except Exception as e:
                messagebox.showerror("错误", f"无法加载图片: {e}")
                import traceback

                traceback.print_exc()

    def display_image(self, cv_image, label):
        # 转换BGR到RGB
        cv_image = cv2.cvtColor(cv_image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(cv_image)

        # 获取原始图片尺寸
        orig_w, orig_h = pil_img.size

        # 强制缩放到合适显示大小（保持比例）
        max_display_w = 400  # 减小显示宽度
        max_display_h = 300  # 减小显示高度

        # 计算缩放比例
        scale = min(max_display_w / orig_w, max_display_h / orig_h)
        if scale < 1 or orig_w < max_display_w or orig_h < max_display_h:
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        else:
            new_w = orig_w
            new_h = orig_h

        # 根据不同的标签保存不同的PhotoImage对象
        if label == self.lbl_original:
            self.tk_original = ImageTk.PhotoImage(pil_img)
            label.config(image=self.tk_original, width=new_w, height=new_h)
        else:
            self.tk_edge = ImageTk.PhotoImage(pil_img)
            label.config(image=self.tk_edge, width=new_w, height=new_h)

    def process_edge(self):
        if self.original_image is None:
            return

        # 转换为灰度图
        gray = cv2.cvtColor(self.original_image, cv2.COLOR_BGR2GRAY)

        # 高斯模糊降噪
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Canny边缘检测
        self.low_threshold = self.scale_low.get()
        self.high_threshold = self.scale_high.get()
        edges = cv2.Canny(blurred, self.low_threshold, self.high_threshold)

        # 膨胀处理使线条更连续
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

        # 反转颜色（白底黑线）
        self.edge_image = 255 - edges

        # 显示边缘图像
        self.display_image(self.edge_image, self.lbl_edge)

    def generate_preview(self):
        """生成绘制预览 - 显示实际绘制路径"""
        if self.image_region is None or self.game_region is None:
            return

        try:
            # 获取要绘制的图像区域
            x1, y1, x2, y2 = self.image_region
            img_region = self.edge_image[y1:y2, x1:x2]

            # 获取游戏绘制区域
            gx1, gy1, gx2, gy2 = self.game_region
            gw = gx2 - gx1
            gh = gy2 - gy1

            # 缩放图像到游戏区域大小
            scaled = cv2.resize(img_region, (gw, gh))

            # 提取绘制路径（与实际绘制相同的逻辑）
            paths = self._extract_contours_as_paths(
                scaled, 0, 0
            )  # 相对于预览区域的坐标

            if not paths:
                self.lbl_preview.config(image="", text="无绘制路径")
                return

            # 合并短路径
            paths = self._merge_short_paths(paths)

            # 创建预览画布
            max_preview_w = 250
            max_preview_h = 150

            # 计算缩放比例以适应预览区域
            scale_x = max_preview_w / gw
            scale_y = max_preview_h / gh
            scale = min(scale_x, scale_y)

            preview_w = int(gw * scale)
            preview_h = int(gh * scale)

            # 创建白色背景的预览图像
            preview_img = np.full(
                (preview_h, preview_w, 3), 255, dtype=np.uint8
            )  # 白色背景

            # 在预览图像上绘制路径
            for path in paths:
                if len(path) < 2:
                    continue

                # 缩放路径坐标到预览大小
                scaled_path = []
                for px, py in path:
                    scaled_x = int(px * scale)
                    scaled_y = int(py * scale)
                    scaled_path.append((scaled_x, scaled_y))

                # 绘制路径线条 - 蓝色
                for i in range(len(scaled_path) - 1):
                    pt1 = scaled_path[i]
                    pt2 = scaled_path[i + 1]
                    cv2.line(
                        preview_img, pt1, pt2, (255, 0, 0), 1
                    )  # 蓝色线条 (BGR格式)

                # 在路径起点画一个小圆圈 - 红色
                if scaled_path:
                    start_x, start_y = scaled_path[0]
                    cv2.circle(
                        preview_img, (start_x, start_y), 2, (0, 0, 255), -1
                    )  # 红色起点

            # 转换为PIL图像
            preview_rgb = cv2.cvtColor(preview_img, cv2.COLOR_BGR2RGB)
            pil_preview = Image.fromarray(preview_rgb)

            self.tk_preview = ImageTk.PhotoImage(pil_preview)
            self.lbl_preview.config(image=self.tk_preview, text="")

            total_paths = len(paths)
            total_points = sum(len(p) for p in paths)
            self.log(f"预览已生成: {total_paths}条路径, {total_points}个点")

        except Exception as e:
            self.log(f"生成预览失败: {e}")
            import traceback

            traceback.print_exc()

    def select_image_region(self):
        if self.edge_image is None:
            messagebox.showwarning("警告", "请先加载图片")
            return

        self.log("正在打开图像选框，请用鼠标框选要绘制的区域...")

        # 隐藏主窗口
        self.root.withdraw()

        # 使用tkinter选择区域
        selector = RegionSelector(
            "框选图像区域 - 请拖动鼠标选择 (按ESC取消)", self.edge_image
        )
        region = selector.select()

        # 恢复主窗口并更新
        self.root.update()
        self.root.deiconify()
        self.root.focus_force()

        if region:
            self.image_region = region

            # 在显示的图像上画框
            x1, y1, x2, y2 = region
            display_img = self.edge_image.copy()
            cv2.rectangle(display_img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            self.display_image(display_img, self.lbl_edge)

            self.log(f"图像区域已选择: 区域大小 {x2-x1}x{y2-y1}")
            self.btn_select_game.config(state=tk.NORMAL)
            self.log("请点击「框选绘制区域」")
        else:
            self.log("未选择区域")

    def select_game_region(self):
        if self.image_region is None:
            messagebox.showwarning("警告", "请先选择图像区域")
            return

        self.log("3秒后开始框选游戏区域，请切换到游戏窗口...")

        # 隐藏主窗口
        self.root.withdraw()
        self.root.update()
        time.sleep(0.5)

        # 截取屏幕
        screen = pyautogui.screenshot()
        screen_np = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)

        # 创建半透明遮罩
        overlay = screen_np.copy()
        cv2.putText(
            overlay,
            "点击左上角，然后拖动到右下角",
            (50, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            3,
        )

        self.log("点击游戏窗口左上角...")

        # 隐藏主窗口再选框
        self.root.withdraw()

        selector = RegionSelector("框选游戏绘制区域 (按ESC取消)", overlay)
        region = selector.select()

        # 恢复主窗口
        self.root.update()
        self.root.deiconify()
        self.root.focus_force()

        if region:
            self.game_region = region
            gx1, gy1, gx2, gy2 = region
            self.log(f"游戏区域已选择: 区域大小 {gx2-gx1}x{gy2-gy1}")
            self.btn_start.config(state=tk.NORMAL)

            # 生成绘制预览
            self.generate_preview()

            self.log("设置完成，点击「开始绘制」")
        else:
            self.log("未选择区域")

    def start_drawing(self):
        if self.image_region is None or self.game_region is None:
            messagebox.showwarning("警告", "请先选择图像区域和游戏区域")
            return

        # 更新速度参数（最大速度翻倍 - 更快）
        self.draw_speed = 0.001 - self.scale_speed.get()* 0.0001

        self.is_drawing = True
        self._right_click_received = False
        self.is_resume_mode = False  # 标记为新开始绘制
        self.btn_start.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_load.config(state=tk.DISABLED)
        self.btn_select_image.config(state=tk.DISABLED)
        self.btn_select_game.config(state=tk.DISABLED)

        self.log("5秒后开始绘制，请确保游戏窗口可见...")
        self.log("绘制时按鼠标右键可随时停止")

        # 启动全局鼠标监听器来捕获右键（按下和释放都监听）
        def on_click(x, y, button, pressed):
            # 右键按下或释放时都停止
            if button == mouse.Button.right:
                self._right_click_received = True
                self.is_drawing = False
                # 立即释放鼠标左键，避免继续绘制
                try:
                    pyautogui.mouseUp(button="left")
                except:
                    pass
                # 停止监听器
                return False

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

        # 隐藏窗口
        self.root.withdraw()

        # 延迟开始
        def delayed_start():
            time.sleep(5)
            self.root.after(0, self._do_drawing)

        self.draw_thread = threading.Thread(target=delayed_start, daemon=True)
        self.draw_thread.start()

    def resume_drawing(self):
        if self.saved_paths is None:
            messagebox.showwarning("警告", "没有保存的绘制状态，请先开始绘制")
            return

        # 更新速度参数
        self.draw_speed = 0.001 - self.scale_speed.get()* 0.0001

        self.is_drawing = True
        self._right_click_received = False
        self.is_resume_mode = True  # 标记为继续绘制模式
        self.btn_start.config(state=tk.DISABLED)
        self.btn_resume.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.btn_load.config(state=tk.DISABLED)
        self.btn_select_image.config(state=tk.DISABLED)
        self.btn_select_game.config(state=tk.DISABLED)

        self.log(
            f"5秒后继续绘制，从第{self.current_path_index}条路径的第{self.current_point_index}个点开始..."
        )
        self.log("绘制时按鼠标右键可随时停止")

        # 启动全局鼠标监听器来捕获右键
        def on_click(x, y, button, pressed):
            if button == mouse.Button.right:
                self._right_click_received = True
                self.is_drawing = False
                return False

        self.mouse_listener = mouse.Listener(on_click=on_click)
        self.mouse_listener.start()

        # 隐藏窗口
        self.root.withdraw()

        # 延迟开始
        def delayed_resume():
            time.sleep(5)
            self.root.after(0, self._do_drawing)

        self.draw_thread = threading.Thread(target=delayed_resume, daemon=True)
        self.draw_thread.start()

    def _do_drawing(self):
        try:
            # 获取要绘制的图像区域
            x1, y1, x2, y2 = self.image_region
            img_region = self.edge_image[y1:y2, x1:x2]

            # 获取游戏绘制区域
            gx1, gy1, gx2, gy2 = self.game_region
            gw = gx2 - gx1
            gh = gy2 - gy1

            # 图像区域大小
            iw = x2 - x1
            ih = y2 - y1

            # 缩放图像到游戏区域大小
            scaled = cv2.resize(img_region, (gw, gh))

            # 如果是新开始绘制，重新生成路径
            if not self.is_resume_mode:
                # 使用改进的轮廓提取生成高质量路径
                paths = self._extract_contours_as_paths(scaled, gx1, gy1)

                if not paths:
                    self.log("没有检测到轮廓线条")
                    self._finish_drawing()
                    return

                self.log(f"准备绘制 {len(paths)} 条高质量轮廓路径，使用曲线绘制模式...")

                # 合并短路径，减少鼠标抬起次数
                paths = self._merge_short_paths(paths)

                self.log(f"合并后 {len(paths)} 条路径，开始绘制...")

                # 保存路径供续绘使用
                self.saved_paths = paths
                self.current_path_index = 0
                self.current_point_index = 0
            else:
                # 继续绘制模式，使用保存的路径
                paths = self.saved_paths
                self.log(
                    f"继续绘制 {len(paths)} 条路径，从第{self.current_path_index}条路径开始..."
                )

            # 绘制所有路径
            total_points = sum(len(p) for p in paths)
            drawn = 0

            # 从保存的路径索引开始
            start_path_idx = self.current_path_index
            start_point_idx = self.current_point_index

            for path_idx in range(start_path_idx, len(paths)):
                path = paths[path_idx]

                # 检查是否收到右键停止信号
                if not self.is_drawing or self._right_click_received:
                    self.is_drawing = False
                    # 保存当前状态
                    self.current_path_index = path_idx
                    self.current_point_index = (
                        0 if path_idx > start_path_idx else start_point_idx
                    )
                    break

                if len(path) < 1:  # 修改：允许单个点绘制
                    continue

                # 确定路径内开始绘制的点索引
                point_start = start_point_idx if path_idx == start_path_idx else 0

                # 移动到起始点
                pyautogui.moveTo(path[point_start][0], path[point_start][1])
                time.sleep(0.02)

                # 按下鼠标开始绘制
                pyautogui.mouseDown(button="left")

                if len(path) == 1:
                    # 单个点：按下后立即释放
                    time.sleep(0.01)
                    pyautogui.mouseUp(button="left")
                    drawn += 1
                    continue

                # 沿着路径移动
                for point_idx in range(point_start + 1, len(path)):
                    px, py = path[point_idx]
                    prev_px, prev_py = path[point_idx - 1]

                    # 检查停止信号
                    if not self.is_drawing or self._right_click_received:
                        self.is_drawing = False
                        # 保存当前状态
                        self.current_path_index = path_idx
                        self.current_point_index = point_idx
                        break

                    # 计算两点之间的距离
                    distance = ((px - prev_px) ** 2 + (py - prev_py) ** 2) ** 0.5

                    if distance > 2:  # 如果距离大于2像素，插入中间点
                        # 计算需要插入的中间点数量
                        num_interpolation = max(1, int(distance / 2))

                        for i in range(1, num_interpolation + 1):
                            # 线性插值
                            ratio = i / (num_interpolation + 1)
                            interp_x = int(prev_px + (px - prev_px) * ratio)
                            interp_y = int(prev_py + (py - prev_py) * ratio)

                            pyautogui.moveTo(interp_x, interp_y)
                            time.sleep(self.draw_speed * 0.5)  # 中间点使用更短的延迟
                            drawn += 1

                    # 移动到目标点
                    pyautogui.moveTo(px, py)
                    time.sleep(self.draw_speed)
                    drawn += 1

                # 释放鼠标
                pyautogui.mouseUp(button="left")

                # 每条路径之间稍微停顿
                if self.is_drawing and path_idx < len(paths) - 1:
                    time.sleep(0.01)

            if self.is_drawing:
                self.log(f"绘制完成! 共绘制 {drawn} 个点")
                # 绘制完成，重置状态
                self.saved_paths = None
                self.current_path_index = 0
                self.current_point_index = 0
            else:
                self.log(f"绘制已停止，已绘制 {drawn} 个点")

        except Exception as e:
            self.log(f"绘制出错: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self._finish_drawing()

    def _organize_paths(self, points, width, height):
        """将散点组织成连续的路径"""
        if not points:
            return []

        # 转换为集合方便查找
        point_set = set(points)

        paths = []
        used = set()

        # 按行组织路径
        for y in range(height):
            row_points = [
                (x, y)
                for x in range(width)
                if (x, y) in point_set and (x, y) not in used
            ]
            if not row_points:
                continue

            # 将这一行的连续点连成路径
            row_points.sort(key=lambda p: p[0])

            current_path = []
            for i, pt in enumerate(row_points):
                if i == 0:
                    current_path.append(pt)
                else:
                    # 检查是否与上一个点相邻
                    prev = current_path[-1]
                    if abs(pt[0] - prev[0]) <= 3:  # 允许小间隙
                        current_path.append(pt)
                    else:
                        # 间隙太大，保存当前路径，开始新路径
                        if len(current_path) >= 1:
                            paths.append(current_path)
                        current_path = [pt]
                used.add(pt)

            if len(current_path) >= 1:
                paths.append(current_path)

        # 移除太短的路径
        paths = [p for p in paths if len(p) >= 1]

        return paths

    def _adjust_window_size(self):
        """根据图片大小自动调整窗口宽度"""
        if self.original_image is None:
            return

        img_h, img_w = self.original_image.shape[:2]

        # 计算需要的显示宽度（左侧图片 + 右侧控制面板）
        # 左侧最大显示宽度400，右侧控制面板宽度约300
        min_window_width = 750  # 最小窗口宽度

        # 如果图片很宽，需要增加窗口宽度
        required_width = min(img_w, 400) + 350  # 图片显示宽度 + 控制面板 + 边距
        new_width = max(min_window_width, required_width)

        # 限制最大宽度
        new_width = min(new_width, 1400)

        # 获取当前窗口高度
        current_height = self.root.winfo_height()
        if current_height < 700:  # 最小高度
            current_height = 700

        # 调整窗口大小
        self.root.geometry(f"{new_width}x{current_height}")

        self.log(f"窗口宽度已调整为 {new_width} 像素")

    def _merge_short_paths(self, paths):
        """合并短路径，减少鼠标抬起次数"""
        if not paths:
            return []

        merged = []
        current_path = paths[0][:]  # 复制第一条路径

        for path in paths[1:]:
            # 如果当前路径不为空，且下一条路径的起点靠近当前路径的终点
            if current_path and path:
                last_point = current_path[-1]
                first_point = path[0]
                distance = (
                    (last_point[0] - first_point[0]) ** 2
                    + (last_point[1] - first_point[1]) ** 2
                ) ** 0.5

                if distance < 20:  # 距离阈值
                    # 合并路径
                    current_path.extend(path)
                else:
                    # 保存当前路径，开始新路径
                    if len(current_path) >= 2:
                        merged.append(current_path)
                    current_path = path[:]
            else:
                if len(current_path) >= 2:
                    merged.append(current_path)
                current_path = path[:]

        # 添加最后一条路径
        if len(current_path) >= 2:
            merged.append(current_path)

        return merged

    def _sort_points_into_paths(self, points):
        """将散点按距离排序成连续路径"""
        if not points:
            return []

        paths = []
        remaining = set(points)

        while remaining:
            # 开始新路径
            current_path = []
            current_point = remaining.pop()
            current_path.append(current_point)

            while remaining:
                # 找到最近的点
                nearest_point = None
                min_distance = float("inf")

                for point in remaining:
                    distance = (
                        (point[0] - current_point[0]) ** 2
                        + (point[1] - current_point[1]) ** 2
                    ) ** 0.5
                    if distance < min_distance:
                        min_distance = distance
                        nearest_point = point

                # 如果最近点距离太远（>10像素），结束当前路径
                if min_distance > 10:
                    break

                current_point = nearest_point
                current_path.append(current_point)
                remaining.remove(current_point)

            if len(current_path) >= 1:
                paths.append(current_path)

        return paths

    def _extract_contours_as_paths(self, image, offset_x, offset_y):
        """使用精细轮廓提取生成高质量绘制路径"""
        # 图像已经是二值化的边缘图像（黑线白底），需要反转以便轮廓提取
        binary = cv2.bitwise_not(image)  # 反转：白底黑线 -> 黑底白线

        # 使用树形结构获取所有轮廓层次，包括内部线条
        contours, hierarchy = cv2.findContours(
            binary, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
        )

        paths = []
        for contour in contours:
            # 过滤掉太小的轮廓，但保留更多细节
            if cv2.contourArea(contour) < 0.5:  # 降低阈值以保留更多细节
                continue

            # 不进行多边形近似，保留所有原始轮廓点
            # 转换为游戏坐标
            path = []
            for point in contour:
                x, y = point[0]
                path.append((offset_x + x, offset_y + y))

            # 对路径进行平滑处理，插入中间点使线条更连续
            if len(path) >= 2:
                smoothed_path = []
                for i in range(len(path)):
                    smoothed_path.append(path[i])
                    # 在相邻点之间插入中间点
                    if i < len(path) - 1:
                        next_point = path[i + 1]
                        current_point = path[i]

                        # 计算距离
                        dx = next_point[0] - current_point[0]
                        dy = next_point[1] - current_point[1]
                        distance = (dx**2 + dy**2) ** 0.5

                        # 如果距离大于3像素，插入中间点
                        if distance > 3:
                            num_points = max(1, int(distance / 3))
                            for j in range(1, num_points + 1):
                                ratio = j / (num_points + 1)
                                mid_x = int(current_point[0] + dx * ratio)
                                mid_y = int(current_point[1] + dy * ratio)
                                smoothed_path.append((mid_x, mid_y))

                paths.append(smoothed_path)

        return paths

    def _finish_drawing(self):
        self.is_drawing = False
        # 确保鼠标左键被释放
        try:
            pyautogui.mouseUp(button="left")
        except:
            pass
        # 停止鼠标监听器
        if self.mouse_listener:
            try:
                self.mouse_listener.stop()
            except:
                pass
            self.mouse_listener = None

        # 记录停止原因
        was_stopped_by_user = self._right_click_received
        self._right_click_received = False

        self.root.deiconify()
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.btn_load.config(state=tk.NORMAL)

        if self.image_region:
            self.btn_select_image.config(state=tk.NORMAL)
        if self.game_region:
            self.btn_select_game.config(state=tk.NORMAL)

        # 如果有保存的绘制状态，启用继续绘画按钮
        if self.saved_paths is not None and was_stopped_by_user:
            self.btn_resume.config(state=tk.NORMAL)
            self.log("绘制已暂停，可以点击「继续绘画」从断点恢复")
        else:
            self.btn_resume.config(state=tk.DISABLED)
            if was_stopped_by_user:
                self.log("用户按下右键，绘制已停止")

    def _on_right_click(self):
        """鼠标右键点击停止绘制（窗口可见时使用）"""
        if self.is_drawing:
            self._right_click_received = True
            self.is_drawing = False
            try:
                pyautogui.mouseUp(button="left")
            except:
                pass
            self.log("用户中断，绘制已停止")
            # 延迟一点后恢复界面，避免线程还在运行
            self.root.after(100, self._finish_drawing)

    def stop_drawing(self):
        self.is_drawing = False
        try:
            pyautogui.mouseUp(button="left")
        except:
            pass
        self.log("正在停止绘制...")
        # 手动停止时不清除保存的状态，允许继续绘画

    def on_closing(self):
        self.is_drawing = False
        try:
            pyautogui.mouseUp(button="left")
        except:
            pass
        self.root.destroy()


def main():
    root = tk.Tk()

    # 尝试加载样式
    try:
        style = ttk.Style()
        style.theme_use("clam")
    except:
        pass

    app = SlayTheSpireMapPainter(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
