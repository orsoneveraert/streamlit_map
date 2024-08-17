import streamlit as st
from pymongo import MongoClient
from urllib.parse import quote_plus

@st.cache_resource
def init_connection():
    username = quote_plus(st.secrets['mongo']['username'])
    password = quote_plus(st.secrets['mongo']['password'])
    host = st.secrets['mongo']['host']
    
    # Correct MongoDB URI
    mongo_uri = f"mongodb+srv://{username}:{password}@{host}/?retryWrites=true&w=majority"
    return MongoClient(mongo_uri)

client = init_connection()
db = client['mazette']  # Correctly use the database name here

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

