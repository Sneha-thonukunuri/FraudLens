
const API_BASE = "http://127.0.0.1:8000";

const analysisPages = ["text", "screenshot", "url", "combined"];

function selectMode(mode) {
    if (!analysisPages.includes(mode)) {
        alert("Invalid analysis mode");
        return;
    }

    const analysisGrid = document.querySelector(".analysis-grid");

    if (analysisGrid) {
        analysisGrid.style.display = "none";
    }

    analysisPages.forEach((pageId) => {
        const page = document.getElementById(pageId);

        if (page) {
            page.style.display = "none";
        }
    });

    const selectedPage = document.getElementById(mode);

    if (selectedPage) {
        selectedPage.style.display = "block";
        window.location.hash = mode;
        selectedPage.scrollIntoView({ behavior: "smooth", block: "start" });
    }
}

function goBack() {
    window.location.hash = "analyze";
}

function showAnalysisSelection() {
    const analysisGrid = document.querySelector(".analysis-grid");

    if (analysisGrid) {
        analysisGrid.style.display = "grid";
    }

    analysisPages.forEach((pageId) => {
        const page = document.getElementById(pageId);

        if (page) {
            page.style.display = "none";
        }
    });
}

function handleNavigation() {
    const mode = window.location.hash.substring(1);

    if (analysisPages.includes(mode)) {
        selectModeWithoutChangingHash(mode);
    } else {
        showAnalysisSelection();
    }
}

function selectModeWithoutChangingHash(mode) {
    const analysisGrid = document.querySelector(".analysis-grid");

    if (analysisGrid) {
        analysisGrid.style.display = "none";
    }

    analysisPages.forEach((pageId) => {
        const page = document.getElementById(pageId);

        if (page) {
            page.style.display = pageId === mode ? "block" : "none";
        }
    });
}

window.addEventListener("DOMContentLoaded", () => {
    handleNavigation();
    setupForms();
});

window.addEventListener("hashchange", handleNavigation);

// Safely escape values before inserting them into HTML.
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, (char) => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function formatLabel(key) {
    return String(key)
        .replace(/([A-Z])/g, " $1")
        .replace(/[_-]/g, " ")
        .replace(/\b\w/g, (char) => char.toUpperCase());
}

// Display general API results as readable cards.
// Supports objects, arrays, strings and numeric values.


function renderGenericResult(data) {
    if (data === null || data === undefined) {
        return "<p>No data available</p>";
    }

    if (Array.isArray(data)) {
        if (!data.length) {
            return "<p>None detected</p>";
        }

        return `<ul>
            ${data.map(item => `
                <li>${typeof item === "object" && item !== null
                    ? renderGenericResult(item)
                    : escapeHTML(item)}</li>
            `).join("")}
        </ul>`;
    }

    if (typeof data !== "object") {
        return `<p>${escapeHTML(data)}</p>`;
    }

    const entries = Object.entries(data);

    const summaryKeys = ["score", "recommendation", "category"];

    const summary = entries.filter(([key]) =>
        summaryKeys.includes(key.toLowerCase())
    );

    const remaining = entries.filter(([key]) => {
        const lowerKey = key.toLowerCase();

        // Skip duplicated raw analysis details.
        if (lowerKey === "details") {
            return false;
        }

        return !summaryKeys.includes(lowerKey);
    });

    let html = "";

    if (summary.length) {
        html += `
            <div class="result-summary">
                ${summary.map(([key, value]) => `
                    <div class="result-item">
                        <span>${escapeHTML(formatLabel(key))}</span>
                        <strong>${escapeHTML(key.toLowerCase() === "score" ? (Number(value)<=1? Number(value)*100 : Number(value)).toFixed(0)+"%": value)}</strong>
                    </div>
                `).join("")}
            </div>
        `;
    }

    remaining.forEach(([key, value]) => {
        html += `
            <div class="result-detail">
                <h4>${escapeHTML(formatLabel(key))}</h4>
                ${renderGenericResult(value)}
            </div>
        `;
    });

    return html;
}



