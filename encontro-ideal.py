import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import random
import string
import pyperclip

# Inicializar Firebase Admin
if not firebase_admin._apps:
    cred = credentials.Certificate(st.secrets["FIREBASE_CREDENTIALS"])
    firebase_admin.initialize_app(cred)
db = firestore.client()

def gerar_codigo_familia(tamanho=6):
    return 'FAM' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=tamanho))

st.set_page_config(page_title="Encontro Ideal da Família", layout="wide")

st.title("Encontro Ideal da Família 🏡")

# --- Gerar código da família ---
st.header("1. Criar código da família")

nome_familia = st.text_input("Digite o nome da sua família (ex: Família Silva)")

if st.button("Gerar código de família"):
    if nome_familia.strip() == "":
        st.error("Por favor, informe o nome da família.")
    else:
        # Gera código e verifica duplicidade
        while True:
            novo_codigo = gerar_codigo_familia()
            doc = db.collection("familias").document(novo_codigo).get()
            if not doc.exists:
                break
        # Salva no Firebase
        db.collection("familias").document(novo_codigo).set({"nome_familia": nome_familia})
        st.success(f"Código gerado para **{nome_familia}**: **{novo_codigo}**")
        st.info("Compartilhe esse código com sua família para que todos possam registrar a disponibilidade.")
        # Botão para copiar código
        if st.button("Copiar código para a área de transferência"):
            try:
                import pyperclip
                pyperclip.copy(novo_codigo)
                st.success("Código copiado! Agora é só colar e compartilhar.")
            except Exception:
                st.warning("Não foi possível copiar automaticamente. Por favor, copie manualmente o código.")

st.markdown("---")

# --- Mostrar códigos de famílias já criados ---
st.header("2. Códigos de famílias já criados")

familias_docs = db.collection("familias").stream()
familias = [(doc.id, doc.to_dict().get("nome_familia", "")) for doc in familias_docs]

if familias:
    df_familias = pd.DataFrame(familias, columns=["Código da Família", "Nome da Família"])
    st.table(df_familias)
else:
    st.write("Nenhum código de família cadastrado ainda.")

st.markdown("---")

# --- Registrar disponibilidade ---
st.header("3. Registrar disponibilidade")

codigo_familia = st.text_input("Digite o código da família")
nome = st.text_input("Seu nome")

dias_semana = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
horarios = ["Manhã", "Tarde", "Noite"]

if codigo_familia and nome:
    st.write("Selecione os dias e horários que você está disponível:")

    disponibilidade = {}
    for dia in dias_semana:
        disponibilidade[dia] = []
        cols = st.columns(len(horarios))
        for i, horario in enumerate(horarios):
            with cols[i]:
                check = st.checkbox(f"{dia} - {horario}", key=f"{dia}_{horario}_{nome}")
                if check:
                    disponibilidade[dia].append(horario)

    if st.button("Salvar disponibilidade"):
        # Verificar se código de família existe
        doc = db.collection("familias").document(codigo_familia).get()
        if not doc.exists:
            st.error("Código de família inválido. Por favor, verifique e tente novamente.")
        else:
            data = {
                "nome": nome,
                "disponibilidade": disponibilidade
            }
            db.collection("familias").document(codigo_familia).collection("respostas").document(nome).set(data)
            st.success("Disponibilidade salva com sucesso!")

    # Mostrar melhor dia e horário para a família (se disponível)
    respostas = db.collection("familias").document(codigo_familia).collection("respostas").stream()
    todos = [r.to_dict() for r in respostas]

    if todos:
        # Contar a disponibilidade geral
        contagem = {dia: {h: 0 for h in horarios} for dia in dias_semana}
        for r in todos:
            disp = r.get("disponibilidade", {})
            for dia in disp:
                for h in disp[dia]:
                    contagem[dia][h] += 1

        # Encontrar o máximo
        max_val = 0
        melhor_dia = None
        melhor_horario = None
        for dia in contagem:
            for h in contagem[dia]:
                if contagem[dia][h] > max_val:
                    max_val = contagem[dia][h]
                    melhor_dia = dia
                    melhor_horario = h

        st.markdown("---")
        st.subheader("Melhor dia e horário para o encontro:")
        st.success(f"**{melhor_dia} - {melhor_horario}** (Disponibilidade de {max_val} pessoa(s))")

else:
    st.info("Por favor, informe o código da família e seu nome para continuar.")
