import * as vscode from 'vscode';
import WebSocket from 'ws';

// ---------------------------------------------------------------------------
// FlowPy bridge client (JSON-RPC 2.0 over WebSocket)
// ---------------------------------------------------------------------------
class FlowPyClient {
    private ws: WebSocket | null = null;
    private reqId = 0;
    private pending = new Map<number, (resp: any) => void>();
    private connecting: Promise<void> | null = null;
    onNotify: ((method: string, params: any) => void) | null = null;

    private url(): string {
        const cfg = vscode.workspace.getConfiguration('flowpy');
        const host = cfg.get<string>('bridgeHost') || '127.0.0.1';
        const port = cfg.get<number>('bridgePort') || 18809;
        return `ws://${host}:${port}`;
    }

    connect(): Promise<void> {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            return Promise.resolve();
        }
        if (this.connecting) {
            return this.connecting;
        }
        this.connecting = new Promise<void>((resolve, reject) => {
            const ws = new WebSocket(this.url());
            ws.on('open', () => {
                this.ws = ws;
                resolve();
            });
            ws.on('message', (data: WebSocket.RawData) => this.onMessage(data.toString()));
            ws.on('close', () => {
                this.ws = null;
                this.connecting = null;
            });
            ws.on('error', (err: Error) => {
                this.connecting = null;
                reject(err);
            });
        });
        return this.connecting;
    }

    private onMessage(raw: string): void {
        let msg: any;
        try {
            msg = JSON.parse(raw);
        } catch {
            return;
        }
        if (msg.id !== undefined && this.pending.has(msg.id)) {
            const cb = this.pending.get(msg.id)!;
            this.pending.delete(msg.id);
            cb(msg);
        } else if (msg.method && this.onNotify) {
            this.onNotify(msg.method, msg.params || {});
        }
    }

    async request(method: string, params: any = {}): Promise<any> {
        await this.connect();
        const id = ++this.reqId;
        const payload = JSON.stringify({ jsonrpc: '2.0', id, method, params });
        return new Promise<any>((resolve, reject) => {
            const timer = setTimeout(() => {
                this.pending.delete(id);
                reject(new Error('FlowPy bridge timeout'));
            }, 8000);
            this.pending.set(id, (resp) => {
                clearTimeout(timer);
                if (resp.error) {
                    reject(new Error(resp.error.message || 'FlowPy error'));
                } else {
                    resolve(resp.result);
                }
            });
            this.ws!.send(payload);
        });
    }

    notify(method: string, params: any = {}): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ jsonrpc: '2.0', method, params }));
        }
    }
}

// ---------------------------------------------------------------------------
// SVG flowchart renderer
// ---------------------------------------------------------------------------
const KIND_COLOR: Record<string, string> = {
    terminator: '#2ea043',
    process: '#8b949e',
    decision: '#d29922',
    io: '#2f81f7',
    subroutine: '#a371f7',
    preparation: '#58a6ff',
    merge: '#6e7681',
    connector: '#6e7681',
};

const NW = 220, NH = 90, SW = 48;

function isSmall(kind: string): boolean {
    return kind === 'merge' || kind === 'connector';
}

function shapeSvg(node: any): string {
    const cx = node.x, cy = node.y;
    const color = KIND_COLOR[node.kind] || '#8b949e';
    const label = (node.label || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    if (isSmall(node.kind)) {
        return `<circle cx="${cx}" cy="${cy}" r="${SW / 2}" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
    }
    const x = cx - NW / 2, y = cy - NH / 2;
    let body = '';
    switch (node.kind) {
        case 'terminator':
            body = `<rect x="${x}" y="${y}" width="${NW}" height="${NH}" rx="${NH / 2}" ry="${NH / 2}" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
            break;
        case 'decision':
            body = `<polygon points="${cx},${y} ${x + NW},${cy} ${cx},${y + NH} ${x},${cy}" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
            break;
        case 'io':
            body = `<polygon points="${x + 24},${y} ${x + NW},${y} ${x + NW - 24},${y + NH} ${x},${y + NH}" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
            break;
        case 'preparation':
            body = `<polygon points="${x + 45},${y} ${x + NW - 45},${y} ${x + NW},${cy} ${x + NW - 45},${y + NH} ${x + 45},${y + NH} ${x},${cy}" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
            break;
        case 'subroutine':
            body = `<rect x="${x}" y="${y}" width="${NW}" height="${NH}" rx="10" ry="10" fill="#161b22" stroke="${color}" stroke-width="2.4"/>` +
                `<rect x="${x + 6}" y="${y + 6}" width="${NW - 12}" height="${NH - 12}" rx="7" ry="7" fill="none" stroke="${color}" stroke-width="1.2"/>`;
            break;
        default:
            body = `<rect x="${x}" y="${y}" width="${NW}" height="${NH}" rx="14" ry="14" fill="#161b22" stroke="${color}" stroke-width="2.4"/>`;
    }
    const font = node.kind === 'decision' || node.kind === 'io' ? 11 : 12;
    const text = `<text x="${cx}" y="${cy + 4}" fill="#ffffff" font-family="Segoe UI, sans-serif" font-size="${font}" text-anchor="middle" dominant-baseline="middle">${label}</text>`;
    return body + text;
}

function buildSvg(graph: any): string {
    const nodes: any[] = graph.nodes || [];
    const edges: any[] = graph.edges || [];
    if (nodes.length === 0) {
        return `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="120"><text x="20" y="60" fill="#8b949e" font-family="Segoe UI" font-size="14">Akış şeması yok (kod boş veya sözdizimi hatası).</text></svg>`;
    }
    const pos = new Map<string, any>();
    nodes.forEach((n) => pos.set(n.id, n));
    let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
    nodes.forEach((n) => {
        const w = isSmall(n.kind) ? SW : NW;
        const h = isSmall(n.kind) ? SW : NH;
        minX = Math.min(minX, n.x - w / 2);
        minY = Math.min(minY, n.y - h / 2);
        maxX = Math.max(maxX, n.x + w / 2);
        maxY = Math.max(maxY, n.y + h / 2);
    });
    const pad = 60;
    const W = Math.ceil(maxX - minX + pad * 2);
    const H = Math.ceil(maxY - minY + pad * 2);
    const ox = -minX + pad, oy = -minY + pad;

    let edgeSvg = '';
    edges.forEach((e) => {
        const a = pos.get(e.src), b = pos.get(e.dst);
        if (!a || !b) return;
        const x1 = a.x + ox, y1 = a.y + oy, x2 = b.x + ox, y2 = b.y + oy;
        const dash = e.back ? ' stroke-dasharray="6 4"' : '';
        edgeSvg += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="#6e7681" stroke-width="2"${dash} marker-end="url(#arrow)"/>`;
        if (e.label) {
            edgeSvg += `<text x="${(x1 + x2) / 2 + 6}" y="${(y1 + y2) / 2 - 4}" fill="#c9d1d9" font-family="Segoe UI" font-size="10">${e.label}</text>`;
        }
    });

    let nodeSvg = '';
    nodes.forEach((n) => {
        nodeSvg += shapeSvg({ ...n, x: n.x + ox, y: n.y + oy });
    });

    return `<svg xmlns="http://www.w3.org/2000/svg" width="${W}" height="${H}" viewBox="0 0 ${W} ${H}">
<defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0,0 L8,3 L0,6 Z" fill="#6e7681"/></marker></defs>
<rect width="${W}" height="${H}" fill="#0d1117"/>
${edgeSvg}
${nodeSvg}
</svg>`;
}

