/*
    FlowPy - Ana Script Dosyası
    ===========================
    Bu dosya üç ana işi yapar:
    
    1. Arka Plan Ağı: Canvas üzerinde turuncu örümcek ağı animasyonu
    2. Arama: Üst çubuktaki arama kutusu ile bölüm bulma
    3. Navigasyon: Bölümler arası geçiş ve aktif bölüm takibi
    4. Derleyici: CodeMirror ile Python IDE, Pyodide ile çalıştırma
    5. Workspace: Dosya/Klasör yönetimi, ZIP import/export
    6. FlowingTR: Akış diyagramı oluşturma ve senkronizasyon
    
    AYARLAR:
    --------
    Aşağıdaki SETTINGS objesi tüm değerleri tek yerde toplar.
    Değiştirmek istediğin değeri bulup düzenlemen yeterli.
    
    - nodeCount: Ağdaki düğüm sayısı (arttırınca daha yoğun ağ)
    - nodeSpeed: Düğümlerin hareket hızı (düşük = yavaş)
    - connectionDistance: Düğümler arası bağlantı mesafesi
    - mouseInfluenceRadius: Mouse'un etki alanı (desktop)
    - touchInfluenceRadius: Dokunmatik etki alanı (mobil)
    
    YENİ BÖLÜM EKLEMEK İÇİN:
    -------------------------
    1. index.html'de <nav> ve <main> bölümlerine ekle
    2. Aşağıdaki SECTIONS listesine ekle:
       { id: 5, name: 'Yeni Bölüm', nameEn: 'New Section', url: '#yeni-bolum' }
    
    Not: id benzersiz olmalı. name Türkçe, nameEn İngilizce arama için.
*/

