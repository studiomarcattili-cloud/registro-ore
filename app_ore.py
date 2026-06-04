import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import io
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

# 1. CONFIGURAZIONE GRAFICA
st.set_page_config(page_title="Gestione Ore Commesse", layout="wide", page_icon="⏱️")

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; }
    h1, h2, h3, h4, p, span, label { color: #1E1E1E !important; }
    input, select, textarea, div[data-baseweb="select"] { color: #1E1E1E !important; }
    div[data-baseweb="popover"] li { color: #1E1E1E !important; }
    .stButton > button {
        background-color: #0066cc !important;
        color: white !important;
        border-radius: 5px !important;
        font-weight: bold !important;
    }
    .stButton > button:hover { background-color: #0052a3 !important; }
    .stTabs [data-baseweb="tab"] { color: #333333; }
    </style>
""", unsafe_allow_html=True)

PASSWORD_ADMIN = "admin2026"

# 2. CONNESSIONE DATABASE
def get_db_connection():
    conn = sqlite3.connect('gestione_commesse_web.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()

# Creazione Tabelle
cursor.execute('''CREATE TABLE IF NOT EXISTS commesse (id INTEGER PRIMARY KEY AUTOINCREMENT, codice TEXT UNIQUE NOT NULL, nome TEXT NOT NULL, stato TEXT DEFAULT 'Attiva')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS anagrafica_utenti (username TEXT PRIMARY KEY, password TEXT NOT NULL, costo_orario_corrente REAL NOT NULL, stato TEXT DEFAULT 'Attivo')''')
cursor.execute('''CREATE TABLE IF NOT EXISTS ore_lavoro (id INTEGER PRIMARY KEY AUTOINCREMENT, collaboratore TEXT NOT NULL, commessa_id INTEGER, ore REAL NOT NULL, data TEXT NOT NULL, descrizione TEXT DEFAULT '', costo_orario_applicato REAL DEFAULT 0.0, FOREIGN KEY (commessa_id) REFERENCES commesse (id))''')
conn.commit()

# Migrazioni automatiche
try: cursor.execute("SELECT costo_orario_applicato FROM ore_lavoro LIMIT 1")
except sqlite3.OperationalError: cursor.execute("ALTER TABLE ore_lavoro ADD COLUMN costo_orario_applicato REAL DEFAULT 0.0")
try: cursor.execute("SELECT stato FROM commesse LIMIT 1")
except sqlite3.OperationalError: cursor.execute("ALTER TABLE commesse ADD COLUMN stato TEXT DEFAULT 'Attiva'")
conn.commit()

# Popolamento iniziale
if cursor.execute("SELECT COUNT(*) FROM anagrafica_utenti").fetchone()[0] == 0:
    cursor.executemany("INSERT INTO anagrafica_utenti (username, password, costo_orario_corrente, stato) VALUES (?, ?, ?, ?)", 
                       [("Giorgia Bruni", "GB2026", 25.0, "Attivo"), ("Stefano Di Gennaro", "SDG2026", 28.0, "Attivo"), ("Stefano Marcattili", "SM2026", 30.0, "Attivo"), ("Amministratore", "admin2026", 35.0, "Attivo")])
    conn.commit()

st.title("⏱️ Registro Ore e Costi Commesse")
st.write("---")

# Sessione Login
if "loggato" not in st.session_state:
    st.session_state.update({"loggato": False, "ruolo": None, "utente_corrente": ""})

df_utenti_db = pd.read_sql_query("SELECT * FROM anagrafica_utenti WHERE stato = 'Attivo'", conn)
lista_collaboratori_attivi = df_utenti_db[df_utenti_db['username'] != 'Amministratore']['username'].tolist()
tutti_utenti_attivi = df_utenti_db['username'].tolist()

def get_mostra_nome(row): return f"[{row.get('codice')}] {row.get('nome')}"

def mostra_pannello_commesse(chiave_univoca):
    st.subheader("📂 Controllo e Creazione Commesse")
    with st.form(f"form_commessa_{chiave_univoca}", clear_on_submit=True):
        codice_commessa = st.text_input("Codice Commessa").strip().upper()
        nuova_commessa = st.text_input("Nome Nuova Commessa").strip()
        if st.form_submit_button("Crea") and codice_commessa and nuova_commessa:
            try:
                cursor.execute("INSERT INTO commesse (codice, nome) VALUES (?, ?)", (codice_commessa, nuova_commessa))
                conn.commit()
                st.rerun()
            except: st.error("Codice già esistente.")
    
    df_commesse = pd.read_sql_query("SELECT * FROM commesse", conn)
    for _, row in df_commesse.iterrows():
        c1, c2, c3 = st.columns([3, 1, 1])
        c1.write(f"• **[{row['codice']}] {row['nome']}** ({row['stato']})")
        if c2.button("📁/🔓" if row['stato']=="Attiva" else "Attiva", key=f"st_{chiave_univoca}_{row['id']}"):
            nuovo_st = "Archiviata" if row['stato'] == "Attiva" else "Attiva"
            cursor.execute("UPDATE commesse SET stato = ? WHERE id = ?", (nuovo_st, row['id'])); conn.commit(); st.rerun()
        if c3.button("🗑️", key=f"del_{chiave
