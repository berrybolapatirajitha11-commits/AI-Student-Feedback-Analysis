
let trendChart = null;
let categoryChart = null;

const $ = (id) => document.getElementById(id);

function showToast(message) {
    const toast = $("toast");
    toast.textContent = message;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}

async function getJSON(url) {
    const response = await fetch(url);
    if (!response.ok) {
        throw new Error("Could not load data.");
    }
    return response.json();
}


// LOAD DASHBOARD
async function loadDashboard() {
    try {
        const data = await getJSON("/api/dashboard");

        $("totalFeedback").textContent = data.total;
        $("averageRating").textContent = data.average + " / 5";
        $("totalUsers").textContent = data.users;
        $("satisfactionRate").textContent = data.satisfaction + "%";

        renderTrendChart(data.trend_labels, data.trend_values);
        renderCategoryChart(data.categories);
        renderFeedbackTable(data.recent);

        await loadInsights();

    } catch (error) {
        showToast("Unable to load dashboard. Please refresh.");
        console.error(error);
    }
}


// FEEDBACK TREND CHART
function renderTrendChart(labels, values) {
    const ctx = $("trendChart").getContext("2d");

    if (trendChart) {
        trendChart.destroy();
    }

    const gradient = ctx.createLinearGradient(0, 0, 0, 250);
    gradient.addColorStop(0, "rgba(217,154,174,0.55)");
    gradient.addColorStop(1, "rgba(143,174,216,0.02)");

    trendChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Feedback",
                data: values,
                borderColor: "#D99AAE",
                backgroundColor: gradient,
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: "#8FAED8"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                x: {
                    ticks: { color: "#DCE4F0" },
                    grid: { color: "rgba(143,174,216,0.10)" }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        color: "#DCE4F0",
                        precision: 0
                    },
                    grid: { color: "rgba(143,174,216,0.12)" }
                }
            }
        }
    });
}


// CATEGORY CHART
function renderCategoryChart(categories) {
    const ctx = $("categoryChart").getContext("2d");

    if (categoryChart) {
        categoryChart.destroy();
    }

    const labels = categories.map(item => item.name);
    const values = categories.map(item => item.total);

    categoryChart = new Chart(ctx, {
        type: "doughnut",
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: [
                    "#D99AAE",
                    "#8FAED8",
                    "#71849A",
                    "#526A91",
                    "#B8A0BC",
                    "#354765"
                ],
                borderColor: "#242B49",
                borderWidth: 3
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: "65%",
            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        color: "#F8F8FC",
                        padding: 13,
                        usePointStyle: true
                    }
                }
            }
        }
    });
}


// RECENT FEEDBACK TABLE
function renderFeedbackTable(items) {
    const table = $("feedbackTable");
    table.innerHTML = "";

    if (!items.length) {
        table.innerHTML =
            '<tr><td colspan="4" class="empty-row">No feedback submitted yet.</td></tr>';
        return;
    }

    items.forEach(item => {
        const row = document.createElement("tr");

        const name = document.createElement("td");
        name.textContent = item.name;

        const comment = document.createElement("td");
        comment.textContent = item.comment;

        const rating = document.createElement("td");
        rating.textContent = "★".repeat(item.rating) +
            "☆".repeat(5 - item.rating);

        const sentimentCell = document.createElement("td");
        const badge = document.createElement("span");
        badge.className = "sentiment " + item.sentiment.toLowerCase();
        badge.textContent = item.sentiment;

        sentimentCell.appendChild(badge);

        row.append(name, comment, rating, sentimentCell);
        table.appendChild(row);
    });
}


// LOAD ANALYSIS
async function loadInsights() {
    try {
        const data = await getJSON("/api/insights");

        $("positiveCount").textContent = data.positive;
        $("negativeCount").textContent = data.negative;
        $("neutralCount").textContent = data.neutral;
        $("topCategory").textContent = data.top_category;
        $("insightMessage").textContent = data.message;

    } catch (error) {
        console.error(error);
        $("insightMessage").textContent = "Analysis could not be loaded.";
    }
}


// SUBMIT FEEDBACK
$("feedbackForm").addEventListener("submit", async function(event) {
    event.preventDefault();

    const button = $("submitBtn");
    const message = $("formMessage");

    const payload = {
        name: $("name").value.trim(),
        email: $("email").value.trim(),
        category: $("category").value,
        rating: $("rating").value,
        comment: $("comment").value.trim()
    };

    button.disabled = true;
    button.innerHTML = '<i class="bi bi-hourglass-split"></i> Submitting...';
    message.textContent = "";
    message.classList.remove("error");

    try {
        const response = await fetch("/api/feedback", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(payload)
        });

        const result = await response.json();

        if (!response.ok || !result.success) {
            throw new Error(result.message || "Submission failed.");
        }

        message.textContent =
            "Submitted! Sentiment: " + result.sentiment;

        $("feedbackForm").reset();
        showToast("Feedback saved successfully!");

        await loadDashboard();

    } catch (error) {
        message.textContent = error.message;
        message.classList.add("error");
    } finally {
        button.disabled = false;
        button.innerHTML =
            '<i class="bi bi-send-fill"></i> Submit Feedback';
    }
});


// REFRESH BUTTON
$("refreshBtn").addEventListener("click", async function() {
    await loadDashboard();
    showToast("Dashboard refreshed!");
});


// REFRESH RECENT FEEDBACK
$("viewAllBtn").addEventListener("click", async function() {
    await loadDashboard();
    showToast("Feedback list updated.");
});


// GENERATE ANALYSIS BUTTON
$("analyzeBtn").addEventListener("click", async function() {
    const button = $("analyzeBtn");

    button.disabled = true;
    button.innerHTML =
        '<i class="bi bi-hourglass-split"></i> Analyzing...';

    await loadInsights();

    button.disabled = false;
    button.innerHTML =
        '<i class="bi bi-stars"></i> Generate Analysis';

    showToast("Feedback analysis completed!");
});


// SIDEBAR ACTIVE LINK
document.querySelectorAll(".nav-link").forEach(link => {
    link.addEventListener("click", function() {
        document.querySelectorAll(".nav-link").forEach(item => {
            item.classList.remove("active");
        });

        this.classList.add("active");
    });
});


// INITIAL DASHBOARD LOAD
document.addEventListener("DOMContentLoaded", loadDashboard);

