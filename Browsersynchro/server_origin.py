from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from flask import Flask, request
from flask_cors import CORS
import threading
import time
import tkinter as tk
from tkinter import messagebox
from selenium.webdriver.chrome.options import Options
import sys
import os
from selenium.webdriver.common.action_chains import ActionChains

app = Flask(__name__)
CORS(app)

driver_chrome_main = None
driver_chrome_follow = None
driver_firefox = None
driver_edge = None

def find_and_click(driver, data, browser_name):
    try:
        path = data.get('path')
        print(f"🔎 클릭 경로(path): {path}")
        element = None

        if path and isinstance(path, list) and len(path) > 0:
            parent = driver.find_element(By.TAG_NAME, "body")
            hover_targets = []
            for step in path:
                tag = step.get('tag')
                class_name = step.get('class')
                idx = step.get('index')
                class_names = class_name.split() if class_name else []
                def class_match(el):
                    el_classes = el.get_attribute('class').split()
                    return all(c in el_classes for c in class_names) if class_names else True
                children = parent.find_elements(By.XPATH, "./*")
                siblings = [el for el in children if el.tag_name.upper() == tag]
                if 0 <= idx < len(siblings):
                    parent = siblings[idx]
                    hover_targets.append(parent)
                else:
                    parent = None
                    break
            element = parent

            # 상위 메뉴들에 순차적으로 hover
            if len(hover_targets) > 1:
                actions = ActionChains(driver)
                for hover_el in hover_targets[:-1]:  # 마지막은 클릭 대상이므로 제외
                    try:
                        actions.move_to_element(hover_el).perform()
                        time.sleep(0.2)  # 메뉴가 열릴 시간 대기
                    except Exception as e:
                        print(f"⚠️ Hover 실패: {e}")

        # 이하 기존 id/class/text 탐색 로직 (path가 없을 때만)
        id_ = data.get('id')
        class_ = data.get('class')
        text = data.get('text')

        if not element and id_:
            try:
                element = WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.ID, id_))
                )
            except:
                pass

        if not element and class_:
            try:
                class_name = class_.split()[0]
                elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, class_name))
                )
                if elements:
                    element = elements[0]
            except:
                pass

        if not element and text:
            try:
                elements = WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.XPATH, f"//*[text()='{text}']"))
                )
                if elements:
                    element = elements[0]
            except:
                pass

        if element:
            try:
                # 내부 button, a, span, i 등 클릭 시도 (우선순위: button > a > span > i)
                for sub_tag in ["button", "a", "span", "i"]:
                    sub_elements = element.find_elements(By.TAG_NAME, sub_tag)
                    if sub_elements:
                        try:
                            sub_elements[0].click()
                            print(f"✅ {browser_name} 내부 {sub_tag} 클릭 완료")
                            return
                        except Exception as e:
                            print(f"🔥 {browser_name} 내부 {sub_tag} 클릭 오류: {e}")
                # 그래도 안 되면 element 자체 클릭
                try:
                    element.click()
                    print(f"✅ {browser_name} 자체 클릭 완료")
                except Exception as e:
                    print(f"🔥 {browser_name} 자체 클릭 오류: {e}")
            except Exception as e:
                print(f"🔥 {browser_name} 클릭 오류: {e}")
        else:
            print(f"❌ {browser_name}에서 요소를 찾지 못했습니다")

    except Exception as e:
        print(f"🔥 {browser_name} 오류: {e}")

def click_in_chrome_follow(data):
    global driver_chrome_follow
    if driver_chrome_follow is None:
        service = ChromeService(executable_path=ChromeDriverManager().install())
        driver_chrome_follow = webdriver.Chrome(service=service)
        driver_chrome_follow.maximize_window()
    find_and_click(driver_chrome_follow, data, "Chrome (Follow)")

def click_in_firefox(data):
    global driver_firefox
    if driver_firefox:
        find_and_click(driver_firefox, data, "Firefox")

def click_in_edge(data):
    global driver_edge
    if driver_edge:
        find_and_click(driver_edge, data, "Edge")

