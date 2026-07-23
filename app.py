import io
import csv
from flask import Flask, render_template, jsonify, send_file, make_response
import database
import collector

app = Flask(__name__)

# Inicializar e migrar o banco na inicialização
database.init_db()

@app.route('/')
def index():
    """Serva a interface principal configurada para a fonte Open-Meteo."""
    return render_template('index.html', source='open-meteo')

@app.route('/openweathermap')
def openweathermap():
    """Serva a interface principal configurada para a fonte OpenWeatherMap."""
    return render_template('index.html', source='openweathermap')

@app.route('/api/summary/<fonte>')
def api_summary(fonte):
    """API para obter o resumo diário das 6 cidades baseado na fonte selecionada."""
    if fonte not in ['open-meteo', 'openweathermap']:
        return jsonify({"error": "Fonte inválida"}), 400
    try:
        summary_data = database.get_dashboard_summary(fonte=fonte)
        return jsonify(summary_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/historical/<fonte>')
def api_historical(fonte):
    """API para obter o histórico de 30 dias formatado para o Chart.js com base na fonte."""
    if fonte not in ['open-meteo', 'openweathermap']:
        return jsonify({"error": "Fonte inválida"}), 400
    try:
        raw_data = database.get_historical_data(days=30, fonte=fonte)
        
        # Encontra datas únicas ordenadas
        dates = sorted(list(set(item['data'] for item in raw_data)))
        
        # Agrupa os valores de chuva por cidade
        cidades_data = {}
        for item in raw_data:
            cidade = item['cidade_nome']
            if cidade not in cidades_data:
                cidades_data[cidade] = {}
            cidades_data[cidade][item['data']] = item['precipitacao_acumulada_mm']
            
        # Monta os datasets do Chart.js
        datasets = []
        for cidade, values in cidades_data.items():
            data_points = []
            for date in dates:
                data_points.append(values.get(date, 0.0))
            
            datasets.append({
                "label": cidade,
                "data": data_points
            })
            
        return jsonify({
            "dates": dates,
            "datasets": datasets
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sync/<fonte>', methods=['POST'])
def api_sync(fonte):
    """Gatilho manual para sincronizar a fonte de dados selecionada."""
    if fonte not in ['open-meteo', 'openweathermap']:
        return jsonify({"error": "Fonte inválida"}), 400
    try:
        # Se for Open-Meteo, busca 30 dias. Se for OpenWeatherMap, o One Call sincroniza a previsão
        result = collector.run_sync(past_days=30, fonte=fonte)
        return jsonify({
            "status": "success",
            "message": f"Dados ({fonte}) sincronizados com sucesso!",
            "details": result
        })
    except PermissionError as e:
        # Captura erros de faturamento ou autenticação da chave OWM
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 401
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Erro na sincronização ({fonte}): {str(e)}"
        }), 500

@app.route('/api/export/csv/<fonte>')
def export_csv(fonte):
    """Exporta histórico em CSV de uma fonte específica."""
    if fonte not in ['open-meteo', 'openweathermap']:
        return make_response("Fonte inválida", 400)
    try:
        raw_data = database.get_historical_data(days=365, fonte=fonte)
        
        si = io.StringIO()
        cw = csv.writer(si)
        cw.writerow(['Data', 'Nome da Cidade', 'Código IBGE', 'Precipitação Acumulada (mm)', 'Fonte'])
        
        for row in raw_data:
            cw.writerow([
                row['data'], 
                row['cidade_nome'], 
                row['cidade_ibge'], 
                row['precipitacao_acumulada_mm'],
                fonte
            ])
            
        output = make_response(si.getvalue())
        output.headers["Content-Disposition"] = f"attachment; filename=chuvas_rs_{fonte}.csv"
        output.headers["Content-type"] = "text/csv; charset=utf-8"
        return output
    except Exception as e:
        return make_response(f"Erro ao exportar CSV: {str(e)}", 500)

@app.route('/api/export/json/<fonte>')
def export_json(fonte):
    """Exporta histórico em JSON de uma fonte específica."""
    if fonte not in ['open-meteo', 'openweathermap']:
        return jsonify({"error": "Fonte inválida"}), 400
    try:
        raw_data = database.get_historical_data(days=365, fonte=fonte)
        response = jsonify(raw_data)
        response.headers["Content-Disposition"] = f"attachment; filename=chuvas_rs_{fonte}.json"
        return response
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
