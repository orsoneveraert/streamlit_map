import streamlit as st
import pandas as pd
import math
import json
import os

PRODUCT_DATABASE_PATH = 'product_database.json'
GENERAL_TODOS_PATH = 'general_todos.json'

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f)

def init_session(session_key):
    if 'products' not in st.session_state:
        st.session_state.products = load_json(PRODUCT_DATABASE_PATH)
    if 'checklist' not in st.session_state:
        session_data = load_json(f'{session_key}_session.json')
        st.session_state.checklist = pd.DataFrame(session_data.get('checklist', []), columns=['Produit', 'Quantité'])
    if 'general_todos' not in st.session_state:
        st.session_state.general_todos = load_json(GENERAL_TODOS_PATH).get('todos', [])

def save_current_session(session_key):
    session_data = {'checklist': st.session_state.checklist.to_dict(orient='records')}
    save_json(f'{session_key}_session.json', session_data)
    save_json(PRODUCT_DATABASE_PATH, st.session_state.products)
    save_json(GENERAL_TODOS_PATH, {'todos': st.session_state.general_todos})

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
        "done": item["done"]
    } for item in items]

def manage_general_todos():
    with st.expander("Gestion des Tâches Générales", expanded=True):
        st.markdown("### 📝 Tâches Générales")
        
        # Add new todo
        new_todo = st.text_input("Nouvelle tâche générale")
        if st.button("Ajouter une tâche générale") and new_todo:
            st.session_state.general_todos.append({'task': new_todo, 'active': True, 'done': False})
            st.success(f"Tâche '{new_todo}' ajoutée")
            st.rerun()

        # Display and manage existing todos
        for i, todo in enumerate(st.session_state.general_todos):
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.session_state.general_todos[i]['task'] = st.text_input(f"Tâche {i+1}", todo['task'], key=f"general_todo_{i}")
            with col2:
                st.session_state.general_todos[i]['active'] = st.checkbox("Actif", todo['active'], key=f"general_todo_active_{i}")
            with col3:
                st.session_state.general_todos[i]['done'] = st.checkbox("Fait", todo.get('done', False), key=f"general_todo_done_{i}")
            with col4:
                if st.button("Supprimer", key=f"remove_general_todo_{i}"):
                    st.session_state.general_todos.pop(i)
                    st.rerun()
        
        st.markdown("---")
        st.markdown("Ces tâches générales apparaîtront dans la checklist de chaque jour si elles sont marquées comme actives.")

def render_checklist():
    st.markdown("### 📋 Checklist - Mise en place")
    
    # Render general todos
    st.markdown("#### Tâches Générales")
    for todo in st.session_state.general_todos:
        if todo['active']:
            todo_key = f"general_todo_{todo['task']}"
            todo['done'] = st.checkbox(todo['task'], value=todo.get('done', False), key=todo_key)
    
    st.markdown("---")
    st.markdown("#### Tâches Spécifiques aux Produits")

    # Render product-specific items
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

