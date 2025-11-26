function getAllocations() {
    // function to get graph with fetch and render with Plotly
    Url = window.allocationUrl+'?disp='+window.disp+'&excluded='+window.excluded.join(',')
    fetch(Url)
        .then(resp => {
            if (resp.status == 204) {
            document.getElementById('allocations-graph').innerText = '';
            } else if (resp.ok) {
            return resp.json();
            } else {
            throw new Error(`HTTP error! status: ${resp.status}`);
            }
        })
        .then(data => {
            document.getElementById('allocations-graph').innerText = '';
            if (!data) return;
            var config = {displayModeBar: false};
            Plotly.setPlotConfig(config);
            Plotly.newPlot('allocations-graph', data, {}, config);
        })
    };
    document.addEventListener('DOMContentLoaded', getAllocations);