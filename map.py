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
