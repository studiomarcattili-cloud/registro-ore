import streamlit as st
import pandas as pd
import sqlite3
import os

# 1. CONFIGURAZIONE GRAFICA
st.set_page_config(page_title="Gestione Ore Commesse", layout="wide", page_icon="⏱️")

# CSS per i colori (commentato se vuoi testare il tema standard)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, p, span, label { color: #1E1E1E !important; }
    .stButton > button { background-color: #0066cc !important; color: white !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

PASSWORD_ADMIN = "admin2026"

# 2. CONNESSIONE E INIZIALIZZAZIONE DATABASE
def get_db_connection():
    conn = sqlite3.connect('gestione_commesse_web.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()

# Creazione Tabelle
cursor.execute('''CREATE TABLE IF NOT EXISTS commesse (id INTEGER PRIMARY KEY AUTOINCREMENT, codice TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, stato TEXT DEFAULT 'Attiva')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS anagrafica_utenti (username TEXT PRIMARY KEY, password TEXT NOT NULL, stato TEXT DEFAULT 'Attivo')''')
conn.commit()

# Popolamento iniziale
if cursor.execute("SELECT COUNT(*) FROM anagrafica_utenti").fetchone()[0] == 0:
    cursor.execute("INSERT INTO anagrafica_utenti (username, password, stato) VALUES (?, ?, ?)", ("Amministratore", "admin2026", "Attivo"))
    conn.commit()

st.title("⏱️ Registro Ore e Commesse")

# 3. LOGICA PANNELLO COMMESSE
def mostra_pannello_commesse(chiave_univoca):
    st.subheader("📂 Controllo e Creazione Commesse")
    with st.form(f"form_commessa_{chiave_univoca}", clear_on_submit=True):
        codice_commessa = st.text_input("Codice Commessa").strip().upper()
        nome_commessa = st.text_input("Nome Nuova Commessa").strip()
        if st.form_submit_button("Crea"):
            if codice_commessa and nome_commessa:
                try:
                    cursor.execute("INSERT INTO commesse (codice, nome) VALUES (?, ?)", (codice_commessa, nome_commessa))
                    conn.commit()
                    st.rerun()
                except: st.error("Codice già esistente.")
    
    df_commesse = pd.read_sql_query("SELECT * FROM commesse", conn)
    for _, row in df_commesse.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"• **[{row['codice']}] {row['nome']}** ({row['stato']})")
        
        # Bottone Archivio
        if c2.button("📁/🔓" if row['stato']=="Attiva" else "Attiva", key=f"st_{chiave_univoca}_{row['id']}"):
            nuovo_st = "Archiviata" if row['stato'] == "Attiva" else "Attiva"
            cursor.execute("UPDATE commesse SET stato = ? WHERE id = ?", (nuovo_st, row['id']))
            conn.commit()
            st.rerun()
            
        # Bottone Elimina (Corretto nell'indentazione)
        if c3.button("🗑️ Elimina", key=f"del_{chiave_univoca}_{row['id']}"):
            cursor.execute("DELETE FROM commesse WHERE id = ?", (row['id'],))
            conn.commit()
            st.rerun()

# 4. GESTIONE LOGIN
if "loggato" not in st.session_state:
    st.session_state.update({"loggato": False, "utente_corrente": ""})

if not st.session_state["loggato"]:
    st.subheader("🔐 Accedi al Sistema")
    pwd_input = st.text_input("Password Admin", type="password")
    if st.button("Entra") and pwd_input == PASSWORD_ADMIN:
        st.session_state.update({"loggato": True, "utente_corrente": "Amministratore"})
        st.rerun()
else:
    if st.sidebar.button("Logout"): st.session_state.clear(); st.rerun()
    st.write(f"Benvenuto {st.session_state['utente_corrente']}")
    mostra_pannello_commesse("admin_panel")
