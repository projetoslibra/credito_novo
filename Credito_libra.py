import streamlit as st
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import date, datetime

# =======================
# PALETA LIBRA
# =======================
SPACE_CADET  = "#042F3C"
HARVEST_GOLD = "#C66300"
HONEYDEW     = "#FFF4E3"
SLATE_GRAY    = "#717c89"

st.set_page_config(page_title="Análise de Crédito", page_icon="📋", layout="wide")
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
      .stTabs [aria-selected="true"] {{
        border: 2px solid #ffffff22;
      }}
      .metric-pill {{
        background: #ffffff10;
        border: 1px solid #ffffff22;
        border-radius: 12px;
        padding: 12px 14px;
      }}
      .good-pill {{
        background: #1f5135; color:#dff6e3; border:1px solid #2c7a4b;
      }}
      .warn-pill {{
        background: #5a3b00; color:#ffe8c7; border:1px solid #C66300aa;
      }}
      .card {{
        background: #00000014; border:1px solid #ffffff22; border-radius:14px; padding:16px;
      }}
      .label {{
        color:{SLATE_GRAY}; font-size:0.85rem;
      }}
      .btn-save button {{
        background:{HARVEST_GOLD} !important; color:{HONEYDEW} !important; font-weight:700 !important;
      }}
      .big-title {{
        color:{HONEYDEW}; font-size:2.0rem; font-weight:900;
        border-bottom: 2px solid {HARVEST_GOLD}99; padding-bottom:.12em;
      }}
      .sub-title {{
        color:{HONEYDEW}; font-size:1.25rem; font-weight:800; margin-top:.75rem;
      }}
      .text {{
        color:{HONEYDEW};
      }}
      .muted {{
        color:{SLATE_GRAY};
      }}
      .dark-input input, .dark-input textarea {{
        background:#20262b !important; color:{HONEYDEW} !important; border:1px solid #ffffff22 !important;
      }}
      .dark-select div[data-baseweb="select"] > div {{
        background:#20262b !important; color:{HONEYDEW} !important; border:1px solid #ffffff22 !important;
      }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =======================
# HEADER (modelo que você mandou)
# =======================
with st.container():
    cols = st.columns([0.2, 0.8])
    with cols[0]:
        st.image("imagens/Capital-branca.png", width=220, output_format="PNG")
    with cols[1]:
        st.markdown(
            f"""
            <span class='big-title'>
                LIBRA CAPITAL
                <span style='font-weight:400;color:{HARVEST_GOLD};'>| Análise de Crédito</span>
            </span>
            """,
            unsafe_allow_html=True
        )

st.write("")  # espaçamento


# =======================
# CONEXÃO COM POSTGRES
# =======================
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": int(st.secrets["db_port"]),
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
}

@st.cache_resource(show_spinner=False)
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def run_query(query, params=None, fetch="df"):
    """
    fetch='df' -> retorna DataFrame
    fetch='one' -> um registro
    fetch=None -> só executa (INSERT/UPDATE/DELETE)
    """
    conn = get_conn()
    with conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params or ())
            if fetch == "df":
                rows = cur.fetchall()
                return pd.DataFrame(rows)
            elif fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            else:
                return True

# =======================
# Utilitários / Negócio
# =======================
SITUACOES = ["Em análise", "Aprovada", "Reprovada", "Stand by"]
SIM_NAO   = ["Não", "Sim"]  # default = Não

def ensure_pendencias_empresa(empresa: str):
    """
    Garante que a empresa tenha todas as pendências base de dim_pendencias
    na tabela pendencias_empresa.
    """
    # documentos base
    base_docs = run_query("SELECT documento FROM dim_pendencias ORDER BY documento;")
    if base_docs.empty:
        return

    # já existentes
    ja = run_query(
        "SELECT documento FROM pendencias_empresa WHERE empresa = %s;",
        (empresa,)
    )
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
                    [(empresa, d) for d in to_insert]
                )

def simnao_to_date(simnao: str):
    """ 'Sim' -> hoje; 'Não' -> None """
    return date.today() if simnao == "Sim" else None

def date_to_simnao(dt):
    """ date/None -> 'Sim'/'Não' """
    return "Sim" if dt else "Não"


