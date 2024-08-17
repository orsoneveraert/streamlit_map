import streamlit as st
import pymongo
from urllib.parse import quote_plus

@st.cache_resource
def init_connection():
    username = quote_plus(st.secrets["mongo"]["username"])
    password = quote_plus(st.secrets["mongo"]["password"])
    cluster = "mazette.dgv4a.mongodb.net"  # This should be your actual cluster name
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority"
    return pymongo.MongoClient(connection_string)

client = init_connection()

@st.cache_data(ttl=600)
def get_data():
    db = client['mazette']  # Replace 'mazette' with your actual database name if different
    items = db.mycollection.find()
    items = list(items)  # make hashable for st.cache_data
    return items

items = get_data()

# Print results.
for item in items:
    st.write(f"{item['name']} has a :{item['pet']}:")

# Optionally, you can print the connection string (without password) to verify it's correct
cluster = "mazette.dgv4a.mongodb.net"
connection_string = f"mongodb+srv://{st.secrets['mongo']['username']}:****@{cluster}/?retryWrites=true&w=majority"
st.write(f"Connecting to: {connection_string}")
