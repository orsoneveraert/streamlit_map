import streamlit as st
import pandas as pd
import math
import json
import os

PRODUCT_DATABASE_PATH = 'product_database.json'

def load_product_database():
    if os.path.exists(PRODUCT_DATABASE_PATH):
        with open(PRODUCT_DATABASE_PATH, 'r') as f:
            return json.load(f)
    return {}

def save_product_database(data):
    with open(PRODUCT_DATABASE_PATH, 'w') as f:
        json.dump(data, f)

def load_state(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {"checklist": []}

def save_state(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

def init_session(session_key):
    if 'products' not in st.session_state:
        st.session_state.products = load_product_database()
    if 'checklist' not in st.session_state:
        session_data = load_state(f'{session_key}_session.json')
        st.session_state.checklist = pd.DataFrame(session_data.get('checklist', []), columns=['Produit', 'Quantité'])

def save_current_session(session_key):
    session_data = {'checklist': st.session_state.checklist.to_dict(orient='records')}
    save_state(f'{session_key}_session.json', session_data)

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

def render_checklist():
    st.markdown("### 📋 Checklist - Mise en place")
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
                    subtask['done'] = st.checkbox(subtask['name'], value=subtask.get('done', False), key=subtask_key)
                
                for prod_item in st.session_state.products[product]['items']:
                    if prod_item['name'] == item['name']:
                        prod_item['done'] = item['done']
                        prod_item['subtasks'] = item['subtasks']
            
            st.markdown("---")
    save_product_database(st.session_state.products)

def manage_products():
    with st.expander("Gestion des Produits"):
        st.markdown("### 🛠️ Gestion des Produits")
        product_to_edit = st.selectbox("Sélectionnez un produit à modifier:", 
                                       list(st.session_state.products.keys()) + ["Ajouter un nouveau produit"])

        if product_to_edit == "Ajouter un nouveau produit":
            new_product = st.text_input("Entrez le nom du nouveau produit:")
            if st.button("Ajouter le produit") and new_product and new_product not in st.session_state.products:
                st.session_state.products[new_product] = {"items": []}
                save_product_database(st.session_state.products)
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
                        save_product_database(st.session_state.products)
                        st.rerun()
                
                st.write("Sous-tâches:")
                for j, subtask in enumerate(item["subtasks"]):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        subtask["name"] = st.text_input(f"Nom de la sous-tâche", subtask["name"], key=f"subtask_name_{i}_{j}")
                    with col2:
                        if st.button("Supprimer la sous-tâche", key=f"remove_subtask_{i}_{j}"):
                            item["subtasks"].pop(j)
                            save_product_database(st.session_state.products)
                            st.rerun()
                
                new_subtask = st.text_input(f"Nouvelle sous-tâche pour {item['name']}", key=f"new_subtask_{i}")
                if st.button(f"Ajouter une sous-tâche à {item['name']}", key=f"add_subtask_{i}") and new_subtask:
                    item["subtasks"].append({"name": new_subtask, "done": False})
                    save_product_database(st.session_state.products)
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
                save_product_database(st.session_state.products)
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
                save_product_database(st.session_state.products)
                st.success(f"Dupliqué '{product_to_duplicate}' en '{new_product_name}'")
                st.rerun()

def main():
    st.set_page_config(layout="wide", page_title="Suivi de Mise en Place")
    
    if 'session_key' not in st.session_state:
        st.session_state.session_key = "LUNDI"
    
    session_key = st.selectbox("Sélectionnez le jour:", ["LUNDI", "MARDI", "JEUDI", "VENDREDI"], key="day_selector")
    
    if session_key != st.session_state.session_key:
        st.session_state.clear()
        st.session_state.session_key = session_key
    
    set_theme(st.session_state.session_key)
    init_session(st.session_state.session_key)
    
    st.title(f"{st.session_state.session_key}")

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

if __name__ == "__main__":
    main()