function renderResult(resultBox, title, data) {
    resultBox.className = "result-box";
    resultBox.style.display = "block";

   
let rawScore = Number(data.risk_score ?? data.score ?? 0);
let score;

// Preserve genuine intermediate backend scores.
// Recalculate when the backend only returns 0 or 1.
if (rawScore > 0 && rawScore < 1) {
    score = rawScore * 100;
} else if (rawScore > 1 && rawScore <= 100) {
    score = rawScore;
} else {
    const tactics = Array.isArray(data.tactics) ? data.tactics : [];
    const signals = Array.isArray(data.signals) ? data.signals : [];

    const recommendation = String(data.recommendation || "").toLowerCase();
    const category = String(data.category || "").toLowerCase();

    score = 5;
    score += tactics.length * 12;
    score += signals.length * 6;

    if (category !== "unknown" && category !== "") {
        score += 15;
    }

    if (recommendation === "block") {
        score += 20;
    } else if (recommendation === "review") {
        score += 10;
    }

    score = Math.min(100, score);
}

score = Math.max(0, Math.min(100, score));


    let level = "Low";
    let color = "#22c55e";

    if (score >= 75) {
        level = "Critical";
        color = "#ef4444";
    } else if (score >= 50) {
        level = "High";
        color = "#f97316";
    } else if (score >= 25) {
        level = "Medium";
        color = "#eab308";
    }
window.currentAnalysisReport = {
    title: title,
    score: score.toFixed(0),
    level: level,
    data: data
};
const securityTips = score >= 75
    ? [
        "Do not click suspicious links or reply to the message.",
        "Never share your OTP, password or banking details.",
        "Verify the message through the bank's official website or app.",
        "Report the suspicious message."
    ]
    : score >= 25
    ? [
        "Be careful before clicking any links.",
        "Verify the sender's identity.",
        "Never share personal or banking information."
    ]
    : [
        "No major fraud indicators were detected.",
        "Stay alert when opening links or sharing personal information."
    ];
    resultBox.innerHTML = `
        <div class="result-heading">
            <h3>${escapeHTML(title)}</h3>
            <p>Fraud detection report</p>
        </div>

        <div class="risk-meter">
            <h3>Visual Risk Meter</h3>
            <div class="risk-score">
                ${score.toFixed(0)}% - ${level} Risk
            </div>

            <div class="risk-track">
                <div class="risk-fill"
                     style="width: ${score}%; background: ${color};">
                </div>
            </div>
        </div>

        <div class="generic-results">
            ${renderGenericResult(data)}
        </div>

<div class="security-recommendations">
    <h3>Security Recommendations</h3>
    <ul>
        ${securityTips.map(tip => `<li>${tip}</li>`).join("")}
    </ul>
</div>

        <button class="analyze-button" onclick="downloadPDF()">
    Download Analysis Report (PDF)
</button>
    `;
}
function downloadPDF() {
    const report = window.currentAnalysisReport;

    if (!report) {
        alert("Please analyze something first.");
        return;
    }

    const { jsPDF } = window.jspdf;
    const pdf = new jsPDF();

    pdf.setFontSize(20);
    pdf.text("FraudLens Analysis Report", 20, 20);

    pdf.setFontSize(12);
    pdf.text("Analysis Type: " + report.title, 20, 40);
    pdf.text("Risk Score: " + report.score + "%", 20, 50);
    pdf.text("Risk Level: " + report.level, 20, 60);

    const details = JSON.stringify(report.data, null, 2);
    pdf.text(pdf.splitTextToSize(details, 170), 20, 75);

    pdf.save("FraudLens_Analysis_Report.pdf");
}
function showLoading(resultBox, message) {
    resultBox.className = "result-box loading-state";
    resultBox.style.display = "block";
    resultBox.textContent = message;
}

function showError(resultBox, message) {
    resultBox.className = "result-box error-state";
    resultBox.style.display = "block";
    resultBox.textContent = "Analysis failed: " + message;
}

async function sendJSONRequest(payload) {
    const response = await fetch(`${API_BASE}/analyze`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(
            typeof data.detail === "string"
                ? data.detail
                : "Analysis failed. Please try again."
        );
    }

    return data;
}

