const API_BASE_URL = (window.BOOKVERSE_CONFIG?.apiBaseUrl || "http://127.0.0.1:5000").replace(/\/$/, "");
const appRoot = document.getElementById("app");
let sessionState = {
    authenticated: false,
    role: "guest",
    user: { name: "Guest", email: "", phone: "" },
    cart_count: 0,
    wishlist_count: 0,
    is_admin: false
};

function escapeHtml(value = "") {
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
}

function formatCurrency(value) {
    return `Rs. ${Number(value || 0)}`;
}

function setFlash(message, kind = "info") {
    const stack = document.getElementById("flashStack");
    if (!stack || !message) return;
    const node = document.createElement("div");
    node.className = "flash";
    if (kind === "error") node.style.borderColor = "rgba(255, 99, 132, 0.4)";
    node.textContent = message;
    stack.prepend(node);
    setTimeout(() => node.remove(), 4000);
}

async function api(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        credentials: "include",
        headers: {
            "Content-Type": "application/json",
            ...(options.headers || {})
        },
        ...options
    });
    let data = {};
    try {
        data = await response.json();
    } catch (_error) {
        data = {};
    }
    if (!response.ok) {
        const error = new Error(data.message || "Request failed.");
        error.status = response.status;
        error.payload = data;
        throw error;
    }
    return data;
}

async function refreshSession() {
    sessionState = await api("/api/session");
    renderSessionChip();
    return sessionState;
}

function renderSessionChip() {
    const chip = document.getElementById("accountChip");
    const authAction = document.getElementById("authAction");
    const cartCount = document.getElementById("cartCount");
    const wishlistCount = document.getElementById("wishlistCount");
    document.querySelectorAll("[data-admin-link]").forEach((link) => {
        link.hidden = !sessionState.is_admin;
    });
    document.querySelectorAll("[data-customer-link]").forEach((link) => {
        link.hidden = sessionState.is_admin;
    });
    cartCount.textContent = sessionState.cart_count || 0;
    wishlistCount.textContent = sessionState.wishlist_count || 0;
    chip.innerHTML = sessionState.authenticated
        ? `<strong>${escapeHtml(sessionState.user.name)}</strong><small>${escapeHtml(sessionState.is_admin ? "Admin access" : (sessionState.user.phone || sessionState.user.email || "Customer"))}</small>`
        : "<strong>Guest</strong><small>Browse the live catalog</small>";
    authAction.textContent = sessionState.authenticated ? "Logout" : "Login";
}

function routePath() {
    return window.location.pathname.replace(/\/+$/, "") || "/";
}

function routeQuery() {
    return new URLSearchParams(window.location.search);
}

function navigate(path) {
    window.history.pushState({}, "", path);
    renderRoute();
}

function attachGlobalHandlers() {
    document.addEventListener("click", (event) => {
        const anchor = event.target.closest("[data-link]");
        if (anchor && anchor.getAttribute("href")) {
            event.preventDefault();
            navigate(anchor.getAttribute("href"));
        }
    });
    window.addEventListener("popstate", renderRoute);
    document.getElementById("authAction").addEventListener("click", async () => {
        if (sessionState.authenticated) {
            await api("/api/auth/logout", { method: "POST" });
            setFlash("Signed out.");
            await refreshSession();
            navigate("/");
            return;
        }
        navigate("/login");
    });
    const themeToggle = document.querySelector("[data-theme-toggle]");
    themeToggle?.addEventListener("click", () => {
        const root = document.documentElement;
        const next = root.dataset.theme === "light" ? "dark" : "light";
        root.dataset.theme = next;
        localStorage.setItem("bookverse-theme", next);
    });
    const savedTheme = localStorage.getItem("bookverse-theme");
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;
}

function currentAuthRole() {
    const params = routeQuery();
    const requested = (params.get("role") || "customer").toLowerCase();
    return requested === "admin" ? "admin" : "customer";
}

function bookCard(book) {
    return `
        <article class="book-card glass-card tall">
            <img src="${book.cover}" alt="${escapeHtml(book.title)}">
            <div>
                <div class="tag-row">
                    <span class="tag">${escapeHtml(book.genre)}</span>
                    <span class="tag">${escapeHtml(book.language)}</span>
                    ${book.preview_ready ? '<span class="tag">Real text preview</span>' : ""}
                </div>
                <h3>${escapeHtml(book.title)}</h3>
                <p>${escapeHtml(book.author)}</p>
                <p class="muted-copy">${escapeHtml(book.summary)}</p>
                <div class="meta-line">
                    <span>${book.rating} / 5</span>
                    <span>${book.sold_count} sold</span>
                    <span class="stock-pill ${book.stock > 0 ? "in-stock" : "out-stock"}">${book.stock > 0 ? `${book.stock} available` : "Out of stock"}</span>
                </div>
                <div class="price-row">
                    <strong>${formatCurrency(book.price)}</strong>
                </div>
                <div class="action-row stacked-mobile">
                    <a class="ghost-btn" href="/book/${book.id}" data-link>Preview</a>
                    <a class="ghost-btn" href="/reader/${book.id}" data-link>Read 10 pages</a>
                    <button class="ghost-btn" type="button" data-wishlist="${book.id}">Wishlist</button>
                    <button class="primary-btn" type="button" data-cart="${book.id}" ${book.stock < 1 ? "disabled" : ""}>Add to cart</button>
                </div>
            </div>
        </article>
    `;
}

function compactBookRow(book) {
    return `
        <a class="book-inline glass-card" href="/book/${book.id}" data-link>
            <img src="${book.cover}" alt="${escapeHtml(book.title)}">
            <div>
                <strong>${escapeHtml(book.title)}</strong>
                <span>${escapeHtml(book.author)}</span>
                <p>${escapeHtml(book.summary)}</p>
            </div>
        </a>
    `;
}

function drawChart(canvasId, labels, values, color) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    canvas.width = 640;
    canvas.height = 280;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const max = Math.max(...values, 1);
    values.forEach((value, index) => {
        const x = 28 + index * 96;
        const h = (value / max) * 190;
        const y = 220 - h;
        ctx.fillStyle = color;
        ctx.fillRect(x, y, 66, h);
        ctx.fillStyle = "#9db0d3";
        ctx.fillText(String(labels[index] || "").slice(0, 10), x, 250, 80);
        ctx.fillText(String(value), x, y - 10);
    });
}

