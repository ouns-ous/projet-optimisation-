"""
Application Streamlit - Simulateur Capacite-Commande Maghreb Steel
Interface web interactive pour la planification de production.
"""

import sys
import os
import io
from pathlib import Path

# ── Forcer UTF-8 sur Windows (evite erreurs charmap avec emojis) ──────────────
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass
os.environ['PYTHONIOENCODING'] = 'utf-8'

# Ajouter src au path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.model import build_and_solve, export_results

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG PAGE
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Maghreb Steel — Simulateur Capacité-Commande",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────────────────────────────────────
# CSS PERSONNALISÉ
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

* { font-family: 'Inter', sans-serif; }

/* Header */
.main-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    padding: 2rem 2.5rem;
    border-radius: 16px;
    margin-bottom: 1.5rem;
    border: 1px solid rgba(255,255,255,0.08);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}
.main-header h1 {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: rgba(255,255,255,0.65);
    margin: 0.4rem 0 0 0;
    font-size: 0.95rem;
}
.logo-badge {
    display: inline-block;
    background: linear-gradient(90deg, #e94560, #f5a623);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 1.1rem;
    margin-bottom: 0.3rem;
}

/* KPI Cards */
.kpi-card {
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 1.2rem 1.4rem;
    text-align: center;
    box-shadow: 0 4px 16px rgba(0,0,0,0.2);
    transition: transform 0.2s;
}
.kpi-card:hover { transform: translateY(-2px); }
.kpi-value {
    font-size: 1.8rem;
    font-weight: 700;
    background: linear-gradient(90deg, #60a5fa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.kpi-label {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.55);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-top: 0.2rem;
}
.kpi-sub {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.35);
    margin-top: 0.15rem;
}

/* Section headers */
.section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    border-left: 3px solid #60a5fa;
    padding-left: 0.75rem;
    margin: 1.2rem 0 0.8rem 0;
}

