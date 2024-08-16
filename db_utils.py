import os
from pymongo import MongoClient
import streamlit as st

# Use st.secrets to securely store your MongoDB connection string
MONGO_URI = st.secrets["mongodb+srv://mazette:XBebw6oZYo6ljjcV@mazette.dgv4a.mongodb.net/?retryWrites=true&w=majority&appName=mazette"]

client = MongoClient(MONGO_URI)
db = client['checklist_app']  # Replace with your database name

def get_collection(collection_name):
    return db[collection_name]

def load_data(collection_name, filter=None):
    collection = get_collection(collection_name)
    if filter is None:
        filter = {}
    return list(collection.find(filter))

def save_data(collection_name, data, filter=None):
    collection = get_collection(collection_name)
    if filter is None:
        # Insert new document
        collection.insert_one(data)
    else:
        # Update existing document
        collection.update_one(filter, {"$set": data}, upsert=True)

def delete_data(collection_name, filter):
    collection = get_collection(collection_name)
    collection.delete_one(filter)
