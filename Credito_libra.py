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
      /* Progress bar discreta no rodapé do card */
      .prog-wrap {{
        width: 100%;
        height: 8px;
        border-radius: 999px;
        background: rgba(255,255,255,0.06);
        border: 1px solid rgba(255,255,255,0.08);
        overflow: hidden;
      }}
      .prog-fill {{
        height: 100%;
        transition: width .45s ease;
      }}
      .chip {{
        padding:3px 10px;border-radius:12px;background:{HARVEST_GOLD}22;border:1px solid {HARVEST_GOLD}55;
      }}
    </style>
    """,
    unsafe_allow_html=True
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
# 🗄️ BANCO DE DADOS
# =========================================================
DB_CONFIG = {
    "host": st.secrets["db_host"],
    "port": st.secrets["db_port"],
    "dbname": st.secrets["db_name"],
    "user": st.secrets["db_user"],
    "password": st.secrets["db_password"],
}

def safe_int(value, default=0):
    try:
        if value is None or str(value).strip() in ["", "None", "nan", "NaN", "NoneType"]:
            return default
        return int(float(value))
    except Exception:
        return default

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
    """
    Registra uma nova transição no fluxo de crédito.
    - Garante que os dados da etapa atual sejam atualizados.
    - Registra histórico completo no log_workflow.
    - Mantém data_ultima_movimentacao sincronizada.
    """
    try:
        # 🧩 Conversão segura do prazo
        try:
            prazo_int = int(float(prazo_dias)) if str(prazo_dias).strip() not in ["", "None", "nan", "NaN"] else 0
        except Exception:
            prazo_int = 0

        # 🕒 Status de prazo inicial
        status_prazo = "Dentro do prazo" if prazo_int > 0 else "Sem prazo"

        # 💾 Registro no log_workflow
        run_exec("""
            INSERT INTO log_workflow (empresa, etapa, responsavel, prazo_dias, status_prazo, created_at)
            VALUES (%s, %s, %s, %s, %s, NOW());
        """, (empresa, nova_etapa, novo_responsavel, prazo_int, status_prazo))

        # 🔄 Atualização na tabela principal
        run_exec("""
            UPDATE analise_credito
               SET etapa_atual = %s,
                   responsavel_atual = %s,
                   data_ultima_movimentacao = NOW()
             WHERE empresa = %s;
        """, (nova_etapa, novo_responsavel, empresa))

        st.toast(
            f"🚀 Etapa '{nova_etapa}' registrada com sucesso! Responsável: {novo_responsavel} | Prazo: {prazo_int} dia(s)",
            icon="✅"
        )

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

# =========================================================
# ⚙️ FUNÇÕES DE NEGÓCIO / HELPERS
# =========================================================
SITUACOES = ["Em análise", "Aprovada", "Reprovada", "Stand by"]
SIM_NAO = ["Não", "Sim"]

def _norm_status(s):
    s = (s or "").strip().lower()
    return "recebido" if s in ("recebido", "ok", "entregue", "sim", "true") else "pendente"

def ensure_pendencias_empresa(empresa):
    """Garante que todos os documentos da DIM_PENDENCIAS existam na pendencias_empresa."""
    try:
        sql = f"""
        INSERT INTO pendencias_empresa (empresa, documento, status, data_ultima_atualizacao)
        SELECT %s, d.documento, 'pendente', NOW()
          FROM dim_pendencias d
         WHERE NOT EXISTS (
               SELECT 1 FROM pendencias_empresa pe
                WHERE pe.empresa = %s
                  AND pe.documento = d.documento
         );
        """
        run_exec(sql, [str(empresa).strip(), str(empresa).strip()])
    except Exception as e:
        st.error(f"Erro ao garantir pendências: {e}")

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

def safe_count(sql, params=None):
    df = run_query_df(sql, params)
    return int(df.iloc[0, 0]) if not df.empty else 0

def conta_kpis(filtro_agente=None):
    where = "WHERE 1=1"
    params = []
    if filtro_agente:
        where += " AND agente = %s"
        params.append(filtro_agente)

    tot_emp = safe_count(f"SELECT COUNT(*) FROM analise_credito {where}", params)
    aprov  = safe_count(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Aprovada'", params)
    reprov = safe_count(f"SELECT COUNT(*) FROM analise_credito {where} AND situacao='Reprovada'", params)

    where_p = "WHERE 1=1"
    params_p = []
    if filtro_agente:
        where_p += " AND empresa IN (SELECT empresa FROM analise_credito WHERE agente = %s)"
        params_p.append(filtro_agente)
    pend = safe_count(f"SELECT COUNT(*) FROM pendencias_empresa {where_p} AND status='pendente'", params_p)
    return tot_emp, aprov, reprov, pend

def tabela_status_empresas(filtro_agente=None, data_ini=None, data_fim=None):
    wheres, params = [], []
    if filtro_agente:
        wheres.append("ac.agente = %s")
        params.append(filtro_agente)
    if data_ini:
        wheres.append("ac.entrada >= %s")
        params.append(data_ini)
    if data_fim:
        wheres.append("ac.entrada <= %s")
        params.append(data_fim)

    where_sql = f"WHERE {' AND '.join(wheres)}" if wheres else ""

    sql = f"""
    SELECT
    ac.empresa,
    ac.agente,
    ac.entrada,
    ac.situacao,
    COALESCE(ac.limite,0) AS limite,
    ac.etapa_atual,
    ac.responsavel_atual,
    ac.data_ultima_movimentacao,

    -- 🔹 Campo novo essencial pra barrinha funcionar
    (SELECT created_at
       FROM log_workflow lw
      WHERE lw.empresa = ac.empresa
      ORDER BY lw.created_at DESC
      LIMIT 1) AS ultima_transicao_em,

    -- 🔹 Prazo mais recente do workflow
    (SELECT prazo_dias
       FROM log_workflow lw
      WHERE lw.empresa = ac.empresa
      ORDER BY lw.created_at DESC
      LIMIT 1) AS prazo_dias,

    -- 🔹 Quantidade de pendências abertas
    (SELECT COUNT(*)
       FROM pendencias_empresa p
      WHERE p.empresa = ac.empresa
        AND p.status='pendente') AS pendentes_restantes

    FROM analise_credito ac
    {where_sql}
    ORDER BY ac.entrada DESC, ac.empresa;
     """
    df = run_query_df(sql, params)
    if not df.empty:
        try:
            df["entrada_fmt"] = pd.to_datetime(df["entrada"]).dt.strftime("%d/%m/%Y")
        except Exception:
            df["entrada_fmt"] = df["entrada"].astype(str)

        try:
            df["ultima_movimentacao_fmt"] = pd.to_datetime(df["data_ultima_movimentacao"]).dt.strftime("%d/%m/%Y")
        except Exception:
            df["ultima_movimentacao_fmt"] = df["data_ultima_movimentacao"].astype(str)
    return df

def listar_agentes():
    try:
        d = run_query_df("SELECT DISTINCT agente FROM analise_credito WHERE agente IS NOT NULL ORDER BY agente")
        ops = d["agente"].dropna().tolist()
        return ["Todos"] + ops if ops else ["Todos"]
    except Exception:
        return ["Todos"]

def pendencias_df(empresa, apenas_pendentes=False):
    sql = "SELECT id, documento, status, data_ultima_atualizacao FROM pendencias_empresa WHERE empresa = %s"
    params = [empresa]
    if apenas_pendentes:
        sql += " AND status='pendente'"
    sql += " ORDER BY documento"
    return run_query_df(sql, params)

def atualizar_campos_empresa(empresa, payload):
    """Atualiza campos arbitrários em analise_credito com segurança."""
    if not payload:
        return
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
    if not data_str_ddmmyyyy or prazo_dias in [None, "", " ", 0]:
        return "Sem prazo"
    try:
        prazo_int = int(float(prazo_dias)) if str(prazo_dias).strip() else 0
    except ValueError:
        prazo_int = 0
    if prazo_int <= 0:
        return "Sem prazo"

    try:
        dt = datetime.strptime(str(data_str_ddmmyyyy), "%d/%m/%Y")
    except Exception:
        return "Sem prazo"

    limite = pd.Timestamp(dt) + pd.Timedelta(days=prazo_int)
    if hasattr(limite, "to_pydatetime"):
        limite = limite.to_pydatetime()
    return "Atrasado" if datetime.now() > limite else "Dentro do prazo"

def calcular_progresso(prazo_dias, ultima_transicao_em):
    """
    Retorna (percentual, cor_hex, dias_restantes, status_avaliado)
    - percentual: 0..100
    - cor: verde / amarelo / vermelho conforme % e atraso
    """
    try:
        p = int(float(prazo_dias)) if str(prazo_dias).strip() not in ["", "None", "nan", "NaN"] else 0
    except Exception:
        p = 0

    if not ultima_transicao_em or p <= 0:
        return 0, "#2E7D32", None, "Sem prazo"  # verde discreto

    try:
        start = pd.to_datetime(ultima_transicao_em)
    except Exception:
        return 0, "#2E7D32", None, "Sem prazo"

    hoje = pd.Timestamp.now()
    dias_passados = max(0, (hoje.normalize() - start.normalize()).days)
    dias_restantes = p - dias_passados
    frac = dias_passados / p if p > 0 else 0
    perc = max(0, min(1, frac)) * 100

    if dias_restantes < 0:
        # atrasado
        return 100, "#C62828", dias_restantes, "Atrasado"
    elif perc >= 80:
        return perc, "#F9A825", dias_restantes, "Dentro do prazo"
    else:
        return perc, "#2E7D32", dias_restantes, "Dentro do prazo"

# =========================================================
# OVERVIEW (Cards + filtros + botão "Ver no Workflow")
# =========================================================

def overview(tipo, agente_logado):
    st.markdown("### 🎛️ Filtros")
    c1, c2, c3, c4 = st.columns([0.25, 0.25, 0.25, 0.25])

    with c1:
        agentes = listar_agentes()
        idx_ag = 0
        if tipo == "comercial" and agente_logado in agentes:
            idx_ag = agentes.index(agente_logado)
        agente_sel = st.selectbox("Comercial", agentes, index=idx_ag)
        filtro_agente = None if agente_sel == "Todos" else agente_sel
        if tipo == "comercial":
            filtro_agente = agente_logado  # força filtro do comercial logado

    with c2:
        data_inicio = st.date_input("Data inicial", value=pd.Timestamp.today() - pd.Timedelta(days=30), format="DD/MM/YYYY")

    with c3:
        data_fim = st.date_input("Data final", value=pd.Timestamp.today(), format="DD/MM/YYYY")

    with c4:
        modo_tabela = st.toggle("Modo tabela", value=False, help="Alterna para a visão tabular clássica")

    # KPIs
    t, a, r, p = conta_kpis(filtro_agente)
    k1, k2, k3, k4 = st.columns(4)
    with k1: kpi("Empresas", t)
    with k2: kpi("Aprovadas", a)
    with k3: kpi("Reprovadas", r)
    with k4: kpi("Pendências totais", p)

    # Dados
    df = tabela_status_empresas(
        filtro_agente=filtro_agente,
        data_ini=pd.to_datetime(data_inicio).date(),
        data_fim=pd.to_datetime(data_fim).date()
    )
    if df.empty:
        st.info("Sem empresas no período/filtro selecionado.")
        return

    # status_prazo calculado a partir da última movimentação + prazo_dias
    df = df.copy()
    df["status_prazo"] = df.apply(
        lambda r: calcular_status_prazo(
            (pd.to_datetime(r.get("data_ultima_movimentacao")).strftime("%d/%m/%Y")
             if pd.notnull(r.get("data_ultima_movimentacao")) else None),
            r.get("prazo_dias")
        ),
        axis=1
    )

    # === Tabela clássica ===
    if modo_tabela:
        cols = ["empresa","agente","situacao","etapa_atual","responsavel_atual",
                "prazo_dias","status_prazo","entrada_fmt","ultima_movimentacao_fmt",
                "pendentes_restantes","limite"]
        show = [c for c in cols if c in df.columns]
        st.dataframe(df[show], use_container_width=True, height=min(640, 80 + len(df)*28))
        return

    # === Cards (visão visual e organizada) ===
    st.markdown("### 📋 Empresas (visão compacta)")
    n_cols = 3
    rows = (len(df) + n_cols - 1) // n_cols

    for r in range(rows):
        cols = st.columns(n_cols)
        for i in range(n_cols):
            idx = r * n_cols + i
            if idx >= len(df):
                break
            row = df.iloc[idx]

            # chips e campos
            etapa = row.get("etapa_atual") or "—"
            resp = row.get("responsavel_atual") or "—"
            pend = safe_int(row.get("pendentes_restantes"))
            prazo = safe_int(row.get("prazo_dias"))
            entrada = row.get("entrada_fmt") or "—"
            ult = row.get("ultima_movimentacao_fmt") or "—"
            limite = float(row.get("limite") or 0.0)
            agente = row.get("agente") or "—"

            # 🔄 Converte a data de última transição em datetime
            ultima_transicao = row.get("ultima_transicao_em")
            if pd.notnull(ultima_transicao) and ultima_transicao not in [None, "None", "NaT", ""]:
                try:
                    ultima_transicao = pd.to_datetime(ultima_transicao)
                except Exception:
                    ultima_transicao = None
            else:
                ultima_transicao = None

            # 🚦 Calcula progresso e status com base no prazo e última transição
            perc, cor_barra, dias_rest, status_calc = calcular_progresso(
                safe_int(row.get("prazo_dias")),
                ultima_transicao
            )

            # 🟡 Chip de status
            status_chip = (
                "🔴 Atrasado" if status_calc == "Atrasado"
                else ("🟢 Dentro do prazo" if status_calc == "Dentro do prazo" else "⚪ Sem prazo")
            )

            # ⏱ Label de prazo
            if dias_rest is None:
                prazo_label = "—"
            elif dias_rest < 0:
                prazo_label = f"⚠️ Atrasado {abs(dias_rest)}d"
            else:
                prazo_label = f"D-{dias_rest}"

            with cols[i]:
                st.markdown(f"""
                <div style="background:linear-gradient(135deg, #0b2e39 0%, #07323f 100%);
                            border:1px solid #104052;
                            border-radius:14px;
                            padding:16px 18px;
                            margin-bottom:12px;
                            box-shadow:0 2px 6px rgba(0,0,0,0.25);">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <div style="font-weight:800;font-size:1.1rem;color:#FFF4E3;">{row['empresa']}</div>
                        <div style="font-size:.85rem;color:#717c89">👤 <b>{agente}</b></div>
                    </div>
                    <div style="margin-top:8px;font-size:.9rem;color:#FFF4E3CC;">
                        <div>📍 Etapa: <b>{etapa}</b> | Resp.: <b>{resp}</b></div>
                        <div>📅 Entrada: <b>{entrada}</b> | Última mov.: <b>{ult}</b></div>
                        <div>🧾 Pendências: <b>{pend}</b> | ⏱ Prazo: <b>{prazo}</b> dias | <b>{prazo_label}</b></div>
                        <div>💰 Limite: <b>R$ {limite:,.2f}</b></div>
                    </div>
                    <div style="margin-top:10px;">
                        <div class="prog-wrap">
                            <div class="prog-fill" style="width:{min(perc,100):.0f}%; background:{cor_barra};"></div>
                        </div>
                        <div style="margin-top:6px; display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:.8rem; color:#717c89">{min(perc,100):.0f}% do prazo</span>
                            <span class="chip">{status_chip}</span>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # 📎 Expander com pendências
                with st.expander("Ver pendências"):
                    dpend = pendencias_df(row["empresa"], apenas_pendentes=(tipo == "comercial"))
                    st.dataframe(dpend, use_container_width=True, height=200)

                # 🧭 Botão direto pro Workflow
                if st.button(f"🧭 Ver no Workflow — {row['empresa']}", key=f"go_{row['empresa']}"):
                    st.session_state.selected_empresa = row["empresa"]
                    st.session_state.tab = "Workflow"
                    st.rerun()

