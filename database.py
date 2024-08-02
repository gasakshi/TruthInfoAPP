import mysql.connector
from mysql.connector import Error


# def insert_qa(question, answers,document_ids):
#     try:
#         connection = mysql.connector.connect(
#             host='localhost',  # Often 'localhost'
#             database='qa_dataset',
#             user='root',
#             password='password'
#         )
#         if connection.is_connected():
#             db_cursor = connection.cursor()
#             question_query = "INSERT INTO question (question) VALUES (%s)"
#             db_cursor.execute(question_query, (question,))
#             question_id = db_cursor.lastrowid  # Retrieve the ID of the inserted question
#             # print(question_id)
#             # Insert answers into the answers table, referencing the question ID
#             # answer_query = "INSERT INTO answers (q_id, answer) VALUES (%s, %s)"
#             # for answer in answers:
#             #     db_cursor.execute(answer_query, (question_id, answer))

#             answer_query = "INSERT INTO answers (q_id, answer, document_id) VALUES (%s, %s, %s)"
#             for answer, document_id in zip(answers, document_ids):
#                 db_cursor.execute(answer_query, (question_id, answer, document_id))
            
#             # query = "INSERT INTO answers (document_id) VALUES (%s)"
#             # for document in document_ids:
#             #     db_cursor.execute(query, (document,))
#             connection.commit()
#             print("Question and answers inserted successfully.")
#     except Error as e:
#         print("Error while connecting to MySQL", e)
#     finally:
#         if connection.is_connected():
#             db_cursor.close()
#             connection.close()
#             print("MySQL connection is closed")

def insert_question_once(question):
    connection = mysql.connector.connect(
            host='localhost',  # Often 'localhost'
            database='qa_dataset',
            user='root',
            password='password'
        )
        
    try:
        db_cursor = connection.cursor(buffered=True)

        check_query = "SELECT q_id FROM question WHERE question = %s"
        db_cursor.execute(check_query, (question,))
        result = db_cursor.fetchone()
        
        if result:
            # The question already exists, return its existing ID
            question_id = result[0]
        else:
            insert_query = "INSERT INTO question (question) VALUES (%s)"
            db_cursor.execute(insert_query, (question,))
            question_id = db_cursor.lastrowid
            connection.commit()
            print("Question inserted successfully.")
        return question_id
            
    except Error as e:
        print("Error while connecting to MySQL", e)
    finally:
        if connection.is_connected():
            db_cursor.close()
            connection.close()
            print("MySQL connection is closed")


def insert_answer(question_id, answer,document_id):
    """Inserts an answer into the database linked to the specified question ID."""
    connection = mysql.connector.connect(
            host='localhost',  # Often 'localhost'
            database='qa_dataset',
            user='root',
            password='password'
        )
    try:
        db_cursor = connection.cursor()
        insert_query = "INSERT INTO answers (q_id, answer, document_id) VALUES (%s, %s, %s)"
        db_cursor.execute(insert_query, (question_id, answer,document_id))
        connection.commit()
        print("Answer inserted successfully.")
    finally:
        db_cursor.close()
        connection.close()


def fetch_qa():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='qa_dataset',
            user='root',
            password='password'
        )
        if connection.is_connected():
            db_cursor = connection.cursor(dictionary=True)
            query = """
                        SELECT q.question, a.answer, a.q_id,a.a_id
                        FROM question q
                        JOIN answers a ON q.q_id = a.q_id
                        """

            db_cursor.execute(query)
            results = db_cursor.fetchall() 
            return results
    except Error as e:
        print("Error while connecting to MySQL", e)
        return []
    finally:
        if connection.is_connected():
            db_cursor.close()
            connection.close()
            print("MySQL connection is closed")


def update_qa(a_id, comment):
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='qa_dataset',
            user='root',
            password='password'
        )
        if connection.is_connected():
            db_cursor = connection.cursor()
            query = 'UPDATE answers SET cumments = %s WHERE a_id = %s'
            db_cursor.execute(query, (comment, a_id))
            connection.commit()
            print(" Comment updated successfully!")
        return []
    finally:
        if connection.is_connected():
            db_cursor.close()
            connection.close()
            print("MySQL connection is closed")


def similarity_search(user_query):
    results = []
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='qa_dataset',
            user='root',
            password='password'
        )
        if connection.is_connected():
            db_cursor = connection.cursor()
            query = """
                        SELECT q.question, a.answer, q.q_id
                        FROM question q
                        JOIN answers a ON q.q_id = a.q_id
                        WHERE MATCH(q.question) AGAINST(%s IN NATURAL LANGUAGE MODE)
                    """
            db_cursor.execute(query, (user_query,))
            results = db_cursor.fetchall() 
            connection.commit()  # This is typically not needed for SELECT queries
            print("Similarity search executed successfully!")
    except mysql.connector.Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            db_cursor.close()
            connection.close()
            print("MySQL connection is closed")
    
    return results

