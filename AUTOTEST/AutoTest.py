import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
import tkinter as tk
from tkinterdnd2 import DND_FILES, TkinterDnD
import os
import re

# Google Sheets 인증 및 시트 연결
def connect_google_sheet(sheet_name, worksheet_name, key_path):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(key_path, scope)
    client = gspread.authorize(creds)
    sheet = client.open(sheet_name).worksheet(worksheet_name)
    return sheet

# Google Sheets에서 TC 읽기
def load_tc_sheet(sheet):
    records = sheet.get_all_records()
    return records

# Google Sheets에 결과 기록
def save_tc_result(sheet, results):
    for idx, result in enumerate(results, start=2):  # 1행은 헤더, 2행부터 데이터
        sheet.update_cell(idx, sheet.find("Result").col, result["Result"])
        sheet.update_cell(idx, sheet.find("Time").col, result["Time"])

def check_pre_condition(driver, pre_condition):
    # "로그인"만 수동 안내, "미로그인"은 자동 진행
    if "로그인" in pre_condition:
        print(f"로그인 상태가 필요한 테스트입니다: {pre_condition}")
        input("로그인 후 Enter를 누르세요.")
    elif "미로그인" in pre_condition:
        print("미로그인 상태가 필요한 테스트입니다. 현재 상태로 진행합니다.")
        # 필요시 자동 로그아웃 코드 추가 가능
    elif "페이지 노출" in pre_condition:
        print("페이지 노출 조건입니다. 현재 URL:", driver.current_url)
        input("페이지가 맞으면 Enter를 누르세요.")
    else:
        print(f"자동 준비 조건: {pre_condition}")
        # 필요시 자동화 코드 추가

