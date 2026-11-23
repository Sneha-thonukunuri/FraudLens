
function selectMode(mode) {
    const pages = {
        text: "text",
        screenshot: "screenshot",
        url: "url",
        combined: "combined"
    };

    const selectedPageId = pages[mode];

    if (!selectedPageId) {
        alert("Invalid analysis mode");
        return;
    }

    // Hide the analysis selection cards
    const analysisGrid = document.querySelector(".analysis-grid");

    if (analysisGrid) {
        analysisGrid.style.display = "none";
    }

    // Hide all analysis pages
    Object.values(pages).forEach(function (pageId) {
        const page = document.getElementById(pageId);

        if (page) {
            page.style.display = "none";
        }
    });

    // Display the selected page
    const selectedPage = document.getElementById(selectedPageId);

    if (!selectedPage) {
        alert("Page not found: " + selectedPageId);
        return;
    }

    selectedPage.style.display = "block";

    // Update browser URL
    window.location.hash = selectedPageId;
}

// Return to analysis selection when opening #analyze
window.addEventListener("hashchange", function () {
    if (window.location.hash === "#analyze") {
        const analysisGrid = document.querySelector(".analysis-grid");

        if (analysisGrid) {
            analysisGrid.style.display = "grid";
        }

        document.querySelectorAll(".analysis-section").forEach(function (page) {
            if (page.id !== "analyze") {
                page.style.display = "none";
            }
        });
    }
});

// Handle direct page opening or refreshing
window.addEventListener("DOMContentLoaded", function () {
    const mode = window.location.hash.substring(1);

    if (["text", "screenshot", "url", "combined"].includes(mode)) {
        selectMode(mode);
    }
});

// Combined Analysis
document.getElementById("combinedForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const text = document.getElementById("combinedText").value;
    const url = document.getElementById("combinedUrl").value;
    const resultBox = document.getElementById("combinedResult");

    resultBox.textContent = "Analyzing...";

    try {
        const response = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: text,
                url: url
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Analysis failed");
        }

        resultBox.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        resultBox.textContent = "Error: " + error.message;
    }
});

// URL Analysis
document.getElementById("urlForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const url = document.getElementById("urlInput").value;
    const resultBox = document.getElementById("urlResult");

    resultBox.textContent = "Analyzing...";

    try {
        const response = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Analysis failed");
        }

        resultBox.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        resultBox.textContent = "Error: " + error.message;
    }
});

// Text Analysis
document.getElementById("textForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const text = document.getElementById("textInput").value;
    const resultBox = document.getElementById("textResult");

    resultBox.textContent = "Analyzing...";

    try {
        const response = await fetch("http://127.0.0.1:8000/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text: text })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Analysis failed");
        }

        resultBox.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        resultBox.textContent = "Error: " + error.message;
    }
});

// Screenshot Analysis
document.getElementById("screenshotForm").addEventListener("submit", async function (event) {
    event.preventDefault();

    const fileInput = document.getElementById("screenshotFile");
    const resultBox = document.getElementById("screenshotResult");

    if (!fileInput.files.length) {
        resultBox.textContent = "Please select an image first.";
        return;
    }

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    resultBox.textContent = "Analyzing screenshot...";

    try {
        const response = await fetch("http://127.0.0.1:8000/analyze/screenshot", {
            method: "POST",
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Screenshot analysis failed");
        }

        resultBox.textContent = JSON.stringify(data, null, 2);

    } catch (error) {
        resultBox.textContent = "Error: " + error.message;
    }
});
