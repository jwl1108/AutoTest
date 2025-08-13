import os
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox

from flask import Flask, request
from flask_cors import CORS

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService

from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.firefox import GeckoDriverManager

# =====================[ 전역 변수 및 설정 ]=====================
app = Flask(__name__)
CORS(app)

driver_chrome_main = None
driver_firefox_main = None
driver_edge_main = None
driver_chrome_follow = None
driver_firefox = None
driver_edge = None

EDGE_DRIVER_PATH = r"D:\Browser\AutoTest\Browsersynchro\drivers\msedgedriver.exe"
CLICKABLE_TAGS = ["button", "a", "span", "li", "div"]

# =====================[ 유틸리티 함수 ]=====================
def wait_and_find_element(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((by, value))
        )
    except Exception:
        return None

def wait_and_find_elements(driver, by, value, timeout=10):
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_all_elements_located((by, value))
        )
    except Exception:
        return []

# =====================[ 클릭 로직 ]=====================
def find_and_click(driver, data, browser_name):
    try:
        path = data.get('path')
        print(f"🔎 클릭 경로(path): {path}")
        element = None

        # 1. path 기반 탐색 (모든 프레임에서)
        if path and isinstance(path, list) and len(path) > 0:
            element = find_element_by_path_in_all_frames(driver, path)
            hover_targets = get_hover_targets(driver, path)
            hover_menu_chain(driver, hover_targets)

        # 2. id/class/text 기반 탐색 (path 실패 시)
        if not element:
            element = find_element_by_id_class_text(driver, data)

        # 3. 클릭 시도
        if element:
            click_element_with_priority(element, browser_name)
        else:
            print(f"❌ {browser_name}에서 요소를 찾지 못했습니다")
    except Exception as e:
        print(f"🔥 {browser_name} 오류: {e}")

def find_element_by_path(driver, path):
    parent = driver.find_element(By.TAG_NAME, "body")
    for step in path:
        tag = step.get('tag')
        class_name = step.get('class')
        idx = step.get('index')
        class_names = class_name.split() if class_name else []
        def class_match(el):
            el_classes = el.get_attribute('class').split()
            return all(c in el_classes for c in el_classes) if class_names else True
        children = parent.find_elements(By.XPATH, "./*")
        siblings = [el for el in children if el.tag_name.upper() == tag]
        if 0 <= idx < len(siblings):
            parent = siblings[idx]
        else:
            return None
    return parent

def get_hover_targets(driver, path):
    parent = driver.find_element(By.TAG_NAME, "body")
    hover_targets = []
    for step in path:
        tag = step.get('tag')
        class_name = step.get('class')
        idx = step.get('index')
        class_names = class_name.split() if class_name else []
        children = parent.find_elements(By.XPATH, "./*")
        siblings = [el for el in children if el.tag_name.upper() == tag]
        if 0 <= idx < len(siblings):
            parent = siblings[idx]
            hover_targets.append(parent)
        else:
            break
    return hover_targets

def hover_menu_chain(driver, hover_targets):
    if len(hover_targets) > 1:
        actions = ActionChains(driver)
        for hover_el in hover_targets[:-1]:
            try:
                actions.move_to_element(hover_el).perform()
                time.sleep(0.05)  # 딜레이 최소화
            except Exception as e:
                print(f"⚠️ Hover 실패: {e}")

def find_element_by_id_class_text(driver, data):
    id_ = data.get('id')
    class_ = data.get('class')
    text = data.get('text')
    element = None

    if id_:
        element = find_element_in_all_frames(driver, By.ID, id_)
    if not element and class_:
        class_name = class_.split()[0]
        elements = wait_and_find_elements(driver, By.CLASS_NAME, class_name)
        if elements:
            element = elements[0]
    if not element and text:
        elements = wait_and_find_elements(driver, By.XPATH, f"//*[text()='{text}']")
        if elements:
            element = elements[0]
    return element

