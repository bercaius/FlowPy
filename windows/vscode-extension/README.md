# FlowPy — Visual Studio Code Extension

FlowPy masaüstü uygulaması için gerçek bir VS Code eklentisi. Python kodunuzu
canlı akış şemasına dönüştürür, gerçek Python yorumlayıcısı ile çalıştırır ve
açık kodu FlowPy masaüstüne gönderir.

## Özellikler

- **Gerçek sözdizimi renklendirme** — `syntaxes/flowpy.tmLanguage.json` içinde
  eksiksiz bir TextMate dilbilgisi (yorumlar, diziler, sayılar, anahtar
  kelimeler, dekoratörler, fonksiyon/sınıf tanımları, f-string'ler).
  `.pyflow` / `.flowpy` dosyaları için geçerlidir.
- **Canlı akış şeması** — `FlowPy: Generate Flowchart` komutu, aktif editördeki
  kodu FlowPy köprüsüne (`ws://127.0.0.1:18809`) gönderir; dönen ISO 5807
  grafiği SVG olarak yan panelde çizilir.
- **Gerçek çalıştırma** — `FlowPy: Run Code`, kodu gerçek Python yorumlayıcısı
  ile çalıştırır; çıktı FlowPy tarafından geri akıtılır.
- **Kod gönderme** — `FlowPy: Send Active File to FlowPy`, kodu masaüstü
  editörüne yazar.

## Kurulum (geliştirme)

```powershell
cd vscode-extension
npm install
npm run compile
```

Ardından VS Code'da **Run Extension** (F5) ile hata ayıklama oturumu başlatın.

## Köprü protokolü (JSON-RPC 2.0)

Eklenti, FlowPy `Services` omurgasının WebSocket köprüsüne bağlanır:

| Yöntem           | params            | dönüş                       |
|------------------|-------------------|-----------------------------|
| `generate_graph` | `{ field }`       | `{ nodes, edges }`          |
| `set_code`       | `{ code }`        | `{ success }`               |
| `run`            | `{ code, cwd }`   | `{ started }` (+ `run_output` bildirimleri) |
| `ping`           | —                 | `"pong"`                    |

## Dizin yapısı

```
vscode-extension/
├── package.json
├── tsconfig.json
├── language-configuration.json
├── syntaxes/
│   └── flowpy.tmLanguage.json
└── src/
    └── extension.ts
```

Marka: TurcoDevelopStudio · Geliştirici: Berkay Özdemir ·
<https://bercaius.github.io/turcodevelop-studio/>
