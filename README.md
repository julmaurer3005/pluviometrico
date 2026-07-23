# Monitor Pluviométrico - Rio Grande do Sul (RS)

Este é um sistema automatizado para monitoramento diário do volume de chuva (precipitação acumulada em mm) em tempo real de 6 municípios do Rio Grande do Sul: **Ijuí, Cruz Alta, Panambi, Ibirubá, Frederico Westphalen e Palmeira das Missões**.

O painel suporta **duas fontes meteorológicas de pesquisa**:
1. **Open-Meteo API:** Totalmente livre, sem chaves e com histórico retroativo completo de 30 dias.
2. **OpenWeatherMap One Call API 4.0:** Utiliza uma chave de API própria.

---

## 🛠️ Tecnologias Utilizadas

- **Linguagem:** Python 3
- **Banco de Dados:** SQLite (arquivo local `rain_data.db` com separação de fontes)
- **Framework Web:** Flask (API REST local e servidor do Dashboard dinâmico)
- **Visualização de Gráficos:** Chart.js
- **Iconografia:** Bootstrap Icons (CDN)

---

## 🔑 Configuração da Chave OpenWeatherMap (Grátis até 1.000 chamadas/dia)

A OpenWeatherMap One Call API 4.0 oferece **1.000 requisições gratuitas por dia**, mas exige ativação no site:
1. Acesse o site da [OpenWeatherMap](https://openweathermap.org/) e faça login.
2. Vá para a aba **Billing** (Faturamento), insira os dados do cartão de crédito e assine o plano **"One Call by Call"**.
3. **Importante:** No próprio painel, configure o limite de chamadas diárias (Daily Limit) para **1.000**. Isso bloqueia novas chamadas antes de gerar qualquer cobrança, garantindo o serviço **100% gratuito**.
4. Crie o arquivo `.env` (instruções abaixo) e adicione a chave. Se o plano não for assinado, a chamada retornará erro `401 Unauthorized`.

---

## 🚀 Instalação e Execução

### 1. Instalar as Dependências
Instale as bibliotecas necessárias usando o `pip`:
```bash
python -m pip install -r requirements.txt
```

### 2. Configurar o Arquivo `.env`
Crie um arquivo chamado `.env` na raiz do projeto contendo a sua chave:
```env
OPENWEATHERMAP_API_KEY=sua_chave_de_api_aqui
```
*(Nota: O arquivo já foi pré-criado no seu ambiente com a chave fornecida).*

### 3. Rodar as Coletas Iniciais (Banco SQLite)
Para preencher o histórico do **Open-Meteo**:
```bash
python collector.py 30 open-meteo
```

Para preencher a previsão do **OpenWeatherMap** (requer assinatura One Call ativa):
```bash
python collector.py 0 openweathermap
```

### 4. Executar o Servidor Web do Dashboard
Inicie a aplicação Flask:
```bash
python app.py
```
Acesse o painel abrindo seu navegador e digitando:
**[http://localhost:5000](http://localhost:5000)**

Você poderá navegar entre as duas abas usando o menu superior e sincronizar cada uma de forma independente!

---

## ⏰ Configurando Automação Diária (Execução Automática)

Configure o agendador de tarefas do seu sistema operacional para rodar o script `collector.py` uma vez por dia para manter ambas as fontes sincronizadas.

### No Windows (Agendador de Tarefas)
Crie duas tarefas básicas configuradas para **Iniciar um Programa** na pasta `c:\Users\User\Desktop\pluviometrico`:
- **Tarefa 1 (Open-Meteo):**
  - **Programa:** `python`
  - **Argumentos:** `collector.py 2 open-meteo` (atualiza hoje e ontem)
- **Tarefa 2 (OpenWeatherMap):**
  - **Programa:** `python`
  - **Argumentos:** `collector.py 0 openweathermap` (atualiza previsões/hoje)

### No Linux ou macOS (Cron)
```bash
0 8 * * * /usr/bin/python3 /caminho/do/projeto/pluviometrico/collector.py 2 open-meteo >> /caminho/do/projeto/pluviometrico/collector.log 2>&1
0 8:30 * * * /usr/bin/python3 /caminho/do/projeto/pluviometrico/collector.py 0 openweathermap >> /caminho/do/projeto/pluviometrico/collector.log 2>&1
```

---

## 📊 Estrutura do Banco de Dados (SQLite)

A tabela `precipitation` dentro do banco `rain_data.db` separa as fontes e previne duplicações através da restrição `UNIQUE(data, cidade_ibge, fonte)`.

### Colunas da Tabela:
- `id`: Chave primária.
- `data`: Data do registro no formato `YYYY-MM-DD`.
- `cidade_nome`: Nome amigável do município (`Ijuí`, `Cruz Alta`, etc).
- `cidade_ibge`: Código IBGE único identificador de 7 dígitos.
- `cidade_lat`: Latitude usada na requisição.
- `cidade_lon`: Longitude usada na requisição.
- `precipitacao_acumulada_mm`: Volume acumulado de chuva nas 24h.
- `atualizado_em`: Timestamp ISO do momento da inserção.
- `fonte`: Nome da fonte identificando a origem (`open-meteo` ou `openweathermap`).
