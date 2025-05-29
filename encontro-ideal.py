import streamlit as st
import pandas as pd
import datetime
import firebase_admin
from firebase_admin import credentials, firestore
import hashlib

# Inicializa Firebase com segredo do Streamlit
if not firebase_admin._apps:
    cred_dict = {
        "type": st.secrets["firebase"]["type"],
        "project_id": st.secrets["firebase"]["project_id"],
        "private_key_id": st.secrets["firebase"]["private_key_id"],
        "private_key": st.secrets["firebase"]["private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase"]["client_email"],
        "client_id": st.secrets["firebase"]["client_id"],
        "auth_uri": st.secrets["firebase"]["auth_uri"],
        "token_uri": st.secrets["firebase"]["token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"],
    }
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Encontro Ideal", page_icon="📅", layout="wide")

st.title("📅 Encontro Ideal - Organize os encontros da família")

# ---------- Funções ------------

def hash_family_code(family_code):
    return hashlib.sha256(family_code.strip().lower().encode()).hexdigest()

def get_family_data(family_hash):
    doc = db.collection("families").document(family_hash).get()
    if doc.exists:
        return doc.to_dict()
    return None

def save_availability(family_hash, user_name, availability_df):
    # Salva disponibilidade do usuário na subcoleção "members" da família
    member_ref = db.collection("families").document(family_hash).collection("members").document(user_name)
    data = availability_df.to_dict(orient="records")
    member_ref.set({"availability": data})

def get_all_availabilities(family_hash):
    members_ref = db.collection("families").document(family_hash).collection("members").stream()
    all_data = {}
    for m in members_ref:
        m_data = m.to_dict()
        if "availability" in m_data:
            df = pd.DataFrame(m_data["availability"])
            all_data[m.id] = df
    return all_data

def generate_date_hour_table(start_date, weeks=4):
    # Gera DataFrame com colunas: Date, Day, and Hours as columns
    dates = []
    for i in range(weeks * 7):
        day = start_date + datetime.timedelta(days=i)
        dates.append(day)
    hours = [f"{h}:00" for h in range(8, 21)]  # 8h às 20h

    # Criar MultiIndex para DataFrame: date+hour
    index = pd.MultiIndex.from_product([dates, hours], names=["Date", "Hour"])

    # DataFrame com coluna "Available" default False
    df = pd.DataFrame(False, index=index, columns=["Available"])
    return df

def display_availability_table(df):
    # Streamlit checkbox table simulada
    st.write("Marque seus horários disponíveis:")
    # Para facilitar UI, vamos mostrar por dia e hora com checkboxes
    selected = []
    for date in sorted(df.index.get_level_values(0).unique()):
        with st.expander(date.strftime("%a, %d %b %Y")):
            cols = st.columns(7)
            hours = df.loc[date].index.get_level_values(0)
            for idx, hour in enumerate(hours):
                col = cols[idx % 7]
                checked = st.checkbox(hour, key=f"{date}_{hour}")
                if checked:
                    selected.append((date, hour))
    return selected

def availability_to_df(selected):
    # Converte lista (date, hour) para DataFrame multiindex
    tuples = [(d, h) for d, h in selected]
    df = pd.DataFrame(index=pd.MultiIndex.from_tuples(tuples, names=["Date", "Hour"]))
    df["Available"] = True
    return df

def calculate_best_slot(all_availabilities):
    # all_availabilities: dict de {user_name: DataFrame(availability)}
    # Faz a união para encontrar os horários com maior disponibilidade comum
    if not all_availabilities:
        return None, None

    # Começa com o primeiro DataFrame preenchendo zeros
    combined = None
    for df in all_availabilities.values():
        # Transforma True/False em 1/0
        bin_df = df["Available"].astype(int)
        if combined is None:
            combined = bin_df
        else:
            combined = combined.add(bin_df, fill_value=0)

    # Achar o(s) índice(s) com o valor máximo (mais gente disponível)
    max_avail = combined.max()
    best_slots = combined[combined == max_avail].index.tolist()

    # Preferir o mais próximo do presente
    best_slots.sort()
    best_slot = best_slots[0]

    return best_slot, max_avail

# ---------- UI -----------

st.sidebar.header("Identificação da Família")
family_code = st.sidebar.text_input("Digite o código da família (ex: Silva123)")

if family_code:
    family_hash = hash_family_code(family_code)
    st.sidebar.success(f"Código da família registrado.")

    st.header("Informe seu nome")
    user_name = st.text_input("Nome para registro")

    if user_name:
        # Pega ou cria tabela para o mês
        start_date = datetime.date.today()
        availability_df = generate_date_hour_table(start_date)

        # Recuperar dados do usuário para preencher checkboxes
        family_data = get_family_data(family_hash)
        user_avail_df = None
        if family_data:
            members = db.collection("families").document(family_hash).collection("members")
            member_doc = members.document(user_name).get()
            if member_doc.exists:
                user_avail_df = pd.DataFrame(member_doc.to_dict().get("availability", []))
                if not user_avail_df.empty:
                    user_avail_df.set_index(["Date", "Hour"], inplace=True)

        # UI para marcar disponibilidade
        selected_slots = display_availability_table(availability_df)

        if st.button("Salvar disponibilidade"):
            if not selected_slots:
                st.warning("Marque pelo menos um horário disponível.")
            else:
                user_df = availability_to_df(selected_slots)
                save_availability(family_hash, user_name, user_df)
                st.success("Disponibilidade salva com sucesso!")

        # Mostrar melhor horário para toda família
        st.header("Melhor horário para a família toda")

        all_avail = get_all_availabilities(family_hash)
        best_slot, count = calculate_best_slot(all_avail)

        if best_slot:
            st.info(
                f"Melhor horário é {best_slot[0].strftime('%A, %d %b %Y')} às {best_slot[1]} "
                f"com {int(count)} pessoa(s) disponível(is)."
            )
        else:
            st.info("Ainda não há dados suficientes para calcular o melhor horário.")

else:
    st.info("Por favor, digite o código da família para começar.")
