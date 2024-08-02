import asyncio
import scipy.spatial
from sentence_transformers import SentenceTransformer
# import streamlit as st
# from similer_search import *
# import pandas as pd

# Load the sentence transformer model
models = SentenceTransformer('all-MiniLM-L6-v2')



def compute_similarities(database_answers, openai_answers):
    # Generate embeddings for all answers
    similarity_score = None
    database_answers = [str(answer) for answer in database_answers]
    # print(database_answers)
    try:
        # Safely encode 'database_answers'
        
        db_embeddings = models.encode( database_answers)
        # Safely encode 'openai_answers'
        openai_embeddings = models.encode([openai_answers])[0] 

    except ValueError as e:
        print(f"Error: {e}")

    # Calculate the cosine similarity between each pair of answers
    for db_embedding in db_embeddings:
        similarity_score = 1 - scipy.spatial.distance.cosine(db_embedding, openai_embeddings)


    
    for db_index, db_answer in enumerate(database_answers):
        # similarity_score = similarity_matrix[db_index]
        # print(f"Database Answer {db_index+1}: {db_answer}")
        # print(f"  vs. OpenAI Answer: {openai_answers}")
        # print(f"  SIMILARITY SCORE: {similarity_score:.4f}")
        # print("-" * 50)
        similarity_score = similarity_score or 0.0
        if similarity_score > 0.60:
         # Add a row for each comparison with similarity score greater than 0.50
            print("answers are similer")
            
        else:
            print("No matches were found.")
    print("-" * 100)
    return similarity_score 

async def compute_similarities_async(database_answers, openai_answers):
    loop = asyncio.get_event_loop()
    similarity_score = await loop.run_in_executor(None, compute_similarities, database_answers, openai_answers)
    return similarity_score       
    # Display answers with their similarity scores
    # data_rows = []

    # for db_index, db_answer in enumerate(database_answers):
    #     print(f"Database Answer {db_index+1}: {db_answer}")
    #     for openai_index, openai_answer in enumerate(openai_answers):
    #         similarity_score = similarity_matrix[db_index][openai_index]
    #         print(f"  vs. OpenAI Answer {openai_index+1}: {openai_answer}")
    #         print(f"  SIMILARITY SCORE: {similarity_score:.4f}")
    #         print("-" * 50)
    #     # Add a row for each comparison
    #         if similarity_score > 0.60:
    #             # Add a row for each comparison with similarity score greater than 0.50
    #             data_rows.append({
    #                 "Database Answer": f"Answer {db_index + 1}: {db_answer}",
    #                 "OpenAI Answer": f"Answer {openai_index + 1}: {openai_answer}",
    #                 "Similarity Score": similarity_score
    #             })
    #             print("answers are similer")
    #             return similarity_score
    #         else:
    #             print("No matches were found.")
    #             return
# Convert the list of rows to a DataFrame
    # if data_rows:
    #     df = pd.DataFrame(data_rows)
    #     # Display the DataFrame
    #     st.table(df)
    #     return similarity_score
    

    
# Display the DataFrame using st.table or st.dataframe
    # st.table(df)




#     # Display answers with their similarity scores
#     for db_index, db_answer in enumerate(database_answers):
#         print(f"Database Answer {db_index+1}: {db_answer}")
#         for openai_index, openai_answer in enumerate(openai_answers):
#             similarity_score = similarity_matrix[db_index][openai_index]
#             print(f"  vs. OpenAI Answer {openai_index+1}: {openai_answer}")
#             print(f"  SIMILARITY SCORE: {similarity_score:.4f}")
#             print("-" * 50)
#         print("-" * 150)
#     # return similarity_score

# # Example usage with multiple answers





