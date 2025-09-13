document.addEventListener("DOMContentLoaded", function() {
    // Dark/Light mode toggle
    const toggleBtn = document.getElementById("theme-toggle");
    if(toggleBtn){
        toggleBtn.addEventListener("click", () => {
            document.body.classList.toggle("dark-mode");
        });
    }

    // Modal
    const modal = document.getElementById("modal");
    if(modal){
        document.querySelectorAll(".view-details").forEach(btn => {
            btn.addEventListener("click", () => {
                modal.querySelector(".modal-content").innerText = btn.dataset.full;
                modal.style.display = "block";
            });
        });
        modal.querySelector(".close").addEventListener("click", () => {
            modal.style.display = "none";
        });
    }

    // Realtime search
    const searchInput = document.getElementById("search");
    if(searchInput){
        searchInput.addEventListener("keyup", () => {
            const filter = searchInput.value.toLowerCase();
            document.querySelectorAll(".transaction-row").forEach(row => {
                row.style.display = row.innerText.toLowerCase().includes(filter) ? "" : "none";
            });
        });
    }
});
