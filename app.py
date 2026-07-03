import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import date, timedelta

st.set_page_config(
    page_title="Raissa Dashboard 2026",
    page_icon="💌",
    layout="wide"
)

SHEET_ID = "1ZvDtBykSxsSVtuu-DmyIa3kMvoxAgvUex_yKO9uUtYo"
ABA = "Página1"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def conectar_planilha():
    creds = Credentials.from_service_account_info(
        st.secrets["google_service_account"],
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).worksheet(ABA)
    return sheet


def carregar_dados():
    sheet = conectar_planilha()
    dados = sheet.get_all_records()

    colunas = ["Nome", "Data", "Prioridade", "Categoria", "Feito", "Descrição"]
    df = pd.DataFrame(dados)

    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = ""

    df = df[colunas]

    if df.empty:
        df = pd.DataFrame(columns=colunas)

    df["Data"] = pd.to_datetime(df["Data"], dayfirst=True, errors="coerce").dt.date

    return df


def adicionar_tarefa(nome, data, prioridade, categoria, feito, descricao):
    sheet = conectar_planilha()
    sheet.append_row([
        nome,
        data.strftime("%d/%m/%Y"),
        prioridade,
        categoria,
        feito,
        descricao
    ])


def atualizar_tarefa(linha_planilha, nome, data, prioridade, categoria, feito, descricao):
    sheet = conectar_planilha()
    sheet.update(f"A{linha_planilha}:F{linha_planilha}", [[
        nome,
        data.strftime("%d/%m/%Y") if hasattr(data, "strftime") else data,
        prioridade,
        categoria,
        feito,
        descricao
    ]])


def deletar_tarefa(linha_planilha):
    sheet = conectar_planilha()
    sheet.delete_rows(linha_planilha)


if "logado" not in st.session_state:
    st.session_state.logado = False


def login():
    st.title("raissa's home | 2026")
    st.subheader("Acesse seu dashboard de tarefas")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar", use_container_width=True):
        if usuario == "raissa" and senha == "2026":
            st.session_state.logado = True
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")


def menu():
    st.sidebar.title("💌 Raissa 2026")

    pagina = st.sidebar.radio(
        "Menu",
        ["Visão Geral", "Tarefas / To-do"]
    )

    if st.sidebar.button("Sair", use_container_width=True):
        st.session_state.logado = False
        st.rerun()

    return pagina


def aplicar_filtros(df):
    st.subheader("Filtros")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        periodo = st.selectbox("Período", ["Todas", "Hoje", "Semana", "Mês"])

    with col2:
        prioridade = st.selectbox("Prioridade", ["Todas", "Alta", "Média", "Baixa"])

    with col3:
        categoria = st.selectbox("Categoria", ["Todas"] + sorted(df["Categoria"].dropna().unique().tolist()))

    with col4:
        feito = st.selectbox("Feito", ["Todos", "Sim", "Não"])

    hoje = date.today()
    df_filtrado = df.copy()

    if periodo == "Hoje":
        df_filtrado = df_filtrado[df_filtrado["Data"] == hoje]

    elif periodo == "Semana":
        inicio = hoje - timedelta(days=hoje.weekday())
        fim = inicio + timedelta(days=6)
        df_filtrado = df_filtrado[
            (df_filtrado["Data"] >= inicio) &
            (df_filtrado["Data"] <= fim)
        ]

    elif periodo == "Mês":
        datas = pd.to_datetime(df_filtrado["Data"], errors="coerce")
        df_filtrado = df_filtrado[datas.dt.month == hoje.month]

    if prioridade != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Prioridade"] == prioridade]

    if categoria != "Todas":
        df_filtrado = df_filtrado[df_filtrado["Categoria"] == categoria]

    if feito != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Feito"] == feito]

    return df_filtrado


def pagina_visao_geral():
    st.title("Visão Geral")

    df = carregar_dados()

    total = len(df)
    concluidas = len(df[df["Feito"].astype(str).str.lower().isin(["sim", "feito", "concluído", "concluida", "concluída"])])
    pendentes = total - concluidas
    produtividade = round((concluidas / total) * 100, 1) if total > 0 else 0

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total de tarefas", total)
    col2.metric("Concluídas", concluidas)
    col3.metric("Pendentes", pendentes)
    col4.metric("Produtividade", f"{produtividade}%")

    st.divider()

    if df.empty:
        st.info("Nenhuma tarefa cadastrada ainda.")
        return

    colg1, colg2 = st.columns(2)

    with colg1:
        st.subheader("Tarefas por prioridade")
        fig = px.pie(df, names="Prioridade", hole=0.45)
        st.plotly_chart(fig, use_container_width=True)

    with colg2:
        st.subheader("Tarefas por categoria")
        contagem_categoria = df["Categoria"].value_counts().reset_index()
        contagem_categoria.columns = ["Categoria", "Quantidade"]
        fig = px.bar(contagem_categoria, x="Categoria", y="Quantidade", text="Quantidade")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Lista geral")
    st.dataframe(df, use_container_width=True)


