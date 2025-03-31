import os
import re
import time
import json
import csv
import datetime
import requests
import concurrent.futures
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# ========== 事件列表 ==========
EVENT_LIST = [
    "Manchester folk festival",
    "Manchestermums",
    "Manchester Marathon",
    "vegansofmanchester",
    "manchester music",
    "Manchester Derby",
    "Manchester coop",
    "Manchester rugby",
    "Manchester job fair",
    "ReadMCR",
    "Mcr Spring Clean25",
    "ChildFriendlyMcr",
    "IWDMcr",
    "McrSportsAwards",
    "ZeroCarbonMcr"
]

# ========== 配置 ==========
LOCATION = "Manchester"
SOURCE = "Twitter"
SCROLL_TIMES = 30
DATE_TAG = datetime.datetime.now().strftime("%m%d")
BASE_FOLDER = "/Users/y/Desktop/DATA ADS 70202/codes/twitter_scraper/results"

# ========== 工具函数 ==========
def create_folder_structure(base_folder, event_name):
    safe_event_name = re.sub(r'[<>:"/\\|?*]', '_', event_name)
    folder_name = f"{safe_event_name}_{DATE_TAG}"
    media_folder = os.path.join(base_folder, folder_name, "media")
    os.makedirs(media_folder, exist_ok=True)
    return media_folder, folder_name

def download_media(url, folder_path, file_name):
    try:
        if "format=jpg" not in url:
            return None
        sanitized_file_name = re.sub(r'[<>:"/\\|?*]', '_', file_name)
        file_path = os.path.join(folder_path, sanitized_file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, stream=True, headers=headers)
        if response.status_code == 200:
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(1024):
                    file.write(chunk)
            print(f"✅ 下载成功: {sanitized_file_name}")
            return sanitized_file_name
    except Exception as e:
        print(f"❌ 下载失败: {file_name}, 错误: {e}")
    return None

def get_html_content(driver, search_url):
    driver.get(search_url)
    time.sleep(5)

    seen_html_blocks = set()
    collected_articles = []

    last_height = driver.execute_script("return document.body.scrollHeight")

    for i in range(SCROLL_TIMES):
        driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
        time.sleep(5)
        new_height = driver.execute_script("return document.body.scrollHeight")

        # 提取当前加载出来的 article 元素
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        new_articles = soup.find_all("article", {"role": "article"})

        new_count = 0
        for article in new_articles:
            article_html = str(article)
            if article_html not in seen_html_blocks:
                seen_html_blocks.add(article_html)
                collected_articles.append(article_html)
                new_count += 1

        print(f"⬇️ 第 {i+1}/{SCROLL_TIMES} 次滑动加载，新增推文数: {new_count}")

        if new_height == last_height:
            print("📦 页面已加载到底，提前结束滚动")
            break
        last_height = new_height

    # 拼接所有收集到的 article 标签，包裹在一个 <html><body> 中返回
    combined_html = "<html><body>" + "\n".join(collected_articles) + "</body></html>"
    return combined_html


def extract_tweets_and_download_images(html_content, media_folder, event_name):
    soup = BeautifulSoup(html_content, 'html.parser')
    tweets = soup.find_all("article", {"role": "article"})
    media_count = 1
    tweet_data_list = []

    for tweet in tweets:
        try:
            tweet_text_element = tweet.find("div", {"data-testid": "tweetText"})
            tweet_text = tweet_text_element.get_text(strip=True) if tweet_text_element else ""
            title = tweet_text[:50]
            date_element = tweet.find("time")
            date_time = date_element['datetime'] if date_element else "Not Found"
            link_element = tweet.find("a", href=True)
            tweet_link = f"https://x.com{link_element['href']}" if link_element else "Not Found"

            media_files = []
            media_urls = []
            for img_tag in tweet.find_all("img"):
                src = img_tag.get("src", "")
                if "format=jpg" in src:
                    media_urls.append(src)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = {}
                for media_url in media_urls:
                    file_name = f"{event_name}_{media_count}.jpg"
                    future = executor.submit(download_media, media_url, media_folder, file_name)
                    futures[future] = file_name
                    media_count += 1

                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result:
                        media_files.append(result)

            tweet_data = {
                "event_name": event_name,
                "title": title,
                "description": tweet_text,
                "date_time": date_time,
                "location": LOCATION,
                "source": SOURCE,
                "link": tweet_link,
                "media_files": media_files
            }
            tweet_data_list.append(tweet_data)
        except Exception as e:
            print(f"❌ 解析推文时出错: {e}")
    return tweet_data_list

def save_to_json(data, filepath):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def save_to_csv(data, filepath):
    with open(filepath, "w", encoding="utf-8", newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            "event_name", "title", "description", "date_time", "location",
            "source", "link", "media_files"
        ])
        writer.writeheader()
        for row in data:
            writer.writerow({
                "event_name": row.get("event_name", ""),
                "title": row.get("title", ""),
                "description": row.get("description", ""),
                "date_time": row.get("date_time", ""),
                "location": row.get("location", ""),
                "source": row.get("source", ""),
                "link": row.get("link", ""),
                "media_files": ", ".join(row.get("media_files", []))
            })

# ========== 主程序 ==========
def main():
    os.makedirs(BASE_FOLDER, exist_ok=True)
    driver = webdriver.Chrome()
    try:
        print("📥 请手动登录 X/Twitter...")
        driver.get("https://x.com/login")
        input("🔑 登录完成后按回车继续...")

        all_tweets = []
        for event in EVENT_LIST:
            print(f"\n🔍 正在处理事件: {event}")
            query = event.replace(" ", "%20")
            search_url = f"https://x.com/search?q={query}&src=typed_query&f=live"
            html_content = get_html_content(driver, search_url)
            media_folder, folder_name = create_folder_structure(BASE_FOLDER, event)
            tweet_data = extract_tweets_and_download_images(html_content, media_folder, event)
            all_tweets.extend(tweet_data)
            time.sleep(10)

        save_to_json(all_tweets, os.path.join(BASE_FOLDER, f"tweets_{DATE_TAG}.json"))
        save_to_csv(all_tweets, os.path.join(BASE_FOLDER, f"tweets_{DATE_TAG}.csv"))
        print("✅ 所有事件处理完成！")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
