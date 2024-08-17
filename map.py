import streamlit as st
import pandas as pd
import math
from fpdf import FPDF
from pymongo import MongoClient
from urllib.parse import quote_plus
from streamlit_extras.tags import tagger_component
from bson import ObjectId

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

def init_session():
    if 'products' not in st.session_state:
st.session_state.products = {item['name']: {**item, '_id': str(item['_id']), 'tasks': item.get('tasks', [])} for item in db.products.find()}
    
    days = ["LUNDI", "MARDI", "JEUDI", "VENDREDI"]
    for day in days:
        if f'{day}_checklist' not in st.session_state:
            checklist_data = db.checklists.find_one({'session_key': day})
            st.session_state[f'{day}_checklist'] = pd.DataFrame(checklist_data['items'] if checklist_data else [], columns=['Produit', 'Quantité'])
        
        if f'{day}_general_todos' not in st.session_state:
            todos_data = list(db.general_todos.find({'session_key': day}))
            st.session_state[f'{day}_general_todos'] = todos_data if todos_data else []

def save_current_session():
    # Save checklist
    db.checklists.update_one(
        {'session_key': st.session_state.session_key},
        {'$set': {'items': st.session_state[f'{st.session_state.session_key}_checklist'].to_dict(orient='records')}},
        upsert=True
    )
    
    # Save products
    for product_name, product_data in st.session_state.products.items():
        product_data_without_id = {k: v for k, v in product_data.items() if k != '_id'}
        
        existing_product = db.products.find_one({'name': product_name})
        if existing_product:
            db.products.update_one(
                {'_id': existing_product['_id']},
                {'$set': product_data_without_id}
            )
        else:
            db.products.insert_one(product_data_without_id)
    
    # Save general todos
    db.general_todos.delete_many({'session_key': st.session_state.session_key})
    if st.session_state[f'{st.session_state.session_key}_general_todos']:
        db.general_todos.insert_many([{**todo, 'session_key': st.session_state.session_key} for todo in st.session_state[f'{st.session_state.session_key}_general_todos']])

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
        "done": item.get("done", False),
        "tags": item.get("tags", [])
    } for item in items]

