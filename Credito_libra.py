import streamlit as st
import pandas as pd
import psycopg2
from psycopg2 import sql
from datetime import datetime

# ======= CONFIGURAÇÃO VISUAL =======
SPACE_CADET = "#042F3C"
HARVEST_GOLD = "#C66300"
HONEYDEW = "#FFF4E3"
SLATE_GRAY = "#717c89"

st.set_page_config(page_title="Libra Capital | Crédito", page_icon="📋", layout="wide")

st.markdown(f"""
    <style>
        /* Background e fontes */
        .stApp {{
            background-color: {SPACE_CADET};
            color: {HONEYDEW};
        }}
        h1, h2, h3, h4, h5, h6 {{
            color: {HONEYDEW};
            font-weight: 700;
        }}
        .stDataFrame {{
            background-color: {SPACE_CADET};
        }}
        /* Botões personalizados */
        .stButton>button {{
            background-color: {HARVEST_GOLD};
            color: white;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            padding: 0.6rem 1.2rem;
        }}
        .stButton>button:hover {{
            background-color: #e67700;
            color: white;
        }}
        /* Navegação customizada */
        .nav-container {{
            display: flex;
            justify-content: center;
            margin-bottom: 1.5rem;
        }}
        .nav-button {{
            background-color: #0e1117;
            border: 1px solid #31333F;
            color: white;
            padding: 0.6rem 1.2rem;
            border-radius: 0.5rem;
            margin: 0 0.3rem;
            cursor: pointer;
            transition: 0.3s;
            font-weight: 600;
        }}
        .nav-button:hover {{
            background-color: #1e222f;
        }}
        .active {{
            background-color: {HARVEST_GOLD};
            color: white;
            border: 1px solid {HARVEST_GOLD};
        }}
    </style>
""", unsafe_allow_html=True)

# ======= LOGO E HEADER =======
st.markdown(f"""
    <div style='text-align: center;'>
        <img src="https://raw.githubusercontent.com/seu_usuario/seu_repositorio/main/imagens/logo_libra.png" width="150">
        <h1 style="color:{HONEYDEW}; margin-top: -10px;">LIBRA CAPITAL</h1>
        <h3 style="color:{HARVEST_GOLD}; margin-top: -20px;">Painel de Análise de Crédito</h3>
    </div>
""", unsafe_allow_html=True)

# ======= CONFIG DB =======
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"]
}

def conectar():
    return psycopg2.connect(**DB_CONFIG)

# ======= LOGIN =======
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
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos")

# ======= FUNÇÕES DB =======
def carregar_dados(query, params=None):
    conn = conectar()
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df

def salvar_dados(query, params):
    conn = conectar()
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    cur.close()
    conn.close()

