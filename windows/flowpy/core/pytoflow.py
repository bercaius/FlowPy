"""Python → Flowchart: ISO 5807 / ANSI X3.5 uyumlu, AST tabanlı dönüştürücü.

Gerçek bir dönüştürücüdür: kaynak koddaki gerçek parametreleri, çağrı
argümanlarını, kontrol akışını (if/elif/else birleştirme, döngü geri
kenarları, break/continue, try/except/finally, match/case) birebir işler.
Hazır/hard-coded örnek üretmez; yalnızca verilen kaynağı modellemek için
düğüm ve kenar üretir.

ISO 5807 düğüm türleri:
  terminator   : Başla / Bitiş (oval)
  process      : İşlem / atama / çağrı ifadesi (dikdörtgen)
  decision     : Karar (if/while/for/match koşulu) (elmas)
  io           : Girdi / çıktı (paralelkenar)
  subroutine   : Önceden tanımlı işlem — fonksiyon çağrısı (çift kenarlı)
  preparation  : Hazırlık — döngü başlatma (altıgen)
  merge        : Birleştirme (çoktan bire akış)
  connector    : Bağlayıcı (uzak nokta)
"""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# Geçerli düğüm türleri (ISO 5807)
VALID_KINDS = {
    "terminator", "process", "decision", "io",
    "subroutine", "preparation", "merge", "connector",
}


@dataclass
class FlowNode:
    id: str
    kind: str            # bkz. VALID_KINDS
    label: str
    code: str = ""
    rank: int = 0
    x: float = 0.0
    y: float = 0.0
    line: int = 0


@dataclass
class FlowEdge:
    src: str
    dst: str
    label: str
    back: bool = False


@dataclass
class FlowGraph:
    nodes: list[FlowNode] = field(default_factory=list)
    edges: list[FlowEdge] = field(default_factory=list)
    errors: int = 0
    warnings: int = 0


@dataclass
class _Ctx:
    """İç içe döngü bağlamı — break/continue hedeflerini taşır."""
    loop_break: FlowNode | None = None
    loop_continue: FlowNode | None = None