# =======================
# OVERVIEW
# =======================
def overview():
    st.markdown(f"<div class='sub-title'>📊 Overview</div>", unsafe_allow_html=True)

    # Quadro principal: empresa, agente, entrada, situacao, limite, saída crédito, pendentes
    df = run_query(
        """
        SELECT
          empresa,
          agente,
          entrada,
          situacao,
          limite,
          saida_credito,
          COALESCE((
            SELECT COUNT(*) FROM pendencias_empresa pe
            WHERE pe.empresa = ac.empresa AND pe.status='pendente'
          ), 0) AS pendentes_restantes
        FROM analise_credito ac
        ORDER BY entrada DESC NULLS LAST, empresa ASC;
        """
    )

    if df.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
        return

    # Métricas gerais
    colm = st.columns(4)
    with colm[0]:
        st.markdown("<div class='label'>Total de empresas</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-pill text'>{len(df):,}</div>", unsafe_allow_html=True)
    with colm[1]:
        a = (df["situacao"] == "Aprovada").sum()
        st.markdown("<div class='label'>Aprovadas</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-pill good-pill'>{a:,}</div>", unsafe_allow_html=True)
    with colm[2]:
        r = (df["situacao"] == "Reprovada").sum()
        st.markdown("<div class='label'>Reprovadas</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-pill warn-pill'>{r:,}</div>", unsafe_allow_html=True)
    with colm[3]:
        pend_total = int(df["pendentes_restantes"].sum())
        st.markdown("<div class='label'>Pendências totais</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='metric-pill warn-pill'>{pend_total:,}</div>", unsafe_allow_html=True)

    st.write("")
    st.markdown("<div class='sub-title'>📚 Status das empresas</div>", unsafe_allow_html=True)

    show = df.copy()
    # formatações amigáveis
    show["entrada"] = show["entrada"].astype(str)
    show["saida_credito"] = show["saida_credito"].astype(str)
    st.dataframe(
        show[["empresa","agente","entrada","situacao","limite","saida_credito","pendentes_restantes"]],
        use_container_width=True, hide_index=True
    )

    # Expansível: lista de pendências por empresa
    st.write("")
    emp_list = df["empresa"].tolist()
    sel = st.selectbox("Selecione uma empresa para ver as pendências:", emp_list)
    if sel:
        ensure_pendencias_empresa(sel)
        p = run_query(
            """
            SELECT documento, status, data_ultima_atualizacao
            FROM pendencias_empresa
            WHERE empresa = %s
            ORDER BY documento;
            """,
            (sel,)
        )
        if p.empty:
            st.info("Sem pendências cadastradas.")
        else:
            p["data_ultima_atualizacao"] = p["data_ultima_atualizacao"].astype(str)
            st.dataframe(p, use_container_width=True, hide_index=True)