def manage_products():
    with st.expander("Gestion des Produits"):
        st.markdown("### 🛠️ Gestion des Produits")
        product_to_edit = st.selectbox("Sélectionnez un produit à modifier:", 
                                       list(st.session_state.products.keys()) + ["Ajouter un nouveau produit"])

        if product_to_edit == "Ajouter un nouveau produit":
            new_product = st.text_input("Entrez le nom du nouveau produit:")
            if st.button("Ajouter le produit") and new_product and new_product not in st.session_state.products:
                st.session_state.products[new_product] = {"items": []}
                st.success(f"Ajouté {new_product}")
                st.rerun()

        elif product_to_edit in st.session_state.products:
            st.subheader(f"Modification de {product_to_edit}")
            
            for i, item in enumerate(st.session_state.products[product_to_edit]["items"]):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    new_name = st.text_input(f"Nom de l'élément", item["name"], key=f"name_{i}")
                with col2:
                    new_capacity = st.number_input(f"Capacité", min_value=1, value=item["capacity"], key=f"capacity_{i}")
                with col3:
                    if st.button("Supprimer l'élément", key=f"remove_item_{i}"):
                        st.session_state.products[product_to_edit]["items"].pop(i)
                        st.rerun()
                
                st.write("Sous-tâches:")
                for j, subtask in enumerate(item["subtasks"]):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        subtask["name"] = st.text_input(f"Nom de la sous-tâche", subtask["name"], key=f"subtask_name_{i}_{j}")
                    with col2:
                        if st.button("Supprimer la sous-tâche", key=f"remove_subtask_{i}_{j}"):
                            item["subtasks"].pop(j)
                            st.rerun()
                
                new_subtask = st.text_input(f"Nouvelle sous-tâche pour {item['name']}", key=f"new_subtask_{i}")
                if st.button(f"Ajouter une sous-tâche à {item['name']}", key=f"add_subtask_{i}") and new_subtask:
                    item["subtasks"].append({"name": new_subtask, "done": False})
                    st.success(f"Sous-tâche '{new_subtask}' ajoutée à {item['name']}")
                    st.rerun()
                
                st.session_state.products[product_to_edit]["items"][i] = {
                    "name": new_name, 
                    "capacity": new_capacity, 
                    "subtasks": item["subtasks"], 
                    "done": item["done"]
                }
                st.markdown("---")
            
            new_item_name = st.text_input("Nom du nouvel élément")
            new_item_capacity = st.number_input("Capacité de l'élément", min_value=1, value=1)
            if st.button("Ajouter un élément") and new_item_name:
                st.session_state.products[product_to_edit]["items"].append({
                    "name": new_item_name, 
                    "capacity": new_item_capacity, 
                    "subtasks": [], 
                    "done": False
                })
                st.success(f"Ajouté {new_item_name} à {product_to_edit}")
                st.rerun()

def duplicate_product():
    with st.expander("Dupliquer le Produit"):
        st.markdown("### 🔄 Dupliquer le Produit")
        product_to_duplicate = st.selectbox("Sélectionnez un produit à dupliquer:", list(st.session_state.products.keys()))
        new_product_name = st.text_input("Entrez le nouveau nom du produit dupliqué:")

        if st.button("Dupliquer le Produit") and new_product_name and product_to_duplicate:
            if new_product_name in st.session_state.products:
                st.error(f"Un produit nommé '{new_product_name}' existe déjà.")
            else:
                st.session_state.products[new_product_name] = st.session_state.products[product_to_duplicate].copy()
                st.success(f"Dupliqué '{product_to_duplicate}' en '{new_product_name}'")
                st.rerun()

def main():
    st.set_page_config(layout="wide", page_title="Suivi de Mise en Place")

    # Add logo to the sidebar
    st.logo(
        LOGO_URL_LARGE,
        link="https://mazette.brussels/wp-content/uploads/2021/03/MAZETTE_LogoBlack_Full-MD.png",
        icon_image=LOGO_URL_SMALL,
    )
    
    if 'session_key' not in st.session_state:
        st.session_state.session_key = "LUNDI"
    
    session_key = st.selectbox("Sélectionnez le jour:", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"], key="day_selector")
    
    if session_key != st.session_state.session_key:
        st.session_state.clear()
        st.session_state.session_key = session_key
    
    set_theme(st.session_state.session_key)
    init_session(st.session_state.session_key)
    
    st.title(f"{st.session_state.session_key}")

    # Move general to-dos management to the top
    manage_general_todos()

    with st.expander("Ajouter aux commandes"):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_product = st.selectbox("Sélectionnez un produit:", list(st.session_state.products.keys()))
        with col2:
            new_quantity = st.number_input("Entrez la quantité:", min_value=1, value=1, step=1)
        with col3:
            if st.button("Ajouter aux commandes"):
                new_row = pd.DataFrame({'Produit': [new_product], 'Quantité': [new_quantity]})
                st.session_state.checklist = pd.concat([st.session_state.checklist, new_row], ignore_index=True)
                save_current_session(st.session_state.session_key)
                st.rerun()

    with st.expander("Commandes", expanded=True):
        st.markdown("### ✅ Commandes")
        edited_df = st.data_editor(st.session_state.checklist, num_rows="dynamic", use_container_width=True)
        st.session_state.checklist = edited_df
        save_current_session(st.session_state.session_key)

    render_checklist()
    manage_products()
    duplicate_product()

    save_current_session(st.session_state.session_key)

if __name__ == "__main__":
    main()