async function addToCart(bookId) {
    try {
        const data = await api(`/api/cart/add/${bookId}`, {
            method: "POST",
            headers: { "X-Requested-With": "XMLHttpRequest" }
        });
        setFlash(data.message || "Book added to cart.");
        await refreshSession();
    } catch (error) {
        if (error.payload?.login_required) {
            setFlash("Sign in to continue with cart and checkout.");
            navigate("/login");
            return;
        }
        setFlash(error.message, "error");
    }
}

async function addToWishlist(bookId) {
    try {
        const data = await api(`/api/wishlist/add/${bookId}`, { method: "POST" });
        setFlash(data.message || "Added to wishlist.");
        await refreshSession();
    } catch (error) {
        if (error.payload?.login_required) {
            setFlash("Sign in to use wishlist.");
            navigate("/login");
            return;
        }
        setFlash(error.message, "error");
    }
}

function bindBookActions(scope = document) {
    scope.querySelectorAll("[data-cart]").forEach((button) => {
        button.addEventListener("click", () => addToCart(button.dataset.cart));
    });
    scope.querySelectorAll("[data-wishlist]").forEach((button) => {
        button.addEventListener("click", () => addToWishlist(button.dataset.wishlist));
    });
}

function ensureAuthView(message) {
    appRoot.innerHTML = `
        <section class="auth-shell">
            <div class="glass-card form-card auth-card">
                <span class="eyebrow">Authentication needed</span>
                <h1>Sign in to continue.</h1>
                <p class="lede">${escapeHtml(message)}</p>
                <div class="action-row">
                    <a class="primary-btn" href="/login" data-link>Open login</a>
                    <a class="ghost-btn" href="/store" data-link>Back to store</a>
                </div>
            </div>
        </section>
    `;
}

function ensureAdminView(message) {
    appRoot.innerHTML = `
        <section class="auth-shell">
            <div class="glass-card form-card auth-card">
                <span class="eyebrow">Admin only</span>
                <h1>Use the admin account for this screen.</h1>
                <p class="lede">${escapeHtml(message)}</p>
                <div class="action-row">
                    <a class="primary-btn" href="/login?role=admin" data-link>Admin login</a>
                    <a class="ghost-btn" href="/store" data-link>Back to store</a>
                </div>
            </div>
        </section>
    `;
}

async function renderHome() {
    const data = await api("/api/home");
    appRoot.innerHTML = `
        <section class="hero">
            <div>
                <span class="eyebrow">Premium bookstore</span>
                <h1>Read, discover, and buy books through one polished storefront.</h1>
                <p class="lede">BOOKVERSE AI pairs a premium catalog with real-reader previews, smart suggestions, book clubs, and operational order tracking.</p>
                <div class="hero-metrics">
                    <span class="tag">${data.catalog_size} titles live</span>
                    <span class="tag">${data.trending.length} trending now</span>
                    <span class="tag">${data.best_sellers.length} bestseller picks</span>
                </div>
                <div class="hero-actions">
                    <a class="primary-btn" href="/store" data-link>Browse store</a>
                    <a class="ghost-btn" href="/community" data-link>See community</a>
                </div>
            </div>
            <div class="hero-stage">
                <div class="bookshelf glass-card">
                    ${data.featured.map((book, index) => `<div class="floating-book" style="--delay:${index}"><img src="${book.cover}" alt="${escapeHtml(book.title)}"></div>`).join("")}
                    <div class="glass-card hero-panel">
                        <span class="eyebrow">Live recommendation moods</span>
                        <h3>Tell us your mood. We'll build a reading stack.</h3>
                        <div class="mood-buttons">
                            <button class="ghost-btn" type="button" data-mood="happy">Happy reads</button>
                            <button class="ghost-btn" type="button" data-mood="thriller">Thrillers tonight</button>
                            <button class="ghost-btn" type="button" data-mood="exam">Exam prep mode</button>
                            <button class="ghost-btn" type="button" data-mood="weekend">Weekend reads</button>
                        </div>
                        <div id="moodResults" class="dynamic-results"></div>
                    </div>
                </div>
            </div>
        </section>

        <section class="section-block">
            <div class="section-head">
                <div>
                    <span class="eyebrow">Trending</span>
                    <h2>New arrivals, best sellers, and live catalog momentum</h2>
                </div>
            </div>
            <div class="slider-track">
                ${data.trending.map(bookCard).join("")}
            </div>
        </section>

        <section class="grid-two section-block">
            <div class="glass-card mood-column">
                <span class="eyebrow">AI Book Match Quiz</span>
                <h2>Reader compatibility with live shelf overlap.</h2>
                <div class="assistant-results">
                    ${data.matches.map((match) => `
                        <div class="compact-card">
                            <strong>${escapeHtml(match.reader.name)} x ${escapeHtml(match.partner.name)}</strong>
                            <p>${match.compatibility}% match around ${escapeHtml(match.bond)}</p>
                            <small>${escapeHtml(match.spark_title)}</small>
                        </div>
                    `).join("")}
                </div>
            </div>
            <div class="glass-card mood-column">
                <span class="eyebrow">Recommendation engine</span>
                <h2>Browse by mood cluster.</h2>
                ${Object.entries(data.recommendation_groups).map(([label, books]) => `
                    <section class="compact-card">
                        <strong>${escapeHtml(label)}</strong>
                        <div class="book-inline-list">
                            ${books.slice(0, 2).map(compactBookRow).join("")}
                        </div>
                    </section>
                `).join("")}
            </div>
        </section>
    `;
    bindBookActions(appRoot);
    appRoot.querySelectorAll("[data-mood]").forEach((button) => {
        button.addEventListener("click", async () => {
            const target = document.getElementById("moodResults");
            target.innerHTML = "<p>Matching your reading mood...</p>";
            const books = await api("/api/mood-match", {
                method: "POST",
                body: JSON.stringify({ mood: button.dataset.mood })
            });
            target.innerHTML = books.map((book) => `
                <div class="compact-card">
                    <strong>${escapeHtml(book.title)}</strong>
                    <p>${escapeHtml(book.author)}</p>
                    <small>${escapeHtml(book.reason)}</small>
                </div>
            `).join("");
        });
    });
}