def manage_general_todos():
    st.subheader("Gestion des Tâches Générales")
    
    # Ensure the key exists
    if f'{st.session_state.session_key}_general_todos' not in st.session_state:
        st.session_state[f'{st.session_state.session_key}_general_todos'] = []

    new_todo = st.text_input("Nouvelle tâche générale")
    if st.button("Ajouter une tâche générale") and new_todo:
        st.session_state[f'{st.session_state.session_key}_general_todos'].append({'task': new_todo, 'active': True})
        save_current_session()
        st.success(f"Tâche '{new_todo}' ajoutée")
        st.rerun()

    for i, todo in enumerate(st.session_state[f'{st.session_state.session_key}_general_todos']):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.session_state[f'{st.session_state.session_key}_general_todos'][i]['task'] = st.text_input(f"Tâche {i+1}", todo['task'], key=f"general_todo_{i}")
        with col2:
            st.session_state[f'{st.session_state.session_key}_general_todos'][i]['active'] = st.checkbox("Actif", todo['active'], key=f"general_todo_active_{i}")
        with col3:
            if st.button("Supprimer", key=f"remove_general_todo_{i}"):
                st.session_state[f'{st.session_state.session_key}_general_todos'].pop(i)
                save_current_session()
                st.rerun()
    
    save_current_session()

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
    for todo in st.session_state[f'{st.session_state.session_key}_general_todos']:
        if todo['active']:
            pdf.cell(0, 10, f"[ ] {todo['task']}", 0, 1)
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, "Tâches Spécifiques aux Produits", 0, 1)
    pdf.ln(5)
    
    for _, row in st.session_state[f'{st.session_state.session_key}_checklist'].iterrows():
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
    
    total_tasks = 0
    completed_tasks = 0

    # General todos
    st.subheader("Tâches Générales")
    for todo in st.session_state[f'{st.session_state.session_key}_general_todos']:
        if todo['active']:
            todo_key = f"general_todo_{todo['task']}"
            todo['done'] = st.checkbox(todo['task'], value=todo.get('done', False), key=todo_key)
            total_tasks += 1
            if todo['done']:
                completed_tasks += 1

    # Product-specific tasks
    for _, row in st.session_state[f'{st.session_state.session_key}_checklist'].iterrows():
        product, quantity = row['Produit'], row['Quantité']
        if product in st.session_state.products:
            st.subheader(f"{product} ({quantity})")
            
            # Items and their subtasks
            items_needed = calculate_needed_items(product, quantity)
            for item in items_needed:
                item_key = f"item_{product}_{item['name']}"
                item['done'] = st.checkbox(f"{item['count']} {item['name']}", value=item.get('done', False), key=item_key)
                total_tasks += 1
                if item['done']:
                    completed_tasks += 1
                
                for i, subtask in enumerate(item['subtasks']):
                    subtask_key = f"{item_key}_subtask_{i}"
                    subtask['done'] = st.checkbox(f"  - {subtask['name']}", value=subtask.get('done', False), key=subtask_key)
                    total_tasks += 1
                    if subtask['done']:
                        completed_tasks += 1
            
            # Product-specific tasks
            st.subheader(f"Tâches spécifiques pour {product}")
            for task in st.session_state.products[product].get('tasks', []):
                task_key = f"task_{product}_{task['name']}"
                task['done'] = st.checkbox(f"{task['name']}", value=task.get('done', False), key=task_key)
                total_tasks += 1
                if task['done']:
                    completed_tasks += 1
                
                for i, subtask in enumerate(task['subtasks']):
                    subtask_key = f"{task_key}_subtask_{i}"
                    subtask['done'] = st.checkbox(f"  - {subtask['name']}", value=subtask.get('done', False), key=subtask_key)
                    total_tasks += 1
                    if subtask['done']:
                        completed_tasks += 1
            
            st.markdown("---")

    # Progress bar
    st.subheader("Progression")
    progress_percentage = (completed_tasks / total_tasks) * 100 if total_tasks > 0 else 0
    st.progress(progress_percentage / 100)
    st.write(f"{completed_tasks} tâches terminées sur {total_tasks} ({progress_percentage:.1f}%)")

    # PDF generation
    if st.button("Générer PDF"):
        generate_pdf_checklist()
        st.success("Checklist PDF générée !")
    
    with open("checklist.pdf", "rb") as f:
        st.download_button("Télécharger la checklist PDF", f, "checklist.pdf")

    # Save the current state
    save_current_session()