def click_element_with_priority(element, browser_name):
    for sub_tag in ["button", "a", "span", "i"]:
        sub_elements = element.find_elements(By.TAG_NAME, sub_tag)
        if sub_elements:
            try:
                sub_elements[0].click()
                print(f"✅ {browser_name} 내부 {sub_tag} 클릭 완료")
                return
            except Exception as e:
                print(f"🔥 {browser_name} 내부 {sub_tag} 클릭 오류: {e}")
    try:
        element.click()
        print(f"✅ {browser_name} 자체 클릭 완료")
    except Exception as e:
        print(f"🔥 {browser_name} 자체 클릭 오류: {e}")

# =====================[ 브라우저별 클릭 핸들러 ]=====================
def click_in_chrome_follow(data):
    global driver_chrome_follow
    find_and_click(driver_chrome_follow, data, "Chrome (Follow)")

def input_in_chrome_follow(data):
    global driver_chrome_follow
    input_to_driver(driver_chrome_follow, data, "Chrome (Follow)")

def scroll_in_chrome_follow(data):
    global driver_chrome_follow
    scroll_x = data.get('scrollX', 0)
    scroll_y = data.get('scrollY', 0)
    if driver_chrome_follow:
        try:
            driver_chrome_follow.execute_script(f"window.scrollTo({int(scroll_x)}, {int(scroll_y)});")
            print(f"✅ Chrome(Follow) 스크롤 위치 이동: x={scroll_x}, y={scroll_y}")
        except Exception as e:
            print(f"🔥 Chrome(Follow) 스크롤 오류: {e}")

def click_in_firefox(data):
    global driver_firefox
    if driver_firefox:
        find_and_click(driver_firefox, data, "Firefox")

def click_in_edge(data):
    global driver_edge
    if driver_edge:
        find_and_click(driver_edge, data, "Edge")

# =====================[ Flask 라우트 ]=====================
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
        if driver_chrome_follow:
            threads.append(threading.Thread(target=scroll_in_chrome_follow, args=(data,)))
        if driver_firefox:
            threads.append(threading.Thread(target=scroll_in_all, args=(data,)))
        if driver_edge:
            threads.append(threading.Thread(target=scroll_in_all, args=(data,)))
    elif action == 'click':
        if driver_chrome_follow:
            threads.append(threading.Thread(target=click_in_chrome_follow, args=(data,)))
        if driver_firefox:
            threads.append(threading.Thread(target=click_in_firefox, args=(data,)))
        if driver_edge:
            threads.append(threading.Thread(target=click_in_edge, args=(data,)))
    elif action == 'input':
        if driver_chrome_follow:
            threads.append(threading.Thread(target=input_in_chrome_follow, args=(data,)))
        if driver_firefox:
            threads.append(threading.Thread(target=input_in_firefox, args=(data,)))
        if driver_edge:
            threads.append(threading.Thread(target=input_in_edge, args=(data,)))
    for t in threads:
        t.start()
    return 'OK', 200

