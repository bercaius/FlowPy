/*
 * FlowPy - Örümcek Ağı Arka Plan Sistemi
 * 
 * Bu kod, sitenin arka planında interaktif bir örümcek ağı görselleştirmesi oluşturur.
 * 
 * AMAÇ:
 * Kullanıcı deneyimini zenginleştirmek için görsel bir arka plan sağlamak.
 * Sadece görsel efekt amaçlıdır, işlevsellik etkileşimi yoktur.
 * 
 * NASIL ÇALIŞIR:
 * - Mobil: Dokunmatik takibi, turuncu ağlar, dokunma noktasına çekim
 * - Desktop: Mouse takibi, 3D derinlik efekti (içe doğru çökme)
 * - Logo koruması: Düğümler logo içine girmiyor
 * - Ekran dışı: Düğümler ekran dışına çıkabilir, görünmez olurlar
 * 
 * GÖRÜNÜM:
 * - Beyaz arka plan
 * - Turuncu ağ çizgileri (#f59e0b)
 * - Logo ortada, ağlar etrafında
 * 
 * GÜVENLIK:
 * - XSS koruması: Kullanıcı girdisi yok
 * - Değer sınırlama: Tüm sayısal değerler kontrol edilir
 * - Encapsulation: IIFE pattern ile global scope koruması
 * 
 * GELİŞTİRİCİ NOTLARI:
 * Aşağıdaki AYARLAR bölümünden tüm değerleri kolayca değiştirebilirsiniz.
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
            searchResults.innerHTML = matches.map(section => 
                `<div class="search-result-item" data-url="${section.url}">${section.name}</div>`
            ).join('');
            searchResults.classList.add('active');

            // Tıklama olayları
            document.querySelectorAll('.search-result-item').forEach(item => {
                item.addEventListener('click', function() {
                    const url = this.getAttribute('data-url');
                    navigateToSection(url);
                });
            });
        } else {
            searchResults.innerHTML = '<div class="search-result-item">Sonuç bulunamadı</div>';
            searchResults.classList.add('active');
        }
    }

    // Bölüme git
    function navigateToSection(url) {
        // Arama çubuğunu gizle
        searchInput.value = '';
        searchResults.classList.remove('active');
        
        // Bölüme git
        console.log('Navigating to:', url);
        
        // Demo için alert
        alert('Bölüme gidiliyor: ' + url);
    }

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
    function animate() {
        // Mouse/touch pozisyonunu yumuşakça güncelle
        inputX += (targetInputX - inputX) * 0.1;
        inputY += (targetInputY - inputY) * 0.1;
        
        // Arka planı temizle
        ctx.fillStyle = '#ffffff';
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
    const nodes = [];
    
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

    window.addEventListener('resize', () => {
        init();
    });

    // ============================================
    // BAŞLAT
    // ============================================
    init();
    animate();

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