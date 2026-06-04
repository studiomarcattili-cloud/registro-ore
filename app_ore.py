import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os
import io

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

# 2. CONNESSIONE E CONFIGURAZIONE DATABASE
def get_db_connection():
    conn = sqlite3.connect('gestione_commesse_web.db', check_same_thread=False)
    return conn

conn = get_db_connection()
cursor = conn.cursor()

# Creazione Tabelle Standard se non esistono
cursor.execute('''
CREATE TABLE IF NOT EXISTS commesse (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    codice TEXT UNIQUE NOT NULL,
    nome TEXT NOT NULL,
    stato TEXT DEFAULT 'Attiva'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS anagrafica_utenti (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    costo_orario_corrente REAL NOT NULL,
    stato TEXT DEFAULT 'Attivo'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS ore_lavoro (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collaboratore TEXT NOT NULL,
    commessa_id INTEGER,
    ore REAL NOT NULL,
    data TEXT NOT NULL,
    descrizione TEXT DEFAULT '',
    costo_orario_applicato REAL DEFAULT 0.0,
    FOREIGN KEY (commessa_id) REFERENCES commesse (id)
)
''')
conn.commit()

# AGGIORNAMENTO AUTOMATICO STRUTTURA DATABASE (Fix per errore No Such Column)
try:
    cursor.execute("SELECT costo_orario_applicato FROM ore_lavoro LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE ore_lavoro ADD COLUMN costo_orario_applicato REAL DEFAULT 0.0")
    conn.commit()

try:
    cursor.execute("SELECT stato FROM commesse LIMIT 1")
except sqlite3.OperationalError:
    cursor.execute("ALTER TABLE commesse ADD COLUMN stato TEXT DEFAULT 'Attiva'")
    conn.commit()

# Popolamento iniziale utenti se vuoto
utenti_esistenti = cursor.execute("SELECT COUNT(*) FROM anagrafica_utenti").fetchone()[0]
if utenti_esistenti == 0:
    utenti_iniziali = [
        ("Giorgia Bruni", "GB2026", 25.0, "Attivo"),
        ("Stefano Di Gennaro", "SDG2026", 28.0, "Attivo"),
        ("Stefano Marcattili", "SM2026", 30.0, "Attivo"),
        ("Amministratore", "admin2026", 35.0, "Attivo")
    ]
    cursor.executemany("INSERT INTO anagrafica_utenti (username, password, costo_orario_corrente, stato) VALUES (?, ?, ?, ?)", utenti_iniziali)
    conn.commit()

# --- LOGO STUDIO ---
if os.path.exists("logo.png"):
    st.image("logo.png", width=180)

st.title("⏱️ Registro Ore e Costi Commesse")
st.write("---")

# --- GESTIONE SESSIONE (LOGIN) ---
if "loggato" not in st.session_state:
    st.session_state["loggato"] = False
    st.session_state["ruolo"] = None
    st.session_state["utente_corrente"] = ""

df_utenti_db = pd.read_sql_query("SELECT * FROM anagrafica_utenti WHERE stato = 'Attivo'", conn)
lista_collaboratori_attivi = df_utenti_db[df_utenti_db['username'] != 'Amministratore']['username'].tolist()
tutti_utenti_attivi = df_utenti_db['username'].tolist()

def get_mostra_nome(row):
    c_cod = row.get('codice', 'N.D.')
    c_nom = row.get('nome', 'Senza Nome')
    return f"[{c_cod}] {c_nom}"

