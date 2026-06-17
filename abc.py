from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

opts = Options()
opts.add_argument("--headless")
opts.add_argument("--headless=new")
# CRITICAL: These make headless look more like a real browser
opts.add_argument("--disable-gpu")
opts.add_argument("--disable-software-rasterizer")
opts.add_argument("--disable-dev-shm-usage")

# Enhanced stealth options
opts.add_argument("--disable-blink-features=AutomationControlled")
opts.add_argument("--no-sandbox")
opts.add_argument("--window-size=1920,1080")
opts.add_argument("--start-maximized")
opts.add_argument("--lang=en-US")
opts.add_experimental_option("excludeSwitches", ["enable-automation"])
opts.add_experimental_option("useAutomationExtension", False)

service = Service(ChromeDriverManager().install())

driver = webdriver.Chrome(service=service, options=opts)

print("created")
print(driver.current_url)

driver.quit()