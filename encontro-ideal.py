import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
import datetime
from datetime import timedelta, time, date

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

def intervalos_sobrepostos(intervalos1, intervalos2):
    sobrepostos = []
    for s1, e1 in intervalos1:
        s1_dt = datetime.datetime.strptime(s1, "%H:%M").time()
        e1_dt = datetime.datetime.strptime(e1, "%H:%M").time()
        for s2, e2 in intervalos2:
            s2_dt = datetime.datetime.strptime(s2, "%H:%M").time()
            e2_dt = datetime.datetime.strptime(e2, "%H:%M").time()
            latest_start = max(s1_dt, s2_dt)
            earliest_end = min(e1_dt, e2_dt)
            if latest_start < earliest_end:
                sobrepostos.append((
                    latest_start.strftime("%H:%M"),
                    earliest_end.strftime("%H:%M")
                ))
    return sobrepostos

def input_intervalos_por_dia(user_id, day):
    st.write(f"Disponibilidade para {day.strftime('%A, %d/%m/%Y')}:")
    intervalos = []
    idx = 0
    while True:
        start_key = f"{user_id}_{day}_start_{idx}"
        end_key = f"{user_id}_{day}_end_{idx}"

        start = st.time_input(f"Início do intervalo {idx + 1}", key=start_key, value=time(8, 0))
        end = st.time_input(f"Fim do intervalo {idx + 1}", key=end_key, value=time(9, 0))

        if end <= start:
            st.warning("O horário final deve ser depois do horário inicial.")
            break

        intervalos.append((start.strftime("%H:%M"), end.strftime("%H:%M")))

        add_more = st.checkbox("Adicionar mais um intervalo", key=f"add_more_{user_id}_{day}_{idx}")
        if not add_more:
            break
        idx += 1
    return intervalos

# -- Interface principal --

st.title("Encontro Ideal - Disponibilidade Familiar")

menu = st.sidebar.selectbox("Menu", ["Entrar na família", "Criar família"])

if menu == "Criar família":
    st.subheader("Criar uma nova família")
    nome_familia = st.text_input("Nome da família (Ex: Família Souza, Amigos, Casal João e Maria)")
    num_membros = st.number_input("Número máximo de pessoas que terão acesso", min_value=1, max_value=50, value=3)
    if st.button("Criar família"):
        import uuid
        codigo = str(uuid.uuid4()).split("-")[0][:6].upper()
        data_expiracao = datetime.datetime.utcnow() + timedelta(days=30)
        db.collection("familias").document(codigo).set({
            "nome": nome_familia,
            "num_membros": num_membros,
            "data_criacao": datetime.datetime.utcnow(),
            "data_expiracao": data_expiracao,
        })
        st.success(f"Família criada com sucesso! Código da família: **{codigo}**. Salve esse código para compartilhar com seus membros.")