(function() {
    'use strict';

    // ============================================
    // KONTROL VE BAŞLATMA
    // ============================================
    const canvas = document.getElementById('networkCanvas');
    if (!canvas) {
        console.warn('Canvas bulunamadı!');
        return;
    }
    
    const ctx = canvas.getContext('2d');
    if (!ctx) {
        console.warn('Canvas context alınamadı!');
        return;
    }

    // ============================================
    // AYARLAR - Kolayca Değiştirilebilir
    // ============================================
    const SETTINGS = {
        isMobile: window.innerWidth < 768,
        nodeCount: 80,
        nodeMinRadius: 0.5,
        nodeMaxRadius: 2,
        nodeSpeed: 0.1,
        nodeMaxSpeed: 0.25,
        connectionDistance: 180,
        connectionBaseOpacity: 0.4,
        connectionLineWidth: 1,
        touchInfluenceRadius: 200,
        mouseInfluenceRadius: 300,
        gravityEffect: 0.3,
        depthEffect: 40,
        logoMargin: 120,
        logoPushForce: 0.2,
        safeMargin: 20,
        returnForce: 0.0002
    };

    const SECTIONS = [
        { id: 0, name: 'FlowPy', nameEn: 'FlowPy', url: '#flowpy' },
        { id: 1, name: 'Ana Sayfa', nameEn: 'Home', url: '#home' },
        { id: 2, name: 'Derleyici', nameEn: 'Executer', url: '#executer' },
        { id: 3, name: 'FlowingTR', nameEn: 'FlowingTR', url: '#flowingtr' },
        { id: 4, name: 'Hakkımızda', nameEn: 'About', url: '#about' },
        { id: 5, name: 'SSS', nameEn: 'FAQ', url: '#faq' }
    ];

    let inputX = window.innerWidth / 2;
    let inputY = window.innerHeight / 2;
    let targetInputX = inputX;
    let targetInputY = inputY;

    class Node {
        constructor(x, y) {
            this.x = clamp(x, 0, canvas.width);
            this.y = clamp(y, 0, canvas.height);
            this.originalX = this.x;
            this.originalY = this.y;
            this.vx = (Math.random() - 0.5) * SETTINGS.nodeSpeed;
            this.vy = (Math.random() - 0.5) * SETTINGS.nodeSpeed;
            this.radius = randomRange(SETTINGS.nodeMinRadius, SETTINGS.nodeMaxRadius);
            this.mass = randomRange(0.5, 1.0);
            this.visible = true;
        }
        update() {
            this.x += this.vx; this.y += this.vy;
            this.checkBoundaries(); this.avoidLogo(); this.limitSpeed();
            this.applyInputForce(); this.returnToOrigin(); this.updateVisibility();
        }
        checkBoundaries() {
            if (this.x < -50) this.vx = Math.abs(this.vx) * 0.5;
            if (this.x > canvas.width + 50) this.vx = -Math.abs(this.vx) * 0.5;
            if (this.y < -50) this.vy = Math.abs(this.vy) * 0.5;
            if (this.y > canvas.height + 50) this.vy = -Math.abs(this.vy) * 0.5;
        }
        updateVisibility() {
            const m = 100;
            this.visible = this.x > -m && this.x < canvas.width + m && this.y > -m && this.y < canvas.height + m;
        }
        avoidLogo() {
            const topBarHeight = 60;
            if (this.y < topBarHeight + SETTINGS.logoMargin) {
                const logo = document.querySelector('.header-logo-img');
                if (!logo) return;
                const rect = logo.getBoundingClientRect();
                const cx = rect.left + rect.width / 2, cy = rect.top + rect.height / 2;
                const dx = this.x - cx, dy = this.y - cy, dist = Math.sqrt(dx * dx + dy * dy);
                if (dist > 0 && dist < SETTINGS.logoMargin) {
                    this.vx += (dx / dist) * SETTINGS.logoPushForce;
                    this.vy += (dy / dist) * SETTINGS.logoPushForce;
                }
            }
        }
        limitSpeed() {
            const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
            if (speed > SETTINGS.nodeMaxSpeed) {
                this.vx = (this.vx / speed) * SETTINGS.nodeMaxSpeed;
                this.vy = (this.vy / speed) * SETTINGS.nodeMaxSpeed;
            }
        }
        applyInputForce() {
            const dx = inputX - this.x, dy = inputY - this.y, dist = Math.sqrt(dx * dx + dy * dy);
            const influenceRadius = SETTINGS.isMobile ? SETTINGS.touchInfluenceRadius : SETTINGS.mouseInfluenceRadius;
            if (dist < influenceRadius && dist > 0) {
                const force = (influenceRadius - dist) / influenceRadius;
                if (SETTINGS.isMobile) {
                    this.vx += (dx / dist) * force * 0.02;
                    this.vy += (dy / dist) * force * 0.02;
                } else {
                    this.vy += force * SETTINGS.gravityEffect * this.mass;
                    this.vx += (dx / dist) * force * 0.005;
                    this.vy += (dy / dist) * force * 0.005;
                }
            }
        }
        returnToOrigin() {
            this.vx += (this.originalX - this.x) * SETTINGS.returnForce;
            this.vy += (this.originalY - this.y) * SETTINGS.returnForce;
        }
        draw() {
            if (!this.visible) return;
            ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.beginPath(); ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2); ctx.fill();
        }
    }

    function drawConnections() {
        for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].visible) continue;
            for (let j = i + 1; j < nodes.length; j++) {
                if (!nodes[j].visible) continue;
                const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y, dist = Math.sqrt(dx * dx + dy * dy);
                if (dist < SETTINGS.connectionDistance) {
                    const midX = (nodes[i].x + nodes[j].x) / 2, midY = (nodes[i].y + nodes[j].y) / 2;
                    let opacity = (1 - (dist / SETTINGS.connectionDistance)) * SETTINGS.connectionBaseOpacity;
                    let sagging = 0;
                    if (!SETTINGS.isMobile) {
                        const inputDist = Math.sqrt(Math.pow(inputX - midX, 2) + Math.pow(inputY - midY, 2));
                        if (inputDist < SETTINGS.mouseInfluenceRadius) {
                            const sagForce = (SETTINGS.mouseInfluenceRadius - inputDist) / SETTINGS.mouseInfluenceRadius;
                            opacity += sagForce * 0.4; sagging = sagForce * SETTINGS.depthEffect;
                        }
                    }
                    opacity = clamp(opacity, 0, 1);
                    ctx.strokeStyle = `rgba(245, 158, 11, ${opacity})`;
                    ctx.lineWidth = SETTINGS.connectionLineWidth;
                    ctx.beginPath(); ctx.moveTo(nodes[i].x, nodes[i].y);
                    ctx.quadraticCurveTo(midX, midY + sagging, nodes[j].x, nodes[j].y); ctx.stroke();
                }
            }
        }
    }

    function drawInputConnections() {
        const influenceRadius = SETTINGS.isMobile ? SETTINGS.touchInfluenceRadius : SETTINGS.mouseInfluenceRadius;
        for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].visible) continue;
            const dx = inputX - nodes[i].x, dy = inputY - nodes[i].y, dist = Math.sqrt(dx * dx + dy * dy);
            if (dist < influenceRadius) {
                const opacity = (1 - (dist / influenceRadius)) * 0.7;
                ctx.strokeStyle = `rgba(245, 158, 11, ${clamp(opacity, 0, 1)})`;
                ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(inputX, inputY); ctx.lineTo(nodes[i].x, nodes[i].y); ctx.stroke();
            }
        }
        ctx.fillStyle = 'rgba(245, 158, 11, 0.9)';
        ctx.beginPath(); ctx.arc(inputX, inputY, 4, 0, Math.PI * 2); ctx.fill();
    }

    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const searchContainer = document.getElementById('searchContainer');

    function performSearch(query) {
        if (!query || query.trim() === '') { searchResults.classList.remove('active'); return; }
        const lowerQuery = query.toLowerCase();
        const matches = SECTIONS.filter(s => s.name.toLowerCase().includes(lowerQuery) || s.nameEn.toLowerCase().includes(lowerQuery)).slice(0, 2);
        if (matches.length > 0) {
            searchResults.textContent = '';
            matches.forEach(section => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.setAttribute('data-url', section.url);
                item.textContent = section.name;
                item.addEventListener('click', function() { navigateToSection(section.url); });
                searchResults.appendChild(item);
            });
            searchResults.classList.add('active');
        } else {
            searchResults.textContent = '';
            const item = document.createElement('div');
            item.className = 'search-result-item search-result-empty';
            item.textContent = 'Sonuç bulunamadı';
            searchResults.appendChild(item);
            searchResults.classList.add('active');
        }
    }

    async function navigateToSection(url) {
        searchInput.value = ''; searchResults.classList.remove('active');
        saveCurrentFile(); await saveFilesToStorage();
        window.location.hash = url; setActiveNav(url);
    }

    function setActiveNav(url) {
        document.querySelectorAll('.nav-link').forEach(link => link.classList.toggle('active', link.getAttribute('href') === url));
    }

    window.addEventListener('hashchange', () => {
        const currentHash = window.location.hash || '#flowpy';
        setActiveNav(currentHash);
        document.body.classList.toggle('on-flowpy', currentHash === '#flowpy');
        updateConsoleVisibility();
    });

    if (searchInput) {
        searchInput.addEventListener('input', (e) => performSearch(e.target.value));
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const firstResult = document.querySelector('.search-result-item');
                if (firstResult) firstResult.click();
            }
        });
        document.addEventListener('click', (e) => { if (!searchContainer.contains(e.target)) searchResults.classList.remove('active'); });
    }

    const nodes = [];
    function animate() {
        inputX += (targetInputX - inputX) * 0.1;
        inputY += (targetInputY - inputY) * 0.1;
        const bgColor = document.body.classList.contains('dark-mode') ? '#1a1a1a' : '#ffffff';
        ctx.fillStyle = bgColor; ctx.fillRect(0, 0, canvas.width, canvas.height);
        drawConnections(); drawInputConnections();
        nodes.forEach(node => { node.update(); node.draw(); });
        requestAnimationFrame(animate);
    }

    function init() {
        canvas.width = window.innerWidth; canvas.height = window.innerHeight;
        nodes.length = 0;
        const cols = 8, rows = Math.ceil(SETTINGS.nodeCount / cols);
        const spacingX = (canvas.width - SETTINGS.safeMargin * 2) / cols;
        const spacingY = (canvas.height - SETTINGS.safeMargin * 2) / rows;
        for (let i = 0; i < SETTINGS.nodeCount; i++) {
            const col = i % cols, row = Math.floor(i / cols);
            const x = SETTINGS.safeMargin + spacingX * (col + 0.5) + (Math.random() - 0.5) * spacingX * 0.5;
            const y = SETTINGS.safeMargin + spacingY * (row + 0.5) + (Math.random() - 0.5) * spacingY * 0.5;
            const topBarHeight = 60;
            const logo = document.querySelector('.header-logo-img');
            let inLogoArea = false;
            if (logo && y < topBarHeight + SETTINGS.logoMargin) {
                const rect = logo.getBoundingClientRect();
                const logoCenterX = rect.left + rect.width / 2, logoCenterY = rect.top + rect.height / 2;
                if (Math.abs(x - logoCenterX) < SETTINGS.logoMargin && Math.abs(y - logoCenterY) < SETTINGS.logoMargin) inLogoArea = true;
            }
            if (!inLogoArea) nodes.push(new Node(x, y));
        }
        while (nodes.length < SETTINGS.nodeCount) {
            const x = SETTINGS.safeMargin + Math.random() * (canvas.width - SETTINGS.safeMargin * 2);
            const y = SETTINGS.safeMargin + Math.random() * (canvas.height - SETTINGS.safeMargin * 2);
            nodes.push(new Node(x, y));
        }
    }

    if (!SETTINGS.isMobile) {
        document.addEventListener('mousemove', (e) => {
            targetInputX = clamp(e.clientX, 0, canvas.width);
            targetInputY = clamp(e.clientY, 0, canvas.height);
        });
    }
    if (SETTINGS.isMobile) {
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length > 0) {
                targetInputX = clamp(e.touches[0].clientX, 0, canvas.width);
                targetInputY = clamp(e.touches[0].clientY, 0, canvas.height);
            }
        });
        document.addEventListener('touchend', () => { targetInputX = canvas.width / 2; targetInputY = canvas.height / 2; });
    }
    let resizeTimeout;
    window.addEventListener('resize', () => { clearTimeout(resizeTimeout); resizeTimeout = setTimeout(init, 200); });

    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');

    function toggleTheme() {
        document.body.classList.toggle('dark-mode');
        if (typeof editor !== 'undefined' && editor) {
            editor.setOption('theme', document.body.classList.contains('dark-mode') ? 'dracula' : 'idea');
        }
        if (document.body.classList.contains('dark-mode')) {
            themeIcon.src = 'Assets/moon.svg'; localStorage.setItem('theme', 'dark');
        } else {
            themeIcon.src = 'Assets/sun.svg'; localStorage.setItem('theme', 'light');
        }
    }
    if (themeToggle) themeToggle.addEventListener('click', toggleTheme);
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') { document.body.classList.add('dark-mode'); if (themeIcon) themeIcon.src = 'Assets/moon.svg'; }

    const devLink = document.getElementById('devLink');
    const studioLink = document.getElementById('studioLink');
    const devDropdown = document.getElementById('devDropdown');
    const studioDropdown = document.getElementById('studioDropdown');

    function toggleDropdown(dropdown) {
        if (dropdown === devDropdown && studioDropdown) studioDropdown.classList.remove('active');
        if (dropdown === studioDropdown && devDropdown) devDropdown.classList.remove('active');
        dropdown.classList.toggle('active');
    }
    if (devLink && devDropdown) devLink.addEventListener('click', (e) => { e.stopPropagation(); toggleDropdown(devDropdown); });
    if (studioLink && studioDropdown) studioLink.addEventListener('click', (e) => { e.stopPropagation(); toggleDropdown(studioDropdown); });
    document.addEventListener('click', () => { if (devDropdown) devDropdown.classList.remove('active'); if (studioDropdown) studioDropdown.classList.remove('active'); });

    function updateActiveSectionOnScroll() {
        const sections = document.querySelectorAll('.section');
        let currentSection = '#flowpy', maxVisibleArea = 0;
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            const visibleHeight = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0);
            if (visibleHeight > maxVisibleArea) { maxVisibleArea = visibleHeight; currentSection = '#' + section.id; }
        });
        setActiveNav(currentSection);
        document.body.classList.toggle('on-flowpy', currentSection === '#flowpy');
        updateConsoleVisibility();
    }

    // ============================================
    // KONSOL GÖRÜNÜRLÜĞÜ - Sadece Executer bölümünde
    // ============================================
    const consolePanelEl = document.getElementById('consolePanel');
    let consoleHideTimeout = null;

    function updateConsoleVisibility() {
        if (!consolePanelEl) return;
        const currentHash = window.location.hash || '#flowpy';
        const isExecuter = currentHash === '#executer';
        
        // Scroll pozisyonu da kontrol et (Executer bölümüne yakınsa göster)
        const executerSection = document.getElementById('executer');
        let scrollNearExecuter = false;
        if (executerSection) {
            const rect = executerSection.getBoundingClientRect();
            scrollNearExecuter = rect.top < window.innerHeight && rect.bottom > 0;
        }
        
        const shouldShow = isExecuter || scrollNearExecuter;
        
        clearTimeout(consoleHideTimeout);
        
        if (shouldShow) {
            consolePanelEl.classList.remove('console-fade-out', 'console-hidden');
        } else {
            consolePanelEl.classList.add('console-fade-out');
            consoleHideTimeout = setTimeout(() => {
                consolePanelEl.classList.add('console-hidden');
                consolePanelEl.classList.remove('console-fade-out');
            }, 400);
        }
    }

    const FAQ_ITEMS = [
        { question: 'Karanlık ve aydınlık mod ne işe yarar nasıl açılır?', answer: 'Karanlık mod, gece kullanımında göz yorgunluğunu azaltır ve daha az enerji tüketir. Üst çubuğun sağ tarafındaki güneş/ay simgesine tıklayarak açılır/kapatılır. Tercihiniz localStorage\'da saklanır.' },
        { question: 'Bu site ne işe yarar?', answer: 'FlowPy, Python kodlarını görsel akış diyagramlarına dönüştüren ve derleyen bir geliştirme aracıdır. Kod yazmayı ve akışları görselleştirmeyi birleştirir.' },
        { question: 'TurcoDevelopStudio nedir?', answer: 'TurcoDevelopStudio, Türkçe geliştirici topluluğu ve açık kaynak projeler geliştiren bir yazılım stüdyosudur. Berkay Özdemir (bercaius) ve BrahimTKM (İbrahim Talha Kömürcü) tarafından kurulmuştur.' },
        { question: 'Derleyiciyi yaparken hangi kütüphaneleri kullandınız?', answer: 'Python\'un built-in ast modülünü ve sys modülünü kullandık. Ayrıca özel dönüştürücüler geliştirdik. Tarayıcıda Python çalıştırmak için Pyodide kullanıyoruz.' },
        { question: 'Derleyicide bir hata olursa hangi eposta adresinden iletişime geçebilirim?', answer: 'berkayozdemirtrtr@gmail.com adresinden bizimle iletişime geçebilirsiniz.' },
        { question: 'Sitedeki Deneme modu tam sürümmü yoksa tam teşekküllü bir sürümde var mı?', answer: 'Evet, sitede deneme sürümü bulunmaktadır. Tam sürümde ek özellikler ve daha gelişmiş derleyici bulunmaktadır.' },
        { question: 'Hangi kütüphaneleri kullanabilirim?', answer: 'Pyodide sayesinde numpy, pandas, matplotlib, scipy, scikit-learn, requests, beautifulsoup4 ve daha birçok popüler Python kütüphanesini tarayıcınızda kullanabilirsiniz. Kütüphaneler butonundan yükleyebilirsiniz.' },
        { question: 'Kod editöründe hangi özellikler var?', answer: 'CodeMirror tabanlı editörümüzde Jupyter benzeri renklendirme, otomatik tamamlama, satır numaraları, kod katlama, parantez eşleştirme, arama/değiştirme ve daha birçok özellik bulunur.' }
    ];

    function initFAQAccordion() {
        const accordion = document.getElementById('faqAccordion');
        if (!accordion) return;
        FAQ_ITEMS.forEach(item => {
            const accordionItem = document.createElement('div');
            accordionItem.className = 'accordion-item';
            const header = document.createElement('div');
            header.className = 'accordion-header';
            header.textContent = item.question;
            const content = document.createElement('div');
            content.className = 'accordion-content';
            const paragraph = document.createElement('p');
            paragraph.textContent = item.answer;
            content.appendChild(paragraph);
            accordionItem.appendChild(header);
            accordionItem.appendChild(content);
            accordion.appendChild(accordionItem);
            header.addEventListener('click', () => {
                const isActive = accordionItem.classList.contains('active');
                document.querySelectorAll('.accordion-item').forEach(function(item) {
                    item.classList.remove('active');
                    item.querySelector('.accordion-content').style.maxHeight = null;
                });
                if (!isActive) { accordionItem.classList.add('active'); content.style.maxHeight = content.scrollHeight + 'px'; }
            });
        });
    }

    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const headerRight = document.getElementById('headerRight');
    if (mobileMenuBtn && headerRight) {
        mobileMenuBtn.addEventListener('click', function() { mobileMenuBtn.classList.toggle('active'); headerRight.classList.toggle('active'); });
        document.querySelectorAll('.nav-link').forEach(link => { link.addEventListener('click', () => { mobileMenuBtn.classList.remove('active'); headerRight.classList.remove('active'); }); });
        document.addEventListener('click', function(e) { if (!headerRight.contains(e.target) && !mobileMenuBtn.contains(e.target)) { mobileMenuBtn.classList.remove('active'); headerRight.classList.remove('active'); } });
    }

    // BAŞLAT
    init(); animate(); initFAQAccordion();
    window.scrollTo(0, 0);
    const initialHash = window.location.hash || '#flowpy';
    setActiveNav(initialHash);
    document.body.classList.toggle('on-flowpy', initialHash === '#flowpy');
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            saveCurrentFile(); saveFilesToStorage();
            const href = link.getAttribute('href');
            setActiveNav(href);
            document.body.classList.toggle('on-flowpy', href === '#flowpy');
            updateConsoleVisibility();
        });
    });
    let scrollTicking = false;
    window.addEventListener('scroll', () => {
        if (!scrollTicking) { requestAnimationFrame(() => { updateActiveSectionOnScroll(); scrollTicking = false; }); scrollTicking = true; }
    });
    updateActiveSectionOnScroll();

    // ============================================
    // DERLEYİCİ - CodeMirror + Pyodide + Workspace
    // ============================================
    const codeEditor = document.getElementById('codeEditor');
    const outputBody = document.getElementById('outputBody');
    const outputPanel = document.getElementById('consolePanel');
    const ideStatus = document.getElementById('ideStatus');
    const flowStatus = document.getElementById('flowStatus');
    const flowCanvas = document.getElementById('flowCanvas');
    const fileTabsContainer = document.getElementById('fileTabs');
    const btnRun = document.getElementById('btnRun');
    const btnSync = document.getElementById('btnSync');
    const btnStop = document.getElementById('btnStop');
    const btnNewFile = document.getElementById('btnNewFile');
    const btnClearOutput = document.getElementById('btnClearOutput');
    const btnReport = document.getElementById('btnReport');
    const reportModal = document.getElementById('reportModal');
    const btnCancelReport = document.getElementById('btnCancelReport');
    const btnSendReport = document.getElementById('btnSendReport');
    const reportText = document.getElementById('reportText');
    const btnFullscreen = document.getElementById('btnFullscreen');

    let currentFile = 'main.py';
    let files = { 'main.py': '# Python kodunuzu buraya yazın\ndef merhaba():\n    print("Merhaba FlowPy!")\n\nmerhaba()\n' };
    let pyodideReady = false;
    let formspreeEndpoint = 'https://formspree.io/f/mzepzgpa';
    let editor = null;
    let isRunning = false;
    let loadedLibraries = new Set();

    // CODEMIRROR
    function initCodeMirror() {
        if (typeof CodeMirror === 'undefined' || !codeEditor) { console.warn('CodeMirror yüklenemedi.'); return; }
        const isDark = document.body.classList.contains('dark-mode');
        editor = CodeMirror.fromTextArea(codeEditor, {
            mode: 'python', theme: isDark ? 'dracula' : 'idea', lineNumbers: true, matchBrackets: true, autoCloseBrackets: true,
            extraKeys: {
                'Ctrl-Space': 'autocomplete', 'Ctrl-/': 'toggleComment', 'Cmd-/': 'toggleComment',
                'Ctrl-F': 'findPersistent', 'Cmd-F': 'findPersistent',
                'Ctrl-Enter': function() { runPython(); }, 'Cmd-Enter': function() { runPython(); }, 'Shift-Enter': function() { runPython(); },
                'F11': function(cm) { toggleFullscreen(); }, 'Esc': function(cm) { if (cm.getOption('fullScreen')) toggleFullscreen(); }
            },
            gutters: ['CodeMirror-linenumbers', 'CodeMirror-foldgutter'], foldGutter: true, styleActiveLine: true,
            autoRefresh: true, placeholder: '# Python kodunuzu buraya yazın\ndef merhaba():\n    print(\'Merhaba FlowPy!\')\n\nmerhaba()',
            indentUnit: 4, tabSize: 4, indentWithTabs: false, lineWrapping: false, scrollbarStyle: 'native', viewportMargin: Infinity
        });
        editor.on('inputRead', function(cm, change) {
            if (change.text[0] && /[\w.]/.test(change.text[0])) { setTimeout(function() { cm.showHint({ completeSingle: false }); }, 300); }
        });
        editor.on('change', function() { saveCurrentFile(); });
        codeEditor.style.display = 'none';
        const cmWrapper = editor.getWrapperElement();
        cmWrapper.classList.add('cm-editor-wrapper');
        codeEditor.parentElement.appendChild(cmWrapper);
        if (btnFullscreen) btnFullscreen.addEventListener('click', toggleFullscreen);
    }

    function toggleFullscreen() { if (!editor) return; const isFull = editor.getOption('fullScreen'); editor.setOption('fullScreen', !isFull); if (!isFull) editor.refresh(); }
    function getEditorValue() { return editor ? editor.getValue() : codeEditor.value; }
    function setEditorValue(value) { if (editor) { editor.setValue(value || ''); editor.refresh(); } else { codeEditor.value = value || ''; } }

    // DOSYA YÖNETİMİ
    async function loadFilesFromStorage() {
        try {
            if (typeof localforage !== 'undefined') { const stored = await localforage.getItem('flowpy_files'); if (stored && typeof stored === 'object') files = stored; }
        } catch (e) { console.warn('Dosyalar yüklenemedi:', e); }
        if (fileTabsContainer) {
            fileTabsContainer.innerHTML = '';
            fileTabsContainer.appendChild(createFileTab(currentFile));
        }
        setEditorValue(files[currentFile] || '');
    }

    async function saveFilesToStorage() {
        try { if (typeof localforage !== 'undefined') await localforage.setItem('flowpy_files', files); } catch (e) { console.warn('Dosyalar kaydedilemedi:', e); }
    }

    // WORKSPACE
    const workspaceTree = document.getElementById('workspaceTree');
    const contextMenu = document.getElementById('contextMenu');
    const btnNewFolder = document.getElementById('btnNewFolder');
    const btnNewFileWS = document.getElementById('btnNewFileWS');
    const btnExportZip = document.getElementById('btnExportZip');
    const btnImportZip = document.getElementById('btnImportZip');
    const zipInput = document.getElementById('zipInput');

    let workspaceItems = [];
    let selectedItemId = null;
    let contextTargetId = null;
    let nextId = 1;

    function generateId() { return 'item_' + Date.now() + '_' + (nextId++); }
    function getItemById(id) { return workspaceItems.find(item => item.id === id); }
    function getChildren(parentId) { return workspaceItems.filter(item => item.parentId === parentId); }

    function createFolder(name, parentId) {
        const folder = { id: generateId(), name: name, type: 'folder', parentId: parentId || null, createdAt: Date.now(), updatedAt: Date.now() };
        workspaceItems.push(folder); return folder;
    }
    function createFile(name, parentId, content) {
        const file = { id: generateId(), name: name, type: 'file', parentId: parentId || null, content: content || '', createdAt: Date.now(), updatedAt: Date.now() };
        workspaceItems.push(file); return file;
    }
    function deleteItem(id) {
        const item = getItemById(id); if (!item) return;
        getChildren(id).forEach(child => deleteItem(child.id));
        const index = workspaceItems.findIndex(i => i.id === id);
        if (index > -1) workspaceItems.splice(index, 1);
        if (currentFile === item.name && item.type === 'file') {
            const root = workspaceItems.find(i => i.name === 'main.py' && i.type === 'file' && !i.parentId);
            if (root) { switchToFile(root.name); files[root.name] = root.content; }
        }
    }
    function renameItem(id, newName) { const item = getItemById(id); if (!item) return; item.name = newName; item.updatedAt = Date.now(); }

    function renderWorkspaceTree() {
        if (!workspaceTree) return;
        workspaceTree.innerHTML = '';
        const rootItems = getChildren(null).sort((a, b) => { if (a.type === b.type) return a.name.localeCompare(b.name); return a.type === 'folder' ? -1 : 1; });
        rootItems.forEach(item => workspaceTree.appendChild(renderTreeItem(item, 0)));
    }

    function renderTreeItem(item, depth) {
        const div = document.createElement('div');
        div.className = 'workspace-item' + (item.id === selectedItemId ? ' active' : '');
        div.style.paddingLeft = (12 + depth * 18) + 'px';
        div.setAttribute('data-id', item.id);
        const icon = document.createElement('span'); icon.className = 'workspace-item-icon'; icon.textContent = item.type === 'folder' ? '📁' : '📄';
        const name = document.createElement('span'); name.className = 'workspace-item-name'; name.textContent = item.name;
        const actions = document.createElement('div'); actions.className = 'workspace-item-actions';
        const renameBtn = document.createElement('button'); renameBtn.className = 'workspace-item-btn'; renameBtn.textContent = '✏️'; renameBtn.title = 'Yeniden Adlandır';
        renameBtn.addEventListener('click', (e) => { e.stopPropagation(); startRename(item.id); });
        const deleteBtn = document.createElement('button'); deleteBtn.className = 'workspace-item-btn'; deleteBtn.textContent = '🗑️'; deleteBtn.title = 'Sil';
        deleteBtn.addEventListener('click', (e) => { e.stopPropagation(); if (confirm('"' + item.name + '" silinsin mi?')) { deleteItem(item.id); saveWorkspaceToStorage(); renderWorkspaceTree(); } });
        actions.appendChild(renameBtn); actions.appendChild(deleteBtn);
        div.appendChild(icon); div.appendChild(name); div.appendChild(actions);
        div.addEventListener('click', () => { selectedItemId = item.id; if (item.type === 'file') openFile(item); renderWorkspaceTree(); });
        div.addEventListener('contextmenu', (e) => { e.preventDefault(); selectedItemId = item.id; contextTargetId = item.id; showContextMenu(e.clientX, e.clientY); renderWorkspaceTree(); });
        div.addEventListener('dblclick', () => { if (item.type === 'file') startRename(item.id); });
        if (item.type === 'folder') {
            const children = getChildren(item.id).sort((a, b) => { if (a.type === b.type) return a.name.localeCompare(b.name); return a.type === 'folder' ? -1 : 1; });
            children.forEach(child => div.appendChild(renderTreeItem(child, depth + 1)));
        }
        return div;
    }

    function openFile(item) {
        if (item.type !== 'file') return;
        currentFile = item.name; files[item.name] = item.content || ''; setEditorValue(files[item.name]);
        let tab = document.querySelector('.file-tab[data-file="' + item.name + '"]');
        if (!tab) { tab = createFileTab(item.name); fileTabsContainer.appendChild(tab); }
        document.querySelectorAll('.file-tab').forEach(t => t.classList.toggle('active', t.getAttribute('data-file') === item.name));
        selectedItemId = item.id; renderWorkspaceTree(); setStatus(ideStatus, 'Düzenleniyor: ' + item.name);
    }

    function startRename(id) {
        const item = getItemById(id); if (!item) return;
        const newName = prompt('Yeni ad:', item.name); if (!newName || newName === item.name) return;
        renameItem(id, newName); saveWorkspaceToStorage(); renderWorkspaceTree();
    }

    function showContextMenu(x, y) { contextMenu.style.left = x + 'px'; contextMenu.style.top = y + 'px'; contextMenu.style.display = 'block'; }
    function hideContextMenu() { contextMenu.style.display = 'none'; contextTargetId = null; }

    document.getElementById('ctxNewFile').addEventListener('click', () => { hideContextMenu(); if (!contextTargetId) return; const target = getItemById(contextTargetId); openNewFileModal(target && target.type === 'folder' ? target.id : null); });
    document.getElementById('ctxNewFolder').addEventListener('click', () => { hideContextMenu(); const parentId = contextTargetId ? (getItemById(contextTargetId).type === 'folder' ? contextTargetId : null) : null; openNewFolderModal(parentId); });
    document.getElementById('ctxRename').addEventListener('click', () => { hideContextMenu(); if (contextTargetId) startRename(contextTargetId); });
    document.getElementById('ctxDelete').addEventListener('click', () => { hideContextMenu(); if (contextTargetId) { const item = getItemById(contextTargetId); if (confirm('"' + item.name + '" silinsin mi?')) { deleteItem(contextTargetId); saveWorkspaceToStorage(); renderWorkspaceTree(); } } });
    document.addEventListener('click', (e) => { if (!contextMenu.contains(e.target)) hideContextMenu(); });

    // YENİ DOSYA / KLASÖR MODALLERİ
    let pendingNewFileParentId = null, pendingNewFolderParentId = null;

    function openNewFileModal(parentId) { pendingNewFileParentId = parentId || null; const modal = document.getElementById('newFileModal'), input = document.getElementById('newFileName'); if (!modal || !input) return; modal.classList.add('active'); input.value = ''; input.focus(); }
    function createNewFile() {
        const input = document.getElementById('newFileName'), modal = document.getElementById('newFileModal');
        if (!input || !modal) return; const name = input.value.trim();
        if (!name) { alert('Lütfen dosya adı girin.'); return; }
        if (!name.endsWith('.py')) { alert('Lütfen .py uzantılı dosya adı girin.'); return; }
        const parentId = pendingNewFileParentId;
        if (workspaceItems.find(i => i.name === name && i.parentId === parentId)) { alert('Bu klasörde aynı isimde dosya zaten var.'); return; }
        const file = createFile(name, parentId, ''); openFile(file); saveWorkspaceToStorage(); renderWorkspaceTree(); modal.classList.remove('active'); pendingNewFileParentId = null;
    }
    function closeNewFileModal() { const modal = document.getElementById('newFileModal'); if (modal) modal.classList.remove('active'); pendingNewFileParentId = null; }

    function openNewFolderModal(parentId) { pendingNewFolderParentId = parentId || null; const modal = document.getElementById('newFolderModal'), input = document.getElementById('newFolderName'); if (!modal || !input) return; modal.classList.add('active'); input.value = ''; input.focus(); }
    function createNewFolder() {
        const input = document.getElementById('newFolderName'), modal = document.getElementById('newFolderModal');
        if (!input || !modal) return; const name = input.value.trim();
        if (!name) { alert('Lütfen klasör adı girin.'); return; }
        const parentId = pendingNewFolderParentId;
        if (workspaceItems.find(i => i.name === name && i.parentId === parentId && i.type === 'folder')) { alert('Bu klasörde aynı isimde klasör zaten var.'); return; }
        createFolder(name, parentId); saveWorkspaceToStorage(); renderWorkspaceTree(); modal.classList.remove('active'); pendingNewFolderParentId = null;
    }
    function closeNewFolderModal() { const modal = document.getElementById('newFolderModal'); if (modal) modal.classList.remove('active'); pendingNewFolderParentId = null; }

    if (btnNewFolder) btnNewFolder.addEventListener('click', () => openNewFolderModal(null));
    if (btnNewFileWS) btnNewFileWS.addEventListener('click', () => openNewFileModal(null));

    // ZIP Export
    if (btnExportZip) {
        btnExportZip.addEventListener('click', async () => {
            if (typeof JSZip === 'undefined') { alert('JSZip kütüphanesi yüklenemedi.'); return; }
            saveCurrentFile(); await saveWorkspaceToStorage();
            const zip = new JSZip();
            const rootFiles = workspaceItems.filter(item => !item.parentId);
            function addToZip(items, folder) { items.forEach(item => { if (item.type === 'folder') { const subfolder = folder.folder(item.name); addToZip(workspaceItems.filter(i => i.parentId === item.id), subfolder); } else { folder.file(item.name, item.content || ''); } }); }
            addToZip(rootFiles, zip);
            const blob = await zip.generateAsync({type: 'blob'}), url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = 'flowpy_workspace.zip'; a.click(); URL.revokeObjectURL(url);
        });
    }
    if (btnImportZip) btnImportZip.addEventListener('click', () => zipInput.click());

    if (zipInput) {
        zipInput.addEventListener('change', async (e) => {
            if (typeof JSZip === 'undefined') { alert('JSZip yüklenemedi.'); return; }
            const file = e.target.files[0]; if (!file) return;
            try {
                const zip = await JSZip.loadAsync(file); workspaceItems = []; nextId = 1;
                async function processZip(folder, parentId) {
                    const entries = Object.keys(folder.files);
                    for (const path of entries) {
                        const zipEntry = folder.files[path], parts = path.split('/').filter(p => p);
                        if (parts.length === 0) continue;
                        if (zipEntry.dir) { const folderItem = createFolder(parts[parts.length - 1], parentId); await processZip(zipEntry, folderItem.id); }
                        else { const content = await zipEntry.async('string'); createFile(parts[parts.length - 1], parentId, content); }
                    }
                }
                await processZip(zip, null); saveWorkspaceToStorage(); renderWorkspaceTree(); appendOutput('Workspace içeri aktarıldı: ' + file.name, 'success');
            } catch (err) { appendOutput('ZIP içe aktarma hatası: ' + err.message, 'error'); }
            zipInput.value = '';
        });
    }

    async function loadWorkspaceFromStorage() {
        try {
            if (typeof localforage !== 'undefined') { const stored = await localforage.getItem('flowpy_workspace'); if (stored && Array.isArray(stored.items)) { workspaceItems = stored.items; nextId = stored.nextId || 1; } }
        } catch (e) { console.warn('Workspace yüklenemedi:', e); }
        if (workspaceItems.length === 0) { createFile('main.py', null, '# Python kodunuzu buraya yazın\ndef merhaba():\n    print("Merhaba FlowPy!")\n\nmerhaba()\n'); createFolder('proje', null); saveWorkspaceToStorage(); }
        renderWorkspaceTree();
    }

    async function saveWorkspaceToStorage() {
        try { if (typeof localforage !== 'undefined') await localforage.setItem('flowpy_workspace', { items: workspaceItems, nextId: nextId }); } catch (e) { console.warn('Workspace kaydedilemedi:', e); }
    }

    const workspaceAutoSave = setInterval(saveWorkspaceToStorage, 30000);
    window.addEventListener('beforeunload', () => { clearInterval(workspaceAutoSave); saveWorkspaceToStorage(); });

    // KONSOL
    function appendOutput(text, type) {
        if (!outputBody) return;
        type = type || 'info';
        const span = document.createElement('span');
        span.className = 'output-text output-' + type;
        span.textContent = text;
        outputBody.appendChild(span);
        outputBody.scrollTop = outputBody.scrollHeight;
    }
    function clearOutput() { outputBody.innerHTML = ''; appendOutput('Çıktı temizlendi.', 'info'); }
    function setStatus(element, text) { if (element) element.textContent = text; }

    const btnToggleOutput = document.getElementById('btnToggleOutput');
    if (btnToggleOutput) {
        btnToggleOutput.addEventListener('click', () => {
            outputPanel.classList.toggle('collapsed');
            const icon = btnToggleOutput.querySelector('.toggle-icon');
            icon.textContent = outputPanel.classList.contains('collapsed') ? '▲' : '_';
            btnToggleOutput.title = outputPanel.classList.contains('collapsed') ? 'Genişlet' : 'Küçült';
        });
    }
    const outputResizer = document.getElementById('outputResizer');
    if (outputResizer) {
        let isResizing = false;
        outputResizer.addEventListener('mousedown', (e) => { isResizing = true; e.preventDefault(); document.body.style.cursor = 'ns-resize'; });
        document.addEventListener('mousemove', (e) => { if (!isResizing) return; const height = window.innerHeight - e.clientY; outputPanel.style.height = Math.max(100, Math.min(500, height)) + 'px'; outputPanel.classList.remove('collapsed'); });
        document.addEventListener('mouseup', () => { isResizing = false; document.body.style.cursor = ''; });
    }

    // DOSYA SEKMELERİ
    function createFileTab(filename) {
        const tab = document.createElement('div');
        tab.className = 'file-tab' + (filename === currentFile ? ' active' : '');
        tab.setAttribute('data-file', filename);
        tab.innerHTML = '<span class="file-name">' + filename + '</span><button class="file-close">&times;</button>';
        tab.querySelector('.file-close').addEventListener('click', function(e) {
            e.stopPropagation();
            const wsItem = workspaceItems.find(i => i.name === filename && i.type === 'file' && !i.parentId);
            if (workspaceItems.filter(i => i.type === 'file' && !i.parentId).length <= 1) return;
            if (wsItem) { deleteItem(wsItem.id); saveWorkspaceToStorage(); renderWorkspaceTree(); }
            delete files[filename]; tab.remove();
            if (currentFile === filename) { const remaining = Object.keys(files); if (remaining.length > 0) switchToFile(remaining[0]); }
        });
        tab.addEventListener('click', function() { switchToFile(filename); });
        return tab;
    }

    function switchToFile(filename) {
        const wsItem = workspaceItems.find(item => item.name === filename && item.type === 'file');
        if (wsItem) { currentFile = filename; files[filename] = wsItem.content || ''; setEditorValue(files[filename]); selectedItemId = wsItem.id; renderWorkspaceTree(); }
        else if (files[filename]) { currentFile = filename; setEditorValue(files[filename]); } else return;
        document.querySelectorAll('.file-tab').forEach(function(t) { t.classList.toggle('active', t.getAttribute('data-file') === filename); });
        setStatus(ideStatus, 'Düzenleniyor: ' + filename);
    }
    function addNewFile() { openNewFileModal(null); }
    function saveCurrentFile() {
        if (!currentFile) return;
        files[currentFile] = getEditorValue();
        const wsItem = workspaceItems.find(item => item.name === currentFile && item.type === 'file');
        if (wsItem) { wsItem.content = getEditorValue(); wsItem.updatedAt = Date.now(); }
    }

    // KÜTÜPHANE YÖNETİMİ
    const AVAILABLE_LIBRARIES = [
        { name: 'numpy', desc: 'Sayısal hesaplama', icon: '🔢' }, { name: 'pandas', desc: 'Veri analizi', icon: '📊' },
        { name: 'matplotlib', desc: 'Grafik çizimi', icon: '📈' }, { name: 'scipy', desc: 'Bilimsel hesaplama', icon: '🔬' },
        { name: 'scikit-learn', desc: 'Makine öğrenmesi', icon: '🤖' }, { name: 'requests', desc: 'HTTP istekleri', icon: '🌐' },
        { name: 'beautifulsoup4', desc: 'Web kazıma', icon: '🍲' }, { name: 'sympy', desc: 'Sembolik matematik', icon: '🧮' },
        { name: 'Pillow', desc: 'Görüntü işleme', icon: '🖼️' }
    ];
    const libModal = document.getElementById('libModal'), libGrid = document.getElementById('libGrid'), btnLibraries = document.getElementById('btnLibraries'), btnCancelLib = document.getElementById('btnCancelLib');

    function renderLibraryGrid() {
        if (!libGrid) return; libGrid.innerHTML = '';
        AVAILABLE_LIBRARIES.forEach(lib => {
            const item = document.createElement('div');
            item.className = 'lib-item' + (loadedLibraries.has(lib.name) ? ' loaded' : '');
            item.setAttribute('data-lib', lib.name);
            item.innerHTML = '<span class="lib-icon">' + lib.icon + '</span><div class="lib-info"><div class="lib-name">' + lib.name + '</div><div class="lib-desc">' + lib.desc + '</div></div><div class="lib-status">' + (loadedLibraries.has(lib.name) ? '✓ Yüklü' : 'Yükle') + '</div>';
            item.addEventListener('click', async () => { if (loadedLibraries.has(lib.name)) { appendOutput(lib.name + ' zaten yüklü.', 'info'); return; } await loadLibrary(lib.name); });
            libGrid.appendChild(item);
        });
    }
    async function loadLibrary(libName) {
        if (typeof window.pyodide === 'undefined' || !pyodideReady) { appendOutput('Pyodide henüz hazır değil. Önce bir kod çalıştırın.', 'error'); return; }
        try { appendOutput(libName + ' yükleniyor...', 'info'); await window.pyodide.loadPackage(libName); loadedLibraries.add(libName); appendOutput(libName + ' başarıyla yüklendi!', 'success'); renderLibraryGrid(); } catch (err) { appendOutput(libName + ' yüklenemedi: ' + err.message, 'error'); }
    }
    if (btnLibraries) btnLibraries.addEventListener('click', () => { renderLibraryGrid(); libModal.classList.add('active'); });
    if (btnCancelLib) btnCancelLib.addEventListener('click', () => libModal.classList.remove('active'));
    if (libModal) libModal.addEventListener('click', function(e) { if (e.target === libModal) libModal.classList.remove('active'); });

    // PYTHON ÇALIŞTIRMA
    async function runPython() {
        if (isRunning) { appendOutput('Kod zaten çalışıyor.', 'warning'); return; }
        saveCurrentFile(); setStatus(ideStatus, 'Çalışıyor...'); setStatus(flowStatus, 'Oluşturuluyor...'); appendOutput('--- Çalıştırılıyor: ' + currentFile + ' ---', 'info');
        const code = getEditorValue();
        if (typeof window.loadPyodide === 'function') {
            try {
                if (!pyodideReady) { appendOutput('Pyodide yükleniyor...', 'info'); window.pyodide = await loadPyodide(); await window.pyodide.loadPackage('micropip'); pyodideReady = true; appendOutput('Pyodide hazır!', 'success'); }
                isRunning = true;
                window.pyodide.runPython('import sys\nfrom io import StringIO\nsys.stdout = StringIO()\nsys.stderr = StringIO()');
                window.pyodide.runPython(code);
                const output = window.pyodide.runPython('sys.stdout.getvalue()'), error = window.pyodide.runPython('sys.stderr.getvalue()');
                if (output) appendOutput(output, 'info'); if (error) appendOutput(error, 'error');
                appendOutput('Kod başarıyla çalıştırıldı.', 'success'); setStatus(ideStatus, 'Başarılı'); setStatus(flowStatus, 'Hazır'); syncFlowchart();
            } catch (err) { appendOutput('Hata: ' + err.message, 'error'); setStatus(ideStatus, 'Hata'); setStatus(flowStatus, 'Hata'); } finally { isRunning = false; }
        } else { appendOutput('Pyodide bulunamadı.', 'error'); setStatus(ideStatus, 'Hata'); setStatus(flowStatus, 'Hata'); }
    }
    function stopPython() {
        if (typeof window.pyodide !== 'undefined' && pyodideReady) { try { window.pyodide.runPython('import sys\nsys.stdout = sys.__stdout__\nsys.stderr = sys.__stderr__'); appendOutput('Kod durduruldu.', 'warning'); setStatus(ideStatus, 'Durduruldu'); } catch (e) { appendOutput('Durdurma hatası: ' + e.message, 'error'); } }
        isRunning = false;
    }
    if (btnStop) btnStop.addEventListener('click', stopPython);

    // FLOWCHART
    function syncFlowchart() {
        appendOutput('Senkronizasyon: Kod -> FlowingTR diyagramı', 'info'); setStatus(flowStatus, 'Senkronize ediliyor...');
        const code = getEditorValue();
        try {
            if (typeof window.pyodide !== 'undefined' && pyodideReady) {
                window.pyodide.FS.writeFile('/tmp/flowpy_code.py', code);
                const result = window.pyodide.runPython('import ast, json\nwith open("/tmp/flowpy_code.py") as f:\n    source = f.read()\ntry:\n    tree = ast.parse(source)\n    nodes_list = []\n    connections_list = []\n    for node in ast.walk(tree):\n        node_type = type(node).__name__\n        node_data = {"type": node_type, "line": getattr(node, "lineno", 0)}\n        if isinstance(node, ast.FunctionDef):\n            node_data["label"] = node.name\n            nodes_list.append(node_data)\n        elif isinstance(node, ast.Assign):\n            for target in node.targets:\n                if isinstance(target, ast.Name):\n                    node_data["label"] = target.id\n                    nodes_list.append(node_data)\n        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):\n            if isinstance(node.value.func, ast.Name):\n                node_data["label"] = node.value.func.id\n                nodes_list.append(node_data)\n        elif isinstance(node, ast.If):\n            node_data["label"] = "if"\n            nodes_list.append(node_data)\n        elif isinstance(node, ast.For):\n            node_data["label"] = "for"\n            nodes_list.append(node_data)\n        elif isinstance(node, ast.While):\n            node_data["label"] = "while"\n            nodes_list.append(node_data)\n        elif isinstance(node, ast.Return):\n            node_data["label"] = "return"\n            nodes_list.append(node_data)\n    for i in range(len(nodes_list) - 1):\n        connections_list.append({"from": i, "to": i + 1})\n    print(json.dumps({"nodes": nodes_list, "connections": connections_list}))\nexcept SyntaxError as e:\n    print(json.dumps({"error": str(e)}))');
                const parsed = JSON.parse(result.trim());
                if (parsed.error) { appendOutput('Senkronizasyon hatası: ' + parsed.error, 'error'); setStatus(flowStatus, 'Hata'); return; }
                renderFlowchart(parsed.nodes, parsed.connections); renderFlowingTR(parsed.nodes, parsed.connections);
            } else {
                const fallbackNodes = [{type: 'FunctionDef', label: 'merhaba', line: 1}, {type: 'Assign', label: 'x', line: 2}, {type: 'Expr', label: 'print()', line: 4}];
                renderFlowchart(fallbackNodes, [{from: 0, to: 1}, {from: 1, to: 2}]); renderFlowingTR(fallbackNodes, [{from: 0, to: 1}, {from: 1, to: 2}]);
            }
            appendOutput('Diyagram başarıyla güncellendi.', 'success'); setStatus(flowStatus, 'Güncel');
        } catch (err) { appendOutput('Senkronizasyon hatası: ' + err.message, 'error'); setStatus(flowStatus, 'Hata'); }
    }

    function renderFlowchart(nodes, connections) {
        flowCanvas.innerHTML = '';
        const container = document.createElement('div'); container.style.position = 'relative'; container.style.width = '100%'; container.style.height = '100%';
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%'); svg.style.position = 'absolute'; svg.style.top = '0'; svg.style.left = '0'; svg.style.pointerEvents = 'none';
        const nodeWidth = 140, nodeHeight = 50, startX = 40, startY = 40, gapX = 180, gapY = 80;
        const nodeElements = [];
        nodes.forEach(function(node, index) {
            const col = index % 3, row = Math.floor(index / 3), x = startX + col * gapX, y = startY + row * gapY;
            const el = document.createElement('div');
            el.className = 'flow-node'; el.setAttribute('data-index', index); el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.width = nodeWidth + 'px'; el.style.height = nodeHeight + 'px';
            el.innerHTML = '<div class="flow-node-header">' + escapeHtml(node.type) + '</div><div class="flow-node-label">' + escapeHtml(node.label || '') + '</div><div class="flow-node-port flow-node-port-in"></div><div class="flow-node-port flow-node-port-out"></div>';
            makeDraggable(el); container.appendChild(el); nodeElements.push({el: el, x: x, y: y, node: node});
        });
        function drawConnections() {
            svg.innerHTML = '';
            connections.forEach(function(conn) {
                if (conn.from >= nodeElements.length || conn.to >= nodeElements.length) return;
                const fromEl = nodeElements[conn.from].el, toEl = nodeElements[conn.to].el;
                const fromRect = {x: fromEl.offsetLeft + nodeWidth, y: fromEl.offsetTop + nodeHeight / 2}, toRect = {x: toEl.offsetLeft, y: toEl.offsetTop + nodeHeight / 2}, midX = (fromRect.x + toRect.x) / 2;
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', 'M ' + fromRect.x + ' ' + fromRect.y + ' C ' + midX + ' ' + fromRect.y + ', ' + midX + ' ' + toRect.y + ', ' + toRect.x + ' ' + toRect.y);
                path.setAttribute('stroke', '#f59e0b'); path.setAttribute('stroke-width', '2'); path.setAttribute('fill', 'none'); path.setAttribute('stroke-opacity', '0.6'); svg.appendChild(path);
                const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                arrow.setAttribute('points', toRect.x + ',' + (toRect.y - 4) + ' ' + (toRect.x + 6) + ',' + toRect.y + ' ' + toRect.x + ',' + (toRect.y + 4));
                arrow.setAttribute('fill', '#f59e0b'); arrow.setAttribute('stroke-opacity', '0.6'); svg.appendChild(arrow);
            });
        }
        drawConnections(); container.appendChild(svg); flowCanvas.appendChild(container);
        container._nodeElements = nodeElements; container._connections = connections; container._drawConnections = drawConnections;
        window._currentFlowContainer = container;
        if (!window._flowResizeHandler) { window._flowResizeHandler = function() { if (window._currentFlowContainer && flowCanvas.contains(window._currentFlowContainer)) window._currentFlowContainer._drawConnections(); }; window.addEventListener('resize', window._flowResizeHandler); }
    }

    // FLOWINGTR
    const flowingtrDiagram = document.getElementById('flowingtrDiagram'), flowingtrStatus = document.getElementById('flowingtrStatus');
    const btnExportMermaid = document.getElementById('btnExportMermaid'), btnExportSvg = document.getElementById('btnExportSvg'), btnExportPng = document.getElementById('btnExportPng');

    function renderFlowingTR(nodes, connections) {
        if (!flowingtrDiagram) return; flowingtrDiagram.innerHTML = '';
        const container = document.createElement('div'); container.style.position = 'relative'; container.style.width = '100%'; container.style.height = '100%';
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%'); svg.setAttribute('height', '100%'); svg.style.position = 'absolute'; svg.style.top = '0'; svg.style.left = '0'; svg.style.pointerEvents = 'none';
        const nodeWidth = 160, nodeHeight = 60, startX = 60, startY = 60, gapX = 220, gapY = 100;
        const nodeElements = [];
        nodes.forEach(function(node, index) {
            const col = index % 4, row = Math.floor(index / 4), x = startX + col * gapX, y = startY + row * gapY;
            const el = document.createElement('div');
            el.className = 'flow-node flowingtr-node'; el.setAttribute('data-index', index); el.style.left = x + 'px'; el.style.top = y + 'px'; el.style.width = nodeWidth + 'px'; el.style.height = nodeHeight + 'px';
            el.innerHTML = '<div class="flow-node-header">' + escapeHtml(node.type) + '</div><div class="flow-node-label">' + escapeHtml(node.label || '') + '</div><div class="flow-node-port flow-node-port-in"></div><div class="flow-node-port flow-node-port-out"></div>';
            makeDraggable(el); container.appendChild(el); nodeElements.push({el: el, x: x, y: y, node: node});
        });
        function drawConnections() {
            svg.innerHTML = '';
            connections.forEach(function(conn) {
                if (conn.from >= nodeElements.length || conn.to >= nodeElements.length) return;
                const fromEl = nodeElements[conn.from].el, toEl = nodeElements[conn.to].el;
                const fromRect = {x: fromEl.offsetLeft + nodeWidth, y: fromEl.offsetTop + nodeHeight / 2}, toRect = {x: toEl.offsetLeft, y: toEl.offsetTop + nodeHeight / 2}, midX = (fromRect.x + toRect.x) / 2;
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', 'M ' + fromRect.x + ' ' + fromRect.y + ' C ' + midX + ' ' + fromRect.y + ', ' + midX + ' ' + toRect.y + ', ' + toRect.x + ' ' + toRect.y);
                path.setAttribute('stroke', '#f59e0b'); path.setAttribute('stroke-width', '2.5'); path.setAttribute('fill', 'none'); path.setAttribute('stroke-opacity', '0.7'); svg.appendChild(path);
                const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                arrow.setAttribute('points', toRect.x + ',' + (toRect.y - 5) + ' ' + (toRect.x + 8) + ',' + toRect.y + ' ' + toRect.x + ',' + (toRect.y + 5));
                arrow.setAttribute('fill', '#f59e0b'); arrow.setAttribute('stroke-opacity', '0.7'); svg.appendChild(arrow);
            });
        }
        drawConnections(); container.appendChild(svg); flowingtrDiagram.appendChild(container);
        container._nodeElements = nodeElements; container._connections = connections; container._drawConnections = drawConnections;
        window._currentFlowingTRContainer = container;
        if (!window._flowingtrResizeHandler) { window._flowingtrResizeHandler = function() { if (window._currentFlowingTRContainer && flowingtrDiagram.contains(window._currentFlowingTRContainer)) window._currentFlowingTRContainer._drawConnections(); }; window.addEventListener('resize', window._flowingtrResizeHandler); }
        if (flowingtrStatus) flowingtrStatus.textContent = 'Güncel';
    }

    function generateMermaidCode() {
        const container = window._currentFlowingTRContainer || window._currentFlowContainer;
        if (!container || !container._nodeElements) return '';
        let mermaid = 'graph TD\n';
        container._nodeElements.forEach(function(item, index) { mermaid += '    node' + index + '["' + (item.node.label || item.node.type) + '"]\n'; });
        container._connections.forEach(function(conn) { mermaid += '    node' + conn.from + ' --> node' + conn.to + '\n'; });
        return mermaid;
    }

    if (btnExportMermaid) {
        btnExportMermaid.addEventListener('click', () => {
            const mermaid = generateMermaidCode();
            if (!mermaid) { appendOutput('Önce bir diyagram oluşturun.', 'warning'); return; }
            navigator.clipboard.writeText(mermaid).then(() => appendOutput('Mermaid kodu panoya kopyalandı!', 'success')).catch(() => appendOutput('Mermaid kodu kopyalanamadı.', 'error'));
        });
    }
    if (btnExportSvg) {
        btnExportSvg.addEventListener('click', () => {
            const container = window._currentFlowingTRContainer || window._currentFlowContainer;
            if (!container) return; const svg = container.querySelector('svg'); if (!svg) return;
            const serializer = new XMLSerializer(), source = serializer.serializeToString(svg), blob = new Blob([source], {type: 'image/svg+xml'}), url = URL.createObjectURL(blob), a = document.createElement('a');
            a.href = url; a.download = 'flowpy_diagram.svg'; a.click(); URL.revokeObjectURL(url); appendOutput('SVG indirildi.', 'success');
        });
    }
    if (btnExportPng) {
        btnExportPng.addEventListener('click', () => {
            const container = window._currentFlowingTRContainer || window._currentFlowContainer;
            if (!container) return; const svg = container.querySelector('svg'); if (!svg) return;
            const serializer = new XMLSerializer(), source = serializer.serializeToString(svg), blob = new Blob([source], {type: 'image/svg+xml'}), url = URL.createObjectURL(blob);
            const img = new Image();
            img.onload = function() { const c = document.createElement('canvas'); c.width = img.width * 2; c.height = img.height * 2; const cctx = c.getContext('2d'); cctx.drawImage(img, 0, 0, c.width, c.height); const a = document.createElement('a'); a.href = c.toDataURL('image/png'); a.download = 'flowpy_diagram.png'; a.click(); URL.revokeObjectURL(url); appendOutput('PNG indirildi.', 'success'); };
            img.src = url;
        });
    }

    function makeDraggable(el) {
        let isDragging = false, startX, startY, initialLeft, initialTop;
        el.addEventListener('mousedown', function(e) { if (e.target.classList.contains('flow-node-port')) return; isDragging = true; startX = e.clientX; startY = e.clientY; initialLeft = el.offsetLeft; initialTop = el.offsetTop; el.style.zIndex = '10'; el.style.cursor = 'grabbing'; });
        document.addEventListener('mousemove', function(e) { if (!isDragging) return; el.style.left = (initialLeft + e.clientX - startX) + 'px'; el.style.top = (initialTop + e.clientY - startY) + 'px'; const container = el.parentElement; if (container && container._drawConnections) container._drawConnections(); });
        document.addEventListener('mouseup', function() { if (isDragging) { isDragging = false; el.style.zIndex = '1'; el.style.cursor = 'grab'; } });
    }
    function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

    // HATA BİLDİR
    function openReportModal() { reportModal.classList.add('active'); reportText.value = ''; reportText.focus(); }
    function closeReportModal() { reportModal.classList.remove('active'); }
    function sendReport() {
        const text = reportText.value.trim(); if (!text) { alert('Lütfen hata açıklaması yazın.'); return; }
        const payload = new URLSearchParams(); payload.append('hata_aciklama', text); payload.append('tarayici', navigator.userAgent); payload.append('tarih', new Date().toLocaleString('tr-TR')); payload.append('dosya', currentFile); payload.append('konum', window.location.href);
        fetch(formspreeEndpoint, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json' }, body: payload.toString() })
            .then(function(response) { if (response.ok) { appendOutput('Hata bildirimi gönderildi. Teşekkürler!', 'success'); closeReportModal(); } else throw new Error('Gönderim başarısız'); })
            .catch(function(err) { appendOutput('Gönderim hatası: ' + err.message, 'error'); appendOutput('Doğrudan mail atmayı deneyin: berkayozdemirtrtr@gmail.com', 'info'); });
    }

    // EVENT LISTENER'LAR
    if (btnRun) btnRun.addEventListener('click', runPython);
    if (btnSync) btnSync.addEventListener('click', syncFlowchart);
    if (btnClearOutput) btnClearOutput.addEventListener('click', clearOutput);
    if (btnReport) btnReport.addEventListener('click', openReportModal);
    if (btnCancelReport) btnCancelReport.addEventListener('click', closeReportModal);
    if (btnSendReport) btnSendReport.addEventListener('click', sendReport);
    if (btnNewFile) btnNewFile.addEventListener('click', addNewFile);

    const btnCreateNewFile = document.getElementById('btnCreateNewFile'), btnCancelNewFile = document.getElementById('btnCancelNewFile'), newFileModal = document.getElementById('newFileModal');
    if (btnCreateNewFile) btnCreateNewFile.addEventListener('click', createNewFile);
    if (btnCancelNewFile) btnCancelNewFile.addEventListener('click', closeNewFileModal);
    if (newFileModal) newFileModal.addEventListener('click', function(e) { if (e.target === newFileModal) closeNewFileModal(); });

    const btnCreateNewFolder = document.getElementById('btnCreateNewFolder'), btnCancelNewFolder = document.getElementById('btnCancelNewFolder'), newFolderModal = document.getElementById('newFolderModal');
    if (btnCreateNewFolder) btnCreateNewFolder.addEventListener('click', createNewFolder);
    if (btnCancelNewFolder) btnCancelNewFolder.addEventListener('click', closeNewFolderModal);
    if (newFolderModal) newFolderModal.addEventListener('click', function(e) { if (e.target === newFolderModal) closeNewFolderModal(); });

    if (reportModal) reportModal.addEventListener('click', function(e) { if (e.target === reportModal) closeReportModal(); });

    // BAŞLATMA
    async function initWorkspace() {
        if (!outputBody || !fileTabsContainer) { console.warn('Derleyici DOM elemanları bulunamadı.'); return; }
        await loadFilesFromStorage(); await loadWorkspaceFromStorage();
        initCodeMirror();
        if (currentFile && files[currentFile]) setEditorValue(files[currentFile]);
        appendOutput('FlowPy derleyici hazır. Kodunuzu yazın ve Çalıştır\'a basın.', 'info');
    }
    initWorkspace();

    const autoSaveInterval = setInterval(saveFilesToStorage, 30000);
    window.addEventListener('beforeunload', () => { clearInterval(autoSaveInterval); saveFilesToStorage(); saveWorkspaceToStorage(); });

    function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
    function randomRange(min, max) { return Math.random() * (max - min) + min; }

})();