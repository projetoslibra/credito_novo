# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras as pg_extras
from datetime import date, datetime

# =========================================================
# PALETA / ESTILO
# =========================================================
SPACE_CADET = "#042F3C"
HARVEST_GOLD = "#C66300"
HONEYDEW = "#FFF4E3"
SLATE_GRAY = "#717c89"

st.set_page_config(
    page_title="Libra Capital | Análise de Crédito",
    page_icon="📄",
    layout="wide",
)

# =========================================================
# HEADER
# =========================================================
def header():
    with st.container():
        cols = st.columns([0.18, 0.82])
        with cols[0]:
            st.image("imagens/Capital-branca.png", width=180, output_format="PNG")
        with cols[1]:
            st.markdown(
                f"""
                <span style='
                    color: {HONEYDEW};
                    font-size: 2.0rem;
                    font-weight:900;
                    border-bottom: 2px solid {HARVEST_GOLD}99;
                    padding-bottom: 0.12em;'>
                    LIBRA CAPITAL
                    <span style='font-weight:400;color:{HARVEST_GOLD};'>| Análise de Crédito</span>
                </span>
                """,
                unsafe_allow_html=True
            )

# CSS fino
st.markdown(
    f"""
    <style>
      .block-container {{ padding-top: 1.2rem; }}
      .stTabs [data-baseweb="tab-list"] button {{ background: {HARVEST_GOLD}; color: white; border-radius: 6px; margin-right: 6px; }}
      .kpi-card {{
        background: {HARVEST_GOLD}22;
        border: 1px solid {HARVEST_GOLD}55;
        color: {HONEYDEW};
        padding: 12px 14px; border-radius: 10px; text-align: center;
      }}
      .kpi-card h3 {{ margin: 0; font-size: 1.7rem; color: {HONEYDEW}; }}
      .kpi-card span {{ font-size: .9rem; color: {SLATE_GRAY}; }}
      .dark-box {{
        background: #0b2e39; border: 1px solid #0e3a47; border-radius: 8px; padding: 10px 14px;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# DB
# =========================================================
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
}

@st.cache_resource(show_spinner=False)
def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def run_query_df(sql, params=None):
    conn = get_conn()
    df = pd.read_sql(sql, conn, params=params)
    return df

def run_exec(sql, params=None, many=False):
    conn = get_conn()
    with conn, conn.cursor(cursor_factory=pg_extras.RealDictCursor) as cur:
        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
    # psycopg2 auto-commit under context

# =========================================================
# LOGIN / SESSÃO
# =========================================================
USERS = {
    # nome_visível: {senha, tipo, agente}
    "Breno": {"senha": "Breno13", "tipo": "comercial", "agente": "Breno"},
    "analista": {"senha": "1234", "tipo": "analista", "agente": None},
    # adicione se quiser
}

def login_box():
    with st.sidebar:
        st.markdown("## Login")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            if u in USERS and USERS[u]["senha"] == p:
                st.session_state.user = u
                st.session_state.tipo = USERS[u]["tipo"]
                st.session_state.agente = USERS[u]["agente"]
                st.rerun()
            else:
                st.error("Usuário/senha inválidos")

if "user" not in st.session_state:
    header()
    login_box()
    st.stop()

# =========================================================
# HELPERS DE NEGÓCIO
# =========================================================
SITUACOES = ["Em análise", "Aprovada", "Reprovada", "Stand by"]
SIM_NAO = ["Não", "Sim"]

def ensure_pendencias_empresa(empresa):
    """Garante que existam registros na pendencias_empresa para todos os docs da dim_pendencias."""
    sql = """
    INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
    SELECT %s, d.documento, 'pendente', NOW()
    FROM dim_pendencias d
    WHERE NOT EXISTS (
        SELECT 1 FROM pendencias_empresa pe
        WHERE pe.empresa = %s AND pe.documento = d.documento
    );
    """
    run_exec(sql, (empresa, empresa))

def seed_empresa_if_missing(empresa, agente):
    """Cria empresa em analise_credito se não existir + cria pendências padrão."""
    run_exec("""
        INSERT INTO analise_credito (empresa, agente, entrada, situacao)
        SELECT %s, %s, CURRENT_DATE, 'Em análise'
        WHERE NOT EXISTS (SELECT 1 FROM analise_credito WHERE empresa = %s);
    """, (empresa, agente, empresa))
    ensure_pendencias_empresa(empresa)

def kpi(label, value):
    st.markdown(f"""
        <div class="kpi-card">
          <h3>{value}</h3>
          <span>{label}</span>
        </div>
    """, unsafe_allow_html=True)

def conta_kpis(filtro_agente=None):
    where = "WHERE 1=1"
    params = []
    if filtro_agente:
        where += " AND agente = %s"
        params.append(filtro_agente)
    tot_emp = run_query_df(f"SELECT COUNT(*) FROM analise_credito {where}", params).iloc[0,0]
    aprov = run_query_df(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Aprovada'", params).iloc[0,0]
    reprov = run_query_df(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Reprovada'", params).iloc[0,0]

    where_p = "WHERE 1=1"
    params_p = []
    if filtro_agente:
        where_p += " AND empresa IN (SELECT empresa FROM analise_credito WHERE agente = %s)"
        params_p.append(filtro_agente)
    pend = run_query_df(f"SELECT COUNT(*) FROM pendencias_empresa {where_p} AND status='pendente'", params_p).iloc[0,0]
    return tot_emp, aprov, reprov, pend

def tabela_status_empresas(filtro_agente=None):
    where = ""
    params = []
    if filtro_agente:
        where = "WHERE ac.agente = %s"
        params = [filtro_agente]
    sql = f"""
    SELECT ac.empresa, ac.agente, ac.entrada, ac.situacao,
           COALESCE(ac.limite,0) AS limite,
           CASE WHEN ac.saida_credito IS NOT NULL THEN TO_CHAR(ac.saida_credito,'YYYY-MM-DD') ELSE 'Não' END AS saida_credito,
           (SELECT COUNT(*) FROM pendencias_empresa p WHERE p.empresa = ac.empresa AND p.status='pendente') AS pendentes_restantes
    FROM analise_credito ac
    {where}
    ORDER BY ac.entrada DESC, ac.empresa;
    """
    return run_query_df(sql, params)

def pendencias_df(empresa, apenas_pendentes=False):
    sql = """
        SELECT id, documento, status, data_ultima_atualizacao
        FROM pendencias_empresa
        WHERE empresa = %s
    """
    params = [empresa]
    if apenas_pendentes:
        sql += " AND status='pendente'"
    sql += " ORDER BY documento"
    return run_query_df(sql, params)

def atualizar_campos_empresa(empresa, payload):
    sets = []
    params = []
    for col, val in payload.items():
        sets.append(f"{col} = %s")
        params.append(val)
    params.append(empresa)
    run_exec(f"UPDATE analise_credito SET {', '.join(sets)} WHERE empresa = %s", params)

def atualizar_pendencias(empresa, updates):
    """
    updates: lista de tuplas (status, id)
    """
    if not updates: 
        return
    sql = """
       UPDATE pendencias_empresa
          SET status = %s, data_ultima_atualizacao = NOW()
        WHERE id = %s AND empresa = %s
    """
    params = [(stt, pid, empresa) for (pid, stt) in updates]
    run_exec(sql, params, many=True)

# =========================================================
# UI – HEADER + Tabs
# =========================================================
header()
st.sidebar.success(f"Olá, **{st.session_state.user}** ({st.session_state.tipo})")

if "tab" not in st.session_state:
    st.session_state.tab = "Overview"

colA, colB = st.columns(2)
with colA:
    if st.button("📊 Overview", use_container_width=True):
        st.session_state.tab = "Overview"
with colB:
    if st.button("🧠 Detalhada", use_container_width=True):
        st.session_state.tab = "Detalhada"

st.write("---")

# =========================================================
# OVERVIEW (Ambos)
# =========================================================
def overview(tipo, agente):
    filtro = agente if tipo == "comercial" else None

    # KPIs
    t, a, r, p = conta_kpis(filtro)
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Empresas", t)
    with k2: kpi("Aprovadas", a)
    with k3: kpi("Reprovadas", r)
    with k4: kpi("Pendências totais", p)

    st.markdown("#### Status das empresas")
    df = tabela_status_empresas(filtro)
    st.dataframe(df, use_container_width=True, height=280)

    # Detalhe de pendências por empresa (somente leitura)
    st.markdown("#### Selecione uma empresa para ver as pendências:")
    opts = df["empresa"].tolist()
    empresa_escolhida = st.selectbox("", ["—"] + opts, index=0)
    if empresa_escolhida and empresa_escolhida != "—":
        st.markdown(f"**Pendências da empresa _{empresa_escolhida}_**")
        dpend = pendencias_df(empresa_escolhida, apenas_pendentes=False)
        st.dataframe(dpend, use_container_width=True, height=360)

# =========================================================
# DETALHADA
# =========================================================
def detalhada(tipo, agente):
    # Comercial pode cadastrar empresa (opcional)
    if tipo == "comercial":
        with st.expander("➕ Cadastrar nova empresa", expanded=False):
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                nova_emp = st.text_input("Empresa")
            with c2:
                st.text_input("Agente", value=agente, disabled=True)
            if st.button("Cadastrar empresa", type="primary"):
                if nova_emp.strip():
                    seed_empresa_if_missing(nova_emp.strip(), agente)
                    st.success("Empresa cadastrada!")
                    st.rerun()
                else:
                    st.warning("Informe o nome da empresa.")

    # Escolha da empresa para edição/visualização
    df = tabela_status_empresas(None if tipo == "analista" else agente)
    if df.empty:
        st.info("Sem empresas para exibir.")
        return

    empresa = st.selectbox("Escolha a empresa:", df["empresa"].tolist())

    # Busca registro principal + garantimos pendências base
    ensure_pendencias_empresa(empresa)

    # Carrega dados atuais
    dados = run_query_df("SELECT * FROM analise_credito WHERE empresa = %s", (empresa,))
    if dados.empty:
        st.warning("Empresa não encontrada.")
        return
    row = dados.iloc[0].to_dict()

    st.markdown("### 🧰 Edição Completa" if tipo == "analista" else "### 📄 Detalhe da Empresa")

    # Formulário (analista pode editar tudo; comercial só vê, com campos bloqueados)
    editable = (tipo == "analista")
    col1, col2, col3 = st.columns([0.33, 0.34, 0.33])

    with col1:
        situacao = st.selectbox("Situação", SITUACOES, index=SITUACOES.index(row.get("situacao","Em análise")) if row.get("situacao") in SITUACOES else 0, disabled=not editable)
        limite = st.number_input("Limite (R$)", min_value=0.0, format="%.2f", value=float(row.get("limite") or 0), disabled=not editable)
        saida_credito = st.text_input("Saída Crédito (YYYY-MM-DD)", value=row.get("saida_credito") or "", disabled=not editable)

    with col2:
        comentario_interno = st.text_area("Comentário Interno", value=row.get("comentario_interno") or "", height=120, disabled=not editable)

    with col3:
        # Card de pendências
        pend_count = run_query_df(
            "SELECT COUNT(*) FROM pendencias_empresa WHERE empresa=%s AND status='pendente'",
            (empresa,)
        ).iloc[0,0]
        st.markdown(
            f"""
            <div class="kpi-card" style="margin-top:28px;">
              <h3>{pend_count}</h3>
              <span>Pendências (quantitativo)</span>
            </div>
            """, unsafe_allow_html=True
        )

    st.markdown("### ✅ Checklist Operacional")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        envio_das = st.selectbox("Envio DAS", SIM_NAO, index=SIM_NAO.index("Sim" if (row.get("envio_das") or "").lower()=="sim" else "Não"), disabled=not editable)
    with c2:
        emissao_contrato = st.selectbox("Emissão contrato", SIM_NAO, index=SIM_NAO.index("Sim" if (row.get("emissao_contrato") or "").lower()=="sim" else "Não"), disabled=not editable)
    with c3:
        assinatura = st.selectbox("Assinatura", SIM_NAO, index=SIM_NAO.index("Sim" if (row.get("assinatura") or "").lower()=="sim" else "Não"), disabled=not editable)
    with c4:
        homologacao = st.selectbox("Homologação", SIM_NAO, index=SIM_NAO.index("Sim" if (row.get("homologacao") or "").lower()=="sim" else "Não"), disabled=not editable)
    with c5:
        apto_a_operar = st.selectbox("Apto a operar", SIM_NAO, index=SIM_NAO.index("Sim" if (row.get("apto_a_operar") or "").lower()=="sim" else "Não"), disabled=not editable)

    # PENDÊNCIAS
    st.markdown("### 📎 Pendências")
    if tipo == "analista":
        st.caption("Marque **Recebido** quando o documento chegar.")
        ptable = pendencias_df(empresa, apenas_pendentes=False)
        # Criamos uma cópia para edição de status
        edit_status = []
        for _, r in ptable.iterrows():
            edit_status.append("Recebido" if r["status"] == "recebido" else "Pendente")

        df_edit = ptable.copy()
        df_edit["Status (editar)"] = edit_status

        # Editor simples por linha
        for idx in range(len(df_edit)):
            c1, c2, c3, c4 = st.columns([0.08, 0.52, 0.2, 0.2])
            c1.write(df_edit.loc[idx, "id"])
            c2.write(df_edit.loc[idx, "documento"])
            new_stat = c3.selectbox(
                "Status", ["Pendente","Recebido"],
                index=0 if df_edit.loc[idx, "Status (editar)"]=="Pendente" else 1,
                key=f"pend_{empresa}_{df_edit.loc[idx,'id']}"
            )
            c4.write(df_edit.loc[idx, "data_ultima_atualizacao"])
            df_edit.loc[idx, "Status (editar)"] = new_stat

        if st.button("💾 Salvar pendências", use_container_width=True, type="primary"):
            ups = []
            for i, r in df_edit.iterrows():
                novo = "pendente" if r["Status (editar)"] == "Pendente" else "recebido"
                if novo != ptable.loc[i, "status"]:
                    ups.append((r["id"], novo))
            if ups:
                atualizar_pendencias(empresa, [(pid, stt) for (pid, stt) in ups])
                st.success("Pendências atualizadas!")
                st.rerun()
            else:
                st.info("Nenhuma alteração a salvar.")
    else:
        # Comercial: somente leitura
        st.caption("Visualização somente leitura")
        dpend = pendencias_df(empresa, apenas_pendentes=False)
        st.dataframe(dpend, use_container_width=True, height=360)

    # SALVAR CAMPOS PRINCIPAIS (Analista)
    if editable:
        if st.button("💾 Salvar dados da empresa", type="primary", use_container_width=True):
            payload = {
                "situacao": situacao,
                "limite": limite,
                "comentario_interno": comentario_interno,
                "envio_das": envio_das,
                "emissao_contrato": emissao_contrato,
                "assinatura": assinatura,
                "homologacao": homologacao,
                "apto_a_operar": apto_a_operar,
            }
            # saída_crédito se estiver no formato válido
            try:
                if saida_credito.strip():
                    datetime.strptime(saida_credito.strip(), "%Y-%m-%d")
                    payload["saida_credito"] = saida_credito.strip()
                else:
                    payload["saida_credito"] = None
            except ValueError:
                st.warning("Data inválida em Saída Crédito (use YYYY-MM-DD).")
                st.stop()

            atualizar_campos_empresa(empresa, payload)
            st.success("Empresa atualizada!")
            st.rerun()

# =========================================================
# ROTEAMENTO
# =========================================================
if st.session_state.tab == "Overview":
    overview(st.session_state.tipo, st.session_state.agente)
else:
    detalhada(st.session_state.tipo, st.session_state.agente)
