import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date

# =======================
# PALETA LIBRA
# =======================
SPACE_CADET = "#042F3C"
HARVEST_GOLD = "#C66300"
HONEYDEW = "#FFF4E3"
SLATE_GRAY = "#717c89"

st.set_page_config(page_title="Análise de Crédito", page_icon="📋", layout="wide")

# =======================
# ESTILOS GERAIS
# =======================
st.markdown(
    f"""
    <style>
      .stApp {{
        background: {SPACE_CADET};
      }}
      .stTabs [data-baseweb="tab-list"] button[role="tab"] {{
        background: {HARVEST_GOLD};
        color: {HONEYDEW};
        border-radius: 10px;
        margin-right: 8px;
        font-weight: 700;
      }}
      .metric-pill {{
        background: #ffffff10;
        border: 1px solid #ffffff22;
        border-radius: 12px;
        padding: 10px 14px;
        color:{HONEYDEW};
        text-align:center;
        font-weight:600;
      }}
      .good-pill {{background:#1f5135; color:#dff6e3; border:1px solid #2c7a4b;}}
      .warn-pill {{background:#5a3b00; color:#ffe8c7; border:1px solid #C66300aa;}}
      .big-title {{
        color:{HONEYDEW}; font-size:2rem; font-weight:900;
        border-bottom:2px solid {HARVEST_GOLD}99; padding-bottom:.12em;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =======================
# HEADER
# =======================
with st.container():
    cols = st.columns([0.2, 0.8])
    with cols[0]:
        st.image("imagens/Capital-branca.png", width=220)
    with cols[1]:
        st.markdown(
            f"""
            <span class='big-title'>
                LIBRA CAPITAL
                <span style='font-weight:400;color:{HARVEST_GOLD};'>| Análise de Crédito</span>
            </span>
            """,
            unsafe_allow_html=True,
        )

st.write("")

# =======================
# CONFIGURAÇÕES DO BANCO
# =======================
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": int(st.secrets["db_port"]),
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
}


@st.cache_resource
def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def run_query(query, params=None, fetch="df"):
    conn = get_conn()
    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch == "df":
                return pd.DataFrame(cur.fetchall())
            elif fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            else:
                return True


# =======================
# LOGIN
# =======================
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
                st.success("Login realizado com sucesso!")
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")


# =======================
# FUNÇÕES AUXILIARES
# =======================
SITUACOES = ["Em análise", "Aprovada", "Reprovada", "Stand by"]
SIM_NAO = ["Não", "Sim"]

def ensure_pendencias_empresa(empresa):
    base_docs = run_query("SELECT documento FROM dim_pendencias ORDER BY documento;")
    if base_docs.empty:
        return
    ja = run_query("SELECT documento FROM pendencias_empresa WHERE empresa = %s;", (empresa,))
    ja_set = set(ja["documento"].tolist()) if not ja.empty else set()
    to_insert = [d for d in base_docs["documento"].tolist() if d not in ja_set]
    if to_insert:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                cur.executemany(
                    """
                    INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
                    VALUES (%s, %s, 'pendente', NOW())
                    ON CONFLICT (empresa, documento) DO NOTHING;
                    """,
                    [(empresa, d) for d in to_insert],
                )


def simnao_to_date(simnao):
    return date.today() if simnao == "Sim" else None


def date_to_simnao(dt):
    return "Sim" if dt else "Não"


# =======================
# PAINEL COMERCIAL
# =======================
def painel_comercial():
    agente = st.session_state["agente"]

    st.markdown("### 🏢 Painel do Comercial")
    empresa = st.text_input("Nome da Empresa:")
    if st.button("➕ Adicionar Empresa"):
        if empresa:
            conn = get_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO analise_credito (empresa, agente, entrada)
                        VALUES (%s, %s, NOW())
                        ON CONFLICT (empresa) DO NOTHING;
                        """,
                        (empresa, agente),
                    )
            st.success(f"Empresa '{empresa}' adicionada com sucesso!")
            ensure_pendencias_empresa(empresa)
            st.rerun()
        else:
            st.warning("Digite o nome da empresa.")

    st.markdown("#### 📋 Empresas Cadastradas")
    df = run_query(
        """
        SELECT empresa, agente, entrada, situacao, limite, comentario_interno,
               saida_credito,
               (SELECT COUNT(*) FROM pendencias_empresa p WHERE p.empresa=a.empresa AND p.status='pendente') AS pendencias
        FROM analise_credito a
        WHERE agente=%s
        ORDER BY entrada DESC;
        """,
        (agente,),
    )

    if df.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
    else:
        df["entrada"] = df["entrada"].astype(str)
        st.dataframe(df, use_container_width=True, hide_index=True)


