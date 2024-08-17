import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def init_connection():
    # Check if we have a full URI in the secrets
    if "mongo" in st.secrets and "uri" in st.secrets["mongo"]:
        return MongoClient(st.secrets["mongo"]["uri"])
    
    # If not, try to construct it from individual components
    elif "mongodb+srv" in st.secrets:
        return MongoClient(st.secrets["mongodb+srv"])
    
    # If neither option works, raise an error
    else:
        raise KeyError("MongoDB connection details not found in secrets.")

client = init_connection()
db = client.mazette  # Replace 'mazette' with your actual database name if different

@st.cache_data(ttl=600)
def load_data(collection_name, filter=None):
    collection = db[collection_name]
    if filter is None:
        filter = {}
    items = collection.find(filter)
    return list(items)

def save_data(collection_name, data, filter=None):
    collection = db[collection_name]
    if filter is None:
        # Insert new document
        collection.insert_one(data)
    else:
        # Update existing document
        collection.update_one(filter, {"$set": data}, upsert=True)

def delete_data(collection_name, filter):
    collection = db[collection_name]
    collection.delete_one(filter)