# TC 실행 및 결과 기록
def run_tc_automation(tc_list, sync):
    results = []
    for row in tc_list:
        tc_no = row.get("No")
        major = row.get("대분류")
        middle = row.get("중분류")
        minor = row.get("소분류")
        pre_condition = row.get("테스트 조건")
        exec_steps = row.get("실행 순서")
        expect = row.get("기대 결과")

        print(f"\n[TC {tc_no}] {major}/{middle}/{minor}")
        print(f"테스트 조건: {pre_condition}")

        check_pre_condition(sync.drivers[0] if sync else driver, pre_condition)

        print(f"실행 순서: {exec_steps}")
        print(f"기대 결과: {expect}")

        try:
            steps = [s.strip() for s in exec_steps.split('\n') if s.strip()]
            for step in steps:
                print(f"실행: {step}")
                # 실제 자동화는 step에 selector/action 정보가 있으면 자동 실행

            # 결과 입력 부분 제거!
            # result = input(f"기대 결과를 확인 후 Pass/Fail을 입력하세요 (TC {tc_no}): ").strip()
            result = None  # 팝업에서 입력받으므로 여기서는 None
        except Exception as e:
            print(f"TC 실패: {e}")
            result = "Fail"

        results.append({
            "Result": result,
            "Time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    return results

def get_sheet_info():
    root = TkinterDnD.Tk()
    root.title("Google Sheets 정보 입력")
    root.geometry("500x180+300+300")
    root.resizable(False, False)

    tk.Label(root, text="구글 스프레드시트 공유 URL을 입력하세요:").pack(pady=(10,0))
    url_var = tk.StringVar()
    url_entry = tk.Entry(root, textvariable=url_var, width=60)
    url_entry.pack(pady=5)

    tk.Label(root, text="인증 키 파일 경로(.json):").pack(pady=(10,0))
    key_path_var = tk.StringVar()
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
            root.sheet_url = sheet_url
            root.key_path = key_path
            root.destroy()
        else:
            tk.messagebox.showerror("입력 오류", "모든 정보를 올바르게 입력하세요.")

    tk.Button(root, text="확인", command=on_submit, width=20).pack(pady=20)
    root.mainloop()
    return getattr(root, "sheet_url", ""), getattr(root, "key_path", "")

# TC 리모컨 팝업
def tc_remote_controller(tc_list, sheet):
    root = tk.Tk()
    root.title("TC 리모콘")
    root.geometry("500x470+400+200")
    root.attributes('-topmost', True)
    root.resizable(False, False)  # 창 크기 고정

    idx = [0]
    total = len(tc_list)

    result_options = ["Not Test", "Pass", "Fail", "N/A", "Blocked"]
    browser_names = ["Chrome", "Edge", "Firefox"]
    browser_vars = {b: tk.BooleanVar(value=True) for b in browser_names}
    result_vars = {b: tk.StringVar(value="Not Test") for b in browser_names}
    qa_comment_var = tk.StringVar()
    sync_var = tk.BooleanVar(value=False)

    # TC 내용 표시용 Text 위젯
    tc_text_widget = tk.Text(root, width=60, height=10, font=("Arial", 12), wrap="word")
    tc_text_widget.pack(pady=20, padx=20)
    tc_text_widget.config(state="disabled")

    # 병합 셀 내용 보존용
    last_tc = {}

    def load_tc(i):
        nonlocal last_tc
        if 0 <= i < total:
            tc = tc_list[i]
            # 병합 셀 값이 비어 있으면 이전 값 사용
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
            row_num = i + 17
            for b in browser_names:
                try:
                    val = sheet.cell(row_num, sheet.find(f"Result\n(PC - {b.lower()})").col).value
                except:
                    val = tc.get(f"Result\n(PC - {b.lower()})", "Not Test")
                result_vars[b].set(val if val else "Not Test")
            try:
                qa_val = sheet.cell(row_num, sheet.find("QA Comment").col).value
            except:
                qa_val = tc.get("QA Comment", "")
            qa_comment_var.set(qa_val if qa_val else "")
        else:
            tc_text_widget.config(state="normal")
            tc_text_widget.delete("1.0", tk.END)
            tc_text_widget.insert(tk.END, "모든 TC가 완료되었습니다.")
            tc_text_widget.config(state="disabled")
            for b in browser_names:
                result_vars[b].set("")
            qa_comment_var.set("")

    browser_headers = {
        "Chrome": "Result\n(PC - chrome)",
        "Edge": "Result\n(PC - edge)",
        "Firefox": "Result\n(PC - firefox)"
    }

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
            col_obj = sheet.find("QA Comment")
            if col_obj:
                sheet.update_cell(row_num, col_obj.col, qa_comment_var.get())
            else:
                print("헤더에서 QA Comment 컬럼을 찾을 수 없습니다.")
            load_tc(i)

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

    sync_cb = tk.Checkbutton(root, text="Result 동시 변경", variable=sync_var, command=on_sync_change)
    sync_cb.pack(pady=(0,5))

    frame = tk.Frame(root)
    frame.pack(pady=10)
    option_menus = {}
    for b in browser_names:
        cb = tk.Checkbutton(frame, text=b, variable=browser_vars[b])
        cb.pack(side="left", padx=8)
        menu = tk.OptionMenu(frame, result_vars[b], *result_options)
        menu.pack(side="left", padx=3)
        option_menus[b] = menu

    tk.Label(root, text="QA Comment:", font=("Arial", 11)).pack(pady=(20,0))
    tk.Entry(root, textvariable=qa_comment_var, width=60).pack(pady=5)

    btn_frame = tk.Frame(root)
    btn_frame.pack(pady=15)
    tk.Button(btn_frame, text="이전 TC", command=prev_tc, width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="저장", command=save_result, width=10).pack(side="left", padx=10)
    tk.Button(btn_frame, text="다음 TC", command=next_tc, width=10).pack(side="left", padx=10)

    load_tc(idx[0])
    root.mainloop()

# 사용 예시
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
    worksheet = sheet.get_worksheet(0)  # 첫 번째 워크시트 사용
    actual_headers = worksheet.row_values(16)
    print("실제 헤더:", actual_headers)
    tc_list = worksheet.get_all_records(expected_headers=actual_headers, head=16)

    browser_headers = {
        "Chrome": "Result\n(PC - chrome)",
        "Edge": "Result\n(PC - edge)",
        "Firefox": "Result\n(PC - firefox)"
    }

    tc_remote_controller(tc_list, worksheet)  # sheet → worksheet로 변경