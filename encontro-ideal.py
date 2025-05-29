import streamlit as st
import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import pandas as pd

# Inicializar Firebase com credenciais do Streamlit Secrets
firebase_cred_dict = json.loads(st.secrets["FIREBASE_CREDENTIALS"])
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

st.set_page_config(page_title="Encontro em Família", layout="centered")
st.title("☕ Agenda do Encontro em Família")

with st.form("formulario"):
    nome = st.text_input("Seu nome")
    codigo_familia = st.text_input("Código da família")

    st.markdown("**Escolha os dias e horários que você está disponível nesta semana:**")
    dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
    horarios = ["08h", "10h", "14h", "16h", "18h", "20h"]

    disponibilidade = {}
    for dia in dias:
        colunas = st.columns(len(horarios))
        disponibilidade[dia] = []
        for i, hora in enumerate(horarios):
            checked = colunas[i].checkbox(f"{hora}", key=f"{dia}-{hora}")
            if checked:
                disponibilidade[dia].append(hora)

    submitted = st.form_submit_button("Salvar minha disponibilidade")

    if submitted:
        if not nome or not codigo_familia:
            st.warning("Por favor, preencha seu nome e o código da família.")
        else:
            doc_ref = db.collection("familias").document(codigo_familia).collection("respostas").document(nome)
            doc_ref.set({
                "nome": nome,
                "codigo_familia": codigo_familia,
                "disponibilidade": disponibilidade,
                "timestamp": datetime.now()
            })
            st.success("Disponibilidade salva com sucesso! 🎉")

st.markdown("---")
st.header("🔍 Melhor horário para a família")
codigo_busca = st.text_input("Digite o código da família para ver o melhor horário")

if st.button("Calcular melhor horário"):
    if not codigo_busca:
        st.warning("Digite um código de família.")
    else:
        respostas = db.collection("familias").document(codigo_busca).collection("respostas").stream()

        total = {}
        for doc in respostas:
            dados = doc.to_dict()
            disponibilidade = dados.get("disponibilidade", {})
            for dia, horas in disponibilidade.items():
                for hora in horas:
                    chave = f"{dia}-{hora}"
                    total[chave] = total.get(chave, 0) + 1

        if total:
            resultados = pd.DataFrame([
                {"Dia": k.split("-")[0], "Hora": k.split("-")[1], "Votos": v} for k, v in total.items()
            ])
            resultados = resultados.sort_values(by="Votos", ascending=False)

            st.subheader("Resultados por popularidade:")
            st.dataframe(resultados.reset_index(drop=True))

            melhor = resultados.iloc[0]
            st.success(f"🎯 Melhor horário para todos: **{melhor['Dia']} às {melhor['Hora']}** com {melhor['Votos']} voto(s)!")
        else:
            st.info("Nenhuma resposta encontrada para esse código ainda.")
