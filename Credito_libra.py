import streamlit as st
import pandas as pd
import psycopg2
from datetime import datetime

# ====== CONFIGURAÇÃO DO BANCO ======
DB_CONFIG = {
    "host": st.secrets["DB_HOST"],
    "port": st.secrets["DB_PORT"],
    "dbname": st.secrets["DB_NAME"],
    "user": st.secrets["DB_USER"],
    "password": st.secrets["DB_PASS"]
}

# ====== CONEXÃO ======
def conectar():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"❌ Erro na conexão com o banco: {e}")
        return None

# ====== INSERIR EMPRESA ======
def inserir_empresa(empresa, agente):
    conn = conectar()
    if conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO analise_credito (empresa, agente, entrada, situacao)
            VALUES (%s, %s, NOW(), 'Em análise')
            ON CONFLICT (empresa) DO NOTHING;
        """, (empresa, agente))
        conn.commit()
        cur.close()
        conn.close()

        # Popula automaticamente as pendências para essa empresa
        conn = conectar()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
            SELECT %s, d.documento, 'pendente', NOW()
            FROM dim_pendencias d
            WHERE NOT EXISTS (
                SELECT 1 FROM pendencias_empresa p WHERE p.empresa = %s AND p.documento = d.documento
            );
        """, (empresa, empresa))
        conn.commit()
        cur.close()
        conn.close()

# ====== CARREGAR DADOS ======
def carregar_dados(query, params=None):
    conn = conectar()
    if conn:
        df = pd.read_sql(query, conn, params=params)
        conn.close()
        return df
    return pd.DataFrame()

# ====== SALVAR DADOS ======
def salvar_dados(query, params):
    conn = conectar()
    if conn:
        cur = conn.cursor()
        cur.execute(query, params)
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

# ====== APP PRINCIPAL ======
def app():
    st.title("📋 Análise de Crédito")

    tipo = st.session_state['tipo']
    agente = st.session_state['agente']

    # =============== ÁREA DO COMERCIAL ===============
    if tipo == "comercial":
        st.subheader(f"🧾 Painel do Comercial - {agente}")

        empresa = st.text_input("Nome da empresa para adicionar:")
        if st.button("Adicionar empresa"):
            if empresa.strip():
                inserir_empresa(empresa.strip(), agente)
                st.success(f"✅ Empresa '{empresa}' adicionada com sucesso!")
            else:
                st.warning("Por favor, insira o nome da empresa.")

        st.markdown("---")
        st.subheader("📊 Status das Empresas")

        query = """
        SELECT empresa, agente, entrada, situacao, limite, comentario_interno, saida_credito
        FROM analise_credito
        WHERE agente = %s
        ORDER BY entrada DESC;
        """
        empresas = carregar_dados(query, (agente,))

        if not empresas.empty:
            st.dataframe(empresas, use_container_width=True)

            empresa_sel = st.selectbox("Selecione uma empresa para ver pendências:", empresas['empresa'].unique())
            if empresa_sel:
                st.markdown(f"### 📂 Pendências da empresa {empresa_sel}")

                query_pend = """
                SELECT documento, status, data_ultima_atualizacao
                FROM pendencias_empresa
                WHERE empresa = %s
                ORDER BY status DESC, documento;
                """
                pendencias = carregar_dados(query_pend, (empresa_sel,))

                pendentes_restantes = pendencias[pendencias["status"] == "pendente"].shape[0]
                st.info(f"📄 Documentos pendentes: **{pendentes_restantes}**")

                st.dataframe(pendencias, use_container_width=True)
        else:
            st.warning("Nenhuma empresa cadastrada ainda.")

    # =============== ÁREA DO ANALISTA ===============
    elif tipo == "analista":
        st.subheader("🧠 Painel do Analista")

        # STATUS DAS EMPRESAS
        st.markdown("### 📊 Status das Empresas")
        query_emp = """
        SELECT a.empresa, a.agente,
               COUNT(p.id) FILTER (WHERE p.status = 'pendente') AS pendentes_restantes
        FROM analise_credito a
        LEFT JOIN pendencias_empresa p ON a.empresa = p.empresa
        GROUP BY a.empresa, a.agente
        ORDER BY pendentes_restantes DESC;
        """
        status_empresas = carregar_dados(query_emp)

        st.dataframe(status_empresas, use_container_width=True)

        # SELECIONAR EMPRESA
        empresas = status_empresas['empresa'].unique() if not status_empresas.empty else []
        empresa_sel = st.selectbox("Selecione uma empresa para ver detalhes:", empresas)

        if empresa_sel:
            st.markdown(f"### 📁 Pendências da empresa {empresa_sel}")

            query_pend = """
            SELECT documento, status, data_ultima_atualizacao
            FROM pendencias_empresa
            WHERE empresa = %s
            ORDER BY status DESC, documento;
            """
            pendencias = carregar_dados(query_pend, (empresa_sel,))

            editar = st.data_editor(
                pendencias,
                use_container_width=True,
                key=f"pend_{empresa_sel}",
                hide_index=True
            )

            if st.button("Salvar alterações"):
                conn = conectar()
                cur = conn.cursor()
                for _, row in editar.iterrows():
                    cur.execute("""
                        UPDATE pendencias_empresa
                        SET status = %s, data_ultima_atualizacao = NOW()
                        WHERE empresa = %s AND documento = %s;
                    """, (row["status"], empresa_sel, row["documento"]))
                conn.commit()
                cur.close()
                conn.close()
                st.success("Alterações salvas com sucesso!")
                st.rerun()

# ====== MAIN ======
if 'usuario' not in st.session_state:
    login()
else:
    app()
