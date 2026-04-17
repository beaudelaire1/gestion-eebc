
document.addEventListener('DOMContentLoaded', function() {
    const selectedYear = '2025';
    const donationsCard = document.getElementById('donationsChart').closest('.card');

    // Configuration du graphique d'évolution des dons
    const donationsCtx = document.getElementById('donationsChart').getContext('2d');
    
    // Données initiales (12 mois)
    const donationsData = {
        labels: JSON.parse(document.getElementById('donations-labels').textContent),
        datasets: [{
            label: 'Recettes de fonctionnement (€)',
            data: JSON.parse(document.getElementById('donations-data').textContent),
            borderColor: 'rgb(10, 54, 255)',
            backgroundColor: 'rgba(10, 54, 255, 0.1)',
            borderWidth: 3,
            fill: true,
            tension: 0.4,
            pointBackgroundColor: 'rgb(10, 54, 255)',
            pointBorderColor: '#ffffff',
            pointBorderWidth: 2,
            pointRadius: 6,
            pointHoverRadius: 8
        }]
    };
    
    const donationsChart = new Chart(donationsCtx, {
        type: 'line',
        data: donationsData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgb(10, 54, 255)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: false,
                    callbacks: {
                        label: function(context) {
                            return 'Recettes: ' + context.parsed.y.toLocaleString('fr-FR') + ' €';
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#64748B',
                        font: {
                            size: 12,
                            weight: '500'
                        }
                    }
                },
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(100, 116, 139, 0.1)'
                    },
                    ticks: {
                        color: '#64748B',
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        callback: function(value) {
                            return value.toLocaleString('fr-FR') + ' €';
                        }
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            },
            elements: {
                point: {
                    hoverBackgroundColor: 'rgb(10, 54, 255)'
                }
            }
        }
    });
    
    // Gestion du changement de période
    document.getElementById('donationsChartPeriod').addEventListener('change', function() {
        const months = this.value;
        
        // Faire une requête AJAX pour récupérer les nouvelles données
        fetch(`/app/finance/dashboard/chart-data/?months=${months}&year=${selectedYear}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': 'o08tnUqYAaB96dIVGd5erl111flUbxHG2n0gUK7ZRjbxeSeg6oNebl2miy6ovys3'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Mettre à jour le graphique
            donationsChart.data.labels = data.labels;
            donationsChart.data.datasets[0].data = data.data;
            donationsChart.update('active');
            
            // Mettre à jour les statistiques
            const donationsStatsRow = donationsCard.querySelector('.row.mt-3');
            donationsStatsRow.querySelector('.col-4:nth-child(1) .fs-6').textContent = 
                data.total.toLocaleString('fr-FR') + '€';
            donationsStatsRow.querySelector('.col-4:nth-child(2) .fs-6').textContent = 
                Math.round(data.average).toLocaleString('fr-FR') + '€';
            donationsStatsRow.querySelector('.col-4:nth-child(3) .fs-6').textContent = 
                (data.data[data.data.length - 1] || 0).toLocaleString('fr-FR') + '€';
        })
        .catch(error => {
            console.error('Erreur lors du chargement des données:', error);
        });
    });
    
    // Configuration du graphique de répartition des dépenses
    const expensesCtx = document.getElementById('expensesChart').getContext('2d');
    
    // Données initiales (12 mois)
    const expensesData = {
        labels: ['Salaire du Pasteur', 'CGSS Guyane - URSSAF', 'AG2R - Retraite complémentaire', 'Club biblique', 'Chrono Clim - Climatisation', 'Groupama Assurance', 'Musique et Son - Sono', 'Loyer Macouria', 'Guyanaise Distribution', 'EDF - Électricité', 'Autres'],
        datasets: [{
            data: [15443.5, 4148.0, 3273.52, 2500.0, 2470.0, 2461.24, 2226.0, 2000.0, 1172.07, 1060.65, 5949.21],
            backgroundColor: ['#EF4444', '#F59E0B', '#10B981', '#3B82F6', '#8B5CF6', '#EC4899', '#06B6D4', '#84CC16', '#F97316', '#6366F1'],
            borderWidth: 2,
            borderColor: '#ffffff',
            hoverBorderWidth: 3,
            hoverBorderColor: '#ffffff'
        }]
    };
    
    const expensesChart = new Chart(expensesCtx, {
        type: 'doughnut',
        data: expensesData,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        font: {
                            size: 12,
                            weight: '500'
                        },
                        color: '#64748B'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.1)',
                    borderWidth: 1,
                    cornerRadius: 8,
                    displayColors: true,
                    callbacks: {
                        label: function(context) {
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = ((context.parsed / total) * 100).toFixed(1);
                            return context.label + ': ' + context.parsed.toLocaleString('fr-FR') + ' € (' + percentage + '%)';
                        }
                    }
                }
            },
            cutout: '60%',
            elements: {
                arc: {
                    borderWidth: 2
                }
            }
        }
    });
    
    // Gestion du changement de période pour les dépenses
    document.getElementById('expensesChartPeriod').addEventListener('change', function() {
        const months = this.value;
        
        // Faire une requête AJAX pour récupérer les nouvelles données
        fetch(`/app/finance/dashboard/chart-data/?months=${months}&type=expenses&year=${selectedYear}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': 'o08tnUqYAaB96dIVGd5erl111flUbxHG2n0gUK7ZRjbxeSeg6oNebl2miy6ovys3'
            }
        })
        .then(response => response.json())
        .then(data => {
            // Mettre à jour le graphique
            expensesChart.data.labels = data.labels;
            expensesChart.data.datasets[0].data = data.data;
            expensesChart.data.datasets[0].backgroundColor = data.colors;
            expensesChart.update('active');
            
            // Mettre à jour les statistiques
            const expensesStatsRow = document.querySelector('#expensesChart').closest('.card').querySelector('.row.mt-3');
            expensesStatsRow.querySelector('.col-6:nth-child(1) .fs-6').textContent = 
                data.total.toLocaleString('fr-FR') + '€';
            expensesStatsRow.querySelector('.col-6:nth-child(2) .fs-6').textContent = 
                data.count;
        })
        .catch(error => {
            console.error('Erreur lors du chargement des données des dépenses:', error);
        });
    });
});
