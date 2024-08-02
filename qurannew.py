import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
import os
import re
import time
from dotenv import load_dotenv

# Load the .env file from the current directory
load_dotenv()

# Access variables using os.getenv()
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "quranxquran"
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

# Connect to the Pinecone index
index = pc.Index(name=index_name)

model = SentenceTransformer('all-MiniLM-L6-v2')
def text_to_vector(text):
    return model.encode(text)

# Initialize a requests session
session = requests.Session()
def is_quran_page_link(link):
    # This regular expression should match the pattern of the Quran pages' URLs
    # Update this regex to fit the URL pattern of Quran pages you are interested in
    # return not re.search(r'/hadith/+/Shamail/English/Book-\d+/Hadith-\d+/', link)
    return re.match(r'^https:\/\/quranx\.com\/\d+\.\d+$', link)
def scrape_text_from_link(url,session):
    # print(url)
    content = fetch_page_content(url ,session)
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
                all_content.extend(verses)
            divs =  soup.find('dd', class_='arabic highlightable')
            if divs is not None:
                text=divs.get_text(strip=True)
                print(text)
                all_content.extend(text)

            pickthall_div = soup.find('dl', {'data-translator-code': "Pickthall"})
            if pickthall_div is not None:
                pickthall_text = pickthall_div.get_text(strip=True)
                print(pickthall_text)
                all_content.extend([pickthall_text])

            qarai_div = soup.find('dl', {'data-translator-code': "Qarai"})
            if qarai_div is not None:
                qarai_text = qarai_div.get_text(strip=True)
                print(qarai_text)
                all_content.extend([qarai_text])
            
        
            combined_content = ' '.join(all_content)
            if combined_content:  # Check if combined_content is not None or empty
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


def fetch_page_content(url, session):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        # time.sleep(1)  # Sleep for 1 second before making a request
        response = session.get(url, headers=headers)
        response.raise_for_status()  # Raises an HTTPError if the response status code is 4XX or 5XX
        return response.content
    except requests.RequestException as e:
        print(f"Request failed: {e}")
        return None

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
def is_valid_url(url, base_domain):
    """Checks if a URL is valid and belongs to the same domain as the base domain."""
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain 

def crawl_website(start_url, session, max_depth=5):   
    """Crawls a website from a starting URL, visiting all unique links within the same domain."""
    
    visited = set()
    
    stack = [(start_url, 0)]  # Stack of URLs to visit, each with their corresponding depth
    # Add explicit URLs for Quran chapters from 1 to 114
    for chapter in range(2, 7):
        for verse in range(1, 300):  # Assuming the maximum number of verses in a chapter is 286
            chapter_url = f'https://quranx.com/{chapter}.{verse}'
            stack.append((chapter_url, 0))

    while stack:
        url, depth = stack.pop()
        if url in visited and depth > max_depth:
            continue

        visited.add(url)
        content = fetch_page_content(url, session)
        if content:
            soup = BeautifulSoup(content, 'html.parser')
            base_domain = urlparse(url).netloc
            links = [a.get('href') for a in soup.find_all('a', href=True)]
            # print(links)
            scrape_text_from_link(url, session)
            for link in links:
                full_link = urljoin(url, link)
                # print(full_link)
                # Ensure the link is not unwanted, is valid, and has not been visited
                if not is_unwanted_link(link) and is_valid_url(full_link, base_domain) and full_link not in visited :
                    # print(full_link)
                    stack.append((full_link, depth + 1))

# Start the crawl
if __name__ == "__main__":
    starting_url = 'https://quranx.com/'
    with requests.Session() as session:
        crawl_website(starting_url, session)