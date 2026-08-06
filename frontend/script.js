 /*
    FlowPy - Ana Script Dosyası
    ===========================
    Bu dosya üç ana işi yapar:
    
    1. Arka Plan Ağı: Canvas üzerinde turuncu örümcek ağı animasyonu
    2. Arama: Üst çubuktaki arama kutusu ile bölüm bulma
    3. Navigasyon: Bölümler arası geçiş ve aktif bölüm takibi
    
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

    console.log('DUR.');

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
        // Cihaz Tipi
        isMobile: window.innerWidth < 768,
        
        // Düğüm Ayarları
        nodeCount: 80,
        nodeMinRadius: 0.5,
        nodeMaxRadius: 2,
        nodeSpeed: 0.1, // Çok yavaş hareket - göz yormasın
        nodeMaxSpeed: 0.25, // Çok yavaş hız limiti
        
        // Bağlantı Ayarları
        connectionDistance: 180,
        connectionBaseOpacity: 0.4,
        connectionLineWidth: 1,
        
        // Etkileşim Ayarları
        touchInfluenceRadius: 200, // Mobildeki etki alanı
        mouseInfluenceRadius: 300, // Desktop'taki etki alanı
        gravityEffect: 0.3, // Çökme efekti şiddeti
        depthEffect: 40, // Derinlik efekti (içe doğru çökme)
        
        // Logo Ayarları
        logoMargin: 120,
        logoPushForce: 0.2,
        
        // Ekran Ayarları
        safeMargin: 20, // Küçük margin - daha fazla hareket
        returnForce: 0.0002 // Çok yavaş dönüş
    };

    // ============================================
    // ARAMA VERİLERİ - Bölümler (Türkçe + İngilizce)
    // ============================================
    const SECTIONS = [
        { id: 0, name: 'FlowPy', nameEn: 'FlowPy', url: '#flowpy' },
        { id: 1, name: 'Ana Sayfa', nameEn: 'Home', url: '#home' },
        { id: 2, name: 'Derleyici', nameEn: 'Executer', url: '#executer' },
        { id: 3, name: 'Hakkımızda', nameEn: 'About', url: '#about' },
        { id: 4, name: 'SSS', nameEn: 'FAQ', url: '#faq' }
    ];

    // ============================================
    // MOUSE/TOUCH TRACKING
    // ============================================
    let inputX = window.innerWidth / 2;
    let inputY = window.innerHeight / 2;
    let targetInputX = inputX;
    let targetInputY = inputY;

    // ============================================
    // DÜĞÜM SINIFI
    // ============================================
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
            this.visible = true; // Görünürlük durumu
        }

        update() {
            // Hareket
            this.x += this.vx;
            this.y += this.vy;

            // Sınır kontrolü - ekran dışına çıkabilir
            this.checkBoundaries();

            // Logo koruması
            this.avoidLogo();

            // Hız sınırlama
            this.limitSpeed();

            // Etkileşim (mobil veya desktop)
            this.applyInputForce();

            // Orijinal konuma dönüş
            this.returnToOrigin();
            
            // Görünürlük kontrolü
            this.updateVisibility();
        }

        checkBoundaries() {
            const margin = SETTINGS.safeMargin;
            
            // Sadece yumuşak yönlendirme, sınır yok
            if (this.x < -50) {
                this.vx = Math.abs(this.vx) * 0.5;
            }
            if (this.x > canvas.width + 50) {
                this.vx = -Math.abs(this.vx) * 0.5;
            }
            if (this.y < -50) {
                this.vy = Math.abs(this.vy) * 0.5;
            }
            if (this.y > canvas.height + 50) {
                this.vy = -Math.abs(this.vy) * 0.5;
            }
        }

        updateVisibility() {
            // Ekran dışına çıkan düğümleri görünmez yap
            const margin = 100;
            this.visible = this.x > -margin && 
                          this.x < canvas.width + margin &&
                          this.y > -margin && 
                          this.y < canvas.height + margin;
        }

        avoidLogo() {
            // Üst çubuktan sonraki alanı kontrol et
            const topBarHeight = 60;
            if (this.y < topBarHeight + SETTINGS.logoMargin) {
                const logo = document.querySelector('.header-logo-img');
                if (!logo) return;
                
                const rect = logo.getBoundingClientRect();
                const centerX = rect.left + rect.width / 2;
                const centerY = rect.top + rect.height / 2;
                
                const dx = this.x - centerX;
                const dy = this.y - centerY;
                const dist = Math.sqrt(dx * dx + dy * dy);
                
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
            const dx = inputX - this.x;
            const dy = inputY - this.y;
            const dist = Math.sqrt(dx * dx + dy * dy);
            
            const influenceRadius = SETTINGS.isMobile ? SETTINGS.touchInfluenceRadius : SETTINGS.mouseInfluenceRadius;
            
            if (dist < influenceRadius && dist > 0) {
                const force = (influenceRadius - dist) / influenceRadius;
                
                if (SETTINGS.isMobile) {
                    // Mobil: Dokunma noktasına doğru çek
                    this.vx += (dx / dist) * force * 0.02;
                    this.vy += (dy / dist) * force * 0.02;
                } else {
                    // Desktop: İçe doğru çök (3D derinlik efekti)
                    const gravity = force * SETTINGS.gravityEffect * this.mass;
                    this.vy += gravity;
                    
                    // Hafifçe mouse'a doğru çek
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
            if (!this.visible) return; // Görünmezse çizme
            
            ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
            ctx.beginPath();
            ctx.arc(this.x, this.y, this.radius, 0, Math.PI * 2);
            ctx.fill();
        }
    }

    // ============================================
    // BAĞLANTI ÇİZGİLERİ
    // ============================================
    function drawConnections() {
        for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].visible) continue; // Görünmezse atla
            
            for (let j = i + 1; j < nodes.length; j++) {
                if (!nodes[j].visible) continue; // Görünmezse atla
                
                const dx = nodes[i].x - nodes[j].x;
                const dy = nodes[i].y - nodes[j].y;
                const dist = Math.sqrt(dx * dx + dy * dy);

                if (dist < SETTINGS.connectionDistance) {
                    const midX = (nodes[i].x + nodes[j].x) / 2;
                    const midY = (nodes[i].y + nodes[j].y) / 2;
                    
                    let opacity = (1 - (dist / SETTINGS.connectionDistance)) * SETTINGS.connectionBaseOpacity;
                    let sagging = 0;

                    // Desktop'ta derinlik efekti (içe doğru çökme)
                    if (!SETTINGS.isMobile) {
                        const inputDist = Math.sqrt(
                            Math.pow(inputX - midX, 2) + Math.pow(inputY - midY, 2)
                        );

                        if (inputDist < SETTINGS.mouseInfluenceRadius) {
                            const sagForce = (SETTINGS.mouseInfluenceRadius - inputDist) / SETTINGS.mouseInfluenceRadius;
                            opacity += sagForce * 0.4;
                            sagging = sagForce * SETTINGS.depthEffect;
                        }
                    }

                    opacity = clamp(opacity, 0, 1);

                    ctx.strokeStyle = `rgba(245, 158, 11, ${opacity})`;
                    ctx.lineWidth = SETTINGS.connectionLineWidth;
                    ctx.beginPath();
                    ctx.moveTo(nodes[i].x, nodes[i].y);
                    
                    // Eğrili çizgi (derinlik efekti)
                    const controlY = midY + sagging;
                    ctx.quadraticCurveTo(midX, controlY, nodes[j].x, nodes[j].y);
                    ctx.stroke();
                }
            }
        }
    }

    // ============================================
    // MOUSE/TOUCH BAĞLANTILARI
    // ============================================
    function drawInputConnections() {
        const influenceRadius = SETTINGS.isMobile ? SETTINGS.touchInfluenceRadius : SETTINGS.mouseInfluenceRadius;
        
        for (let i = 0; i < nodes.length; i++) {
            if (!nodes[i].visible) continue; // Görünmezse atla
            
            const dx = inputX - nodes[i].x;
            const dy = inputY - nodes[i].y;
            const dist = Math.sqrt(dx * dx + dy * dy);

            if (dist < influenceRadius) {
                const opacity = (1 - (dist / influenceRadius)) * 0.7;
                ctx.strokeStyle = `rgba(245, 158, 11, ${clamp(opacity, 0, 1)})`;
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.moveTo(inputX, inputY);
                ctx.lineTo(nodes[i].x, nodes[i].y);
                ctx.stroke();
            }
        }

        // İmleç/dokunma noktası
        ctx.fillStyle = 'rgba(245, 158, 11, 0.9)';
        ctx.beginPath();
        ctx.arc(inputX, inputY, 4, 0, Math.PI * 2);
        ctx.fill();
    }

    // ============================================
    // ARAMA İŞLEVSELLİĞİ - Türkçe + İngilizce
    // ============================================
    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const searchContainer = document.getElementById('searchContainer');

    // Arama yap
    function performSearch(query) {
        if (!query || query.trim() === '') {
            searchResults.classList.remove('active');
            return;
        }

        const lowerQuery = query.toLowerCase();
        
        // Hem Türkçe hem İngilizce arama
        const matches = SECTIONS.filter(section => 
            section.name.toLowerCase().includes(lowerQuery) ||
            section.nameEn.toLowerCase().includes(lowerQuery)
        ).slice(0, 2); // Sadece ilk 2 sonuç

        // Sonuçları göster
        if (matches.length > 0) {
            searchResults.textContent = '';
            matches.forEach(section => {
                const item = document.createElement('div');
                item.className = 'search-result-item';
                item.setAttribute('data-url', section.url);
                item.textContent = section.name;
                item.addEventListener('click', function() {
                    navigateToSection(section.url);
                });
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

    // Bölüme git
    async function navigateToSection(url) {
        // Arama çubuğunu gizle
        searchInput.value = '';
        searchResults.classList.remove('active');
        
        // Dosyaları kaydet
        saveCurrentFile();
        await saveFilesToStorage();
        
        // Bölüme git (hash değiştir)
        window.location.hash = url;
        setActiveNav(url);
    }

    // Aktif bölümü işaretle (alt çizgi göster)
    function setActiveNav(url) {
        document.querySelectorAll('.nav-link').forEach(link => {
            link.classList.toggle('active', link.getAttribute('href') === url);
        });
    }

    // Hash değişince aktif bölümü güncelle
    window.addEventListener('hashchange', () => {
        const currentHash = window.location.hash || '#flowpy';
        setActiveNav(currentHash);
        document.body.classList.toggle('on-flowpy', currentHash === '#flowpy');
    });

    // Arama inputu event listener
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            performSearch(e.target.value);
        });

        // Enter tuşu
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                const firstResult = document.querySelector('.search-result-item');
                if (firstResult) {
                    firstResult.click();
                }
            }
        });

        // Dışarı tıklayınca kapat
        document.addEventListener('click', (e) => {
            if (!searchContainer.contains(e.target)) {
                searchResults.classList.remove('active');
            }
        });
    }

    // ============================================
    // ANİMASYON DÖNGÜSÜ
    // ============================================
    const nodes = [];
    
    function animate() {
        // Mouse/touch pozisyonunu yumuşakça güncelle
        inputX += (targetInputX - inputX) * 0.1;
        inputY += (targetInputY - inputY) * 0.1;
        
        // Arka planı temizle (dark mode kontrolü)
        const bgColor = document.body.classList.contains('dark-mode') ? '#1a1a1a' : '#ffffff';
        ctx.fillStyle = bgColor;
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        // Bağlantıları çiz
        drawConnections();
        drawInputConnections();

        // Düğümleri güncelle ve çiz
        nodes.forEach(node => {
            node.update();
            node.draw();
        });

        requestAnimationFrame(animate);
    }

    // ============================================
    // BAŞLATMA
    // ============================================
    function init() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        nodes.length = 0;
        
        // Grid tabanlı dağılım
        const cols = 8;
        const rows = Math.ceil(SETTINGS.nodeCount / cols);
        const spacingX = (canvas.width - SETTINGS.safeMargin * 2) / cols;
        const spacingY = (canvas.height - SETTINGS.safeMargin * 2) / rows;
        
        for (let i = 0; i < SETTINGS.nodeCount; i++) {
            const col = i % cols;
            const row = Math.floor(i / cols);
            const x = SETTINGS.safeMargin + spacingX * (col + 0.5) + (Math.random() - 0.5) * spacingX * 0.5;
            const y = SETTINGS.safeMargin + spacingY * (row + 0.5) + (Math.random() - 0.5) * spacingY * 0.5;
            
            // Üst çubuk ve logo alanını kontrol et
            const topBarHeight = 60;
            const logo = document.querySelector('.header-logo-img');
            let inLogoArea = false;
            
            if (logo && y < topBarHeight + SETTINGS.logoMargin) {
                const rect = logo.getBoundingClientRect();
                const logoCenterX = rect.left + rect.width / 2;
                const logoCenterY = rect.top + rect.height / 2;
                
                if (Math.abs(x - logoCenterX) < SETTINGS.logoMargin &&
                    Math.abs(y - logoCenterY) < SETTINGS.logoMargin) {
                    inLogoArea = true;
                }
            }
            
            if (!inLogoArea) {
                nodes.push(new Node(x, y));
            }
        }
        
        // Yeterli düğüm yoksa ekle
        while (nodes.length < SETTINGS.nodeCount) {
            const x = SETTINGS.safeMargin + Math.random() * (canvas.width - SETTINGS.safeMargin * 2);
            const y = SETTINGS.safeMargin + Math.random() * (canvas.height - SETTINGS.safeMargin * 2);
            nodes.push(new Node(x, y));
        }
    }

    // ============================================
    // EVENT LISTENERS
    // ============================================
    
    // Mouse hareketi (desktop)
    if (!SETTINGS.isMobile) {
        document.addEventListener('mousemove', (e) => {
            targetInputX = clamp(e.clientX, 0, canvas.width);
            targetInputY = clamp(e.clientY, 0, canvas.height);
        });
    }
    
    // Dokunmatik hareket (mobil)
    if (SETTINGS.isMobile) {
        document.addEventListener('touchmove', (e) => {
            if (e.touches.length > 0) {
                targetInputX = clamp(e.touches[0].clientX, 0, canvas.width);
                targetInputY = clamp(e.touches[0].clientY, 0, canvas.height);
            }
        });

        document.addEventListener('touchend', () => {
            // Dokunma bittiğinde ortaya dön
            targetInputX = canvas.width / 2;
            targetInputY = canvas.height / 2;
        });
    }

    let resizeTimeout;
    window.addEventListener('resize', () => {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(init, 200);
    });

    // ============================================
    // TEMA DEĞİŞTİRME - Dark/Light mode
    // ============================================
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');

    // Tema değiştir
    function toggleTheme() {
        document.body.classList.toggle('dark-mode');
        
        // Icon değiştir
        if (document.body.classList.contains('dark-mode')) {
            themeIcon.src = 'Assets/moon.svg';
            localStorage.setItem('theme', 'dark');
        } else {
            themeIcon.src = 'Assets/sun.svg';
            localStorage.setItem('theme', 'light');
        }
    }

    // Tema butonu event listener
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Sayfa yüklendiğinde kaydedilmiş temayı uygula
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
        document.body.classList.add('dark-mode');
        if (themeIcon) themeIcon.src = 'Assets/moon.svg';
    }

    // ============================================
    // FOOTER DROPDOWN - İletişim Bilgileri
    // ============================================
    const devLink = document.getElementById('devLink');
    const studioLink = document.getElementById('studioLink');
    const devDropdown = document.getElementById('devDropdown');
    const studioDropdown = document.getElementById('studioDropdown');

    // Dropdown aç/kapat
    function toggleDropdown(dropdown) {
        // Diğer dropdown'ı kapat
        if (dropdown === devDropdown && studioDropdown) {
            studioDropdown.classList.remove('active');
        }
        if (dropdown === studioDropdown && devDropdown) {
            devDropdown.classList.remove('active');
        }
        dropdown.classList.toggle('active');
    }

    if (devLink && devDropdown) {
        devLink.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(devDropdown);
        });
    }

    if (studioLink && studioDropdown) {
        studioLink.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleDropdown(studioDropdown);
        });
    }

    // Dışarı tıklayınca kapat
    document.addEventListener('click', () => {
        if (devDropdown) devDropdown.classList.remove('active');
        if (studioDropdown) studioDropdown.classList.remove('active');
    });

    // ============================================
    // SCROLL İLE AKTİF BÖLÜM TAKİBİ
    // ============================================
    function updateActiveSectionOnScroll() {
        const sections = document.querySelectorAll('.section');
        let currentSection = '#flowpy';
        let maxVisibleArea = 0;
        
        sections.forEach(section => {
            const rect = section.getBoundingClientRect();
            const visibleHeight = Math.min(rect.bottom, window.innerHeight) - Math.max(rect.top, 0);
            
            if (visibleHeight > maxVisibleArea) {
                maxVisibleArea = visibleHeight;
                currentSection = '#' + section.id;
            }
        });
        
        setActiveNav(currentSection);
        
        // FlowPy bölümünde logo görünür, diğerlerinde soluk
        document.body.classList.toggle('on-flowpy', currentSection === '#flowpy');
    }

    // ============================================
    // FAQ ACCORDION - SSS Bölümü
    // ============================================
    // Soruları buradan kolayca değiştirin
    const FAQ_ITEMS = [
        {
            question: 'Karanlık ve aydınlık mod ne işe yarar nasıl açılır?',
            answer: 'Karanlık mod, gece kullanımında göz yorgunluğunu azaltır ve daha az enerji tüketir. Üst çubuğun sağ tarafındaki güneş/ay simgesine tıklayarak açılır/kapatılır. Tercihiniz localStorage\'da saklanır.'
        },
        {
            question: 'Bu site ne işe yarar?',
            answer: 'FlowPy, Python kodlarını görsel akış diyagramlarına dönüştüren ve derleyen bir geliştirme aracıdır. Kod yazmayı ve akışları görselleştirmeyi birleştirir.'
        },
        {
            question: 'TurcoDevelopStudio nedir?',
            answer: 'TurcoDevelopStudio, Türkçe geliştirici topluluğu ve açık kaynak projeler geliştiren bir yazılım stüdyosudur. Berkay Özdemir (bercaius) ve BrahimTKM (İbrahim Talha Kömürcü) tarafından kurulmuştur.'
        },
        {
            question: 'Derleyiciyi yaparken hangi kütüphaneleri kullandınız?',
            answer: 'Python\'un built-in ast modülünü ve sys modülünü kullandık. Ayrıca özel dönüştürücüler geliştirdik.'
        },
        {
            question: 'Derleyicide bir hata olursa hangi eposta adresinden iletişime geçebilirim?',
            answer: 'berkayozdemirtrtr@gmail.com adresinden bizimle iletişime geçebilirsiniz.'
        },
        {
            question: 'Sitedeki Deneme modu tam sürümmü yoksa tam teşekküllü bir sürümde var mı?',
            answer: 'Evet, sitede deneme sürümü bulunmaktadır. Tam sürümde ek özellikler ve daha gelişmiş derleyici bulunmaktadır.'
        }
    ];

    // FAQ Accordion'ı oluştur
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
                if (!isActive) {
                    accordionItem.classList.add('active');
                    content.style.maxHeight = content.scrollHeight + 'px';
                }
            });
        });
    }

    // ============================================
    // MOBİL MENÜ
    // ============================================
    const mobileMenuBtn = document.getElementById('mobileMenuBtn');
    const headerRight = document.getElementById('headerRight');

    if (mobileMenuBtn && headerRight) {
        mobileMenuBtn.addEventListener('click', function() {
            mobileMenuBtn.classList.toggle('active');
            headerRight.classList.toggle('active');
        });

        document.querySelectorAll('.nav-link').forEach(link => {
            link.addEventListener('click', () => {
                mobileMenuBtn.classList.remove('active');
                headerRight.classList.remove('active');
            });
        });

        document.addEventListener('click', function(e) {
            if (!headerRight.contains(e.target) && !mobileMenuBtn.contains(e.target)) {
                mobileMenuBtn.classList.remove('active');
                headerRight.classList.remove('active');
            }
        });
    }

    // ============================================
    // BAŞLAT
    // ============================================
    init();
    animate();
    initFAQAccordion();
    
    // Sayfa yüklendiğinde en üste git (FlowPy bölümü)
    window.scrollTo(0, 0);
    
    // Başlangıçta aktif bölümü belirle
    const initialHash = window.location.hash || '#flowpy';
    setActiveNav(initialHash);
    document.body.classList.toggle('on-flowpy', initialHash === '#flowpy');
    
    // Nav-link tıklamalarında aktif bölümü güncelle
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            saveCurrentFile();
            saveFilesToStorage();
            const href = link.getAttribute('href');
            setActiveNav(href);
            document.body.classList.toggle('on-flowpy', href === '#flowpy');
        });
    });
    
    // Scroll olayında aktif bölümü güncelle
    let scrollTicking = false;
    window.addEventListener('scroll', () => {
        if (!scrollTicking) {
            requestAnimationFrame(() => {
                updateActiveSectionOnScroll();
                scrollTicking = false;
            });
            scrollTicking = true;
        }
    });

    // Başlangıçta aktif bölümü belirle
    updateActiveSectionOnScroll();

    // ============================================
    // DERLEYİCİ - Dosya Yönetimi ve Çalıştırma
    // ============================================
    const codeEditor = document.getElementById('codeEditor');
    const outputBody = document.getElementById('outputBody');
    const outputPanel = document.getElementById('outputPanel');
    const ideStatus = document.getElementById('ideStatus');
    const flowStatus = document.getElementById('flowStatus');
    const flowCanvas = document.getElementById('flowCanvas');
    const fileTabsContainer = document.getElementById('fileTabs');
    const btnRun = document.getElementById('btnRun');
    const btnSync = document.getElementById('btnSync');
    const btnClearOutput = document.getElementById('btnClearOutput');
    const btnReport = document.getElementById('btnReport');
    const reportModal = document.getElementById('reportModal');
    const btnCancelReport = document.getElementById('btnCancelReport');
    const btnSendReport = document.getElementById('btnSendReport');
    const reportText = document.getElementById('reportText');

    let currentFile = 'main.py';
    let files = { 'main.py': '# Python kodunuzu buraya yazın\ndef merhaba():\n    print("Merhaba FlowPy!")\n\nmerhaba()\n' };
    let pyodideReady = false;
    let formspreeEndpoint = 'https://formspree.io/f/mzepzgpa';

    async function loadFilesFromStorage() {
        try {
            if (typeof localforage !== 'undefined') {
                const stored = await localforage.getItem('flowpy_files');
                if (stored && typeof stored === 'object') {
                    files = stored;
                }
            }
        } catch (e) {
            console.warn('Dosyalar yüklenemedi:', e);
        }
        const tab = createFileTab(currentFile);
        fileTabsContainer.appendChild(tab);
        codeEditor.value = files[currentFile] || '';
    }

    async function saveFilesToStorage() {
        try {
            if (typeof localforage !== 'undefined') {
                await localforage.setItem('flowpy_files', files);
            }
        } catch (e) {
            console.warn('Dosyalar kaydedilemedi:', e);
        }
    }

    function appendOutput(text, type) {
        type = type || 'info';
        const span = document.createElement('span');
        span.className = 'output-text output-' + type;
        span.textContent = text;
        outputBody.appendChild(span);
        outputPanel.scrollTop = outputPanel.scrollHeight;
    }

    function clearOutput() {
        outputBody.innerHTML = '';
        appendOutput('Çıktı temizlendi.', 'info');
    }

    function setStatus(element, text) {
        if (element) element.textContent = text;
    }

    function createFileTab(filename) {
        const tab = document.createElement('div');
        tab.className = 'file-tab' + (filename === currentFile ? ' active' : '');
        tab.setAttribute('data-file', filename);
        tab.innerHTML = '<span class="file-name">' + filename + '</span><button class="file-close">&times;</button>';
        tab.querySelector('.file-close').addEventListener('click', function(e) {
            e.stopPropagation();
            if (Object.keys(files).length <= 1) return;
            delete files[filename];
            tab.remove();
            if (currentFile === filename) {
                const remaining = Object.keys(files);
                switchToFile(remaining[0]);
            }
        });
        tab.addEventListener('click', function() {
            switchToFile(filename);
        });
        return tab;
    }

    function switchToFile(filename) {
        if (!files[filename]) return;
        currentFile = filename;
        codeEditor.value = files[filename];
        document.querySelectorAll('.file-tab').forEach(function(t) {
            t.classList.toggle('active', t.getAttribute('data-file') === filename);
        });
        setStatus(ideStatus, 'Düzenleniyor: ' + filename);
    }

    function addNewFile() {
        const name = prompt('Dosya adı (örn: script.py):');
        if (!name) return;
        if (!name.endsWith('.py')) {
            alert('Lütfen .py uzantılı dosya adı girin.');
            return;
        }
        if (files[name]) {
            alert('Bu dosya zaten var.');
            return;
        }
        files[name] = '';
        const tab = createFileTab(name);
        fileTabsContainer.appendChild(tab);
        switchToFile(name);
    }

    function saveCurrentFile() {
        if (!currentFile) return;
        files[currentFile] = codeEditor.value;
    }

    async function runPython() {
        saveCurrentFile();
        setStatus(ideStatus, 'Çalışıyor...');
        setStatus(flowStatus, 'Oluşturuluyor...');
        appendOutput('--- Çalıştırılıyor: ' + currentFile + ' ---', 'info');
        
        const code = codeEditor.value;
        
        if (typeof window.loadPyodide === 'function') {
            try {
                if (!pyodideReady) {
                    appendOutput('Pyodide yükleniyor...', 'info');
                    window.pyodide = await loadPyodide();
                    await window.pyodide.loadPackage('micropip');
                    pyodideReady = true;
                }
                
                window.pyodide.runPython(`
import sys
from io import StringIO
sys.stdout = StringIO()
`);
                window.pyodide.runPython(code);
                const output = window.pyodide.runPython('sys.stdout.getvalue()');
                if (output) {
                    appendOutput(output, 'info');
                }
                appendOutput('Kod başarıyla çalıştırıldı.', 'success');
                setStatus(ideStatus, 'Başarılı');
                setStatus(flowStatus, 'Hazır');
            } catch (err) {
                appendOutput('Hata: ' + err.message, 'error');
                setStatus(ideStatus, 'Hata');
                setStatus(flowStatus, 'Hata');
            }
        } else {
            appendOutput('Pyodide bulunamadı. Lütfen sayfayı yenileyin.', 'error');
            setStatus(ideStatus, 'Hata');
            setStatus(flowStatus, 'Hata');
        }
    }

    function syncFlowchart() {
        appendOutput('Senkronizasyon: Kod -> FlowingTR diyagramı', 'info');
        setStatus(flowStatus, 'Senkronize ediliyor...');
        
        const code = codeEditor.value;
        const nodes = [];
        const connections = [];
        
        try {
            if (typeof window.pyodide !== 'undefined' && pyodideReady) {
                const escapedCode = code.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
                const astCode = [
                    'import ast, json, sys',
                    'code = """' + escapedCode + '"""',
                    'try:',
                    '    tree = ast.parse(code)',
                    '    nodes_list = []',
                    '    connections_list = []',
                    '    for node in ast.walk(tree):',
                    '        node_type = type(node).__name__',
                    '        node_data = {"type": node_type, "line": getattr(node, "lineno", 0)}',
                    '        if isinstance(node, ast.FunctionDef):',
                    '            node_data["label"] = node.name',
                    '            nodes_list.append(node_data)',
                    '        elif isinstance(node, ast.Assign):',
                    '            for target in node.targets:',
                    '                if isinstance(target, ast.Name):',
                    '                    node_data["label"] = target.id',
                    '                    nodes_list.append(node_data)',
                    '        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):',
                    '            if isinstance(node.value.func, ast.Name):',
                    '                node_data["label"] = node.value.func.id',
                    '                nodes_list.append(node_data)',
                    '    for i in range(len(nodes_list) - 1):',
                    '        connections_list.append({"from": i, "to": i + 1})',
                    '    print(json.dumps({"nodes": nodes_list, "connections": connections_list}))',
                    'except SyntaxError as e:',
                    '    print(json.dumps({"error": str(e)}))'
                ].join('\\n');
                
                const result = window.pyodide.runPython(astCode);
                const parsed = JSON.parse(result.trim());
                if (parsed.error) {
                    appendOutput('Senkronizasyon hatası: ' + parsed.error, 'error');
                    setStatus(flowStatus, 'Hata');
                    return;
                }
                renderFlowchart(parsed.nodes, parsed.connections);
            } else {
                renderFlowchart(
                    [
                        {type: 'FunctionDef', label: 'merhaba', line: 1},
                        {type: 'Assign', label: 'x', line: 2},
                        {type: 'Expr', label: 'print()', line: 4}
                    ],
                    [{from: 0, to: 1}, {from: 1, to: 2}]
                );
            }
            appendOutput('Diyagram başarıyla güncellendi.', 'success');
            setStatus(flowStatus, 'Güncel');
        } catch (err) {
            appendOutput('Senkronizasyon hatası: ' + err.message, 'error');
            setStatus(flowStatus, 'Hata');
        }
    }

    function renderFlowchart(nodes, connections) {
        const canvas = flowCanvas;
        canvas.innerHTML = '';
        
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.position = 'absolute';
        svg.style.top = '0';
        svg.style.left = '0';
        svg.style.pointerEvents = 'none';
        
        const container = document.createElement('div');
        container.style.position = 'relative';
        container.style.width = '100%';
        container.style.height = '100%';
        
        const nodeWidth = 140;
        const nodeHeight = 50;
        const startX = 40;
        const startY = 40;
        const gapX = 180;
        const gapY = 80;
        
        const nodeElements = [];
        
        nodes.forEach(function(node, index) {
            const col = index % 3;
            const row = Math.floor(index / 3);
            const x = startX + col * gapX;
            const y = startY + row * gapY;
            
            const el = document.createElement('div');
            el.className = 'flow-node';
            el.setAttribute('data-index', index);
            el.style.left = x + 'px';
            el.style.top = y + 'px';
            el.style.width = nodeWidth + 'px';
            el.style.height = nodeHeight + 'px';
            el.innerHTML = '<div class="flow-node-header">' + escapeHtml(node.type) + '</div>' +
                          '<div class="flow-node-label">' + escapeHtml(node.label || '') + '</div>' +
                          '<div class="flow-node-port flow-node-port-in"></div>' +
                          '<div class="flow-node-port flow-node-port-out"></div>';
            
            makeDraggable(el);
            container.appendChild(el);
            nodeElements.push({el: el, x: x, y: y, node: node});
        });
        
        function drawConnections() {
            svg.innerHTML = '';
            connections.forEach(function(conn) {
                if (conn.from >= nodeElements.length || conn.to >= nodeElements.length) return;
                const fromEl = nodeElements[conn.from].el;
                const toEl = nodeElements[conn.to].el;
                const fromRect = {x: fromEl.offsetLeft + nodeWidth, y: fromEl.offsetTop + nodeHeight / 2};
                const toRect = {x: toEl.offsetLeft, y: toEl.offsetTop + nodeHeight / 2};
                
                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                const midX = (fromRect.x + toRect.x) / 2;
                const d = 'M ' + fromRect.x + ' ' + fromRect.y + ' C ' + midX + ' ' + fromRect.y + ', ' + midX + ' ' + toRect.y + ', ' + toRect.x + ' ' + toRect.y;
                path.setAttribute('d', d);
                path.setAttribute('stroke', '#f59e0b');
                path.setAttribute('stroke-width', '2');
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke-opacity', '0.6');
                svg.appendChild(path);
                
                const arrow = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
                const ax = toRect.x;
                const ay = toRect.y;
                arrow.setAttribute('points', (ax) + ',' + (ay - 4) + ' ' + (ax + 6) + ',' + (ay) + ' ' + (ax) + ',' + (ay + 4));
                arrow.setAttribute('fill', '#f59e0b');
                arrow.setAttribute('stroke-opacity', '0.6');
                svg.appendChild(arrow);
            });
        }
        
        drawConnections();
        container.appendChild(svg);
        canvas.appendChild(container);
        
        container._nodeElements = nodeElements;
        container._connections = connections;
        container._drawConnections = drawConnections;
        
        if (!window._flowResizeHandler) {
            window._flowResizeHandler = function() {
                if (flowCanvas.contains(container)) {
                    drawConnections();
                }
            };
            window.addEventListener('resize', window._flowResizeHandler);
        }
    }

    function makeDraggable(el) {
        let isDragging = false;
        let startX, startY, initialLeft, initialTop;
        
        el.addEventListener('mousedown', function(e) {
            if (e.target.classList.contains('flow-node-port')) return;
            isDragging = true;
            startX = e.clientX;
            startY = e.clientY;
            initialLeft = el.offsetLeft;
            initialTop = el.offsetTop;
            el.style.zIndex = '10';
            el.style.cursor = 'grabbing';
        });
        
        document.addEventListener('mousemove', function(e) {
            if (!isDragging) return;
            const dx = e.clientX - startX;
            const dy = e.clientY - startY;
            el.style.left = (initialLeft + dx) + 'px';
            el.style.top = (initialTop + dy) + 'px';
            
            const container = el.parentElement;
            if (container && container._drawConnections) {
                container._drawConnections();
            }
        });
        
        document.addEventListener('mouseup', function() {
            if (isDragging) {
                isDragging = false;
                el.style.zIndex = '1';
                el.style.cursor = 'grab';
            }
        });
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    function openReportModal() {
        reportModal.classList.add('active');
        reportText.value = '';
        reportText.focus();
    }

    function closeReportModal() {
        reportModal.classList.remove('active');
    }

    function sendReport() {
        const text = reportText.value.trim();
        if (!text) {
            alert('Lütfen hata açıklaması yazın.');
            return;
        }
        
        const payload = new URLSearchParams();
        payload.append('hata_aciklama', text);
        payload.append('tarayici', navigator.userAgent);
        payload.append('tarih', new Date().toLocaleString('tr-TR'));
        payload.append('dosya', currentFile);
        payload.append('konum', window.location.href);
        
        fetch(formspreeEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Accept': 'application/json'
            },
            body: payload.toString()
        }).then(function(response) {
            if (response.ok) {
                appendOutput('Hata bildirimi gönderildi. Teşekkürler!', 'success');
                closeReportModal();
            } else {
                throw new Error('Gönderim başarısız');
            }
        }).catch(function(err) {
            appendOutput('Gönderim hatası: ' + err.message, 'error');
            appendOutput('Doğrudan mail atmayı deneyin: berkayozdemirtrtr@gmail.com', 'info');
        });
    }

    if (btnRun) btnRun.addEventListener('click', runPython);
    if (btnSync) btnSync.addEventListener('click', syncFlowchart);
    if (btnClearOutput) btnClearOutput.addEventListener('click', clearOutput);
    if (btnReport) btnReport.addEventListener('click', openReportModal);
    if (btnCancelReport) btnCancelReport.addEventListener('click', closeReportModal);
    if (btnSendReport) btnSendReport.addEventListener('click', sendReport);
    if (btnNewFile) btnNewFile.addEventListener('click', addNewFile);

    codeEditor.addEventListener('input', function() {
        saveCurrentFile();
    });

    reportModal.addEventListener('click', function(e) {
        if (e.target === reportModal) closeReportModal();
    });

    loadFilesFromStorage();

    // Kaydetme otomatik
    const autoSaveInterval = setInterval(saveFilesToStorage, 30000);
    window.addEventListener('beforeunload', () => {
        clearInterval(autoSaveInterval);
        saveFilesToStorage();
    });

    // ============================================
    // YARDIMCI FONKSİYONLAR
    // ============================================
    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function randomRange(min, max) {
        return Math.random() * (max - min) + min;
    }

})();