async function renderStore(prefillPrompt = "") {
    const params = routeQuery();
    const data = await api(`/api/store?${params.toString()}`);
    appRoot.innerHTML = `
        <section class="page-hero compact">
            <span class="eyebrow">Book store</span>
            <h1>Browse a 500+ title inventory with live stock, real covers, and readable previews.</h1>
            <p class="lede">${data.counts.titles} titles ${data.counts.inventory} copies in inventory ${data.counts.out_of_stock} out of stock</p>
        </section>

        <section class="grid-two">
            <div class="glass-card form-card">
                <span class="eyebrow">AI store assistant</span>
                <h2>Ask for a subject, title, or topic and get purchasable options.</h2>
                <form id="assistantForm" class="assistant-form">
                    <input type="text" id="assistantPrompt" placeholder="Try: science, mystery, history, Shakespeare, reasoning" value="${escapeHtml(prefillPrompt)}">
                    <button class="primary-btn" type="submit">Find books</button>
                </form>
                <p id="assistantMessage" class="assistant-message">Ask for a topic and the assistant will return available options from the current store inventory.</p>
                <div id="assistantResults" class="assistant-results"></div>
            </div>
            <div class="glass-card filter-panel">
                <form id="filterForm" class="filter-form">
                    <input type="text" name="search" placeholder="Search titles, authors, genres" value="${escapeHtml(params.get("search") || "")}">
                    <select name="genre"><option value="">All genres</option>${data.facets.genres.map((genre) => `<option ${params.get("genre") === genre ? "selected" : ""}>${escapeHtml(genre)}</option>`).join("")}</select>
                    <select name="author"><option value="">All authors</option>${data.facets.authors.map((author) => `<option ${params.get("author") === author ? "selected" : ""}>${escapeHtml(author)}</option>`).join("")}</select>
                    <select name="language"><option value="">All languages</option>${data.facets.languages.map((language) => `<option ${params.get("language") === language ? "selected" : ""}>${escapeHtml(language)}</option>`).join("")}</select>
                    <select name="rating">
                        <option value="">Any rating</option>
                        ${["4", "4.5"].map((rating) => `<option value="${rating}" ${params.get("rating") === rating ? "selected" : ""}>${rating}+ stars</option>`).join("")}
                    </select>
                    <select name="price">
                        <option value="">Any price</option>
                        <option value="400" ${params.get("price") === "400" ? "selected" : ""}>Up to Rs. 400</option>
                        <option value="600" ${params.get("price") === "600" ? "selected" : ""}>Up to Rs. 600</option>
                        <option value="800" ${params.get("price") === "800" ? "selected" : ""}>Up to Rs. 800</option>
                    </select>
                    <select name="availability">
                        <option value="">All stock states</option>
                        <option value="in" ${params.get("availability") === "in" ? "selected" : ""}>In stock</option>
                        <option value="out" ${params.get("availability") === "out" ? "selected" : ""}>Out of stock</option>
                    </select>
                    <button class="primary-btn" type="submit">Apply filters</button>
                </form>
            </div>
        </section>

        <section class="catalog-grid section-block">
            ${data.books.map(bookCard).join("")}
        </section>
    `;
    bindBookActions(appRoot);
    document.getElementById("filterForm").addEventListener("submit", (event) => {
        event.preventDefault();
        const formData = new FormData(event.currentTarget);
        const next = new URLSearchParams();
        for (const [key, value] of formData.entries()) {
            if (String(value).trim()) next.set(key, value);
        }
        navigate(`/store?${next.toString()}`);
    });
    document.getElementById("assistantForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const prompt = document.getElementById("assistantPrompt").value.trim();
        const messageNode = document.getElementById("assistantMessage");
        const resultsNode = document.getElementById("assistantResults");
        if (!prompt) return;
        messageNode.textContent = "Checking the current store inventory...";
        const data = await api("/api/store-assistant", { method: "POST", body: JSON.stringify({ prompt }) });
        messageNode.textContent = data.message;
        resultsNode.innerHTML = data.books.map((book) => `
            <article class="assistant-card glass-card">
                <img src="${book.cover}" alt="${escapeHtml(book.title)}">
                <div>
                    <strong>${escapeHtml(book.title)}</strong>
                    <p>${escapeHtml(book.author)} | ${escapeHtml(book.genre)}</p>
                    <p>${escapeHtml(book.summary)}</p>
                    <div class="meta-line">
                        <span>${book.rating} / 5</span>
                        <span>${book.stock} available</span>
                        <span>${formatCurrency(book.price)}</span>
                    </div>
                    <div class="action-row">
                        <a class="ghost-btn" href="/book/${book.id}" data-link>Preview</a>
                        <button class="primary-btn" type="button" data-cart="${book.id}">Add to cart</button>
                    </div>
                </div>
            </article>
        `).join("");
        bindBookActions(resultsNode);
    });
}

async function renderBook(bookId) {
    const data = await api(`/api/books/${bookId}`);
    const { book, reviews, related, author_books } = data;
    appRoot.innerHTML = `
        <section class="detail-layout">
            <aside class="glass-card detail-cover">
                <img src="${book.cover}" alt="${escapeHtml(book.title)}">
                <div class="action-row stacked-mobile section-block">
                    <button class="primary-btn" type="button" data-cart="${book.id}" ${book.stock < 1 ? "disabled" : ""}>Add to cart</button>
                    <a class="ghost-btn" href="/reader/${book.id}" data-link>Open 10-page reader</a>
                    <button class="ghost-btn" type="button" data-wishlist="${book.id}">Wishlist</button>
                </div>
            </aside>
            <section class="detail-copy">
                <span class="eyebrow">${escapeHtml(book.genre)} | ${escapeHtml(book.language)}</span>
                <h1>${escapeHtml(book.title)}</h1>
                <p>By ${escapeHtml(book.author)} | ${book.rating} / 5 | ${formatCurrency(book.price)}</p>
                <div class="meta-line">
                    <span class="stock-pill ${book.stock > 0 ? "in-stock" : "out-stock"}">${book.stock > 0 ? `${book.stock} copies available` : "Out of stock"}</span>
                    <span>${book.sold_count} sold</span>
                    <span>${book.preview_ready ? "Real public-domain preview" : "Metadata preview"}</span>
                </div>
                <p>${escapeHtml(book.description)}</p>
                <div class="glass-card info-card">
                    <h3>Book summary</h3>
                    <p>${escapeHtml(book.summary)}</p>
                </div>
                <div class="grid-two">
                    <div class="glass-card info-card">
                        <h3>Related books</h3>
                        <div class="book-inline-list">${related.map(compactBookRow).join("")}</div>
                    </div>
                    <div class="glass-card info-card">
                        <h3>More from this author</h3>
                        <div class="book-inline-list">${author_books.map(compactBookRow).join("")}</div>
                    </div>
                </div>
                <div class="glass-card info-card">
                    <h3>Reader reviews</h3>
                    ${reviews.map((review) => `<div class="review-row"><strong>${escapeHtml(review.reviewer)}</strong><span>${review.rating} / 5</span><p>${escapeHtml(review.comment)}</p></div>`).join("")}
                </div>
            </section>
        </section>
    `;
    bindBookActions(appRoot);
}

