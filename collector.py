import requests
import sys
import os
import time
from datetime import datetime, timezone, timedelta
import database

# Importa a definição compartilhada de cidades para evitar redundância e importação circular
from database import CIDADES

def get_env_var(key, default=None):
    """Lê uma variável de configuração a partir de um arquivo .env local ou do sistema."""
    env_path = '.env'
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    parts = line.split('=', 1)
                    if len(parts) == 2 and parts[0].strip() == key:
                        return parts[1].strip()
    return os.environ.get(key, default)

def fetch_precipitation_for_city_meteo(city, past_days=30):
    """Consulta a Open-Meteo API (Livre) para obter dados pluviométricos."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": city["lat"],
        "longitude": city["lon"],
        "daily": "precipitation_sum",
        "timezone": "America/Sao_Paulo",
        "past_days": past_days
    }
    
    headers = {
        "User-Agent": "PluviometricoApp/1.0 (https://github.com/julmaurer3005/pluviometrico)"
    }
    
    try:
        print(f"[*] [Open-Meteo] Consultando {city['nome']} (IBGE: {city['ibge']})...", flush=True)
        response = requests.get(url, params=params, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        if "daily" not in data or "time" not in data["daily"] or "precipitation_sum" not in data["daily"]:
            print(f"[!] Erro: Resposta inválida da Open-Meteo para {city['nome']}.", flush=True)
            return 0
            
        times = data["daily"]["time"]
        precip_sums = data["daily"]["precipitation_sum"]
        
        saved_count = 0
        for i in range(len(times)):
            data_str = times[i]
            valor_mm = precip_sums[i] if precip_sums[i] is not None else 0.0
            
            database.save_precipitation(
                data=data_str,
                cidade_nome=city["nome"],
                cidade_ibge=city["ibge"],
                lat=city["lat"],
                lon=city["lon"],
                valor_mm=valor_mm,
                fonte='open-meteo'
            )
            saved_count += 1
            
        print(f"[+] [Open-Meteo] Sucesso: {saved_count} registros diários salvos para {city['nome']}.", flush=True)
        return saved_count
        
    except requests.exceptions.RequestException as e:
        print(f"[!] Erro ao consultar Open-Meteo para {city['nome']}: {e}", file=sys.stderr, flush=True)
        return 0

def fetch_precipitation_for_city_owm(city, api_key):
    """
    Consulta a OpenWeatherMap One Call API 4.0 para obter dados pluviométricos.
    Utiliza a chave de API fornecida e o faturamento configurado.
    """
    url = "https://api.openweathermap.org/data/4.0/onecall/timeline/1day"
    params = {
        "lat": city["lat"],
        "lon": city["lon"],
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        print(f"[*] [OpenWeatherMap 4.0] Consultando {city['nome']} (IBGE: {city['ibge']})...")
        response = requests.get(url, params=params, timeout=10)
        
        # Tratamento explícito de chaves de API não-assinadas ou limites de faturamento
        if response.status_code == 401:
            raise PermissionError(
                "A chave de API não possui a assinatura ativa do plano 'One Call by Call'. "
                "Cadastre um cartão e assine o plano (1.000 chamadas/dia grátis) nas configurações da OpenWeatherMap."
            )
        elif response.status_code == 402:
            raise PermissionError(
                "Erro de Faturamento (Payment Required). Verifique o faturamento no painel da OpenWeatherMap."
            )
            
        response.raise_for_status()
        
        data = response.json()
        if "data" not in data or not isinstance(data["data"], list):
            print(f"[!] Erro: Formato de resposta inválido da OpenWeatherMap (4.0) para {city['nome']}.")
            return 0
            
        timezone_offset = data.get("timezone_offset", -10800) # Default fuso RS (-3h)
        tz = timezone(timedelta(seconds=timezone_offset))
        
        saved_count = 0
        for item in data["data"]:
            dt = item["dt"]
            # Timestamps diários na OWM 4.0 referem-se ao início do dia em UTC (00:00:00 UTC)
            dt_object = datetime.fromtimestamp(dt, tz=timezone.utc)
            data_str = dt_object.strftime('%Y-%m-%d')
            
            # OpenWeatherMap omite a chave 'rain' caso não haja expectativa de chuva
            valor_mm = item.get("rain", 0.0)
            
            database.save_precipitation(
                data=data_str,
                cidade_nome=city["nome"],
                cidade_ibge=city["ibge"],
                lat=city["lat"],
                lon=city["lon"],
                valor_mm=valor_mm,
                fonte='openweathermap'
            )
            saved_count += 1
            
        print(f"[+] [OpenWeatherMap 4.0] Sucesso: {saved_count} registros diários salvos para {city['nome']}.")
        return saved_count
        
    except requests.exceptions.RequestException as e:
        print(f"[!] Erro de conexão/API ao consultar OpenWeatherMap para {city['nome']}: {e}", file=sys.stderr)
        return 0

def run_sync(past_days=30, fonte='open-meteo'):
    """Executa a sincronização completa filtrada por fonte ('open-meteo' ou 'openweathermap')."""
    print("==================================================")
    print(f"Iniciando Coleta Pluviométrica ({fonte.upper()}): {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("==================================================")
    
    # Garante tabela inicializada
    database.init_db()
    
    total_records = 0
    success_cities = 0
    
    if fonte == 'open-meteo':
        for city in CIDADES:
            count = fetch_precipitation_for_city_meteo(city, past_days=past_days)
            if count > 0:
                success_cities += 1
                total_records += count
            time.sleep(0.5)  # Pequeno delay para evitar Rate Limit (HTTP 429) no Open-Meteo
                
    elif fonte == 'openweathermap':
        api_key = get_env_var("OPENWEATHERMAP_API_KEY") or get_env_var("OPENWEATHER_API_KEY")
        if not api_key:
            raise ValueError(
                "A chave de API da OpenWeatherMap não foi encontrada! "
                "Configure a variável de ambiente OPENWEATHERMAP_API_KEY ou OPENWEATHER_API_KEY."
            )
            
        for city in CIDADES:
            count = fetch_precipitation_for_city_owm(city, api_key)
            if count > 0:
                success_cities += 1
                total_records += count
    else:
        print(f"[!] Erro: Fonte climática desconhecida: {fonte}", file=sys.stderr)
        return {"cidades_sucesso": 0, "total_cidades": len(CIDADES), "registros_salvos": 0}
        
    print("==================================================")
    print(f"Resumo da Execução:")
    print(f"- Cidades com sucesso: {success_cities}/{len(CIDADES)}")
    print(f"- Total de registros salvos/atualizados: {total_records}")
    print("==================================================\n")
    
    return {
        "cidades_sucesso": success_cities,
        "total_cidades": len(CIDADES),
        "registros_salvos": total_records
    }

if __name__ == "__main__":
    # Suporte a execução manual:
    # python collector.py [dias] [fonte]
    # Ex: python collector.py 30 open-meteo
    # Ex: python collector.py 0 openweathermap
    days = 30
    fonte = 'open-meteo'
    
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass
            
    if len(sys.argv) > 2:
        fonte = sys.argv[2]
        
    run_sync(past_days=days, fonte=fonte)
