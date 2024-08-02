import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, PodSpec
import os
import re
import time
from dotenv import load_dotenv

# Load the .env file from the current directory
load_dotenv()

# Access variables using os.getenv()
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "websitetext"
vector_dimension = 384
if index_name not in pc.list_indexes().names():
    pc.create_index(
        name=index_name,
        dimension=vector_dimension,
        metric="cosine",  # or "euclidean", depending on your use case
        spec=PodSpec(
            pod_type="starter",
            environment="gcp-starter"  # Choose the region that is closest to you or your users
        )
    )

# Connect to the Pinecone index
index = pc.Index(name=index_name)

model = SentenceTransformer('all-MiniLM-L6-v2')
def text_to_vector(text):
    return model.encode(text)

# Initialize a requests session
session = requests.Session()

# Initialize the model for converting text to vectors (ensure consistency with your indexing process)
def scrape_text_from_link(url, session):
    content = fetch_page_content(url, session)
    all_content=[]
    if content:
        soup = BeautifulSoup(content, 'html.parser')
        # print(soup)
        text_details_div = soup.find('div', class_='text_details')
        if text_details_div:
            # Capture text directly in the div, not within a nested tag
            for content in text_details_div.contents:
                if isinstance(content, NavigableString) and content.strip():
                    all_content.append(content.strip())
    
    # Capture text from <p> tags within the div
            paragraphs = text_details_div.find_all('p')
            for p in paragraphs:
                all_content.append(p.get_text().strip())

        else:
            paragraphs = []        
        # print(paragraphs)
        # all_content.extend(paragraphs)

# Extract text from elements with class 'transliteration'
        transliterations = [elem.get_text() for elem in soup.find_all(class_='transliteration')]
        all_content.extend(transliterations)

# Extract text from elements with class 'translation'
        translations = [elem.get_text() for elem in soup.find_all(class_='translation')]
        all_content.extend(translations)
        # references = [elem.get_text() for elem in soup.find_all(class_='hadith_reference')]
        # all_content.extend(references)

        title=[elem.get_text() for elem in soup.find_all(class_='chapter')]
        # all_content.extend(title)
        grade=[elem.get_text() for elem in soup.find_all(class_='gradetable')]
        all_content.extend(grade)
# Combine all collected content into a single string
        combined_content = ' '.join(all_content)
        # print(combined_content)
# Generate a vector from the combined content
        MAX_CONTENT_SIZE = 1000
        vector = text_to_vector(combined_content)
        if(len(combined_content)>MAX_CONTENT_SIZE):
            content_to_store = combined_content[:MAX_CONTENT_SIZE]
        else:
            content_to_store = combined_content
        metadata = {'url': url,'title':title,'content':content_to_store,'grade':grade}
        print(metadata)
        # Insert into Pinecone (using URL as ID for simplicity)
        index.upsert(vectors=[(url, vector,metadata)])
        print(f"Inserted text vector from {url} into Pinecone.")
        # all_content.append(content)

        # combined_content = ' '.join(all_content)
        # print(texts)
        # return combined_content
    #     # print(f"Text from {url}:\n{combined_content}")  # Print first 500 characters for brevity
    # else:
    #     print(f"Failed to fetch content from {url}")


# def is_desired_format(url):
#     # This regex checks if the URL follows a specific pattern without a colon in the specific part
#     pattern = r'https://sunnah\.com/([^/:]+)(/\d+)?($)'
#     match = re.search(pattern, url)
#     if match:
#         print(f"Matched URL: {url}")  # Debugging output
#         return True
# Example of creating a document ID with embedded URL info
def create_document_id(url):
    unique_identifier = hash(url)  # Simplified; consider a more collision-resistant approach
    return f"{unique_identifier}_{url}"

        
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
    """Check if the link contains one of the undesired paths."""
    unwanted_paths = ['https://sunnah.com/about', 'https://sunnah.com/contact', 'https://sunnah.com/privacy','https://sunnah.com/searchtips','https://sunnah.com/news','changelog','narrator/',
                      'https://quranicaudio.com','https://salah.com'
                      'https://quran.com','https://sunnah.com/developers','https://sunnah.com/support',
                        "/support", "/developers", "/contact",'/support','/developers','/about', '/news',
                        "https://www.facebook.com/Sunnahcom-104172848076350", "https://www.instagram.com/_sunnahcom/", 
                      "https://twitter.com/SunnahCom", "https://statcounter.com/"]  # Add more paths as needed
    return any(unwanted_path in link for unwanted_path in unwanted_paths)
def is_valid_url(url, base_domain):
    """Checks if a URL is valid and belongs to the same domain as the base domain."""
    parsed_url = urlparse(url)
    return bool(parsed_url.scheme) and bool(parsed_url.netloc) and parsed_url.netloc == base_domain

def crawl_website(start_url, session, max_depth=5):   
    """Crawls a website from a starting URL, visiting all unique links within the same domain."""
    
    visited = set()
    
    stack = [(start_url, 0)]  # Stack of URLs to visit, each with their corresponding depth

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
            scrape_text_from_link(url, session)
            for link in links:
                full_link = urljoin(url, link)
                # Ensure the link is not unwanted, is valid, and has not been visited
                if not is_unwanted_link(full_link) and is_valid_url(full_link, base_domain) and full_link not in visited :
                    # print(full_link)  # or process it as needed
                    stack.append((full_link, depth + 1))

# Start the crawl
if __name__ == "__main__":
    starting_url = 'https://sunnah.com/abudawud:5274'
    with requests.Session() as session:
        crawl_website(starting_url, session)