def manage_products():
    product_to_edit = st.selectbox(
        "Sélectionnez un produit à modifier:",
        list(st.session_state.products.keys()) + ["Ajouter un nouveau produit"]
    )

    if product_to_edit == "Ajouter un nouveau produit":
        new_product = st.text_input("Entrez le nom du nouveau produit:")
        if st.button("Ajouter le produit") and new_product and new_product not in st.session_state.products:
            st.session_state.products[new_product] = {"items": [], "tasks": []}
            save_current_session()
            st.success(f"Produit '{new_product}' ajouté")
            st.rerun()

    elif product_to_edit in st.session_state.products:
        st.subheader(f"Modification de '{product_to_edit}'")

        for i, item in enumerate(st.session_state.products[product_to_edit]["items"]):
            col1, col2, col3 = st.columns([2, 1, 1])
            with col1:
                new_name = st.text_input(f"Nom de l'élément {i+1}", item["name"], key=f"name_{i}")
            with col2:
                new_capacity = st.number_input(f"Capacité de l'élément {i+1}", min_value=1, value=item["capacity"], key=f"capacity_{i}")
            with col3:
                if st.button("Supprimer l'élément", key=f"remove_item_{i}"):
                    st.session_state.products[product_to_edit]["items"].pop(i)
                    save_current_session()
                    st.rerun()

            st.write("Sous-tâches:")
            for j, subtask in enumerate(item["subtasks"]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    subtask_name = st.text_input(f"Nom de la sous-tâche {j+1}", subtask["name"], key=f"subtask_name_{i}_{j}")
                with col2:
                    if st.button("Supprimer la sous-tâche", key=f"remove_subtask_{i}_{j}"):
                        item["subtasks"].pop(j)
                        save_current_session()
                        st.rerun()

            new_subtask = st.text_input(f"Nouvelle sous-tâche pour l'élément {item['name']}", key=f"new_subtask_{i}")
            if st.button(f"Ajouter une sous-tâche à {item['name']}", key=f"add_subtask_{i}") and new_subtask:
                item["subtasks"].append({"name": new_subtask, "done": False})
                save_current_session()
                st.success(f"Sous-tâche '{new_subtask}' ajoutée à '{item['name']}'")
                st.rerun()

            st.session_state.products[product_to_edit]["items"][i] = {
                "name": new_name,
                "capacity": new_capacity,
                "subtasks": item["subtasks"],
                "done": item.get("done", False)
            }

            st.markdown("---")

        new_item_name = st.text_input("Nom du nouvel élément")
        new_item_capacity = st.number_input("Capacité du nouvel élément", min_value=1, value=1)
        if st.button("Ajouter un élément") and new_item_name:
            st.session_state.products[product_to_edit]["items"].append({
                "name": new_item_name,
                "capacity": new_item_capacity,
                "subtasks": [],
                "done": False
            })
            save_current_session()
            st.success(f"Ajouté {new_item_name} à {product_to_edit}")
            st.rerun()

# New task management section
        st.subheader("Tâches du produit")
        if "tasks" not in st.session_state.products[product_to_edit]:
            st.session_state.products[product_to_edit]["tasks"] = []

        for i, task in enumerate(st.session_state.products[product_to_edit]["tasks"]):
            col1, col2 = st.columns([3, 1])
            with col1:
                task_name = st.text_input(f"Nom de la tâche {i+1}", task["name"], key=f"task_name_{i}")
            with col2:
                if st.button("Supprimer la tâche", key=f"remove_task_{i}"):
                    st.session_state.products[product_to_edit]["tasks"].pop(i)
                    save_current_session()
                    st.rerun()

            st.write("Sous-tâches:")
            for j, subtask in enumerate(task["subtasks"]):
                col1, col2 = st.columns([3, 1])
                with col1:
                    subtask_name = st.text_input(f"Nom de la sous-tâche {j+1}", subtask["name"], key=f"task_subtask_name_{i}_{j}")
                with col2:
                    if st.button("Supprimer la sous-tâche", key=f"remove_task_subtask_{i}_{j}"):
                        task["subtasks"].pop(j)
                        save_current_session()
                        st.rerun()

            new_subtask = st.text_input(f"Nouvelle sous-tâche pour la tâche {task['name']}", key=f"new_task_subtask_{i}")
            if st.button(f"Ajouter une sous-tâche à {task['name']}", key=f"add_task_subtask_{i}") and new_subtask:
                task["subtasks"].append({"name": new_subtask, "done": False})
                save_current_session()
                st.success(f"Sous-tâche '{new_subtask}' ajoutée à la tâche '{task['name']}'")
                st.rerun()

            st.session_state.products[product_to_edit]["tasks"][i] = {
                "name": task_name,
                "subtasks": task["subtasks"],
                "done": task.get("done", False)
            }

            st.markdown("---")

        # New task addition
        new_task_name = st.text_input("Nom de la nouvelle tâche")
        if st.button("Ajouter une tâche") and new_task_name:
            st.session_state.products[product_to_edit]["tasks"].append({
                "name": new_task_name,
                "subtasks": [],
                "done": False
            })
            save_current_session()
            st.success(f"Ajouté la tâche {new_task_name} à {product_to_edit}")
            st.rerun()

def duplicate_product():
    st.subheader("Dupliquer le Produit")
    product_to_duplicate = st.selectbox("Sélectionnez un produit à dupliquer:", list(st.session_state.products.keys()))
    new_product_name = st.text_input("Entrez le nouveau nom du produit dupliqué:")

    if st.button("Dupliquer le Produit") and new_product_name and product_to_duplicate:
        if new_product_name in st.session_state.products:
            st.error(f"Un produit nommé '{new_product_name}' existe déjà.")
        else:
            # Create a new copy of the product without the '_id' field
            new_product = {k: v for k, v in st.session_state.products[product_to_duplicate].items() if k != '_id'}
            new_product['name'] = new_product_name
            st.session_state.products[new_product_name] = new_product
            save_current_session()
            st.success(f"Dupliqué '{product_to_duplicate}' en '{new_product_name}'")
            st.rerun()

    st.subheader("Supprimer un produit")
    product_to_delete = st.selectbox("Sélectionnez un produit à supprimer", [""] + list(st.session_state.products.keys()))
    if product_to_delete and st.button(f"Supprimer {product_to_delete}"):
        del st.session_state.products[product_to_delete]
        save_current_session()
        st.success(f"Produit '{product_to_delete}' supprimé")
        st.experimental_rerun()

def main():
    if 'session_key' not in st.session_state:
        st.session_state.session_key = "LUNDI"

    with st.sidebar:
        session_key = st.selectbox("Sélectionnez le jour:", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"], key="day_selector")

    if session_key != st.session_state.session_key:
        st.session_state.session_key = session_key

    set_theme(st.session_state.session_key)
    init_session()  # Call init_session() here

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
                st.session_state[f'{st.session_state.session_key}_checklist'] = pd.concat(
                    [st.session_state[f'{st.session_state.session_key}_checklist'], new_row], 
                    ignore_index=True
                )
                save_current_session()
                st.rerun()

            st.subheader("Commandes")
            edited_df = st.data_editor(
                st.session_state[f'{st.session_state.session_key}_checklist'], 
                num_rows="dynamic", 
                use_container_width=True
            )
            st.session_state[f'{st.session_state.session_key}_checklist'] = edited_df
            save_current_session()

        elif menu_choice == "Gestion des Tâches Générales":
            manage_general_todos()

        elif menu_choice == "Gestion des Produits":
            manage_products()

        elif menu_choice == "Dupliquer le Produit":
            duplicate_product()

    tabs = st.sidebar.radio("Navigation", ["Checklist", "Commandes", "Gestion des Produits", "Tâches Générales"])

    if tabs == "Checklist":
        render_checklist()
    elif tabs == "Commandes":
        st.subheader("Ajouter aux commandes")
        new_product = st.selectbox("Sélectionnez un produit:", list(st.session_state.products.keys()))
        new_quantity = st.number_input("Entrez la quantité:", min_value=1, value=1, step=1)
        if st.button("Ajouter aux commandes"):
            new_row = pd.DataFrame({'Produit': [new_product], 'Quantité': [new_quantity]})
            st.session_state[f'{st.session_state.session_key}_checklist'] = pd.concat(
                [st.session_state[f'{st.session_state.session_key}_checklist'], new_row], 
                ignore_index=True
            )
            save_current_session()
            st.rerun()
        
        st.subheader("Commandes")
        edited_df = st.data_editor(
            st.session_state[f'{st.session_state.session_key}_checklist'], 
            num_rows="dynamic", 
            use_container_width=True
        )
        st.session_state[f'{st.session_state.session_key}_checklist'] = edited_df
        save_current_session()
    elif tabs == "Gestion des Produits":
        manage_products()
    elif tabs == "Tâches Générales":
        manage_general_todos()

if __name__ == "__main__":
    main()
