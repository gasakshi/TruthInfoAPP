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
# from transformers import pipeline
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from sentence_transformers import SentenceTransformer
from comparing_answer import * # for similarity search
import nltk
# Load the .env file
load_dotenv()

# Initialize Pinecone
Pincone_API_KEY = os.getenv("pincone_API_KEY")
pc = Pinecone(api_key=Pincone_API_KEY)
index_names = ["websitetext", "quranx", "equran","quranxquran","dorarnet"]
# index_names = [ "surahquran","quranxquran","dorarnet"]

# Initialize the model for converting text to vectors
model = SentenceTransformer('all-MiniLM-L6-v2')
# nltk.download('vader_lexicon')
# Streamlit UI
st.title("Chat with Me")

def extract_keywords(question):
    stop_words = set(stopwords.words('english'))
    word_tokens = word_tokenize(question)
    
    filtered_tokens = [word for word in word_tokens if word.isalnum() and word.lower() not in stop_words]
    tagged_tokens = pos_tag(filtered_tokens)
    keywords = [word for word, tag in tagged_tokens if tag in ['NN', 'NNP', 'NNS', 'NNPS', 'JJ', 'VBG', 'VB', 'VBD', 'VBN', 'VBP', 'VBZ', 'PRP']]
    return keywords

ITEMS_PER_PAGE=5
async def query_index_async(index_name, query_vector_list):
    index = pc.Index(name=index_name)
    results = await asyncio.to_thread(index.query, vector=query_vector_list, top_k=30, include_metadata=True)
    return results

async def fetch_response(session, url, headers, data):
    async with session.post(url, headers=headers, json=data) as response:
        return await response.json()

def normalize_question(question):
    question = question.lower().strip()
    return question

