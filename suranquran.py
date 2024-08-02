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
index_name = "surahquran"
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
    # return  re.search(r'https://surahquran\.com/\d+\.html$', link) 
    return  re.search(r'https://surahquran\.com/English/\d+\.html$', link) 


def scrape_text_from_link(url):
    print(url)
    content = fetch_page_content(url )
    all_content=[]
    if content :
        soup = BeautifulSoup(content, 'html.parser')
        # print(soup)

        # verse=soup.find('div', style='font-size:2.2em;text-align:center;font-family:conv_original-hafs;color:#17274a;font-weight:400;line-height:1.65em;margin:0 0 1em')
        # verse=soup.find('div', style='font-size:2em;text-align:center;font-family:conv_original-hafs;color:#17274a;font-weight:400;line-height:1.5em;margin:0 0 1em')
        verse=soup.find('div', style='font-size:2.2em;text-align:justify;font-family:conv_original-hafs;color:#17274a;font-weight:400;line-height:1.65em;margin:0 0 1em')
                                        
        # print(verse)
        if verse is not None:
            vers=[elem.get_text() for elem in verse.find('br')]
            verses=verse.get_text(strip=True)
            print("verses",verses)
            print('vers',vers)
        # 
        # combined_content = ' '.join(all_content)      
            MAX_CONTENT_SIZE = 1000
            vector = text_to_vector(verses)
            if(len(verses)>MAX_CONTENT_SIZE):
                content_to_store = verses[:MAX_CONTENT_SIZE]
            else:
                content_to_store = verses  

            metadata = {'url': url,'content':content_to_store} 
                  
            if is_quran_page_link(url): # Insert into Pinecone (using URL as ID for simplicity)
                index.upsert(vectors=[(url, vector, metadata)])
                print(f"Inserted text vector from  {url}  into Pinecone.")
    
    else:
        print(f"Failed to fetch content from {url}")


def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain 

def crawl_website(start_url, session, max_depth=5):
    visited = set()
    stack = [(start_url, 0)]  # Stack of URLs to visit, each with their corresponding depth

    while stack:
        url, depth = stack.pop()
        if url in visited or depth > max_depth:  # Corrected condition to skip visited URLs or URLs beyond max depth
            continue

        visited.add(url)
        content = fetch_page_content(url)
        if content:
            # print(url)  # Moved URL printing here to ensure uniqueness
            soup = BeautifulSoup(content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            base_domain = urlparse(url).netloc
            scrape_text_from_link(url)
            for link in links:
                full_link = urljoin(url, link)
                # print(full_link)
                if is_quran_page_link(link) and is_valid_url(full_link, base_domain) and full_link not in visited:
                    stack.append((full_link, depth + 1))
                    # print(full_link)

if __name__ == "__main__":
    starting_url = 'https://surahquran.com/English/'
    with requests.Session() as session:
        crawl_website(starting_url, session)