function initReaderInteractions(bookId) {
    const readerShell = document.querySelector("[data-reader]");
    if (!readerShell) return;
    const pages = Array.from(readerShell.querySelectorAll(".reader-page"));
    const progressBar = readerShell.querySelector("[data-progress-bar]");
    const progressText = readerShell.querySelector("[data-progress-text]");
    const noteBox = document.getElementById("readerNote");
    let current = Number(localStorage.getItem(`reader-${bookId}-page`) || 1);
    let animating = false;
    function render() {
        pages.forEach((page, index) => {
            const isCurrent = index + 1 === current;
            page.classList.toggle("current", isCurrent);
            page.classList.toggle("active", isCurrent);
            page.classList.toggle("before", index + 1 < current);
            page.classList.toggle("after", index + 1 > current);
        });
        const pct = (current / pages.length) * 100;
        if (progressBar) progressBar.style.width = `${pct}%`;
        if (progressText) progressText.textContent = `Page ${current} / ${pages.length}`;
        localStorage.setItem(`reader-${bookId}-page`, current);
    }
    function go(next) {
        if (animating || next < 1 || next > pages.length || next === current) return;
        animating = true;
        current = next;
        render();
        setTimeout(() => { animating = false; }, 420);
    }
    readerShell.querySelector("[data-prev-page]")?.addEventListener("click", () => go(current - 1));
    readerShell.querySelector("[data-next-page]")?.addEventListener("click", () => go(current + 1));
    readerShell.querySelector(".flipbook")?.addEventListener("wheel", (event) => {
        event.preventDefault();
        go(event.deltaY > 0 ? current + 1 : current - 1);
    }, { passive: false });
    document.addEventListener("keydown", (event) => {
        if (routePath() !== `/reader/${bookId}`) return;
        if (event.key === "ArrowRight") go(current + 1);
        if (event.key === "ArrowLeft") go(current - 1);
    });
    readerShell.querySelectorAll("[data-reader-mode]").forEach((button) => {
        button.addEventListener("click", () => {
            const night = button.dataset.readerMode === "night";
            pages.forEach((page) => page.classList.toggle("night-page", night));
        });
    });
    readerShell.querySelector("[data-bookmark]")?.addEventListener("click", (event) => {
        localStorage.setItem(`reader-${bookId}-bookmark`, current);
        event.currentTarget.textContent = `Bookmarked page ${current}`;
    });
    readerShell.querySelector("[data-highlight]")?.addEventListener("click", () => {
        pages[current - 1].style.boxShadow = "0 0 0 3px rgba(255, 183, 3, 0.65), 0 18px 60px rgba(0,0,0,.26)";
    });
    readerShell.querySelector("[data-reader-speak]")?.addEventListener("click", () => {
        const speech = new SpeechSynthesisUtterance(pages[current - 1]?.innerText || "");
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(speech);
    });
    readerShell.querySelector("[data-font-size]")?.addEventListener("input", (event) => {
        pages.forEach((page) => {
            const block = page.querySelector(".reader-text");
            if (block) block.style.fontSize = `${event.currentTarget.value}px`;
        });
    });
    readerShell.querySelector("[data-companion]")?.addEventListener("click", async () => {
        const prompt = document.getElementById("companionPrompt").value;
        const data = await api("/api/companion", { method: "POST", body: JSON.stringify({ prompt, book_id: bookId }) });
        document.getElementById("companionResponse").textContent = data.answer;
    });
    const savedNote = localStorage.getItem(`reader-${bookId}-note`);
    if (savedNote && noteBox) noteBox.value = savedNote;
    noteBox?.addEventListener("input", () => localStorage.setItem(`reader-${bookId}-note`, noteBox.value));
    render();
}

async function renderReader(bookId) {
    const data = await api(`/api/books/${bookId}/reader`);
    const { book, pages } = data;
    appRoot.innerHTML = `
        <section class="reader-shell" data-reader data-book-id="${book.id}">
            <aside class="glass-card reader-tools">
                <span class="eyebrow">${escapeHtml(book.genre)} | Real text source</span>
                <h2>${escapeHtml(book.title)}</h2>
                <p>${escapeHtml(book.author)}</p>
                <div class="tool-group">
                    <button class="ghost-btn" type="button" data-reader-mode="day">Day</button>
                    <button class="ghost-btn" type="button" data-reader-mode="night">Night</button>
                    <button class="ghost-btn" type="button" data-reader-speak>Read aloud</button>
                </div>
                <label>Font size<input type="range" min="16" max="24" value="18" data-font-size></label>
                <div class="tool-group">
                    <button class="ghost-btn" type="button" data-bookmark>Bookmark page</button>
                    <button class="ghost-btn" type="button" data-highlight>Highlight quote</button>
                </div>
                <textarea id="readerNote" placeholder="Write notes while reading..."></textarea>
                <div class="companion-box glass-card">
                    <h3>AI Reading Companion</h3>
                    <textarea id="companionPrompt" placeholder="Ask about the book, summary, theme, or characters."></textarea>
                    <button class="primary-btn" type="button" data-companion>Ask companion</button>
                    <p id="companionResponse" class="muted-copy"></p>
                </div>
            </aside>
            <section class="reader-stage">
                <div class="section-head">
                    <div class="progress-bar"><i data-progress-bar></i></div>
                    <strong data-progress-text>Page 1 / ${pages.length}</strong>
                </div>
                <div class="flipbook glass-card">
                    ${pages.map((page, index) => `
                        <article class="reader-page ${index === 0 ? "current active" : "after"}">
                            <span class="page-number">${String(index + 1).padStart(2, "0")}</span>
                            <div class="reader-text">
                                ${String(page).split("\n\n").map((paragraph) => `<p>${escapeHtml(paragraph)}</p>`).join("")}
                            </div>
                        </article>
                    `).join("")}
                </div>
                <div class="action-row">
                    <button class="ghost-btn" type="button" data-prev-page>Previous page</button>
                    <button class="primary-btn" type="button" data-next-page>Next page</button>
                </div>
            </section>
        </section>
    `;
    initReaderInteractions(book.id);
}

