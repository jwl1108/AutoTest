import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import re

def get_sheet_by_url_and_json():
    root = tk.Tk()
    root.withdraw()
    # credentials.json 파일 선택
    json_path = filedialog.askopenfilename(
        title="구글 인증 JSON 파일 선택",
        filetypes=[("JSON 파일", "*.json")]
    )
    if not json_path:
        messagebox.showerror("오류", "구글 인증 JSON 파일을 선택해야 합니다.")
        root.destroy()
        return None
    # 구글 시트 링크 입력
    url = simpledialog.askstring("구글 시트 링크 입력", "구글 시트 링크를 입력하세요:")
    if not url:
        messagebox.showerror("오류", "구글 시트 링크를 입력해야 합니다.")
        root.destroy()
        return None
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_url(url).sheet1
        root.destroy()
        return sheet
    except Exception as e:
        messagebox.showerror("오류", f"구글 시트 열기 실패: {e}")
        root.destroy()
        return None

def run_tc(tc_rows):
    driver = webdriver.Chrome()
    driver.maximize_window()
    for row in tc_rows[16:]:  # G17부터 시작
        실행순서 = row[6] if len(row) > 6 else ""
        for line in 실행순서.split('\n'):
            found = False
            for btn_text in extract_click_target(line):
                btns = driver.find_elements(By.TAG_NAME, "button")
                btn = next((b for b in btns if btn_text in b.text), None)
                if btn:
                    btn.click()
                    print(f"'{btn_text}' 버튼 클릭 성공")
                    time.sleep(1)
                    found = True
                else:
                    print(f"예외: '{btn_text}' 버튼을 찾지 못함 (텍스트가 없거나 이미지 버튼일 수 있음)")
            if not found and not list(extract_click_target(line)):
                print(f"예외: 클릭 대상 문구를 추출하지 못함 → '{line}'")
    driver.quit()

def extract_button_text(line):
    # 다양한 버튼 클릭 문구 패턴을 한 번에 추출
    patterns = [
        r"\[([^\]]+)\]\s*(?:탭\s*)?버튼",         # [텍스트] 버튼, [텍스트] 탭 버튼
        r"([^\[\]\s]+)\s*(?:탭\s*)?버튼",        # 텍스트 버튼, 텍스트 탭 버튼
        r"([^\[\]\s]+)\s*버튼\s*클릭",           # 텍스트 버튼 클릭
        r"([^\[\]\s]+)\s*탭\s*버튼\s*클릭",      # 텍스트 탭 버튼 클릭
        r"([^\[\]\s]+)\s*버튼을\s*누른다",       # 텍스트 버튼을 누른다
        r"([^\[\]\s]+)\s*버튼을\s*선택",         # 텍스트 버튼을 선택
    ]
    for pat in patterns:
        m = re.findall(pat, line)
        for btn_text in m:
            if btn_text:
                yield btn_text

def save_button_texts(tc_rows, output_path="button_texts.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        for row in tc_rows[16:]:  # G17부터 시작
            실행순서 = row[6] if len(row) > 6 else ""
            for line in 실행순서.split('\n'):
                for btn_text in extract_button_text(line):
                    f.write(f"{btn_text}\n")
    print(f"버튼 문구 추출 완료: {output_path}")

def extract_click_target(line):
    # "버튼 클릭", "탭 버튼 클릭", "영역 클릭", "메뉴 클릭", "토글 클릭" 등 앞의 전체 문구 추출 (대괄호 패턴 제거)
    patterns = [
        r"(.+?)\s*버튼\s*클릭",                        # 여러 단어 버튼 클릭
        r"(.+?)\s*탭\s*버튼\s*클릭",                   # 여러 단어 탭 버튼 클릭
        r"(.+?)\s*영역\s*클릭",                        # 여러 단어 영역 클릭
        r"(.+?)\s*메뉴\s*클릭",                        # 여러 단어 메뉴 클릭
        r"(.+?)\s*토글\s*클릭",                        # 여러 단어 토글 클릭
    ]
    for pat in patterns:
        for m in re.findall(pat, line):
            # 여러 단어 추출
            yield m.strip()

def save_click_targets(tc_rows, output_path="click_targets.txt"):
    with open(output_path, "w", encoding="utf-8") as f:
        for row in tc_rows[16:]:  # G17부터 시작
            실행순서 = row[6] if len(row) > 6 else ""
            for line in 실행순서.split('\n'):
                for target in extract_click_target(line):
                    f.write(f"{target}\n")
    print(f"클릭 대상 문구 추출 완료: {output_path}")

if __name__ == "__main__":
    sheet = get_sheet_by_url_and_json()
    if sheet is None:
        input("프로그램을 종료하려면 엔터를 누르세요.")
        exit(1)
    tc_rows = sheet.get_all_values()[1:]  # 첫 행은 헤더라고 가정
    save_click_targets(tc_rows)