# =======================
# DETALHADA (FORM ANALISTA)
# =======================
def detalhada():
    st.markdown(f"<div class='sub-title'>🧠 Detalhada</div>", unsafe_allow_html=True)

    empresas = run_query("SELECT empresa, agente, situacao FROM analise_credito ORDER BY empresa;")
    if empresas.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
        return

    emp_names = empresas["empresa"].tolist()
    emp = st.selectbox("Escolha a empresa:", emp_names, index=0, key="sel_emp_detalhe")
    ensure_pendencias_empresa(emp)

    dados = run_query(
        """
        SELECT empresa, agente, entrada, situacao, limite, comentario_interno,
               saida_credito, envio_das, emissao_contrato, assinatura,
               homologacao, apto_a_operar, email_informando
        FROM analise_credito
        WHERE empresa = %s
        """,
        (emp,),
        fetch="df"
    ).iloc[0]

    # ===== bloco de edição
    st.markdown("##### ✏️ Edição Completa")
    c1,c2,c3 = st.columns([1,1.2,1])

    with c1:
        situacao = st.selectbox(
            "Situação",
            SITUACOES,
            index = SITUACOES.index(dados["situacao"]) if dados["situacao"] in SITUACOES else 0,
            help="Definida manualmente pelo analista."
        )
        limite = st.number_input("Limite (R$)", value=float(dados["limite"]) if dados["limite"] else 0.0, step=1000.0, min_value=0.0)

    with c2:
        comentario = st.text_area("Comentário Interno", value=dados["comentario_interno"] or "", height=140)

    with c3:
        st.markdown("**Pendências (quantitativo)**")
        qtd_pend = run_query(
            "SELECT COUNT(*) q FROM pendencias_empresa WHERE empresa=%s AND status='pendente';",
            (emp,), fetch="one"
        )["q"]
        st.markdown(f"<div class='metric-pill warn-pill' style='text-align:center;font-size:1.2rem;'>{qtd_pend} pendente(s)</div>", unsafe_allow_html=True)

    c4,c5 = st.columns([1,1])
    with c4:
        saida_credito = st.date_input("Saída Crédito", value=pd.to_datetime(dados["saida_credito"]).date() if dados["saida_credito"] else None)
    with c5:
        apto = st.selectbox("Apto a operar", SIM_NAO, index=SIM_NAO.index("Sim" if dados["apto_a_operar"] else "Não"))

    st.markdown("##### ☑️ Checklist Operacional")
    c6,c7,c8,c9 = st.columns(4)
    with c6:
        envio_das = st.selectbox("Envio DAS", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["envio_das"])))
    with c7:
        emissao_contrato = st.selectbox("Emissão contrato", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["emissao_contrato"])))
    with c8:
        assinatura = st.selectbox("Assinatura", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["assinatura"])))
    with c9:
        homologacao = st.selectbox("Homologação", SIM_NAO, index=SIM_NAO.index(date_to_simnao(dados["homologacao"])))

    # ===== Pendências (grid interativo)
    st.markdown("##### 📎 Pendências (marque recebido quando o documento chegar)")
    pend = run_query(
        """
        SELECT id, documento, status, data_ultima_atualizacao
        FROM pendencias_empresa
        WHERE empresa=%s
        ORDER BY documento;
        """,
        (emp,)
    )
    # Config do editor: Selectbox por linha (pendente/recebido)
    if not pend.empty:
        pend["status"] = pend["status"].fillna("pendente")
        edited = st.data_editor(
            pend,
            hide_index=True,
            use_container_width=True,
            column_config={
                "status": st.column_config.SelectboxColumn(
                    "status", options=["pendente","recebido"], required=True
                ),
                "data_ultima_atualizacao": st.column_config.DatetimeColumn(
                    "data_ultima_atualizacao", disabled=True
                ),
                "id": st.column_config.NumberColumn("id", disabled=True),
                "documento": st.column_config.TextColumn("documento", disabled=True)
            },
            key=f"editor_pend_{emp}"
        )
    else:
        edited = pend

    st.write("")
    save = st.button("💾 Salvar alterações", type="primary", help="Persiste todas as alterações desta empresa")
    if save:
        conn = get_conn()
        with conn:
            with conn.cursor() as cur:
                # Update principal
                cur.execute(
                    """
                    UPDATE analise_credito
                    SET situacao=%s,
                        limite=%s,
                        comentario_interno=%s,
                        saida_credito=%s,
                        envio_das=%s,
                        emissao_contrato=%s,
                        assinatura=%s,
                        homologacao=%s,
                        apto_a_operar=%s
                    WHERE empresa=%s
                    """,
                    (
                        situacao,
                        limite if limite else None,
                        comentario,
                        saida_credito,
                        simnao_to_date(envio_das),
                        simnao_to_date(emissao_contrato),
                        simnao_to_date(assinatura),
                        simnao_to_date(homologacao),
                        (apto == "Sim"),
                        emp
                    )
                )

                # Update pendências linha a linha
                if not edited.empty:
                    for _, row in edited.iterrows():
                        cur.execute(
                            """
                            UPDATE pendencias_empresa
                            SET status=%s,
                                data_ultima_atualizacao=NOW()
                            WHERE id=%s
                            """,
                            (row["status"], int(row["id"]))
                        )

        st.success("Alterações salvas com sucesso! Atualize o Overview para ver os números recalculados.")


# =======================
# MAIN (Tabs)
# =======================
tab1, tab2 = st.tabs(["📊 Overview", "🧠 Detalhada"])
with tab1:
    overview()
with tab2:
    detalhada()
