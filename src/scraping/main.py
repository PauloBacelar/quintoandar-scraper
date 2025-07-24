import os
import random
import undetected_chromedriver as uc
import re
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
total_collected_ads = 0

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
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2
    })
    return options


def launch_browser(url):
    driver = uc.Chrome(options=get_chrome_options())
    driver.execute_cdp_cmd('Network.enable', {})
    driver.execute_cdp_cmd('Network.setBlockedURLs', {"urls": ["*.png", "*.jpg", "*.jpeg", "*.gif"]})
    driver.get(url)

    write_csv_headers()
    page = 1
    while True:
        print(f"\nPage: {page}")

        if page == 1:
            get_current_grid_ads(driver, page, 0)
            page += 1
            continue

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
            ads_quant_before_click = len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="house-card-container"]'))
            button.click()

            print("Successful click! Reading grid data...")
            get_current_grid_ads(driver, page, ads_quant_before_click)

            page += 1
        except ElementClickInterceptedException as e:
            print("Error! Click intercepted. Trying to accept cookies.")
            accept_cookies(driver)

            try:
                button = driver.find_element(By.ID, "see-more")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", button)
                ads_quant_before_click = len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="house-card-container"]'))
                button.click()

                print("Successful retry! Reading grid data...")
                get_current_grid_ads(driver, page, ads_quant_before_click)

                page += 1
            except Exception as e2:
                print("Retry failed:", e2)
        
        except Exception as e:
            print("Error:", e)

    driver.quit()


def write_csv_headers():
    csv_file_path = os.path.join(base_path, os.pardir, 'data', 'properties_data.csv')
    csv_file_path = os.path.abspath(csv_file_path)

    header = ["property_id", "address", "neighborhood", "city", "property_type", "total_price", "condo_fee", "area", "sq_m_price", "bedroom_qnt", "parking_spaces_qnt"]
    with open(csv_file_path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(header)


def write_property_info_on_csv(row):
    file_path = os.path.join(base_path, "../data", "properties_data.csv")
    with open(file_path, 'a', newline='') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(row)


def get_current_grid_ads(driver, page, ads_len_before_click):
    sleep(random.uniform(1, 2))
    wait = WebDriverWait(driver, 10)
    wait.until(lambda driver: len(driver.find_elements(By.CSS_SELECTOR, '[data-testid="house-card-container"]')) > ads_len_before_click)
    ad_cards = driver.find_elements(By.CSS_SELECTOR, '[data-testid="house-card-container"]')

    grid_ad_quant = len(ad_cards) - ads_len_before_click
    print(page, grid_ad_quant)

    for i in range(len(ad_cards), len(ad_cards) - grid_ad_quant, -1):
        ad_xpath = f'(//*[@data-testid="house-card-container"])[{i}]'
        ad_card = driver.find_element(By.XPATH, ad_xpath)

        ad_card_link = ad_card.find_element(By.TAG_NAME, "a").get_attribute("href")
        property_info = ad_card.find_element(By.TAG_NAME, "h3").text
        ad_description = ad_card.find_elements(By.TAG_NAME, "h2")[0].text
        property_location = ad_card.find_elements(By.TAG_NAME, "h2")[1].text
        property_prices_info = ad_card.find_elements(By.TAG_NAME, "p")

        extract_property_data({
            "ad_card_link": ad_card_link,
            "property_info": property_info,
            "ad_description": ad_description,
            "property_location": property_location,
            "property_prices_info": property_prices_info
        })


def extract_property_data(grid_data):
    global total_collected_ads
    id = grid_data["ad_card_link"].split("imovel/")[1].split("/")[0]
    area = bedroom_quant = parking_spaces_quant = 0

    area_match = re.search(r"(\d+)\s*m²", grid_data["property_info"])
    bedrooms_match = re.search(r"(\d+)\s*quarto", grid_data["property_info"])
    parking_match = re.search(r"(\d+)\s*vaga", grid_data["property_info"])

    if area_match:
        area = int(area_match.group(1))
    if bedrooms_match:
        bedroom_quant = int(bedrooms_match.group(1))
    if parking_match:
        parking_spaces_quant = int(parking_match.group(1))
    
    main_address = grid_data["property_location"].split(" · ")[0]
    city = grid_data["property_location"].split(" · ")[1]

    if len(main_address.split(", ")) > 1:
        address = grid_data["property_location"].split(",")[0]
        neighborhood = grid_data["property_location"].split(", ")[1].split(" · ")[0]
    else:
        address = main_address
        neighborhood = ""

    total_price = int(grid_data["property_prices_info"][0].text.replace("R$ ", "").replace(".", ""))
    condo_fee = int(grid_data["property_prices_info"][1].text.split(" Condo.")[0].replace("R$ ", "").replace(".", ""))

    sq_m_price = 0
    if area:
        sq_m_price = round((total_price / area), 2)

    property_type = ""
    if "apartamento" in grid_data["ad_description"].lower():
        property_type = "apartamento"
    elif "casa" in grid_data["ad_description"].lower():
        property_type = "casa"
    elif "studio" in grid_data["ad_description"].lower() or "kit" in grid_data["ad_description"].lower():
        property_type = "studio/kitnet"

    total_collected_ads += 1
    print(id, address, neighborhood, city, property_type, total_price, condo_fee, area, sq_m_price, bedroom_quant, parking_spaces_quant)
    


def accept_cookies(driver):
    sleep(random.uniform(1, 2))
    accept_cookies_button = driver.find_element(By.ID, "c-s-bn")
    accept_cookies_button.click()


links = get_links()
for link in links:
    website = link
    total_collected_ads = 0
    launch_browser(website)
    sleep(random.uniform(1, 2))
