import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import os
import json
from urllib.parse import urljoin, urlparse
import re

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, PodSpec,ServerlessSpec
from selenium import webdriver
import os,bs4
import itertools
from dotenv import load_dotenv
load_dotenv()


# url = 'https://sunnah.com'
session=requests.Session()

driver = webdriver.Chrome()
Pincone_API_KEY = os.getenv("pincone_API_KEY")
# Pincone_API_KEY='530ba1af-e67f-47c0-8bbc-81bb5fbc185d'
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "quranx"
vector_dimension = 384
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=vector_dimension,
        metric="cosine",  # or "euclidean", depending on your use case
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"  # Choose the region that is closest to you or your users
        )
    )
index = pc.Index(name=index_name)

model = SentenceTransformer('all-MiniLM-L6-v2')
def text_to_vector(text):
    return model.encode(text)
def fetch_page_content(url):
    try:
        driver.get(url)
        return driver.page_source
    except Exception as e:
        print(f"Failed to fetch page using Selenium: {e}")
        return None

def is_quran_page_link(link):
    # This regular expression should match the pattern of the Quran pages' URLs
    # Update this regex to fit the URL pattern of Quran pages you are interested in
    # return not re.search(r'/hadith/+/Shamail/English/Book-\d+/Hadith-\d+/', link)
    return re.match(r'^https:\/\/quranx\.com\/\d+\.\d+$', link)

def is_unwanted_url(link):
    # Define patterns to exclude specific URLs
    unwanted_patterns = [r'/analysis/-?\d+(\.\d+)?',r'/tafsirs/-?\d+(\.\d+)?']
    return any(re.search(pattern, link) for pattern in unwanted_patterns)


def is_unwanted_link(link):

        unwanted_paths = ['/Tafsirs','/Help','/Search','/About','/Analysis/','/azkaarchapters/','/history', '/duas/', 
                          '/cdn-cgi','/searchtips','/news','changelog','narrator/','/translation',"/donate",
                      '/seerahbooks','/fiqhchapters','/preferences','https://quranicaudio.com','/blogs','/hadiths/',
                      "/appendix","/tafsir",'/kids-quran','/references','/rss.xml','/node','/service',
                      '/hadith','/Hadith','developers',"/articles/","/ebooks/",'/widgets/','/ad-plans',
                      '/mobile-app','/funeral-services','/about-us','#0','c','/s','/get-involved','/infographics/',
                        '/about','/azkaar/','/alltafaseer/','/wordbyword/','/alltafaseer','/azkaarbooks','/home',
                        '/hadithchapters/',"/support", "/developers", "/contact","/ar","/es","/de","/fr",
                        "/prayertimes","/id/index.php?page=contactus","https://www.facebook.com/Sunnahcom-104172848076350"
                        , "https://www.instagram.com/_sunnahcom/",'/faq','/surah-info', 
                      "https://twitter.com/SunnahCom", "https://statcounter.com/",
                      
                      
                      ]
        return any(unwanted_path in link for unwanted_path in unwanted_paths)

def scrape_text_from_link(url):
    print(url)
    content = fetch_page_content(url )
    all_content=[]
    if content :
        soup = BeautifulSoup(content, 'html.parser')
        # print(soup)

        verse=soup.find('div',class_='container-fluid body-content pt')
        
        if verse is not None:
            
            vers=verse.find('span',class_='verse__reference')
            if vers is not None:
                verses=vers.get_text(strip=True)
                print(verses)
            divs =  soup.find('dd', class_='arabic highlightable')
            if divs is not None:
                text=divs.get_text(strip=True)
                print(text)

        # hadith=soup.find('div',class_='hadith')
        # if hadith:
        #     nos=[elem.get_text() for elem in hadith.find('div',class_='hadith__reference-value')]
        #     print(nos)
        #     text_details_div = hadith.find('div', class_='hadith__text')
        #     if text_details_div: 
        #         paragraphs = text_details_div.find_all('p')
        #         for p in paragraphs:
        #             all_content.append(p.get_text().strip()) 
        #         # print(all_content)  
            
        #     text_details_divs = hadith.find('div', class_='hadith__text arabic')
        #     if text_details_divs: 
        #         arebic = text_details_divs.find_all('p')
        #         for p in arebic:
        #             all_content.append(p.get_text().strip()) 
        #     print(all_content)
        # combined_content = ' '.join(all_content)      
        # MAX_CONTENT_SIZE = 1000
        # vector = text_to_vector(combined_content)
        # if(len(combined_content)>MAX_CONTENT_SIZE):
        #     content_to_store = combined_content[:MAX_CONTENT_SIZE]
        # else:
        #     content_to_store = combined_content  
# 
        # metadata = {'url': url,'content':content_to_store} 
        #                 # Insert into Pinecone (using URL as ID for simplicity)
        # if not is_quran_page_link(url):
        #     index.upsert(vectors=[(url, vector, metadata)])
        #     print(f"Inserted text vector from  {url}  into Pinecone.")
    
                        
                        

                        # combined_content = ' '.join(all_content)
                        # print(texts)
        # return combined_content
                        # print(f"Text from {url}:\n{combined_content}")  # Print first 500 characters for brevity
    else:
        print(f"Failed to fetch content from {url}")


def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain and not is_unwanted_url(url) 

def crawl_website(start_url, session, max_depth=5):
    visited = set()
    stack = [(start_url, 0)]  # Stack of URLs to visit, each with their corresponding depth

    while stack:
        url, depth = stack.pop()
        if url in visited or depth > max_depth:  # Corrected condition to skip visited URLs or URLs beyond max depth
            continue

        visited.add(url)
        content = fetch_page_content(url)
        if content :
            # print(url)  # Moved URL printing here to ensure uniqueness
            soup = BeautifulSoup(content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            
            scrape_text_from_link(url)
            for link in links:
                full_link = urljoin(url, link)
                # print(full_link)
                if not is_unwanted_link(link)and is_valid_url(full_link, base_domain) and full_link not in visited :
                    stack.append((full_link, depth + 1))
                    # print(full_link)

if __name__ == "__main__":
    starting_url = 'https://quranx.com/'
    with requests.Session() as session:
        crawl_website(starting_url, session)
