import tkinter as tk
from tkinter import filedialog, messagebox
import requests
import os

def download_file(url, save_path):
    try:
        response = requests.get(url)
        response.raise_for_status()
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    except Exception as e:
        messagebox.showerror("다운로드 오류", f"다운로드 실패: {e}")
        return False

def on_download():
    url = url_entry.get().strip()
    if not url:
        messagebox.showerror("오류", "다운로드할 server.py의 URL을 입력하세요.")
        return
    save_path = filedialog.asksaveasfilename(defaultextension=".py", initialfile="server.py")
    if not save_path:
        return
    if download_file(url, save_path):
        messagebox.showinfo("완료", f"다운로드 성공!\n{save_path}")

root = tk.Tk()
root.title("server.py 설치 프로그램")
tk.Label(root, text="server.py 다운로드 URL:").pack(padx=10, pady=5)
url_entry = tk.Entry(root, width=60)
url_entry.pack(padx=10, pady=5)
tk.Button(root, text="다운로드", command=on_download, width=20).pack(pady=10)
root.mainloop()