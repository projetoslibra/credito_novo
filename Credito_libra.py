# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import psycopg2
import psycopg2.extras as pg_extras
from datetime import date, datetime

# =========================================================
# 🎨 PALETA / ESTILO
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
# 🧭 SIDEBAR (Logo + saudação)
# =========================================================
def sidebar_content():
    with st.sidebar:
        st.markdown(
            f"""
            <style>
            .logo-hover {{
                transition: all 0.3s ease-in-out;
                filter: drop-shadow(0px 0px 8px rgba(198,99,0,0.4));
                cursor: pointer;
            }}
            .logo-hover:hover {{
                transform: scale(1.06);
                filter: drop-shadow(0px 0px 12px rgba(198,99,0,0.7));
            }}
            </style>

            <div style="
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:center;
                margin-top:10px;
                margin-bottom:15px;">
                <img src="https://raw.githubusercontent.com/juancarneirolibra/assets/main/Capital-branca.png" class="logo-hover" width="150">
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

        if "user" in st.session_state:
            nome = st.session_state.get("user", "").capitalize()
            tipo = st.session_state.get("tipo", "")
            st.success(f"Olá, **{nome}** ({tipo})")
            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)

# =========================================================
# 🏷 HEADER CENTRALIZADO
# =========================================================
def header():
    st.markdown(
        f"""
        <div style="
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.8rem;
            padding-top: 25px;
            padding-bottom: 25px;
        ">
            <span style='
                color:{HONEYDEW};
                font-size: 1.8rem;
                font-weight:900;
                letter-spacing:0.02em;
                border-bottom: 2px solid {HARVEST_GOLD}80;
                padding-bottom: 0.1em;
                text-shadow: 0px 0px 8px rgba(255,255,255,0.1);
            '>LIBRA CAPITAL</span>
            <span style='font-weight:400; color:{HARVEST_GOLD}; font-size: 1.3rem;'>| Análise de Crédito</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("<div style='margin-bottom: 1.5rem;'></div>", unsafe_allow_html=True)

# =========================================================
# 🌑 CSS GLOBAL
# =========================================================
st.markdown(
    f"""
    <style>
      html, body, [data-testid="stAppViewContainer"], [data-testid="stSidebar"], [data-testid="stHeader"] {{
        background-color: #061e26 !important;
        color: {HONEYDEW} !important;
      }}
      * {{ color-scheme: dark !important; }}
      .block-container {{ padding-top: 1.2rem; }}
      .kpi-card {{
        background: {HARVEST_GOLD}22;
        border: 1px solid {HARVEST_GOLD}55;
        color: {HONEYDEW};
        padding: 12px 14px; border-radius: 10px; text-align: center;
      }}
      .kpi-card h3 {{ margin: 0; font-size: 1.7rem; color: {HONEYDEW}; }}
      .kpi-card span {{ font-size: .9rem; color: {SLATE_GRAY}; }}
      .stDataFrame, .stTable, .stMarkdown, .stText {{
        color: {HONEYDEW} !important;
      }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================================================
# 🗄️ BANCO DE DADOS
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
    return pd.read_sql(sql, conn, params=params)

def run_exec(sql, params=None, many=False):
    conn = get_conn()
    with conn, conn.cursor(cursor_factory=pg_extras.RealDictCursor) as cur:
        if many:
            cur.executemany(sql, params)
        else:
            cur.execute(sql, params)
    conn.commit()

# índices úteis (roda uma vez)
@st.cache_resource(show_spinner=False)
def ensure_indexes():
    ddl = [
        "CREATE INDEX IF NOT EXISTS idx_ac_empresa ON analise_credito(empresa)",
        "CREATE INDEX IF NOT EXISTS idx_ac_agente  ON analise_credito(agente)",
        "CREATE INDEX IF NOT EXISTS idx_pe_empresa ON pendencias_empresa(empresa)",
        "CREATE INDEX IF NOT EXISTS idx_pe_status  ON pendencias_empresa(status)",
        "CREATE INDEX IF NOT EXISTS idx_pe_doc     ON pendencias_empresa(documento)"
    ]
    for q in ddl:
        try:
            run_exec(q)
        except Exception:
            pass
ensure_indexes()

def registrar_transicao(empresa, nova_etapa, novo_responsavel, prazo_dias):
    """Registra transição de etapa e atualiza status atual."""
    try:
        status_prazo = "Dentro do prazo" if prazo_dias and prazo_dias > 0 else "Sem prazo"
        run_exec("""
            INSERT INTO log_workflow (empresa, etapa, responsavel, prazo_dias, status_prazo)
            VALUES (%s, %s, %s, %s, %s);
        """, (empresa, nova_etapa, novo_responsavel, prazo_dias, status_prazo))
        run_exec("""
            UPDATE analise_credito
               SET etapa_atual = %s,
                   responsavel_atual = %s,
                   data_ultima_movimentacao = NOW()
             WHERE empresa = %s;
        """, (nova_etapa, novo_responsavel, empresa))
    except Exception as e:
        st.error(f"Erro ao registrar transição: {e}")

# =========================================================
# 🔐 LOGIN / SESSÃO
# =========================================================
USERS = {
    # === COMERCIAIS ===
    "gabriel":  {"senha": "Gabriel33",  "tipo": "comercial", "agente": "Gabriel"},
    "marcelo":  {"senha": "Marcelo33",  "tipo": "comercial", "agente": "Marcelo"},
    "lilian":   {"senha": "Lilian33",   "tipo": "comercial", "agente": "Lilian"},
    "heverton": {"senha": "Heverton33", "tipo": "comercial", "agente": "Heverton"},
    "moacir":   {"senha": "Moacir33",   "tipo": "comercial", "agente": "Moacir"},
    "ellen":    {"senha": "Ellen33",    "tipo": "comercial", "agente": "Ellen"},
    "jose":     {"senha": "Jose33",     "tipo": "comercial", "agente": "Jose"},
    "sayonara": {"senha": "Sayonara33", "tipo": "comercial", "agente": "Sayonara"},
    "joao":     {"senha": "Joao33",     "tipo": "comercial", "agente": "Joao"},
    "andressa": {"senha": "Andressa33", "tipo": "comercial", "agente": "Andressa"},
    # === ANALISTAS / LIDERANÇA ===
    "leonardo": {"senha": "Leonardo13", "tipo": "Diretor", "agente": None},
    "rafael":   {"senha": "Rafael13",   "tipo": "analista", "agente": None},
    "breno":    {"senha": "Breno13",    "tipo": "CEO", "agente": None},
}

def login_box():
    with st.sidebar:
        st.markdown("## Login")
        u = st.text_input("Usuário")
        p = st.text_input("Senha", type="password")
        if st.button("Entrar", use_container_width=True):
            key = (u or "").strip().lower()
            if key in USERS and USERS[key]["senha"] == p:
                st.session_state.user = key
                st.session_state.tipo = USERS[key]["tipo"]
                st.session_state.agente = USERS[key]["agente"]
                st.rerun()
            else:
                st.error("Usuário/senha inválidos")

if "user" not in st.session_state:
    header()
    login_box()
    st.stop()

# =========================================================
# ⚙️ FUNÇÕES DE NEGÓCIO
# =========================================================
SITUACOES = ["Em análise", "Aprovada", "Reprovada", "Stand by"]
SIM_NAO = ["Não", "Sim"]

def _norm_status(s):
    s = (s or "").strip().lower()
    return "recebido" if s in ("recebido", "ok", "entregue", "sim", "true") else "pendente"

def ensure_pendencias_empresa(empresa):
    run_exec("""
        INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
        SELECT %s, d.documento, 'pendente', NOW()
        FROM dim_pendencias d
        WHERE NOT EXISTS (
            SELECT 1 FROM pendencias_empresa pe
            WHERE pe.empresa = %s AND pe.documento = d.documento
        );
    """, (empresa, empresa))

def seed_empresa_if_missing(empresa, agente):
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
    aprov  = run_query_df(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Aprovada'", params).iloc[0,0]
    reprov = run_query_df(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Reprovada'", params).iloc[0,0]

    where_p = "WHERE 1=1"
    params_p = []
    if filtro_agente:
        where_p += " AND empresa IN (SELECT empresa FROM analise_credito WHERE agente = %s)"
        params_p.append(filtro_agente)
    pend = run_query_df(f"SELECT COUNT(*) FROM pendencias_empresa {where_p} AND status='pendente'", params_p).iloc[0,0]
    return tot_emp, aprov, reprov, pend

def tabela_status_empresas(filtro_agente=None):
    where, params = "", []
    if filtro_agente:
        where = "WHERE ac.agente = %s"
        params = [filtro_agente]
    # inclui prazo atual (último do log) via subselect
    sql = f"""
    SELECT
        ac.empresa,
        ac.agente,
        TO_CHAR(ac.entrada,'DD/MM/YYYY') AS entrada,
        ac.situacao,
        COALESCE(ac.limite,0) AS limite,
        ac.etapa_atual,
        ac.responsavel_atual,
        TO_CHAR(ac.data_ultima_movimentacao,'DD/MM/YYYY') AS ultima_movimentacao,
        (SELECT prazo_dias
           FROM log_workflow lw
          WHERE lw.empresa = ac.empresa
          ORDER BY lw.created_at DESC
          LIMIT 1) AS prazo_dias,
        (SELECT COUNT(*)
           FROM pendencias_empresa p
          WHERE p.empresa = ac.empresa
            AND p.status='pendente') AS pendentes_restantes
    FROM analise_credito ac
    {where}
    ORDER BY ac.entrada DESC, ac.empresa;
    """
    return run_query_df(sql, params)

def pendencias_df(empresa, apenas_pendentes=False):
    sql = "SELECT id, documento, status, data_ultima_atualizacao FROM pendencias_empresa WHERE empresa = %s"
    params = [empresa]
    if apenas_pendentes:
        sql += " AND status='pendente'"
    sql += " ORDER BY documento"
    return run_query_df(sql, params)

def atualizar_campos_empresa(empresa, payload):
    sets, params = [], []
    for col, val in payload.items():
        sets.append(f"{col} = %s")
        params.append(val)
    params.append(empresa)
    run_exec(f"UPDATE analise_credito SET {', '.join(sets)} WHERE empresa = %s", params)

def atualizar_pendencias(empresa, updates):
    if not updates:
        return
    sql = """
       UPDATE pendencias_empresa
          SET status = %s, data_ultima_atualizacao = NOW()
        WHERE id = %s AND empresa = %s
    """
    params = [(_norm_status(stt), pid, empresa) for (pid, stt) in updates]
    run_exec(sql, params, many=True)

def calcular_status_prazo(data_str_ddmmyyyy, prazo_dias):
    if not data_str_ddmmyyyy or not prazo_dias:
        return "Sem prazo"
    try:
        dt = datetime.strptime(data_str_ddmmyyyy, "%d/%m/%Y")
    except Exception:
        return "Sem prazo"
    limite = dt + pd.Timedelta(days=int(prazo_dias))
    return "Atrasado" if datetime.now() > limite.to_pydatetime() else "Dentro do prazo"

# =========================================================
# OVERVIEW
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

    # Calcula status de prazo (com base na última movimentação + prazo_dias do log)
    if not df.empty:
        df = df.copy()
        df["status_prazo"] = df.apply(
            lambda r: calcular_status_prazo(r.get("ultima_movimentacao"), r.get("prazo_dias")),
            axis=1
        )

    # Visual diferente por perfil
    if tipo != "comercial":
        st.caption("📌 Exibindo etapa, responsável, prazo e status de prazo")
        cols = ["empresa","agente","situacao","etapa_atual","responsavel_atual","prazo_dias","status_prazo","ultima_movimentacao","pendentes_restantes"]
        show_cols = [c for c in cols if c in df.columns]
        st.dataframe(df[show_cols], use_container_width=True, height=300)
    else:
        st.dataframe(df[["empresa","agente","situacao","entrada"]], use_container_width=True, height=300)

    # Detalhe de pendências por empresa (somente leitura)
    st.markdown("#### Selecione uma empresa para ver as pendências:")
    opts = df["empresa"].tolist() if not df.empty else []
    empresa_escolhida = st.selectbox("", ["—"] + opts, index=0)
    if empresa_escolhida and empresa_escolhida != "—":
        st.markdown(f"**Pendências da empresa _{empresa_escolhida}_**")
        only_pend = (tipo == "comercial")
        dpend = pendencias_df(empresa_escolhida, apenas_pendentes=only_pend)
        st.dataframe(dpend, use_container_width=True, height=360)

# =========================================================
# DETALHADA
# =========================================================
def detalhada(tipo, agente):
    # Comercial pode cadastrar empresa
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
                    # inicia o fluxo marcando pendência de posicionamento
                    registrar_transicao(nova_emp.strip(), "Pendência de Posicionamento", "Analista", 1)
                    st.success("Empresa cadastrada e fluxo iniciado!")
                    st.rerun()
                else:
                    st.warning("Informe o nome da empresa.")

    # Escolha da empresa
    df = tabela_status_empresas(None if tipo != "comercial" else agente)
    if df.empty:
        st.info("Sem empresas para exibir.")
        return

    empresa = st.selectbox("Escolha a empresa:", df["empresa"].tolist())

    # Garante pendências base
    ensure_pendencias_empresa(empresa)

    # Carrega dados atuais
    dados = run_query_df("SELECT * FROM analise_credito WHERE empresa = %s", (empresa,))
    if dados.empty:
        st.warning("Empresa não encontrada.")
        return
    row = dados.iloc[0].to_dict()

    st.markdown("### 🧰 Edição Completa" if tipo != "comercial" else "### 📄 Detalhe da Empresa")

    # Formulário (analista/liderança pode editar; comercial só vê)
    editable = (tipo in ["analista", "Diretor", "CEO"])
    col1, col2, col3 = st.columns([0.33, 0.34, 0.33])

    with col1:
        situacao = st.selectbox(
            "Situação",
            SITUACOES,
            index=SITUACOES.index(row.get("situacao","Em análise")) if row.get("situacao") in SITUACOES else 0,
            disabled=not editable
        )
        limite = st.number_input("Limite (R$)", min_value=0.0, format="%.2f", value=float(row.get("limite") or 0), disabled=not editable)
        saida_credito = st.text_input("Saída Crédito (DD-MM-YYYY)", value=(row.get("saida_credito") or ""), disabled=not editable)

    with col2:
        comentario_interno = st.text_area("Comentário Interno", value=row.get("comentario_interno") or "", height=120, disabled=not editable)

    with col3:
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
    if editable:
        st.caption("Marque **Recebido** quando o documento chegar.")
        ptable = pendencias_df(empresa, apenas_pendentes=False)
        df_edit = ptable.copy()
        for i, r in df_edit.iterrows():
            c1x, c2x, c3x, c4x = st.columns([0.08, 0.52, 0.2, 0.2])
            c1x.write(int(r["id"]))
            c2x.write(r["documento"])
            novo = c3x.selectbox(
                "Status",
                ["Pendente","Recebido"],
                index=(0 if r["status"]!="recebido" else 1),
                key=f"pend_{empresa}_{int(r['id'])}"
            )
            c4x.write(r["data_ultima_atualizacao"])
            df_edit.loc[i, "status"] = "recebido" if novo == "Recebido" else "pendente"

        if st.button("💾 Salvar pendências", use_container_width=True, type="primary"):
            ups = []
            for i, r in df_edit.iterrows():
                if r["status"] != ptable.loc[i,"status"]:
                    ups.append( (int(r["id"]), r["status"]) )
            if ups:
                atualizar_pendencias(empresa, ups)
                st.success("Pendências atualizadas!")
                st.rerun()
            else:
                st.info("Nenhuma alteração a salvar.")
    else:
        st.caption("Visualização somente leitura")
        dpend = pendencias_df(empresa, apenas_pendentes=True)
        st.dataframe(dpend, use_container_width=True, height=360)

    # SALVAR CAMPOS PRINCIPAIS (Analista / Liderança)
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
            if saida_credito and saida_credito.strip():
                try:
                    data_formatada = datetime.strptime(saida_credito.strip(), "%d-%m-%Y").date()
                    payload["saida_credito"] = data_formatada
                except ValueError:
                    st.warning("Data inválida em Saída Crédito (use DD-MM-YYYY).")
                    st.stop()
            else:
                payload["saida_credito"] = None

            try:
                atualizar_campos_empresa(empresa, payload)
                st.success("Empresa atualizada com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao salvar no banco: {e}")

# =========================================================
# 🧭 WORKFLOW – nova aba dedicada
# =========================================================
def workflow(tipo, agente):
    st.markdown("## 🧭 Controle de Workflow")
    st.caption("Gerencie as etapas, prazos e responsáveis das análises de crédito de forma visual e organizada.")

    # 🔹 Escolha da empresa
    df_emp = run_query_df("SELECT empresa, etapa_atual, responsavel_atual FROM analise_credito ORDER BY empresa")
    if df_emp.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
        return

    empresa = st.selectbox("Selecione uma empresa", df_emp["empresa"].tolist())
    dados = run_query_df("SELECT * FROM analise_credito WHERE empresa = %s", (empresa,))
    row = dados.iloc[0].to_dict()

    # 🔹 Cabeçalho informativo
    st.markdown(f"""
    <div style="background:#0b2e39;padding:14px;border-radius:10px;border:1px solid #0e3a47;">
        <h3 style="margin:0;">🏢 {empresa}</h3>
        <p style="margin:4px 0 0 0;">
        <b>Etapa atual:</b> {row.get('etapa_atual','Cadastro')} |
        <b>Responsável:</b> {row.get('responsavel_atual','Analista')} |
        <b>Última atualização:</b> {row.get('data_ultima_movimentacao')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 🔹 Linha do tempo visual (Timeline)
    etapas = [
        "Cadastro", "Pendência de Posicionamento", "Aguardando Documentos", "Em Análise",
        "Aguardando Documentos Finais", "Elaboração Contrato", "Assinatura Cliente",
        "Formalização Gestora", "Finalizado"
    ]
    etapa_atual = row.get("etapa_atual", "Cadastro")
    st.markdown("### 📜 Etapas do Processo")
    timeline = []
    for e in etapas:
        if e == etapa_atual:
            timeline.append(f"<span style='color:#C66300;font-weight:700;'>🟡 {e}</span>")
        elif etapas.index(e) < etapas.index(etapa_atual):
            timeline.append(f"<span style='color:#00C853;font-weight:600;'>🟢 {e}</span>")
        else:
            timeline.append(f"<span style='color:#546E7A;'>⚪ {e}</span>")
    st.markdown(" → ".join(timeline), unsafe_allow_html=True)

    # 🔹 Atualização de Workflow (somente analista ou diretor)
    if tipo in ["analista", "Diretor", "CEO"]:
        st.markdown("### 🔄 Atualizar Workflow")
        nova_etapa = st.selectbox("Nova Etapa", etapas, index=etapas.index(etapa_atual))
        novo_resp = st.selectbox("Novo Responsável", ["Analista", "Comercial", "Gestora"])
        prazo_dias = st.number_input("Prazo (dias)", min_value=0, step=1, value=2)

        if st.button("💾 Registrar Transição", use_container_width=True, type="primary"):
            try:
                registrar_transicao(empresa, nova_etapa, novo_resp, prazo_dias)
                st.success(f"✅ Etapa '{nova_etapa}' atualizada com sucesso! Responsável: {novo_resp}")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao registrar transição: {e}")

    # 🔹 Histórico de movimentações
    df_log = run_query_df("""
        SELECT etapa, responsavel, created_at, prazo_dias, status_prazo
        FROM log_workflow
        WHERE empresa = %s
        ORDER BY created_at DESC;
    """, (empresa,))
    st.markdown("### 🕒 Histórico de Movimentações")
    if df_log.empty:
        st.info("Nenhuma transição registrada ainda.")
    else:
        st.dataframe(df_log, use_container_width=True, height=300)

        # 🗑️ EXCLUSÃO (somente analista)
        if tipo == "analista":
            st.markdown("---")
            st.warning("⚠️ Esta ação é irreversível. Confirme antes de excluir a empresa.", icon="⚠️")
            confirmar = st.checkbox(f"Confirmo que desejo excluir permanentemente '{empresa}'")
            if confirmar:
                if st.button(f"🗑️ Excluir empresa '{empresa}'", type="secondary", use_container_width=True):
                    try:
                        run_exec("DELETE FROM pendencias_empresa WHERE empresa = %s", (empresa,))
                        run_exec("DELETE FROM log_workflow WHERE empresa = %s", (empresa,))
                        run_exec("DELETE FROM analise_credito WHERE empresa = %s", (empresa,))
                        st.success(f"✅ Empresa '{empresa}' e seus registros foram removidos com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao excluir empresa: {e}")
            else:
                st.info("Marque a caixa de confirmação para habilitar o botão de exclusão.")

# =========================================================
# 📊 INTERFACE E ROTEAMENTO FINAL
# =========================================================
header()
sidebar_content()

if "tab" not in st.session_state:
    st.session_state.tab = "Overview"

colA, colB, colC = st.columns(3)
with colA:
    if st.button("📊 Overview", use_container_width=True):
        st.session_state.tab = "Overview"
with colB:
    if st.button("🧠 Detalhada", use_container_width=True):
        st.session_state.tab = "Detalhada"
with colC:
    if st.button("🧭 Workflow", use_container_width=True):
        st.session_state.tab = "Workflow"

if st.session_state.tab == "Overview":
    overview(st.session_state.tipo, st.session_state.agente)
elif st.session_state.tab == "Detalhada":
    detalhada(st.session_state.tipo, st.session_state.agente)
else:
    workflow(st.session_state.tipo, st.session_state.agente)
