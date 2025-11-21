// window.tf = "";
// window.adjust = "False";
// window.allocations = "sector";

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

btn1mo.addEventListener('click', function() {
window.tf = "30";
});
btn3mo.addEventListener('click', function() {
window.tf = "91";
});
btn6mo.addEventListener('click', function() {
window.tf = "182";
});
btn1yr.addEventListener('click', function() {
window.tf = "365";
});
btn3yr.addEventListener('click', function() {
window.tf = "1095";
});
btnall.addEventListener('click', function() {
window.tf = "";
});

btnadjust.addEventListener('click', function() {

if (window.adj == "True") {
    window.adj = "False";
} else {
    window.adj = "True";
}
console.log(window.adj);
});

btnnone.addEventListener('click', function() {
window.compare = "";
btnadjust.classList.remove('btn-primary')
btnadjust.classList.remove('disabled');
btnadjust.classList.add('btn-outline-primary');
btnadjust.classList.add('active');
});
btnsp.addEventListener('click', function() {
window.compare = "sp";
window.adj = "True";
btnadjust.classList.remove('btn-outline-primary')
btnadjust.classList.add('btn-primary');
btnadjust.classList.add('disabled');
});
btndji.addEventListener('click', function() {
window.compare = "dji";
window.adj = "True";
btnadjust.classList.remove('btn-outline-primary')
btnadjust.classList.add('btn-primary');
btnadjust.classList.add('disabled');
});
btnnasdaq.addEventListener('click', function() {
window.compare = "nasdaq";
window.adj = "True";
btnadjust.classList.remove('btn-outline-primary')
btnadjust.classList.add('btn-primary');
btnadjust.classList.add('disabled');
});
