import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import re
import json

CONFIG_PATH = "last_sheet_config.json"

def load_last_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_last_config(sheet_url, key_path):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump({"sheet_url": sheet_url, "key_path": key_path}, f)
    except Exception:
        pass

def get_sheet_info():
    last_config = load_last_config()
    root = TkinterDnD.Tk()
    root.title("Google Sheets 정보 입력")
    root.geometry("500x180+300+300")
    root.resizable(False, False)

    tk.Label(root, text="구글 스프레드시트 공유 URL을 입력하세요:").pack(pady=(10,0))
    url_var = tk.StringVar(value=last_config.get("sheet_url", ""))
    url_entry = tk.Entry(root, textvariable=url_var, width=60)
    url_entry.pack(pady=5)

    tk.Label(root, text="인증 키 파일 경로(.json):").pack(pady=(10,0))
    key_path_var = tk.StringVar(value=last_config.get("key_path", ""))
    key_entry = tk.Entry(root, textvariable=key_path_var, width=60)
    key_entry.pack(pady=5)

    # 드래그&드롭 지원
    def drop(event):
        path = event.data.strip('{}')
        key_entry.delete(0, tk.END)
        key_entry.insert(0, path)
    key_entry.drop_target_register(DND_FILES)
    key_entry.dnd_bind('<<Drop>>', drop)

    def on_submit():
        sheet_url = url_var.get().strip()
        key_path = key_path_var.get().strip()
        if sheet_url and key_path and os.path.exists(key_path):
            save_last_config(sheet_url, key_path)
            root.sheet_url = sheet_url
            root.key_path = key_path
            root.destroy()
        else:
            tk.messagebox.showerror("입력 오류", "모든 정보를 올바르게 입력하세요.")

    tk.Button(root, text="확인", command=on_submit, width=20).pack(pady=20)
    root.mainloop()
    return getattr(root, "sheet_url", ""), getattr(root, "key_path", "")