# FUNZIONE PANNELLO COMMESSE
def mostra_pannello_commesse(chiave_univoca):
    st.subheader("📂 Controllo e Creazione Commesse")
    with st.form(f"form_commessa_{chiave_univoca}", clear_on_submit=True):
        codice_commessa = st.text_input("Codice Commessa (es. C2026-01, JOB-02)").strip().upper()
        nuova_commessa = st.text_input("Nome Nuova Commessa").strip()
        submit_c = st.form_submit_button("Crea Nuova Commessa")
        
        if submit_c and nuova_commessa and codice_commessa:
            try:
                cursor.execute("INSERT INTO commesse (codice, nome) VALUES (?, ?)", (codice_commessa, nuova_commessa))
                conn.commit()
                st.success(f"✔️ Commessa [{codice_commessa}] {nuova_commessa} creata!")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("⚠️ Questo Codice Commessa esiste già.")
    
    st.write("🛠️ **Azioni sulle Commesse Esistenti**")
    df_tutte_commesse = pd.read_sql_query("SELECT * FROM commesse", conn)
    if not df_tutte_commesse.empty:
        for idx, row in df_tutte_commesse.iterrows():
            c_id, c_cod, c_nome, c_stato = row['id'], row['codice'], row['nome'], row['stato']
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.write(f"• **[{c_cod}] {c_nome}** ({c_stato})")
            
            label_archivia = "📁 Archivia" if c_stato == "Attiva" else "🔓 Attiva"
            if c2.button(label_archivia, key=f"arch_{chiave_univoca}_{c_id}"):
                nuovo_st = "Archiviata" if c_stato == "Attiva" else "Attiva"
                cursor.execute("UPDATE commesse SET stato = ? WHERE id = ?", (nuovo_st, c_id))
                conn.commit()
                st.rerun()
            
            if c3.button("🗑️ Elimina", key=f"del_{chiave_univoca}_{c_id}"):
                ore_collegate = cursor.execute("SELECT COUNT(*) FROM ore_lavoro WHERE commessa_id = ?", (c_id,)).fetchone()[0]
                if ore_collegate > 0:
                    st.error(f"❌ Impossibile eliminare: ha {ore_collegate} ore collegate. Archiviala!")
                else:
                    cursor.execute("DELETE FROM commesse WHERE id = ?", (c_id,))
                    conn.commit()
                    st.rerun()

if not st.session_state["loggato"]:
    st.subheader("🔐 Accedi al Sistema")
    tipo_accesso = st.radio("Seleziona il tipo di accesso:", ["Collaboratore", "Amministratore"])
    
    if tipo_accesso == "Collaboratore":
        username = st.selectbox("Seleziona il tuo Nome/Username", options=[""] + lista_collaboratori_attivi)
        password = st.text_input("Inserisci la tua Password", type="password")
        
        if st.button("Accedi come Collaboratore"):
            utente_match = df_utenti_db[(df_utenti_db['username'] == username) & (df_utenti_db['password'] == password)]
            if not utente_match.empty:
                st.session_state["loggato"] = True
                st.session_state["ruolo"] = "collaboratore"
                st.session_state["utente_corrente"] = username
                st.rerun()
            else:
                st.error("⚠️ Username o Password errati.")
    else:
        password_admin_input = st.text_input("Inserisci la Password Amministratore", type="password")
        if st.button("Accedi come Admin"):
            if password_admin_input == PASSWORD_ADMIN:
                st.session_state["loggato"] = True
                st.session_state["ruolo"] = "admin"
                st.session_state["utente_corrente"] = "Amministratore"
                st.rerun()
            else:
                st.error("⚠️ Password Amministratore errata.")
