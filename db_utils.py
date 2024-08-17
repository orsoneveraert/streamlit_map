import streamlit as st
from pymongo import MongoClient

@st.cache_resource
def init_connection():
    mongo_uri = f"mongodb+srv://{st.secrets['mongo']['username']}:{st.secrets['mongo']['password']}@{st.secrets['mongo']['host']}/?retryWrites=true&w=majority"
    return MongoClient(mongo_uri)

client = init_connection()
db = client.mazette  # This selects the 'mazette' database after connection

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
