// window.tf = "";
// window.adjust = "False";
// window.allocations = "sector";

document.addEventListener("DOMContentLoaded", function() {
    console.log('running onload');
    window.disp = "sector";
    window.excluded = [];
    getHistory();
    getAllocations();
    getPositionsTable();
    getMetricsTable();
    getSummary();

    const btn1mo = document.getElementById('btn-1mo');
    const btn3mo = document.getElementById('btn-3mo');
    const btn6mo = document.getElementById('btn-6mo');
    const btn1yr = document.getElementById('btn-1yr');
    const btn3yr = document.getElementById('btn-3yr');
    const btnall = document.getElementById('btn-all');
    const btnadjust = document.getElementById('btn-adjust');
    const btnnone = document.getElementById('compare-none');
    const btnsp = document.getElementById('compare-sp');
    const btndji = document.getElementById('compare-dji');
    const btnnasdaq = document.getElementById('compare-nasdaq');
    const btnsector = document.getElementById('btn-sector');
    const btnasset = document.getElementById('btn-asset');
    const checkboxes = document.querySelectorAll('input[type="checkbox"]');

    checkboxes.forEach(function(checkbox) {
            checkbox.addEventListener('change', function() {
                symb = this.id.split('-')[0];
                if (!this.checked) {
                    window.excluded.push(symb);
                } else {
                    window.excluded = window.excluded.filter(item => item !== symb);
                }
            console.log(window.excluded);
            getPositionsTable();
            getHistory();
            getAllocations();
            getMetricsTable();
            getSummary();
        });
    });

    // History Time-frame buttons
    btn1mo.addEventListener('click', function() {
    window.tf = "30";
    getHistory();
    });
    btn3mo.addEventListener('click', function() {
    window.tf = "91";
    getHistory();
    });
    btn6mo.addEventListener('click', function() {
    window.tf = "182";
    getHistory();
    });
    btn1yr.addEventListener('click', function() {
    window.tf = "365";
    getHistory();
    });
    btn3yr.addEventListener('click', function() {
    window.tf = "1095";
    getHistory();
    });
    btnall.addEventListener('click', function() {
    window.tf = "";
    getHistory();
    });

    // Adjust buy/sell button
    btnadjust.addEventListener('click', function() {
        if (window.adj == "True") {
            window.adj = "False";
        } else {
            window.adj = "True";
        }
        getHistory();
    });

    // Compare buttons
    btnnone.addEventListener('click', function() {
        window.compare = "";
        btnadjust.classList.remove('btn-primary')
        btnadjust.classList.remove('disabled');
        btnadjust.classList.add('btn-outline-primary');
        btnadjust.classList.add('active');
        getHistory();
        getMetricsTable();
    });
    btnsp.addEventListener('click', function() {
        window.compare = "sp";
        window.adj = "True";
        btnadjust.classList.remove('btn-outline-primary')
        btnadjust.classList.add('btn-primary');
        btnadjust.classList.add('disabled');
        getHistory();
        getMetricsTable();
    });
    btndji.addEventListener('click', function() {
        window.compare = "dji";
        window.adj = "True";
        btnadjust.classList.remove('btn-outline-primary')
        btnadjust.classList.add('btn-primary');
        btnadjust.classList.add('disabled');
        getHistory();
        getMetricsTable();
    });
    btnnasdaq.addEventListener('click', function() {
        window.compare = "nasdaq";
        window.adj = "True";
        btnadjust.classList.remove('btn-outline-primary')
        btnadjust.classList.add('btn-primary');
        btnadjust.classList.add('disabled');
        getHistory();
        getMetricsTable();
    });

    // Sector/asset buttons
    btnsector.addEventListener('click', function() {
        window.disp = "sector";
        getAllocations();
    });
    btnasset.addEventListener('click', function() {
        window.disp = "asset";
        getAllocations();
    });




});