# =======================
# PAINEL ANALISTA
# =======================
def painel_analista():
    tab1, tab2 = st.tabs(["📊 Overview", "🧠 Detalhada"])

    # === OVERVIEW ===
    with tab1:
        st.markdown("### 📈 Overview")
        df = run_query(
            """
            SELECT
              empresa, agente, entrada, situacao, limite, saida_credito,
              COALESCE((
                SELECT COUNT(*) FROM pendencias_empresa pe
                WHERE pe.empresa = ac.empresa AND pe.status='pendente'
              ), 0) AS pendentes_restantes
            FROM analise_credito ac
            ORDER BY entrada DESC;
            """
        )

        if df.empty:
            st.info("Nenhuma empresa cadastrada ainda.")
        else:
            st.dataframe(
                df[["empresa","agente","entrada","situacao","limite","saida_credito","pendentes_restantes"]],
                use_container_width=True, hide_index=True
            )

            emp = st.selectbox("Selecione uma empresa:", df["empresa"].tolist())
            if emp:
                pend = run_query(
                    """
                    SELECT documento, status, data_ultima_atualizacao
                    FROM pendencias_empresa
                    WHERE empresa=%s AND status='pendente'
                    ORDER BY documento;
                    """,
                    (emp,),
                )
                if pend.empty:
                    st.success("🎉 Nenhuma pendência para essa empresa!")
                else:
                    pend["data_ultima_atualizacao"] = pend["data_ultima_atualizacao"].astype(str)
                    st.dataframe(pend, use_container_width=True, hide_index=True)

    # === DETALHADA ===
    with tab2:
        st.markdown("### 🧩 Detalhada")
        empresas = run_query("SELECT empresa FROM analise_credito ORDER BY empresa;")
        if empresas.empty:
            st.info("Nenhuma empresa cadastrada ainda.")
            return

        emp = st.selectbox("Escolha a empresa:", empresas["empresa"].tolist())
        ensure_pendencias_empresa(emp)
        dados = run_query("SELECT * FROM analise_credito WHERE empresa=%s;", (emp,)).iloc[0]

        st.markdown("#### Edição Completa")
        c1, c2 = st.columns(2)
        situacao = c1.selectbox("Situação", SITUACOES, index=SITUACOES.index(dados["situacao"]) if dados["situacao"] in SITUACOES else 0)
        limite = c1.number_input("Limite (R$)", value=float(dados["limite"]) if dados["limite"] else 0.0)
        comentario = c2.text_area("Comentário Interno", value=dados["comentario_interno"] or "", height=100)

        st.markdown("##### Checklist Operacional")
        c3, c4, c5, c6 = st.columns(4)
        envio_das = c3.selectbox("Envio DAS", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["envio_das"])))
        emissao_contrato = c4.selectbox("Emissão contrato", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["emissao_contrato"])))
        assinatura = c5.selectbox("Assinatura", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["assinatura"])))
        homologacao = c6.selectbox("Homologação", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["homologacao"])))
        apto = st.selectbox("Apto a operar", SIM_NAO, index=SIM_NAO.index("Sim" if dados["apto_a_operar"] else "Não"))

        pend = run_query(
            """
            SELECT id, documento, status, data_ultima_atualizacao
            FROM pendencias_empresa WHERE empresa=%s ORDER BY documento;
            """,
            (emp,),
        )
        pend["status"] = pend["status"].fillna("pendente")

        edited = st.data_editor(
            pend,
            hide_index=True,
            use_container_width=True,
            column_config={
                "status": st.column_config.SelectboxColumn("status", options=["pendente", "recebido"], required=True),
                "data_ultima_atualizacao": st.column_config.DatetimeColumn("data_ultima_atualizacao", disabled=True),
                "documento": st.column_config.TextColumn("documento", disabled=True),
                "id": st.column_config.NumberColumn("id", disabled=True),
            },
            key=f"editor_pend_{emp}",
        )

        if st.button("💾 Salvar alterações"):
            conn = get_conn()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE analise_credito
                        SET situacao=%s, limite=%s, comentario_interno=%s,
                            envio_das=%s, emissao_contrato=%s,
                            assinatura=%s, homologacao=%s, apto_a_operar=%s
                        WHERE empresa=%s;
                        """,
                        (
                            situacao, limite, comentario,
                            simnao_to_date(envio_das), simnao_to_date(emissao_contrato),
                            simnao_to_date(assinatura), simnao_to_date(homologacao),
                            apto == "Sim", emp
                        ),
                    )
                    for _, row in edited.iterrows():
                        cur.execute(
                            """
                            UPDATE pendencias_empresa
                            SET status=%s, data_ultima_atualizacao=NOW()
                            WHERE id=%s;
                            """,
                            (row["status"], int(row["id"])),
                        )
            st.success("Alterações salvas com sucesso!")
            st.rerun()


# =======================
# MAIN
# =======================
if "usuario" not in st.session_state:
    login()
else:
    tipo = st.session_state["tipo"]
    if tipo == "comercial":
        painel_comercial()
    elif tipo == "analista":
        painel_analista()
