from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.service import Service as EdgeService
import time

def test_browsers():
    # Chrome 테스트
    chrome_service = ChromeService(executable_path=r"D:\Browser\drivers\chromedriver.exe")
    chrome_driver = webdriver.Chrome(service=chrome_service)
    chrome_driver.get("https://www.google.com")
    print("Chrome 열림")
    time.sleep(2)
    chrome_driver.quit()

    # Firefox 테스트
    firefox_service = FirefoxService(executable_path=r"D:\Browser\drivers\geckodriver.exe")
    firefox_driver = webdriver.Firefox(service=firefox_service)
    firefox_driver.get("https://www.google.com")
    print("Firefox 열림")
    time.sleep(2)
    firefox_driver.quit()

    # Edge 테스트
    edge_service = EdgeService(executable_path=r"D:\Browser\drivers\msedgedriver.exe")
    edge_driver = webdriver.Edge(service=edge_service)
    edge_driver.get("https://www.google.com")
    print("Edge 열림")
    time.sleep(2)
    edge_driver.quit()

if __name__ == "__main__":
    test_browsers()
