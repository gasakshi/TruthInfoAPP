from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, PodSpec

Pincone_API_KEY ="0b8a413f-e72c-4a9f-89e8-b4933ff7f7c8"
# Initialize Pinecone
#
pc = Pinecone(api_key=Pincone_API_KEY)
index_name = "finalvector"
vector_dimension = 384

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

def final_store(question,answer,q_id):
    question_embedding=model.encode(question,convert_to_tensor=False).tolist()
    answer_embedding =model.encode(answer,convert_to_tensor=False).tolist()
        
    index.upsert(vectors=[(f"{q_id}-question", question_embedding),
                        (f"{q_id}-{answer}", answer_embedding)])
    print("Data Successfully stored in final vector")



def search_qurey_finalvector(query_vector_list):
    results = index.query(vector=query_vector_list, top_k=1)
    if not results["matches"]:
        return 