import json
import os
import shutil
import glob
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk, filedialog
from tkinter import font as tkfont
from datetime import datetime, timedelta
import calendar
import csv
import winsound

CONFIG_FILE = "config.json"
DEFAULT_DATA_FILE = "reading_tracker.json"
BACKUP_DIR_NAME = "backups"
MAX_BACKUPS = 5
CURRENT_VERSION = 6

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind('<Enter>', self.show_tip)
        widget.bind('<Leave>', self.hide_tip)

    def show_tip(self, event=None):
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify=tk.LEFT,
                         background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                         font=("tahoma", "8", "normal"))
        label.pack()

    def hide_tip(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

class ReadingTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Theo dõi đọc sách theo phiên v7.0")
        self.root.geometry("900x750")
        self.root.resizable(True, True)

        self.books = []
        self.current_book_index = -1
        self.display_mode = "sessions"
        self.timer_display_mode = "bar"
        self.timer_running = False
        self.timer_paused = False
        self.timer_seconds = 0
        self.target_seconds = 30 * 60  # Mặc định 30 phút
        self.after_id = None
        self.bold_mode = False

        self._current_target = self.target_seconds

        # Đọc cấu hình để lấy đường dẫn file dữ liệu
        self.data_file = self.load_config()

        # Tạo thư mục backup trong cùng thư mục với file dữ liệu
        data_dir = os.path.dirname(self.data_file) or "."
        self.backup_dir = os.path.join(data_dir, BACKUP_DIR_NAME)
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)

        self.load_data()

        self.home_frame = ttk.Frame(self.root)
        self.detail_frame = ttk.Frame(self.root)

        self.create_home_widgets()
        self.create_detail_widgets()

        self.show_home()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.root.bind("<Control-s>", self.save_notes_shortcut)
        self.root.bind("<Control-Down>", self.focus_notes_shortcut)
        self.root.bind("<Tab>", self.tab_shortcut)

    # -------------------- CẤU HÌNH --------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                data_file = config.get("data_file", DEFAULT_DATA_FILE)
                if not os.path.exists(os.path.dirname(data_file)) and os.path.dirname(data_file):
                    return DEFAULT_DATA_FILE
                return data_file
            except:
                return DEFAULT_DATA_FILE
        else:
            return DEFAULT_DATA_FILE

    def save_config(self):
        try:
            config = {"data_file": self.data_file}
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu cấu hình: {e}")

    # -------------------- BACKUP & RESTORE --------------------
    def create_backup(self):
        if not os.path.exists(self.data_file):
            return
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"reading_tracker_backup_{timestamp}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        try:
            shutil.copy2(self.data_file, backup_path)
            self.cleanup_old_backups()
        except Exception as e:
            print(f"Lỗi khi tạo backup: {e}")

    def cleanup_old_backups(self):
        backups = glob.glob(os.path.join(self.backup_dir, "reading_tracker_backup_*.json"))
        if len(backups) <= MAX_BACKUPS:
            return
        backups.sort(key=os.path.getctime)
        for old_file in backups[:-MAX_BACKUPS]:
            try:
                os.remove(old_file)
            except:
                pass

    def find_latest_backup(self):
        backups = glob.glob(os.path.join(self.backup_dir, "reading_tracker_backup_*.json"))
        if not backups:
            return None
        backups.sort(key=os.path.getctime, reverse=True)
        return backups[0]

    def restore_from_backup(self, backup_path):
        try:
            with open(backup_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể khôi phục: {e}")
            return False

    # -------------------- DỮ LIỆU & CACHE --------------------
    def load_data(self):
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"books": [], "settings": {}, "schema_version": CURRENT_VERSION}
        except Exception as e:
            answer = messagebox.askyesno(
                "Lỗi dữ liệu",
                f"File dữ liệu bị lỗi: {e}\nBạn có muốn khôi phục từ bản sao lưu gần nhất không?"
            )
            if answer:
                latest = self.find_latest_backup()
                if latest and self.restore_from_backup(latest):
                    with open(self.data_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    messagebox.showwarning("Không thể khôi phục", "Sẽ tạo dữ liệu mới.")
                    data = {"books": [], "settings": {}, "schema_version": CURRENT_VERSION}
            else:
                data = {"books": [], "settings": {}, "schema_version": CURRENT_VERSION}

        version = data.get("schema_version", 1)
        self.books = data.get("books", [])

        for book in self.books:
            if "notes" not in book:
                book["notes"] = ""
            if "target_seconds" not in book:
                book["target_seconds"] = 0
            if "author" not in book:
                book["author"] = ""

            new_sessions = []
            for s in book.get("sessions", []):
                if isinstance(s, (int, float)):
                    new_sessions.append({
                        "duration": int(s),
                        "timestamp": None
                    })
                elif isinstance(s, dict) and "duration" in s:
                    new_sessions.append(s)
                else:
                    print(f"Bỏ qua session lỗi trong '{book['name']}': {s}")
            book["sessions"] = new_sessions

            self._update_book_cache(book)

        settings = data.get("settings", {})
        default_seconds = settings.get("default_session_seconds", 30 * 60)
        self.target_seconds = default_seconds
        self._current_target = self.target_seconds

        if version < CURRENT_VERSION:
            self.save_data(force_version=CURRENT_VERSION)

    def _update_book_cache(self, book):
        total = sum(s["duration"] for s in book.get("sessions", []))
        book["_total_seconds"] = total
        book["_virtual_sessions"] = total // self.target_seconds

    def _update_all_cache(self):
        for book in self.books:
            book["_virtual_sessions"] = book["_total_seconds"] // self.target_seconds

    def save_data(self, force_version=None):
        try:
            self.create_backup()

            books_to_save = []
            for book in self.books:
                # Tạo bản copy và loại bỏ các trường cache
                book_copy = book.copy()
                book_copy.pop("_total_seconds", None)
                book_copy.pop("_virtual_sessions", None)
                books_to_save.append(book_copy)

            data = {
                "schema_version": force_version if force_version else CURRENT_VERSION,
                "books": books_to_save,
                "settings": {
                    "default_session_seconds": self.target_seconds
                }
            }
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu dữ liệu: {e}")

    def manual_backup(self):
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile=f"reading_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        if not filepath:
            return
        try:
            shutil.copy2(self.data_file, filepath)
            messagebox.showinfo("Thành công", f"Đã sao lưu vào:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể sao lưu: {e}")

    def manual_restore(self):
        filepath = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if not filepath:
            return
        if self.restore_from_backup(filepath):
            messagebox.showinfo("Thành công", "Đã khôi phục dữ liệu.")
            self.books.clear()
            self.load_data()
            self.refresh_home_books()
            if self.detail_frame.winfo_ismapped():
                self.show_home()
            else:
                self.refresh_home_books()

    # -------------------- PHÍM TẮT --------------------
    def save_notes_shortcut(self, event):
        if self.detail_frame.winfo_ismapped() and self.current_book_index >= 0:
            self.save_notes()
        return "break"

    def focus_notes_shortcut(self, event):
        if self.detail_frame.winfo_ismapped():
            self.notes_text.focus_set()
        return "break"

    def tab_shortcut(self, event):
        if self.detail_frame.winfo_ismapped() and self.current_book_index >= 0:
            self.toggle_timer_display()
        return "break"

    # -------------------- MÀN HÌNH CHÍNH (HOME) --------------------
    def create_home_widgets(self):
        header_frame = ttk.Frame(self.home_frame)
        header_frame.pack(fill=tk.X, padx=20, pady=10)

        title_label = ttk.Label(header_frame, text="Tủ sách của bạn", font=("Arial", 18, "bold"))
        title_label.pack(side=tk.LEFT)

        help_btn = ttk.Button(header_frame, text="❓ Help", command=self.show_help)
        help_btn.pack(side=tk.RIGHT, padx=5)
        ToolTip(help_btn, "Xem hướng dẫn sử dụng")

        stats_btn = ttk.Button(header_frame, text="📊 Thống kê tất cả", command=self.show_overall_statistics)
        stats_btn.pack(side=tk.RIGHT, padx=5)
        ToolTip(stats_btn, "Xem thống kê tổng hợp tất cả sách")

        settings_btn = ttk.Button(header_frame, text="⚙️ Cài đặt", command=self.open_settings_from_home)
        settings_btn.pack(side=tk.RIGHT, padx=5)
        ToolTip(settings_btn, "Cài đặt thời gian phiên, sao lưu và chọn file dữ liệu")

        add_frame = ttk.Frame(self.home_frame)
        add_frame.pack(pady=5)

        add_new_btn = ttk.Button(add_frame, text="+ Thêm sách mới", command=self.add_book_from_home)
        add_new_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(add_new_btn, "Thêm sách mới (chưa có thời gian đọc)")

        add_old_btn = ttk.Button(add_frame, text="📚 Thêm sách cũ", command=self.add_old_book)
        add_old_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(add_old_btn, "Thêm sách đã đọc trước đây, nhập thời gian đã đọc")

        self.books_container = ttk.Frame(self.home_frame)
        self.books_container.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.refresh_home_books()

    def open_settings_from_home(self):
        self.open_settings()

    def on_card_enter(self, event, card):
        card.config(bg='#e0e0e0')

    def on_card_leave(self, event, card):
        card.config(bg='#f0f0f0')

    def show_card_context_menu(self, event, index):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Sửa tên sách", command=lambda: self.edit_book_name(index))
        menu.add_command(label="Sửa tác giả", command=lambda: self.edit_book_author(index))
        menu.add_separator()
        menu.add_command(label="Xóa sách", command=lambda: self.delete_book_from_card(index))
        menu.tk_popup(event.x_root, event.y_root)

    def edit_book_name(self, index):
        book = self.books[index]
        new_name = self.prompt_for_input("Sửa tên sách", "Nhập tên mới:", book["name"])
        if new_name and new_name != book["name"]:
            for b in self.books:
                if b["name"].lower() == new_name.lower() and b != book:
                    messagebox.showwarning("Cảnh báo", "Tên sách đã tồn tại!")
                    return
            book["name"] = new_name
            self.save_data()
            self.refresh_home_books()
            if self.current_book_index == index and self.detail_frame.winfo_ismapped():
                self.book_name_label.config(text=book["name"])

    def edit_book_author(self, index):
        book = self.books[index]
        new_author = self.prompt_for_input("Sửa tác giả", "Nhập tác giả mới:", book.get("author", ""))
        if new_author is not None:
            book["author"] = new_author
            self.save_data()
            self.refresh_home_books()
            if self.current_book_index == index and self.detail_frame.winfo_ismapped():
                self.author_label.config(text=f"Tác giả: {new_author}")

    def delete_book_from_card(self, index):
        book = self.books[index]
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa sách '{book['name']}'?"):
            del self.books[index]
            self.save_data()
            self.refresh_home_books()
            if self.current_book_index == index and self.detail_frame.winfo_ismapped():
                self.show_home()
            elif self.current_book_index > index:
                self.current_book_index -= 1

    def refresh_home_books(self):
        for widget in self.books_container.winfo_children():
            widget.destroy()

        if not self.books:
            ttk.Label(self.books_container, text="Chưa có cuốn sách nào. Hãy thêm sách mới!").pack(pady=20)
            return

        row, col = 0, 0
        max_col = 3

        for idx, book in enumerate(self.books):
            card = tk.Frame(self.books_container, relief=tk.RIDGE, borderwidth=2, bg='#f0f0f0', padx=10, pady=10)
            card.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

            card.bind("<Enter>", lambda e, c=card: self.on_card_enter(e, c))
            card.bind("<Leave>", lambda e, c=card: self.on_card_leave(e, c))
            card.bind("<Button-1>", lambda e, i=idx: self.show_detail(i))
            card.bind("<Button-3>", lambda e, i=idx: self.show_card_context_menu(e, i))
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, i=idx: self.show_detail(i))
                child.bind("<Button-3>", lambda e, i=idx: self.show_card_context_menu(e, i))

            title_frame = tk.Frame(card, bg='#f0f0f0')
            title_frame.pack(fill=tk.X)

            tk.Label(title_frame, text=book["name"], font=("Arial", 12, "bold"), bg='#f0f0f0').pack(side=tk.LEFT)

            virtual_sessions = book["_virtual_sessions"]
            groups = virtual_sessions // 5
            remainder = virtual_sessions % 5
            bar_str = "卌" * groups + "|" * remainder

            bar_label = tk.Label(title_frame, text=bar_str, font=("Courier", 8), fg="blue", bg='#f0f0f0')
            bar_label.pack(side=tk.RIGHT, padx=2)

            tk.Label(card, text=f"Tác giả: {book.get('author', '')}", font=("Arial", 9, "italic"), bg='#f0f0f0').pack(anchor=tk.W, pady=2)

            total_seconds = book["_total_seconds"]
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            time_str = f"{hours} giờ {minutes} phút {seconds} giây" if hours > 0 else f"{minutes} phút {seconds} giây"
            tk.Label(card, text=f"Đã đọc: {time_str}", bg='#f0f0f0').pack(anchor=tk.W, pady=2)

            target = book.get("target_seconds", 0)
            if target > 0:
                percent = min(100, int((total_seconds / target) * 100))
                tk.Label(card, text=f"Mục tiêu: {percent}%", bg='#f0f0f0').pack(anchor=tk.W)
                progress = ttk.Progressbar(card, length=150, mode='determinate', value=percent)
                progress.pack(anchor=tk.W, pady=2)
            else:
                tk.Label(card, text="Chưa đặt mục tiêu", bg='#f0f0f0').pack(anchor=tk.W)

            col += 1
            if col >= max_col:
                col = 0
                row += 1

        for i in range(max_col):
            self.books_container.columnconfigure(i, weight=1)

    def prompt_for_input(self, title, prompt, initial_value=""):
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text=prompt).pack(pady=10)

        var = tk.StringVar(value=initial_value)
        entry = ttk.Entry(dialog, textvariable=var, width=40)
        entry.pack(pady=5)
        entry.focus_set()
        entry.select_range(0, tk.END)

        result = [None]

        def on_ok():
            result[0] = var.get().strip()
            dialog.destroy()

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=on_cancel).pack(side=tk.LEFT, padx=5)

        entry.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: on_cancel())
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        self.root.wait_window(dialog)
        return result[0]

    def add_book_from_home(self):
        name = self.prompt_for_input("Thêm sách mới", "Nhập tên sách:")
        if not name:
            return
        for book in self.books:
            if book["name"].lower() == name.lower():
                messagebox.showwarning("Cảnh báo", "Tên sách đã tồn tại!")
                return

        author = self.prompt_for_input("Thêm sách mới - Tác giả", "Nhập tác giả (có thể để trống):", "")
        if author is None:
            return

        new_book = {
            "name": name,
            "author": author,
            "sessions": [],
            "notes": "",
            "target_seconds": 0,
            "_total_seconds": 0,
            "_virtual_sessions": 0
        }
        self.books.append(new_book)
        self.save_data()
        self.refresh_home_books()
        self.show_detail(len(self.books) - 1)

    def add_old_book(self):
        name = self.prompt_for_input("Thêm sách cũ", "Nhập tên sách:")
        if not name:
            return
        for book in self.books:
            if book["name"].lower() == name.lower():
                messagebox.showwarning("Cảnh báo", "Tên sách đã tồn tại!")
                return

        author = self.prompt_for_input("Thêm sách cũ - Tác giả", "Nhập tác giả (có thể để trống):", "")
        if author is None:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Nhập thời gian đã đọc")
        dialog.geometry("300x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nhập thời gian đã đọc trước đây:").pack(pady=10)

        frame = ttk.Frame(dialog)
        frame.pack(pady=5)

        ttk.Label(frame, text="Giờ:").grid(row=0, column=0, padx=5, pady=2)
        hours_spin = ttk.Spinbox(frame, from_=0, to=999, width=5)
        hours_spin.grid(row=0, column=1, padx=5)
        hours_spin.set(0)
        hours_spin.focus_set()

        ttk.Label(frame, text="Phút:").grid(row=1, column=0, padx=5, pady=2)
        minutes_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        minutes_spin.grid(row=1, column=1, padx=5)
        minutes_spin.set(0)

        ttk.Label(frame, text="Giây:").grid(row=2, column=0, padx=5, pady=2)
        seconds_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        seconds_spin.grid(row=2, column=1, padx=5)
        seconds_spin.set(0)

        result = [False]

        def on_ok():
            try:
                h = int(hours_spin.get())
                m = int(minutes_spin.get())
                s = int(seconds_spin.get())
                total_seconds = h * 3600 + m * 60 + s
                if total_seconds > 0:
                    new_book = {
                        "name": name,
                        "author": author,
                        "sessions": [{
                            "duration": total_seconds,
                            "timestamp": None,
                            "note": "Đọc trước khi dùng app"
                        }],
                        "notes": "",
                        "target_seconds": 0,
                        "_total_seconds": total_seconds,
                        "_virtual_sessions": total_seconds // self.target_seconds
                    }
                    self.books.append(new_book)
                    self.save_data()
                    self.refresh_home_books()
                    self.show_detail(len(self.books) - 1)
                    result[0] = True
                    dialog.destroy()
                else:
                    messagebox.showwarning("Cảnh báo", "Thời gian phải lớn hơn 0!")
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")

        def on_cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Thêm", command=on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=on_cancel).pack(side=tk.LEFT, padx=5)

        dialog.bind("<Return>", lambda e: on_ok())
        dialog.bind("<Escape>", lambda e: on_cancel())
        dialog.protocol("WM_DELETE_WINDOW", on_cancel)

        self.root.wait_window(dialog)

    # -------------------- HELP WINDOW --------------------
    def show_help(self):
        help_win = tk.Toplevel(self.root)
        help_win.title("Hướng dẫn sử dụng")
        help_win.geometry("600x500")
        help_win.resizable(False, False)
        help_win.transient(self.root)
        help_win.grab_set()
        help_win.bind("<Escape>", lambda e: help_win.destroy())

        ttk.Label(help_win, text="Ứng dụng Theo dõi đọc sách theo phiên", font=("Arial", 16, "bold")).pack(pady=10)
        ttk.Label(help_win, text="Phiên bản 7.0", font=("Arial", 12)).pack()
        ttk.Label(help_win, text="Ngày hoàn thành: 02/03/2026", font=("Arial", 10)).pack(pady=5)

        frame = ttk.Frame(help_win)
        frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        text = tk.Text(frame, wrap=tk.WORD, font=("Arial", 10))
        scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        help_text = """
Tác giả: hmtcyrus

GIỚI THIỆU:
   Ứng dụng giúp bạn theo dõi thời gian đọc sách theo từng phiên, đặt mục tiêu, ghi chú và thống kê.
TÍNH NĂNG BACKUP:
   - Tự động tạo bản sao lưu mỗi khi lưu dữ liệu (giữ 5 bản gần nhất trong thư mục 'backups').
   - Nếu file dữ liệu chính bị lỗi, ứng dụng sẽ hỏi bạn có muốn khôi phục từ bản sao lưu gần nhất không.
   - Bạn có thể chủ động sao lưu hoặc khôi phục trong mục Cài đặt.

TÙY CHỌN FILE DỮ LIỆU:
   - Bạn có thể chọn nơi lưu file dữ liệu (mặc định là 'reading_tracker.json' trong thư mục chương trình).
   - Trong Cài đặt, chọn "Chọn file dữ liệu" để thay đổi. Ứng dụng sẽ tự động tải dữ liệu từ file mới.

CÁC MÀN HÌNH:
1. MÀN HÌNH CHÍNH (HOME):
   - Hiển thị tất cả sách dưới dạng thẻ.
   - Click vào thẻ để vào chi tiết sách.
   - Chuột phải vào thẻ để sửa tên/tác giả hoặc xóa sách.
   - Nút "Thêm sách mới" để tạo sách chưa có thời gian đọc.
   - Nút "Thêm sách cũ" để tạo sách và nhập thời gian đã đọc trước đó.
   - Nút "Cài đặt" để thay đổi thời gian mặc định mỗi phiên, quản lý backup và chọn file dữ liệu.
   - Nút "Thống kê tất cả" xem báo cáo tổng hợp.
   - Nút "Help" xem hướng dẫn này.

2. MÀN HÌNH CHI TIẾT (DETAIL):
   - Xem thông tin sách: tên, tác giả, tổng thời gian đã đọc, vạch phiên (mỗi vạch | tương ứng 1 phiên, mỗi 卌 = 5 phiên). Nếu có mục tiêu, vạch phiên hiển thị tiến độ: vạch đậm là đã đọc, vạch mờ là còn lại.
   - Đặt mục tiêu thời gian cho sách (con trỏ focus và bôi đen ô giờ).
   - Bộ đếm phiên: có thể chuyển giữa thanh và đồng hồ (nút "Chuyển sang ..." hoặc phím Tab).
   - Nút "Bắt đầu/Tạm dừng/Tiếp tục" để điều khiển timer.
   - Nút "Lưu phiên" để ghi nhận thời gian hiện tại vào tổng thời gian (timer dừng và reset).
   - Nút "Đặt lại" reset timer về 0.
   - Ghi chú: nhập ghi chú cho sách, tự động lưu khi rời khỏi ô, có thể phóng to/thu nhỏ font bằng Ctrl + lăn chuột, và:
        * Ctrl + B: bật/tắt chế độ gõ đậm (các ký tự tiếp theo sẽ được in đậm)
        * Ctrl + B (khi có vùng chọn): bật/tắt in đậm cho vùng chọn.
   - Chuột phải vào tên sách để điều chỉnh tổng thời gian (thêm/bớt thủ công).

LƯU Ý:
   - Khi quay lại màn hình chính hoặc chuyển sách, ghi chú được tự động lưu.
   - Khi tắt ứng dụng, mọi dữ liệu đều được lưu.

PHÍM TẮT:
   - Ctrl + Mũi tên Xuống: Focus vào ô ghi chú.
   - Tab: Chuyển đổi giữa hiển thị thanh và đồng hồ (khi ở màn hình chi tiết).
   - Trong ghi chú: Ctrl + Z (hoàn tác), Ctrl + B (bật/tắt chế độ gõ đậm hoặc bôi đậm vùng chọn), Escape (thoát focus khỏi ghi chú).
   - Trong các hộp thoại: Enter = OK, Escape = Hủy/Đóng.

ÂM THANH:
   - Khi kết thúc một phiên đọc (đếm ngược về 0), sẽ có tiếng beep thông báo.

THỐNG KÊ:
   - Màn hình thống kê tổng thể: hiển thị bảng theo sách, theo tuần, theo tháng.
   - Có thể sao chép (📋) hoặc xuất ra CSV (💾) tab hiện tại.

Chúc bạn đọc sách hiệu quả!
"""
        text.insert(tk.END, help_text)
        text.config(state=tk.DISABLED)

        ttk.Button(help_win, text="Đóng", command=help_win.destroy).pack(pady=10)

    # -------------------- THỐNG KÊ TỔNG THỂ (HOME) --------------------
    def show_overall_statistics(self):
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Thống kê đọc - Tất cả sách")
        stats_win.geometry("800x550")
        stats_win.transient(self.root)
        stats_win.bind("<Escape>", lambda e: stats_win.destroy())

        all_sessions = []
        for book in self.books:
            for s in book.get("sessions", []):
                if s.get("timestamp"):
                    all_sessions.append({
                        "book": book["name"],
                        "author": book.get("author", ""),
                        "duration": s["duration"],
                        "timestamp": s["timestamp"]
                    })

        if not all_sessions:
            ttk.Label(stats_win, text="Chưa có dữ liệu thời gian cho phiên nào.").pack(pady=20)
            return

        main_frame = ttk.Frame(stats_win)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)

        book_frame = ttk.Frame(notebook)
        notebook.add(book_frame, text="Theo sách")

        columns = ("STT", "Tên sách", "Tác giả", "Tổng thời gian", "Số phiên")
        book_tree = ttk.Treeview(book_frame, columns=columns, show="headings", height=12)
        book_tree.pack(fill=tk.BOTH, expand=True)

        book_tree.heading("STT", text="STT")
        book_tree.heading("Tên sách", text="Tên sách")
        book_tree.heading("Tác giả", text="Tác giả")
        book_tree.heading("Tổng thời gian", text="Tổng thời gian")
        book_tree.heading("Số phiên", text="Số phiên")

        book_tree.column("STT", width=40, anchor="center")
        book_tree.column("Tên sách", width=200)
        book_tree.column("Tác giả", width=150)
        book_tree.column("Tổng thời gian", width=150, anchor="center")
        book_tree.column("Số phiên", width=80, anchor="center")

        book_stats = {}
        for s in all_sessions:
            book_name = s["book"]
            if book_name not in book_stats:
                book_stats[book_name] = {
                    "author": s["author"],
                    "total": 0,
                    "count": 0
                }
            book_stats[book_name]["total"] += s["duration"]
            book_stats[book_name]["count"] += 1

        for i, (book_name, stats) in enumerate(sorted(book_stats.items()), 1):
            total = stats["total"]
            count = stats["count"]
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            total_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"

            book_tree.insert("", tk.END, values=(
                i,
                book_name,
                stats["author"],
                total_str,
                count
            ))

        week_frame = ttk.Frame(notebook)
        notebook.add(week_frame, text="Theo tuần")

        week_tree = ttk.Treeview(week_frame, columns=("Tuần", "Tổng thời gian", "Số phiên"), show="headings", height=12)
        week_tree.pack(fill=tk.BOTH, expand=True)

        week_tree.heading("Tuần", text="Tuần")
        week_tree.heading("Tổng thời gian", text="Tổng thời gian")
        week_tree.heading("Số phiên", text="Số phiên")

        week_tree.column("Tuần", width=120, anchor="center")
        week_tree.column("Tổng thời gian", width=150, anchor="center")
        week_tree.column("Số phiên", width=80, anchor="center")

        week_data = {}
        week_count = {}
        for s in all_sessions:
            try:
                dt = datetime.fromisoformat(s["timestamp"])
                year_week = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                week_data[year_week] = week_data.get(year_week, 0) + s["duration"]
                week_count[year_week] = week_count.get(year_week, 0) + 1
            except:
                continue

        for week in sorted(week_data.keys()):
            total = week_data[week]
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            total_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
            week_tree.insert("", tk.END, values=(week, total_str, week_count[week]))

        month_frame = ttk.Frame(notebook)
        notebook.add(month_frame, text="Theo tháng")

        month_tree = ttk.Treeview(month_frame, columns=("Tháng", "Tổng thời gian", "Số phiên"), show="headings", height=12)
        month_tree.pack(fill=tk.BOTH, expand=True)

        month_tree.heading("Tháng", text="Tháng")
        month_tree.heading("Tổng thời gian", text="Tổng thời gian")
        month_tree.heading("Số phiên", text="Số phiên")

        month_tree.column("Tháng", width=100, anchor="center")
        month_tree.column("Tổng thời gian", width=150, anchor="center")
        month_tree.column("Số phiên", width=80, anchor="center")

        month_data = {}
        month_count = {}
        for s in all_sessions:
            try:
                dt = datetime.fromisoformat(s["timestamp"])
                year_month = f"{dt.year}-{dt.month:02d}"
                month_data[year_month] = month_data.get(year_month, 0) + s["duration"]
                month_count[year_month] = month_count.get(year_month, 0) + 1
            except:
                continue

        for month in sorted(month_data.keys()):
            total = month_data[month]
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            total_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
            month_tree.insert("", tk.END, values=(month, total_str, month_count[month]))

        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="📋 Sao chép tab này", 
                   command=lambda: self.copy_treeview_to_clipboard(notebook)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="💾 Xuất tab này ra CSV", 
                   command=lambda: self.export_treeview_to_csv(notebook)).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Đóng", command=stats_win.destroy).pack(side=tk.RIGHT, padx=5)

    def copy_treeview_to_clipboard(self, notebook):
        current_tab = notebook.select()
        if not current_tab:
            return
        frame = notebook.nametowidget(current_tab)
        tree = None
        for child in frame.winfo_children():
            if isinstance(child, ttk.Treeview):
                tree = child
                break
        if not tree:
            messagebox.showerror("Lỗi", "Không tìm thấy bảng dữ liệu.")
            return

        columns = [tree.heading(col)['text'] for col in tree['columns']]
        rows = []
        for item in tree.get_children():
            row = tree.item(item)['values']
            rows.append(row)

        text = '\t'.join(columns) + '\n'
        for row in rows:
            text += '\t'.join(str(cell) for cell in row) + '\n'

        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Thành công", "Đã sao chép dữ liệu vào clipboard.")

    def export_treeview_to_csv(self, notebook):
        current_tab = notebook.select()
        if not current_tab:
            return
        frame = notebook.nametowidget(current_tab)
        tree = None
        for child in frame.winfo_children():
            if isinstance(child, ttk.Treeview):
                tree = child
                break
        if not tree:
            messagebox.showerror("Lỗi", "Không tìm thấy bảng dữ liệu.")
            return

        tab_name = notebook.tab(current_tab, "text")
        default_filename = f"thongke_{tab_name}.csv"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=default_filename
        )
        if not filepath:
            return

        columns = [tree.heading(col)['text'] for col in tree['columns']]
        rows = []
        for item in tree.get_children():
            row = tree.item(item)['values']
            rows.append(row)

        try:
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(columns)
                writer.writerows(rows)
            messagebox.showinfo("Thành công", f"Đã xuất dữ liệu ra file:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể ghi file: {e}")

    # -------------------- MÀN HÌNH CHI TIẾT --------------------
    def create_detail_widgets(self):
        back_btn = ttk.Button(self.detail_frame, text="← Quay lại", command=self.show_home)
        back_btn.pack(anchor=tk.W, padx=10, pady=5)
        ToolTip(back_btn, "Quay lại tủ sách (tự động lưu phiên và ghi chú hiện tại)")

        info_frame = ttk.LabelFrame(self.detail_frame, text="Thông tin sách", padding=5)
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.book_name_label = tk.Label(info_frame, text="", font=("Arial", 12, "bold"), anchor=tk.W)
        self.book_name_label.pack(fill=tk.X, pady=2)
        self.book_name_label.bind("<Button-3>", self.show_detail_context_menu)
        ToolTip(self.book_name_label, "Nhấp chuột phải để điều chỉnh tổng thời gian")

        self.author_label = ttk.Label(info_frame, text="", font=("Arial", 10, "italic"))
        self.author_label.pack(anchor=tk.W, pady=2)

        self.target_frame = ttk.Frame(info_frame)
        self.target_frame.pack(fill=tk.X, pady=2)

        self.stats_label = ttk.Label(info_frame, text="", font=("Arial", 10))
        self.stats_label.pack(anchor=tk.W, pady=2)

        self.sessions_frame = ttk.Frame(info_frame)
        self.sessions_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
        self.sessions_done_label = ttk.Label(self.sessions_frame, font=("Courier", 14), foreground="blue")
        self.sessions_done_label.pack(side=tk.LEFT)
        self.sessions_remaining_label = ttk.Label(self.sessions_frame, font=("Courier", 14), foreground="lightgray")
        self.sessions_remaining_label.pack(side=tk.LEFT)

        self.toggle_mode_btn = ttk.Button(info_frame, text="Chuyển sang tổng thời gian", command=self.toggle_display_mode)
        self.toggle_mode_btn.pack(anchor=tk.W, pady=2)
        ToolTip(self.toggle_mode_btn, "Chuyển đổi giữa hiển thị số phiên và tổng thời gian")

        stats_btn = ttk.Button(info_frame, text="📊 Thống kê sách này", command=self.show_book_statistics)
        stats_btn.pack(anchor=tk.W, pady=2)
        ToolTip(stats_btn, "Xem thống kê chi tiết cho sách này")

        timer_frame = ttk.LabelFrame(self.detail_frame, text="Bộ đếm phiên", padding=5)
        timer_frame.pack(fill=tk.X, padx=10, pady=5)

        top_timer_line = ttk.Frame(timer_frame)
        top_timer_line.pack(fill=tk.X, pady=2)

        ttk.Label(top_timer_line, text="Thời gian mỗi phiên:").pack(side=tk.LEFT, padx=5)
        self.session_time_label = ttk.Label(top_timer_line, text=self.format_time(self.target_seconds),
                                            font=("Arial", 10, "bold"))
        self.session_time_label.pack(side=tk.LEFT, padx=5)
        ToolTip(self.session_time_label, "Thời gian mỗi phiên (có thể thay đổi trong Cài đặt)")

        self.toggle_timer_display_btn = ttk.Button(top_timer_line, text="Chuyển sang đồng hồ",
                                                   command=self.toggle_timer_display)
        self.toggle_timer_display_btn.pack(side=tk.RIGHT, padx=5)
        ToolTip(self.toggle_timer_display_btn, "Chuyển đổi giữa thanh tiến trình và đồng hồ (phím Tab)")

        self.canvas_width = 450
        self.canvas_height = 30
        self.progress_canvas = tk.Canvas(timer_frame, width=self.canvas_width, height=self.canvas_height,
                                         bg='lightgray', highlightthickness=1, highlightbackground='gray')
        self.progress_canvas.pack(pady=5)
        self.bar = self.progress_canvas.create_rectangle(0, 0, self.canvas_width, self.canvas_height,
                                                         fill='green', outline='')
        self.bar_color = 'green'

        self.clock_label = ttk.Label(timer_frame, text="00:00", font=("Arial", 24))
        self.clock_label.pack(pady=5)
        self.clock_label.pack_forget()

        control_frame = ttk.Frame(timer_frame)
        control_frame.pack(pady=5)

        self.start_pause_btn = ttk.Button(control_frame, text="Bắt đầu", command=self.start_pause_toggle, width=12)
        self.start_pause_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.start_pause_btn, "Bắt đầu / Tạm dừng / Tiếp tục phiên đọc")

        self.save_session_btn = ttk.Button(control_frame, text="💾 Lưu phiên", command=self.save_current_session, width=12)
        self.save_session_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.save_session_btn, "Lưu thời gian hiện tại thành một phiên và reset đồng hồ")

        self.reset_btn = ttk.Button(control_frame, text="Đặt lại", command=self.reset_timer)
        self.reset_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.reset_btn, "Đặt lại đồng hồ về 0 (không lưu)")

        self.auto_start_var = tk.BooleanVar(value=False)
        auto_start_cb = ttk.Checkbutton(timer_frame, text="Tự động bắt đầu phiên tiếp theo", variable=self.auto_start_var)
        auto_start_cb.pack(pady=5)
        ToolTip(auto_start_cb, "Sau khi lưu phiên, tự động bắt đầu phiên mới")

        notes_frame = ttk.LabelFrame(self.detail_frame, text="", padding=5)
        notes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        notes_header = ttk.Frame(notes_frame)
        notes_header.pack(fill=tk.X, pady=(0,5))

        ttk.Label(notes_header, text="Ghi chú", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        ToolTip(notes_header, "Ghi chú cho sách (tự động lưu khi rời khỏi ô hoặc chuyển sách)")

        self.notes_font = tkfont.Font(family="TkDefaultFont", size=10)
        self.notes_text = tk.Text(notes_frame, wrap=tk.WORD, height=8, font=self.notes_font, undo=True)
        self.notes_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bold_font = self.notes_font.copy()
        bold_font.configure(weight="bold")
        self.notes_text.tag_configure("bold", font=bold_font)

        self.notes_text.bind("<Control-z>", lambda e: self.notes_text.edit_undo() or "break")
        self.notes_text.bind("<Control-b>", self.toggle_bold)
        self.notes_text.bind("<Key>", self.on_notes_key)
        self.notes_text.bind("<Escape>", self.escape_from_notes)
        self.notes_text.bind("<FocusOut>", lambda e: self.save_notes())

        self.notes_text.bind("<Control-MouseWheel>", self.on_notes_zoom)
        self.notes_text.bind("<Control-Button-4>", self.on_notes_zoom_linux)
        self.notes_text.bind("<Control-Button-5>", self.on_notes_zoom_linux)

        notes_scroll = ttk.Scrollbar(notes_frame, orient=tk.VERTICAL, command=self.notes_text.yview)
        notes_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_text.config(yscrollcommand=notes_scroll.set)

    def toggle_bold(self, event):
        if self.notes_text.tag_ranges("sel"):
            if self.notes_text.tag_nextrange("bold", "sel.first", "sel.last"):
                self.notes_text.tag_remove("bold", "sel.first", "sel.last")
            else:
                self.notes_text.tag_add("bold", "sel.first", "sel.last")
        else:
            self.bold_mode = not self.bold_mode
            if self.bold_mode:
                self.notes_text.config(cursor="xterm")
            else:
                self.notes_text.config(cursor="")
        return "break"

    def on_notes_key(self, event):
        if self.bold_mode and event.char and event.char.isprintable():
            self.notes_text.insert(tk.INSERT, event.char, "bold")
            return "break"
        return None

    def escape_from_notes(self, event):
        self.start_pause_btn.focus_set()
        self.bold_mode = False
        return "break"

    def save_current_session(self):
        if self.current_book_index < 0:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cuốn sách!")
            return

        if self.timer_seconds == 0:
            messagebox.showinfo("Thông báo", "Chưa có thời gian để lưu.")
            return

        if self.timer_running:
            if self.timer_paused:
                self.timer_running = False
                self.timer_paused = False
            else:
                self.timer_running = False
                if self.after_id:
                    self.root.after_cancel(self.after_id)
                    self.after_id = None

        session = {
            "duration": self.timer_seconds,
            "timestamp": datetime.now().isoformat()
        }
        book = self.books[self.current_book_index]
        book["sessions"].append(session)

        book["_total_seconds"] += self.timer_seconds
        book["_virtual_sessions"] = book["_total_seconds"] // self.target_seconds

        self.save_data()
        self.update_stats_label()
        self.update_target_display()

        self.timer_seconds = 0
        self.start_pause_btn.config(text="Bắt đầu")
        self.set_bar_color('green')
        self.update_timer_display()

        messagebox.showinfo("Thành công", f"Đã lưu {self.format_time(session['duration'])} vào tổng thời gian.")

    def show_detail_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label="Điều chỉnh tổng thời gian đã đọc", command=self.adjust_total_time)
        menu.tk_popup(event.x_root, event.y_root)

    def adjust_total_time(self):
        if self.current_book_index < 0:
            return
        book = self.books[self.current_book_index]
        current_total = book["_total_seconds"]

        dialog = tk.Toplevel(self.root)
        dialog.title("Điều chỉnh tổng thời gian")
        dialog.geometry("300x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nhập tổng thời gian mới (giờ:phút:giây):").pack(pady=10)

        frame = ttk.Frame(dialog)
        frame.pack(pady=5)

        ttk.Label(frame, text="Giờ:").grid(row=0, column=0, padx=5, pady=2)
        hours_spin = ttk.Spinbox(frame, from_=0, to=999, width=5)
        hours_spin.grid(row=0, column=1, padx=5)
        hours_spin.set(current_total // 3600)

        ttk.Label(frame, text="Phút:").grid(row=1, column=0, padx=5, pady=2)
        minutes_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        minutes_spin.grid(row=1, column=1, padx=5)
        minutes_spin.set((current_total % 3600) // 60)

        ttk.Label(frame, text="Giây:").grid(row=2, column=0, padx=5, pady=2)
        seconds_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        seconds_spin.grid(row=2, column=1, padx=5)
        seconds_spin.set(current_total % 60)

        def save_adjustment():
            try:
                h = int(hours_spin.get())
                m = int(minutes_spin.get())
                s = int(seconds_spin.get())
                new_total = h * 3600 + m * 60 + s
                if new_total < 0:
                    messagebox.showwarning("Cảnh báo", "Thời gian không hợp lệ!")
                    return
                diff = new_total - current_total
                if diff != 0:
                    adj_session = {
                        "duration": diff,
                        "timestamp": datetime.now().isoformat(),
                        "note": "Điều chỉnh thủ công"
                    }
                    book["sessions"].append(adj_session)
                    book["_total_seconds"] = new_total
                    book["_virtual_sessions"] = new_total // self.target_seconds
                    self.save_data()
                    self.update_stats_label()
                    self.update_target_display()
                    self.refresh_home_books()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")

        dialog.bind("<Return>", lambda e: save_adjustment())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Áp dụng", command=save_adjustment).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def show_book_statistics(self):
        if self.current_book_index < 0:
            return
        book = self.books[self.current_book_index]

        stats_win = tk.Toplevel(self.root)
        stats_win.title(f"Thống kê - {book['name']}")
        stats_win.geometry("600x400")
        stats_win.transient(self.root)
        stats_win.bind("<Escape>", lambda e: stats_win.destroy())

        sessions = [s for s in book.get("sessions", []) if s.get("timestamp")]

        if not sessions:
            ttk.Label(stats_win, text="Chưa có dữ liệu thời gian cho các phiên.").pack(pady=20)
            return

        notebook = ttk.Notebook(stats_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        week_frame = ttk.Frame(notebook)
        notebook.add(week_frame, text="Theo tuần")
        week_tree = ttk.Treeview(week_frame, columns=("Tuần", "Tổng thời gian", "Số phiên"), show="headings", height=12)
        week_tree.pack(fill=tk.BOTH, expand=True)
        week_tree.heading("Tuần", text="Tuần")
        week_tree.heading("Tổng thời gian", text="Tổng thời gian")
        week_tree.heading("Số phiên", text="Số phiên")
        week_tree.column("Tuần", width=120, anchor="center")
        week_tree.column("Tổng thời gian", width=150, anchor="center")
        week_tree.column("Số phiên", width=80, anchor="center")

        week_data = {}
        week_count = {}
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["timestamp"])
                year_week = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                week_data[year_week] = week_data.get(year_week, 0) + s["duration"]
                week_count[year_week] = week_count.get(year_week, 0) + 1
            except:
                continue

        for week in sorted(week_data.keys()):
            total = week_data[week]
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            total_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
            week_tree.insert("", tk.END, values=(week, total_str, week_count[week]))

        month_frame = ttk.Frame(notebook)
        notebook.add(month_frame, text="Theo tháng")
        month_tree = ttk.Treeview(month_frame, columns=("Tháng", "Tổng thời gian", "Số phiên"), show="headings", height=12)
        month_tree.pack(fill=tk.BOTH, expand=True)
        month_tree.heading("Tháng", text="Tháng")
        month_tree.heading("Tổng thời gian", text="Tổng thời gian")
        month_tree.heading("Số phiên", text="Số phiên")
        month_tree.column("Tháng", width=100, anchor="center")
        month_tree.column("Tổng thời gian", width=150, anchor="center")
        month_tree.column("Số phiên", width=80, anchor="center")

        month_data = {}
        month_count = {}
        for s in sessions:
            try:
                dt = datetime.fromisoformat(s["timestamp"])
                year_month = f"{dt.year}-{dt.month:02d}"
                month_data[year_month] = month_data.get(year_month, 0) + s["duration"]
                month_count[year_month] = month_count.get(year_month, 0) + 1
            except:
                continue

        for month in sorted(month_data.keys()):
            total = month_data[month]
            hours = total // 3600
            minutes = (total % 3600) // 60
            seconds = total % 60
            total_str = f"{hours}h {minutes}m {seconds}s" if hours > 0 else f"{minutes}m {seconds}s"
            month_tree.insert("", tk.END, values=(month, total_str, month_count[month]))

        ttk.Button(stats_win, text="Đóng", command=stats_win.destroy).pack(pady=5)

    # -------------------- CÁC PHƯƠNG THỨC XỬ LÝ CHI TIẾT --------------------
    def display_book(self, index):
        if index < 0 or index >= len(self.books):
            return
        book = self.books[index]
        # Không gọi save_notes ở đây vì đã được gọi trước khi vào detail
        self.book_name_label.config(text=book["name"])
        self.author_label.config(text=f"Tác giả: {book.get('author', '')}")
        self.update_stats_label()
        self.update_target_display()
        self.notes_text.delete(1.0, tk.END)
        self.notes_text.insert(1.0, book.get("notes", ""))
        self.reset_timer()

    def update_target_display(self):
        for widget in self.target_frame.winfo_children():
            widget.destroy()

        if self.current_book_index < 0:
            return

        book = self.books[self.current_book_index]
        total_seconds = book["_total_seconds"]
        target = book.get("target_seconds", 0)

        if target <= 0:
            ttk.Label(self.target_frame, text="Mục tiêu: chưa đặt").pack(side=tk.LEFT, padx=5)
            ttk.Button(self.target_frame, text="Đặt mục tiêu", command=self.set_target).pack(side=tk.LEFT, padx=5)
        else:
            percent = min(100, int((total_seconds / target) * 100)) if target > 0 else 0
            progress_bar = ttk.Progressbar(self.target_frame, length=200, mode='determinate', value=percent)
            progress_bar.pack(side=tk.LEFT, padx=5)

            label_text = f"{self.format_time(total_seconds)} / {self.format_time(target)} ({percent}%)"
            ttk.Label(self.target_frame, text=label_text).pack(side=tk.LEFT, padx=5)

            ttk.Button(self.target_frame, text="Sửa", command=self.set_target).pack(side=tk.LEFT, padx=2)

    def set_target(self):
        if self.current_book_index < 0:
            return
        book = self.books[self.current_book_index]
        current_target = book.get("target_seconds", 0)

        dialog = tk.Toplevel(self.root)
        dialog.title("Đặt mục tiêu thời gian")
        dialog.geometry("300x200")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        ttk.Label(dialog, text="Nhập thời gian mục tiêu:").pack(pady=10)

        frame = ttk.Frame(dialog)
        frame.pack(pady=5)

        ttk.Label(frame, text="Giờ:").grid(row=0, column=0, padx=5, pady=2)
        hours_spin = ttk.Spinbox(frame, from_=0, to=999, width=5)
        hours_spin.grid(row=0, column=1, padx=5)
        hours_spin.set(current_target // 3600)
        hours_spin.focus_set()
        hours_spin.select_range(0, tk.END)

        ttk.Label(frame, text="Phút:").grid(row=1, column=0, padx=5, pady=2)
        minutes_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        minutes_spin.grid(row=1, column=1, padx=5)
        minutes_spin.set((current_target % 3600) // 60)

        ttk.Label(frame, text="Giây:").grid(row=2, column=0, padx=5, pady=2)
        seconds_spin = ttk.Spinbox(frame, from_=0, to=59, width=5)
        seconds_spin.grid(row=2, column=1, padx=5)
        seconds_spin.set(current_target % 60)

        def save_target():
            try:
                h = int(hours_spin.get())
                m = int(minutes_spin.get())
                s = int(seconds_spin.get())
                new_target = h * 3600 + m * 60 + s
                if new_target >= 0:
                    book["target_seconds"] = new_target
                    self.save_data()
                    self.update_target_display()
                    self.update_stats_label()
                    dialog.destroy()
                else:
                    messagebox.showwarning("Cảnh báo", "Thời gian không hợp lệ!")
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")

        dialog.bind("<Return>", lambda e: save_target())
        dialog.bind("<Escape>", lambda e: dialog.destroy())

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=10)
        ttk.Button(btn_frame, text="Lưu", command=save_target).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Hủy", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def open_settings(self):
        settings_win = tk.Toplevel(self.root)
        settings_win.title("Cài đặt")
        settings_win.geometry("350x350")
        settings_win.resizable(False, False)
        settings_win.transient(self.root)
        settings_win.grab_set()

        time_frame = ttk.LabelFrame(settings_win, text="Thời gian phiên mặc định", padding=5)
        time_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Label(time_frame, text="Phút:").grid(row=0, column=0, padx=5, pady=2)
        minutes_spin = ttk.Spinbox(time_frame, from_=0, to=999, width=5, justify=tk.RIGHT)
        minutes_spin.grid(row=0, column=1, padx=5)
        minutes_spin.set(self.target_seconds // 60)
        minutes_spin.focus_set()
        minutes_spin.select_range(0, tk.END)

        ttk.Label(time_frame, text="Giây:").grid(row=0, column=2, padx=5)
        seconds_spin = ttk.Spinbox(time_frame, from_=0, to=59, width=5, justify=tk.RIGHT)
        seconds_spin.grid(row=0, column=3, padx=5)
        seconds_spin.set(self.target_seconds % 60)

        def save_settings():
            try:
                m = int(minutes_spin.get())
                s = int(seconds_spin.get())
                new_target = m * 60 + s
                if new_target > 0:
                    self.target_seconds = new_target
                    self._current_target = new_target
                    self.session_time_label.config(text=self.format_time(self.target_seconds))
                    for book in self.books:
                        book["_virtual_sessions"] = book["_total_seconds"] // new_target
                    self.save_data()
                    self.update_stats_label()
                    self.update_timer_display()
                    self.refresh_home_books()
                    messagebox.showinfo("Thông báo", "Đã lưu cài đặt.")
                else:
                    messagebox.showwarning("Cảnh báo", "Thời gian phải lớn hơn 0!")
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ!")

        btn_frame = ttk.Frame(time_frame)
        btn_frame.grid(row=1, column=0, columnspan=4, pady=5)
        ttk.Button(btn_frame, text="Lưu", command=save_settings).pack(side=tk.LEFT, padx=5)

        backup_frame = ttk.LabelFrame(settings_win, text="Sao lưu & Phục hồi", padding=5)
        backup_frame.pack(fill=tk.X, padx=10, pady=5)

        ttk.Button(backup_frame, text="💾 Sao lưu dữ liệu", command=self.manual_backup).pack(fill=tk.X, pady=2)
        ttk.Button(backup_frame, text="🔄 Khôi phục từ bản sao lưu", command=self.manual_restore).pack(fill=tk.X, pady=2)

        data_frame = ttk.LabelFrame(settings_win, text="File dữ liệu", padding=5)
        data_frame.pack(fill=tk.X, padx=10, pady=5)

        current_file_label = ttk.Label(data_frame, text=f"Hiện tại: {os.path.basename(self.data_file)}", wraplength=300)
        current_file_label.pack(anchor=tk.W, pady=2)

        def choose_data_file():
            new_file = filedialog.asksaveasfilename(
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialfile=os.path.basename(self.data_file)
            )
            if not new_file:
                return
            if os.path.exists(new_file):
                answer = messagebox.askyesno("Xác nhận", f"File {new_file} đã tồn tại. Bạn có muốn tải dữ liệu từ file đó không? (Chọn No để tạo file mới)")
                if answer:
                    self.data_file = new_file
                    self.backup_dir = os.path.join(os.path.dirname(new_file), BACKUP_DIR_NAME)
                    if not os.path.exists(self.backup_dir):
                        os.makedirs(self.backup_dir)
                    self.books.clear()
                    self.load_data()
                    self.refresh_home_books()
                    if self.detail_frame.winfo_ismapped():
                        self.show_home()
                    self.save_config()
                    messagebox.showinfo("Thành công", "Đã chuyển sang file dữ liệu mới.")
                else:
                    self.data_file = new_file
                    self.backup_dir = os.path.join(os.path.dirname(new_file), BACKUP_DIR_NAME)
                    if not os.path.exists(self.backup_dir):
                        os.makedirs(self.backup_dir)
                    self.save_data()
                    self.save_config()
                    messagebox.showinfo("Thành công", "Đã chuyển sang file dữ liệu mới và lưu dữ liệu hiện tại.")
            else:
                self.data_file = new_file
                self.backup_dir = os.path.join(os.path.dirname(new_file), BACKUP_DIR_NAME)
                if not os.path.exists(self.backup_dir):
                    os.makedirs(self.backup_dir)
                self.save_data()
                self.save_config()
                messagebox.showinfo("Thành công", "Đã chuyển sang file dữ liệu mới.")

        ttk.Button(data_frame, text="📁 Chọn file dữ liệu", command=choose_data_file).pack(fill=tk.X, pady=2)

        ttk.Button(settings_win, text="Đóng", command=settings_win.destroy).pack(pady=10)

        settings_win.bind("<Escape>", lambda e: settings_win.destroy())

    # -------------------- CÁC HÀM HỖ TRỢ KHÁC --------------------
    def on_notes_zoom(self, event):
        size = self.notes_font.cget("size")
        if event.delta > 0:
            size += 1
        else:
            size = max(6, size - 1)
        self.notes_font.config(size=size)
        bold_font = self.notes_font.copy()
        bold_font.configure(weight="bold")
        self.notes_text.tag_configure("bold", font=bold_font)

    def on_notes_zoom_linux(self, event):
        size = self.notes_font.cget("size")
        if event.num == 4:
            size += 1
        elif event.num == 5:
            size = max(6, size - 1)
        self.notes_font.config(size=size)
        bold_font = self.notes_font.copy()
        bold_font.configure(weight="bold")
        self.notes_text.tag_configure("bold", font=bold_font)

    def set_bar_color(self, color):
        if self.bar_color != color:
            self.progress_canvas.itemconfig(self.bar, fill=color)
            self.bar_color = color

    def format_time(self, seconds):
        m = seconds // 60
        s = seconds % 60
        return f"{m:02d}:{s:02d}"

    def toggle_timer_display(self):
        if self.timer_display_mode == "bar":
            self.timer_display_mode = "clock"
            self.toggle_timer_display_btn.config(text="Chuyển sang thanh")
            self.progress_canvas.pack_forget()
            self.clock_label.pack(pady=5)
        else:
            self.timer_display_mode = "bar"
            self.toggle_timer_display_btn.config(text="Chuyển sang đồng hồ")
            self.clock_label.pack_forget()
            self.progress_canvas.pack(pady=5)
        self.update_timer_display()

    def update_timer_display(self):
        if self.timer_running and not self.timer_paused:
            remaining = max(0, self.target_seconds - self.timer_seconds)
            if self.timer_display_mode == "bar":
                bar_length = int((remaining / self.target_seconds) * self.canvas_width)
                self.progress_canvas.coords(self.bar, 0, 0, bar_length, self.canvas_height)
            else:
                self.clock_label.config(text=self.format_time(remaining))
        else:
            if self.timer_display_mode == "bar":
                self.progress_canvas.coords(self.bar, 0, 0, 0, self.canvas_height)
            else:
                self.clock_label.config(text="00:00")

    def start_pause_toggle(self):
        if self.current_book_index < 0:
            messagebox.showwarning("Cảnh báo", "Vui lòng chọn một cuốn sách!")
            return

        if not self.timer_running:
            self.timer_running = True
            self.timer_paused = False
            self.start_pause_btn.config(text="Tạm dừng")
            self.set_bar_color('green')
            self.update_timer()
        elif self.timer_running and not self.timer_paused:
            self.timer_paused = True
            self.start_pause_btn.config(text="Tiếp tục")
            self.set_bar_color('gray')
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
        else:
            self.timer_paused = False
            self.start_pause_btn.config(text="Tạm dừng")
            self.set_bar_color('green')
            self.update_timer()

    def reset_timer(self):
        if self.timer_running:
            self.timer_running = False
            self.timer_paused = False
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
        self.timer_seconds = 0
        self.start_pause_btn.config(text="Bắt đầu")
        self.set_bar_color('green')
        self.update_timer_display()

    def update_timer(self):
        if self.timer_running and not self.timer_paused:
            self.timer_seconds += 1
            self.update_timer_display()

            if self.timer_seconds >= self.target_seconds:
                self.timer_running = False
                self.timer_paused = False
                self.start_pause_btn.config(text="Bắt đầu")
                if self.after_id:
                    self.root.after_cancel(self.after_id)
                    self.after_id = None

                winsound.MessageBeep()

                result = messagebox.askyesno(
                    "Kết thúc phiên",
                    f"Đã hoàn thành phiên {self.format_time(self.target_seconds)}.\n"
                    "Bạn có muốn ghi nhận phiên này và bắt đầu phiên mới?"
                )
                if result:
                    session = {
                        "duration": self.target_seconds,
                        "timestamp": datetime.now().isoformat()
                    }
                    book = self.books[self.current_book_index]
                    book["sessions"].append(session)
                    book["_total_seconds"] += self.target_seconds
                    book["_virtual_sessions"] = book["_total_seconds"] // self.target_seconds
                    self.save_data()
                    self.update_stats_label()
                    self.update_target_display()
                    self.timer_seconds = 0
                    self.update_timer_display()
                    if self.auto_start_var.get():
                        self.start_pause_toggle()
                else:
                    self.timer_seconds = 0
                    self.update_timer_display()
            else:
                self.after_id = self.root.after(1000, self.update_timer)

    def update_stats_label(self):
        if self.current_book_index < 0:
            self.stats_label.config(text="")
            self.sessions_done_label.config(text="")
            self.sessions_remaining_label.config(text="")
            return

        book = self.books[self.current_book_index]
        total_seconds = book["_total_seconds"]
        target = book.get("target_seconds", 0)

        done_sessions = total_seconds // self.target_seconds

        if target > 0:
            target_sessions = target // self.target_seconds
            remaining_sessions = max(0, target_sessions - done_sessions)
        else:
            remaining_sessions = 0

        done_groups = done_sessions // 5
        done_remainder = done_sessions % 5
        done_str = "卌" * done_groups + "|" * done_remainder

        remaining_groups = remaining_sessions // 5
        remaining_remainder = remaining_sessions % 5
        remaining_str = "卌" * remaining_groups + "|" * remaining_remainder

        self.sessions_done_label.config(text=done_str)
        self.sessions_remaining_label.config(text=remaining_str)

        if self.display_mode == "sessions":
            self.stats_label.config(text=f"Số phiên (theo {self.format_time(self.target_seconds)}): {done_sessions}")
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            secs = total_seconds % 60
            if hours > 0:
                text = f"Tổng thời gian đã đọc: {hours} giờ {minutes} phút {secs} giây"
            else:
                text = f"Tổng thời gian đã đọc: {minutes} phút {secs} giây"
            self.stats_label.config(text=text)

    def toggle_display_mode(self):
        if self.display_mode == "sessions":
            self.display_mode = "total_time"
            self.toggle_mode_btn.config(text="Chuyển sang số phiên")
            self.sessions_frame.pack_forget()
        else:
            self.display_mode = "sessions"
            self.toggle_mode_btn.config(text="Chuyển sang tổng thời gian")
            self.sessions_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
        self.update_stats_label()

    def save_notes(self):
        if self.current_book_index < 0:
            return
        notes = self.notes_text.get(1.0, tk.END).strip()
        book = self.books[self.current_book_index]
        if book.get("notes", "") != notes:
            book["notes"] = notes
            self.save_data()

    # -------------------- CHUYỂN MÀN HÌNH --------------------
    def show_home(self):
        # Lưu ghi chú của sách hiện tại nếu có
        if self.current_book_index >= 0:
            self.save_notes()
        # Lưu phiên nếu đang có thời gian
        if self.current_book_index >= 0 and self.timer_seconds > 0:
            self.save_current_session()
        else:
            if self.timer_running:
                self.reset_timer()
        self.detail_frame.pack_forget()
        self.refresh_home_books()
        self.home_frame.pack(fill=tk.BOTH, expand=True)

    def show_detail(self, book_index):
        # Lưu ghi chú của sách hiện tại trước khi chuyển
        if self.current_book_index >= 0:
            self.save_notes()
        # Lưu phiên nếu đang có thời gian (trước khi chuyển)
        if self.current_book_index >= 0 and self.timer_seconds > 0:
            self.save_current_session()
        elif self.timer_running:
            self.reset_timer()
        self.current_book_index = book_index
        self.home_frame.pack_forget()
        self.display_book(book_index)
        if self.display_mode == "sessions":
            self.sessions_frame.pack(anchor=tk.W, pady=2, fill=tk.X)
        else:
            self.sessions_frame.pack_forget()
        self.detail_frame.pack(fill=tk.BOTH, expand=True)

    # -------------------- ĐÓNG ỨNG DỤNG --------------------
    def on_closing(self):
        # Lưu ghi chú hiện tại
        if self.current_book_index >= 0:
            self.save_notes()
        # Lưu phiên nếu có
        if self.current_book_index >= 0 and self.timer_seconds > 0:
            self.save_current_session()
        elif self.timer_running:
            self.reset_timer()
        self.save_data()
        self.save_config()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = ReadingTrackerApp(root)
    root.mainloop()
