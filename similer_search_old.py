import streamlit as st 
import asyncio
import aiohttp
import random
import requests
import os, re
from database import *  # this contains the necessary database operations
from final_vectore import *
from nltk.tag import pos_tag
from dotenv import load_dotenv
from pinecone import Pinecone
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sentence_transformers import SentenceTransformer
from comparing_answer import * # for similarity search

# Load the .env file
load_dotenv()

# Initialize Pinecone
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_names = ["websitetext", "quranx", "equran","surahquran","dorarnet","quranxquran"]

# Initialize the model for converting text to vectors
model = SentenceTransformer('all-MiniLM-L6-v2')

# Streamlit UI
st.title("Chat with Me")

def extract_keywords(question):
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(question)
    filtered_tokens = [word for word in word_tokens if word.isalnum() and word.lower() not in stop_words]
    tagged_tokens = pos_tag(filtered_tokens)
    keywords = [word for word, tag in tagged_tokens if tag in ['NN', 'NNP', 'NNS', 'NNPS']]
    return keywords

ITEMS_PER_PAGE=5
async def query_index_async(index_name, query_vector_list):
    index = pc.Index(name=index_name)
    results = await asyncio.to_thread(index.query, vector=query_vector_list, top_k=5, include_metadata=True)
    return results

async def fetch_response(session, url, headers, data):
    async with session.post(url, headers=headers, json=data) as response:
        return await response.json()

def normalize_question(question):
    question = question.lower().strip()
    return question

async def handle_query(question):
    normalized_question = normalize_question(question)
    ans = similarity_search(normalized_question)
    query_vector = model.encode(normalized_question)
    query_vector_list = query_vector.tolist()

    all_results = []
    tasks = [query_index_async(index_name, query_vector_list) for index_name in index_names]
    query_results = await asyncio.gather(*tasks)

    for results in query_results:
        if results["matches"]:
            all_results.extend(results["matches"])
    random.shuffle(all_results)
    print(all_results)
    if not all_results:
        st.write("I don't know.")
    else:
        question_id = insert_question_once(normalized_question)
        document_ids = [hit["id"] for hit in all_results]
        # url = metadata.get("url", "URL not available")
        keywords = extract_keywords(normalized_question)
        metadata_list = [match.get("metadata", {}) for match in all_results]
        api_key = os.getenv('OpenAI_API_KEY')
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, (doc_id, metadata) in enumerate(zip(document_ids, metadata_list)):
                content = metadata.get("content", "content not available")
                prompt = f"Based on the following document:{doc_id,content}, answer the question: {normalized_question} "
                data = {
                    'model': "gpt-3.5-turbo",
                    'temperature': 0.5,
                    'max_tokens': 250,
                    'messages': [
                        {"role": "system", "content": "Provide answers to the question based solely on the provided document content without altering or manipulating the information of the document. Please analyze the provided document carefully. Respond with 'Don't know' for insufficient information or 'Document does not contain information' for unrelated content."},
                        {"role": "user", "content": prompt}
                    ],  
                }
                response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)

                # if 'responses' not in st.session_state or not st.session_state.responses:
                #     return
                if response.status_code == 200:
                    response_data = response.json()
                    text_data = response_data.get('choices', [])[0].get('message', {}).get('content', 'No response.')
                    if is_response_relevant(text_data, keywords):
                        # print("relevant:",is_response_relevant(text_data, keywords))
                        print(text_data)
                        st.session_state.responses.append({
                            "idx": idx+1,
                            "doc_id": doc_id,
                            "text_data": text_data
                        })
                        similarity_score = compute_similarities(ans, text_data)
                        similarity_score = similarity_score or 0.0
                        # if similarity_score < 0.60:
                        #     insert_answer(question_id, text_data, doc_id)
            st.session_state.page = 0
            st.session_state.total_pages = (len(st.session_state.responses) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

  

def is_response_relevant(response_text, keywords):
    negative_context_phrases = [
        r"did not have any\s+(?:\w+\s+){0,3}?mentioned",
        r"no mention of",
        r"only mentions",
        r"does not discuss",
        r"The document does not mention the",   
        r"lacks information on",
        r"without any details on",
        r"fails to provide",
        r"no details are given about",
        r"no information is provided on",
        r"there is no mention of",
        r"not discussed",
        r"not included",
        r"document does not",
        r"does not provide",
        r"omits",
        r"Don't know",
        r"does not directly",
        r"the document does not explicitly mention",
        r"no reference to",
        r"absent in the document",
        r"is not specified",
        r"it does not specify",
        r"The document does not provide information about",
        r"The document does not specify the exact",
        r"the document does not specify",
        r"is not explicitly mentioned",
        r"does not contain information",
        r"is not specified",
        r"is not mentioned ",
        r"does not contain ",
        r"not mentioned in provided",
    ]
    combined_pattern = r'|'.join(negative_context_phrases)
    
    if re.search(combined_pattern, response_text, re.IGNORECASE):
        # print("response text:",response_text)
        for keyword in keywords:
            keyword_pattern = rf'\b{re.escape(keyword)}\b'
            if re.search(keyword_pattern, response_text, re.IGNORECASE):
                return False
        return False    
        
    return True



# Initialize session state variables
if 'responses' not in st.session_state:
    st.session_state.responses = []
if 'page' not in st.session_state:
    st.session_state.page = 0
if 'total_pages' not in st.session_state:
    st.session_state.total_pages = 0

# UI for the query input
question = st.text_input("Enter your question:", "")
if st.button("Submit"):
    st.session_state.responses = []  # Clear previous responses
    st.session_state.page =0  # Reset to the first page
    asyncio.run(handle_query(question))

# Pagination logic
# total_pages = (len(st.session_state.responses) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

if st.session_state.responses:
    st.session_state.total_pages = (len(st.session_state.responses) +  ITEMS_PER_PAGE - 1) //  ITEMS_PER_PAGE
def previous_page():
    if st.session_state.page > 0:
        st.session_state.page -= 1

def next_page():
    if st.session_state.page < st.session_state.total_pages - 1:
        st.session_state.page += 1
if st.session_state.responses:
    start_idx = st.session_state.page * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    for response in st.session_state.responses[start_idx:end_idx]:
        st.write(response["idx"])
        st.write(f"**URL:** {response['doc_id']}")
        st.write(f"**Response:** {response['text_data']}")

if st.session_state.responses:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.session_state.page > 0:
                st.button("Previous", on_click=previous_page)
        with col2:
            st.write(f"Page {st.session_state.page + 1} of {st.session_state.total_pages}")
        with col3:
            if st.session_state.page < st.session_state.total_pages - 1:
                st.button("Next", on_click=next_page)  

# if st.session_state.responses:
#     asyncio.run(handle_query(question))