async function renderGenres() {
    const data = await api("/api/genres");
    appRoot.innerHTML = `
        <section class="page-hero compact">
            <span class="eyebrow">Genres</span>
            <h1>Genre collections with title counts, ratings, and starting prices.</h1>
        </section>
        <section class="card-grid three-up">
            ${data.genres.map((row) => `
                <a class="glass-card genre-card large" href="/store?genre=${encodeURIComponent(row.genre)}" data-link>
                    <h3>${escapeHtml(row.genre)}</h3>
                    <p>${row.total} titles · ${row.avg_rating} average rating</p>
                    <p>Starting at ${formatCurrency(row.min_price)}</p>
                </a>
            `).join("")}
        </section>
    `;
}

async function renderAuthors() {
    const data = await api("/api/authors");
    appRoot.innerHTML = `
        <section class="page-hero compact"><span class="eyebrow">Authors</span><h1>Featured authors powering the catalog.</h1></section>
        <section class="author-grid">
            ${data.authors.map((author) => `
                <article class="glass-card author-card large">
                    <img src="${author.avatar}" alt="${escapeHtml(author.author)}">
                    <h3>${escapeHtml(author.author)}</h3>
                    <p>${author.total} books · ${author.rating} ★</p>
                    <p>${author.stock} copies currently in inventory.</p>
                </article>
            `).join("")}
        </section>
    `;
}

async function renderCommunity() {
    const data = await api("/api/community");
    appRoot.innerHTML = `
        <section class="page-hero compact">
            <span class="eyebrow">Community</span>
            <h1>Reading streaks, live rooms, and social proof around the catalog.</h1>
        </section>
        <section class="grid-two">
            <div class="glass-card info-card">
                <span class="eyebrow">Challenges</span>
                ${data.challenges.map((row) => `
                    <div class="challenge-row">
                        <strong>${escapeHtml(row.name)}</strong>
                        <span>${row.participants} participants</span>
                    </div>
                `).join("")}
            </div>
            <div class="glass-card info-card">
                <span class="eyebrow">Discussion rooms</span>
                ${data.discussions.map((row) => `
                    <div class="discussion-row">
                        <strong>${escapeHtml(row.topic)}</strong>
                        <span>${escapeHtml(row.club)} · ${row.replies} replies</span>
                    </div>
                `).join("")}
            </div>
        </section>
        <section class="section-block">
            <span class="eyebrow">Leaderboard</span>
            <h2>Top readers this month</h2>
            <div class="card-grid four-up">
                ${data.top_readers.map((reader) => `
                    <article class="glass-card leaderboard-card">
                        <h3>${escapeHtml(reader.name)}</h3>
                        <p>@${escapeHtml(reader.handle)}</p>
                        <p>${reader.streak} day streak ${escapeHtml(reader.badge)}</p>
                    </article>
                `).join("")}
            </div>
        </section>
    `;
}

async function renderClubs() {
    const data = await api("/api/clubs");
    appRoot.innerHTML = `
        <section class="page-hero compact"><span class="eyebrow">Book clubs</span><h1>Live rooms for readers who want accountability, taste, and conversation.</h1></section>
        <section class="card-grid three-up">
            ${data.clubs.map((club) => `
                <article class="glass-card info-card">
                    <h3>${escapeHtml(club.name)}</h3>
                    <p>${escapeHtml(club.description)}</p>
                    <div class="action-row">
                        <span>${escapeHtml(club.meeting_time)}</span>
                        <button class="primary-btn" type="button">Join room</button>
                    </div>
                </article>
            `).join("")}
        </section>
    `;
}

async function renderWishlist() {
    try {
        const data = await api("/api/wishlist");
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">Wishlist</span><h1>Saved books ready to move into checkout.</h1></section>
            <section class="catalog-grid">${data.entries.map((entry) => bookCard(entry.book)).join("")}</section>
        `;
        bindBookActions(appRoot);
    } catch (error) {
        ensureAuthView(error.message);
    }
}

async function renderCart() {
    try {
        const data = await api("/api/cart");
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">Cart</span><h1>Review your books, then move into shipping and payment.</h1></section>
            <section class="grid-two">
                <div class="glass-card info-card">
                    <span class="eyebrow">Cart items</span>
                    ${data.items.map((item) => `
                        <div class="cart-row">
                            <img src="${item.book.cover}" alt="${escapeHtml(item.book.title)}">
                            <div>
                                <strong>${escapeHtml(item.book.title)}</strong>
                                <p>${item.qty} x ${formatCurrency(item.book.price)}</p>
                                <small>${item.book.stock} left in stock</small>
                            </div>
                            <div>
                                <strong>${formatCurrency(item.subtotal)}</strong>
                                <button class="ghost-btn" type="button" data-remove-cart="${item.book.id}">Remove</button>
                            </div>
                        </div>
                    `).join("")}
                    <div class="summary-row section-block"><strong>Total</strong><strong>${formatCurrency(data.total)}</strong></div>
                    <div class="action-row"><a class="primary-btn" href="/checkout" data-link>Continue to shipping and payment</a></div>
                </div>
                <div class="glass-card info-card">
                    <span class="eyebrow">Blind date with a book</span>
                    ${data.blind_date ? `<img class="mystery-cover" src="${data.blind_date.cover}" alt="${escapeHtml(data.blind_date.title)}"><h3>${escapeHtml(data.blind_date.title)}</h3><p>${escapeHtml(data.blind_date.summary)}</p>` : "<p>No surprise pick available right now.</p>"}
                </div>
            </section>
        `;
        appRoot.querySelectorAll("[data-remove-cart]").forEach((button) => {
            button.addEventListener("click", async () => {
                await api(`/api/cart/remove/${button.dataset.removeCart}`, { method: "POST" });
                setFlash("Removed from cart.");
                await refreshSession();
                renderCart();
            });
        });
    } catch (error) {
        ensureAuthView(error.message);
    }
}