async def handle_query(question):
    normalized_question = normalize_question(question)
    question_sentiment = get_sentiment(normalized_question)
    print("Question Sentiment:", question_sentiment)
    ans = similarity_search(normalized_question)
    query_vector = model.encode(normalized_question)
    query_vector_list = query_vector.tolist()

    all_results = []
    tasks = [query_index_async(index_name, query_vector_list) for index_name in index_names]
    query_results = await asyncio.gather(*tasks)
    # print("query result: ",query_results)
    for results in query_results:
        if results["matches"]:
            all_results.extend(results["matches"])
    random.shuffle(all_results)
    # print(all_results)
    if not all_results:
        st.write("I don't know.")
    else:
        question_id = insert_question_once(normalized_question)
        document_ids = [hit["id"] for hit in all_results]
        # url = metadata.get("url", "URL not available")
        keywords = extract_keywords(normalized_question)
        # print(keywords)
       
        metadata_list = [match.get("metadata", {}) for match in all_results]
        api_key = os.getenv('OpenAI_API_KEY')
        headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}

        async with aiohttp.ClientSession() as session:
            tasks = []
            for idx, (doc_id, metadata) in enumerate(zip(document_ids, metadata_list)):
                content = metadata.get("content", "content not available")
                grade = metadata.get("grade", "grade not available")
                if isinstance(grade, list) and len(grade) > 0:
                    grade = grade[0]
                elif not isinstance(grade, str):
                    grade = str(grade)
                match = re.search(r'Grade:\xa0(.+?)\xa0', grade)
                
                if match:
                    grade = match.group(1)

                prompt = f"Based on the following document(ID:{doc_id}),answer the question strictly using only the provided document content:\n\n{content}\n\nQuestion:{normalized_question} "
                data = {
                    'model': "gpt-3.5-turbo",
                    'temperature': 0.5,
                    'max_tokens': 250,
                    'messages': [
                        {"role": "system", "content": "You are a helpful assistent. Provide answers to the question based solely on the provided document content without altering or manipulating the information of the document. Please analyze the provided document carefully. Respond with 'Don't know' for insufficient information or 'Document does not contain information' for unrelated content."},
                        {"role": "user", "content": prompt}
                    ],  
                }
                response = requests.post('https://api.openai.com/v1/chat/completions', headers=headers, json=data)
                # print(response)
                # if 'responses' not in st.session_state or not st.session_state.responses:
                #     return
                if response.status_code == 200:
                    response_data = response.json()
                    text_data = response_data.get('choices', [])[0].get('message', {}).get('content', 'No response.')
                    # print(doc_id)
                    # print(text_data)
                    # print(is_response_relevant(text_data, keywords, question_sentiment))
                    if is_response_relevant(text_data, keywords, question_sentiment):
                        # print(text_data)
                        # print("************************************************************")
                        st.session_state.responses.append({
                            "idx": idx+1,
                            "doc_id": doc_id,
                            "text_data": text_data
                        })
                        # similarity_score = compute_similarities(ans, text_data)
                        # similarity_score = similarity_score or 0.0
                        # if similarity_score < 0.60:
                        #     insert_answer(question_id, text_data, doc_id[idx])
            st.session_state.page = 0
            st.session_state.total_pages = (len(st.session_state.responses) + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

def get_sentiment(question):
    # negative_keywords = [ r"not permissible",r"forbidden",r"prohibited",r"not allowed",r"unacceptable",r"bad",r"poor",
    #                     r"horrible",r"terrible",r"awful",r"disgusting",r"hate",r"dislike",r"problem",
    #                     r"issue",r"fail",r"failure",r"worst",r"never",r"disappointed",r"dissatisfied",
    #                     r"not good",r"can't",r"shouldn't",r"won't",r"couldn't",r"don't",r"complaint",
    #                     r"regret",r"useless",r"waste",r"not telling"]
    positive_keywords = [r"permissible",r"halal",r"telling",r"allowed", r"acceptable",r"justifiable",r"good",r"great",
                        r"excellent",r"wonderful",r"fantastic",r"amazing",r"love",r"like",r"enjoy",r"happy",r"satisfied",
                        r"pleased", r"approved",r"successful",r"best",r"can",r"should",r"will",r"could",r"do",r"permitted",
                        r"encouraged",r"appreciated",r"beneficial",r"valuable",r"worthwhile"]
    
    negations = [r"not", r"never", r"no", r"none", r"nobody", r"nothing", r"neither", r"nowhere", r"hardly", r"scarcely", 
                 r"barely", r"can't", r"couldn't", r"don't", r"doesn't", r"didn't", r"isn't", r"aren't", r"wasn't", 
                 r"weren't", r"won't", r"wouldn't", r"shan't", r"shouldn't", r"mustn't", r"mightn't", r"wouldn't",r"haram"]
    # Normalize the question to lowercase for consistent matching
    negation_present = any(re.search(negation, question) for negation in negations)

    # for keyword in negative_keywords:
    #     if re.search(keyword, question):
    #         if negation_present:
    #             return "positive"
    #         return "negative"

    for keyword in positive_keywords:
        if re.search(keyword, question):
            if negation_present:
                return "negative"
            return "positive"
    
    # Default to neutral if no specific keywords are found
    return 'neutral'



def is_response_relevant(response_text, keywords, question_sentiment):
    phrases = [
        "did not have any mentioned", "no mention of", "only mentions", "does not discuss",
        "not considered", "The document does not mention the", "lacks information on",
        "without any details on", "fails to provide", "no details are given about",
        "no information is provided on", "there is no mention of", "not discussed",
        "not included", "document does not", "does not provide", "omits", "except",
        "Don't know", "does not directly", "the document does not explicitly mention",
        "no reference to", "absent in the document", "is not specified", "it does not specify",
        "The document does not provide information about", "The document does not specify the exact",
        "the document does not specify", "is not explicitly mentioned", "does not contain information",
        "is not specified", "is not mentioned", "does not contain", "not mentioned in provided"
    ]
    
    positive_context_phrases = [
        "is permissible", "halal", "is telling", "allowed", "acceptable", "good", "great",
        "excellent", "wonderful", "fantastic", "amazing", "love", "like", "enjoy", "happy", "satisfied",
        "pleased", "approved", "successful", "best", "can", "should", "will", "could", "do", "permitted",
        "encouraged", "appreciated", "beneficial", "valuable", "worthwhile","lawful"]

    negative_context_phrases = [
        "not permissible", "forbidden", "prohibited", "haram", "not allowed", "unacceptable", "bad", "poor",
        "horrible", "terrible", "awful", "disgusting", "hate", "dislike", "problem", "is not",
        "issue", "fail", "failure", "worst", "never", "disappointed", "dissatisfied",
        "not good", "can't", "shouldn't", "won't", "couldn't", "don't", "complaint",
        "regret", "useless", "waste", "not telling", "forbade"
    ]
    
    combined_negative_pattern = r'\b(?:' + '|'.join(negative_context_phrases)+ r')\b'
    combined_positive_pattern = r'\b(?:' + '|'.join(positive_context_phrases)+ r')\b'
    pattern = r'\b(?:' + '|'.join(phrases) + r')\b'
    
    # print(question_sentiment)
    
    if question_sentiment == 'positive':
        if re.search(combined_positive_pattern, response_text, re.IGNORECASE):
            # print("Positive context found")
            if not re.search(rf"{pattern}|{combined_negative_pattern}", response_text, re.IGNORECASE):
                # print("No negative patterns or specified phrases found")
                for keyword in keywords:
                    keyword_pattern = rf'\b{re.escape(keyword)}\b'
                    if re.search(keyword_pattern, response_text, re.IGNORECASE):
                        # print(f"Keyword found: {keyword}")
                        return True
                # print("No keywords found")
                return False
            else:
                # print("Negative patterns or specified phrases found")
                return False
        else:
            # print("No positive context found")
            return False       
        # if re.search(combined_positive_pattern, response_text, re.IGNORECASE):
        #     if re.search(rf"{pattern}|{combined_negative_pattern}", response_text, re.IGNORECASE):
        #         for keyword in keywords:
        #             keyword_pattern = rf'\b{re.escape(keyword)}\b'
        #             if re.search(keyword_pattern, response_text, re.IGNORECASE):
        #                 return False
        #         return False 
        #     return True
        
        
    elif question_sentiment == 'negative':    
            if re.search(combined_negative_pattern, response_text, re.IGNORECASE):
                if not re.search(pattern, response_text, re.IGNORECASE):
                    return True
            return False
                # for keyword in keywords:
                #     keyword_pattern = rf'\b{re.escape(keyword)}\b'
                #     if re.search(keyword_pattern, response_text, re.IGNORECASE):
                #         return True
                        
            
    elif question_sentiment == 'neutral':
        if re.search(pattern, response_text, re.IGNORECASE):
            # print("response text:",response_text)
            for keyword in keywords:
                keyword_pattern = rf'\b{re.escape(keyword)}\b'
                if re.search(keyword_pattern, response_text, re.IGNORECASE):
                    return False
            return False 
        return True
    return

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
