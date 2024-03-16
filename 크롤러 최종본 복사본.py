import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
import re

# 기본 URL
base_url = "https://news.daum.net/breakingnews/digital?page="

#html 변수정의
html_content = "" 

# 오늘 날짜 가져오기
today = (datetime.today() - timedelta(days=1)).strftime('%Y%m%d')
#today = datetime.today().strftime('%Y%m%d') 12시에 날짜가 바껴 뉴스 사라짐

# 비어있는 DataFrame 생성
all_data = pd.DataFrame(columns=["Title", "Link"])

# 마지막 페이지 모르기에 첫 페이지에서 시작
response = requests.get(base_url + "1&regDate=" + today)
response.raise_for_status()  # 응답코드 200 아니면 오류 발생
soup = BeautifulSoup(response.text, 'html.parser')

# <span> tag 내부의 page 숫자들 추출
page_numbers = [int(tag.text) for tag in soup.select('.inner_paging .num_page') if tag.text.isdigit()]

# 마지막 페이지 찾기
last_page_number = max(page_numbers) if page_numbers else 1

# 페이지 돌면서 url 추출
for page in range(1, last_page_number + 1):
    # 페이지 별 오늘 날짜 뉴스 추출
    url = base_url + str(page) + "&regDate=" + today

    # 내용 가져오기
    response = requests.get(url)
    response.raise_for_status()  
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # news item 추출
    news_items = soup.select('.box_etc li > div.cont_thumb > strong.tit_thumb')

    # 제목, 링크 추출 후 df 추가
    for item in news_items:
        title = item.select_one('a.link_txt').text
        link = item.select_one('a.link_txt')['href']
        # 새로운 행을 DataFrame으로 변환
        new_row = pd.DataFrame([{"Title": title, "Link": link}])

        # 원본 DataFrame과 새로운 행을 결합
        all_data = pd.concat([all_data, new_row], ignore_index=True)
        
# 뉴스 기사 본문 추출
def extract_article_content(url):
    with session.get(url) as response:
        soup = BeautifulSoup(response.text, 'html.parser')
        # <section> tag 내부 <p> tag 추출
        article_paragraphs = soup.select("div.article_view section p")
        article_text = '\n'.join([para.text for para in article_paragraphs])
        return article_text if article_text else ""

# url 링크 리스트만들기
links_to_scrape = all_data["Link"].tolist()

# requests요청 위한 session 사용
with requests.Session() as session:
    # requests 병렬 처리
    with ThreadPoolExecutor(max_workers=10) as executor:
        # 병렬 처리로 인해 순서가 다를 수 있으니 순서가 유지되도록 보장
        all_data["article"] = list(executor.map(extract_article_content, links_to_scrape))

all_data.to_excel('news.xlsx')


# OpenAI API 키 설정
openai.api_key = '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'

# 엑셀 파일 불러오기
#file_path = "news.xlsx"
#data = pd.read_excel(file_path)
data = all_data

# 중요 뉴스 가져오기
def get_important_titles_for_chunk(chunk):
    titles = "\n".join(chunk)
    prompt_text = f"Given the following news titles, select the top 3 most important ones:\n{titles}\n\nTop 3 important news titles are:"
    response = openai.Completion.create(
        model="gpt-35-turbo", # 여긴왜 3.5버전 안썼지?
        prompt=prompt_text,
        max_tokens=200
    )
    important_titles = response.choices[0].text.strip().split("\n")
    return [re.sub(r"^\d+\.\s*", "", title) for title in important_titles]

# 10개씩 청크로 나누기
chunk_size = 10
chunks = [data['Title'][i:i+chunk_size].tolist() for i in range(0, len(data), chunk_size)]

all_important_titles = []
for chunk in chunks:
    all_important_titles.extend(get_important_titles_for_chunk(chunk))

# 최종적으로 원하는 숫자만큼 중요 기사 선택 (예: 상위 5개)
final_important_titles = all_important_titles[:5]

# 중요한 뉴스 제목에 해당하는 행들을 새로운 DataFrame으로 가져오기
important_news_df = data[data['Title'].isin(final_important_titles)]

print(important_news_df)

# 뉴스 요약
def summarize_news(news_body):

    # 뉴스 본문을 요약하려면 사용자의 지시에 따라 대화를 정의
    conversation = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"주어진 기사를 짧게 요약해줘 한글로: {news_body}"}
    ]

    # 최대 토큰 개수 지정
    max_tokens = 100

    # api 요청
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=conversation,
    )
    # 요약 추출
    summary = response["choices"][0]["message"]["content"]
    return summary

def main(news_body):
    # 뉴스 요약
    summary = summarize_news(news_body)
    print("Summary:")
    print(summary)
    return summary

# 뉴스 요약
summary_list = important_news_df['article'].apply(main)
important_news_df['summary']=summary_list

def extract_keywords_from_content(content):
    # 본문의 시작 부분과 끝 부분을 결합
    truncated_content = content[:600] + "\n...\n" + content[-600:]

    prompt_text = f"주어진 뉴스 기사의 본문을 보고 핵심 키워드를 `핵심 키워드 : 축구, 이강인, 멘체스터 유나이티드' 와 같은 형태로 추출해줘. ###{truncated_content}###"
    response = openai.Completion.create(
        model="gpt-35-turbo",
        prompt=prompt_text,
        max_tokens=200  # 조절 가능
    )
    keywords = response.choices[0].text.strip().split(", ")
    keywords[0]=keywords[0].replace("핵심 키워드","")
    keywords[0]=keywords[0].replace(":","").strip()
    return keywords

# 각 본문에 대해 주요 키워드를 추출
keywords_list = important_news_df['article'].apply(extract_keywords_from_content)

# 새로운 DataFrame 생성
keywords_df = important_news_df.copy()

keywords_df['keywords']=keywords_list
print(keywords_df)

# 엑셀 파일로 저장
file_name = "gpt_news.xlsx"
keywords_df.to_excel(file_name, index=False)

# 데이터프레임의 내용을 HTML 형식으로 변환
email_content = keywords_df.to_html()
file_path = '/Users/woong/gpt_news.xlsx'
df = pd.read_excel(file_path)

# DataFrame을 원하는 형태로 리스트로 변환
html_content = ""
for index, row in keywords_df.iterrows():
    title = row["Title"]
    link = row["Link"]
    summary = row["summary"]
    keyword = row["keywords"]

    # 하이퍼링크 추가
    title_with_link = f'<a href="{link}">{title}</a>'

    # 형식에 맞게 포맷팅
    formatted_item = f"<h2>제목 : {title_with_link}</h2><br>요약<br>{summary}<br>키워드: {keyword[:5]}<br>"

    html_content += formatted_item