# =====================[ 기타 기능 함수 ]=====================
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
    js_code = """
    function injectSyncEvents(doc) {
        if (!doc.__browser_sync_injected) {
            doc.__browser_sync_injected = true;

            // 입력값 변경 이벤트 (input, textarea) - debounce 적용
            let inputTimer = null;
            doc.addEventListener('input', function(e) {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                    if (inputTimer) clearTimeout(inputTimer);
                    inputTimer = setTimeout(function() {
                        const inputInfo = {
                            action: 'input',
                            tag: e.target.tagName,
                            id: e.target.id,
                            class: e.target.className,
                            value: e.target.value,
                            url: doc.location.href
                        };
                        console.log("[브라우저 동기화] input 이벤트 전송", inputInfo);
                        fetch('http://localhost:5000/event', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(inputInfo)
                        });
                    }, 150);
                }
            });

            // 클릭 이벤트
            doc.addEventListener('click', function(e) {
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
                    url: doc.location.href
                };
                console.log("[브라우저 동기화] click 이벤트 전송", elementInfo);
                fetch('http://localhost:5000/event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(elementInfo)
                });
            });

            // 키다운 이벤트
            doc.addEventListener('keydown', function(e) {
                const keyInfo = {
                    action: 'keydown',
                    key: e.key,
                    code: e.code,
                    ctrlKey: e.ctrlKey,
                    shiftKey: e.shiftKey,
                    altKey: e.altKey,
                    metaKey: e.metaKey
                };
                console.log("[브라우저 동기화] keydown 이벤트 전송", keyInfo);
                fetch('http://localhost:5000/event', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(keyInfo)
                });
            });

            // 스크롤 이벤트
            let lastScrollX = doc.defaultView.scrollX;
            let lastScrollY = doc.defaultView.scrollY;
            doc.defaultView.addEventListener('scroll', function() {
                const nowX = doc.defaultView.scrollX;
                const nowY = doc.defaultView.scrollY;
                if (Math.abs(nowX - lastScrollX) > 10 || Math.abs(nowY - lastScrollY) > 10) {
                    lastScrollX = nowX;
                    lastScrollY = nowY;
                    const scrollInfo = {
                        action: 'scroll',
                        url: doc.location.href,
                        scrollX: nowX,
                        scrollY: nowY
                    };
                    console.log("[브라우저 동기화] scroll 이벤트 전송", scrollInfo);
                    fetch('http://localhost:5000/event', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(scrollInfo)
                    });
                }
            });
        }
    }

    // 메인 문서에 주입
    injectSyncEvents(document);

    // 모든 iframe에도 주입
    function injectAllIframes(doc) {
        Array.from(doc.getElementsByTagName('iframe')).forEach(function(iframe) {
            try {
                if (iframe.contentDocument) {
                    injectSyncEvents(iframe.contentDocument);
                }
            } catch (e) {
                // cross-origin iframe은 접근 불가
            }
        });
    }
    injectAllIframes(document);

    // iframe 동적 생성/변경 감지
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.tagName === 'IFRAME') {
                    try {
                        if (node.contentDocument) {
                            injectSyncEvents(node.contentDocument);
                        }
                    } catch (e) {}
                }
            });
        });
        injectAllIframes(document);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    """
    driver.execute_script(js_code)

def monitor_and_inject(driver):
    last_url = driver.current_url
    while True:
        time.sleep(1)
        try:
            if driver.current_url != last_url:
                inject_js(driver)
                last_url = driver.current_url
        except Exception as e:
            print(f"monitor_and_inject 종료: {e}")
            break  # 브라우저가 닫히면 스레드 종료

def close_all_and_exit():
    try:
        # 수동 브라우저 종료
        if 'driver_chrome_main' in globals() and driver_chrome_main:
            driver_chrome_main.quit()
        if 'driver_firefox_main' in globals() and driver_firefox_main:
            driver_firefox_main.quit()
        if 'driver_edge_main' in globals() and driver_edge_main:
            driver_edge_main.quit()
        # 따라하기용 브라우저 종료
        if driver_chrome_follow:
            driver_chrome_follow.quit()
        if driver_firefox:
            driver_firefox.quit()
        if driver_edge:
            driver_edge.quit()
    except Exception as e:
        print(f"브라우저 종료 중 오류: {e}")
    print("모든 브라우저와 서버를 종료합니다.")
    os._exit(0)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

