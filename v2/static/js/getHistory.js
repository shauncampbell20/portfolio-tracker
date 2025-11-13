function getHistory(tf) {
    // function to get graph with fetch and render with Plotly
    // const url = "{{ url_for('main.history_endpoint') }}?tf="+tf;
    fetch(window.historyUrl+tf)
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
    };
    document.addEventListener('DOMContentLoaded', getHistory);