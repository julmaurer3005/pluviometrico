// Cores dedicadas para cada cidade no gráfico
const CORES_CIDADES = {
    "Ijuí": "#3b82f6",          // Azul
    "Cruz Alta": "#8b5cf6",     // Violeta
    "Panambi": "#10b981",       // Esmeralda
    "Ibirubá": "#f59e0b",       // Âmbar
    "Frederico Westphalen": "#ec4899", // Rosa
    "Palmeira das Missões": "#06b6d4"  // Ciano
};

// Captura a fonte meteorológica ativa a partir do atributo do body
const activeSource = document.body.dataset.source || 'open-meteo';
let historicoChart = null;

// Efeito de Holofote (Spotlight) nos Cards de KPI
function setupCardSpotlight() {
    const cards = document.querySelectorAll('.kpi-card');
    cards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            card.style.setProperty('--x', `${x}px`);
            card.style.setProperty('--y', `${y}px`);
        });
    });
}

// Mostra notificações toast
function showToast(message, isError = false) {
    const toast = document.getElementById('toast-feedback');
    const toastMessage = document.getElementById('toast-message');
    const toastIcon = toast.querySelector('i');
    
    toastMessage.textContent = message;
    
    if (isError) {
        toast.classList.add('error');
        toastIcon.className = 'bi bi-exclamation-triangle-fill';
    } else {
        toast.classList.remove('error');
        toastIcon.className = 'bi bi-check-circle-fill';
    }
    
    toast.classList.add('show');
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 6000); // 6 segundos de visibilidade para ler mensagens de erro longas da API
}

// Busca e renderiza os dados resumo na tabela e nos cards
async function loadSummary() {
    try {
        const response = await fetch(`/api/summary/${activeSource}`);
        if (!response.ok) throw new Error("Erro ao carregar resumo");
        const data = await response.json();
        
        const tableBody = document.getElementById('table-body');
        
        // Verifica se há dados reais salvos no banco
        const hasData = data.some(item => item.hoje > 0 || item.ontem > 0 || item.media_7d > 0);
        
        if (!hasData && activeSource === 'openweathermap') {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" style="text-align: center; color: var(--text-secondary); padding: 2rem;">
                        Sem dados para esta fonte. Certifique-se de que sua chave de API possui o plano "One Call by Call" ativo e clique em "Sincronizar Agora".
                    </td>
                </tr>
            `;
        }
        
        tableBody.innerHTML = '';
        let totalChuvaHoje = 0;
        let maxChuvaHoje = -1;
        let cidadeMaxChuva = "-";
        
        data.forEach(item => {
            totalChuvaHoje += item.hoje;
            
            if (item.hoje > maxChuvaHoje) {
                maxChuvaHoje = item.hoje;
                cidadeMaxChuva = item.cidade_nome;
            }
            
            // Renderização da linha da tabela
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>
                    <div class="city-cell">
                        ${item.cidade_nome}
                        <span class="ibge">IBGE: ${item.cidade_ibge}</span>
                    </div>
                </td>
                <td style="text-align: right;" class="precip-val ${item.hoje > 0 ? 'rainy' : 'dry'}">
                    ${item.hoje.toFixed(1)} mm
                </td>
                <td style="text-align: right;" class="precip-val ${item.ontem > 0 ? 'rainy' : 'dry'}">
                    ${item.ontem.toFixed(1)} mm
                </td>
                <td style="text-align: right;" class="precip-val ${item.media_7d > 0 ? 'rainy' : 'dry'}">
                    ${item.media_7d.toFixed(1)} mm
                </td>
            `;
            tableBody.appendChild(tr);
        });
        
        // Atualiza os Cards de KPIs
        const mediaChuvaHoje = totalChuvaHoje / data.length;
        
        document.getElementById('val-total-chuva').textContent = `${totalChuvaHoje.toFixed(1)} mm`;
        document.getElementById('val-media-chuva').textContent = `${mediaChuvaHoje.toFixed(1)} mm`;
        
        if (maxChuvaHoje > 0) {
            document.getElementById('val-max-chuva').textContent = `${maxChuvaHoje.toFixed(1)} mm`;
            document.getElementById('lbl-max-cidade').innerHTML = `<i class="bi bi-geo-alt-fill"></i> Registrado em ${cidadeMaxChuva}`;
        } else {
            document.getElementById('val-max-chuva').textContent = "0.0 mm";
            document.getElementById('lbl-max-cidade').innerHTML = `<i class="bi bi-geo-alt"></i> Tempo seco na região`;
        }
        
        // Atualiza a legenda de última atualização
        const now = new Date();
        document.getElementById('lbl-ultima-atualizacao').textContent = `Atualizado: ${now.toLocaleTimeString('pt-BR', {hour: '2-digit', minute:'2-digit'})}`;
        
    } catch (error) {
        console.error("Erro no carregamento do resumo:", error);
        showToast("Erro ao carregar dados do painel.", true);
    }
}

