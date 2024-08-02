import streamlit as st
from database import fetch_qa,update_qa
from collections import defaultdict
from final_vectore import *
# Assuming final_vectore.py contains the final_store function

# Fetch question and answers from the database
qa_data = fetch_qa()
questions = defaultdict(list)
for item in qa_data:
    questions[item['q_id']].append((item['question'], item['answer'], item['a_id']))  # Assuming 'a_id' is available

# Initialize session state for pagination
if 'page' not in st.session_state:
    st.session_state.page = 0

questions_per_page = 1
total_pages = len(questions) // questions_per_page + (1 if len(questions) % questions_per_page > 0 else 0)
start_index = st.session_state.page * questions_per_page
end_index = start_index + questions_per_page
current_page_questions = list(questions.items())[start_index:end_index]

action_tracker = {}  # Resetting action_tracker for each page load

for q_id, qa_pairs in current_page_questions:
    question = qa_pairs[0][0]  # Assuming the first question is representative
    st.subheader(f"Q{q_id}: {question}")
    answer_selected = False

    for index, (question_text, answer, a_id) in enumerate(qa_pairs):

        checkbox_key = f"checkbox_{q_id}_{index}"
        comment_key = f"comment_{q_id}_{index}"
        if st.checkbox(answer, key=checkbox_key):
            answer_selected = True
            # Track selected answers
            if q_id not in action_tracker:
                action_tracker[q_id] = {'selected': [], 'comments': {}}
            action_tracker[q_id]['selected'].append((qa_pairs[0][0],answer, a_id))
        
        # Track comments for each answer, regardless of checkbox state
        comment = st.text_area("Provide an example or further information:", key=comment_key)
        if comment:
            if q_id not in action_tracker:
                action_tracker[q_id] = {'selected': [], 'comments': {}}
            action_tracker[q_id]['comments'][a_id] = comment
            # print(comment)

    # When 'Submit' is clicked for each question
    if st.button('Submit', key=f'submit_{q_id}'):
        if q_id in action_tracker:
            actions = action_tracker[q_id]

            # Process selected answers
            if actions['selected']:
                for question_text, answer, a_id in actions['selected']:
                    final_store(question_text, answer, q_id)
                    st.success(f"Stored question and selected answer in vector for Q{q_id}.")
            
            # Process comments
            if actions['comments']:
                for a_id, comment in actions['comments'].items():
                    update_qa(a_id, comment)
                    st.success(f"Comment updated successfully in database for answer ID {a_id}.")

            # If no action was recorded for both selections and comments
            if not actions['selected'] and not actions['comments']:
                st.error("No action performed. Please select an answer or enter a comment.")
        else:
            st.error("No action performed. Please select an answer or enter a comment.")
# Pagination buttons
col1, col2 = st.columns(2)
with col1:
    if st.button('Previous') and st.session_state.page > 0:
        st.session_state.page -= 1
        # st.experimental_rerun()

with col2:
    if st.button('Next') and st.session_state.page < total_pages - 1:
        st.session_state.page += 1
        # st.experimental_rerun()