# =========================================================
# DETALHADA
# =========================================================
def detalhada(tipo, agente):
    # Comercial pode cadastrar empresa
    if tipo == "comercial":
        with st.expander("➕ Cadastrar nova empresa", expanded=False):
            c1, c2 = st.columns([0.6, 0.4])
            with c1:
                nova_emp = st.text_input("Empresa", placeholder="Digite o nome da empresa")
            with c2:
                st.text_input("Agente", value=agente, disabled=True)

            if st.button("Cadastrar empresa", type="primary", use_container_width=True):
                if not nova_emp or not nova_emp.strip():
                    st.warning("⚠️ Informe o nome da empresa antes de cadastrar.")
                    st.stop()

                empresa_nome = nova_emp.strip()

                # 🧱 Cria o registro base se não existir
                seed_empresa_if_missing(empresa_nome, agente)

                # 🚀 Inicia automaticamente o fluxo com o analista (1 dia)
                registrar_transicao(
                    empresa=empresa_nome,
                    nova_etapa="Pendência de Posicionamento",
                    novo_responsavel="Analista",
                    prazo_dias=1
                )

                st.balloons()
                st.success(f"🚀 Empresa **{empresa_nome}** cadastrada com sucesso!")
                st.info("📨 Fluxo iniciado: o analista tem **1 dia** para posicionar o cliente.")
                st.rerun()

    # 👇 lista de empresas para o selectbox
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
        limite = st.number_input("Limite (R$)", min_value=0.0, format="%.2f",
                                 value=float(row.get("limite") or 0), disabled=not editable)
        saida_credito = st.text_input("Saída Crédito (DD-MM-YYYY)",
                                      value=(row.get("saida_credito") or ""), disabled=not editable)

    with col2:
        comentario_interno = st.text_area("Comentário Interno",
                                          value=row.get("comentario_interno") or "",
                                          height=120, disabled=not editable)

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
        envio_das = st.selectbox("Envio DAS", SIM_NAO,
                                 index=SIM_NAO.index("Sim" if (row.get("envio_das") or "").lower()=="sim" else "Não"),
                                 disabled=not editable)
    with c2:
        emissao_contrato = st.selectbox("Emissão contrato", SIM_NAO,
                                        index=SIM_NAO.index("Sim" if (row.get("emissao_contrato") or "").lower()=="sim" else "Não"),
                                        disabled=not editable)
    with c3:
        assinatura = st.selectbox("Assinatura", SIM_NAO,
                                  index=SIM_NAO.index("Sim" if (row.get("assinatura") or "").lower()=="sim" else "Não"),
                                  disabled=not editable)
    with c4:
        homologacao = st.selectbox("Homologação", SIM_NAO,
                                   index=SIM_NAO.index("Sim" if (row.get("homologacao") or "").lower()=="sim" else "Não"),
                                   disabled=not editable)
    with c5:
        apto_a_operar = st.selectbox("Apto a operar", SIM_NAO,
                                     index=SIM_NAO.index("Sim" if (row.get("apto_a_operar") or "").lower()=="sim" else "Não"),
                                     disabled=not editable)

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
# 🧭 WORKFLOW – com restrição por tipo de usuário
# =========================================================
def workflow(tipo, agente):
    st.markdown("## 🧭 Controle de Workflow")
    st.caption("Gerencie as etapas, prazos e responsáveis das análises de crédito de forma visual e organizada.")

    st.markdown("---")
    if st.button("⬅️ Voltar para Overview", use_container_width=True):
        st.session_state.tab = "Overview"
        st.rerun()

    # 🔒 Restrição de acesso para comerciais
    if tipo == "comercial":
        df_emp = run_query_df(
            "SELECT empresa, etapa_atual, responsavel_atual FROM analise_credito WHERE agente = %s ORDER BY empresa",
            (agente,)
        )
    else:
        df_emp = run_query_df(
            "SELECT empresa, etapa_atual, responsavel_atual FROM analise_credito ORDER BY empresa"
        )

    if df_emp.empty:
        st.info("Nenhuma empresa cadastrada ainda.")
        return

    # Mantém a empresa selecionada vinda do Overview, se houver
    empresa_default = st.session_state.get("selected_empresa")
    empresas_lista = df_emp["empresa"].tolist()
    idx_default = empresas_lista.index(empresa_default) if empresa_default in empresas_lista else 0
    empresa = st.selectbox("Selecione uma empresa", empresas_lista, index=idx_default)
    st.session_state.selected_empresa = empresa

    dados = run_query_df("SELECT * FROM analise_credito WHERE empresa = %s", (empresa,))
    if dados.empty:
        st.warning("Empresa não encontrada.")
        return
    row = dados.iloc[0].to_dict()

    # Cabeçalho
    st.markdown(f"""
    <div style="background:#0b2e39;padding:14px;border-radius:10px;border:1px solid #0e3a47;margin-top:10px;">
        <h3 style="margin:0;">🏢 {empresa}</h3>
        <p style="margin:4px 0 0 0;">
        <b>Etapa atual:</b> {row.get('etapa_atual','Cadastro')} |
        <b>Responsável:</b> {row.get('responsavel_atual','Analista')} |
        <b>Última atualização:</b> {row.get('data_ultima_movimentacao')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Timeline
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

    # Atualização
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

    # Log
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

        # Excluir (somente analista)
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
# 📊 INTERFACE / ROTEAMENTO
# =========================================================
header()
if "user" not in st.session_state:
    login_box()
    st.stop()

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
