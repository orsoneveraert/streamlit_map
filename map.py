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

# Initialize session state
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

# Save session state to database
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

# Set theme based on the selected day
def set_theme(day):
    themes = {
        "LUNDI": "#f2dcdb", "MARDI": "#ebf1dd", "JEUDI": "#e5e0ec", "VENDREDI": "#dbeef3"
    }
    color = themes.get(day, "#FFFFFF")
    st.markdown(f"<style>.stApp {{background-color: {color};}}</style>", unsafe_allow_html=True)

# Calculate needed items based on the product and quantity
def calculate_needed_items(product, quantity):
    items = st.session_state.products[product]["items"]
    return [{
        "name": item['name'],
        "count": math.ceil(quantity / item["capacity"]),
        "subtasks": item["subtasks"],
        "done": item.get("done", False)
    } for item in items]

# Manage general to-dos
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

# Generate a PDF checklist
def generate_pdf_checklist():
    if st.session_state.checklist.empty:
        st.warning("La checklist est vide. Ajoutez des produits avant de générer un PDF.")
        return

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, txt="Checklist de Commandes", ln=True, align="C")

    pdf.set_font("Arial", "B", 12)
    pdf.ln(10)  # Add a line break

    for _, row in st.session_state.checklist.iterrows():
        product = row['Produit']
        quantity = row['Quantité']
        pdf.cell(200, 10, txt=f"{product} - {quantity} unité(s)", ln=True, align="L")
        
        # Add needed items for the product
        needed_items = calculate_needed_items(product, quantity)
        for item in needed_items:
            pdf.cell(10)  # indentation
            pdf.cell(200, 8, txt=f" - {item['name']}: {item['count']} unité(s)", ln=True, align="L")
    
    pdf_output = f"checklist_{st.session_state.session_key}.pdf"
    pdf.output(pdf_output)

    with open(pdf_output, "rb") as pdf_file:
        st.download_button(
            label="Télécharger la checklist en PDF",
            data=pdf_file,
            file_name=pdf_output,
            mime="application/pdf",
        )

# Render the checklist with progress
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
    product_to_edit = st.selectbox("Sélectionnez un produit à modifier:", 
                                   list(st.session_state.products.keys()) + ["Ajouter un nouveau produit"])

    if product_to_edit == "Ajouter un nouveau produit":
        new_product = st.text_input("Entrez le nom du nouveau produit:")
        if st.button("Ajouter le produit") and new_product and new_product not in st.session_state.products:
            st.session_state.products[new_product] = {"name": new_product, "items": []}
            st.success(f"Ajouté {new_product}")
            st.rerun()

    if product_to_edit and product_to_edit != "Ajouter un nouveau produit":
        product = st.session_state.products[product_to_edit]

        new_name = st.text_input("Nom du produit", product["name"])
        if new_name != product["name"]:
            st.session_state.products.pop(product["name"])
            product["name"] = new_name
            st.session_state.products[new_name] = product

        st.write("### Éléments du produit")
        for i, item in enumerate(product["items"]):
            st.write(f"#### Élément {i + 1}")
            item["name"] = st.text_input("Nom de l'élément", item["name"], key=f"{product_to_edit}_item_{i}")
            item["capacity"] = st.number_input("Capacité", value=item["capacity"], min_value=1, key=f"{product_to_edit}_capacity_{i}")

            subtask_count = len(item["subtasks"])
            for j in range(subtask_count):
                item["subtasks"][j]["name"] = st.text_input(
                    f"Nom de la sous-tâche {j + 1}", 
                    item["subtasks"][j]["name"], 
                    key=f"{product_to_edit}_subtask_{i}_{j}"
                )

            if st.button("Supprimer cet élément", key=f"remove_item_{product_to_edit}_{i}"):
                product["items"].pop(i)
                st.rerun()

        if st.button("Ajouter un élément"):
            product["items"].append({"name": "", "capacity": 1, "subtasks": []})

        if st.button("Sauvegarder les modifications"):
            st.session_state.products[product["name"]] = product
            st.success("Modifications sauvegardées")
            save_current_session(st.session_state.session_key)

def main():
    session_key = st.text_input("Entrez la clé de session (une valeur unique pour chaque utilisateur):")

    if session_key:
        st.session_state.session_key = session_key
        init_session(session_key)
        day = st.selectbox("Choisissez le jour:", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"])
        set_theme(day)

        tab1, tab2, tab3 = st.tabs(["Checklist", "Gérer Produits", "Tâches Générales"])

        with tab1:
            render_checklist()
        with tab2:
            manage_products()
        with tab3:
            manage_general_todos()

        if st.button("Sauvegarder la session"):
            save_current_session(session_key)
            st.success("Session sauvegardée")

if __name__ == "__main__":
    main()