@app.route('/click', methods=['POST'])
def handle_click():
    data = request.json
    print(f"🔔 클릭 이벤트 수신: {data}")

    threading.Thread(target=click_in_chrome_follow, args=(data,)).start()
    threading.Thread(target=click_in_firefox, args=(data,)).start()
    threading.Thread(target=click_in_edge, args=(data,)).start()

    return 'OK', 200

@app.route('/event', methods=['POST'])
def handle_event():
    data = request.json
    action = data.get('action')
    print(f"🔔 이벤트 수신: {data}")

    threads = []
    if action == 'scroll':
        threads.append(threading.Thread(target=scroll_in_all, args=(data,)))
    elif action == 'click':
        if driver_firefox:
            threads.append(threading.Thread(target=click_in_firefox, args=(data,)))
        if driver_edge:
            threads.append(threading.Thread(target=click_in_edge, args=(data,)))
    elif action == 'input':
        if driver_firefox:
            threads.append(threading.Thread(target=input_in_firefox, args=(data,)))
        if driver_edge:
            threads.append(threading.Thread(target=input_in_edge, args=(data,)))
    for t in threads:
        t.start()
    return 'OK', 200

def scroll_in_all(data):
    scroll_x = data.get('scrollX', 0)
    scroll_y = data.get('scrollY', 0)
    drivers = []
    if driver_firefox:
        drivers.append((driver_firefox, "Firefox"))
    if driver_edge:
        drivers.append((driver_edge, "Edge"))
    for driver, name in drivers:
        try:
            driver.execute_script(f"window.scrollTo({int(scroll_x)}, {int(scroll_y)});")
            print(f"✅ {name} 스크롤 위치 이동: x={scroll_x}, y={scroll_y}")
        except Exception as e:
            print(f"🔥 {name} 스크롤 오류: {e}")

def inject_js(driver):
    # 클릭 + 스크롤 감지 JS 코드
    js_code = """
    if (!window.__browser_sync_injected) {
        window.__browser_sync_injected = true;

        // 클릭 이벤트
        document.addEventListener('click', function(e) {
            let path = [];
            let elem = e.target;
            while (elem && elem.tagName !== 'BODY') {
                const siblings = Array.from(elem.parentNode.children)
                    .filter(el => el.tagName === elem.tagName);
                path.unshift({
                    tag: elem.tagName,
                    class: elem.className,
                    index: siblings.indexOf(elem)
                });
                elem = elem.parentElement;
            }
            const elementInfo = {
                action: 'click',
                path: path,
                tag: e.target.tagName,
                id: e.target.id,
                class: e.target.className,
                text: e.target.innerText,
                url: window.location.href
            };
            fetch('http://localhost:5000/event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(elementInfo)
            });
        });

        // 키다운 이벤트
        document.addEventListener('keydown', function(e) {
            const keyInfo = {
                action: 'keydown',
                key: e.key,
                code: e.code,
                ctrlKey: e.ctrlKey,
                shiftKey: e.shiftKey,
                altKey: e.altKey,
                metaKey: e.metaKey
            };
            fetch('http://localhost:5000/event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(keyInfo)
            });
        });

        // 스크롤 이벤트
        let lastScrollX = window.scrollX;
        let lastScrollY = window.scrollY;
        window.addEventListener('scroll', function() {
            const nowX = window.scrollX;
            const nowY = window.scrollY;
            if (Math.abs(nowX - lastScrollX) > 10 || Math.abs(nowY - lastScrollY) > 10) {
                lastScrollX = nowX;
                lastScrollY = nowY;
                fetch('http://localhost:5000/event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        action: 'scroll',
                        url: window.location.href,
                        scrollX: nowX,
                        scrollY: nowY
                    })
                });
            }
        });

        // 입력값 변경 이벤트 (input, textarea)
        document.addEventListener('input', function(e) {
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                const inputInfo = {
                    action: 'input',
                    tag: e.target.tagName,
                    id: e.target.id,
                    class: e.target.className,
                    value: e.target.value,
                    url: window.location.href
                };
                fetch('http://localhost:5000/event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(inputInfo)
                });
            }
        });
    }
    """
    driver.execute_script(js_code)

def monitor_and_inject(driver):
    last_url = driver.current_url
    while True:
        time.sleep(1)
        if driver.current_url != last_url:
            inject_js(driver)
            last_url = driver.current_url

