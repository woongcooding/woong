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
            {"role": "system", "content": "다음 기사를 한국어로 번역해줘."},#프롬프트 창
            {"role": "user", "content": article_content}
        ]
    )
    
    return completion.choices[0].message.content.strip()

# 기사 데이터를 저장할 리스트
article_data = []

# 날짜 설정: 현재 날짜에서 하루를 빼서 사용
target_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

# Chrome WebDriver 초기화 및 설정
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
base_url = "https://www.tennis.co.kr/tkboard/tkboard_list.php?category=internal"
driver.get(base_url)
time.sleep(5)  # 페이지 로딩 대기

# 페이지의 HTML 소스 가져오기 및 파싱
page_source = driver.page_source
soup = BeautifulSoup(page_source, 'html.parser')

# 모든 기사 링크 가져오기
links = soup.select('div.news_txt a')
for link in links:
    article_url = urljoin(base_url, link['href'])
    driver.get(article_url)
    time.sleep(5)  # 기사 페이지 로딩 대기
    
    article_page_source = driver.page_source
    article_soup = BeautifulSoup(article_page_source, 'html.parser')
    
    # 기사 게시 날짜 확인
    time_tag = article_soup.select_one('li.right')
    time_data = time_tag.text.strip() if time_tag else ''
    if target_date in time_data:
        # 기사 제목, 내용 가져오기
        title = article_soup.select_one('h4').text.strip()
        content_tag = article_soup.select_one('div.view_txt')
        content = content_tag.text.strip() if content_tag else ''
        
        # 기사 내용 요약
        article_summary = summarize_article(content)
        
        # 요약된 내용을 데이터에 추가
        article_data.append({
            'title': title, 
            'date': time_data, 
            'content': content, 
            'summary': article_summary
        })
    
# 드라이버 종료
driver.quit()

# DataFrame으로 변환
df = pd.DataFrame(article_data)

# 엑셀 파일로 저장
df.to_excel('테니스코리아_국내_요약.xlsx', index=False)

print("기사 내용 및 요약이 '테니스코리아_국내_요약.xlsx' 파일에 저장되었습니다.")