elif menu == "Entrar na família":
    family_code = st.text_input("Digite o código da família:")
    user_name = st.text_input("Seu nome ou apelido:")

    if family_code and user_name:
        fam_doc = db.collection("familias").document(family_code).get()
        if not fam_doc.exists:
            st.error("Código da família não encontrado.")
        else:
            familia = fam_doc.to_dict()
            data_exp = familia.get("data_expiracao")

            if data_exp is None:
                st.error("Data de expiração inválida.")
                st.stop()

            # Converter para datetime.datetime, se necessário
            if hasattr(data_exp, "to_datetime"):
                data_exp = data_exp.to_datetime()
            elif isinstance(data_exp, datetime.datetime):
                pass  # já é datetime
            elif isinstance(data_exp, str):
                try:
                    data_exp = datetime.datetime.fromisoformat(data_exp)
                except Exception:
                    st.error("Formato da data de expiração não suportado (string).")
                    st.stop()
            else:
                st.error(f"Formato da data de expiração não suportado: {type(data_exp)}")
                st.stop()

            if not isinstance(data_exp, datetime.datetime):
                st.error(f"Data de expiração não é datetime após conversão, é {type(data_exp)}")
                st.stop()

            if data_exp < datetime.datetime.utcnow():
                st.error("Essa família expirou. Crie uma nova família.")
            else:
                user_id = user_name.replace(" ", "_").lower()
                membro_ref = db.collection("familias").document(family_code).collection("membros").document(user_id)

                # Verificar limite de membros
                membros_cadastrados = list(db.collection("familias").document(family_code).collection("membros").stream())
                limite = familia.get("num_membros", 1)

                if user_id not in [m.id for m in membros_cadastrados] and len(membros_cadastrados) >= limite:
                    st.error("Limite de membros cadastrados atingido para essa família.")
                else:
                    tab1, tab2 = st.tabs(["Minha disponibilidade", "Membros da família"])

                    with tab1:
                        days = [date.today() + timedelta(days=i) for i in range(30)]
                        st.write(f"Marque sua disponibilidade para os próximos 30 dias, {user_name}:")
                        disponibilidade = {}
                        for day in days:
                            intervalos = input_intervalos_por_dia(user_id, day)
                            disponibilidade[str(day)] = intervalos

                        if st.button("Salvar minha disponibilidade"):
                            membro_ref.set({
                                "nome": user_name,
                                "disponibilidade": disponibilidade
                            }, merge=True)
                            st.success("Disponibilidade salva com sucesso!")

                        st.write("---")
                        st.write(f"Análise de disponibilidade da família '{familia.get('nome', family_code)}':")

                        membros = db.collection("familias").document(family_code).collection("membros").stream()
                        membros_list = list(membros)
                        total_membros = len(membros_list)

                        if total_membros == 0:
                            st.info("Nenhum membro da família registrou disponibilidade ainda.")
                        else:
                            disponibilidade_geral = {}
                            for membro in membros_list:
                                dados = membro.to_dict()
                                disp = dados.get("disponibilidade", {})
                                for dia, intervalos in disp.items():
                                    if dia not in disponibilidade_geral:
                                        disponibilidade_geral[dia] = intervalos
                                    else:
                                        disponibilidade_geral[dia] = intervalos_sobrepostos(disponibilidade_geral[dia], intervalos)

                            horarios_comuns = []
                            for dia, intervalos in disponibilidade_geral.items():
                                for intervalo in intervalos:
                                    horarios_comuns.append((dia, f"{intervalo[0]} até {intervalo[1]}"))

                            if horarios_comuns:
                                st.success(f"Horários que todos podem comparecer ({total_membros} membros):")
                                df = pd.DataFrame(horarios_comuns, columns=["Data", "Intervalo"])
                                df["Data"] = pd.to_datetime(df["Data"]).dt.strftime("%A, %d/%m/%Y")
                                st.dataframe(df)
                            else:
                                st.warning("Não há nenhum intervalo em que todos possam comparecer simultaneamente nos próximos 30 dias.")

                    with tab2:
                        st.write(f"Membros cadastrados na família '{familia.get('nome', family_code)}':")
                        membros = db.collection("familias").document(family_code).collection("membros").stream()
                        membros_list = list(membros)
                        if not membros_list:
                            st.info("Nenhum membro cadastrado ainda.")
                        else:
                            for membro in membros_list:
                                dados = membro.to_dict()
                                st.markdown(f"**{dados.get('nome', membro.id)}**")
                                disp = dados.get("disponibilidade", {})
                                if disp:
                                    st.write("Disponibilidade registrada:")
                                    for dia, intervalos in disp.items():
                                        if intervalos:
                                            intervalos_str = ", ".join([f"{i[0]}–{i[1]}" for i in intervalos])
                                            st.write(f"- {dia}: {intervalos_str}")
                                else:
                                    st.write("Sem disponibilidade registrada.")
    else:
        st.info("Digite o código da família e seu nome para começar.")
