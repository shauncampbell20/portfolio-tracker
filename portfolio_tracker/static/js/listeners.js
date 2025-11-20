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
console.log(window.adj)
});