def tc_remote_controller(tc_list, sheet):
    root = tk.Tk()
    root.title("TC 리모콘")
    root.geometry("900x600+400+200")
    root.attributes('-topmost', True)
    root.resizable(True, True)

    idx = [0]
    total = len(tc_list)

    result_options = ["Not Test", "Pass", "Fail", "N/A", "Blocked"]
    browser_names = ["Chrome", "Edge", "Firefox"]
    browser_headers = {
        "Chrome": "Result\n(PC - chrome)",
        "Edge": "Result\n(PC - edge)",
        "Firefox": "Result\n(PC - firefox)"
    }

    browser_vars = {b: tk.BooleanVar(value=True) for b in browser_names}
    result_vars = {b: tk.StringVar(value="Not Test") for b in browser_names}
    qa_comment_var = tk.StringVar()
    sync_var = tk.BooleanVar(value=False)

    last_tc = {}

    # 결과값과 QA Comment 미리 로드
    all_values = sheet.get_all_values()
    header = all_values[15]
    data_rows = all_values[16:]
    col_idx = {name: idx for idx, name in enumerate(header)}
    result_cache = [{} for _ in range(len(data_rows))]
    qa_comment_cache = [""] * len(data_rows)

    def get_tc_status(i):
        val = result_cache[i]["Chrome"]
        return val if val else "Not Test"

    for i, row in enumerate(data_rows):
        for b in browser_names:
            col_name = browser_headers[b]
            idx_ = col_idx.get(col_name)
            val = row[idx_] if idx_ is not None and idx_ < len(row) else "Not Test"
            result_cache[i][b] = val if val else "Not Test"
        idx_qa = col_idx.get("QA Comment")
        qa_val = row[idx_qa] if idx_qa is not None and idx_qa < len(row) else ""
        qa_comment_cache[i] = qa_val if qa_val else ""

    # 전체 프레임
    main_frame = tk.Frame(root)
    main_frame.pack(fill=tk.BOTH, expand=1)

    # 왼쪽 메인 UI
    left_frame = tk.Frame(main_frame)
    left_frame.pack(side="left", fill=tk.BOTH, expand=1)

    tc_text_widget = tk.Text(left_frame, width=60, height=10, font=("Arial", 12), wrap="word")
    tc_text_widget.pack(padx=20, pady=20, fill=tk.X)

    def load_tc(i):
        nonlocal last_tc
        if 0 <= i < total:
            tc = tc_list[i]
            for key in ["No", "대분류", "중분류", "소분류", "테스트 조건", "실행 순서", "기대 결과"]:
                if not tc.get(key):
                    tc[key] = last_tc.get(key, "")
                else:
                    last_tc[key] = tc[key]
            tc_text_widget.config(state="normal")
            tc_text_widget.delete("1.0", tk.END)
            tc_text_widget.insert(tk.END,
                f"TC No: {tc.get('No')}\n"
                f"대분류: {tc.get('대분류')}\n"
                f"중분류: {tc.get('중분류')}\n"
                f"소분류: {tc.get('소분류')}\n"
                f"테스트 조건: {tc.get('테스트 조건')}\n"
                f"실행 순서: {tc.get('실행 순서')}\n"
                f"기대 결과: {tc.get('기대 결과')}\n"
            )
            tc_text_widget.config(state="disabled")
            for b in browser_names:
                result_vars[b].set(result_cache[i][b])
            qa_comment_var.set(qa_comment_cache[i])
            if tc_no_listbox.winfo_ismapped():
                tc_no_listbox.selection_clear(0, tk.END)
                tc_no_listbox.selection_set(i)
                tc_no_listbox.activate(i)
        else:
            tc_text_widget.config(state="normal")
            tc_text_widget.delete("1.0", tk.END)
            tc_text_widget.insert(tk.END, "모든 TC가 완료되었습니다.")
            tc_text_widget.config(state="disabled")
            for b in browser_names:
                result_vars[b].set("")
            qa_comment_var.set("")

    def save_result():
        i = idx[0]
        if 0 <= i < total:
            row_num = i + 17
            for b in browser_names:
                if browser_vars[b].get():
                    col_obj = sheet.find(browser_headers[b])
                    if col_obj is None:
                        print(f"헤더에서 {browser_headers[b]} 컬럼을 찾을 수 없습니다.")
                        continue
                    sheet.update_cell(row_num, col_obj.col, result_vars[b].get())
                    result_cache[i][b] = result_vars[b].get()
            col_obj = sheet.find("QA Comment")
            if col_obj:
                sheet.update_cell(row_num, col_obj.col, qa_comment_var.get())
                qa_comment_cache[i] = qa_comment_var.get()
            else:
                print("헤더에서 QA Comment 컬럼을 찾을 수 없습니다.")
            update_tc_no_listbox()

    def prev_tc():
        if idx[0] > 0:
            idx[0] -= 1
            load_tc(idx[0])

    def next_tc():
        if idx[0] < total - 1:
            idx[0] += 1
            load_tc(idx[0])

    def on_sync_change(*_):
        if sync_var.get():
            def sync_all(varname, *_):
                val = result_vars[varname].get()
                for b in browser_names:
                    result_vars[b].set(val)
            for b in browser_names:
                result_vars[b].trace_add("write", lambda *_ , b=b: sync_all(b))
        else:
            for b in browser_names:
                result_vars[b].trace_vdelete("write", result_vars[b]._trace_id) if hasattr(result_vars[b], "_trace_id") else None

    sync_cb = tk.Checkbutton(left_frame, text="Result 동시 변경", variable=sync_var, command=on_sync_change)
    sync_cb.pack(anchor="w", padx=20)

    frame = tk.Frame(left_frame)
    frame.pack(pady=10, anchor="w")
    option_menus = {}
    for b in browser_names:
        cb = tk.Checkbutton(frame, text=b, variable=browser_vars[b])
        cb.pack(side="left", padx=8)
        menu = tk.OptionMenu(frame, result_vars[b], *result_options)
        menu.pack(side="left", padx=3)
        option_menus[b] = menu

    tk.Label(left_frame, text="QA Comment:", font=("Arial", 11)).pack(anchor="w", padx=20)
    tk.Entry(left_frame, textvariable=qa_comment_var, width=60).pack(pady=5, anchor="w", padx=20)

    btn_frame = tk.Frame(left_frame)
    btn_frame.pack(pady=15, anchor="w", padx=20)
    tk.Button(btn_frame, text="이전 TC", command=prev_tc, width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="저장", command=save_result, width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="다음 TC", command=next_tc, width=10).pack(side="left", padx=10)

    # 오른쪽 TC NO 리스트 프레임
    right_frame = tk.Frame(main_frame)
    right_frame.pack(side="right", fill=tk.Y)

    # 리스트 박스
    tc_no_listbox = tk.Listbox(right_frame, width=20, height=30)
    tc_no_listbox.pack(fill=tk.BOTH, expand=1, padx=(10,0), pady=(20,0))

    def update_tc_no_listbox():
        tc_no_listbox.delete(0, tk.END)
        for i, tc in enumerate(tc_list):
            status = get_tc_status(i)
            display = f"{tc.get('No','')} [{status}]"
            tc_no_listbox.insert(tk.END, display)

    def on_tc_no_select(event):
        sel = tc_no_listbox.curselection()
        if sel:
            idx[0] = sel[0]
            load_tc(idx[0])

    tc_no_listbox.bind("<<ListboxSelect>>", on_tc_no_select)

    # 리스트 숨기기/보이기 버튼 (root 우측 하단에 고정)
    def toggle_listbox():
        if right_frame.winfo_ismapped():
            right_frame.pack_forget()
            toggle_btn.config(text="TC 리스트 열기")
        else:
            right_frame.pack(side="right", fill=tk.Y)
            toggle_btn.config(text="TC 리스트 닫기")

    # 버튼을 root 우측 하단에 고정
    toggle_btn = tk.Button(root, text="TC 리스트 닫기", command=toggle_listbox)
    toggle_btn.place(relx=0.0, rely=1.0, anchor="sw", x=-20, y=-20)  # 창 우측 하단에 고정

    update_tc_no_listbox()
    load_tc(idx[0])
    root.mainloop()

if __name__ == "__main__":
    SHEET_URL, KEY_PATH = get_sheet_info()
    print("스프레드시트 URL:", SHEET_URL)
    print("인증키 경로:", KEY_PATH)

    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', SHEET_URL)
    sheet_id = match.group(1) if match else SHEET_URL
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(KEY_PATH, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    worksheet = sheet.get_worksheet(0)
    actual_headers = worksheet.row_values(16)
    print("실제 헤더:", actual_headers)
    tc_list = worksheet.get_all_records(expected_headers=actual_headers, head=16)

    tc_remote_controller(tc_list, worksheet)