def get_user_input():
    def on_submit():
        url = url_entry.get().strip()
        manual_browser = manual_var.get()
        use_chrome_follow = var_chrome_follow.get()
        use_firefox = var_firefox.get()
        use_edge = var_edge.get()
        edge_driver_path = edge_entry.get().strip()
        if not url:
            messagebox.showerror("오류", "URL을 입력하세요.")
            return
        if use_edge and not edge_driver_path:
            messagebox.showerror("오류", "Edge 드라이버 경로를 입력하세요.")
            return
        root.user_url = url
        root.manual_browser = manual_browser
        root.use_chrome_follow = use_chrome_follow
        root.use_firefox = use_firefox
        root.use_edge = use_edge
        root.edge_driver_path = edge_driver_path
        root.destroy()

    if DND_AVAILABLE:
        root = TkinterDnD.Tk()
    else:
        root = tk.Tk()
    root.title("브라우저 동기화 테스트")
    tk.Label(root, text="테스트할 URL:").pack()
    url_entry = tk.Entry(root, width=40)
    url_entry.pack()
    url_entry.insert(0, "https://")

    # 수동 브라우저 선택 (라디오버튼)
    tk.Label(root, text="수동 브라우저 선택:").pack()
    manual_var = tk.StringVar(value="chrome")
    tk.Radiobutton(root, text="Chrome", variable=manual_var, value="chrome").pack(anchor='w')
    tk.Radiobutton(root, text="Firefox", variable=manual_var, value="firefox").pack(anchor='w')
    tk.Radiobutton(root, text="Edge", variable=manual_var, value="edge").pack(anchor='w')

    # 따라하기용 브라우저 선택 (체크박스)
    tk.Label(root, text="따라하기 페이지 선택:").pack()
    var_chrome_follow = tk.BooleanVar()
    var_firefox = tk.BooleanVar()
    var_edge = tk.BooleanVar()
    tk.Checkbutton(root, text="Chrome 따라하기", variable=var_chrome_follow).pack(anchor='w')
    tk.Checkbutton(root, text="Firefox 따라하기", variable=var_firefox).pack(anchor='w')
    tk.Checkbutton(root, text="Edge 따라하기", variable=var_edge).pack(anchor='w')

    tk.Label(root, text="Edge 드라이버 경로 (드래그&드롭 가능):").pack()
    edge_entry = tk.Entry(root, width=60)
    edge_entry.pack()
    edge_entry.insert(0, r"D:\Browser\AutoTest\Browsersynchro\drivers\msedgedriver.exe")
    if DND_AVAILABLE:
        def drop(event):
            path = event.data.strip('{}')
            edge_entry.delete(0, tk.END)
            edge_entry.insert(0, path)
        edge_entry.drop_target_register(DND_FILES)
        edge_entry.dnd_bind('<<Drop>>', drop)
    tk.Button(root, text="시작", command=on_submit).pack(pady=10)
    root.protocol("WM_DELETE_WINDOW", close_all_and_exit)
    root.mainloop()
    return (root.user_url, root.manual_browser, root.use_chrome_follow, root.use_firefox, root.use_edge, root.edge_driver_path)

def input_in_firefox(data):
    input_to_driver(driver_firefox, data, "Firefox")

def input_in_edge(data):
    input_to_driver(driver_edge, data, "Edge")

def input_to_driver(driver, data, browser_name):
    try:
        id_ = data.get('id')
        class_ = data.get('class')
        value = data.get('value')
        if not driver:
            print(f"🔥 {browser_name} 드라이버가 준비되지 않았습니다.")
            return
        element = None
        if id_:
            element = find_element_in_all_frames(driver, By.ID, id_)
        if not element and class_:
            class_name = class_.split()[0]
            element = wait_and_find_element(driver, By.CLASS_NAME, class_name, timeout=5)
        if element:
            # 기존 값과 다를 때만 입력
            current_value = element.get_attribute("value")
            if current_value != value:
                element.clear()
                element.send_keys(value)
                print(f"✅ {browser_name} 입력값 동기화: {value}")
            else:
                print(f"⏩ {browser_name} 입력값 동일, 동기화 생략")
        else:
            print(f"❌ {browser_name}에서 입력 요소를 찾지 못했습니다")
    except Exception as e:
        print(f"🔥 {browser_name} 입력 오류: {e}")

def show_exit_window():
    exit_root = tk.Tk()
    exit_root.title("브라우저 동기화 종료")
    tk.Label(exit_root, text="프로그램을 종료하려면 아래 버튼을 누르세요.").pack(padx=20, pady=10)
    tk.Button(exit_root, text="종료", command=close_all_and_exit, width=20, height=2).pack(pady=10)
    exit_root.protocol("WM_DELETE_WINDOW", lambda: None)
    exit_root.mainloop()

def auto_test_all_clickables(driver):
    elements = []
    for tag in CLICKABLE_TAGS:
        elements += driver.find_elements(By.TAG_NAME, tag)
    elements = list(dict.fromkeys(elements))
    for idx, el in enumerate(elements):
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", el)
            time.sleep(0.05)
            el_class = el.get_attribute('class')
            el_text = el.text
            print(f"[{idx}] {el.tag_name} class='{el_class}' text='{el_text}' 클릭 시도")
            el.click()
            time.sleep(0.1)
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