function setupJSONForm(formId, resultId, title, getPayload) {
    const form = document.getElementById(formId);
    const resultBox = document.getElementById(resultId);

    if (!form || !resultBox) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        showLoading(resultBox, "Analyzing... Please wait.");

        try {
            const payload = getPayload();
            const data = await sendJSONRequest(payload);

            renderResult(resultBox, title, data);
        } catch (error) {
            showError(resultBox, error.message);
        }
    });
}

function renderScreenshotResult(data) {
    const resultBox = document.getElementById("screenshotResult");

    const tactics = Array.isArray(data.tactics) ? data.tactics : [];
    const signals = Array.isArray(data.signals) ? data.signals : [];

    resultBox.className = "result-box";
    resultBox.style.display = "block";

let securityTips = [];

if (score >= 75) {
    securityTips = [
        "Do not click suspicious links or scan unknown QR codes.",
        "Never share your OTP, password or banking details.",
        "Do not make payments or respond to suspicious messages.",
        "Verify the sender through official channels."
    ];
} else if (score >= 50) {
    securityTips = [
        "Be cautious when opening links or attachments.",
        "Verify the sender before sharing information.",
        "Avoid making payments without verification."
    ];
} else if (score >= 25) {
    securityTips = [
        "Check the website address carefully.",
        "Verify unexpected requests through official channels.",
        "Never share confidential information."
    ];
} else {
    securityTips = [
        "No major warning signs detected.",
        "Continue to avoid unknown links and suspicious requests.",
        "Never share your OTP or password."
    ];
}

    resultBox.innerHTML = `
        <div class="result-heading">
            <h3>Screenshot Analysis Results</h3>
            <p>Fraud detection report</p>
        </div>

        <div class="result-summary">
            <div class="result-item">
                <span>Risk Score</span>
                <strong>${escapeHTML(data.score ?? "N/A")}</strong>
            </div>

            <div class="result-item">
                <span>Recommendation</span>
                <strong>${escapeHTML(data.recommendation ?? "N/A")}</strong>
            </div>

            <div class="result-item">
                <span>Category</span>
                <strong>${escapeHTML(data.category ?? "N/A")}</strong>
            </div>
        </div>

        <div class="result-detail">
            <h4>Detected Tactics</h4>
            <p>
                ${tactics.length
                    ? tactics.map(escapeHTML).join(", ")
                    : "None detected"}
            </p>
        </div>

        <div class="result-detail">
            <h4>Detected Signals</h4>
            <ul>
                ${signals.length
                    ? signals.map(signal => `<li>${escapeHTML(signal)}</li>`).join("")
                    : "<li>No signals detected</li>"}
            </ul>
        </div>

        <div class="result-detail">
            <h4>Explanation</h4>
            <p>${escapeHTML(data.explanation ?? "No explanation available")}</p>
        </div>
    `;
}

function setupScreenshotForm() {
    const form = document.getElementById("screenshotForm");
    const fileInput = document.getElementById("screenshotFile");
    const resultBox = document.getElementById("screenshotResult");

    if (!form || !fileInput || !resultBox) {
        return;
    }

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        if (!fileInput.files.length) {
            showError(resultBox, "Please select an image first.");
            return;
        }

        const formData = new FormData();
        formData.append("file", fileInput.files[0]);

        showLoading(resultBox, "Analyzing screenshot... Please wait.");

        try {
            const response = await fetch(`${API_BASE}/analyze/screenshot`, {
                method: "POST",
                body: formData
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    typeof data.detail === "string"
                        ? data.detail
                        : "Screenshot analysis failed."
                );
            }

            renderScreenshotResult(data);
        } catch (error) {
            showError(resultBox, error.message);
        }
    });
}

function setupForms() {
    setupJSONForm(
        "textForm",
        "textResult",
        "Text Analysis Results",
        () => ({
            text: document.getElementById("textInput").value
        })
    );

    setupJSONForm(
        "urlForm",
        "urlResult",
        "URL Analysis Results",
        () => ({
            url: document.getElementById("urlInput").value
        })
    );

    setupJSONForm(
        "combinedForm",
        "combinedResult",
        "Combined Analysis Results",
        () => ({
            text: document.getElementById("combinedText").value,
            url: document.getElementById("combinedUrl").value
        })
    );

    setupScreenshotForm();
}
