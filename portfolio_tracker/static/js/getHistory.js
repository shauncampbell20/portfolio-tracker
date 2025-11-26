function getHistory() {
    // function to get graph with fetch and render with Plotly    
    setTimeout(() => {
        histUrl = window.historyUrl+'?tf='+window.tf+'&adj='+window.adj+'&comp='+window.compare+'&excluded='+window.excluded.join(',')
        fetch(histUrl)
        .then(resp => {
            if (resp.status == 204) {
            document.getElementById('history-graph').innerText = '';
            } else if (resp.ok) {
            return resp.json();
            } else {
            throw new Error(`HTTP error! status: ${resp.status}`);
            }
        })
        .then(data => {
            document.getElementById('history-graph').innerText = '';
            if (!data) return;
            var config = {displayModeBar: false};
            Plotly.setPlotConfig(config);
            Plotly.newPlot('history-graph', data, {}, config);
        })
    }, 10);

    };
    // document.addEventListener('DOMContentLoaded', getHistory);