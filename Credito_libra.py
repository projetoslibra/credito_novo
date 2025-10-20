import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# ====== CONFIGURAÇÕES DO BANCO ======
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "port": st.secrets["DB_PORT"],
    "dbname": st.secrets["DB_NAME"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASS"]
}

# ====== FUNÇÃO DE CONEXÃO ======
def conectar():
    return psycopg2.connect(**DB_CONFIG)

# ====== FUNÇÃO PARA CONSULTAS ======
def obter_dados(query, params=None):
    conn = conectar()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

# ====== FUNÇÃO PARA INSERIR EMPRESA ======
def inserir_empresa(empresa, agente):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO analise_credito (empresa, agente, entrada, situacao)
        VALUES (%s, %s, NOW(), 'Em análise')
        ON CONFLICT (empresa) DO NOTHING;
    """, (empresa, agente))
    conn.commit()
    cur.close()
    conn.close()

# ====== FUNÇÃO PARA ATUALIZAR PENDÊNCIAS ======
def atualizar_pendencias(df_editado):
    conn = conectar()
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

# ====== LOGIN ======
USERS = {
    "Breno": {"senha": "Breno13", "tipo": "comercial", "agente": "Breno"},
    "analista": {"senha": "1234", "tipo": "analista", "agente": None},
}

def login():
    with st.sidebar:
        st.markdown("## 🔐 Login")
        user = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if user in USERS and USERS[user]["senha"] == password:
                st.session_state["usuario"] = user
                st.session_state["tipo"] = USERS[user]["tipo"]
                st.session_state["agente"] = USERS[user]["agente"]
                st.success("✅ Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos")

# ====== APP PRINCIPAL ======
def app():
    st.title("📋 Análise de Crédito - Libra Capital")

    tipo = st.session_state["tipo"]
    agente = st.session_state["agente"]

    # === COMERCIAL ===
    if tipo == "comercial":
        st.subheader(f"🏢 Painel do Comercial - Agente: {agente}")

        # Input nova empresa
        empresa = st.text_input("🧾 Nome da nova empresa:")
        if st.button("Cadastrar empresa"):
            if empresa.strip():
                inserir_empresa(empresa.strip(), agente)
                st.success(f"✅ Empresa '{empresa}' cadastrada com sucesso!")
                st.rerun()
            else:
                st.warning("⚠️ Digite o nome da empresa antes de cadastrar.")

        # Filtros e atualização
        st.markdown("### 🔎 Empresas Cadastradas")
        filtro_situacao = st.selectbox(
            "Filtrar por situação:",
            ["Todas", "Em análise", "Aprovada", "Reprovada", "Stand by"]
        )

        if st.button("🔄 Atualizar tabela"):
            st.rerun()

        query = """
            SELECT 
                empresa,
                agente,
                TO_CHAR(entrada, 'DD/MM/YYYY HH24:MI') AS entrada,
                COALESCE(situacao, 'Em análise') AS situacao,
                limite,
                comentario_interno,
                TO_CHAR(saida_credito, 'DD/MM/YYYY') AS saida_credito,
                pendencias
            FROM analise_credito
            WHERE agente = %s
        """

        if filtro_situacao != "Todas":
            query += " AND situacao = %s"
            params = (agente, filtro_situacao)
        else:
            params = (agente,)

        query += " ORDER BY entrada DESC;"
        empresas = obter_dados(query, params)

        st.dataframe(empresas, use_container_width=True)

    # === ANALISTA ===
    elif tipo == "analista":
        st.subheader("🧠 Painel do Analista")

        empresas = obter_dados("""
            SELECT 
                a.empresa,
                a.agente,
                COALESCE(a.situacao, 'Em análise') AS situacao,
                TO_CHAR(a.entrada, 'DD/MM/YYYY HH24:MI') AS entrada,
                COUNT(p.status) FILTER (WHERE p.status = 'pendente') AS pendentes_restantes
            FROM analise_credito a
            LEFT JOIN pendencias_empresa p ON a.empresa = p.empresa
            GROUP BY a.empresa, a.agente, a.situacao, a.entrada
            ORDER BY a.entrada DESC;
        """)

        st.markdown("### 📊 Status das Empresas")
        st.dataframe(empresas, use_container_width=True)

        empresa_sel = st.selectbox("Selecione uma empresa para ver detalhes:",
                                   empresas["empresa"] if not empresas.empty else [])
        if empresa_sel:
            pendencias = obter_dados("""
                SELECT empresa, documento, status, 
                       TO_CHAR(data_ultima_atualizacao, 'DD/MM/YYYY HH24:MI') AS data_ultima_atualizacao
                FROM pendencias_empresa
                WHERE empresa = %s
                ORDER BY documento;
            """, (empresa_sel,))

            st.markdown(f"### 📎 Pendências da empresa **{empresa_sel}**")
            editadas = st.data_editor(
                pendencias,
                num_rows="fixed",
                use_container_width=True,
                key="editor_pendencias"
            )

            if st.button("💾 Salvar alterações"):
                atualizar_pendencias(editadas)
                st.success("✅ Pendências atualizadas com sucesso!")
                st.rerun()

# ====== MAIN ======
if "usuario" not in st.session_state:
    login()
else:
    app()
