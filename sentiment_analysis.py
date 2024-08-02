import streamlit as st
from transformers import pipeline
from dotenv import load_dotenv
load_dotenv()

# Load the pre-trained sentiment analysis model
sentiment_pipeline = pipeline("sentiment-analysis")

# Function to analyze sentiment and provide chatbot response
def analyze_sentiment_and_respond(user_message):
    sentiment = sentiment_pipeline(user_message)[0]
    if sentiment['label'] == 'NEGATIVE':
        return "I understand you're upset. Let me connect you to a human agent."
    else:
        return "Thank you for your feedback. How can I assist you further?"

st.title("Customer Service Chatbot")
user_input = st.text_input("Enter your message:")
if st.button("Send"):
    response = analyze_sentiment_and_respond(user_input)
    st.write(f"Chatbot: {response}")