def find_element_in_all_frames(driver, by, value):
    # 1. 메인 프레임에서 시도
    try:
        return driver.find_element(by, value)
    except:
        pass
    # 2. 모든 iframe에서 시도
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        try:
            driver.switch_to.frame(iframe)
            el = driver.find_element(by, value)
            driver.switch_to.default_content()
            return el
        except:
            driver.switch_to.default_content()
            continue
    return None

def find_element_by_path_in_all_frames(driver, path):
    # 1. 메인 프레임에서 시도
    try:
        driver.switch_to.default_content()
        el = find_element_by_path(driver, path)
        if el:
            return el
    except Exception:
        pass
    # 2. 모든 iframe에서 시도
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    for iframe in iframes:
        try:
            driver.switch_to.frame(iframe)
            el = find_element_by_path(driver, path)
            driver.switch_to.default_content()
            if el:
                return el
        except Exception:
            driver.switch_to.default_content()
            continue
    driver.switch_to.default_content()
    return None

def find_element_by_path_in_all_frames_recursive(driver, path):
    def _search(driver):
        # 1. 현재 프레임에서 시도
        try:
            el = find_element_by_path(driver, path)
            if el:
                return el
        except Exception:
            pass
        # 2. 하위 iframe에서 재귀적으로 시도
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                found = _search(driver)
                driver.switch_to.default_content()
                if found:
                    return found
            except Exception:
                driver.switch_to.default_content()
                continue
        driver.switch_to.default_content()
        return None
    # 항상 최상위 프레임부터 시작
    driver.switch_to.default_content()
    return _search(driver)

# =====================[ 메인 실행부 ]=====================
if __name__ == '__main__':
    test_url, manual_browser, use_chrome_follow, use_firefox, use_edge, edge_driver_path = get_user_input()

    chrome_driver_path = ChromeDriverManager().install()
    firefox_driver_path = GeckoDriverManager().install()

    manual_driver = None

    # 수동 브라우저만 생성
    if manual_browser == "chrome":
        chrome_options = Options()
        chrome_options.add_argument('--proxy-server=http://프록시주소:포트')
        service_chrome = ChromeService(executable_path=chrome_driver_path)
        driver_chrome_main = webdriver.Chrome(service=service_chrome, options=chrome_options)
        driver_chrome_main.maximize_window()
        driver_chrome_main.get(test_url)
        manual_driver = driver_chrome_main
    elif manual_browser == "firefox":
        service_firefox_main = FirefoxService(executable_path=firefox_driver_path)
        driver_firefox_main = webdriver.Firefox(service=service_firefox_main)
        driver_firefox_main.maximize_window()
        driver_firefox_main.get(test_url)
        manual_driver = driver_firefox_main
    elif manual_browser == "edge":
        from selenium.webdriver.edge.options import Options as EdgeOptions
        service_edge_main = EdgeService(executable_path=edge_driver_path)
        driver_edge_main = webdriver.Edge(service=service_edge_main)
        driver_edge_main.maximize_window()
        driver_edge_main.get(test_url)
        manual_driver = driver_edge_main

    # 따라하기용 Chrome
    driver_chrome_follow = None
    if use_chrome_follow and manual_browser != "chrome":
        service_chrome_follow = ChromeService(executable_path=chrome_driver_path)
        driver_chrome_follow = webdriver.Chrome(service=service_chrome_follow)
        driver_chrome_follow.maximize_window()
        driver_chrome_follow.get(test_url)

    # 따라하기용 Firefox
    driver_firefox = None
    if use_firefox:
        service_firefox = FirefoxService(executable_path=firefox_driver_path)
        driver_firefox = webdriver.Firefox(service=service_firefox)
        driver_firefox.maximize_window()
        driver_firefox.get(test_url)

    # 따라하기용 Edge
    driver_edge = None
    if use_edge:
        service_edge = EdgeService(executable_path=edge_driver_path)
        driver_edge = webdriver.Edge(service=service_edge)
        driver_edge.maximize_window()
        driver_edge.get(test_url)

    # 수동 브라우저에만 JS 삽입
    inject_js(manual_driver)

    print('서버 실행 중... http://localhost:5000')

    threading.Thread(target=lambda: app.run(port=5000, threaded=True, use_reloader=False)).start()
    threading.Thread(target=monitor_and_inject, args=(manual_driver,)).start()
    show_exit_window()