// Busca e plota o histórico de 30 dias com Chart.js
async function loadHistoricalChart() {
    try {
        const response = await fetch(`/api/historical/${activeSource}`);
        if (!response.ok) throw new Error("Erro ao carregar histórico");
        const data = await response.json();
        
        const ctx = document.getElementById('chart-historico').getContext('2d');
        
        // Formatar datas para exibição legível (ex: "dd/mm")
        const formatedDates = data.dates.map(dateStr => {
            const parts = dateStr.split('-');
            return `${parts[2]}/${parts[1]}`;
        });
        
        // Configura datasets com cores específicas e styling premium
        const datasets = data.datasets.map(ds => {
            const cor = CORES_CIDADES[ds.label] || "#ffffff";
            return {
                label: ds.label,
                data: ds.data,
                borderColor: cor,
                backgroundColor: cor + "15", // Transparência de fill
                borderWidth: 2,
                pointRadius: 2,
                pointHoverRadius: 5,
                tension: 0.35, // Curvas suaves
                fill: false
            };
        });
        
        // Se o gráfico já existe, reconstrói para limpar dados antigos
        if (historicoChart) {
            historicoChart.destroy();
        }
        
        historicoChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: formatedDates,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#94a3b8',
                            font: {
                                family: 'Plus Jakarta Sans',
                                size: 11,
                                weight: '600'
                            },
                            boxWidth: 12,
                            usePointStyle: true,
                            pointStyle: 'circle'
                        }
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        titleColor: '#f8fafc',
                        bodyColor: '#f8fafc',
                        titleFont: { family: 'Outfit', weight: '700' },
                        bodyFont: { family: 'Plus Jakarta Sans' },
                        borderColor: 'rgba(255,255,255,0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                return ` ${context.dataset.label}: ${context.raw.toFixed(1)} mm`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.03)'
                        },
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Plus Jakarta Sans', size: 10 }
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.03)'
                        },
                        ticks: {
                            color: '#64748b',
                            font: { family: 'Plus Jakarta Sans', size: 10 },
                            callback: function(value) {
                                return value + ' mm';
                            }
                        },
                        title: {
                            display: true,
                            text: 'Precipitação Acumulada',
                            color: '#64748b',
                            font: { family: 'Plus Jakarta Sans', size: 10, weight: '600' }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error("Erro ao plotar histórico:", error);
    }
}

// Dispara a rotina de sincronização manual via API
async function triggerSync() {
    const btnSync = document.getElementById('btn-sync');
    
    // Inicia estado de loading no botão
    btnSync.disabled = true;
    btnSync.classList.add('loading');
    btnSync.innerHTML = `<i class="bi bi-arrow-clockwise" style="animation: spin 1.5s linear infinite; display: inline-block;"></i> Sincronizando...`;
    
    try {
        const response = await fetch(`/api/sync/${activeSource}`, { method: 'POST' });
        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            showToast(result.message);
            // Recarrega todos os dados
            await loadSummary();
            await loadHistoricalChart();
        } else {
            throw new Error(result.message || "Falha na sincronização");
        }
    } catch (error) {
        console.error(error);
        showToast(error.message, true);
    } finally {
        // Restaura o botão
        btnSync.disabled = false;
        btnSync.classList.remove('loading');
        btnSync.innerHTML = `<i class="bi bi-arrow-clockwise"></i> Sincronizar Agora`;
    }
}

// Inicialização do Painel
document.addEventListener('DOMContentLoaded', () => {
    setupCardSpotlight();
    loadSummary();
    loadHistoricalChart();
    
    document.getElementById('btn-sync').addEventListener('click', triggerSync);
    
    // Exportação padrão ao clicar no botão principal do header redirecionando para a fonte ativa
    const btnExport = document.getElementById('btn-export');
    if (btnExport) {
        btnExport.addEventListener('click', () => {
            window.location.href = `/api/export/csv/${activeSource}`;
        });
    }
});
