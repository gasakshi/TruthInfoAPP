import streamlit as st
# from similer_search import *
from database import fetch_qa,update_qa
from collections import defaultdict
from final_vectore import *


# fatch question and answers from databses
qa_data=fetch_qa()
# print(qa_data)
questions = defaultdict(list)
for item in qa_data:
    questions[item['q_id']].append((item['question'], item['answer'], item['a_id']))  # Assuming 'a_id' is available



# Initialize session state for pagination
if 'page' not in st.session_state:
    st.session_state.page = 0

# Determine the number of questions per page
questions_per_page = 10

# Calculate total number of pages
total_pages = len(questions) // questions_per_page + (1 if len(questions) % questions_per_page > 0 else 0)

# Select questions for the current page
start_index = st.session_state.page * questions_per_page
end_index = start_index + questions_per_page
current_page_questions = list(questions.items())[start_index:end_index]

# To keep track of user actions
action_tracker = {}
# Displaying the questions and answers
# for q_id, qa_pairs in questions.items():
#     question = qa_pairs[0][0]  # Assuming the first question is representative
#     st.subheader(f"Q{q_id}: {question}")


for q_id, qa_pairs in current_page_questions:
    question = qa_pairs[0][0]  # Assuming the first question is representative
    st.subheader(f"Q{q_id}: {question}")
    answer_selected = False

    for index, (question_text, answer, a_id) in enumerate(qa_pairs):
        checkbox_key = f"checkbox_{q_id}_{index}"  # Use index to ensure uniqueness
        comment_key = f"comment_{q_id}_{index}"  # Use index to ensure uniqueness
        # print(checkbox_key)
        # print(comment_key)

        if st.checkbox(answer, key=checkbox_key):
            answer_selected = True
            action_tracker[q_id] = ('vector', qa_pairs[0][0], answer,a_id)
    # for _, answer in qa_pairs:
    #     checkbox_key = f"{q_id}-{answer}"
    #     if st.checkbox(answer, key=checkbox_key):
    #         answer_selected = True
    #         action_tracker[q_id] = ('vector', question, answer)
            
    # Modified to include a unique key for each text_area
        # comment_key = f"comment_{q_id}_{a_id}"  # Use a_id for unique identification
        # print(comment_key)
        comment = st.text_area("Provide an example or further information:", key=comment_key)
        if comment:
            # Track comments for database updates
            # Assuming you're associating comments with answers, hence using a_id
            action_tracker[a_id] = ('database', comment)    

    # Check if the "Submit" button is clicked
    if st.button('Submit', key=f'submit_{q_id}'):
        action_type, *data = action_tracker.get(q_id, (None,))

        if action_type == 'vector' and answer_selected:
            # If an answer was selected, store question and answer in Pinecone

            question, answer,a_id = data
            final_store(question,answer,q_id)
           
            st.success(f"Stored question and selected answer in vector for Q{q_id}.")
        elif action_type == 'database':
            # If a comment was entered, update the database
            comment = data[0]
            update_qa(a_id, comment)
            st.success('Comment updated successfully in database!')
        else:
            st.error("No action performed. Please select an answer or enter a comment.")

# Pagination buttons
col1, col2 = st.columns(2)
with col1:
    # Disable the 'Previous' button on the first page
    prev_disabled = st.session_state.page == 0
    if st.button('Previous', disabled=prev_disabled):
        if st.session_state.page > 0:
            st.session_state.page -= 1

with col2:
    # Disable the 'Next' button on the last page
    next_disabled = st.session_state.page >= total_pages - 1
    if st.button('Next', disabled=next_disabled):
        if st.session_state.page < total_pages - 1:
            st.session_state.page += 1
