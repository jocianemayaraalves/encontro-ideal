import streamlit as st

st.set_page_config(page_title="Encontro Ideal", page_icon="🤝", layout="centered")

st.title("🤝 Encontro Ideal - Ache o melhor horário em família!")

st.markdown("Cadastrem os dias e horários em que **cada pessoa está disponível**.")
st.markdown("Formato sugerido: `segunda-19h`, `domingo-10h`")

# Inicializa o estado da sessão
if "disponibilidade" not in st.session_state:
    st.session_state.disponibilidade = {}

# Formulário para entrada de dados
with st.form("formulario_disponibilidade"):
    nome = st.text_input("👤 Nome")
    horarios = st.text_area("📅 Dias e horários disponíveis (um por linha)", height=150)
    enviado = st.form_submit_button("Salvar Disponibilidade")

    if enviado:
        if nome and horarios:
            dias_horas = set(h.strip().lower() for h in horarios.splitlines() if h.strip())
            st.session_state.disponibilidade[nome] = dias_horas
            st.success(f"Disponibilidade de {nome} salva com sucesso!")
        else:
            st.error("Por favor, preencha o nome e os horários.")

# Exibe dados inseridos
if st.session_state.disponibilidade:
    st.markdown("### 👥 Disponibilidades cadastradas:")
    for pessoa, horarios in st.session_state.disponibilidade.items():
        st.write(f"**{pessoa}**: {', '.join(sorted(horarios))}")

    # Verifica horários em comum
    st.markdown("### 🔍 Horários em comum:")
    valores = list(st.session_state.disponibilidade.values())
    comuns = set.intersection(*valores) if valores else set()

    if comuns:
        st.success("Todo mundo pode nos seguintes horários:")
        for horario in sorted(comuns):
            st.markdown(f"- ✅ **{horario.capitalize()}**")
    else:
        st.warning("Infelizmente, ainda **não há horário em comum** entre todos.")
else:
    st.info("Adicione pelo menos uma pessoa para começar!")

# Botão de reinício
if st.button("🔄 Limpar tudo e começar de novo"):
    st.session_state.disponibilidade = {}
    st.experimental_rerun()
