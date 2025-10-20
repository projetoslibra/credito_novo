import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# ========== CONFIGURAÇÃO DO BANCO DE DADOS ==========
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"]
}

# ========== PERMISSÕES POR USUÁRIO ==========
USERS = {
    "Breno": {"senha": "Breno13", "tipo": "comercial", "agente": "Breno"},
    "analista": {"senha": "1234", "tipo": "analista", "agente": None},
    # Adicione mais usuários aqui se quiser...
}

# ========== CONECTAR BANCO ==========
def conectar_db():
    return psycopg2.connect(**DB_CONFIG)

# ========== LOGIN ==========
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

# ========== CARREGAR DADOS ==========
def carregar_dados():
    conn = conectar_db()
    df = pd.read_sql("SELECT * FROM analise_credito ORDER BY id", conn)
    conn.close()
    return df

# ========== SALVAR DADOS ==========
def salvar_dados(df):
    conn = conectar_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM analise_credito")
    for _, row in df.iterrows():
        cur.execute("""
            INSERT INTO analise_credito (
                entrada, empresa, agente, situacao, limite,
                comentario_interno, saida_credito, pendencias,
                envio_das, emissao_contrato, assinatura,
                homologacao, apto_a_operar, email_informando
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, tuple(row.get(col, None) for col in [
            'entrada', 'empresa', 'agente', 'situacao', 'limite',
            'comentario_interno', 'saida_credito', 'pendencias',
            'envio_das', 'emissao_contrato', 'assinatura',
            'homologacao', 'apto_a_operar', 'email_informando'
        ]))
    conn.commit()
    conn.close()

# ========== APP PRINCIPAL ==========
def app():
    st.title("📋 Análise de Crédito")
    df = carregar_dados()

    tipo = st.session_state['tipo']
    agente = st.session_state['agente']

    if tipo == "comercial":
        st.subheader(f"🔍 Visualização de dados - Agente: {agente}")
        dados_agente = df[df['agente'] == agente]
        editar = st.data_editor(
            dados_agente[['entrada', 'empresa', 'agente']],
            num_rows="dynamic",
            use_container_width=True,
            key="editor_comercial"
        )

        if st.button("💾 Salvar alterações"):
            for idx in editar.index:
                row = editar.loc[idx]
                mask = (df['empresa'] == row['empresa']) & (df['agente'] == agente)
                if mask.any():
                    for col in ['entrada', 'empresa', 'agente']:
                        df.loc[mask, col] = row[col]
                else:
                    nova_linha = {col: None for col in df.columns if col != 'id'}
                    nova_linha.update(row.to_dict())
                    df = pd.concat([df, pd.DataFrame([nova_linha])], ignore_index=True)
            salvar_dados(df)
            st.success("Alterado com sucesso!")

    elif tipo == "analista":
        st.subheader("🧠 Análise completa")
        editar = st.data_editor(
            df,
            num_rows="dynamic",
            use_container_width=True,
            key="editor_analista"
        )
        if st.button("💾 Salvar todas as alterações"):
            salvar_dados(editar)
            st.success("Salvo com sucesso!")

# ========== MAIN ==========
if 'usuario' not in st.session_state:
    login()
else:
    app()
