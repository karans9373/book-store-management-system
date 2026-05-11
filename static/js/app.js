const themeToggle = document.querySelector("[data-theme-toggle]");
if (themeToggle) {
    themeToggle.addEventListener("click", () => {
        const root = document.documentElement;
        const next = root.dataset.theme === "light" ? "dark" : "light";
        root.dataset.theme = next;
        localStorage.setItem("bookverse-theme", next);
    });
    const saved = localStorage.getItem("bookverse-theme");
    if (saved) document.documentElement.dataset.theme = saved;
}

document.querySelectorAll("[data-mood]").forEach((button) => {
    button.addEventListener("click", async () => {
        const mood = button.dataset.mood;
        const target = document.getElementById("mood-results");
        if (!target) return;
        target.innerHTML = "<p>Matching your reading mood...</p>";
        const response = await fetch("/api/mood-match", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ mood })
        });
        const books = await response.json();
        target.innerHTML = books.map((book) => `
            <a class="book-inline glass-card" href="/book/${book.id}">
                <div>
                    <strong>${book.title}</strong>
                    <span>${book.author}</span>
                    <p>${book.reason}</p>
                </div>
            </a>
        `).join("");
    });
});

const readerShell = document.querySelector("[data-reader]");
if (readerShell) {
    const pages = Array.from(readerShell.querySelectorAll(".reader-page"));
    const bookId = readerShell.dataset.bookId;
    const progressBar = readerShell.querySelector("[data-progress-bar]");
    const progressText = readerShell.querySelector("[data-progress-text]");
    const noteBox = document.getElementById("reader-note");
    let current = Number(localStorage.getItem(`reader-${bookId}-page`) || 1);
    let isAnimating = false;

    const renderPage = () => {
        pages.forEach((page, index) => {
            const isCurrent = index + 1 === current;
            page.classList.toggle("active", isCurrent);
            page.classList.toggle("current", isCurrent);
            page.classList.toggle("before", index + 1 < current);
            page.classList.toggle("after", index + 1 > current);
        });
        const pct = (current / pages.length) * 100;
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressText) progressText.textContent = `Page ${current} / ${pages.length}`;
        localStorage.setItem(`reader-${bookId}-page`, String(current));
    };

    const changePage = (nextPage) => {
        if (isAnimating || nextPage === current || nextPage < 1 || nextPage > pages.length) return;
        isAnimating = true;
        current = nextPage;
        renderPage();
        window.setTimeout(() => {
            isAnimating = false;
        }, 420);
    };

    readerShell.querySelector("[data-next-page]")?.addEventListener("click", () => {
        changePage(Math.min(current + 1, pages.length));
    });
    readerShell.querySelector("[data-prev-page]")?.addEventListener("click", () => {
        changePage(Math.max(current - 1, 1));
    });

    readerShell.querySelector(".flipbook")?.addEventListener("wheel", (event) => {
        event.preventDefault();
        if (Math.abs(event.deltaY) < 10) return;
        if (event.deltaY > 0) {
            changePage(Math.min(current + 1, pages.length));
        } else {
            changePage(Math.max(current - 1, 1));
        }
    }, { passive: false });

    document.addEventListener("keydown", (event) => {
        if (!readerShell.closest("body")) return;
        if (event.key === "ArrowRight") changePage(Math.min(current + 1, pages.length));
        if (event.key === "ArrowLeft") changePage(Math.max(current - 1, 1));
    });

    readerShell.querySelectorAll("[data-reader-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            const night = button.dataset.readerMode === "night";
            pages.forEach((page) => page.classList.toggle("night-page", night));
        });
    });

    const fontRange = readerShell.querySelector("[data-font-size]");
    fontRange?.addEventListener("input", () => {
        pages.forEach((page) => {
            const textBlock = page.querySelector(".reader-text");
            if (textBlock) textBlock.style.fontSize = `${fontRange.value}px`;
        });
    });

    readerShell.querySelector("[data-bookmark]")?.addEventListener("click", (event) => {
        localStorage.setItem(`reader-${bookId}-bookmark`, String(current));
        event.currentTarget.textContent = `Bookmarked page ${current}`;
    });

    readerShell.querySelector("[data-highlight]")?.addEventListener("click", () => {
        const active = pages.find((page) => page.classList.contains("active"));
        if (active) active.style.boxShadow = "0 0 0 3px rgba(255, 183, 3, 0.65), 0 18px 60px rgba(0,0,0,.26)";
    });

    const storedNote = localStorage.getItem(`reader-${bookId}-note`);
    if (storedNote && noteBox) noteBox.value = storedNote;
    noteBox?.addEventListener("input", () => localStorage.setItem(`reader-${bookId}-note`, noteBox.value));

    readerShell.querySelector("[data-reader-speak]")?.addEventListener("click", () => {
        const activeText = pages[current - 1]?.innerText || "";
        const speech = new SpeechSynthesisUtterance(activeText);
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(speech);
    });

    readerShell.querySelector("[data-companion]")?.addEventListener("click", async () => {
        const prompt = document.getElementById("companion-prompt")?.value || "";
        const response = await fetch("/api/companion", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({ prompt, book_id: bookId })
        });
        const data = await response.json();
        const responseTarget = document.getElementById("companion-response");
        if (responseTarget) responseTarget.textContent = data.answer;
    });

    renderPage();
}

