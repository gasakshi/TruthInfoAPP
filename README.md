For llm application:
1. database.py
      file used for
      1 insert_qa()- store qa in mysql database from enduser UI
      2 fetch_qa()- retreve data for Review Team UI
      3 update_qa()- update database after comment given by Review Team
      4 similarity_search()- fetch data for query matche to database question is present in database 

2. final_vectore.py
    file used for
    1 final_store()- To store final result in pinecone
    2 search_qurey()-  search the question which is present in pinecone (marked done)  

3. similer_search.py
    file used for
    1 connect pinecone and found index name
    2 Input Question
    3 used similarity_search(question) function from database to found similer question from databaseand fetch answer from database if found same question
    4 click on button 
    5 convert  query into vector
    6 send query to pinecone
    7 if match fetch document_id from with metadata and vetors
    8 post request to openai api with apikey, prompt and question with document_id
    9 generate response from openai api
    10 insert question and openai responses to database with ids
    11 display response to end user
<<<<<<< HEAD
    12 now compare openai response with database answers witch is fetch previously by similarity_search fucntion using compute_similarities(ans, text_data) 


=======
    12 now compare openai response with database answers witch is fetch previously by similarity_search fucntion using compute_similarities(ans, text_data)  
>>>>>>> 28341e0c965ea9f0261343f497536be85bfcc0f2
4. comparing_answer.py
    file used for 
    1 encode_answers_safe(models, answers) to encode answer then convert into list and pass it to compute_similarities()
    2 compute_similarities() used to compare database answer to openai response and calculate similarity_score

5. storeQA_pinecone.py
<<<<<<< HEAD


=======
>>>>>>> 28341e0c965ea9f0261343f497536be85bfcc0f2
6. storingPredefineData_vector.py
    file used for storing predefine websites into pinecone vector