def pagina_tarefas():
    st.title("Tarefas / To-do")

    df = carregar_dados()

    st.subheader("Adicionar nova tarefa")

    with st.form("nova_tarefa"):
        col1, col2 = st.columns(2)

        with col1:
            nome = st.text_input("Nome da tarefa")
            data_tarefa = st.date_input("Data", value=date.today())
            prioridade = st.selectbox("Prioridade", ["Alta", "Média", "Baixa"])

        with col2:
            categoria = st.selectbox("Categoria", ["Trabalho", "Pessoal", "Estudo", "Financeiro", "Marketing"])
            feito = st.selectbox("Feito", ["Não", "Sim"])

        descricao = st.text_area("Descrição")

        salvar = st.form_submit_button("Adicionar tarefa", use_container_width=True)

        if salvar:
            if nome.strip() == "":
                st.warning("Preencha o nome da tarefa.")
            else:
                adicionar_tarefa(nome, data_tarefa, prioridade, categoria, feito, descricao)
                st.success("Tarefa adicionada com sucesso!")
                st.rerun()

    st.divider()

    df_filtrado = aplicar_filtros(df)

    st.subheader("Editar tarefas")

    if df_filtrado.empty:
        st.info("Nenhuma tarefa encontrada.")
        return

    for index, row in df_filtrado.iterrows():
        linha_planilha = index + 2

        titulo = row["Nome"] if row["Nome"] else "Tarefa sem nome"

        with st.expander(titulo):
            col1, col2 = st.columns(2)

            data_atual = row["Data"] if pd.notna(row["Data"]) else date.today()

            with col1:
                novo_nome = st.text_input("Nome", value=row["Nome"], key=f"nome_{index}")
                nova_data = st.date_input("Data", value=data_atual, key=f"data_{index}")
                nova_prioridade = st.selectbox(
                    "Prioridade",
                    ["Alta", "Média", "Baixa"],
                    index=["Alta", "Média", "Baixa"].index(row["Prioridade"]) if row["Prioridade"] in ["Alta", "Média", "Baixa"] else 0,
                    key=f"prioridade_{index}"
                )

            with col2:
                nova_categoria = st.selectbox(
                    "Categoria",
                    ["Trabalho", "Pessoal", "Estudo", "Financeiro", "Marketing"],
                    index=["Trabalho", "Pessoal", "Estudo", "Financeiro", "Marketing"].index(row["Categoria"]) if row["Categoria"] in ["Trabalho", "Pessoal", "Estudo", "Financeiro", "Marketing"] else 0,
                    key=f"categoria_{index}"
                )

                novo_feito = st.selectbox(
                    "Feito",
                    ["Não", "Sim"],
                    index=["Não", "Sim"].index(row["Feito"]) if row["Feito"] in ["Não", "Sim"] else 0,
                    key=f"feito_{index}"
                )

            nova_descricao = st.text_area("Descrição", value=row["Descrição"], key=f"descricao_{index}")

            col_salvar, col_deletar = st.columns(2)

            with col_salvar:
                if st.button("Salvar alteração", key=f"salvar_{index}", use_container_width=True):
                    atualizar_tarefa(
                        linha_planilha,
                        novo_nome,
                        nova_data,
                        nova_prioridade,
                        nova_categoria,
                        novo_feito,
                        nova_descricao
                    )
                    st.success("Tarefa atualizada!")
                    st.rerun()

            with col_deletar:
                if st.button("Excluir tarefa", key=f"deletar_{index}", use_container_width=True):
                    deletar_tarefa(linha_planilha)
                    st.success("Tarefa excluída!")
                    st.rerun()


def main():
    if not st.session_state.logado:
        login()
    else:
        pagina = menu()

        if pagina == "Visão Geral":
            pagina_visao_geral()

        elif pagina == "Tarefas / To-do":
            pagina_tarefas()


if __name__ == "__main__":
    main()
