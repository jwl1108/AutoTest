from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from flask import Flask, request
import threading
import time

app = Flask(__name__)

driver_chrome_main = None
driver_chrome_follow = None
driver_firefox = None
driver_edge = None

def get_driver(browser_name):
    browser_name = browser_name.lower()
    if browser_name == "chrome":
        service = ChromeService(executable_path=ChromeDriverManager().install())
        return webdriver.Chrome(service=service)
    elif browser_name == "firefox":
        options = FirefoxOptions()
        # Firefox 설치 경로를 본인 PC에 맞게 변경하세요
        options.binary_location = r"C:\Program Files\Mozilla Firefox\firefox.exe"
        service = FirefoxService(executable_path=GeckoDriverManager().install())
        return webdriver.Firefox(service=service, options=options)
    elif browser_name == "edge":
        # Edge는 미리 받아둔 드라이버 직접 경로 지정 (webdriver_manager 미사용)
        service = EdgeService(executable_path=r"D:\Browser\drivers\msedgedriver.exe")
        return webdriver.Edge(service=service)
    else:
        raise ValueError("지원하지 않는 브라우저입니다.")

def find_and_click(driver, data, browser_name):
    try:
        url = data.get('url')
        id_ = data.get('id')
        class_ = data.get('class')
        text = data.get('text')

        if not driver:
            print(f"🔥 {browser_name} 드라이버가 준비되지 않았습니다.")
            return

        driver.get(url)
        time.sleep(2)  # 페이지 로딩 대기 (WebDriverWait 사용 권장)

        element = None
        if id_:
            try:
                element = driver.find_element(By.ID, id_)
            except:
                pass

        if not element and class_:
            try:
                class_name = class_.split()[0]
                element = driver.find_element(By.CLASS_NAME, class_name)
            except:
                pass

        if not element and text:
            try:
                element = driver.find_element(By.XPATH, f"//*[text()='{text}']")
            except:
                pass

        if element:
            element.click()
            print(f"✅ {browser_name} 자동 클릭 완료")
        else:
            print(f"❌ {browser_name}에서 요소를 찾지 못했습니다")
    except Exception as e:
        print(f"🔥 {browser_name} 오류: {e}")

def click_in_chrome_follow(data):
    global driver_chrome_follow
    if driver_chrome_follow is None:
        driver_chrome_follow = get_driver("chrome")
        driver_chrome_follow.maximize_window()
        driver_chrome_follow.get(data.get("url", "about:blank"))
    find_and_click(driver_chrome_follow, data, "Chrome (Follow)")

def click_in_firefox(data):
    global driver_firefox
    if driver_firefox is None:
        driver_firefox = get_driver("firefox")
        driver_firefox.maximize_window()
        driver_firefox.get(data.get("url", "about:blank"))
    find_and_click(driver_firefox, data, "Firefox")

def click_in_edge(data):
    global driver_edge
    if driver_edge is None:
        driver_edge = get_driver("edge")
        driver_edge.maximize_window()
        driver_edge.get(data.get("url", "about:blank"))
    find_and_click(driver_edge, data, "Edge")

@app.route('/click', methods=['POST'])
def handle_click():
    data = request.json
    threading.Thread(target=click_in_chrome_follow, args=(data,)).start()
    threading.Thread(target=click_in_firefox, args=(data,)).start()
    threading.Thread(target=click_in_edge, args=(data,)).start()
    return 'OK', 200

if __name__ == '__main__':
    test_url = input("테스트할 URL을 입력하세요: ").strip()

    # 1) 수동 조작용 Chrome
    driver_chrome_main = get_driver("chrome")
    driver_chrome_main.maximize_window()
    driver_chrome_main.get(test_url)

    # 2) 자동 클릭용 Chrome
    driver_chrome_follow = get_driver("chrome")
    driver_chrome_follow.maximize_window()
    driver_chrome_follow.get(test_url)

    # 3) Firefox
    driver_firefox = get_driver("firefox")
    driver_firefox.maximize_window()
    driver_firefox.get(test_url)

    # 4) Edge (미리 받아둔 드라이버 사용)
    driver_edge = get_driver("edge")
    driver_edge.maximize_window()
    driver_edge.get(test_url)

    # 크롬 수동 조작용에 클릭 이벤트 감지 JS 삽입
    js_code = """
    document.addEventListener('click', function(e) {
        const elementInfo = {
            tag: e.target.tagName,
            id: e.target.id,
            class: e.target.className,
            text: e.target.innerText,
            url: window.location.href
        };
        fetch('http://localhost:5000/click', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(elementInfo)
        });
    });
    """
    driver_chrome_main.execute_script(js_code)

    print('서버 실행 중... http://localhost:5000')
    app.run(port=5000)
