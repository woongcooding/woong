from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time

# Chrome WebDriver 초기화 및 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
base_url = "https://tenniseye.com/board_BXPZ63"
target_date = "Mar 17, 2024"
driver.get(base_url)
time.sleep(5)  # 페이지 로딩 대기

# 기사 데이터를 저장할 리스트
article_data = []

# 'hx' 클래스를 가진 모든 'a' 태그 찾기 및 처리
links = soup.find_all('a', class_='hx')
for link in links:
    article_url = urljoin(base_url, link['href'])
    driver.execute_script(f"window.open('{article_url}');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(5)  # 기사 페이지 로딩 대기
    
    article_page_source = driver.page_source
    article_soup = BeautifulSoup(article_page_source, 'html.parser')
    
    date_tag = article_soup.select_one('.top_area.ngeb.np_18px')  # 날짜 태그 수정
    article_title = article_soup.select_one('h1.font.ngeb').text.strip()  # 제목 추출
    article_date = date_tag.text.strip() if date_tag else ''
    
    # 날짜가 목표 날짜와 일치하는지 확인 후 처리
    if target_date in article_date:
        # 기사 내용 추출
        article_content = article_soup.select_one('div[data-pswp-uid="1"]').text.strip()
        article_data.append({'title': article_title, 'date': article_date, 'content': article_content})
    
    driver.close()  # 현재 탭 닫기
    driver.switch_to.window(driver.window_handles[0])  # 원래 탭으로 돌아가기

# 드라이버 종료
driver.quit()

# 저장된 기사 제목, 날짜, 내용을 출력
for article in article_data:
    print(f"Title: {article['title']}")
    print(f"Date: {article['date']}")
    print(f"Content: {article['content']}")
    print("-" * 100)
