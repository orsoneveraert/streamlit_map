import streamlit as st
import pandas as pd
import math
from fpdf import FPDF
from pymongo import MongoClient
from urllib.parse import quote_plus

st.set_page_config(layout="wide", page_title="Suivi de Mise en Place")

# MongoDB connection
@st.cache_resource
def init_connection():
    username = quote_plus(st.secrets["mongo"]["username"])
    password = quote_plus(st.secrets["mongo"]["password"])
    cluster = "mazette.dgv4a.mongodb.net"
    connection_string = f"mongodb+srv://{username}:{password}@{cluster}/?retryWrites=true&w=majority"
    return MongoClient(connection_string)

client = init_connection()
db = client.mazette

# Initialize session data
def init_session():
    if 'products' not in st.session_state:
        st.session_state.products = {item['name']: item for item in db.products.find()}
    if 'checklist' not in st.session_state:
        checklist_data = db.checklists.find_one({'session_key': 'shared'})
        if checklist_data:
            st.session_state.checklist = pd.DataFrame(checklist_data['items'])
        else:
            st.session_state.checklist = pd.DataFrame(columns=['Produit', 'Quantité'])
    if 'general_todos' not in st.session_state:
        st.session_state.general_todos = list(db.general_todos.find()) or []  # Use an empty list if no todos found

# Save session data to MongoDB
def save_current_session():
    # Save checklist
    db.checklists.update_one(
        {'session_key': 'shared'},
        {'$set': {'items': st.session_state.checklist.to_dict(orient='records')}},
        upsert=True
    )
    
    # Save products
    for product_name, product_data in st.session_state.products.items():
        db.products.update_one({'name': product_name}, {'$set': product_data}, upsert=True)
    
    # Save general todos
    db.general_todos.delete_many({})
    if st.session_state.general_todos:  # Only insert if the list is not empty
        db.general_todos.insert_many(st.session_state.general_todos)

# Set theme based on the day
def set_theme(day):
    themes = {
        "LUNDI": "#f2dcdb", "MARDI": "#ebf1dd", "JEUDI": "#e5e0ec", "VENDREDI": "#dbeef3"
    }
    color = themes.get(day, "#FFFFFF")
    st.markdown(f"<style>.stApp {{background-color: {color};}}</style>", unsafe_allow_html=True)

# Calculate needed items for a product
def calculate_needed_items(product, quantity):
    items = st.session_state.products[product]["items"]
    return [{
        "name": item['name'],
        "count": math.ceil(quantity / item["capacity"]),
        "subtasks": item["subtasks"],
        "done": item.get("done", False)
    } for item in items]

# Manage general todos
def manage_general_todos():
    st.subheader("Gestion des Tâches Générales")
    
    new_todo = st.text_input("Nouvelle tâche générale")
    if st.button("Ajouter une tâche générale") and new_todo:
        st.session_state.general_todos.append({'task': new_todo, 'active': True})
        st.success(f"Tâche '{new_todo}' ajoutée")
        st.experimental_rerun()

    for i, todo in enumerate(st.session_state.general_todos):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.session_state.general_todos[i]['task'] = st.text_input(f"Tâche {i+1}", todo['task'], key=f"general_todo_{i}")
        with col2:
            st.session_state.general_todos[i]['active'] = st.checkbox("Actif", todo['active'], key=f"general_todo_active_{i}")
        with col3:
            if st.button("Supprimer", key=f"remove_general_todo_{i}"):
                st.session_state.general_todos.pop(i)
                st.experimental_rerun()

# Generate a PDF checklist
def generate_pdf_checklist():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Checklist - Partagée", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Tâches Générales", 0, 1)
    pdf.ln(5)
    
    pdf.set_font("Arial", size=12)
    for todo in st.session_state.general_todos:
        if todo['active']:
            pdf.cell(0, 10, f"[ ] {todo['task']}", 0, 1)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Tâches Spécifiques aux Produits", 0, 1)
    pdf.ln(5)
    
    for _, row in st.session_state.checklist.iterrows():
        product, quantity = row['Produit'], row['Quantité']
        if product in st.session_state.products:
            items_needed = calculate_needed_items(product, quantity)
            rounded_quantity = math.ceil(quantity)
            
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, f"{product} ({rounded_quantity})", 0, 1)
            
            pdf.set_font("Arial", size=12)
            for item in items_needed:
                pdf.cell(0, 10, f"[ ] {item['count']} {item['name']}", 0, 1)
                for subtask in item['subtasks']:
                    pdf.cell(10)
                    pdf.cell(0, 10, f"[ ] {subtask['name']}", 0, 1)
            pdf.ln(5)
    
    pdf.output("checklist.pdf")

