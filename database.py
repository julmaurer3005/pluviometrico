import sqlite3
import os
from datetime import datetime

DATABASE_NAME = 'rain_data.db'

# Definição compartilhada das 6 cidades do RS
CIDADES = [
    {"nome": "Ijuí", "ibge": "4310207", "lat": -28.3878, "lon": -53.9147},
    {"nome": "Cruz Alta", "ibge": "4306106", "lat": -28.6386, "lon": -53.6064},
    {"nome": "Panambi", "ibge": "4313904", "lat": -28.2925, "lon": -53.5017},
    {"nome": "Ibirubá", "ibge": "4310009", "lat": -28.6278, "lon": -53.0900},
    {"nome": "Frederico Westphalen", "ibge": "4308508", "lat": -27.3589, "lon": -53.3939},
    {"nome": "Palmeira das Missões", "ibge": "4313706", "lat": -27.8989, "lon": -53.3139}
]

def get_db_connection():
    """Retorna uma conexão ativa com o banco de dados SQLite."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Inicializa o banco de dados. 
    Se a tabela antiga existir sem a coluna 'fonte', ela é migrada/recriada.
    """
    conn = get_db_connection()
    try:
        # Verifica se a tabela existe e se possui a coluna 'fonte'
        cursor = conn.cursor()
        table_exists = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='precipitation'"
        ).fetchone()
        
        needs_recreate = False
        if table_exists:
            # Verifica colunas
            columns_info = cursor.execute("PRAGMA table_info(precipitation)").fetchall()
            columns = [col['name'] for col in columns_info]
            if 'fonte' not in columns:
                needs_recreate = True
                
        if needs_recreate:
            print("[*] Migração: Detectado esquema antigo. Recriando tabela para suportar fontes diferentes...")
            cursor.execute("DROP TABLE precipitation")
            conn.commit()
            
        # Cria a tabela com a nova coluna e restrição UNIQUE de 3 colunas
        query = """
        CREATE TABLE IF NOT EXISTS precipitation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,                  -- Formato YYYY-MM-DD
            cidade_nome TEXT NOT NULL,           -- Nome da cidade
            cidade_ibge TEXT NOT NULL,           -- Código IBGE
            cidade_lat REAL NOT NULL,            -- Latitude
            cidade_lon REAL NOT NULL,            -- Longitude
            precipitacao_acumulada_mm REAL NOT NULL, 
            atualizado_em TEXT NOT NULL,         
            fonte TEXT NOT NULL,                 -- 'open-meteo' ou 'openweathermap'
            UNIQUE(data, cidade_ibge, fonte)     -- Evita duplicidade por data, cidade e fonte
        );
        """
        cursor.execute(query)
        conn.commit()
    finally:
        conn.close()

def save_precipitation(data, cidade_nome, cidade_ibge, lat, lon, valor_mm, fonte):
    """
    Salva ou atualiza um registro de precipitação diária para uma cidade e fonte específicas.
    """
    query = """
    INSERT OR REPLACE INTO precipitation (
        data, cidade_nome, cidade_ibge, cidade_lat, cidade_lon, precipitacao_acumulada_mm, atualizado_em, fonte
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    """
    timestamp = datetime.now().isoformat()
    conn = get_db_connection()
    try:
        conn.execute(query, (data, cidade_nome, cidade_ibge, lat, lon, valor_mm, timestamp, fonte))
        conn.commit()
    finally:
        conn.close()

def get_historical_data(days=30, fonte='open-meteo'):
    """Retorna o histórico de chuvas dos últimos X dias para todas as cidades de uma fonte específica."""
    query = """
        SELECT data, cidade_nome, cidade_ibge, precipitacao_acumulada_mm
        FROM precipitation
        WHERE data >= date('now', ?, 'localtime') AND fonte = ?
        ORDER BY data ASC, cidade_nome ASC;
    """
    param = f"-{days} days"
    conn = get_db_connection()
    try:
        rows = conn.execute(query, (param, fonte)).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

def get_dashboard_summary(fonte='open-meteo'):
    """
    Retorna a sumarização diária filtrada por fonte.
    Se não houver registros para a fonte no banco, retorna as cidades com valores zerados.
    """
    conn = get_db_connection()
    summary = []
    try:
        # Busca todas as cidades que já possuem dados para essa fonte no banco
        cidades_db = conn.execute(
            "SELECT DISTINCT cidade_nome, cidade_ibge FROM precipitation WHERE fonte = ?", 
            (fonte,)
        ).fetchall()
        
        # Fallback para usar a lista padrão se o banco estiver vazio para a fonte
        if not cidades_db:
            cidades_list = [{"cidade_nome": c["nome"], "cidade_ibge": c["ibge"]} for c in CIDADES]
        else:
            cidades_list = [{"cidade_nome": c["cidade_nome"], "cidade_ibge": c["cidade_ibge"]} for c in cidades_db]
            
        for cidade in cidades_list:
            ibge = cidade['cidade_ibge']
            nome = cidade['cidade_nome']
            
            # Chuva de hoje
            chuva_hoje = conn.execute(
                "SELECT precipitacao_acumulada_mm FROM precipitation WHERE cidade_ibge = ? AND data = date('now', 'localtime') AND fonte = ?",
                (ibge, fonte)
            ).fetchone()
            
            # Chuva de ontem
            chuva_ontem = conn.execute(
                "SELECT precipitacao_acumulada_mm FROM precipitation WHERE cidade_ibge = ? AND data = date('now', '-1 day', 'localtime') AND fonte = ?",
                (ibge, fonte)
            ).fetchone()
            
            # Média dos últimos 7 dias (excluindo hoje)
            media_7d = conn.execute(
                """
                SELECT AVG(precipitacao_acumulada_mm) as media 
                FROM precipitation 
                WHERE cidade_ibge = ? 
                  AND data >= date('now', '-7 days', 'localtime')
                  AND data < date('now', 'localtime')
                  AND fonte = ?
                """,
                (ibge, fonte)
            ).fetchone()
            
            summary.append({
                'cidade_nome': nome,
                'cidade_ibge': ibge,
                'hoje': chuva_hoje['precipitacao_acumulada_mm'] if chuva_hoje else 0.0,
                'ontem': chuva_ontem['precipitacao_acumulada_mm'] if chuva_ontem else 0.0,
                'media_7d': round(media_7d['media'], 2) if media_7d and media_7d['media'] is not None else 0.0
            })
            
        # Ordena por nome da cidade para manter padrão na interface
        return sorted(summary, key=lambda x: x['cidade_nome'])
    finally:
        conn.close()
