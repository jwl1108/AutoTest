import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from selenium import webdriver
from selenium.webdriver.common.by import By

# Google Sheets 인증 및 시트 연결
def connect_google_sheet(sheet_name, worksheet_name):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
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

# TC 실행 및 결과 기록
def run_tc_automation(tc_list, sync):
    results = []
    for row in tc_list:
        tc_id = row.get("TC_ID")
        action = row.get("Action")
        selector = row.get("Selector")
        value = row.get("Value", "")
        expect = row.get("Expect", "")
        manual = row.get("Manual", False)

        print(f"[{tc_id}] {action} {selector} {value}")

        try:
            if manual:
                input(f"수동 TC입니다. TC_ID={tc_id} 수행 후 Enter를 눌러주세요.")
                result = "Manual"
            else:
                if action == "click":
                    sync.click(selector)
                elif action == "input":
                    sync.input(selector, value)
                elif action == "goto":
                    sync.goto(value)
                result = "Pass"
        except Exception as e:
            print(f"TC 실패: {e}")
            result = "Fail"

        results.append({
            "TC_ID": tc_id,
            "Result": result,
            "Time": time.strftime("%Y-%m-%d %H:%M:%S")
        })
    return results

if __name__ == "__main__":
    # Google Sheets 정보
    SHEET_NAME = "테스트케이스시트명"
    WORKSHEET_NAME = "Sheet1"

    # 시트 연결 및 TC 로드
    sheet = connect_google_sheet(SHEET_NAME, WORKSHEET_NAME)
    tc_list = load_tc_sheet(sheet)

    # 브라우저 동기화 객체 생성 (이미 구현된 도구 활용)
    # sync = BrowserSync([...])  # Chrome, Firefox, Edge 등

    # 예시: 단일 브라우저로 테스트 (동기화 도구로 교체 가능)
    sync = None
    driver = webdriver.Chrome()
    driver.get("https://테스트주소")
    # sync = BrowserSync([driver])  # 실제 동기화 도구로 교체

    # TC 자동화 실행 및 결과 기록
    results = run_tc_automation(tc_list, sync)
    save_tc_result(sheet, results)

    # 브라우저 종료
    driver.quit()