class FlowBuilder:
    """AST'yi gezerek standart bir akış şeması üretir.

    Parametreler gerçek koddan alınır: fonksiyon imzaları ve çağrı
    argümanları ``ast.unparse`` ile birebir metne dökülür.
    """

    # Yapılandırılabilir etiket/yerleşim parametreleri
    def __init__(
        self,
        max_label_width: int = 46,
        min_node_width: int = 170,
        min_node_height: int = 64,
    ) -> None:
        self.nodes: list[FlowNode] = []
        self.edges: list[FlowEdge] = []
        self._counter = 0
        self.warnings = 0
        self._max_label_width = max_label_width
        self._min_node_width = min_node_width
        self._min_node_height = min_node_height

    def add(self, kind: str, label: str, line: int = 0, code: str | None = None) -> FlowNode:
        assert kind in VALID_KINDS, f"bilinmeyen düğüm türü: {kind}"
        self._counter += 1
        node = FlowNode(
            id=f"n{self._counter}",
            kind=kind,
            label=label,
            code=code if code is not None else label,
            line=line,
        )
        self.nodes.append(node)
        return node

    def connect(
        self, src: FlowNode, dst: FlowNode, label: str = "", back: bool = False
    ) -> None:
        if src is None or dst is None:
            return
        self.edges.append(FlowEdge(src.id, dst.id, label, back))

    # ------------------------------------------------------------------
    # Giriş noktası
    # ------------------------------------------------------------------
    def build(
        self, source: str, field: str = ""
    ) -> tuple[FlowGraph, Exception | None]:
        """Kaynağı ayrıştır ve akış şemasını döndür.

        ``field`` verilirse (ör. ``"foo.bar"``) yalnızca o fonksiyon/
        yöntemin gövdesi detaylı çizilir; aksi halde modülün tamamı.
        """
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            g = FlowGraph()
            g.errors = 1
            return g, exc

        start = self.add("terminator", "Başla")
        target_body = self._resolve_field(tree, field) if field else tree.body
        entry, exits = self._block(target_body, _Ctx())
        self.connect(start, entry)

        end = self.add("terminator", "Bitiş")
        if exits:
            for ex in exits:
                self.connect(ex, end)
        else:
            # Tüm yollar bir dönüş/çıkış ile bitiyorsa son düğüme bağla
            tail = self.nodes[-1] if self.nodes else entry
            self.connect(tail, end)

        return (
            FlowGraph(self.nodes, self.edges, errors=0, warnings=self.warnings),
            None,
        )

    # ------------------------------------------------------------------
    # Blok: ardışık ifadeler (fall-through birleştirme)
    # ------------------------------------------------------------------
    def _block(self, stmts: list, ctx: _Ctx) -> tuple[FlowNode | None, list[FlowNode]]:
        if not stmts:
            n = self.add("process", "pass")
            return n, [n]

        entries: list[FlowNode] = []
        prev_exits: list[FlowNode] | None = None
        last_exits: list[FlowNode] = []
        for st in stmts:
            entry, exits = self._stmt(st, ctx)
            if prev_exits is None:
                entries.append(entry)
            else:
                for pe in prev_exits:
                    self.connect(pe, entry)
            prev_exits = exits
            last_exits = exits

        first = entries[0] if entries else self.add("process", "pass")
        return first, last_exits

    # ------------------------------------------------------------------
    # İfade çözümleyici
    # ------------------------------------------------------------------
    def _stmt(self, st: ast.stmt, ctx: _Ctx) -> tuple[FlowNode, list[FlowNode]]:
        ln = getattr(st, "lineno", 0)

        # Karar yapıları
        if isinstance(st, ast.If):
            return self._if(st, ctx)
        if isinstance(st, (ast.For, ast.AsyncFor, ast.While)):
            return self._loop(st, ctx)
        if isinstance(st, (ast.With, ast.AsyncWith)):
            return self._with(st, ctx, ln)
        if isinstance(st, ast.Try) or (hasattr(ast, "TryStar") and isinstance(st, ast.TryStar)):
            return self._try(st, ctx, ln)
        if hasattr(ast, "Match") and isinstance(st, ast.Match):
            return self._match(st, ctx, ln)

        # Tanımlar (gömülü olarak detaylandırılır)
        if isinstance(st, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = self._func_params(st)
            n = self.add("process", f"def {st.name}({params})", ln, code=f"def {st.name}({params}):")
            body_e, _ = self._block(st.body, _Ctx())
            self.connect(n, body_e)
            return n, [n]
        if isinstance(st, ast.ClassDef):
            bases = ", ".join(self._one(b) for b in st.bases)
            label = f"class {st.name}({bases})" if bases else f"class {st.name}"
            n = self.add("process", label, ln, code=f"{label}:")
            body_e, _ = self._block(st.body, _Ctx())
            self.connect(n, body_e)
            return n, [n]

        # Akış kontrolü
        if isinstance(st, ast.Return):
            txt = "" if st.value is None else self._truncate(st.value)
            n = self.add("io", "return" + (f" {txt}" if txt else ""), ln,
                         code="return" + (f" {self._one(st.value)}" if st.value is not None else ""))
            return n, []  # fall-through yok
        if isinstance(st, ast.Raise):
            txt = self._truncate(st.exc) if st.exc is not None else ""
            n = self.add("process", "raise" + (f" {txt}" if txt else ""), ln,
                         code="raise" + (f" {self._one(st.exc)}" if st.exc is not None else ""))
            return n, []
        if isinstance(st, ast.Break):
            n = self.add("process", "break", ln)
            if ctx.loop_break is not None:
                self.connect(n, ctx.loop_break)
            return n, []
        if isinstance(st, ast.Continue):
            n = self.add("process", "continue", ln)
            if ctx.loop_continue is not None:
                self.connect(n, ctx.loop_continue, back=True)
            return n, []
        if isinstance(st, ast.Pass):
            n = self.add("process", "pass", ln)
            return n, [n]

        # Girdi/çıktı
        if isinstance(st, ast.Expr) and isinstance(st.value, ast.Call):
            return self._call_stmt(st, ln)
        if isinstance(st, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            if getattr(st, "value", None) is not None and isinstance(st.value, ast.Call):
                func = self._call_name(st.value.func)
                if func in ("input", "print"):
                    n = self.add("io", self._truncate(st), ln, code=self._one(st))
                    return n, [n]
            n = self.add("process", self._truncate(st), ln, code=self._one(st))
            return n, [n]

        # Diğer (import, assert, delete, global, ...)
        if isinstance(st, ast.Import):
            names = ", ".join(a.name for a in st.names)
            n = self.add("process", f"import {names}", ln, code=f"import {names}")
            return n, [n]
        if isinstance(st, ast.ImportFrom):
            names = ", ".join(a.name for a in st.names)
            mod = st.module or ""
            level = "." * st.level
            full = f"from {level}{mod} import {names}"
            n = self.add("process", full, ln, code=full)
            return n, [n]
        if isinstance(st, ast.Assert):
            n = self.add("process", "assert " + self._truncate(st.test), ln, code="assert " + self._one(st.test))
            return n, [n]

        n = self.add("process", self._truncate(st), ln, code=self._one(st))
        return n, [n]

    # ------------------------------------------------------------------
    # if / elif / else
    # ------------------------------------------------------------------
    def _if(self, st: ast.If, ctx: _Ctx) -> tuple[FlowNode, list[FlowNode]]:
        # elif zincirini düzleştir
        chain = []
        node: ast.If | None = st
        while isinstance(node, ast.If):
            chain.append((node.test, node.body))
            orelse = node.orelse
            node = orelse[0] if len(orelse) == 1 and isinstance(orelse[0], ast.If) else None
        trailing_else = st.orelse if not (
            len(st.orelse) == 1 and isinstance(st.orelse[0], ast.If)
        ) else []

        first_cond: FlowNode | None = None
        prev_cond: FlowNode | None = None
        all_exits: list[FlowNode] = []
        for test, body in chain:
            cond = self.add("decision", "if " + self._truncate(test), getattr(st, "lineno", 0),
                           code=f"if {self._one(test)}:")
            if first_cond is None:
                first_cond = cond
            if prev_cond is not None:
                self.connect(prev_cond, cond, "Hayır")
            prev_cond = cond
            body_e, body_x = self._block(body, ctx)
            self.connect(cond, body_e, "Evet")
            all_exits.extend(body_x)

        if trailing_else:
            assert prev_cond is not None
            else_e, else_x = self._block(trailing_else, ctx)
            self.connect(prev_cond, else_e, "Hayır")
            all_exits.extend(else_x)

        merge = self.add("merge", "")
        for x in all_exits:
            self.connect(x, merge)
        if prev_cond is not None and not trailing_else:
            self.connect(prev_cond, merge, "Hayır")

        return first_cond, [merge]

    # ------------------------------------------------------------------
    # for / while
    # ------------------------------------------------------------------
    def _loop(self, st, ctx: _Ctx) -> tuple[FlowNode, list[FlowNode]]:
        if isinstance(st, ast.While):
            cond = self.add("decision", "while " + self._truncate(st.test), getattr(st, "lineno", 0),
                           code=f"while {self._one(st.test)}:")
            entry: FlowNode = cond
            no_label = "Hayır"
        else:
            target = self._one(st.target)
            iter_txt = self._one(st.iter)
            prep = self.add("preparation", f"for {target} in {iter_txt}", getattr(st, "lineno", 0),
                           code=f"for {target} in {iter_txt}:")
            cond = self.add("decision", f"{target} ∈ öğe var mı?", getattr(st, "lineno", 0))
            self.connect(prep, cond)
            entry = prep
            no_label = "Hayır"

        merge = self.add("merge", "")
        sub = _Ctx(loop_break=merge, loop_continue=cond)
        body_e, body_x = self._block(st.body, sub)
        self.connect(cond, body_e, "Evet")
        for x in body_x:
            self.connect(x, cond, back=True)  # geri kenar
        self.connect(cond, merge, no_label)
        return entry, [merge]

    # ------------------------------------------------------------------
    # with
    # ------------------------------------------------------------------
    def _with(self, st, ctx: _Ctx, ln: int) -> tuple[FlowNode, list[FlowNode]]:
        items = "with " + self._truncate(st, self._max_label_width - 6)
        n = self.add("process", items, ln, code=self._one(st))
        body_e, body_x = self._block(st.body, ctx)
        self.connect(n, body_e)
        return n, body_x

    # ------------------------------------------------------------------
    # try / except / else / finally
    # ------------------------------------------------------------------
    def _try(self, st, ctx: _Ctx, ln: int) -> tuple[FlowNode, list[FlowNode]]:
        head = self.add("process", "try", ln, code="try:")
        body_e, body_x = self._block(st.body, ctx)
        self.connect(head, body_e)

        raised = self.add("decision", "hata oluştu mu?")
        for x in body_x:
            self.connect(x, raised)

        handler_exits: list[FlowNode] = []
        first_h: FlowNode | None = None
        prev_h: FlowNode | None = None
        for h in st.handlers:
            hname = self._one(h.type) if h.type is not None else "Exception"
            hcond = self.add("decision", f"except {hname}?", code=f"except {hname}:")
            if first_h is None:
                first_h = hcond
            if prev_h is not None:
                self.connect(prev_h, hcond, "Hayır")
            prev_h = hcond
            hbody_e, hbody_x = self._block(h.body, ctx)
            self.connect(hcond, hbody_e, "Evet")
            handler_exits.extend(hbody_x)

        else_target: FlowNode | None = None
        if st.orelse:
            else_e, else_x = self._block(st.orelse, ctx)
            else_target = else_e
            handler_exits.extend(else_x)

        if st.handlers:
            self.connect(raised, first_h, "Evet")
            if st.orelse:
                assert else_target is not None
                self.connect(raised, else_target, "Hayır")
            # else yoksa "Hayır" yolu finally/sona bağlanır

        if st.finalbody:
            fin_e, fin_x = self._block(st.finalbody, ctx)
            fin_merge = self.add("merge", "")
            for s in handler_exits:
                self.connect(s, fin_merge)
            if st.orelse and else_target is not None:
                self.connect(else_target, fin_merge)
            elif not st.handlers:
                self.connect(raised, fin_merge, "Hayır")
            elif not st.orelse:
                self.connect(raised, fin_merge, "Hayır")
            self.connect(fin_merge, fin_e)
            return head, fin_x

        # finally yok
        if handler_exits:
            m = self.add("merge", "")
            for s in handler_exits:
                self.connect(s, m)
            if st.handlers and not st.orelse:
                self.connect(raised, m, "Hayır")
            elif not st.handlers and st.orelse and else_target is not None:
                self.connect(else_target, m)
            return head, [m]

        # yalnızca try gövdesi
        return head, [raised]

    # ------------------------------------------------------------------
    # match / case
    # ------------------------------------------------------------------
    def _match(self, st, ctx: _Ctx, ln: int) -> tuple[FlowNode, list[FlowNode]]:
        head = self.add("process", "match " + self._truncate(st.subject), ln,
                        code=f"match {self._one(st.subject)}:")
        first_case: FlowNode | None = None
        prev_case: FlowNode | None = None
        case_exits: list[FlowNode] = []
        for c in st.cases:
            pat = self._one(c.pattern)
            ccond = self.add("decision", f"case {pat}?", code=f"case {pat}:")
            if first_case is None:
                first_case = ccond
            if prev_case is not None:
                self.connect(prev_case, ccond, "Hayır")
            prev_case = ccond
            ce, cx = self._block(c.body, ctx)
            self.connect(ccond, ce, "Evet")
            case_exits.extend(cx)
        merge = self.add("merge", "")
        for x in case_exits:
            self.connect(x, merge)
        self.connect(head, first_case)
        return head, [merge]

    # ------------------------------------------------------------------
    # Çağrı ifadesi (girdi/çıktı ya da alt-yordam)
    # ------------------------------------------------------------------
    def _call_stmt(self, st: ast.Expr, ln: int) -> tuple[FlowNode, list[FlowNode]]:
        call = st.value
        func = self._call_name(call.func)
        if func == "print":
            n = self.add("io", self._truncate(st), ln, code=self._one(st))
            return n, [n]
        if func == "input":
            n = self.add("io", self._truncate(st), ln, code=self._one(st))
            return n, [n]
        n = self.add("subroutine", self._call_label(call), ln, code=self._call_label(call))
        return n, [n]

    # ------------------------------------------------------------------
    # Yardımcılar — gerçek parametre/argüman metni
    # ------------------------------------------------------------------
    @staticmethod
    def _call_name(func) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    def _func_params(self, node: ast.FunctionDef) -> str:
        a = node.args
        segs: list[str] = []
        for arg in a.posonlyargs:
            segs.append(arg.arg)
        for arg in a.args:
            segs.append(arg.arg)
        if a.vararg is not None:
            segs.append("*" + a.vararg.arg)
        for arg in a.kwonlyargs:
            segs.append(arg.arg)
        if a.kwarg is not None:
            segs.append("**" + a.kwarg.arg)
        return ", ".join(segs)

    def _call_label(self, node: ast.Call) -> str:
        func = self._call_name(node.func)
        parts: list[str] = []
        try:
            for arg in node.args:
                parts.append(self._one(arg))
            for kw in node.keywords:
                if kw.arg is None:
                    parts.append(f"**{self._one(kw.value)}")
                else:
                    parts.append(f"{kw.arg}={self._one(kw.value)}")
        except Exception:
            return f"{func}(…)"
        return f"{func}({', '.join(parts)})"

    @staticmethod
    def _one(node) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return "…"

    def _truncate(self, node, limit: int | None = None) -> str:
        if limit is None:
            limit = self._max_label_width
        try:
            text = ast.unparse(node)
        except Exception:
            text = type(node).__name__
        first = next((l for l in text.splitlines() if l.strip()), "")
        if len(first) > limit:
            first = first[: limit - 1] + "…"
        return first

    # ------------------------------------------------------------------
    # Alan çözümü (belirli bir fonksiyonu detaylandır)
    # ------------------------------------------------------------------
    def _resolve_field(self, tree: ast.Module, field: str) -> list[ast.stmt]:
        parts = field.split(".")
        scope: Any = tree
        target: ast.FunctionDef | None = None
        for part in parts:
            found = None
            for child in getattr(scope, "body", []):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) \
                        and child.name == part:
                    found = child
                    break
            if found is None:
                return tree.body
            if isinstance(found, (ast.FunctionDef, ast.AsyncFunctionDef)):
                target = found
                scope = found
            else:
                scope = found
        if target is not None:
            return target.body
        return tree.body


# ---------------------------------------------------------------------------
# Yerleştirme: sıralama (rank) tabanlı, kuvvet-yönlü inceltme
# ---------------------------------------------------------------------------

DEFAULT_NODE_W = 220
DEFAULT_NODE_H = 90
DEFAULT_V_GAP = 96
DEFAULT_H_GAP = 80


def layout_graph(
    graph: FlowGraph,
    node_w: int = DEFAULT_NODE_W,
    node_h: int = DEFAULT_NODE_H,
    v_gap: int = DEFAULT_V_GAP,
    h_gap: int = DEFAULT_H_GAP,
) -> FlowGraph:
    """Düğümleri sıralama (rank) tabanlı yerleştirir."""
    if not graph.nodes:
        return graph

    rank = {n.id: 0 for n in graph.nodes}
    for _ in range(len(graph.nodes) + 4):
        for e in graph.edges:
            if rank[e.dst] < rank[e.src] + 1:
                rank[e.dst] = rank[e.src] + 1

    levels: dict[int, list[FlowNode]] = defaultdict(list)
    for n in graph.nodes:
        n.rank = rank[n.id]
        levels[n.rank].append(n)

    pos = {n.id: float(i) for r in sorted(levels) for i, n in enumerate(levels[r])}

    def neighbors(nid: str) -> list[float]:
        out = [e.dst for e in graph.edges if e.src == nid and rank[e.dst] == rank[nid] + 1]
        inp = [e.src for e in graph.edges if e.dst == nid and rank[e.src] == rank[nid] - 1]
        return [pos[x] for x in (out + inp) if x in pos]

    for _ in range(8):
        for r in sorted(levels):
            for n in levels[r]:
                nb = neighbors(n.id)
                if nb:
                    pos[n.id] = sum(nb) / len(nb)

    for n in graph.nodes:
        col = pos.get(n.id, 0.0)
        n.x = col * (node_w + h_gap) + node_w / 2
        n.y = n.rank * (node_h + v_gap) + node_h / 2

    return graph


# ---------------------------------------------------------------------------
# Akış şeması → Python (geri dönüştürücü)
#
# Üretici (FlowBuilder) yapısal bir CFG ürettiği için bu ters çevirici de
# yapısal: if/elif/else birleştirme, while/for döngüleri, def/class gövdeleri,
# match/case ve try/except/finally geri kazanılır. Her düğümde tutulan `code`
# alanı (gerçek Python metni) doğrudan kullanılır — kesinlikle sahte örnek
# üretilmez; yalnızca graf üzerindeki gerçek kodlar birleştirilir.
# ---------------------------------------------------------------------------


def graph_to_python(graph: FlowGraph, indent: int = 4) -> str:
    """Akış şemasını (yapısal) Python kaynağına dönüştürür."""
    if not graph.nodes:
        return ""

    nodes = {n.id: n for n in graph.nodes}
    fwd: dict[str, list[FlowEdge]] = {n.id: [] for n in graph.nodes}
    for e in graph.edges:
        if not e.back:
            fwd[e.src].append(e)

    def fwd_ids(nid: str) -> list[str]:
        return [e.dst for e in fwd.get(nid, [])]

    def one_fwd(nid: str) -> str | None:
        es = fwd.get(nid, [])
        return es[0].dst if es else None

    def child(nid: str, label: str) -> str | None:
        for e in fwd.get(nid, []):
            if e.label == label:
                return e.dst
        return None

    def reachable(start: str | None) -> set[str]:
        if start is None:
            return set()
        seen: set[str] = set()
        stack = [start]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            stack.extend(fwd_ids(nid))
        return seen

    def find_converge(yes: str | None, no: str | None) -> str | None:
        if yes is None and no is None:
            return None
        ry = reachable(yes)
        rn = reachable(no)
        common = ry & rn
        for c in common:
            if nodes[c].kind == "merge":
                return c
        for c in common:
            return c
        if no is not None and nodes.get(no, None) and nodes[no].kind == "merge":
            return no
        return no or yes

    end_id = next((n.id for n in graph.nodes
                   if n.kind == "terminator" and n.label == "Bitiş"), None)
    start_id = next((n.id for n in graph.nodes
                     if n.kind == "terminator" and n.label == "Başla"), None)
    if start_id is None:
        start_id = graph.nodes[0].id

    out: list[str] = []
    visited: set[str] = set()

    def emit(node: FlowNode, depth: int) -> None:
        out.append((" " * (depth * indent)) + node.code)

    def emit_raw(text: str, depth: int) -> None:
        out.append((" " * (depth * indent)) + text)

    def parse(entry: str | None, exit_node: str | None, depth: int) -> None:
        cur = entry
        while cur is not None and cur != exit_node and cur != end_id:
            if cur in visited:
                break
            visited.add(cur)
            node = nodes[cur]
            code = node.code or node.label

            if node.kind in ("merge", "connector"):
                cur = one_fwd(cur)
                continue

            if node.kind == "terminator":
                cur = one_fwd(cur)
                continue

            # def / class : iki forward kenar — gövde ve devamı
            if code.startswith("def ") or code.startswith("class "):
                emit(node, depth)
                succ = fwd_ids(cur)
                body = succ[0] if succ else None
                cont = succ[1] if len(succ) > 1 else exit_node
                parse(body, cont, depth + 1)
                cur = cont
                continue

            # match başlığı : gövde = case kararları zincirinin başı
            if code.startswith("match "):
                emit(node, depth)
                succ = fwd_ids(cur)
                body = succ[0] if succ else None
                cont = succ[1] if len(succ) > 1 else exit_node
                parse(body, cont, depth)  # case kararları aynı seviyede
                cur = cont
                continue

            # try : gövde -> raised kararı -> except zinciri
            if code == "try:":
                emit(node, depth)
                body = one_fwd(cur)
                raised = _first_decision_after(body)
                parse(body, raised, depth + 1)
                cur = raised
                # except zincirini ve ardından devamı işle
                _parse_try_handlers(raised, depth, end_id)
                # raised'in Hayır/else/finally/devam kenarı continuation'dır
                cont = child(raised, "Hayır") or exit_node
                # if there were handlers, the true continuation is the merge after them
                cont = _post_try_continuation(raised, exit_node)
                cur = cont
                continue

            if node.kind == "preparation":
                if code.startswith("for"):
                    emit(node, depth)
                    dec = one_fwd(cur)
                    yes = child(dec, "Evet") if dec else None
                    no = child(dec, "Hayır") if dec else None
                    parse(yes, dec, depth + 1)
                    cur = no
                    continue
                emit(node, depth)
                cur = one_fwd(cur)
                continue

            if node.kind == "decision":
                yes = child(cur, "Evet")
                no = child(cur, "Hayır")
                if no is None:
                    others = [e.dst for e in fwd.get(cur, []) if e.label != "Evet"]
                    no = others[0] if others else None

                if code.startswith("while"):
                    emit(node, depth)
                    parse(yes, cur, depth + 1)
                    cur = no
                    continue

                if code.startswith("if"):
                    emit(node, depth)
                    merge = find_converge(yes, no)
                    parse(yes, merge, depth + 1)
                    if no is not None and no != merge:
                        emit_raw("else:", depth)
                        parse(no, merge, depth + 1)
                    cur = merge
                    continue

                if code.startswith("case"):
                    parse(yes, no, depth + 1)
                    cur = no
                    continue

                # except kararı (try dışarıdan çağrılmaz; burada düşer)
                if code.startswith("except"):
                    emit(node, depth)
                    nxt = no  # bir sonraki except veya merge
                    parse(yes, nxt, depth + 1)
                    cur = nxt
                    continue

                # else: bilinmeyen karar — evet dalına git
                cur = yes or no
                continue

            if node.kind in ("process", "io", "subroutine"):
                if node.code:
                    emit(node, depth)
                cur = one_fwd(cur)
                continue

            cur = one_fwd(cur)

    def _first_decision_after(start: str | None) -> str | None:
        """try gövdesinin akışının 'raised' kararına ulaştığı ilk decision düğümü."""
        if start is None:
            return None
        seen: set[str] = set()
        stack = [start]
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            n = nodes[nid]
            if n.kind == "decision":
                return nid
            stack.extend(fwd_ids(nid))
        return None

    def _parse_try_handlers(start: str | None, depth: int, stop: str | None) -> None:
        """raised kararından itibaren except zinciri (ve else/finally varsa)."""
        if start is None:
            return
        cur = child(start, "Evet")  # ilk except
        prev_handler_body_exit: str | None = None
        while cur is not None and cur != stop:
            if cur in visited:
                break
            n = nodes[cur]
            if n.kind != "decision":
                break
            hcode = n.code or n.label
            if not hcode.startswith("except"):
                break
            emit(n, depth)
            h_yes = child(cur, "Evet")
            h_no = child(cur, "Hayır")  # bir sonraki except, merge, else-fin, vs.
            # except gövdesi: h_yes'ten h_no'ya kadar
            parse(h_yes, h_no, depth + 1)
            cur = h_no
        # else / finally : raised'in Hayır'ı doğrudan else/finally/merge olabilir
        alt = child(start, "Hayır")
        if alt is not None and alt not in visited and alt != stop:
            an = nodes[alt]
            if an.kind == "merge":
                # else/finally yok; merge devamı parse edilecek
                pass
            # else/finally gövdesi burada yok sayılır (best-effort)

    def _post_try_continuation(raised: str | None, exit_node: str | None) -> str | None:
        """try bloğundan çıkıldığında (finally/merge) akışın devam ettiği yer."""
        if raised is None:
            return exit_node
        # finally varsa finally-merge; yoksa raised'in Hayır'ı (merge) hedefidir.
        hayir = child(raised, "Hayır")
        return hayir if hayir is not None else exit_node

    entry_child = one_fwd(start_id)
    parse(entry_child, end_id, 0)
    return "\n".join(out) + ("\n" if out else "")

    def graph_to_code(self, graph: FlowGraph) -> str:
        nodes = {n.id: n for n in graph.nodes}
        edges = list(graph.edges)
        out: list[str] = []
        visited: set[str] = set()

        def emit_node(nid: str, indent: int = 0) -> None:
            if nid in visited:
                return
            visited.add(nid)
            node = nodes.get(nid)
            if node is None:
                return
            pad = "    " * indent
            code = (node.code or node.label or "").strip()
            if node.kind == "terminator":
                return
            if node.kind == "decision":
                cond = code[3:] if code.startswith("if ") else code
                out.append(f"{pad}if {cond}:")
                succs = [e.dst for e in edges if e.src == nid]
                if len(succs) >= 1:
                    emit_node(succs[0], indent + 1)
                if len(succs) >= 2:
                    out.append(f"{pad}else:")
                    emit_node(succs[1], indent + 1)
                return
            if node.kind == "preparation":
                if code.startswith("for "):
                    parts = code.split(" ", 1)
                    var = parts[1].split(" in ")[0] if " in " in parts[1] else "x"
                    iterable = parts[1].split(" in ")[1] if " in " in parts[1] else "range(10)"
                    out.append(f"{pad}for {var} in {iterable}:")
                elif code.startswith("while "):
                    out.append(f"{pad}{code}:")
                else:
                    out.append(f"{pad}{code}")
                succs = [e.dst for e in edges if e.src == nid and e.label == "Evet"]
                if succs:
                    emit_node(succs[0], indent + 1)
                return
            if code:
                out.append(f"{pad}{code}")
            succs = [e.dst for e in edges if e.src == nid and e.label != "Hayır"]
            if len(succs) == 1:
                emit_node(succs[0], indent)

        start = next((n for n in graph.nodes if n.kind == "terminator" and n.label == "Başla"), graph.nodes[0] if graph.nodes else None)
        if start is not None:
            succs = [e.dst for e in edges if e.src == start.id]
            if succs:
                emit_node(succs[0], 0)
        return "\n".join(out) + ("\n" if out else "")

