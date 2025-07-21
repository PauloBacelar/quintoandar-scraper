import os
import math
import undetected_chromedriver as uc
import traceback
import csv
from random import randint
from time import sleep
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from random_user_agent.user_agent import UserAgent
from random_user_agent.params import SoftwareName, OperatingSystem
from selenium.common.exceptions import ElementClickInterceptedException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


base_path = os.path.dirname(os.path.abspath(__file__))
ids = []

def get_links():
    file_path = os.path.join(base_path, "utils", "links.txt")
    links = []

    with open(file_path, mode="r", encoding="utf-8") as file:
        for line in file:
            links.append(line.replace('\n', ''))

    return links


def get_user_agent():
    user_agent_rotator = UserAgent(
        software_names=[SoftwareName.CHROME.value],
        operating_systems=[OperatingSystem.WINDOWS.value, OperatingSystem.LINUX.value],
        limit=100
    )
    return user_agent_rotator.get_random_user_agent()


def get_chrome_options():
    options = Options()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(f"user-agent={get_user_agent()}")
    return options


def launch_browser(url):
    driver = uc.Chrome(options=get_chrome_options())
    driver.get(url)

    element = driver.find_element(By.CSS_SELECTOR, '[data-testid="CONTEXTUAL_SEARCH_TITLE"]')
    ads_quant = int(element.text.split(" ")[0].replace(".", ""))
    page_quant = math.ceil(ads_quant / 12) 

    write_csv_headers()

    page = 1
    while True:
        sleep_time = randint(1, 5)
        print(f"\nPage: {page}")

        try:
            wait = WebDriverWait(driver, 10)
            button = wait.until(EC.element_to_be_clickable((By.ID, "see-more")))
        except TimeoutException as e:
            print("Timeout trying to find see-more button. Scrolling probably came to an end")
            break
        except Exception as e2:
            print("No button found", e2)
            traceback.print_exc()
        
        try:
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
        except Exception as e:
            print("Failed to scroll into view", e)
            traceback.print_exc()
        
        try:
            button.click()

            print("Successful click!")
            page += 1
        except ElementClickInterceptedException as e:
            print("Error! Click intercepted. Trying to accept cookies.")

            sleep(1)
            accept_cookies(driver)
            sleep(1)

            try:
                button = driver.find_element(By.ID, "see-more")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                button.click()

                print("Successful retry!")
                page += 1
            except Exception as e2:
                print("Retry failed:", e2)
        
        except Exception as e:
            print("Error:", e)
                
        sleep(sleep_time)

    driver.quit()


def write_csv_headers():
    csv_file_path = os.path.join(base_path, os.pardir, 'data', 'properties_data.csv')
    csv_file_path = os.path.abspath(csv_file_path)

    header = ["property_id", "district", "property_type", "total_price", "condo_fee", "area", "bedroom_qnt", "bathroom_qnt", "parking_spaces_qnt", "sq_m_price"]
    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)


def accept_cookies(driver):
    accept_cookies_button = driver.find_element(By.ID, "c-s-bn")
    accept_cookies_button.click()


links = get_links()
for link in links:
    website = link
    launch_browser(website)
    sleep(randint(5, 15))