function drawMiniChart(canvasId, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const labels = JSON.parse(canvas.dataset.labels || "[]");
    const values = JSON.parse(canvas.dataset.values || "[]");
    canvas.width = 640;
    canvas.height = 300;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const max = Math.max(...values, 1);
    const barWidth = 72;
    values.forEach((value, index) => {
        const x = 36 + index * 95;
        const h = (value / max) * 190;
        const y = 240 - h;
        ctx.fillStyle = color;
        ctx.fillRect(x, y, barWidth, h);
        ctx.fillStyle = "#9db0d3";
        ctx.fillText(labels[index] || "", x, 268, 80);
        ctx.fillText(String(value), x, y - 12);
    });
}

drawMiniChart("salesChart", "#ffb703");
drawMiniChart("visitorChart", "#4cc9f0");

async function attachAjaxCart(form) {
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        const button = form.querySelector("button[type='submit']");
        if (button?.disabled) return;
        const originalText = button?.textContent || "";
        if (button) {
            button.disabled = true;
            button.textContent = "Adding...";
        }
        try {
            const response = await fetch(form.action, {
                method: "POST",
                headers: {"X-Requested-With": "XMLHttpRequest"}
            });
            const data = await response.json();
            if (data.login_required && data.redirect) {
                window.location.href = data.redirect;
                return;
            }
            const flashStack = document.querySelector(".flash-stack") || document.createElement("div");
            if (!flashStack.classList.contains("flash-stack")) {
                flashStack.className = "flash-stack";
                const main = document.querySelector("main");
                main?.parentNode?.insertBefore(flashStack, main);
            }
            const flash = document.createElement("div");
            flash.className = "flash";
            flash.textContent = data.message || "Updated.";
            flashStack.prepend(flash);
            const cartLink = Array.from(document.querySelectorAll("a")).find((link) => link.textContent.trim().startsWith("Cart "));
            if (cartLink && typeof data.cart_count === "number") {
                cartLink.textContent = `Cart ${data.cart_count}`;
            }
        } catch (_error) {
            window.location.href = form.action;
        } finally {
            if (button) {
                button.disabled = false;
                button.textContent = originalText;
            }
        }
    });
}

document.querySelectorAll("form[data-ajax-cart]").forEach((form) => attachAjaxCart(form));

const assistantButton = document.querySelector("[data-store-assistant]");
if (assistantButton) {
    assistantButton.addEventListener("click", async () => {
        const promptInput = document.getElementById("assistantPrompt");
        const messageBox = document.getElementById("assistantMessage");
        const resultsBox = document.getElementById("assistantResults");
        const prompt = promptInput?.value.trim() || "";
        if (!prompt) {
            if (messageBox) messageBox.textContent = "Type a subject, title, or topic first.";
            return;
        }
        assistantButton.disabled = true;
        assistantButton.textContent = "Searching...";
        if (messageBox) messageBox.textContent = "Checking the current store inventory...";
        try {
            const response = await fetch("/api/store-assistant", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({ prompt })
            });
            const data = await response.json();
            if (messageBox) messageBox.textContent = data.message || "Results loaded.";
            if (resultsBox) {
                resultsBox.innerHTML = (data.books || []).map((book) => `
                    <article class="assistant-card glass-card">
                        <img src="${book.cover}" alt="${book.title}">
                        <div>
                            <strong>${book.title}</strong>
                            <p>${book.author} | ${book.genre}</p>
                            <p>${book.summary}</p>
                            <div class="meta-line">
                                <span>${book.rating} / 5</span>
                                <span>${book.stock} available</span>
                                <span>Rs. ${book.price}</span>
                            </div>
                            <div class="action-row">
                                <a class="ghost-btn" href="/book/${book.id}">Preview</a>
                                <form method="post" action="/cart/add/${book.id}" data-ajax-cart>
                                    <button class="primary-btn" type="submit">Add to cart</button>
                                </form>
                            </div>
                        </div>
                    </article>
                `).join("");
                resultsBox.querySelectorAll("form[data-ajax-cart]").forEach((form) => attachAjaxCart(form));
            }
        } catch (_error) {
            if (messageBox) messageBox.textContent = "Assistant search failed. Try again.";
        } finally {
            assistantButton.disabled = false;
            assistantButton.textContent = "Find books";
        }
    });
}
