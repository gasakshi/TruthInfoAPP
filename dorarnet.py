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
index_name = "dorarnet"
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
    # return re.search(r'/tafseer/\d+$', link) is not None
    return re.search(r'^https:\/\/dorar\.net\/en\/ahadith\?page=\d+$', link) is not None

def is_error_report_link(link):
    # Returns True if the link is an error report link, otherwise False
    return '/en/error-report','/feedback/error-report' in link

def scrape_text_from_link(url):
    print(url)
    content = fetch_page_content(url )
    all_content=[]
    if content :
        soup = BeautifulSoup(content, 'html.parser')
        # print(soup)
        # divs = [elem.get_text() for elem in soup.find_all ('p', class_='pt-1 text-justify')]
        # print(divs)
        divs=soup.find('div',class_='card-body')
        if divs is not None:
            # text=divs.get_text(strip=True)
            transliterations = [elem.get_text() for elem in divs.find_all('div',class_='custom_number')]
            print(transliterations)  
        # all_content.extend(transliterations)
            transliteration = [elem.get_text() for elem in divs.find_all('h5',class_='px-3 card-title third_text_color card_custom_surah')]
            print(transliteration)  
        # all_content.extend(transliteration)  
        # combined_content = ' '.join(all_content)      
        # MAX_CONTENT_SIZE = 1000
        # vector = text_to_vector(combined_content)
        # if(len(combined_content)>MAX_CONTENT_SIZE):
        #     content_to_store = combined_content[:MAX_CONTENT_SIZE]
        # else:
        #     content_to_store = combined_content  
        # metadata = {'url': url,'title':divs,'content':content_to_store} 
        #                 # Insert into Pinecone (using URL as ID for simplicity)
        
        # index.upsert(vectors=[(url, vector, metadata)])
        # print(f"Inserted text vector from  {url}  into Pinecone.")
    
                        
                        

                        # combined_content = ' '.join(all_content)
                        # print(texts)
        # return combined_content
                        # print(f"Text from {url}:\n{combined_content}")  # Print first 500 characters for brevity
    else:
        print(f"Failed to fetch content from {url}")


def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    # Check if the link is not an error report link and belongs to the base domain
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain and not is_error_report_link(url)


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
                if  is_valid_url(full_link, base_domain) and full_link not in visited:
                    # print(f"Queueing: {full_link}")  # Debug output
                    stack.append((full_link, depth + 1))

if __name__ == "__main__":
    driver = webdriver.Chrome()
    start_url = 'https://dorar.net/'
    with requests.Session() as session:
        crawl_website(start_url)
    driver.quit()
