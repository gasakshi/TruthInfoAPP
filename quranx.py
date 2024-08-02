import requests
from bs4 import BeautifulSoup
from selenium import webdriver
import os
import json
from urllib.parse import urljoin, urlparse
import re
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, PodSpec, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize necessary variables
session = requests.Session()
driver = webdriver.Chrome()
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "quranx"
vector_dimension = 384

# Create index if it doesn't exist
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



def is_unwanted_url(link):
    unwanted_patterns = [r'/analysis/-?\d+(\.\d+)?', r'/tafsirs/-?\d+(\.\d+)?']
    return any(re.search(pattern, link) for pattern in unwanted_patterns)

def is_unwanted_link(link):
    unwanted_paths = [
        '/Tafsirs', '/Help', '/Search', '/About', '/Analysis/', '/azkaarchapters/', '/history', '/duas/', '/cdn-cgi',
        '/searchtips', '/news', 'changelog', 'narrator/', '/translation', '/seerahbooks', '/fiqhchapters', 
        '/preferences', 'https://quranicaudio.com', '/blogs', "/appendix", "/tafsir", '/kids-quran', '/references', 
        '/rss.xml', '/node', '/service', 'developers', "/articles/", "/ebooks/", '/widgets/', '/ad-plans', '/mobile-app', 
        '/funeral-services', '/about-us', '#0', 'c', '/s', '/about', '/azkaar/', '/alltafaseer/', '/wordbyword/', 
        '/alltafaseer', '/azkaarbooks', '/home', '/hadithchapters/', "/support", "/developers", "/contact", "/ar", 
        "/es", "/de", "/fr", "/prayertimes", "/id/index.php?page=contactus", 
        "https://www.facebook.com/Sunnahcom-104172848076350", "https://www.instagram.com/_sunnahcom/", '/faq', 
        '/surah-info', "https://twitter.com/SunnahCom", "https://statcounter.com/", '/donate', '/get-involved', 
        '/infographics/'
    ]
    return any(unwanted_path in link for unwanted_path in unwanted_paths)

def scrape_text_from_link(url):
    # print(url)
    content = fetch_page_content(url)
    all_content = []
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        hadith = soup.find('div', class_='hadith')
        # print(hadith)
        if hadith is not None:
            nos = [elem.get_text() for elem in hadith.find('div', class_='hadith__reference-value')]
            text_details_div = hadith.find('div', class_='hadith__text')
            # print(text_details_div)
            if text_details_div: 
                paragraphs = text_details_div.find_all('p')
                # print(paragraphs)
                for p in paragraphs:
                    all_content.append(p.get_text().strip()) 
                # print(all_content)
            text_details_divs = hadith.find('div', class_='hadith__text arabic')
            if text_details_divs: 
                arebic = text_details_divs.find_all('p')
                for p in arebic:
                    all_content.append(p.get_text().strip()) 
            print(all_content)
        combined_content = ' '.join(all_content)
        MAX_CONTENT_SIZE = 1000
        vector = text_to_vector(combined_content)
        if len(combined_content) > MAX_CONTENT_SIZE:
            content_to_store = combined_content[:MAX_CONTENT_SIZE]
        else:
            content_to_store = combined_content  
        metadata = {'url': url, 'content': content_to_store}
        if is_quran_page_link(url):
            index.upsert(vectors=[(url, vector, metadata)])
            print(f"Inserted text vector from {url} into Pinecone.")
    else:
        print(f"Failed to fetch content from {url}")

def is_valid_url(url, base_domain):
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and is_quran_page_link(url) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain and not is_unwanted_url(url) 

def crawl_website(start_url, session, max_depth=5):
    visited = set()
    stack = [(start_url, 0)]

    while stack:
        url, depth = stack.pop()
        if url in visited or depth > max_depth:
            continue

        visited.add(url)
        content = fetch_page_content(url)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            base_domain = urlparse(url).netloc
            scrape_text_from_link(url)
            for link in links:
                full_link = urljoin(url, link)
                if not is_unwanted_link(link) and is_valid_url(full_link, base_domain) and full_link not in visited:
                    stack.append((full_link, depth + 1))

def is_quran_page_link(link):
    
    return re.match(r'^https:\/\/quranx\.com\/hadith\/Nasai\/In-Book\/Book-\d+\/Hadith-\d+\/$', link)  
if __name__ == "__main__":
    
    starting_url = 'https://quranx.com/hadith/Nasai/In-Book/Book-20/Hadith-1/'
    with requests.Session() as session:
        crawl_website(starting_url, session)