def close_all_and_exit():
    try:
        if driver_chrome_main:
            driver_chrome_main.quit()
        if driver_chrome_follow:
            driver_chrome_follow.quit()
        if driver_firefox:
            driver_firefox.quit()
        if driver_edge:
            driver_edge.quit()
    except Exception as e:
        print(f"브라우저 종료 중 오류: {e}")
    print("모든 브라우저와 서버를 종료합니다.")
    os._exit(0)  # 완전 종료 (sys.exit()보다 강력)

def get_user_input():
    def on_submit():
        url = url_entry.get().strip()
        use_firefox = var_firefox.get()
        use_edge = var_edge.get()
        if not url:
            messagebox.showerror("오류", "URL을 입력하세요.")
            return
        root.user_url = url
        root.use_firefox = use_firefox
        root.use_edge = use_edge
        root.destroy()  # "시작" 누르면 창 닫기

    root = tk.Tk()
    root.title("브라우저 동기화 테스트")

    tk.Label(root, text="테스트할 URL:").pack()
    url_entry = tk.Entry(root, width=40)
    url_entry.pack()
    url_entry.insert(0, "https://")  # 기본값

    var_firefox = tk.BooleanVar()
    var_edge = tk.BooleanVar()
    tk.Checkbutton(root, text="Firefox 따라하기", variable=var_firefox).pack(anchor='w')
    tk.Checkbutton(root, text="Edge 따라하기", variable=var_edge).pack(anchor='w')

    tk.Button(root, text="시작", command=on_submit).pack(pady=10)
    # 종료 버튼은 제거

    root.protocol("WM_DELETE_WINDOW", close_all_and_exit)

    root.mainloop()
    return root.user_url, root.use_firefox, root.use_edge

def input_in_firefox(data):
    input_to_driver(driver_firefox, data, "Firefox")

def input_in_edge(data):
    input_to_driver(driver_edge, data, "Edge")

def input_to_driver(driver, data, browser_name):
    try:
        # url = data.get('url')  # 이 줄은 더 이상 필요 없음
        id_ = data.get('id')
        class_ = data.get('class')
        value = data.get('value')
        if not driver:
            print(f"🔥 {browser_name} 드라이버가 준비되지 않았습니다.")
            return
        # driver.get(url)  # 이 줄을 제거!
        # WebDriverWait(driver, 10).until(lambda d: d.execute_script("return document.readyState") == "complete")
        element = None
        if id_:
            try:
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, id_))
                )
            except:
                pass
        if not element and class_:
            try:
                class_name = class_.split()[0]
                element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, class_name))
                )
            except:
                pass
        if element:
            element.clear()
            element.send_keys(value)
            print(f"✅ {browser_name} 입력값 동기화: {value}")
        else:
            print(f"❌ {browser_name}에서 입력 요소를 찾지 못했습니다")
    except Exception as e:
        print(f"🔥 {browser_name} 입력 오류: {e}")

def show_exit_window():
    exit_root = tk.Tk()
    exit_root.title("브라우저 동기화 종료")
    tk.Label(exit_root, text="프로그램을 종료하려면 아래 버튼을 누르세요.").pack(padx=20, pady=10)
    tk.Button(exit_root, text="종료", command=close_all_and_exit, width=20, height=2).pack(pady=10)
    exit_root.protocol("WM_DELETE_WINDOW", lambda: None)  # X버튼 비활성화(강제종료만 허용)
    exit_root.mainloop()

def auto_test_all_clickables(driver):
    clickable_tags = ["button", "a", "span", "li", "div"]
    # 모든 후보를 한 번에 수집 (중복 방지)
    elements = []
    for tag in clickable_tags:
        elements += driver.find_elements(By.TAG_NAME, tag)
    # 중복 제거
    elements = list(dict.fromkeys(elements))
    for idx, el in enumerate(elements):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.2)
            el_class = el.get_attribute('class')
            el_text = el.text
            print(f"[{idx}] {el.tag_name} class='{el_class}' text='{el_text}' 클릭 시도")
            el.click()
            time.sleep(0.5)
        except Exception as e:
            print(f"❌ 클릭 실패: {e}")