def inserir_empresa(empresa, agente):
    conn = conectar()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO analise_credito (empresa, agente, entrada)
        VALUES (%s, %s, NOW())
        ON CONFLICT (empresa) DO NOTHING;
    """, (empresa, agente))
    conn.commit()
    cur.close()
    conn.close()

# ======= APP =======
def app():
    st.markdown("---")
    tipo = st.session_state['tipo']
    agente = st.session_state['agente']

    # ======= COMERCIAL =======
    if tipo == "comercial":
        st.subheader(f"🧾 Painel do Comercial - {agente}")
        empresa = st.text_input("Nova empresa:")
        if st.button("Adicionar empresa"):
            if empresa.strip():
                inserir_empresa(empresa.strip(), agente)
                st.success(f"✅ '{empresa}' adicionada com sucesso!")
                st.rerun()
            else:
                st.warning("Digite o nome da empresa.")

        query = """
        SELECT empresa, agente, entrada, situacao, limite, comentario_interno, saida_credito
        FROM analise_credito WHERE agente = %s ORDER BY entrada DESC;
        """
        empresas = carregar_dados(query, (agente,))

        if not empresas.empty:
            st.dataframe(empresas, use_container_width=True)
            empresa_sel = st.selectbox("Selecione uma empresa:", empresas['empresa'])
            if empresa_sel:
                st.markdown(f"### 📂 Pendências da empresa {empresa_sel}")
                query_pend = """
                SELECT documento, status, data_ultima_atualizacao
                FROM pendencias_empresa WHERE empresa = %s
                ORDER BY status DESC, documento;
                """
                pend = carregar_dados(query_pend, (empresa_sel,))
                pendentes = pend[pend["status"] == "pendente"].shape[0]
                st.info(f"📄 Documentos pendentes: **{pendentes}**")
                st.dataframe(pend, use_container_width=True)
        else:
            st.info("Nenhuma empresa adicionada.")

    # ======= ANALISTA =======
    elif tipo == "analista":
        # Controle das abas
        if "aba_analista" not in st.session_state:
            st.session_state["aba_analista"] = "overview"

        col1, col2 = st.columns(2)
        with col1:
            if st.button("📊 Overview", key="overview", use_container_width=True):
                st.session_state["aba_analista"] = "overview"
        with col2:
            if st.button("🧠 Detalhada", key="detalhada", use_container_width=True):
                st.session_state["aba_analista"] = "detalhada"

        st.markdown("---")

        # === ABA 1: OVERVIEW ===
        if st.session_state["aba_analista"] == "overview":
            st.subheader("📈 Status das Empresas")
            query_emp = """
            SELECT a.empresa, a.agente, a.situacao,
                   COUNT(*) FILTER (WHERE p.status = 'pendente') AS pendentes_restantes
            FROM analise_credito a
            LEFT JOIN pendencias_empresa p ON a.empresa = p.empresa
            GROUP BY a.empresa, a.agente, a.situacao
            ORDER BY pendentes_restantes DESC;
            """
            status_empresas = carregar_dados(query_emp)
            if not status_empresas.empty:
                def color_status(s):
                    cores = {
                        "Aprovada": "🟢 Aprovada",
                        "Reprovada": "🔴 Reprovada",
                        "Em análise": "🟡 Em análise",
                        "Stand by": "⚪ Stand by"
                    }
                    return cores.get(s, "⚪ Não definida")
                status_empresas["situacao"] = status_empresas["situacao"].apply(color_status)
                st.dataframe(status_empresas, use_container_width=True)

                empresa_sel = st.selectbox("Selecionar empresa:", status_empresas["empresa"])
                if empresa_sel:
                    st.markdown(f"### 📂 Pendências - {empresa_sel}")
                    query_p = """
                    SELECT documento, status, data_ultima_atualizacao
                    FROM pendencias_empresa WHERE empresa = %s
                    ORDER BY status DESC, documento;
                    """
                    pend = carregar_dados(query_p, (empresa_sel,))
                    pendentes = pend[pend["status"] == "pendente"].shape[0]
                    st.info(f"📄 Documentos pendentes: **{pendentes}**")
                    st.dataframe(pend, use_container_width=True)
            else:
                st.warning("Nenhuma empresa cadastrada.")

        # === ABA 2: DETALHADA ===
        elif st.session_state["aba_analista"] == "detalhada":
            st.subheader("🧩 Edição Completa")
            query_all = "SELECT * FROM analise_credito ORDER BY entrada DESC;"
            dados = carregar_dados(query_all)
            if not dados.empty:
                for i, row in dados.iterrows():
                    with st.expander(f"📄 {row['empresa']} — {row['situacao']}"):
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            situacao = st.selectbox(
                                "Situação",
                                ["Em análise", "Aprovada", "Reprovada", "Stand by"],
                                index=["Em análise", "Aprovada", "Reprovada", "Stand by"].index(
                                    row["situacao"] if row["situacao"] in ["Em análise", "Aprovada", "Reprovada", "Stand by"] else "Em análise"
                                ),
                                key=f"situacao_{i}"
                            )
                            limite = st.number_input("Limite (R$)", value=float(row["limite"] or 0), key=f"limite_{i}")
                        with col2:
                            comentario = st.text_area("Comentário Interno", value=row["comentario_interno"], key=f"coment_{i}")
                            saida_credito = st.date_input("Saída Crédito", value=row["saida_credito"], key=f"saida_{i}")
                        with col3:
                            pendencias = st.text_input("Pendências", value=row["pendencias"], key=f"pend_{i}")

                        if st.button(f"💾 Salvar {row['empresa']}", key=f"save_{i}"):
                            query_upd = """
                            UPDATE analise_credito
                            SET situacao=%s, limite=%s, comentario_interno=%s, saida_credito=%s, pendencias=%s
                            WHERE empresa=%s;
                            """
                            salvar_dados(query_upd, (situacao, limite, comentario, saida_credito, pendencias, row["empresa"]))
                            st.success(f"✅ Empresa '{row['empresa']}' atualizada!")
                            st.rerun()
            else:
                st.info("Nenhum dado disponível.")