async function renderCheckout() {
    try {
        const data = await api("/api/cart");
        if (!data.items.length) {
            navigate("/cart");
            return;
        }
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">Checkout</span><h1>Shipping, contact details, and demo payment flow.</h1></section>
            <section class="grid-two">
                <form class="glass-card form-card" id="checkoutForm">
                    <label>Name<input name="name" value="${escapeHtml(sessionState.user.name || "")}" required></label>
                    <label>Email<input name="email" value="${escapeHtml(sessionState.user.email || "")}"></label>
                    <label>Phone<input name="phone" value="${escapeHtml(sessionState.user.phone || "")}" required></label>
                    <label>Address<textarea name="address" required></textarea></label>
                    <div class="grid-two">
                        <label>City<input name="city" required></label>
                        <label>State<input name="state" required></label>
                    </div>
                    <div class="grid-two">
                        <label>Pincode<input name="pincode" required></label>
                        <label>Coupon<input name="coupon" placeholder="BOOKVERSE150"></label>
                    </div>
                    <button class="primary-btn" type="submit">Pay successfully</button>
                </form>
                <div class="glass-card info-card">
                    <span class="eyebrow">Billing</span>
                    ${data.items.map((item) => `<div class="summary-row"><span>${escapeHtml(item.book.title)} x ${item.qty}</span><strong>${formatCurrency(item.subtotal)}</strong></div>`).join("")}
                    <div class="summary-row checkout-total"><strong>Total</strong><strong>${formatCurrency(data.total)}</strong></div>
                </div>
            </section>
        `;
        document.getElementById("checkoutForm").addEventListener("submit", async (event) => {
            event.preventDefault();
            const formData = new FormData(event.currentTarget);
            const payload = Object.fromEntries(formData.entries());
            try {
                const result = await api("/api/checkout", { method: "POST", body: JSON.stringify(payload) });
                setFlash(`${result.message} ${result.order.order_number}`);
                await refreshSession();
                navigate(`/track?order=${encodeURIComponent(result.order.order_number)}`);
            } catch (error) {
                setFlash(error.message, "error");
            }
        });
    } catch (error) {
        ensureAuthView(error.message);
    }
}

async function renderOrders() {
    try {
        const data = await api("/api/orders/mine");
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">My orders</span><h1>Track your recent purchases and shipment progress.</h1></section>
            <section class="order-card-list">
                ${data.orders.map((order) => `
                    <article class="glass-card order-card">
                        <div class="order-card-head">
                            <div>
                                <strong>${escapeHtml(order.order_number)}</strong>
                                <p>${escapeHtml(order.customer_name)} | ${escapeHtml(order.city)}, ${escapeHtml(order.state)}</p>
                                <small>Status: ${escapeHtml(order.status)} | Payment: ${escapeHtml(order.payment_status)}</small>
                            </div>
                            <div class="order-actions">
                                <a class="ghost-btn" href="/track?order=${encodeURIComponent(order.order_number)}" data-link>Track</a>
                            </div>
                        </div>
                        <div class="order-items-grid">
                            ${order.items.map((item) => `
                                <div class="order-line">
                                    <img src="${item.cover}" alt="${escapeHtml(item.title)}">
                                    <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.author)}</p><small>${item.qty} x ${formatCurrency(item.price)}</small></div>
                                    <strong>${formatCurrency(item.line_total)}</strong>
                                </div>
                            `).join("")}
                        </div>
                    </article>
                `).join("")}
            </section>
        `;
    } catch (error) {
        ensureAuthView(error.message);
    }
}

async function renderTrack() {
    const orderNumber = routeQuery().get("order") || sessionStorage.getItem("track-order") || "";
    if (!orderNumber) {
        appRoot.innerHTML = `
            <section class="auth-shell">
                <form class="glass-card form-card auth-card" id="trackForm">
                    <span class="eyebrow">Track order</span>
                    <h1>Enter your order number.</h1>
                    <label>Order number<input name="order" placeholder="BV-20260510-03162B"></label>
                    <button class="primary-btn" type="submit">Track now</button>
                </form>
            </section>
        `;
        document.getElementById("trackForm").addEventListener("submit", (event) => {
            event.preventDefault();
            const nextOrder = new FormData(event.currentTarget).get("order");
            sessionStorage.setItem("track-order", nextOrder);
            navigate(`/track?order=${encodeURIComponent(nextOrder)}`);
        });
        return;
    }
    try {
        const data = await api(`/api/orders/track/${encodeURIComponent(orderNumber)}`);
        const order = data.order;
        appRoot.innerHTML = `
            <section class="page-hero compact">
                <span class="eyebrow">Track order</span>
                <h1>${escapeHtml(order.order_number)} | ${escapeHtml(order.tracking_number)}</h1>
                <p>${escapeHtml(order.customer_name)} | ${escapeHtml(order.city)}, ${escapeHtml(order.state)} - ${escapeHtml(order.pincode)}</p>
            </section>
            <section class="grid-two">
                <div class="glass-card info-card">
                    <span class="eyebrow">Shipment status</span>
                    <div class="timeline">
                        ${order.steps.map((step) => `
                            <div class="timeline-step ${step.done ? "done" : ""}">
                                <div class="timeline-dot"></div>
                                <div><strong>${escapeHtml(step.label)}</strong><p>${step.done ? "Completed" : "Pending"}</p></div>
                            </div>
                        `).join("")}
                    </div>
                </div>
                <div class="glass-card info-card">
                    <span class="eyebrow">Billing</span>
                    <div class="summary-row"><span>Payment</span><strong>${escapeHtml(order.payment_status)}</strong></div>
                    <div class="summary-row"><span>Total</span><strong>${formatCurrency(order.total)}</strong></div>
                    <div class="summary-row"><span>Expected delivery</span><strong>${escapeHtml(order.expected_delivery)}</strong></div>
                </div>
            </section>
        `;
    } catch (error) {
        setFlash(error.message, "error");
        navigate("/my-orders");
    }
}

function authMarkup(active) {
    const role = currentAuthRole();
    return `
        <section class="auth-shell">
            <div class="glass-card form-card auth-card">
                <span class="eyebrow">${role === "admin" ? "Admin access" : "Welcome back"}</span>
                <h1>${role === "admin" ? "Sign in to admin operations" : (active === "register" ? "Create your account" : "Sign in to your reading dashboard")}</h1>
                <div class="auth-switch">
                    <a href="/login?role=customer" data-link class="ghost-btn ${active === "login" && role === "customer" ? "active-tab" : ""}">Customer Login</a>
                    <a href="/login?role=admin" data-link class="ghost-btn ${active === "login" && role === "admin" ? "active-tab" : ""}">Admin Login</a>
                    <a href="/register?role=customer" data-link class="ghost-btn ${active === "register" ? "active-tab" : ""}">Sign Up</a>
                </div>
                <form id="authForm" class="form-card">
                    ${active === "register" ? `
                        <label>Name<input name="name" placeholder="Aanya"></label>
                        <label>Email<input name="email" placeholder="reader@example.com"></label>
                        <label>Phone<input name="phone" placeholder="9876543210"></label>
                    ` : `
                        <label>${role === "admin" ? "Admin Email" : "Email or Phone"}<input name="identifier" placeholder="${role === "admin" ? "admin@bookverse.ai" : "reader@example.com or 9876543210"}"></label>
                    `}
                    <label>Password<input type="password" name="password" placeholder="password"></label>
                    <button class="primary-btn" type="submit">${role === "admin" ? "Open admin dashboard" : (active === "register" ? "Create account" : "Sign in")}</button>
                    <small class="muted-copy">Admin login: admin@bookverse.ai / admin123</small>
                    <div class="action-row">
                        ${role === "admin"
                            ? '<button class="ghost-btn" type="button" id="fillAdminDemo">Use admin demo</button>'
                            : (active === "register"
                                ? '<button class="ghost-btn" type="button" id="fillCustomerDemo">Use customer demo</button>'
                                : '<button class="ghost-btn" type="button" id="fillCustomerDemo">Use customer demo</button>')}
                    </div>
                </form>
            </div>
        </section>
    `;
}

