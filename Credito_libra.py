import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ====== CONFIGURAÇÃO ======
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = '18y83fQmWjBvjXaktOJ2PV3OCNtKIouXfF4zKWy_uXMQ'
ABA_ANALISE = 'ANALISE_RETORNO'
ABA_PENDENCIAS = 'DIM_PENDENCIAS'

# ====== PERMISSÕES POR USUÁRIO ======
USERS = {
    "Breno": {"senha": "Breno13", "tipo": "comercial", "agente": "Breno"},
    "analista": {"senha": "1234", "tipo": "analista", "agente": None},
    # Adicione mais usuários aqui...
}

# ====== AUTENTICAÇÃO COM GOOGLE SHEETS ======
def conectar_planilha():
    import json
    creds_dict = json.loads(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID)
    return sheet
# ====== LOGIN ======
def login():
    with st.sidebar:
        st.markdown("## Login")
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if user in USERS and USERS[user]["senha"] == password:
                st.session_state['usuario'] = user
                st.session_state['tipo'] = USERS[user]['tipo']
                st.session_state['agente'] = USERS[user]['agente']
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# ====== CARREGAR DADOS ======
def carregar_dados(sheet):
    aba = sheet.worksheet(ABA_ANALISE)
    dados = pd.DataFrame(aba.get_all_records())
    return dados, aba

# ====== SALVAR DADOS ======
def salvar_dados(aba, df):
    aba.clear()
    aba.update([df.columns.values.tolist()] + df.values.tolist())

# ====== APP PRINCIPAL ======
def app():
    st.title("📋 Análise de Crédito")
    sheet = conectar_planilha()
    dados, aba = carregar_dados(sheet)

    tipo = st.session_state['tipo']
    agente = st.session_state['agente']

    if tipo == "comercial":
        st.subheader(f"🔍 Visualização de dados - Agente: {agente}")
        dados_agente = dados[dados['agente'] == agente]
        editar = st.experimental_data_editor(
            dados_agente[['data', 'empresa', 'agente']],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_comercial"
        )

        if st.button("Salvar alterações"):
            # Atualizar somente as linhas do agente
            for idx in editar.index:
                mask = (dados['empresa'] == editar.at[idx, 'empresa']) & (dados['agente'] == agente)
                if not mask.any():
                    # Nova linha
                    nova_linha = {col: "" for col in dados.columns}
                    nova_linha.update(editar.loc[idx].to_dict())
                    dados = dados.append(nova_linha, ignore_index=True)
                else:
                    for col in ['data', 'empresa', 'agente']:
                        dados.loc[mask, col] = editar.at[idx, col]
            salvar_dados(aba, dados)
            st.success("Alterado com sucesso!")

    elif tipo == "analista":
        st.subheader("🧠 Análise completa")
        editar = st.experimental_data_editor(
            dados,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_analista"
        )
        if st.button("Salvar todas as alterações"):
            salvar_dados(aba, editar)
            st.success("Salvo com sucesso!")

        # PENDÊNCIAS
        st.markdown("---")
        st.subheader("📎 Documentos Pendentes")
        aba_pend = sheet.worksheet(ABA_PENDENCIAS)
        pend = pd.DataFrame(aba_pend.get_all_records())
        st.dataframe(pend, use_container_width=True)

# ====== MAIN ======
if 'usuario' not in st.session_state:
    login()
else:
    app()
