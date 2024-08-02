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

# Load the .env file from the current directory
load_dotenv()

session=requests.Session()

driver = webdriver.Chrome()

# Access variables using os.getenv()
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "equran"
vector_dimension = 384
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=vector_dimension,
        metric="cosine",  
        spec=ServerlessSpec(
            cloud="aws",
            region="us-east-1"  
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


def is_error_report_link(link):
    # Returns True if the link is an error report link, otherwise False
    return '/en/error-report','/feedback/error-report' in link

def scrape_text_from_link(url):
    print(url)
    transliteration=""
    content = fetch_page_content(url )
    all_content=[]
    if content :
        soup = BeautifulSoup(content, 'html.parser')
        
        # Hadith Text Scrape
        div=soup.find('div',class_='small-12 medium-10 medium-offset-1 large-8 large-offset-2 container-column columns')
        # print(div)
        if div is not None:
            divsen=soup.find('div',class_='translation-english small-12 columns')
            if divsen:
                transliteration = [elem.get_text() for elem in divsen.find_all('span',class_='translation-english preformatted hadith-text')]
                # print(transliteration) 
                all_content.extend(transliteration)

            divs=soup.find('div',class_='text-hadith small-12 columns center-justified mr-top-15')
            if divs:
                texts=[elem.get_text() for elem in divs.find_all('span',dir='rtl')]
                # print(texts)
                all_content.extend(texts)


            muslim=soup.find('div',class_='translation small-12 columns center-justified')
        # print(muslim)
            if muslim is not None:
                muslims=[elem.get_text() for elem in muslim.find_all('span',dir='rtl')]
                # print(muslims)
                all_content.extend(muslims)

              

        #quran Text Scrape    text center-justified
        quran=soup.find('div',class_='padding10px') 
        # print(quran) 
        if quran is not None:
            text=[elem.get_text() for elem in quran.find_all('span',dir='rtl')]
            
            all_content.extend(text)
            # print(all_content)
        
        
        combined_content = ' '.join(all_content)      
        MAX_CONTENT_SIZE = 1000
        vector = text_to_vector(combined_content)
        if(len(combined_content)>MAX_CONTENT_SIZE):   
            content_to_store = combined_content[:MAX_CONTENT_SIZE]
        else:
                content_to_store = combined_content  
        metadata = {'url': url,'content':content_to_store} 
        
        # Insert into Pinecone (using URL as ID for simplicity)
        if is_quran_page_link(url):
            print(content_to_store)
            index.upsert(vectors=[(url, vector, metadata)])
            print(f"Inserted text vector from  {url}  into Pinecone.")
            print("--------------------------------------------------------------------------------------------------")
                        
                        

                        # combined_content = ' '.join(all_content)
                        # print(texts)
        # return combined_content
                        # print(f"Text from {url}:\n{combined_content}")  # Print first 500 characters for brevity
    else:
        print(f"Failed to fetch content from {url}")


def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    # Check if the link is not an error report link and belongs to the base domain
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain 

def is_unwanted_link(link):

        unwanted_paths = ['/Help','/Search','/About','/Analysis/','/azkaarchapters/','/history', '/duas/',
                           '/cdn-cgi','/searchtips','/news','changelog','narrator/','/translation',"/id/index.php?page=contactus",
                      '/seerahbooks','/fiqhchapters','/preferences','https://quranicaudio.com','/blogs',"/appendix",
                      "/tafsir",'/kids-quran','/references','/rss.xml','/node','/service','/mobile-app','/funeral-services','/about-us',
                      '/tafseer','developers',"/articles/","/ebooks/",'/widgets/','/ad-plans',"/prayertimes",'/faq','/surah-info',
                        '#0','c','/s','/about','/azkaar/','/alltafaseer/','/wordbyword/','/alltafaseer','/azkaarbooks',
                        '/hadithchapters/',"/support", "/developers", "/contact","/ar","/es","/de","/fr",
                        "https://www.facebook.com/Sunnahcom-104172848076350", "https://www.instagram.com/_sunnahcom/", 
                      "https://twitter.com/SunnahCom", "https://statcounter.com/","/donate",'/get-involved','/infographics/',
                      
                      
                      ]
        return any(unwanted_path in link for unwanted_path in unwanted_paths)

def is_quran_page_link(link):
    return re.match(r'^https://equranlibrary\.com/quran/\d+$', link) or re.match(r'^https://equranlibrary\.com/hadith/abudawood/\d+/\d+$', link) 

def crawl_website(start_url, max_depth=5):   
    visited = set()
    stack = [(start_url, 0)]
    while stack:
        url, depth = stack.pop()
        if url in visited or depth > max_depth:  # Corrected logical condition
            continue
        visited.add(url)
        # print(f"Visiting: {url}")  # Debug output
        content = fetch_page_content(url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            scrape_text_from_link(url)  # Process the current page
            for link in links:
                full_link = urljoin(url, link)
                if not is_unwanted_link(link) and is_valid_url(full_link, base_domain) and full_link not in visited:
                    # print(f"Queueing: {full_link}")  # Debug output
                    stack.append((full_link, depth + 1))

if __name__ == "__main__":
    driver = webdriver.Chrome()
    start_url = 'https://equranlibrary.com/hadithchapters/abudawood'
    with requests.Session() as session:
        crawl_website(start_url)
    driver.quit()