async function renderAuth(mode) {
    appRoot.innerHTML = authMarkup(mode);
    const role = currentAuthRole();
    const fillCustomer = document.getElementById("fillCustomerDemo");
    const fillAdmin = document.getElementById("fillAdminDemo");
    fillCustomer?.addEventListener("click", () => {
        const form = document.getElementById("authForm");
        if (mode === "register") {
            form.querySelector("[name='name']").value = "Demo Customer";
            form.querySelector("[name='email']").value = "customer@bookverse.ai";
            form.querySelector("[name='phone']").value = "9876543210";
        } else {
            form.querySelector("[name='identifier']").value = "9876543210";
        }
        const password = form.querySelector("[name='password']");
        if (password) password.value = "demo123";
    });
    fillAdmin?.addEventListener("click", () => {
        const form = document.getElementById("authForm");
        form.querySelector("[name='identifier']").value = "admin@bookverse.ai";
        const password = form.querySelector("[name='password']");
        if (password) password.value = "admin123";
    });
    document.getElementById("authForm").addEventListener("submit", async (event) => {
        event.preventDefault();
        const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
        payload.role = role;
        try {
            const result = await api(`/api/auth/${mode === "register" ? "register" : "login"}`, { method: "POST", body: JSON.stringify(payload) });
            setFlash(result.message);
            await refreshSession();
            navigate(sessionState.is_admin ? "/admin/dashboard" : "/store");
        } catch (error) {
            setFlash(error.message, "error");
        }
    });
}

async function renderAdminDashboard() {
    try {
        const data = await api("/api/admin/dashboard");
        appRoot.innerHTML = `
            <section class="dashboard-hero">
                <div class="dashboard-hero-copy">
                    <span class="eyebrow">Admin dashboard</span>
                    <h1>Store performance at a glance.</h1>
                    <p class="dashboard-subcopy">Revenue, orders, visitor flow, inventory risk, and shipment activity in one clean view.</p>
                </div>
                <div class="glass-card dashboard-highlight">
                    <span class="eyebrow">Today snapshot</span>
                    <div class="dashboard-highlight-grid">
                        <div><strong>${data.stats.today_orders}</strong><span>Orders</span></div>
                        <div><strong>${formatCurrency(data.stats.today_revenue)}</strong><span>Revenue</span></div>
                        <div><strong>${data.stats.today_visitors}</strong><span>Visitors</span></div>
                    </div>
                </div>
            </section>
            <section class="stat-grid dashboard-grid section-block">
                ${[
                    ["Total revenue", formatCurrency(data.stats.revenue), "All completed demo sales"],
                    ["Today revenue", formatCurrency(data.stats.today_revenue), "Revenue booked today"],
                    ["Total orders", data.stats.total_orders, "Orders created so far"],
                    ["Today orders", data.stats.today_orders, "New orders today"],
                    ["Books sold", data.stats.books_sold, "Units sold across catalog"],
                    ["Sold today", data.stats.today_books_sold, "Units sold today"],
                    ["Visitors", data.stats.total_visitors, "Total storefront traffic"],
                    ["Visitors today", data.stats.today_visitors, "Fresh daily traffic"],
                    ["Page views", data.stats.page_views, "Across all visited screens"],
                    ["Inventory units", data.stats.inventory_units, "Total copies in stock"],
                    ["Out of stock", data.stats.out_of_stock, "Titles needing replenishment"]
                ].map(([label, value, note]) => `
                    <article class="glass-card metric ${label === "Out of stock" ? "metric-alert" : ""}">
                        <span class="metric-label">${label}</span>
                        <strong>${value}</strong>
                        <small>${note}</small>
                    </article>
                `).join("")}
            </section>
            <section class="grid-two section-block">
                <div class="glass-card info-card">
                    <span class="eyebrow">Inventory controls</span>
                    <h3>Manage titles and stock</h3>
                    <p>Add new books, delete existing uploads, and review live inventory units from one screen.</p>
                    <div class="action-row">
                        <a class="primary-btn" href="/admin/inventory" data-link>Open inventory</a>
                        <a class="ghost-btn" href="/admin/orders" data-link>View orders</a>
                    </div>
                </div>
                <div class="glass-card info-card">
                    <span class="eyebrow">Order controls</span>
                    <h3>Print and track customer orders</h3>
                    <p>Open the orders screen to print invoices, inspect shipping addresses, and review sold stock.</p>
                    <div class="action-row">
                        <a class="primary-btn" href="/admin/orders" data-link>Open orders</a>
                    </div>
                </div>
            </section>
            <section class="grid-two section-block">
                <div class="glass-card chart-panel">
                    <h3>Popular books</h3>
                    <canvas id="salesChart"></canvas>
                </div>
                <div class="glass-card chart-panel">
                    <h3>Visitor activity</h3>
                    <canvas id="visitorChart"></canvas>
                </div>
            </section>
            <section class="grid-two section-block">
                <div class="glass-card info-card">
                    <h3>Low stock alerts</h3>
                    ${data.low_stock.map((book) => `<div class="summary-row"><span>${escapeHtml(book.title)}</span><strong>${book.stock} left</strong></div>`).join("") || "<p>No low stock titles right now.</p>"}
                </div>
                <div class="glass-card info-card">
                    <h3>Recent orders</h3>
                    ${data.recent_orders.map((order) => `<div class="summary-row"><span>${escapeHtml(order.order_number)}</span><strong>${formatCurrency(order.total)}</strong></div>`).join("")}
                </div>
            </section>
        `;
        drawChart("salesChart", data.sales_chart.labels, data.sales_chart.values, "#ffb703");
        drawChart("visitorChart", data.visitor_chart.labels, data.visitor_chart.values, "#4cc9f0");
    } catch (error) {
        ensureAdminView(error.message);
    }
}

