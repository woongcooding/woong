import pandas as pd
from datetime import datetime, timedelta
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from openai import OpenAI

#gpt api 추가
client = OpenAI(
    api_key='당신의 개인 api_key를 입력하세요'#api_key 입력창
)


def summarize_article(article_content):
    """
    주어진 기사 내용을 OpenAI GPT-3.5 모델을 사용하여 요약합니다.
    """
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant that summarizes articles."},#프롬프트 창
            {"role": "user", "content": article_content}
        ]
    )
    
    return completion.choices[0].message.content.strip()

# 기사 데이터를 저장할 리스트
article_data = []

# 날짜 설정: 현재 날짜에서 하루를 빼서 사용
target_date = (datetime.now() - timedelta(days=1)).strftime('%b %d, %Y')

# Chrome WebDriver 초기화 및 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
base_url = "https://tenniseye.com/board_BXPZ63"
driver.get(base_url)
time.sleep(5)  # 페이지 로딩 대기

# 페이지의 HTML 소스 가져오기 및 파싱
page_source = driver.page_source
soup = BeautifulSoup(page_source, 'html.parser')

# 'hx' 클래스를 가진 모든 'a' 태그 찾기 및 처리
links = soup.find_all('a', class_='hx')
for link in links:
    article_url = urljoin(base_url, link['href'])
    driver.execute_script(f"window.open('{article_url}');")
    driver.switch_to.window(driver.window_handles[1])
    time.sleep(5)  # 기사 페이지 로딩 대기
    
    article_page_source = driver.page_source
    article_soup = BeautifulSoup(article_page_source, 'html.parser')
    
    date_tag = article_soup.select_one('.top_area.ngeb.np_18px')  # 날짜 태그
    article_title = article_soup.select_one('h1.font.ngeb').text.strip()  # 제목 추출
    article_date = date_tag.text.strip() if date_tag else ''
    
    if target_date in article_date:
        article_content = article_soup.select_one('div[data-pswp-uid="1"]').text.strip()
        article_data.append({'title': article_title, 'date': article_date, 'content': article_content})
        if target_date in article_date:
            article_content = article_soup.select_one('div[data-pswp-uid="1"]').text.strip()
            # 기사 내용 요약
            article_summary = summarize_article(article_content)
            # 요약된 내용을 데이터에 추가
            article_data.append({
                'title': article_title, 
                'date': article_date, 
                'content': article_content, 
                'summary': article_summary  # 요약된 내용 추가
        })
    
    driver.close()  # 현재 탭 닫기
    driver.switch_to.window(driver.window_handles[0])  # 원래 탭으로 돌아가기

# 드라이버 종료
driver.quit()

# 기존 엑셀 파일을 불러오거나, 파일이 없으면 새 DataFrame 생성
try:
    existing_df = pd.read_excel('테니스라이프.xlsx')
except FileNotFoundError:
    existing_df = pd.DataFrame(columns=['title', 'date', 'content'])

# 새로운 기사 데이터를 DataFrame으로 변환
new_df = pd.DataFrame(article_data)

# 기존 DataFrame에 새로운 기사 데이터 추가
final_df = pd.concat([existing_df, new_df], ignore_index=True)

# 최종 DataFrame을 엑셀 파일로 저장
final_df.to_excel('테니스라이프_요약.xlsx', index=False)

print("기사 내용이 '테니스라이프_요약.xlsx' 파일에 저장되었습니다.")