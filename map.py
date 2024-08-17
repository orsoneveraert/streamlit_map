import streamlit as st
import pymongo

# Initialize connection.
# Uses st.cache_resource to only run once.
@st.cache_resource
def init_connection():
    connection_string = f"mongodb+srv://{st.secrets['mongo']['username']}:{st.secrets['mongo']['password']}@{st.secrets['mongo']['host']}/?authSource={st.secrets['mongo']['authSource']}&authMechanism={st.secrets['mongo']['authMechanism']}"
    return pymongo.MongoClient(connection_string)

client = init_connection()

# Pull data from the collection.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def get_data():
    db = client['mazette']  # Select the 'mazette' database
    items = db.mycollection.find()
    items = list(items)  # make hashable for st.cache_data
    return items

items = get_data()

# Print results.
for item in items:
    st.write(f"{item['name']} has a :{item['pet']}:")
