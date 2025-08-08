import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date
import numpy as np
import io
import openpyxl

# Configuração da página
st.set_page_config(
    page_title="Avaliação de Motoristas",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# CSS personalizado para melhor responsividade
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 1rem 0;
        color: #1f77b4;
        border-bottom: 2px solid #1f77b4;
        margin-bottom: 2rem;
    }

    .metric-container {
        background: linear-gradient(90deg, #f0f2f6, #ffffff);
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }

    .driver-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }

    .evaluation-form {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
    }

    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 1.5rem !important;
        }
        .metric-container {
            margin: 0.3rem 0;
            padding: 0.8rem;
        }
    }
</style>
""", unsafe_allow_html=True)


# Inicialização do banco de dados
def init_database():
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()

    # Tabela de motoristas
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS motoristas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            veiculo_id INTEGER,
            data_cadastro DATE NOT NULL,
            FOREIGN KEY (veiculo_id) REFERENCES veiculos (id)
        )
    ''')

    # Tabela de veículos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS veiculos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            placa TEXT NOT NULL UNIQUE,
            modelo TEXT NOT NULL,
            tipo_veiculo TEXT NOT NULL,
            proprio_alugado TEXT NOT NULL,
            cidade TEXT NOT NULL,
            ano INTEGER NOT NULL
        )
    ''')

    # Tabela de avaliações
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS avaliacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            motorista_id INTEGER,
            custo_manutencao INTEGER NOT NULL,
            disponibilidade_frota INTEGER NOT NULL,
            metas_producao INTEGER NOT NULL,
            seguranca_trabalho INTEGER NOT NULL,
            realizacao_checklist INTEGER NOT NULL,
            conhecimento_manutencao INTEGER NOT NULL,
            comunicacao_assertiva INTEGER NOT NULL,
            comentario TEXT,
            avaliador TEXT,
            data_avaliacao DATETIME NOT NULL,
            FOREIGN KEY (motorista_id) REFERENCES motoristas (id)
        )
    ''')

    conn.commit()
    conn.close()


# Funções do banco de dados
def cadastrar_motorista(nome, veiculo_id):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO motoristas (nome, veiculo_id, data_cadastro)
        VALUES (?, ?, ?)
    ''', (nome, veiculo_id, date.today()))
    conn.commit()
    conn.close()


def listar_motoristas():
    conn = sqlite3.connect('motoristas.db')
    df = pd.read_sql_query('''
        SELECT m.id, m.nome, v.placa, v.modelo, v.tipo_veiculo, v.cidade, m.data_cadastro
        FROM motoristas m
        LEFT JOIN veiculos v ON m.veiculo_id = v.id
        ORDER BY m.nome
    ''', conn)
    conn.close()
    return df


def listar_veiculos():
    conn = sqlite3.connect('motoristas.db')
    df = pd.read_sql_query('SELECT * FROM veiculos ORDER BY placa', conn)
    conn.close()
    return df


def cadastrar_veiculo(placa, modelo, tipo_veiculo, proprio_alugado, cidade, ano):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO veiculos (placa, modelo, tipo_veiculo, proprio_alugado, cidade, ano)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (placa, modelo, tipo_veiculo, proprio_alugado, cidade, ano))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def importar_veiculos_excel(df_excel):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()

    sucessos = 0
    erros = []

    for index, row in df_excel.iterrows():
        try:
            cursor.execute('''
                INSERT INTO veiculos (placa, modelo, tipo_veiculo, proprio_alugado, cidade, ano)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(row['Placa']).upper().strip(),
                str(row['Modelo']).strip(),
                str(row['Tipo de veículo']).strip(),
                str(row['Próprio ou alugado']).strip(),
                str(row['Cidade']).strip(),
                int(row['Ano'])
            ))
            sucessos += 1
        except Exception as e:
            erros.append(f"Linha {index + 2}: {str(e)}")

    conn.commit()
    conn.close()
    return sucessos, erros


def obter_motorista_por_id(motorista_id):
    conn = sqlite3.connect('motoristas.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT m.id, m.nome, m.veiculo_id, v.placa, v.modelo, m.data_cadastro
        FROM motoristas m
        LEFT JOIN veiculos v ON m.veiculo_id = v.id
        WHERE m.id = ?
    ''', (motorista_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def atualizar_motorista(motorista_id, nome, veiculo_id):
    conn = sqlite3.connect('motoristas.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE motoristas 
        SET nome = ?, veiculo_id = ?
        WHERE id = ?
    ''', (nome, veiculo_id, motorista_id))
    conn.commit()
    conn.close()


def excluir_motorista(motorista_id):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()
    # Primeiro exclui todas as avaliações do motorista
    cursor.execute('DELETE FROM avaliacoes WHERE motorista_id = ?', (motorista_id,))
    # Depois exclui o motorista
    cursor.execute('DELETE FROM motoristas WHERE id = ?', (motorista_id,))
    conn.commit()
    conn.close()


def adicionar_avaliacao(motorista_id, custo_manutencao, disponibilidade_frota, metas_producao, seguranca_trabalho,
                        realizacao_checklist, conhecimento_manutencao, comunicacao_assertiva, comentario, avaliador):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO avaliacoes (motorista_id, custo_manutencao, disponibilidade_frota, metas_producao, seguranca_trabalho, realizacao_checklist, conhecimento_manutencao, comunicacao_assertiva, comentario, avaliador, data_avaliacao)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
    motorista_id, custo_manutencao, disponibilidade_frota, metas_producao, seguranca_trabalho, realizacao_checklist,
    conhecimento_manutencao, comunicacao_assertiva, comentario, avaliador, datetime.now()))
    conn.commit()
    conn.close()


def obter_avaliacoes_motorista(motorista_id):
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    df = pd.read_sql_query('''
        SELECT * FROM avaliacoes 
        WHERE motorista_id = ? 
        ORDER BY data_avaliacao DESC
    ''', conn, params=[motorista_id])
    conn.close()
    return df


def calcular_estatisticas_motorista(motorista_id):
    df = obter_avaliacoes_motorista(motorista_id)
    if df.empty:
        return None

    stats = {
        'media_geral': df[['custo_manutencao', 'disponibilidade_frota', 'metas_producao', 'seguranca_trabalho',
                           'realizacao_checklist', 'conhecimento_manutencao', 'comunicacao_assertiva']].mean().mean(),
        'media_custo_manutencao': df['custo_manutencao'].mean(),
        'media_disponibilidade_frota': df['disponibilidade_frota'].mean(),
        'media_metas_producao': df['metas_producao'].mean(),
        'media_seguranca_trabalho': df['seguranca_trabalho'].mean(),
        'media_realizacao_checklist': df['realizacao_checklist'].mean(),
        'media_conhecimento_manutencao': df['conhecimento_manutencao'].mean(),
        'media_comunicacao_assertiva': df['comunicacao_assertiva'].mean(),
        'total_avaliacoes': len(df),
        'ultima_avaliacao': df['data_avaliacao'].iloc[0] if not df.empty else None
    }
    return stats


def obter_ranking_geral():
    conn = sqlite3.connect('motoristas.db',check_same_thread=False)
    df = pd.read_sql_query('''
        SELECT 
            m.nome,
            v.placa,
            v.modelo,
            AVG((a.custo_manutencao + a.disponibilidade_frota + a.metas_producao + a.seguranca_trabalho + a.realizacao_checklist + a.conhecimento_manutencao + a.comunicacao_assertiva) / 7.0) as media_geral,
            COUNT(a.id) as total_avaliacoes
        FROM motoristas m
        LEFT JOIN veiculos v ON m.veiculo_id = v.id
        LEFT JOIN avaliacoes a ON m.id = a.motorista_id
        GROUP BY m.id, m.nome, v.placa, v.modelo
        HAVING COUNT(a.id) > 0
        ORDER BY media_geral DESC
    ''', conn)
    conn.close()
    return df


# Inicializar banco
init_database()

# Interface principal
st.markdown('<div class="main-header"><h1>🚗 Sistema de Avaliação de Motoristas</h1></div>', unsafe_allow_html=True)

# Menu lateral
menu = st.sidebar.selectbox(
    "📋 Menu",
    ["🏠 Início", "🚛 Cadastrar Veículos", "➕ Cadastrar Motorista", "✏️ Editar Motorista", "⭐ Avaliar Motorista",
     "📊 Dashboard", "🏆 Ranking"]
)

# Página Início
if menu == "🏠 Início":
    st.markdown("### 👋 Bem-vindo ao Sistema de Avaliação!")

    col1, col2, col3 = st.columns(3)

    motoristas_df = listar_motoristas()
    total_motoristas = len(motoristas_df)

    with col1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("🚗 Motoristas Cadastrados", total_motoristas)
        st.markdown('</div>', unsafe_allow_html=True)

    # Calcular total de avaliações
    conn = sqlite3.connect('motoristas.db')
    try:
        total_avaliacoes = pd.read_sql_query('SELECT COUNT(*) as total FROM avaliacoes', conn)['total'].iloc[0]
    except:
        total_avaliacoes = 0
    conn.close()

    with col2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("⭐ Total de Avaliações", total_avaliacoes)
        st.markdown('</div>', unsafe_allow_html=True)

    with col3:
        media_sistema = 0
        if total_avaliacoes > 0:
            conn = sqlite3.connect('motoristas.db')
            try:
                media_sistema = pd.read_sql_query('''
                    SELECT AVG((custo_manutencao + disponibilidade_frota + metas_producao + seguranca_trabalho + realizacao_checklist + conhecimento_manutencao + comunicacao_assertiva) / 7.0) as media 
                    FROM avaliacoes
                ''', conn)['media'].iloc[0]
            except:
                media_sistema = 0
            conn.close()

        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("📈 Média do Sistema", f"{media_sistema:.2f}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🎯 Como usar o sistema:")
    st.markdown("""
    1. **Cadastrar Veículos**: Importe veículos via Excel ou cadastre individualmente
    2. **Cadastrar Motorista**: Adicione novos motoristas e associe a veículos
    3. **Editar Motorista**: Altere informações dos motoristas cadastrados
    4. **Avaliar Motorista**: Dê notas de 1 a 5 em diferentes critérios
    5. **Dashboard**: Veja o desempenho individual dos motoristas
    6. **Ranking**: Compare todos os motoristas do sistema
    """)

# Página Cadastrar Veículos
elif menu == "🚛 Cadastrar Veículos":
    st.markdown("### 🚛 Cadastrar Veículos")

    tab1, tab2, tab3 = st.tabs(["📤 Importar Excel", "➕ Cadastro Individual", "📋 Veículos Cadastrados"])

    with tab1:
        st.markdown("#### 📤 Importar Veículos via Excel")

        # Template para download
        col1, col2 = st.columns([2, 1])

        with col1:
            st.markdown("""
            **📋 Formato do arquivo Excel:**
            - O arquivo deve conter as seguintes colunas (exatamente com estes nomes):
            - **Placa**, **Modelo**, **Tipo de veículo**, **Próprio ou alugado**, **Cidade**, **Ano**
            """)

        with col2:
            # Criar template para download
            template_data = {
                'Placa': ['ABC-1234', 'DEF-5678'],
                'Modelo': ['Volkswagen Delivery', 'Mercedes Sprinter'],
                'Tipo de veículo': ['Caminhão', 'Van'],
                'Próprio ou alugado': ['Próprio', 'Alugado'],
                'Cidade': ['São Paulo', 'Rio de Janeiro'],
                'Ano': [2020, 2019]
            }
            template_df = pd.DataFrame(template_data)

            # Converter para Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                template_df.to_excel(writer, index=False, sheet_name='Veiculos')

            st.download_button(
                label="📥 Baixar Template Excel",
                data=output.getvalue(),
                file_name="template_veiculos.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.markdown("---")

        # Upload do arquivo
        uploaded_file = st.file_uploader(
            "📁 Selecione o arquivo Excel com os veículos:",
            type=['xlsx', 'xls'],
            help="Arquivo deve conter as colunas: Placa, Modelo, Tipo de veículo, Próprio ou alugado, Cidade, Ano"
        )

        if uploaded_file is not None:
            try:
                # Ler o arquivo Excel
                df_excel = pd.read_excel(uploaded_file)

                # Verificar se as colunas obrigatórias estão presentes
                colunas_obrigatorias = ['Placa', 'Modelo', 'Tipo de veículo', 'Próprio ou alugado', 'Cidade', 'Ano']
                colunas_faltando = [col for col in colunas_obrigatorias if col not in df_excel.columns]

                if colunas_faltando:
                    st.error(f"❌ Colunas faltando no arquivo: {', '.join(colunas_faltando)}")
                else:
                    st.success("✅ Arquivo válido! Preview dos dados:")
                    st.dataframe(df_excel.head(10))

                    col1, col2, col3 = st.columns([1, 1, 1])

                    with col2:
                        if st.button("📥 Importar Veículos", use_container_width=True, type="primary"):
                            sucessos, erros = importar_veiculos_excel(df_excel)

                            if sucessos > 0:
                                st.success(f"✅ {sucessos} veículos importados com sucesso!")

                            if erros:
                                st.error("❌ Erros encontrados:")
                                for erro in erros:
                                    st.write(f"• {erro}")

                            st.rerun()

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo: {str(e)}")

    with tab2:
        st.markdown("#### ➕ Cadastro Individual de Veículo")

        with st.form("cadastro_veiculo"):
            st.markdown('<div class="evaluation-form">', unsafe_allow_html=True)

            col1, col2 = st.columns(2)

            with col1:
                placa = st.text_input("🚗 Placa", placeholder="Ex: ABC-1234")
                modelo = st.text_input("🚙 Modelo", placeholder="Ex: Volkswagen Delivery")
                tipo_veiculo = st.selectbox("🚛 Tipo de Veículo",
                                            ["Caminhão", "Van", "Carro", "Moto", "Ônibus", "Outro"])

            with col2:
                proprio_alugado = st.selectbox("💰 Próprio ou Alugado", ["Próprio", "Alugado"])
                cidade = st.text_input("🏙️ Cidade", placeholder="Ex: São Paulo")
                ano = st.number_input("📅 Ano", min_value=1990, max_value=2030, value=2020)

            st.markdown('</div>', unsafe_allow_html=True)

            if st.form_submit_button("✅ Cadastrar Veículo", use_container_width=True):
                if placa and modelo and cidade:
                    if cadastrar_veiculo(placa.upper(), modelo, tipo_veiculo, proprio_alugado, cidade, ano):
                        st.success(f"✅ Veículo {placa.upper()} cadastrado com sucesso!")
                        st.rerun()
                    else:
                        st.error("❌ Erro: Esta placa já está cadastrada!")
                else:
                    st.error("❌ Por favor, preencha todos os campos obrigatórios!")

    with tab3:
        st.markdown("#### 📋 Veículos Cadastrados")

        veiculos_df = listar_veiculos()

        if not veiculos_df.empty:
            # Mostrar estatísticas
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("🚛 Total de Veículos", len(veiculos_df))

            with col2:
                proprios = len(veiculos_df[veiculos_df['proprio_alugado'] == 'Próprio'])
                st.metric("🏠 Próprios", proprios)

            with col3:
                alugados = len(veiculos_df[veiculos_df['proprio_alugado'] == 'Alugado'])
                st.metric("🏢 Alugados", alugados)

            with col4:
                tipos = veiculos_df['tipo_veiculo'].nunique()
                st.metric("📊 Tipos Diferentes", tipos)

            st.markdown("---")

            # Tabela de veículos
            st.dataframe(
                veiculos_df[['placa', 'modelo', 'tipo_veiculo', 'proprio_alugado', 'cidade', 'ano']],
                column_config={
                    'placa': 'Placa',
                    'modelo': 'Modelo',
                    'tipo_veiculo': 'Tipo',
                    'proprio_alugado': 'Status',
                    'cidade': 'Cidade',
                    'ano': 'Ano'
                },
                use_container_width=True
            )
        else:
            st.info("📝 Nenhum veículo cadastrado ainda. Use as abas acima para cadastrar!")

# Página Cadastrar Motorista
elif menu == "➕ Cadastrar Motorista":
    st.markdown("### ➕ Cadastrar Novo Motorista")

    # Verificar se há veículos cadastrados
    veiculos_df = listar_veiculos()

    if veiculos_df.empty:
        st.warning("⚠️ Nenhum veículo cadastrado! Cadastre veículos primeiro na seção 'Cadastrar Veículos'.")
    else:
        with st.form("cadastro_motorista"):
            st.markdown('<div class="evaluation-form">', unsafe_allow_html=True)

            col1, col2 = st.columns([2, 1])

            with col1:
                nome = st.text_input("👤 Nome Completo", placeholder="Digite o nome do motorista")

            with col2:
                # Criar opções de veículos
                veiculo_opcoes = {}
                for _, veiculo in veiculos_df.iterrows():
                    label = f"{veiculo['placa']} - {veiculo['modelo']} ({veiculo['cidade']})"
                    veiculo_opcoes[label] = veiculo['id']

                veiculo_selecionado = st.selectbox(
                    "🚛 Selecione o Veículo",
                    options=["Selecione um veículo..."] + list(veiculo_opcoes.keys())
                )

            st.markdown('</div>', unsafe_allow_html=True)

            if st.form_submit_button("✅ Cadastrar Motorista", use_container_width=True):
                if nome and veiculo_selecionado != "Selecione um veículo...":
                    veiculo_id = veiculo_opcoes[veiculo_selecionado]
                    cadastrar_motorista(nome, veiculo_id)
                    st.success(f"✅ Motorista {nome} cadastrado com sucesso!")
                    st.rerun()
                else:
                    st.error("❌ Por favor, preencha todos os campos!")

    # Listar motoristas cadastrados
    st.markdown("### 📋 Motoristas Cadastrados")
    motoristas_df = listar_motoristas()

    if not motoristas_df.empty:
        for _, motorista in motoristas_df.iterrows():
            veiculo_info = f"{motorista['placa']} - {motorista['modelo']}" if motorista[
                'placa'] else "Veículo não encontrado"

            st.markdown(f'''
            <div class="driver-card">
                <h4>👤 {motorista['nome']}</h4>
                <p><strong>🚛 Veículo:</strong> {veiculo_info}</p>
                <p><strong>🏙️ Cidade:</strong> {motorista['cidade'] if motorista['cidade'] else 'N/A'}</p>
                <p><strong>📅 Cadastrado em:</strong> {motorista['data_cadastro']}</p>
            </div>
            ''', unsafe_allow_html=True)
    else:
        st.info("👆 Nenhum motorista cadastrado ainda. Use o formulário acima!")

# Página Editar Motorista
elif menu == "✏️ Editar Motorista":
    st.markdown("### ✏️ Editar Motorista")

    motoristas_df = listar_motoristas()

    if motoristas_df.empty:
        st.warning("⚠️ Nenhum motorista cadastrado. Cadastre um motorista primeiro!")
    else:
        # Seleção do motorista para editar
        motorista_opcoes = {f"{row['nome']} - {row['placa']} {row['modelo']}": row['id']
                            for _, row in motoristas_df.iterrows()}

        motorista_selecionado = st.selectbox(
            "🚗 Selecione o motorista para editar:",
            options=["Selecione um motorista..."] + list(motorista_opcoes.keys())
        )

        if motorista_selecionado != "Selecione um motorista...":
            motorista_id = motorista_opcoes[motorista_selecionado]

            # Buscar dados atuais do motorista
            motorista_atual = obter_motorista_por_id(motorista_id)
            veiculos_df = listar_veiculos()

            if motorista_atual:
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown("#### 📝 Editar Informações")

                    with st.form("editar_motorista"):
                        st.markdown('<div class="evaluation-form">', unsafe_allow_html=True)

                        nome_novo = st.text_input(
                            "👤 Nome Completo",
                            value=motorista_atual[1],
                            placeholder="Digite o nome do motorista"
                        )

                        # Seleção de veículo
                        veiculo_opcoes = {}
                        veiculo_atual_label = None

                        for _, veiculo in veiculos_df.iterrows():
                            label = f"{veiculo['placa']} - {veiculo['modelo']} ({veiculo['cidade']})"
                            veiculo_opcoes[label] = veiculo['id']
                            if veiculo['id'] == motorista_atual[2]:  # veiculo_id atual
                                veiculo_atual_label = label

                        # Index do veículo atual
                        opcoes_lista = list(veiculo_opcoes.keys())
                        index_atual = opcoes_lista.index(veiculo_atual_label) if veiculo_atual_label else 0

                        veiculo_novo = st.selectbox(
                            "🚛 Veículo",
                            options=opcoes_lista,
                            index=index_atual
                        )

                        st.markdown('</div>', unsafe_allow_html=True)

                        col_btn1, col_btn2 = st.columns(2)

                        with col_btn1:
                            if st.form_submit_button("✅ Salvar Alterações", use_container_width=True):
                                if nome_novo and veiculo_novo:
                                    veiculo_id_novo = veiculo_opcoes[veiculo_novo]
                                    atualizar_motorista(motorista_id, nome_novo, veiculo_id_novo)
                                    st.success(f"✅ Motorista {nome_novo} atualizado com sucesso!")
                                    st.rerun()
                                else:
                                    st.error("❌ Por favor, preencha todos os campos!")

                        with col_btn2:
                            if st.form_submit_button("🗑️ Excluir Motorista", use_container_width=True,
                                                     type="secondary"):
                                st.session_state.confirmar_exclusao = True

                with col2:
                    st.markdown("#### ℹ️ Informações Atuais")
                    veiculo_info = f"{motorista_atual[3]} - {motorista_atual[4]}" if motorista_atual[
                        3] else "Sem veículo"

                    st.markdown(f'''
                    <div class="driver-card">
                        <p><strong>👤 Nome:</strong><br>{motorista_atual[1]}</p>
                        <p><strong>🚛 Veículo:</strong><br>{veiculo_info}</p>
                        <p><strong>📅 Cadastrado:</strong><br>{motorista_atual[5]}</p>
                    </div>
                    ''', unsafe_allow_html=True)

                    # Mostrar estatísticas do motorista
                    stats = calcular_estatisticas_motorista(motorista_id)
                    if stats:
                        st.markdown("#### 📊 Estatísticas")
                        st.metric("⭐ Nota Média", f"{stats['media_geral']:.2f}")
                        st.metric("📊 Avaliações", stats['total_avaliacoes'])

                # Confirmação de exclusão
                if st.session_state.get('confirmar_exclusao', False):
                    st.markdown("---")
                    st.error("⚠️ **ATENÇÃO:** Esta ação não pode ser desfeita!")
                    st.warning(
                        f"Tem certeza que deseja excluir o motorista **{motorista_atual[1]}** e todas as suas avaliações?")

                    col_conf1, col_conf2, col_conf3 = st.columns([1, 1, 1])

                    with col_conf1:
                        if st.button("✅ SIM, Excluir", use_container_width=True, type="primary"):
                            excluir_motorista(motorista_id)
                            st.success(f"✅ Motorista {motorista_atual[1]} excluído com sucesso!")
                            st.session_state.confirmar_exclusao = False
                            st.rerun()

                    with col_conf3:
                        if st.button("❌ Cancelar", use_container_width=True):
                            st.session_state.confirmar_exclusao = False
                            st.rerun()

# Página Avaliar Motorista
elif menu == "⭐ Avaliar Motorista":
    st.markdown("### ⭐ Avaliar Motorista")

    motoristas_df = listar_motoristas()

    if motoristas_df.empty:
        st.warning("⚠️ Nenhum motorista cadastrado. Cadastre um motorista primeiro!")
    else:
        # Seleção do motorista
        motorista_opcoes = {f"{row['nome']} - {row['placa']} {row['modelo']}": row['id']
                            for _, row in motoristas_df.iterrows()}

        motorista_selecionado = st.selectbox(
            "🚗 Selecione o motorista:",
            options=list(motorista_opcoes.keys())
        )

        if motorista_selecionado:
            motorista_id = motorista_opcoes[motorista_selecionado]

            with st.form("avaliacao_form"):
                st.markdown('<div class="evaluation-form">', unsafe_allow_html=True)

                st.markdown("#### 📊 Avalie os critérios de 1 a 5:")

                col1, col2 = st.columns(2)

                with col1:
                    custo_manutencao = st.select_slider(
                        "💰 Custo de Manutenção",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                    disponibilidade_frota = st.select_slider(
                        "🚛 Disponibilidade de Frota",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                    metas_producao = st.select_slider(
                        "🎯 Metas de Produção",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                    seguranca_trabalho = st.select_slider(
                        "🛡️ Segurança do Trabalho",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                with col2:
                    realizacao_checklist = st.select_slider(
                        "📋 Realização de Checklist",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                    conhecimento_manutencao = st.select_slider(
                        "🔧 Conhecimento Básico de Manutenção",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                    comunicacao_assertiva = st.select_slider(
                        "💬 Comunicação Assertiva",
                        options=[1, 2, 3, 4, 5],
                        value=5,
                        format_func=lambda x: "⭐" * x
                    )

                comentario = st.text_area(
                    "💬 Comentários (opcional)",
                    placeholder="Deixe um comentário sobre a experiência...",
                    height=100
                )

                avaliador = st.text_input(
                    "👤 Seu nome (opcional)",
                    placeholder="Digite seu nome"
                )

                st.markdown('</div>', unsafe_allow_html=True)

                # Preview da nota
                media_preview = (
                                            custo_manutencao + disponibilidade_frota + metas_producao + seguranca_trabalho + realizacao_checklist + conhecimento_manutencao + comunicacao_assertiva) / 7
                st.markdown(f"**📊 Nota Geral: {media_preview:.1f}/5.0** {'⭐' * int(media_preview)}")

                if st.form_submit_button("✅ Enviar Avaliação", use_container_width=True):
                    adicionar_avaliacao(
                        motorista_id, custo_manutencao, disponibilidade_frota, metas_producao,
                        seguranca_trabalho, realizacao_checklist, conhecimento_manutencao, comunicacao_assertiva,
                        comentario, avaliador or "Anônimo"
                    )
                    st.success("✅ Avaliação enviada com sucesso!")
                    st.balloons()
                    st.rerun()

# Página Dashboard
elif menu == "📊 Dashboard":
    st.markdown("### 📊 Dashboard do Motorista")

    motoristas_df = listar_motoristas()

    if motoristas_df.empty:
        st.warning("⚠️ Nenhum motorista cadastrado.")
    else:
        # Seleção do motorista
        motorista_opcoes = {f"{row['nome']} - {row['placa']} {row['modelo']}": row['id']
                            for _, row in motoristas_df.iterrows()}

        motorista_selecionado = st.selectbox(
            "🚗 Selecione o motorista:",
            options=list(motorista_opcoes.keys())
        )

        if motorista_selecionado:
            motorista_id = motorista_opcoes[motorista_selecionado]
            stats = calcular_estatisticas_motorista(motorista_id)

            if stats is None:
                st.info("📝 Este motorista ainda não possui avaliações.")
            else:
                # Métricas principais
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    st.metric("⭐ Nota Geral", f"{stats['media_geral']:.2f}")

                with col2:
                    st.metric("📊 Avaliações", stats['total_avaliacoes'])

                with col3:
                    if stats['ultima_avaliacao']:
                        ultima = pd.to_datetime(stats['ultima_avaliacao']).strftime('%d/%m/%Y')
                        st.metric("📅 Última Avaliação", ultima)

                with col4:
                    estrelas = "⭐" * int(stats['media_geral'])
                    st.metric("🌟 Classificação", estrelas)

                st.markdown("---")

                # Gráfico radar das categorias
                categorias = ['Custo Manutenção', 'Disponib. Frota', 'Metas Produção', 'Segurança Trabalho',
                              'Realiz. Checklist', 'Conhec. Manutenção', 'Comunicação']
                valores = [
                    stats['media_custo_manutencao'], stats['media_disponibilidade_frota'],
                    stats['media_metas_producao'], stats['media_seguranca_trabalho'],
                    stats['media_realizacao_checklist'], stats['media_conhecimento_manutencao'],
                    stats['media_comunicacao_assertiva']
                ]

                fig_radar = go.Figure()
                fig_radar.add_trace(go.Scatterpolar(
                    r=valores,
                    theta=categorias,
                    fill='toself',
                    name='Desempenho',
                    line_color='#1f77b4'
                ))

                fig_radar.update_layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 5])
                    ),
                    title="📊 Desempenho por Categoria",
                    height=400
                )

                col1, col2 = st.columns([2, 1])

                with col1:
                    st.plotly_chart(fig_radar, use_container_width=True)

                with col2:
                    st.markdown("#### 📈 Médias por Categoria")
                    categorias_completas = ['Custo de Manutenção', 'Disponibilidade de Frota', 'Metas de Produção',
                                            'Segurança do Trabalho', 'Realização de Checklist',
                                            'Conhec. Básico de Manutenção', 'Comunicação Assertiva']
                    for categoria, valor in zip(categorias_completas, valores):
                        st.markdown(f"**{categoria}:** {valor:.2f} {'⭐' * int(valor)}")

                # Histórico de avaliações
                st.markdown("#### 📝 Últimas Avaliações")
                avaliacoes_df = obter_avaliacoes_motorista(motorista_id)

                for _, avaliacao in avaliacoes_df.head(5).iterrows():
                    media_avaliacao = (avaliacao['custo_manutencao'] + avaliacao['disponibilidade_frota'] +
                                       avaliacao['metas_producao'] + avaliacao['seguranca_trabalho'] +
                                       avaliacao['realizacao_checklist'] + avaliacao['conhecimento_manutencao'] +
                                       avaliacao['comunicacao_assertiva']) / 7

                    data_formatada = pd.to_datetime(avaliacao['data_avaliacao']).strftime('%d/%m/%Y %H:%M')

                    with st.expander(f"⭐ {media_avaliacao:.1f} - {data_formatada} - por {avaliacao['avaliador']}"):
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write(f"💰 **Custo de Manutenção:** {avaliacao['custo_manutencao']}/5")
                            st.write(f"🚛 **Disponibilidade de Frota:** {avaliacao['disponibilidade_frota']}/5")
                            st.write(f"🎯 **Metas de Produção:** {avaliacao['metas_producao']}/5")
                            st.write(f"🛡️ **Segurança do Trabalho:** {avaliacao['seguranca_trabalho']}/5")

                        with col2:
                            st.write(f"📋 **Realização de Checklist:** {avaliacao['realizacao_checklist']}/5")
                            st.write(f"🔧 **Conhecimento de Manutenção:** {avaliacao['conhecimento_manutencao']}/5")
                            st.write(f"💬 **Comunicação Assertiva:** {avaliacao['comunicacao_assertiva']}/5")

                        if avaliacao['comentario']:
                            st.write(f"💬 **Comentário:** {avaliacao['comentario']}")

# Página Ranking
elif menu == "🏆 Ranking":
    st.markdown("### 🏆 Ranking Geral dos Motoristas")

    ranking_df = obter_ranking_geral()

    if ranking_df.empty:
        st.info("📊 Ainda não há avaliações suficientes para gerar o ranking.")
    else:
        st.markdown("#### 🥇 Melhores Motoristas")

        for i, (_, motorista) in enumerate(ranking_df.iterrows()):
            # Medalhas para o top 3
            medalha = ""
            if i == 0:
                medalha = "🥇"
            elif i == 1:
                medalha = "🥈"
            elif i == 2:
                medalha = "🥉"
            else:
                medalha = f"{i + 1}º"

            # Card do motorista
            col1, col2, col3 = st.columns([1, 3, 1])

            with col1:
                st.markdown(f"### {medalha}")

            with col2:
                st.markdown(f"**{motorista['nome']}**")
                veiculo_info = f"{motorista['placa']} - {motorista['modelo']}" if motorista['placa'] else "Sem veículo"
                st.markdown(f"🚛 {veiculo_info}")
                st.markdown(f"📊 {motorista['total_avaliacoes']} avaliações")

            with col3:
                nota = motorista['media_geral']
                st.markdown(f"### {nota:.2f}")
                st.markdown("⭐" * int(nota))

            st.markdown("---")

        # Gráfico do ranking
        if len(ranking_df) > 1:
            fig_ranking = px.bar(
                ranking_df.head(10),
                x='nome',
                y='media_geral',
                title='📊 Top 10 Motoristas',
                labels={'nome': 'Motorista', 'media_geral': 'Nota Média'},
                color='media_geral',
                color_continuous_scale='Viridis'
            )

            fig_ranking.update_layout(
                xaxis_tickangle=-45,
                height=500
            )

            st.plotly_chart(fig_ranking, use_container_width=True)

# Footer
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; padding: 2rem;'>"
    "🚗 Sistema de Avaliação de Motoristas - Desenvolvido com Streamlit"
    "</div>",
    unsafe_allow_html=True
)
