$(document).ready(function() {
// Function to set active/inactive button classes
$(".btn-group > .btn").click(function() {
    $(this).siblings().removeClass("active");
    $(this).addClass("active");
});
});