/* Goulot badge */
.goulot { color: #ef4444; font-weight: 600; }
.tension { color: #f59e0b; font-weight: 600; }
.ok { color: #10b981; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a, #1e293b);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }

/* DataFrame */
[data-testid="stDataFrame"] {
    border-radius: 8px;
    overflow: hidden;
}

/* Boutons */
.stButton > button {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.5rem;
    font-weight: 600;
    width: 100%;
    transition: all 0.2s;
}
.stButton > button:hover {
    background: linear-gradient(135deg, #60a5fa, #3b82f6);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59,130,246,0.4);
}

/* Alert boxes */
.alert-success {
    background: linear-gradient(135deg, rgba(16,185,129,0.15), rgba(5,150,105,0.1));
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #34d399;
}
.alert-warning {
    background: linear-gradient(135deg, rgba(245,158,11,0.15), rgba(217,119,6,0.1));
    border: 1px solid rgba(245,158,11,0.3);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #fbbf24;
}
.alert-danger {
    background: linear-gradient(135deg, rgba(239,68,68,0.15), rgba(220,38,38,0.1));
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #f87171;
}

/* Tabs */
.stTabs [data-baseweb="tab"] {
    background: transparent;
    color: rgba(255,255,255,0.6);
    border-bottom: 2px solid transparent;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #60a5fa;
    border-bottom: 2px solid #60a5fa;
}

/* Metric containers */
[data-testid="metric-container"] {
    background: rgba(30, 41, 59, 0.6);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 0.8rem;
}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 1rem 0;'>
        <div style='font-size:2rem;'>🏭</div>
        <div style='font-size:1rem; font-weight:700; color:#60a5fa;'>Maghreb Steel</div>
        <div style='font-size:0.75rem; color:rgba(255,255,255,0.4);'>Simulateur Capacité-Commande</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### ⚙️ Configuration")

    data_path = st.text_input(
        "Fichier de données",
        value="data/Donnees_MaghrebSteel.xlsx",
        help="Chemin vers le fichier Excel Maghreb Steel"
    )

    st.markdown("### 🎭 Scénario")
    scenario = st.selectbox(
        "Choisir un scénario",
        ["Base", "HRC +10% (E20)", "Panne LGB S2 (E21)", "Commande urgente HDG (E22)"],
        index=0
    )

    hrc_mult = 1.0
    extra_arrets = None
    extra_cmds = None

    if scenario == "HRC +10% (E20)":
        hrc_mult = 1.10
        st.info("Prix HRC majorés de 10% pour tous les grades")
    elif scenario == "Panne LGB S2 (E21)":
        extra_arrets = {"LGB": {2: 2}}
        st.warning("LGB : +2 jours d'arrêt en semaine 2")
    elif scenario == "Commande urgente HDG (E22)":
        extra_cmds = [{
            "ID": "CMD-NEW", "Client": "Nouveau_Client",
            "Famille": "HDG", "Grade": "DC01",
            "Epaisseur": 0.5, "Largeur": 1140,
            "Tonnage": 300, "Prix_vente": 11500,
            "Semaine_livraison": 1, "Priorite": "Haute"
        }]
        st.success("Nouvelle commande HDG 300T ajoutée")

    st.markdown("---")
    run_btn = st.button("🚀 Lancer l'optimisation", use_container_width=True)

    st.markdown("---")
    st.markdown("""
    <div style='font-size:0.72rem; color:rgba(255,255,255,0.3); text-align:center;'>
        EMINES UM6P — Promo 2026<br>
        Projet Recherche Opérationnelle
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<div class='main-header'>
    <div class='logo-badge'>MAGHREB STEEL</div>
    <h1>🏭 Simulateur Capacité-Commande</h1>
    <p>Optimisation multi-périodes · Multi-produits · Multi-ressources · Horizon 4 semaines</p>
</div>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# SESSION STATE & RUN
# ─────────────────────────────────────────────────────────────────────────────
if "resultats" not in st.session_state:
    st.session_state.resultats = None
    st.session_state.scenario_label = "Base"

if run_btn:
    with st.spinner("Optimisation en cours... Veuillez patienter."):
        try:
            import sys, io
            # Forcer UTF-8 pour eviter les erreurs d'encoding sur Windows
            if hasattr(sys.stdout, 'reconfigure'):
                try:
                    sys.stdout.reconfigure(encoding='utf-8')
                except Exception:
                    pass
            r = build_and_solve(
                data_path,
                hrc_multiplier=hrc_mult,
                extra_arrets=extra_arrets,
                extra_commandes=extra_cmds,
            )
            st.session_state.resultats = r
            st.session_state.scenario_label = scenario
            export_results(r, "outputs")
            st.success("Optimisation terminee avec succes !")
        except Exception as e:
            st.error("Erreur : {}".format(str(e)))
            st.stop()

# Auto-run on first load
if st.session_state.resultats is None and not run_btn:
    with st.spinner("Chargement initial..."):
        try:
            import sys
            if hasattr(sys.stdout, 'reconfigure'):
                try:
                    sys.stdout.reconfigure(encoding='utf-8')
                except Exception:
                    pass
            r = build_and_solve(data_path)
            st.session_state.resultats = r
            export_results(r, "outputs")
        except Exception as e:
            st.warning("Fichier non trouve ou erreur : {}".format(str(e)))
            st.info("Cliquez sur 'Lancer l optimisation' pour demarrer.")
            st.stop()

res = st.session_state.resultats
if res is None:
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-value'>{res['marge_totale']/1e6:.1f}M</div>
        <div class='kpi-label'>Marge Totale</div>
        <div class='kpi-sub'>MAD</div>
    </div>""", unsafe_allow_html=True)

with c2:
    color = "#34d399" if res['taux_service'] >= 85 else "#f59e0b" if res['taux_service'] >= 70 else "#ef4444"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-value' style='background: linear-gradient(90deg, {color}, {color}); -webkit-background-clip:text;'>{res['taux_service']:.1f}%</div>
        <div class='kpi-label'>Taux de Service</div>
        <div class='kpi-sub'>{res['tonnage_livre_total']:,.0f} / {res['tonnage_demande_total']:,.0f} T</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-value'>{res['tonnage_livre_total']:,.0f}</div>
        <div class='kpi-label'>Tonnage Livré</div>
        <div class='kpi-sub'>Tonnes</div>
    </div>""", unsafe_allow_html=True)

with c4:
    n_ref = len(res['commandes_refusees'])
    n_tot = len(res['commandes'])
    color_ref = "#ef4444" if n_ref > 10 else "#f59e0b" if n_ref > 5 else "#34d399"
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-value' style='background: linear-gradient(90deg, {color_ref}, {color_ref}); -webkit-background-clip:text;'>{n_ref}</div>
        <div class='kpi-label'>Cdes Refusées</div>
        <div class='kpi-sub'>sur {n_tot} commandes</div>
    </div>""", unsafe_allow_html=True)

with c5:
    marge_par_t = res['marge_totale'] / res['tonnage_livre_total'] if res['tonnage_livre_total'] > 0 else 0
    st.markdown(f"""
    <div class='kpi-card'>
        <div class='kpi-value'>{marge_par_t:,.0f}</div>
        <div class='kpi-label'>Marge / Tonne</div>
        <div class='kpi-sub'>MAD/T</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# TABS
# ─────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Plan de Marche",
    "🔩 Utilisation Lignes",
    "📦 Commandes",
    "📈 Analyse Économique",
    "⚠️ Shadow Prices",
])

# ── TAB 1 : PLAN DE MARCHE ────────────────────────────────────────────────────
with tab1:
    st.markdown("<div class='section-title'>Plan de Production — Tonnes par ligne × semaine</div>", unsafe_allow_html=True)

    rows = []
    for ligne, sems in res["plan_marche"].items():
        for sem, fams in sems.items():
            for fam, ton in fams.items():
                if ton > 0.1:
                    rows.append({"Ligne": ligne, "Semaine": f"S{sem}", "Famille": fam, "Tonnage (T)": round(ton)})
    df_plan = pd.DataFrame(rows)

    if not df_plan.empty:
        # Heatmap-like pivot
        pivot = df_plan.pivot_table(
            index="Ligne", columns="Semaine", values="Tonnage (T)", aggfunc="sum", fill_value=0
        )
        fig_heat = px.imshow(
            pivot,
            text_auto=True,
            color_continuous_scale="Blues",
            title="Tonnage total par ligne et semaine (T)",
            aspect="auto",
        )
        fig_heat.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="#e2e8f0",
            title_font_size=14,
            height=350,
        )
        st.plotly_chart(fig_heat, use_container_width=True)

        # Barres empilées par famille
        fig_bar = px.bar(
            df_plan, x="Semaine", y="Tonnage (T)", color="Famille",
            facet_col="Ligne", facet_col_wrap=4,
            title="Tonnage par famille, semaine et ligne",
            color_discrete_map={
                "CRC": "#3b82f6", "HDG": "#10b981", "PPGI": "#f59e0b",
                "BACR": "#8b5cf6", "HRC DEC": "#6b7280"
            }
        )
        fig_bar.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(15,23,42,0.6)",
            font_color="#e2e8f0",
            height=500,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.dataframe(df_plan, use_container_width=True, hide_index=True)

# ── TAB 2 : UTILISATION LIGNES ────────────────────────────────────────────────
with tab2:
    st.markdown("<div class='section-title'>Taux d'Utilisation par Ligne de Production (%)</div>", unsafe_allow_html=True)

    util_rows = []
    for ligne, sems in res["utilisation_lignes"].items():
        for sem, util in sems.items():
            util_rows.append({"Ligne": ligne, "Semaine": f"S{sem}", "Utilisation (%)": util})
    df_util = pd.DataFrame(util_rows)

    # Radar / heatmap utilisation
    pivot_util = df_util.pivot_table(index="Ligne", columns="Semaine", values="Utilisation (%)", fill_value=0)

    fig_util = go.Figure()
    colors = {"S1": "#3b82f6", "S2": "#10b981", "S3": "#f59e0b", "S4": "#ef4444"}
    for sem in ["S1", "S2", "S3", "S4"]:
        if sem in pivot_util.columns:
            fig_util.add_trace(go.Bar(
                name=sem,
                x=pivot_util.index.tolist(),
                y=pivot_util[sem].tolist(),
                marker_color=colors[sem],
                opacity=0.85,
            ))

    fig_util.add_hline(y=90, line_dash="dash", line_color="#ef4444",
                        annotation_text="Seuil critique 90%", annotation_position="right")
    fig_util.add_hline(y=75, line_dash="dot", line_color="#f59e0b",
                        annotation_text="Seuil tension 75%", annotation_position="right")
    fig_util.update_layout(
        barmode="group",
        title="Taux d'utilisation par ligne et semaine",
        yaxis_title="Utilisation (%)",
        yaxis_range=[0, 110],
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(15,23,42,0.6)",
        font_color="#e2e8f0",
        legend_title="Semaine",
        height=420,
    )
    st.plotly_chart(fig_util, use_container_width=True)

    # Identifier les goulots
    st.markdown("<div class='section-title'>Analyse des Goulots</div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3)
    goulots = []
    tensions = []
    ok_lignes = []
    for ligne, sems in res["utilisation_lignes"].items():
        max_util = max(sems.values())
        if max_util >= 90:
            goulots.append(f"{ligne} ({max_util:.0f}%)")
        elif max_util >= 75:
            tensions.append(f"{ligne} ({max_util:.0f}%)")
        else:
            ok_lignes.append(f"{ligne} ({max_util:.0f}%)")

    with g1:
        st.markdown(f"""<div class='alert-danger'>
        <b>🔴 Goulots (>90%)</b><br>{'<br>'.join(goulots) if goulots else 'Aucun'}
        </div>""", unsafe_allow_html=True)
    with g2:
        st.markdown(f"""<div class='alert-warning'>
        <b>🟡 En tension (75-90%)</b><br>{'<br>'.join(tensions) if tensions else 'Aucun'}
        </div>""", unsafe_allow_html=True)
    with g3:
        st.markdown(f"""<div class='alert-success'>
        <b>🟢 OK (<75%)</b><br>{'<br>'.join(ok_lignes) if ok_lignes else 'Aucun'}
        </div>""", unsafe_allow_html=True)

# ── TAB 3 : COMMANDES ─────────────────────────────────────────────────────────
with tab3:
    st.markdown("<div class='section-title'>Carnet de Commandes — Résultats</div>", unsafe_allow_html=True)

    df_cmds = pd.DataFrame(res["commandes"])

    # Filtres
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        filt_fam = st.multiselect("Famille", df_cmds["famille"].unique().tolist(), default=df_cmds["famille"].unique().tolist())
    with col_f2:
        filt_prio = st.multiselect("Priorité", df_cmds["priorite"].unique().tolist(), default=df_cmds["priorite"].unique().tolist())
    with col_f3:
        filt_status = st.selectbox("Statut", ["Toutes", "Honorées (>95%)", "Partielles (5-95%)", "Refusées (<5%)"])

    df_show = df_cmds[
        df_cmds["famille"].isin(filt_fam) &
        df_cmds["priorite"].isin(filt_prio)
    ].copy()

    if filt_status == "Honorées (>95%)":
        df_show = df_show[df_show["taux_service"] >= 95]
    elif filt_status == "Partielles (5-95%)":
        df_show = df_show[(df_show["taux_service"] >= 5) & (df_show["taux_service"] < 95)]
    elif filt_status == "Refusées (<5%)":
        df_show = df_show[df_show["taux_service"] < 5]

    # Colorier les lignes
    def color_taux(val):
        if val >= 95:
            return "color: #34d399"
        elif val >= 5:
            return "color: #fbbf24"
        else:
            return "color: #f87171"

    styled = df_show.style.applymap(color_taux, subset=["taux_service"])
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 column_config={
                     "taux_service": st.column_config.ProgressColumn(
                         "Taux service (%)", min_value=0, max_value=100
                     ),
                     "marge_unitaire": st.column_config.NumberColumn("Marge/T (MAD)", format="%,.0f"),
                     "tonnage_livre": st.column_config.NumberColumn("Livré (T)", format="%.1f"),
                     "tonnage_demande": st.column_config.NumberColumn("Demandé (T)", format="%.0f"),
                 })

    # Camembert par famille
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        df_pie = df_cmds.groupby("famille")["tonnage_livre"].sum().reset_index()
        fig_pie = px.pie(df_pie, values="tonnage_livre", names="famille",
                         title="Tonnage livré par famille",
                         color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#8b5cf6","#6b7280"])
        fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="#e2e8f0", height=320)
        st.plotly_chart(fig_pie, use_container_width=True)
    with col_p2:
        df_prio_bar = df_cmds.groupby(["priorite","famille"])["tonnage_livre"].sum().reset_index()
        fig_prio = px.bar(df_prio_bar, x="priorite", y="tonnage_livre", color="famille",
                          title="Tonnage livré par priorité",
                          color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#8b5cf6"])
        fig_prio.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)",
                                font_color="#e2e8f0", height=320)
        st.plotly_chart(fig_prio, use_container_width=True)

    # Commandes refusées
    if res["commandes_refusees"]:
        st.markdown("<div class='section-title'>⛔ Commandes Refusées</div>", unsafe_allow_html=True)
        df_ref = pd.DataFrame(res["commandes_refusees"])
        st.dataframe(df_ref[["id","famille","grade","epaisseur","tonnage_demande","semaine","priorite","marge_unitaire"]],
                     use_container_width=True, hide_index=True)

# ── TAB 4 : ANALYSE ÉCONOMIQUE ─────────────────────────────────────────────────
with tab4:
    st.markdown("<div class='section-title'>Analyse Économique — Marge par Famille</div>", unsafe_allow_html=True)

    col_e1, col_e2 = st.columns(2)
    with col_e1:
        df_marge_fam = pd.DataFrame([
            {"Famille": k, "Marge_totale_MMAD": v/1e6, "Tonnage_T": res["tonnage_par_famille"].get(k,0)}
            for k, v in res["marge_par_famille"].items()
            if v > 0
        ])
        if not df_marge_fam.empty:
            df_marge_fam["Marge_par_T"] = (
                df_marge_fam["Marge_totale_MMAD"] * 1e6 / df_marge_fam["Tonnage_T"].replace(0, 1)
            )
            fig_marge = px.bar(
                df_marge_fam.sort_values("Marge_totale_MMAD", ascending=False),
                x="Famille", y="Marge_totale_MMAD",
                color="Famille", title="Marge totale par famille (MMAD)",
                text_auto=".2f",
                color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#8b5cf6","#6b7280"]
            )
            fig_marge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)",
                font_color="#e2e8f0", height=350, showlegend=False
            )
            st.plotly_chart(fig_marge, use_container_width=True)

    with col_e2:
        # Scatter marge/tonne vs tonnage
        df_cmds_all = pd.DataFrame(res["commandes"])
        df_cmds_all = df_cmds_all[df_cmds_all["tonnage_livre"] > 0]
        if not df_cmds_all.empty:
            fig_sc = px.scatter(
                df_cmds_all, x="tonnage_livre", y="marge_unitaire",
                color="famille", size="tonnage_livre",
                hover_data=["id","grade","epaisseur","semaine"],
                title="Marge unitaire vs Tonnage livré",
                color_discrete_sequence=["#3b82f6","#10b981","#f59e0b","#8b5cf6","#6b7280"]
            )
            fig_sc.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)",
                font_color="#e2e8f0", height=350
            )
            st.plotly_chart(fig_sc, use_container_width=True)

    # Recommandations
    st.markdown("<div class='section-title'>💡 Recommandations Opérationnelles (E23)</div>", unsafe_allow_html=True)

    # Trouver le goulot principal
    max_util = {l: max(sems.values()) for l, sems in res["utilisation_lignes"].items()}
    goulot_principal = max(max_util, key=max_util.get)
    best_fam = max(res["marge_par_famille"], key=res["marge_par_famille"].get) if res["marge_par_famille"] else "HDG"

    r1, r2, r3 = st.columns(3)
    with r1:
        st.markdown(f"""<div class='alert-success'>
        <b>🎯 Rec. 1 — Capacité</b><br>
        Investir dans la ligne <b>{goulot_principal}</b> (goulot à {max_util.get(goulot_principal,0):.0f}%).
        Débloquer ce goulot permettrait d'absorber les commandes refusées.
        </div>""", unsafe_allow_html=True)
    with r2:
        st.markdown(f"""<div class='alert-success'>
        <b>💰 Rec. 2 — Mix produit</b><br>
        Prioriser la famille <b>{best_fam}</b> qui génère la marge la plus élevée.
        Revoir la politique commerciale pour favoriser ce mix.
        </div>""", unsafe_allow_html=True)
    with r3:
        st.markdown(f"""<div class='alert-success'>
        <b>📦 Rec. 3 — HRC</b><br>
        Négocier les prix HRC pour les grades les plus consommés (DC01, DX51).
        Un gain de 5% sur le prix HRC améliore la marge de ~150-200 MAD/T.
        </div>""", unsafe_allow_html=True)

# ── TAB 5 : SHADOW PRICES ─────────────────────────────────────────────────────
with tab5:
    st.markdown("<div class='section-title'>Shadow Prices — Valeur Marginale des Contraintes</div>", unsafe_allow_html=True)

    if res["shadow_prices"]:
        sp_df = pd.DataFrame([
            {"Contrainte": k, "Shadow Price (MAD)": v, "Valeur absolue": abs(v)}
            for k, v in res["shadow_prices"].items()
        ]).sort_values("Valeur absolue", ascending=False).head(20)

        fig_sp = px.bar(
            sp_df, x="Shadow Price (MAD)", y="Contrainte",
            orientation="h",
            title="Top Shadow Prices (valeur absolue décroissante)",
            color="Shadow Price (MAD)",
            color_continuous_scale="RdBu_r",
        )
        fig_sp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(15,23,42,0.6)",
            font_color="#e2e8f0", height=500, yaxis={"autorange": "reversed"}
        )
        st.plotly_chart(fig_sp, use_container_width=True)

        st.markdown("<div class='section-title'>Interprétation Business (E18)</div>", unsafe_allow_html=True)
        top3 = sp_df.head(3)
        for _, row in top3.iterrows():
            name = row["Contrainte"]
            sp_val = row["Shadow Price (MAD)"]
            if name.startswith("dem_"):
                cmd_id = name.replace("dem_","").replace("_","-")
                interp = f"Si on relâche d'une tonne la contrainte de demande de **{cmd_id}**, la marge augmente de **{abs(sp_val):,.0f} MAD**. Cette commande est très rentable."
            elif name.startswith("cap_"):
                parts = name.split("_")
                ligne_name = parts[1] if len(parts) > 1 else "?"
                interp = f"Une tonne supplémentaire de capacité sur la ligne **{ligne_name}** rapporte **{abs(sp_val):,.0f} MAD** de marge additionnelle. C'est un investissement prioritaire."
            elif name.startswith("hrc_"):
                grade_name = name.replace("hrc_","")
                interp = f"1 tonne supplémentaire de HRC **{grade_name}** génère **{abs(sp_val):,.0f} MAD** de marge. Négocier davantage de stock de ce grade est prioritaire."
            else:
                interp = f"Valeur marginale de la contrainte : **{abs(sp_val):,.0f} MAD** par unité relâchée."
            st.info(f"**{name}** ({sp_val:+,.0f} MAD) — {interp}")
    else:
        st.info("Aucun shadow price significatif (toutes contraintes non saturées).")

    # Limites du modèle (E24)
    st.markdown("<div class='section-title'>⚠️ Limites du Modèle (E24)</div>", unsafe_allow_html=True)
    lim1, lim2, lim3 = st.columns(3)
    with lim1:
        st.markdown("""<div class='alert-warning'>
        <b>1. Relaxation LP</b><br>
        Variables continues → solutions fractionnaires.
        En pratique, la production se fait par campagne entière.
        </div>""", unsafe_allow_html=True)
    with lim2:
        st.markdown("""<div class='alert-warning'>
        <b>2. Horizon 4 semaines</b><br>
        Ne capture pas les effets à long terme (contrats cadres,
        planification trimestrielle, tendances marché).
        </div>""", unsafe_allow_html=True)
    with lim3:
        st.markdown("""<div class='alert-warning'>
        <b>3. Incertitudes ignorées</b><br>
        Cadences, rendements, prix HRC supposés certains.
        Un modèle robuste nécessiterait une approche stochastique.
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
col_dl1, col_dl2, col_spacer = st.columns([1, 1, 3])
with col_dl1:
    plan_csv_path = Path("outputs/plan_marche.csv")
    if plan_csv_path.exists():
        with open(plan_csv_path, "rb") as f:
            st.download_button(
                "📥 Télécharger Plan de Marche",
                data=f.read(),
                file_name="plan_marche.csv",
                mime="text/csv",
            )
with col_dl2:
    res_xlsx = Path("outputs/resultats_complets.xlsx")
    if res_xlsx.exists():
        with open(res_xlsx, "rb") as f:
            st.download_button(
                "📥 Télécharger Résultats Excel",
                data=f.read(),
                file_name="resultats_maghreb_steel.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

st.markdown("""
<div style='text-align:center; color:rgba(255,255,255,0.3); font-size:0.75rem; padding:1rem;'>
    Maghreb Steel — Simulateur Capacité-Commande · EMINES UM6P Promo 2026 · Projet Recherche Opérationnelle
</div>
""", unsafe_allow_html=True)
