import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# ========== CONFIGURAÇÕES ==========
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"]
}

# ====== PERMISSÕES POR USUÁRIO ======
USERS = {
    "Breno": {"senha": "Breno13", "tipo": "comercial", "agente": "Breno"},
    "analista": {"senha": "1234", "tipo": "analista", "agente": None},
}

# ====== FUNÇÃO DE CONEXÃO COM O BANCO ======
def get_connection():
    return psycopg2.connect(**DB_CONFIG)

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

# ====== INSERIR NOVA EMPRESA ======
def inserir_empresa(empresa, agente):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO analise_credito (empresa, agente, entrada)
        VALUES (%s, %s, NOW())
        ON CONFLICT (empresa) DO NOTHING;
    """, (empresa, agente))
    conn.commit()

    # Criar pendências automáticas com base na dim_pendencias
    cur.execute("SELECT documento FROM dim_pendencias;")
    documentos = cur.fetchall()
    for doc in documentos:
        cur.execute("""
            INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
            VALUES (%s, %s, 'pendente', NOW())
            ON CONFLICT DO NOTHING;
        """, (empresa, doc[0]))

    conn.commit()
    cur.close()
    conn.close()

# ====== OBTER DADOS ======
def obter_dados(query, params=None):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(query, params or ())
    dados = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(dados)

# ====== ATUALIZAR STATUS DE PENDÊNCIAS ======
def atualizar_pendencias(df_editado):
    conn = get_connection()
    cur = conn.cursor()
    for _, row in df_editado.iterrows():
        cur.execute("""
            UPDATE pendencias_empresa
            SET status = %s,
                data_ultima_atualizacao = NOW()
            WHERE empresa = %s AND documento = %s;
        """, (row["status"], row["empresa"], row["documento"]))
    conn.commit()
    cur.close()
    conn.close()

# ====== APP PRINCIPAL ======
def app():
    st.title("📋 Análise de Crédito - Libra Capital")

    tipo = st.session_state['tipo']
    agente = st.session_state['agente']

    if tipo == "comercial":
        st.subheader(f"🏢 Comercial - Agente: {agente}")
        empresa = st.text_input("Nome da nova empresa:")
        if st.button("Cadastrar empresa"):
            if empresa.strip():
                inserir_empresa(empresa.strip(), agente)
                st.success(f"✅ Empresa '{empresa}' cadastrada com sucesso!")
            else:
                st.warning("Digite o nome da empresa antes de cadastrar.")

        # Mostrar empresas já cadastradas pelo comercial
        empresas = obter_dados(
            "SELECT empresa, agente, entrada FROM analise_credito WHERE agente = %s ORDER BY entrada DESC;",
            (agente,)
        )
        st.dataframe(empresas, use_container_width=True)

    elif tipo == "analista":
        st.subheader("🧠 Painel do Analista")

        # Mostrar todas as empresas e pendências
        empresas = obter_dados("""
            SELECT a.empresa, a.agente, COUNT(p.status) AS pendentes_restantes
            FROM analise_credito a
            LEFT JOIN pendencias_empresa p ON a.empresa = p.empresa AND p.status = 'pendente'
            GROUP BY a.empresa, a.agente
            ORDER BY a.empresa;
        """)

        st.markdown("### 📊 Status das Empresas")
        st.dataframe(empresas, use_container_width=True)

        empresa_sel = st.selectbox("Selecione uma empresa para ver detalhes:", empresas["empresa"] if not empresas.empty else [])
        if empresa_sel:
            pendencias = obter_dados("""
                SELECT empresa, documento, status, data_ultima_atualizacao
                FROM pendencias_empresa
                WHERE empresa = %s
                ORDER BY documento;
            """, (empresa_sel,))

            st.markdown(f"### 🗂️ Pendências da empresa **{empresa_sel}**")
            editadas = st.data_editor(
                pendencias,
                num_rows="fixed",
                use_container_width=True,
                key="editor_pendencias"
            )

            if st.button("Salvar alterações"):
                atualizar_pendencias(editadas)
                st.success("✅ Pendências atualizadas com sucesso!")
                st.rerun()

# ====== MAIN ======
if 'usuario' not in st.session_state:
    login()
else:
    app()
