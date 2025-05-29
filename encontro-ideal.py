import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
from datetime import timedelta
import uuid

def init_firebase():
    if not firebase_admin._apps:
        firebase_config = {
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
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    return firestore.client()

db = init_firebase()

st.title("Encontro Ideal - Disponibilidade Familiar")

# Entrada código da família e usuário (pode ser nome ou id)
family_code = st.text_input("Digite o código da família:")
user_name = st.text_input("Seu nome ou apelido:")

if family_code and user_name:
    # ID do membro: para simplificar, pode ser o nome, mas ideal usar algo único
    user_id = user_name.replace(" ", "_").lower()
    membro_ref = db.collection("familias").document(family_code).collection("membros").document(user_id)

    days = [datetime.date.today() + timedelta(days=i) for i in range(30)]  # 30 dias de margem
    hours = [f"{h}:00" for h in range(8, 21)]  # 8h às 20h

    st.write(f"Marque sua disponibilidade para os próximos 30 dias, {user_name}:")

    disponibilidade = {}

    for day in days:
        slots = st.multiselect(
            f"{day.strftime('%A, %d/%m/%Y')}",
            options=hours,
            key=f"{user_id}_{str(day)}"
        )
        disponibilidade[str(day)] = slots

    if st.button("Salvar minha disponibilidade"):
        membro_ref.set({"disponibilidade": disponibilidade})
        st.success("Disponibilidade salva com sucesso!")

    # Agora vamos calcular a disponibilidade geral da família
    st.write("---")
    st.write("Análise de disponibilidade da família:")

    membros = db.collection("familias").document(family_code).collection("membros").stream()

    # Dicionário para contar quantos membros estão disponíveis por dia e hora
    disponibilidade_geral = {}

    membros_list = list(membros)
    total_membros = len(membros_list)
    if total_membros == 0:
        st.info("Nenhum membro da família registrou disponibilidade ainda.")
    else:
        for membro in membros_list:
            data = membro.to_dict()
            disp = data.get("disponibilidade", {})
            for dia, horarios in disp.items():
                if dia not in disponibilidade_geral:
                    disponibilidade_geral[dia] = {}
                for h in horarios:
                    disponibilidade_geral[dia][h] = disponibilidade_geral[dia].get(h, 0) + 1

        # Agora achar os horários com 100% dos membros disponíveis
        horarios_completos = []
        for dia, horarios in disponibilidade_geral.items():
            for h, contagem in horarios.items():
                if contagem == total_membros:
                    horarios_completos.append((dia, h))

        if horarios_completos:
            st.success(f"Horários que todos podem comparecer ({total_membros} membros):")
            df = pd.DataFrame(horarios_completos, columns=["Data", "Hora"])
            df["Data"] = pd.to_datetime(df["Data"]).dt.strftime("%A, %d/%m/%Y")
            st.dataframe(df)
        else:
            st.warning("Não há nenhum horário em que todos possam comparecer simultaneamente nos próximos 30 dias.")
else:
    st.info("Digite o código da família e seu nome para começar.")