else:
    # --- LOGOUT ---
    st.sidebar.write(f"👤 Loggato come: **{st.session_state['utente_corrente']}**")
    if st.sidebar.button("🚪 Disconnetti (Logout)"):
        st.session_state["loggato"] = False
        st.session_state["ruolo"] = None
        st.session_state["utente_corrente"] = ""
        st.rerun()

    df_commesse_attive = pd.read_sql_query("SELECT * FROM commesse WHERE stato = 'Attiva'", conn)

    # --- SITO COLLABORATORE ---
    if st.session_state["ruolo"] == "collaboratore":
        tab_ore_user, tab_commesse_user, tab_password_user = st.tabs(["📝 Inserimento Ore", "📂 Gestione Commesse", "🔒 Sicurezza Account"])
        
        with tab_ore_user:
            col_user_1, col_user_2 = st.columns([5, 3])
            with col_user_1:
                st.subheader(f"📝 Benvenuto {st.session_state['utente_corrente']}. Inserisci le tue ore:")
                if df_commesse_attive.empty:
                    st.warning("⚠️ Nessuna commessa attiva nel sistema. Creane una nel tab 'Gestione Commesse'.")
                else:
                    df_commesse_attive['visualizzazione'] = df_commesse_attive.apply(get_mostra_nome, axis=1)
                    lista_commesse = dict(zip(df_commesse_attive['visualizzazione'], df_commesse_attive['id']))
                    
                    with st.form("form_ore_user", clear_on_submit=True):
                        commessa_scelta = st.selectbox("Seleziona la Commessa", options=lista_commesse.keys())
                        ore = st.number_input("Ore lavorate", min_value=0.5, max_value=24.0, value=8.0, step=0.5)
                        data_lavoro = st.date_input("Data del lavoro", datetime.now())
                        descrizione_attivita = st.text_area("Descrizione delle attività svolte", placeholder="Dettaglio del lavoro...")
                        
                        submit_ore = st.form_submit_button("Registra Ore")
                        if submit_ore:
                            tariffa_istante = float(df_utenti_db[df_utenti_db['username'] == st.session_state['utente_corrente']]['costo_orario_corrente'].values[0])
                            cursor.execute(
                                "INSERT INTO ore_lavoro (collaboratore, commessa_id, ore, data, descrizione, costo_orario_applicato) VALUES (?, ?, ?, ?, ?, ?)",
                                (st.session_state['utente_corrente'], lista_commesse[commessa_scelta], ore, str(data_lavoro), descrizione_attivita, tariffa_istante)
                            )
                            conn.commit()
                            st.success(f"✔️ Registrate {ore} ore. Tariffa storicizzata: € {tariffa_istante:.2f}/h.")
                            st.rerun()
            with col_user_2:
                st.markdown("### 💡 Suggerimento\nSe la commessa non compare, aggiungila nel tab **'Gestione Commesse'**.")
                
        with tab_commesse_user:
            mostra_pannello_commesse(chiave_univoca="user")

        with tab_password_user:
            st.subheader("🔒 Aggiorna la tua Password")
            with st.form("form_cambio_pass_autonomo", clear_on_submit=True):
                nuova_pass_user = st.text_input("Nuova Password", type="password").strip()
                conferma_pass_user = st.text_input("Conferma Nuova Password", type="password").strip()
                if st.form_submit_button("Aggiorna Password"):
                    if nueva_pass_user and nuova_pass_user == conferma_pass_user:
                        cursor.execute("UPDATE anagrafica_utenti SET password = ? WHERE username = ?", (nuova_pass_user, st.session_state['utente_corrente']))
                        conn.commit()
                        st.success("✔️ Password aggiornata!")
                    else:
                        st.error("❌ Errore nelle password.")

    # --- SITO AMMINISTRATORE ---
    elif st.session_state["ruolo"] == "admin":
        tab_inserimento, tab_tariffe, tab_collaboratori, tab_report = st.tabs([
            "📝 Gestione Operativa", "💰 Tariffe Orarie", "👥 Anagrafica Collaboratori", "📊 Report & Spese"
        ])
        
        with tab_inserimento:
            st.subheader("📅 Riepilogo Ore Settimanali Collaboratori")
            oggi = datetime.now().date()
            lunedi = oggi - timedelta(days=oggi.weekday())
            giorni_settimana = [(lunedi + timedelta(days=i)) for i in range(7)]
            nomi_giorni = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]
            date_stringhe = [str(g) for g in giorni_settimana]
            
            query_settimana = f"""
                SELECT collaboratore, data, SUM(ore) as tot_ore 
                FROM ore_lavoro 
                WHERE data BETWEEN '{date_stringhe[0]}' AND '{date_stringhe[-1]}'
                GROUP BY collaboratore, data
            """
            df_sett = pd.read_sql_query(query_settimana, conn)
            
            timesheet_data = []
            for utente in tutti_utenti_attivi:
                riga = {"Collaboratore": utente}
                totale_utente = 0.0
                for g_nome, g_data in zip(nomi_giorni, date_stringhe):
                    if not df_sett.empty:
                        ore_trovate = df_sett[(df_sett['collaboratore'] == utente) & (df_sett['data'] == g_data)]['tot_ore'].values
                        if len(ore_trovate) > 0:
                            riga[g_nome] = f"{ore_trovate[0]} h"
                            totale_utente += ore_trovate[0]
                        else:
                            riga[g_nome] = "-"
                    else:
                        riga[g_nome] = "-"
                riga["Totale"] = f"{totale_utente} h"
                timesheet_data.append(riga)
            st.dataframe(pd.DataFrame(timesheet_data), use_container_width=True, hide_index=True)
            st.write("---")
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("✍️ Inserisci Ore (Come Admin)")
                if df_commesse_attive.empty:
                    st.warning("⚠️ Crea almeno una commessa nel pannello di destra.")
                else:
                    df_commesse_attive['visualizzazione'] = df_commesse_attive.apply(get_mostra_nome, axis=1)
                    lista_commesse = dict(zip(df_commesse_attive['visualizzazione'], df_commesse_attive['id']))
                    
                    collaboratore_selezionato = st.selectbox("Seleziona chi ha lavorato", options=tutti_utenti_attivi)
                    tariffa_proposta = float(df_utenti_db[df_utenti_db['username'] == collaboratore_selezionato]['costo_orario_corrente'].values[0])
                    
                    with st.form("form_ore_admin", clear_on_submit=True):
                        commessa_scelta = st.selectbox("Seleziona la Commessa ", options=lista_commesse.keys())
                        ore = st.number_input("Ore lavorate ", min_value=0.5, max_value=24.0, value=8.0, step=0.5)
                        st.caption(f"ℹ️ Tariffa corrente: **€ {tariffa_proposta:.2f}/h**.")
                        data_lavoro = st.date_input("Data del lavoro ", datetime.now())
                        descrizione_attivita = st.text_area("Descrizione attività svolte ", placeholder="Dettaglio del lavoro...")
                        
                        if st.form_submit_button("Registra Ore (Admin)"):
                            cursor.execute(
                                "INSERT INTO ore_lavoro (collaboratore, commessa_id, ore, data, descrizione, costo_orario_applicato) VALUES (?, ?, ?, ?, ?, ?)",
                                (collaboratore_selezionato, lista_commesse[commessa_scelta], ore, str(data_lavoro), descrizione_attivita, tariffa_proposta)
                            )
                            conn.commit()
                            st.success(f"✔️ Registrate {ore} ore!")
                            st.rerun()
            with col2:
                mostra_pannello_commesse(chiave_univoca="admin")

        with tab_tariffe:
            st.subheader("💰 Imposta Costi Orari")
            for idx, riga_t in df_utenti_db.iterrows():
                ut_nome = riga_t['username']
                ut_costo = riga_t['costo_orario_corrente']
                tc1, tc2, tc3 = st.columns([2, 2, 1])
                tc1.write(f"👤 Utente: **{ut_nome}**")
                nuovo_prezzo = tc2.number_input(f"Tariffa (€/h) per {ut_nome}", min_value=0.0, value=float(ut_costo), step=0.5, key=f"tarif_val_{ut_nome}")
                if tc3.button("💾 Salva", key=f"btn_tar_{ut_nome}"):
                    cursor.execute("UPDATE anagrafica_utenti SET costo_orario_corrente = ? WHERE username = ?", (nuovo_prezzo, ut_nome))
                    conn.commit()
                    st.rerun()

        with tab_collaboratori:
            st.subheader("👥 Gestione Personale e Credenziali")
            col_u1, col_u2 = st.columns([1, 2])
            with col_u1:
                st.write("✨ **Nuovo Collaboratore**")
                with st.form("form_nuovo_utente", clear_on_submit=True):
                    nuovo_user = st.text_input("Nome e Cognome").strip()
                    nuova_pass = st.text_input("Password").strip()
                    costo_init = st.number_input("Costo Orario (€/h)", min_value=0.0, value=25.0)
                    if st.form_submit_button("Crea") and nuovo_user and nuova_pass:
                        try:
                            cursor.execute("INSERT INTO anagrafica_utenti (username, password, costo_orario_corrente, stato) VALUES (?, ?, ?, 'Attivo')", (nuovo_user, nuova_pass, costo_init))
                            conn.commit()
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username esistente.")
            with col_u2:
                st.write("📋 **Lista Credenziali**")
                df_tutti_utenti_gestione = pd.read_sql_query("SELECT username, password, stato FROM anagrafica_utenti WHERE username != 'Amministratore'", conn)
                for idx, riga_u in df_tutti_utenti_gestione.iterrows():
                    u_name, u_pass, u_stato = riga_u['username'], riga_u['password'], riga_u['stato']
                    uc1, uc2, uc3, uc4 = st.columns([2, 2, 1, 1])
                    uc1.write(f"• **{u_name}** ({u_stato})")
                    nuova_p = uc2.text_input(f"Psw {u_name}", value=u_pass, key=f"pass_edit_{u_name}")
                    if nuova_p != u_pass:
                        if uc3.button("💾 Salva", key=f"sv_{u_name}"):
                            cursor.execute("UPDATE anagrafica_utenti SET password = ? WHERE username = ?", (nuova_p, u_name))
                            conn.commit()
                            st.rerun()
                    else:
                        lbl_st = "🚫 Disattiva" if u_stato == "Attivo" else "✅ Attiva"
                        if uc3.button(lbl_st, key=f"st_ut_{u_name}"):
                            nst = "Disattivato" if u_stato == "Attivo" else "Attivo"
                            cursor.execute("UPDATE anagrafica_utenti SET stato = ? WHERE username = ?", (nst, u_name))
                            conn.commit()
                            st.rerun()
                    if uc4.button("🗑️ Elimina", key=f"del_ut_{u_name}"):
                        cursor.execute("DELETE FROM anagrafica_utenti WHERE username = ?", (u_name,))
                        conn.commit()
                        st.rerun()

        with tab_report:
            st.subheader("🔍 Analisi Finanziaria")
            query = """
                SELECT o.id AS ID, o.data AS Data, c.codice AS Codice, c.nome AS Commessa, 
                       o.collaboratore AS Collaboratore, o.ore AS Ore, o.descrizione AS Attività,
                       COALESCE(o.costo_orario_applicato, 0.0) AS Costo_Applicato
                FROM ore_lavoro o
                JOIN commesse c ON o.commessa_id = c.id
                ORDER BY o.data DESC
            """
            df_completo = pd.read_sql_query(query, conn)
            
            if df_completo.empty:
                st.info("Nessun dato registrato.")
            else:
                df_completo['Filtro_Commessa'] = df_completo.apply(lambda r: f"[{r['Codice']}] {r['Commessa']}", axis=1)
                f_col1, f_col2, f_col3 = st.columns(3)
                filtro_commessa = f_col1.multiselect("Filtra per Commessa", options=df_completo['Filtro_Commessa'].unique())
                filtro_utente = f_col2.multiselect("Filtra per Utente", options=df_completo['Collaboratore'].unique())
                date_range = f_col3.date_input("Filtra per Periodo", [])

                df_filtrato = df_completo.copy()
                if filtro_commessa:
                    df_filtrato = df_filtrato[df_filtrato['Filtro_Commessa'].isin(filtro_commessa)]
                if filtro_utente:
                    df_filtrato = df_filtrato[df_filtrato['Collaboratore'].isin(filtro_utente)]
                if len(date_range) == 2:
                    df_filtrato = df_filtrato[(df_filtrato['Data'] >= str(date_range[0])) & (df_filtrato['Data'] <= str(date_range[1]))]

                df_filtrato["Costo Presunto (€)"] = df_filtrato['Ore'] * df_filtrato['Costo_Applicato']
                df_filtrato["Seleziona"] = False
                
                colonne_ordine = ["Data", "Codice", "Commessa", "Collaboratore", "Ore", "Costo Presunto (€)", "Attività", "Seleziona", "ID"]
                df_filtrato = df_filtrato[colonne_ordine]

                risultato_griglia = st.data_editor(
                    df_filtrato,
                    hide_index=True,
                    disabled=["Data", "Codice", "Commessa", "Collaboratore", "Ore", "Costo Presunto (€)", "Attività"],
                    column_config={
                        "ID": None,
                        "Costo Presunto (€)": st.column_config.NumberColumn(format="€ %.2f"),
                        "Seleziona": st.column_config.CheckboxColumn("Seleziona", default=False)
                    },
                    use_container_width=True,
                    key="tabella_cancellazione_multipla"
                )
                
                tot_ore = df_filtrato['Ore'].sum()
                tot_costo = df_filtrato['Costo Presunto (€)'].sum()
                
                m1, m2 = st.columns(2)
                m1.metric("Totale Ore Calcolate", f"{tot_ore} ore")
                m2.metric("Costo Aziendale Complessivo", f"€ {tot_costo:,.2f}")
                
                # Cancellazione Righe Multipla
                ids_da_eliminare = []
                if "tabella_cancellazione_multipla" in st.session_state:
                    cambiamenti = st.session_state["tabella_cancellazione_multipla"].get("edited_rows", {})
                    for riga_idx, modifiche in cambiamenti.items():
                        if modifiche.get("Seleziona") is True:
                            ids_da_eliminare.append(int(df_filtrato.iloc[riga_idx]["ID"]))

                if ids_da_eliminare:
                    if st.button("🔴 Conferma ed Elimina Righe Selezionate"):
                        for id_del in ids_da_eliminare:
                            cursor.execute("DELETE FROM ore_lavoro WHERE id = ?", (id_del,))
                        conn.commit()
                        st.success("Eliminate!")
                        st.rerun()

                st.write("---")
                
                # EXCEL FORMATTATO CON OPENPYXL
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df_export = df_filtrato.drop(columns=['ID', 'Seleziona'])
                    df_export.to_excel(writer, sheet_name='Report Ore e Costi', index=False)
                    worksheet = writer.sheets['Report Ore e Costi']
                    
                    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
                    font_header = Font(name='Segoe UI', size=11, bold=True, color='FFFFFF')
                    fill_header = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid') 
                    font_data = Font(name='Segoe UI', size=10)
                    font_total = Font(name='Segoe UI', size=11, bold=True, color='000000')
                    fill_total = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid') 
                    border_thin = Border(left=Side(style='thin', color='D9D9D9'), right=Side(style='thin', color='D9D9D9'), top=Side(style='thin', color='D9D9D9'), bottom=Side(style='thin', color='D9D9D9'))
                    border_total = Border(top=Side(style='thin', color='000000'), bottom=Side(style='double', color='000000'))
                    
                    for cell in worksheet[1]:
                        cell.font = font_header
                        cell.fill = fill_header
                        cell.alignment = Alignment(horizontal='center', vertical='center')
                    
                    num_rows = len(df_export)
                    for row in worksheet.iter_rows(min_row=2, max_row=num_rows+1):
                        for cell in row:
                            cell.font = font_data
                            cell.border = border_thin
                            if cell.column_letter in ['A', 'B']: 
                                cell.alignment = Alignment(horizontal='center')
                            elif cell.column_letter == 'E': 
                                cell.number_format = '#,##0.0'
                                cell.alignment = Alignment(horizontal='right')
                            elif cell.column_letter == 'F': 
                                cell.number_format = '€ #,##0.00'
                                cell.alignment = Alignment(horizontal='right')
                    
                    total_row_idx = num_rows + 2
                    worksheet.cell(row=total_row_idx, column=1, value="TOTALE GENERALE").font = font_total
                    worksheet.cell(row=total_row_idx, column=5, value=float(tot_ore)).number_format = '#,##0.0'
                    worksheet.cell(row=total_row_idx, column=6, value=float(tot_costo)).number_format = '€ #,##0.00'
                    
                    for col in range(1, 8):
                        cell = worksheet.cell(row=total_row_idx, column=col)
                        cell.font = font_total
                        cell.fill = fill_total
                        cell.border = border_total
                    
                    for col in worksheet.columns:
                        max_len = max(len(str(cell.value or '')) for cell in col)
                        col_letter = col[0].column_letter
                        worksheet.column_dimensions[col_letter].width = max(max_len + 4, 12)
                
                st.download_button(
                    label="📥 Scarica Report Excel Formattato (.xlsx)",
                    data=buffer.getvalue(),
                    file_name=f"report_costi_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )