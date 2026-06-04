import streamlit as st
import pandas as pd
import sqlite3

# 1. CONFIGURAZIONE GRAFICA
st.set_page_config(page_title="Gestione Ore Commesse", layout="wide", page_icon="⏱️")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, p, span, label { color: #1E1E1E !important; }
    .stButton > button { background-color: #0066cc !important; color: white !important; font-weight: bold !important; }
    </style>
""", unsafe_allow_html=True)

PASSWORD_ADMIN = "admin2026"

# 2. CONNESSIONE DATABASE
def get_db_connection():
    conn = sqlite3.connect('gestione_commesse_web.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()

# Inizializzazione Tabelle
cursor.execute('''CREATE TABLE IF NOT EXISTS commesse (id INTEGER PRIMARY KEY AUTOINCREMENT, codice TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, stato TEXT DEFAULT 'Attiva')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS anagrafica_utenti (username TEXT PRIMARY KEY, password TEXT NOT NULL, stato TEXT DEFAULT 'Attivo')''')
conn.commit()

if cursor.execute("SELECT COUNT(*) FROM anagrafica_utenti").fetchone()[0] == 0:
    cursor.execute("INSERT INTO anagrafica_utenti VALUES (?, ?, ?)", ("Amministratore", "admin2026", "Attivo"))
    conn.commit()

# 3. FUNZIONI INTERFACCIA
def mostra_pannello_admin():
    st.subheader("📂 Pannello Amministratore: Gestione Commesse")
    with st.form("form_commessa", clear_on_submit=True):
        c1, c2 = st.columns(2)
        codice = c1.text_input("Codice Commessa").strip().upper()
        nome = c2.text_input("Nome Commessa").strip()
        if st.form_submit_button("Crea Commessa"):
            if codice and nome:
                try:
                    cursor.execute("INSERT INTO commesse (codice, nome) VALUES (?, ?)", (codice, nome))
                    conn.commit()
                    st.rerun()
                except: st.error("Codice già esistente.")
    
    df = pd.read_sql_query("SELECT * FROM commesse", conn)
    for _, row in df.iterrows():
        cols = st.columns([3, 1, 1])
        cols[0].write(f"• **[{row['codice']}] {row['nome']}** ({row['stato']})")
        if cols[1].button("📁/🔓" if row['stato']=="Attiva" else "Attiva", key=f"st_{row['id']}"):
            nuovo_st = "Archiviata" if row['stato'] == "Attiva" else "Attiva"
            cursor.execute("UPDATE commesse SET stato = ? WHERE id = ?", (nuovo_st, row['id']))
            conn.commit(); st.rerun()
        if cols[2].button("🗑️ Elimina", key=f"del_{row['id']}"):
            cursor.execute("DELETE FROM commesse WHERE id = ?", (row['id'],))
            conn.commit(); st.rerun()

def mostra_pannello_collaboratore(user):
    st.subheader(f"👋 Benvenuto, {user}")
    st.write("Qui potrai inserire le tue ore di lavoro.")
    # Aggiungi qui la logica di inserimento ore per il collaboratore

# 4. LOGICA LOGIN
if "loggato" not in st.session_state:
    st.session_state.update({"loggato": False, "utente_corrente": "", "ruolo": ""})

if not st.session_state["loggato"]:
    st.title("⏱️ Login Registro Ore")
    tipo = st.radio("Accesso:", ["Collaboratore", "Amministratore"])
    
    if tipo == "Amministratore":
        pwd = st.text_input("Password", type="password")
        if st.button("Entra") and pwd == PASSWORD_ADMIN:
            st.session_state.update({"loggato": True, "utente_corrente": "Amministratore", "ruolo": "admin"})
            st.rerun()
    else:
        user = st.selectbox("Username", ["Giorgia Bruni", "Stefano Di Gennaro", "Stefano Marcattili"])
        if st.button("Accedi"):
            st.session_state.update({"loggato": True, "utente_corrente": user, "ruolo": "
