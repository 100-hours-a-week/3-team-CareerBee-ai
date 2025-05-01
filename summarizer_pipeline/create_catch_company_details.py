import os
import time
import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv


# 함수: 안전하게 요소 가져오기
def safe_get(selector, attr="text"):
    try:
        element = driver.find_element(By.CSS_SELECTOR, selector)
        return element.get_attribute(attr) if attr != "text" else element.text.strip()
    except:
        return None


# 초기 셋업
load_dotenv()
CATCH_ID = os.getenv("CATCH_ID")
CATCH_PW = os.getenv("CATCH_PW")

options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

# 1. 로그인
driver.get("https://www.catch.co.kr/Member/Login")
time.sleep(2)

id_input = wait.until(EC.presence_of_element_located((By.ID, "id_login")))
pw_input = driver.find_element(By.ID, "pw_login")
id_input.clear()
pw_input.clear()
id_input.send_keys(CATCH_ID)
pw_input.send_keys(CATCH_PW)
pw_input.send_keys(Keys.ENTER)
time.sleep(3)

# 2. 필터링
driver.get("https://www.catch.co.kr/Comp/CompMajor/SearchPage")
time.sleep(2)

# 업종 필터 (IT·통신)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(2)",
).click()
time.sleep(2)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(2) > ul > li:nth-child(5) > button",
).click()
time.sleep(2)

# 'IT·통신 전체' 선택 (label 클릭)
industry_all_checkbox = wait.until(
    EC.element_to_be_clickable(
        (
            By.CSS_SELECTOR,
            "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(2) > ul > li:nth-child(5) > div > span:nth-child(1) > label",
        )
    )
)
industry_all_checkbox.click()
time.sleep(1)

# 지역 필터 (경기 > 성남시)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(3)",
).click()
time.sleep(0.5)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(3) > ul > li:nth-child(9) > button",
).click()
time.sleep(0.5)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(3) > ul > li:nth-child(9) > div > span:nth-child(12) > label",
).click()
time.sleep(0.5)

# 기업규모 필터 (대기업, 중견기업, 중소기업)
driver.find_element(
    By.CSS_SELECTOR,
    "#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(4)",
).click()
time.sleep(0.5)
for i in range(1, 4):
    driver.find_element(
        By.CSS_SELECTOR,
        f"#contents2 > div.corp_fav_category2 > div.filter_search > div > div:nth-child(4) > div > span:nth-child({i}) > label",
    ).click()
    time.sleep(0.5)

time.sleep(2)

# 3. 기업 리스트 & 상세 정보 수집
results = []
page = 1
prev_company_names = set()

while True:
    print(f"📄 페이지 {page} 수집 중...")

    cards = driver.find_elements(
        By.CSS_SELECTOR, "#contents2 > div.corp_sch_result2 > ul > li"
    )
    current_page_names = set()

    for card in cards:
        try:
            name = card.find_element(By.CSS_SELECTOR, "div.txt > p.name > a").text
            detail_link = card.find_element(
                By.CSS_SELECTOR, "div.txt > p.name > a"
            ).get_attribute("href")
            current_page_names.add(name)

            # 상세 페이지 이동
            driver.execute_script("window.open(arguments[0]);", detail_link)
            driver.switch_to.window(driver.window_handles[-1])
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "#contents2 > div.corp_info_baseinfo")
                )
            )

            result = {
                "기업명": name,
                "키워드": ", ".join(
                    kw.text.strip()
                    for kw in driver.find_elements(
                        By.CSS_SELECTOR,
                        "#contents2 > div.corp_info_baseinfo > div.corp_info_base2 > p > span",
                    )
                    if kw.text.strip()
                ),
                "로고": safe_get(
                    "#contents2 > div:nth-child(1) > div.corp_info_top > div > div.info > div.logo > img",
                    attr="src",
                ),
                "카테고리": safe_get(
                    "#contents2 > div:nth-child(1) > div.corp_info_top > div > div.info > div.txt > p > span:nth-child(2)"
                ),
                "신입연봉": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base2 > div > div.btns > p:nth-child(1) > a"
                ),
                "평균연봉": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base2 > div > div.btns > p:nth-child(2) > a"
                ),
                "주소": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base2 > div > div.tbl > table > tbody > tr:nth-child(4) > td"
                ),
                "사원수": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base1 > div.item.type2 > div > div > p.t1"
                ),
                "홈페이지": safe_get(
                    "#contents2 > div:nth-child(1) > div.corp_info_top > div > div.info > div.txt > div > a",
                    attr="href",
                ),
                "기업형태": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base1 > div.item.type1 > div > p"
                ),
                "매출액": safe_get(
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base1 > div.item.type3 > div:nth-child(3) > div > p.t1"
                ),
                "사업현황": safe_get(
                    "#contents2 > div:nth-child(3) > div:nth-child(1) > div.corp_info_introduce > div > p"
                ),
            }

            # 재무정보 모달 클릭
            try:
                finance_btn = driver.find_element(
                    By.CSS_SELECTOR,
                    "#contents2 > div.corp_info_baseinfo > div.corp_info_base1 > p > button",
                )
                driver.execute_script("arguments[0].click();", finance_btn)
                time.sleep(1)

                result["영업이익"] = safe_get(
                    "#layerFS > div > div.modal_cont > div.scroll > div > div > dl:nth-child(3) > dd:nth-child(3)"
                )
            except:
                result["영업이익"] = None

            results.append(result)

            driver.close()
            driver.switch_to.window(driver.window_handles[0])

        except Exception as e:
            print(f"🚫 에러 발생: {e}")
            driver.switch_to.window(driver.window_handles[0])
            continue

    # 다음 페이지 이동
    try:
        next_btn = driver.find_element(
            By.CSS_SELECTOR, "#contents2 > div.corp_sch_result2 > p > a.ico.next"
        )

        if current_page_names == prev_company_names:
            print("✅ 마지막 페이지 도달. 종료.")
            break

        prev_company_names = current_page_names
        driver.execute_script("arguments[0].click();", next_btn)
        page += 1
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "#contents2 > div.corp_sch_result2 > ul > li")
            )
        )
        time.sleep(2)

    except Exception as e:
        print("🚫 다음 페이지 클릭 실패. 종료.")
        break


# 4. 데이터 저장
df = pd.DataFrame(results)
df.to_csv("catch_companies.csv", index=False)
print("✅ 모든 기업 정보 저장 완료!")

print(df)
