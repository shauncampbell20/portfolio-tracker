function getHistory() {
    // function to get graph with fetch and render with Plotly
    // const url = "{{ url_for('main.history_endpoint') }}?tf="+tf;
    
    setTimeout(() => {
        histUrl = window.historyUrl+'?tf='+window.tf+'&adj='+window.adj+'&comp='+window.compare
        console.log(histUrl);
        fetch(histUrl)
        .then(resp => {
            if (resp.status == 204) {
            console.log('no content');
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
    document.addEventListener('DOMContentLoaded', getHistory);