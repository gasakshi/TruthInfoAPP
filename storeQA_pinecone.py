from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, PodSpec
import numpy as np

Pincone_API_KEY ="530ba1af-e67f-47c0-8bbc-81bb5fbc185d"
# Initialize Pinecone
#
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "qadataset"
vector_dimension = 2304

# Check if the index exists and create it if not
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
# def text_to_vector(text):
#     return model.encode(text, convert_to_tensor=False).tolist()
def qadataset_store(question,answer,q_id):
    question_embedding=model.encode(question,convert_to_tensor=False).tolist()
    answer_embedding =model.encode(answer,convert_to_tensor=False).tolist()

    combined_embedding = concatenate_embeddings(question_embedding, answer_embedding)
    
    index.upsert(vectors=[(f"{q_id}-qa", combined_embedding)])
    print("Data inserted into QADataset")

def search_query_qaDataset(query_vector_list):
    results = index.query(vector=query_vector_list)
    if not results["matches"]:
        return 

def concatenate_embeddings(question_embedding, answer_embedding):
    question_embedding = np.array(question_embedding)
    answer_embedding = np.array(answer_embedding)

    # Flatten both arrays to 1D if they are not already
    question_embedding = question_embedding.flatten()
    answer_embedding = answer_embedding.flatten()
    # Concatenate the question and answer embeddings
    combined_embedding = np.concatenate([question_embedding, answer_embedding])
    return combined_embedding.tolist()