# Render the checklist
def render_checklist():
    st.header("📋 Checklist - Mise en place")

    # Calculate total tasks and completed tasks
    total_tasks = 0
    completed_tasks = 0

    # Count general todos
    for todo in st.session_state.general_todos:
        if todo['active']:
            total_tasks += 1
            if todo.get('done', False):
                completed_tasks += 1

    # Count product-specific tasks
    for _, row in st.session_state.checklist.iterrows():
        product, quantity = row['Produit'], row['Quantité']
        if product in st.session_state.products:
            items_needed = calculate_needed_items(product, quantity)
            for item in items_needed:
                total_tasks += 1
                if item.get('done', False):
                    completed_tasks += 1
                for subtask in item['subtasks']:
                    total_tasks += 1
                    if subtask.get('done', False):
                        completed_tasks += 1

    # Display progress
    st.subheader("Progression")
    progress_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    st.progress(progress_percentage / 100)
    st.write(f"{completed_tasks} tâches terminées sur {total_tasks} ({progress_percentage:.1f}%)")

    st.subheader("Tâches Générales")
    for todo in st.session_state.general_todos:
        if todo['active']:
            todo_key = f"general_todo_{todo['task']}"
            todo['done'] = st.checkbox(todo['task'], value=todo.get('done', False), key=todo_key)
    
    st.subheader("Tâches Spécifiques aux Produits")
    for _, row in st.session_state.checklist.iterrows():
        product, quantity = row['Produit'], row['Quantité']
        if product in st.session_state.products:
            items_needed = calculate_needed_items(product, quantity)
            rounded_quantity = math.ceil(quantity)
            st.markdown(f"#### {product} ({rounded_quantity})")
            for item in items_needed:
                item_key = f"task_{product}_{item['name']}"
                item['done'] = st.checkbox(f"{item['count']} {item['name']}", value=item['done'], key=item_key)
                
                for i, subtask in enumerate(item['subtasks']):
                    subtask_key = f"{item_key}_subtask_{i}"
                    subtask['done'] = st.checkbox(f"  - {subtask['name']}", value=subtask.get('done', False), key=subtask_key)
                
                for prod_item in st.session_state.products[product]['items']:
                    if prod_item['name'] == item['name']:
                        prod_item['done'] = item['done']
                        prod_item['subtasks'] = item['subtasks']
            
            st.markdown("---")

    if st.button("Générer PDF"):
        generate_pdf_checklist()
        st.success("Checklist PDF générée !")
    
    with open("checklist.pdf", "rb") as f:
        st.download_button("Télécharger la checklist PDF", f, "checklist.pdf")

# Manage products
def manage_products():
    st.subheader("Gestion des Produits")
    product_to_edit = st.selectbox("Sélectionnez un produit à modifier", [""] + list(st.session_state.products.keys()))

    if product_to_edit:
        product_data = st.session_state.products[product_to_edit]
        new_product_name = st.text_input("Nom du produit", value=product_data['name'])
        new_items = product_data['items']

        # Edit items in the product
        for i, item in enumerate(new_items):
            st.text(f"Élément {i + 1}")
            item['name'] = st.text_input(f"Nom de l'élément {i + 1}", value=item['name'], key=f"edit_item_name_{i}")
            item['capacity'] = st.number_input(f"Capacité de l'élément {i + 1}", value=item['capacity'], key=f"edit_item_capacity_{i}")
            item['subtasks'] = st.text_area(f"Sous-tâches pour l'élément {i + 1} (séparées par des virgules)", value=", ".join([sub['name'] for sub in item['subtasks']]), key=f"edit_item_subtasks_{i}").split(", ")

            new_items[i] = item

        if st.button("Enregistrer les modifications du produit"):
            st.session_state.products[new_product_name] = {'name': new_product_name, 'items': new_items}
            if new_product_name != product_to_edit:
                del st.session_state.products[product_to_edit]
            st.success(f"Modifications du produit '{new_product_name}' enregistrées")
            st.experimental_rerun()

    st.markdown("---")
    st.subheader("Ajouter un nouveau produit")
    
    new_product_name = st.text_input("Nom du nouveau produit")
    if new_product_name and new_product_name not in st.session_state.products:
        st.session_state.products[new_product_name] = {'name': new_product_name, 'items': []}
        st.success(f"Produit '{new_product_name}' ajouté à la base de données")
    elif new_product_name:
        st.warning("Ce produit existe déjà.")

    st.markdown("---")

    st.subheader("Supprimer un produit")
    product_to_delete = st.selectbox("Sélectionnez un produit à supprimer", [""] + list(st.session_state.products.keys()))
    if product_to_delete and st.button(f"Supprimer {product_to_delete}"):
        del st.session_state.products[product_to_delete]
        db.products.delete_one({'name': product_to_delete})
        st.success(f"Produit '{product_to_delete}' supprimé")
        st.experimental_rerun()

# Main application
init_session()

day = st.sidebar.selectbox("Jour", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"])
set_theme(day)

tabs = st.sidebar.radio("Navigation", ["Checklist", "Gestion des Produits", "Tâches Générales"])

if tabs == "Checklist":
    render_checklist()
elif tabs == "Gestion des Produits":
    manage_products()
elif tabs == "Tâches Générales":
    manage_general_todos()

if st.sidebar.button("Sauvegarder la session"):
    save_current_session()
    st.sidebar.success("Session sauvegardée avec succès!")



