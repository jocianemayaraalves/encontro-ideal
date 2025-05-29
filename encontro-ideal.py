import streamlit as st

st.set_page_config(page_title="Encontro Ideal", page_icon="🤝", layout="centered")
st.title("🤝 Encontro Ideal - Ache o melhor horário em família!")
st.markdown("Marque os dias e horários que você está disponível:")

dias_semana = ["segunda", "terça", "quarta", "quinta", "sexta", "sábado", "domingo"]
horarios_dia = ["10h", "14h", "16h", "18h", "19h", "20h"]

# Inicializa estado
if "disponibilidade" not in st.session_state:
    st.session_state.disponibilidade = {}

# Nome da pessoa
nome = st.text_input("👤 Seu nome:")

# Grade de horários
st.markdown("### 📅 Selecione seus horários disponíveis:")

marcados = []

for dia in dias_semana:
    st.markdown(f"**{dia.capitalize()}**")
    cols = st.columns(len(horarios_dia))
    for i, hora in enumerate(horarios_dia):
        checked = cols[i].checkbox(hora, key=f"{nome}_{dia}_{hora}")
        if checked:
            marcados.append(f"{dia}-{hora}")

# Botão para salvar
if st.button("💾 Salvar minha disponibilidade"):
    if nome.strip() == "":
        st.error("Por favor, insira seu nome antes de salvar.")
    elif not marcados:
        st.warning("Você não marcou nenhum horário!")
    else:
        st.session_state.disponibilidade[nome.strip()] = set(marcados)
        st.success("Disponibilidade salva com sucesso! ✅")

# Exibe tudo que foi salvo
if st.session_state.disponibilidade:
    st.markdown("---")
    st.markdown("### 👥 Disponibilidades cadastradas:")
    for pessoa, horarios in st.session_state.disponibilidade.items():
        st.write(f"**{pessoa}**: {', '.join(sorted(horarios))}")

    # Verifica horários em comum
    valores = list(st.session_state.disponibilidade.values())
    comuns = set.intersection(*valores) if valores else set()

    st.markdown("### 🔍 Horários em comum entre todos:")
    if comuns:
        for horario in sorted(comuns):
            st.markdown(f"- ✅ **{horario.capitalize()}**")
    else:
        st.warning("⚠️ Ainda não há horário em comum entre todos!")

# Resetar dados
if st.button("🔄 Limpar tudo"):
    st.session_state.disponibilidade = {}
    st.experimental_rerun()