// ---------------------------------------------------------------------------
// Commands
// ---------------------------------------------------------------------------
function activeCode(): { code: string; ok: boolean } {
    const ed = vscode.window.activeTextEditor;
    if (!ed) {
        vscode.window.showWarningMessage('FlowPy: Önce bir dosya açın.');
        return { code: '', ok: false };
    }
    return { code: ed.document.getText(), ok: true };
}

async function generateFlowchart(client: FlowPyClient): Promise<void> {
    const { code, ok } = activeCode();
    if (!ok) return;
    try {
        const graph = await client.request('generate_graph', { field: '' });
        if (graph && graph.error) {
            vscode.window.showErrorMessage(`FlowPy: ${graph.error}`);
            return;
        }
        const panel = vscode.window.createWebviewPanel(
            'flowpyFlowchart',
            'FlowPy Akış Şeması',
            vscode.ViewColumn.Beside,
            { enableScripts: false }
        );
        panel.webview.html = `<!DOCTYPE html><html><body style="margin:0;background:#0d1117">
<div style="padding:8px;color:#8b949e;font-family:Segoe UI;font-size:12px">FlowPy — ISO 5807 akış şeması</div>
${buildSvg(graph)}
</body></html>`;
    } catch (err: any) {
        vscode.window.showErrorMessage(`FlowPy köprüsüne bağlanılamadı: ${err.message}`);
    }
}

async function runCode(client: FlowPyClient): Promise<void> {
    const { code, ok } = activeCode();
    if (!ok) return;
    const out = vscode.window.createOutputChannel('FlowPy');
    out.show(true);
    out.appendLine('>> FlowPy ile çalıştırılıyor...');
    client.onNotify = (method, params) => {
        if (method === 'run_output') {
            out.appendLine(params.line);
        } else if (method === 'run_finished') {
            out.appendLine(`[bitti] exit=${params.exit}`);
        } else if (method === 'run_started') {
            out.appendLine('[başladı]');
        }
    };
    try {
        await client.request('run', { code });
        vscode.window.showInformationMessage('FlowPy: Kod çalıştırıldı, çıktı aşağıda.');
    } catch (err: any) {
        out.appendLine(`HATA: ${err.message}`);
    }
}

async function sendToFlowPy(client: FlowPyClient): Promise<void> {
    const { code, ok } = activeCode();
    if (!ok) return;
    try {
        await client.request('set_code', { code });
        vscode.window.showInformationMessage('FlowPy: Kod FlowPy masaüstüne gönderildi.');
    } catch (err: any) {
        vscode.window.showErrorMessage(`FlowPy köprüsüne bağlanılamadı: ${err.message}`);
    }
}

function openFlowPy(): void {
    vscode.env.openExternal(vscode.Uri.parse('https://bercaius.github.io/turcodevelop-studio/'));
}

export function activate(context: vscode.ExtensionContext): void {
    const client = new FlowPyClient();
    context.subscriptions.push(
        vscode.commands.registerCommand('flowpy.generateFlowchart', () => generateFlowchart(client)),
        vscode.commands.registerCommand('flowpy.runCode', () => runCode(client)),
        vscode.commands.registerCommand('flowpy.sendToFlowPy', () => sendToFlowPy(client)),
        vscode.commands.registerCommand('flowpy.openFlowPy', () => openFlowPy())
    );
}

export function deactivate(): void {
    // client bağlantısı süreç kapanınca otomatik sonlanır
}
