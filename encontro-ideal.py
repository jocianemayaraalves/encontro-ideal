import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
from datetime import timedelta
import uuid

# Inicializar Firebase
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

# Limpar famílias expiradas
def limpar_familias_expiradas():
    now = datetime.datetime.utcnow()
    familias = db.collection("familias").stream()
    for fam in familias:
        data_exp = fam.get("data_expiracao")
        # Converte se for Timestamp do Firestore
        if hasattr(data_exp, "timestamp"):
            data_exp = datetime.datetime.fromtimestamp(data_exp.timestamp())
        if isinstance(data_exp, datetime.datetime) and data_exp < now:
            membros = db.collection("familias").document(fam.id).collection("membros").stream()
            for membro in membros:
                membro.reference.delete()
            fam.reference.delete()
            st.write(f"Família '{fam.id}' expirada e removida.")

limpar_familias_expiradas()

# Interface principal
st.title("Encontro Ideal - Disponibilidade Familiar")
menu = st.sidebar.selectbox("Menu", ["Entrar na família", "Criar família"])

# Criar nova família
if menu == "Criar família":
    st.subheader("Criar uma nova família")
    nome_familia = st.text_input("Nome da família (Ex: Família Souza, Amigos, Casal João e Maria)")
    num_membros = st.number_input("Número máximo de pessoas que terão acesso", min_value=1, max_value=50, value=3)
    if st.button("Criar família"):
        codigo = str(uuid.uuid4()).split("-")[0][:6].upper()
        data_expiracao = datetime.datetime.utcnow() + timedelta(days=30)
        db.collection("familias").document(codigo).set({
            "nome": nome_familia,
            "num_membros": num_membros,
            "data_criacao": datetime.datetime.utcnow(),
            "data_expiracao": data_expiracao,
        })
        st.success(f"Família criada com sucesso! Código da família: **{codigo}**. Salve esse código para compartilhar com seus membros.")

# Entrar em uma família
elif menu == "Entrar na família":
    family_code = st.text_input("Digite o código da família:")
    user_name = st.text_input("Seu nome ou apelido:")

    if family_code and user_name:
        try:
            fam_doc = db.collection("familias").document(family_code).get()
            if not fam_doc.exists:
                st.error("Código da família não encontrado.")
            else:
                familia = fam_doc.to_dict()
                data_exp = familia.get("data_expiracao")

                # Converter data se necessário
                if hasattr(data_exp, "timestamp"):
                    data_exp = datetime.datetime.fromtimestamp(data_exp.timestamp())

                if isinstance(data_exp, datetime.datetime) and data_exp < datetime.datetime.utcnow():
                    st.error("Essa família expirou. Crie uma nova família.")
                else:
                    user_id = user_name.replace(" ", "_").lower()
                    membro_ref = db.collection("familias").document(family_code).collection("membros").document(user_id)

                    membros_cadastrados = list(db.collection("familias").document(family_code).collection("membros").stream())
                    limite = familia.get("num_membros", 1)

                    if user_id not in [m.id for m in membros_cadastrados] and len(membros_cadastrados) >= limite:
                        st.error("Limite de membros cadastrados atingido para essa família.")
                    else:
                        days = [datetime.date.today() + timedelta(days=i) for i in range(30)]
                        hours = [f"{h}:00" for h in range(8, 21)]

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

                        st.write("---")
                        st.write(f"Análise de disponibilidade da família '{familia.get('nome', family_code)}':")

                        membros = db.collection("familias").document(family_code).collection("membros").stream()
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
        except Exception as e:
            st.error(f"Erro ao processar os dados: {e}")
    else:
        st.info("Digite o código da família e seu nome para começar.")