def find_clickable_by_class(driver, keywords=["menu", "btn", "nav", "header"]):
    all_elements = driver.find_elements(By.XPATH, "//*")
    candidates = []
    for el in all_elements:
        class_attr = el.get_attribute("class") or ""
        if any(kw in class_attr for kw in keywords):
            candidates.append(el)
    return candidates

if __name__ == '__main__':
    test_url, use_firefox, use_edge = get_user_input()

    # 드라이버 경로 미리 받아두기
    chrome_driver_path = ChromeDriverManager().install()
    firefox_driver_path = GeckoDriverManager().install()
    # Edge 드라이버 자동 설치
    edge_driver_path = r"D:\Browser\AutoTest\Browsersynchro\drivers\msedgedriver.exe"

    # 1) 수동 조작용 Chrome (항상 실행)
    chrome_options = Options()
    chrome_options.add_argument('--proxy-server=http://프록시주소:포트')

    service_main = ChromeService(executable_path=chrome_driver_path)
    driver_chrome_main = webdriver.Chrome(service=service_main, options=chrome_options)
    driver_chrome_main.maximize_window()
    driver_chrome_main.get(test_url)

    # 2) 자동 따라하기용 Firefox
    driver_firefox = None
    if use_firefox:
        service_firefox = FirefoxService(executable_path=firefox_driver_path)
        driver_firefox = webdriver.Firefox(service=service_firefox)
        driver_firefox.maximize_window()
        driver_firefox.get(test_url)

    # 3) 자동 따라하기용 Edge
    driver_edge = None
    if use_edge:
        from selenium.webdriver.edge.options import Options as EdgeOptions
        service_edge = EdgeService(executable_path=edge_driver_path)
        driver_edge = webdriver.Edge(service=service_edge)
        driver_edge.maximize_window()
        driver_edge.get(test_url)

    # 클릭 + 스크롤 감지 JS 코드 (수동 Chrome에 삽입)
    js_code = """
    // 클릭 이벤트
    document.addEventListener('click', function(e) {
        let path = [];
        let elem = e.target;
        while (elem && elem.tagName !== 'BODY') {
            const siblings = Array.from(elem.parentNode.children)
                .filter(el => el.tagName === elem.tagName);
            path.unshift({
                tag: elem.tagName,
                class: elem.className,
                index: siblings.indexOf(elem)
            });
            elem = elem.parentElement;
        }
        const elementInfo = {
            action: 'click',
            path: path,
            tag: e.target.tagName,
            id: e.target.id,
            class: e.target.className,
            text: e.target.innerText,
            url: window.location.href
        };
        fetch('http://localhost:5000/event', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(elementInfo)
        });
    });

    // 스크롤 이벤트
    let lastScrollX = window.scrollX;
    let lastScrollY = window.scrollY;
    window.addEventListener('scroll', function() {
        const nowX = window.scrollX;
        const nowY = window.scrollY;
        if (Math.abs(nowX - lastScrollX) > 10 || Math.abs(nowY - lastScrollY) > 10) {
            lastScrollX = nowX;
            lastScrollY = nowY;
            fetch('http://localhost:5000/event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    action: 'scroll',
                    url: window.location.href,
                    scrollX: nowX,
                    scrollY: nowY
                })
            });
        }
    });

    // 입력값 변경 이벤트 (input, textarea)
    document.addEventListener('input', function(e) {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            const inputInfo = {
                action: 'input',
                tag: e.target.tagName,
                id: e.target.id,
                class: e.target.className,
                value: e.target.value,
                url: window.location.href
            };
            fetch('http://localhost:5000/event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(inputInfo)
            });
        }
    });
    """
    driver_chrome_main.execute_script(js_code)

    print('서버 실행 중... http://localhost:5000')

    # Flask를 별도 스레드로 실행
    threading.Thread(target=lambda: app.run(port=5000, threaded=True, use_reloader=False)).start()

    # URL 변경 감지 및 JS 코드 주입 스레드 시작
    threading.Thread(target=monitor_and_inject, args=(driver_chrome_main,)).start()

    # 종료 대기 UI 표시
    show_exit_window()