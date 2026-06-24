console.log("HEmant");
document
  .getElementById("generate-report")
  .addEventListener("click", function () {
    document.getElementById("export-options").classList.remove("hidden");
  });
function toggleProfileMenu() {
    document.getElementById("profileDropdown").classList.toggle("show");
}

document.addEventListener("click", function (e) {
    if (!e.target.closest(".profile-menu")) {
        document.getElementById("profileDropdown").classList.remove("show");
    }
});

/* ===== DARK MODE PERSISTENCE ===== */
(function () {
    const theme = localStorage.getItem("theme");
    if (theme === "dark") {
        document.body.classList.add("dark");
    }
})();

function toggleDark() {
    document.body.classList.toggle("dark");
    localStorage.setItem(
        "theme",
        document.body.classList.contains("dark") ? "dark" : "light"
    );
}
