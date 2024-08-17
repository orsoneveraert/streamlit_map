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

# Collections to create:
# - products
# - checklists
# - general_todos

def init_session(session_key):
    if 'products' not in st.session_state:
        st.session_state.products = {item['name']: item for item in db.products.find()}
    if 'checklist' not in st.session_state:
        checklist_data = db.checklists.find_one({'session_key': session_key})
        if checklist_data:
            st.session_state.checklist = pd.DataFrame(checklist_data['items'])
        else:
            st.session_state.checklist = pd.DataFrame(columns=['Produit', 'Quantité'])
    if 'general_todos' not in st.session_state:
        st.session_state.general_todos = list(db.general_todos.find()) or []  # Use an empty list if no todos found

def save_current_session(session_key):
    # Save checklist
    db.checklists.update_one(
        {'session_key': session_key},
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

def set_theme(day):
    themes = {
        "LUNDI": "#f2dcdb", "MARDI": "#ebf1dd", "JEUDI": "#e5e0ec", "VENDREDI": "#dbeef3"
    }
    color = themes.get(day, "#FFFFFF")
    st.markdown(f"<style>.stApp {{background-color: {color};}}</style>", unsafe_allow_html=True)

def calculate_needed_items(product, quantity):
    items = st.session_state.products[product]["items"]
    return [{
        "name": item['name'],
        "count": math.ceil(quantity / item["capacity"]),
        "subtasks": item["subtasks"],
        "done": item.get("done", False)
    } for item in items]

def manage_general_todos():
    st.subheader("Gestion des Tâches Générales")
    
    new_todo = st.text_input("Nouvelle tâche générale")
    if st.button("Ajouter une tâche générale") and new_todo:
        st.session_state.general_todos.append({'task': new_todo, 'active': True})
        st.success(f"Tâche '{new_todo}' ajoutée")
        st.rerun()

    for i, todo in enumerate(st.session_state.general_todos):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.session_state.general_todos[i]['task'] = st.text_input(f"Tâche {i+1}", todo['task'], key=f"general_todo_{i}")
        with col2:
            st.session_state.general_todos[i]['active'] = st.checkbox("Actif", todo['active'], key=f"general_todo_active_{i}")
        with col3:
            if st.button("Supprimer", key=f"remove_general_todo_{i}"):
                st.session_state.general_todos.pop(i)
                st.rerun()

def generate_pdf_checklist():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Checklist - {st.session_state.session_key}", 0, 1, 'C')
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

def manage_products():
    st.subheader("Gestion des Produits")
    product_to_edit = st.selectbox("Sélectionnez un produit à modifier:", 
                                   list(st.session_state.products.keys()) + ["Ajouter un nouveau produit"])

    if product_to_edit == "Ajouter un nouveau produit":
        new_product = st.text_input("Entrez le nom du nouveau produit:")
        if st.button("Ajouter le produit") and new_product and new_product not in st.session_state.products:
            st.session_state.products[new_product] = {"name": new_product, "items": []}
            st.success(f"Ajouté {new_product}")
            st.rerun()

    elif product_to_edit in st.session_state.products:
        # Product editing code remains the same
        pass

def duplicate_product():
    # Product duplication code remains the same
    pass

def main():
    
    if 'session_key' not in st.session_state:
        st.session_state.session_key = "LUNDI"
    
    with st.sidebar:
        session_key = st.selectbox("Sélectionnez le jour:", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"], key="day_selector")
    
    if session_key != st.session_state.session_key:
        st.session_state.clear()
        st.session_state.session_key = session_key
    
    set_theme(st.session_state.session_key)
    init_session(st.session_state.session_key)
    
    st.title(f"{st.session_state.session_key}")

    with st.sidebar:
        st.header("Gestion")
        menu_choice = st.radio("", ["Commandes", "Gestion des Tâches Générales", "Gestion des Produits", "Dupliquer le Produit"])

        if menu_choice == "Commandes":
            st.subheader("Ajouter aux commandes")
            new_product = st.selectbox("Sélectionnez un produit:", list(st.session_state.products.keys()))
            new_quantity = st.number_input("Entrez la quantité:", min_value=1, value=1, step=1)
            if st.button("Ajouter aux commandes"):
                new_row = pd.DataFrame({'Produit': [new_product], 'Quantité': [new_quantity]})
                st.session_state.checklist = pd.concat([st.session_state.checklist, new_row], ignore_index=True)
                save_current_session(st.session_state.session_key)
                st.rerun()

            st.subheader("Commandes")
            edited_df = st.data_editor(st.session_state.checklist, num_rows="dynamic", use_container_width=True)
            st.session_state.checklist = edited_df
            save_current_session(st.session_state.session_key)

        elif menu_choice == "Gestion des Tâches Générales":
            manage_general_todos()

        elif menu_choice == "Gestion des Produits":
            manage_products()

        elif menu_choice == "Dupliquer le Produit":
            duplicate_product()

    render_checklist()
    save_current_session(st.session_state.session_key)

if __name__ == "__main__":
    main()