async function renderAdminInventory() {
    try {
        const data = await api("/api/admin/inventory");
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">Inventory</span><h1>${data.total_titles} titles and ${data.inventory_units} inventory units are now live in the catalog.</h1></section>
            <section class="grid-two">
                <form class="glass-card form-card" id="inventoryForm">
                    <label>Title<input name="title" required></label>
                    <label>Author<input name="author" required></label>
                    <div class="grid-two">
                        <label>Genre<input name="genre" value="Fiction"></label>
                        <label>Language<input name="language" value="English"></label>
                    </div>
                    <div class="grid-two">
                        <label>Price<input name="price" type="number" value="499"></label>
                        <label>Stock<input name="stock" type="number" value="12"></label>
                    </div>
                    <label>Summary<textarea name="summary"></textarea></label>
                    <label>Description<textarea name="description"></textarea></label>
                    <button class="primary-btn" type="submit">Add book</button>
                </form>
                <div class="glass-card table-card">
                    <h3>Latest inventory slice</h3>
                    <table>
                        <thead><tr><th>Title</th><th>Genre</th><th>Stock</th><th>Price</th><th>Sold</th><th>Action</th></tr></thead>
                        <tbody>
                            ${data.books.slice(0, 20).map((book) => `
                                <tr>
                                    <td>${escapeHtml(book.title)}</td>
                                    <td>${escapeHtml(book.genre)}</td>
                                    <td>${book.stock}</td>
                                    <td>${formatCurrency(book.price)}</td>
                                    <td>${book.sold_count}</td>
                                    <td><button class="ghost-btn" type="button" data-delete-book="${book.id}">Delete</button></td>
                                </tr>
                            `).join("")}
                        </tbody>
                    </table>
                </div>
            </section>
        `;
        document.getElementById("inventoryForm").addEventListener("submit", async (event) => {
            event.preventDefault();
            const payload = Object.fromEntries(new FormData(event.currentTarget).entries());
            await api("/api/admin/inventory", { method: "POST", body: JSON.stringify(payload) });
            setFlash("Inventory updated.");
            renderAdminInventory();
        });
        appRoot.querySelectorAll("[data-delete-book]").forEach((button) => {
            button.addEventListener("click", async () => {
                await api(`/api/admin/inventory/delete/${button.dataset.deleteBook}`, { method: "POST" });
                setFlash("Book removed.");
                renderAdminInventory();
            });
        });
    } catch (error) {
        ensureAdminView(error.message);
    }
}

async function renderAdminOrders() {
    try {
        const data = await api("/api/admin/orders");
        appRoot.innerHTML = `
            <section class="page-hero compact"><span class="eyebrow">Orders</span><h1>Customer purchases, shipment addresses, print-ready invoices, and order analytics.</h1></section>
            <section class="order-card-list">
                ${data.orders.map((order) => `
                    <article class="glass-card order-card">
                        <div class="order-card-head">
                            <div>
                                <strong>${escapeHtml(order.order_number)}</strong>
                                <p>${escapeHtml(order.customer_name)} | ${escapeHtml(order.phone)} | ${escapeHtml(order.email)}</p>
                            </div>
                            <div class="order-actions">
                                <a class="ghost-btn print-btn" href="${order.print_url}" target="_blank" rel="noreferrer">Print order</a>
                                <strong>${formatCurrency(order.total)}</strong>
                            </div>
                        </div>
                        <div class="order-address">
                            <strong>Shipment address</strong>
                            <span>${escapeHtml(order.address)}, ${escapeHtml(order.city)}, ${escapeHtml(order.state)} - ${escapeHtml(order.pincode)}</span>
                            <small>Status: ${escapeHtml(order.status)} | Payment: ${escapeHtml(order.payment_status)} | Tracking: ${escapeHtml(order.tracking_number)}</small>
                        </div>
                        <div class="order-items-grid">
                            ${order.items.map((item) => `
                                <div class="order-line">
                                    <img src="${item.cover}" alt="${escapeHtml(item.title)}">
                                    <div><strong>${escapeHtml(item.title)}</strong><p>${escapeHtml(item.author)}</p><small>${item.qty} x ${formatCurrency(item.price)}</small></div>
                                    <strong>${formatCurrency(item.line_total)}</strong>
                                </div>
                            `).join("")}
                        </div>
                    </article>
                `).join("")}
            </section>
        `;
    } catch (error) {
        ensureAdminView(error.message);
    }
}

function renderStaticPage(title, body) {
    appRoot.innerHTML = `
        <section class="page-hero compact">
            <span class="eyebrow">${escapeHtml(title)}</span>
            <h1>${escapeHtml(title)}</h1>
            <p class="lede">${body}</p>
        </section>
    `;
}

async function renderRoute() {
    const path = routePath();
    document.getElementById("flashStack").innerHTML = "";
    await refreshSession();
    if (path === "/") return renderHome();
    if (path === "/store" || path === "/ai-suggestions") return renderStore(path === "/ai-suggestions" ? "science" : "");
    if (path.startsWith("/book/")) return renderBook(path.split("/").pop());
    if (path.startsWith("/reader/")) return renderReader(path.split("/").pop());
    if (path === "/genres") return renderGenres();
    if (path === "/authors") return renderAuthors();
    if (path === "/community") return renderCommunity();
    if (path === "/clubs") return renderClubs();
    if (path === "/wishlist") return renderWishlist();
    if (path === "/cart") return renderCart();
    if (path === "/checkout") return renderCheckout();
    if (path === "/my-orders") return renderOrders();
    if (path === "/track") return renderTrack();
    if (path === "/login") return renderAuth("login");
    if (path === "/register") return renderAuth("register");
    if (path === "/admin/dashboard") return renderAdminDashboard();
    if (path === "/admin/inventory") return renderAdminInventory();
    if (path === "/admin/orders") return renderAdminOrders();
    if (path === "/contact") return renderStaticPage("Contact", "Reach the BOOKVERSE AI team for product walkthroughs, bookstore onboarding, and demo support.");
    if (path === "/about") return renderStaticPage("About", "BOOKVERSE AI combines an online bookstore, reading preview engine, AI discovery tools, and admin operations in one premium full-stack experience.");
    return renderStaticPage("Page not found", "The requested screen is not available in the static frontend route map yet.");
}

attachGlobalHandlers();
renderRoute();
