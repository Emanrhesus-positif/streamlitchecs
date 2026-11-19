"""Simulateur d'échiquier pas à pas pour les moments critiques.

Les fichiers ne contiennent pas la suite complète des coups : on dispose, pour
chaque « moment critique », du FEN **avant** le coup et du coup joué. Le
simulateur rejoue donc ce coup à la demande, avec navigation, lecture
automatique et affichage du meilleur coup. Tout se passe dans le composant HTML
(JavaScript), sans relance Streamlit : les boutons Précédent / Suivant / Jouer
sont fluides et réellement pas à pas.
"""

from __future__ import annotations

import html
import json

import chess
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from data import DATA

PIECE_UNICODE = {
    "P": "♙",
    "N": "♘",
    "B": "♗",
    "R": "♖",
    "Q": "♕",
    "K": "♔",
    "p": "♟",
    "n": "♞",
    "b": "♝",
    "r": "♜",
    "q": "♛",
    "k": "♚",
}

PHASE_LABELS = {
    "opening": "Ouverture",
    "middlegame": "Milieu",
    "endgame": "Finale",
}

COULEUR_LABELS = {"white": "Blancs", "black": "Noirs"}


def charger_moments() -> pd.DataFrame:
    """Charge moments_critiques.csv (mise en cache par l'appelant si besoin)."""
    return pd.read_csv(DATA / "moments_critiques.csv")


def _square(square: int) -> dict[str, int]:
    return {"file": chess.square_file(square), "rank": chess.square_rank(square)}


def _pieces(fen: str) -> list[dict]:
    board = chess.Board(fen)
    pieces = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece is None:
            continue
        pieces.append(
            {
                "file": chess.square_file(square),
                "rank": chess.square_rank(square),
                "symbol": PIECE_UNICODE[piece.symbol()],
                "color": "w" if piece.color == chess.WHITE else "b",
            }
        )
    return pieces


def _move_info(fen: str, san: object) -> dict | None:
    """Traduit un coup SAN en coordonnées, capture, roque et promotion."""
    if san is None or (isinstance(san, float) and pd.isna(san)):
        return None
    san = str(san).strip()
    if not san:
        return None

    board = chess.Board(fen)
    try:
        move = board.parse_san(san)
    except Exception:
        return None

    info: dict = {
        "from": _square(move.from_square),
        "to": _square(move.to_square),
        "promotion": chess.piece_symbol(move.promotion).upper() if move.promotion else None,
        "rook_move": None,
        "captured": None,
        "castling": None,
    }

    if board.is_en_passant(move):
        captured_square = chess.square(
            chess.square_file(move.to_square), chess.square_rank(move.from_square)
        )
        info["captured"] = _square(captured_square)
    elif board.is_capture(move):
        info["captured"] = _square(move.to_square)

    if board.is_castling(move):
        rank = chess.square_rank(move.from_square)
        if chess.square_file(move.to_square) == 6:  # petit roque
            info["rook_move"] = {
                "from": {"file": 7, "rank": rank},
                "to": {"file": 5, "rank": rank},
            }
            info["castling"] = "O-O"
        elif chess.square_file(move.to_square) == 2:  # grand roque
            info["rook_move"] = {
                "from": {"file": 0, "rank": rank},
                "to": {"file": 3, "rank": rank},
            }
            info["castling"] = "O-O-O"

    return info


def _valeur(valeur: object, defaut: str = "—") -> object:
    if valeur is None:
        return defaut
    try:
        if pd.isna(valeur):
            return defaut
    except Exception:
        pass
    return valeur


def construire_sequence(
    partie_id: str,
    moments: pd.DataFrame,
    *,
    max_moments: int = 40,
) -> list[dict]:
    """Prépare les moments d'une partie pour le composant JavaScript."""
    pm = moments[moments["partie_id"] == partie_id].copy()
    pm = pm.sort_values(["ply", "numero_coup"]).head(max_moments)

    sequence: list[dict] = []
    for _, row in pm.iterrows():
        fen = row.get("fen_avant")
        if pd.isna(fen):
            continue
        move = _move_info(fen, row.get("coup"))
        if move is None:
            continue
        best_move = _move_info(fen, row.get("meilleur_coup"))
        perte = row.get("perte_eval_cp")
        try:
            perte = float(perte) if pd.notna(perte) else 0.0
        except Exception:
            perte = 0.0

        sequence.append(
            {
                "fen": str(fen),
                "pieces": _pieces(fen),
                "move": move,
                "best_move": best_move,
                "played": str(row.get("coup", "—")),
                "best": str(_valeur(row.get("meilleur_coup"))),
                "perte": perte,
                "phase": PHASE_LABELS.get(str(row.get("phase")), str(row.get("phase", "—"))),
                "numero": int(row.get("numero_coup")) if pd.notna(row.get("numero_coup")) else None,
                "ply": int(row.get("ply")) if pd.notna(row.get("ply")) else None,
                "couleur": COULEUR_LABELS.get(str(row.get("couleur")), str(row.get("couleur", "—"))),
                "eval_avant": _valeur(row.get("eval_avant_cp")),
                "eval_apres": _valeur(row.get("eval_apres_cp")),
            }
        )
    return sequence


TEMPLATE = r"""
<div class="sim">
  <div class="sim-head">
    <div>
      <div class="sim-title">__TITLE__</div>
      <div class="sim-sub" id="step-label">Moment 1 / 1</div>
    </div>
    <div class="badge" id="badge">Position avant le coup</div>
  </div>

  <div class="sim-body">
    <div class="board-side">
      <div id="board" aria-label="Échiquier"></div>
      <div class="board-caption" id="board-caption">Chargement…</div>
    </div>

    <div class="info-side">
      <div class="info" id="info"></div>

      <div class="controls">
        <button id="first" title="Premier moment">⏮</button>
        <button id="prev" title="Moment précédent">◀</button>
        <button id="play" class="primary" title="Jouer / rejouer le coup">▶ Jouer le coup</button>
        <button id="next" title="Moment suivant">▶|</button>
        <button id="auto" title="Lire tous les moments">▶▶ Tout lire</button>
        <button id="best" title="Afficher / masquer le meilleur coup">✦ Meilleur coup</button>
      </div>

      <input id="step" class="step" type="range" min="0" max="0" value="0" step="1" />

      <div class="hint">
        Chaque étape part de la position <b>avant</b> le coup et l'anime à la demande.
        Les fichiers fournissent les moments critiques, pas la suite complète des coups :
        on passe donc d'un moment critique au suivant.
      </div>
    </div>
  </div>
</div>

<style>
  :root {
    --panel: rgba(255,255,255,.055);
    --border: rgba(255,255,255,.14);
    --text: #e5e7eb;
    --muted: #9aa4b2;
    --blue: #60a5fa;
    --green: #22c55e;
    --amber: #f59e0b;
    --red: #ef4444;
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; background: transparent; color: var(--text); font-family: Inter, Segoe UI, system-ui, sans-serif; }
  .sim { padding: 6px 2px 10px; }
  .sim-head { display:flex; align-items:center; justify-content:space-between; gap:12px; margin-bottom:10px; }
  .sim-title { color:#f8fafc; font-weight:650; font-size:15px; }
  .sim-sub { color: var(--muted); font-size:12.5px; margin-top:2px; }
  .badge {
    display:inline-flex; align-items:center; gap:6px;
    border:1px solid var(--border); background: var(--panel);
    padding: 6px 10px; border-radius: 999px; font-size:12.5px; color:#dbeafe;
    white-space:nowrap;
  }
  .badge.gaffe { background: rgba(239,68,68,.16); border-color: rgba(239,68,68,.55); color:#fecaca; }
  .badge.erreur { background: rgba(245,158,11,.14); border-color: rgba(245,158,11,.55); color:#fde68a; }
  .badge.imprecision { background: rgba(96,165,250,.14); border-color: rgba(96,165,250,.55); color:#bfdbfe; }
  .sim-body { display:flex; gap:20px; align-items:flex-start; }
  .board-side { flex: 0 0 440px; max-width: 100%; }
  #board {
    position: relative; width: 440px; max-width: 100%; aspect-ratio: 1 / 1;
    border-radius: 14px; overflow: hidden; background:#0b1020;
    border:1px solid var(--border);
    box-shadow: 0 18px 48px rgba(0,0,0,.55);
  }
  #board .sq { position:absolute; }
  #board .light { background:#465a78; }
  #board .dark { background:#1d2941; }
  #board .hl { position:absolute; pointer-events:none; z-index:1; border:2px solid currentColor; box-shadow: inset 0 0 18px currentColor; }
  #board .hand { position:absolute; display:flex; align-items:center; justify-content:center;
    width:12.5%; height:12.5%; font-size: 38px; line-height:1; user-select:none; z-index:3;
    transition: left .72s cubic-bezier(.22,.61,.36,1), top .72s cubic-bezier(.22,.61,.36,1),
                transform .25s ease, opacity .32s ease;
  }
  #board .wp { color:#f8fafc; text-shadow: 0 2px 7px rgba(0,0,0,.85), 0 0 1px #000; }
  #board .bp { color:#dbe4f3; text-shadow: 0 2px 7px rgba(0,0,0,.95), 0 0 2px rgba(0,0,0,.9); }
  #board .last { outline: 2px solid rgba(96,165,250,.85); outline-offset: -2px; }
  #arrow { position:absolute; inset:0; pointer-events:none; z-index:4; }
  .board-caption { color:var(--muted); font-size:12px; text-align:center; margin-top:8px; }
  .info-side { flex:1 1 auto; min-width: 260px; }
  .info { display:grid; grid-template-columns: repeat(2, minmax(0,1fr)); gap:8px; margin-bottom:12px; }
  .kv { background: var(--panel); border:1px solid var(--border); border-radius:10px; padding:7px 9px; }
  .kv .k { color:var(--muted); font-size:11px; text-transform:uppercase; letter-spacing:.04em; }
  .kv .v { color:#f8fafc; font-size:14px; font-weight:600; margin-top:1px; }
  .kv.wide { grid-column: 1 / -1; }
  .controls { display:flex; flex-wrap:wrap; gap:7px; margin: 4px 0 10px; }
  .controls button {
    background: rgba(255,255,255,.075); color:#f8fafc; border:1px solid rgba(255,255,255,.22);
    border-radius: 10px; padding:8px 11px; cursor:pointer; font-size:13px;
    transition: background .18s ease, border-color .18s ease, transform .18s ease;
  }
  .controls button:hover { background: rgba(124,156,255,.20); border-color: rgba(148,176,255,.62); transform: translateY(-1px); }
  .controls button.primary { background: rgba(124,156,255,.24); border-color: rgba(148,176,255,.65); font-weight:600; }
  .controls button:disabled { opacity:.38; cursor:not-allowed; transform:none; }
  .step { width:100%; accent-color: var(--blue); margin: 2px 0 10px; }
  .hint { color:var(--muted); font-size:12px; line-height:1.45; border-top:1px solid var(--border); padding-top:8px; }
  .hint b { color:#dbeafe; }
  @media (max-width: 780px) {
    .sim-body { flex-direction: column; }
    .board-side { flex: 1 1 auto; width: 100%; }
    #board { width: 100%; max-width: 440px; margin: 0 auto; }
    .info-side { width: 100%; }
    #board .hand { font-size: 32px; }
  }
</style>

<script>
(function () {
  const DATA = __DATA__;
  const moments = DATA.moments || [];
  const board = document.getElementById('board');
  const badge = document.getElementById('badge');
  const info = document.getElementById('info');
  const stepLabel = document.getElementById('step-label');
  const boardCaption = document.getElementById('board-caption');
  const playBtn = document.getElementById('play');
  const autoBtn = document.getElementById('auto');
  const bestBtn = document.getElementById('best');
  const firstBtn = document.getElementById('first');
  const prevBtn = document.getElementById('prev');
  const nextBtn = document.getElementById('next');
  const step = document.getElementById('step');

  if (!moments.length) {
    badge.textContent = 'Aucun moment critique';
    boardCaption.textContent = 'Rien à afficher pour cette partie.';
    playBtn.disabled = autoBtn.disabled = bestBtn.disabled = true;
    return;
  }

  const state = {
    i: 0, played: false, auto: false, showBest: false,
    timers: [], sq: 0, size: 0, m: null, mover: null, captured: null,
    rook: null, arrow: null, pieceEls: []
  };

  function clearTimers() {
    state.timers.forEach((id) => clearTimeout(id));
    state.timers = [];
  }
  function later(fn, ms) {
    const id = setTimeout(() => {
      state.timers = state.timers.filter((x) => x !== id);
      fn();
    }, ms);
    state.timers.push(id);
    return id;
  }
  function top(rank, sq) { return (7 - rank) * sq; }
  function left(file, sq) { return file * sq; }
  function center(file, rank, sq) { return { x: (file + 0.5) * sq, y: (7 - rank + 0.5) * sq }; }
  function niveau(perte) { return perte >= 200 ? 'gaffe' : (perte >= 100 ? 'erreur' : 'imprecision'); }
  function couleurNiveau(perte) {
    return perte >= 200 ? '#ef4444' : (perte >= 100 ? '#f59e0b' : '#60a5fa');
  }

  function renderBoard(m, animateHighlights) {
    clearTimers();
    state.played = false;
    state.m = m;
    const size = Math.max(240, Math.round(board.getBoundingClientRect().width || 440));
    const sq = size / 8;
    state.size = size;
    state.sq = sq;
    board.innerHTML = '';
    state.pieceEls = [];

    for (let r = 0; r < 8; r++) {
      for (let f = 0; f < 8; f++) {
        const d = document.createElement('div');
        d.className = 'sq ' + ((r + f) % 2 === 0 ? 'light' : 'dark');
        d.style.left = (f * sq) + 'px';
        d.style.top = (r * sq) + 'px';
        d.style.width = sq + 'px';
        d.style.height = sq + 'px';
        board.appendChild(d);
      }
    }

    // Dernières cases jouées (repère visuel)
    const lastFrom = document.createElement('div');
    const lastTo = document.createElement('div');
    [lastFrom, lastTo].forEach((el) => { el.className = 'hl'; el.style.color = 'rgba(96,165,250,.75)'; });
    lastFrom.style.left = left(m.move.from.file, sq) + 'px';
    lastFrom.style.top = top(m.move.from.rank, sq) + 'px';
    lastTo.style.left = left(m.move.to.file, sq) + 'px';
    lastTo.style.top = top(m.move.to.rank, sq) + 'px';
    lastFrom.style.width = lastTo.style.width = sq + 'px';
    lastFrom.style.height = lastTo.style.height = sq + 'px';
    board.appendChild(lastFrom);
    board.appendChild(lastTo);
    later(() => { lastFrom.style.opacity = '0.55'; lastTo.style.opacity = '0.55'; }, 60);

    m.pieces.forEach((p) => {
      const el = document.createElement('div');
      el.className = 'hand ' + (p.color === 'w' ? 'wp' : 'bp');
      el.textContent = p.symbol;
      el.style.left = left(p.file, sq) + 'px';
      el.style.top = top(p.rank, sq) + 'px';
      el.style.width = sq + 'px';
      el.style.height = sq + 'px';
      el.style.fontSize = Math.round(sq * 0.78) + 'px';
      board.appendChild(el);
      state.pieceEls.push({ el, p });
    });

    // Flèche « meilleur coup » (cachée avant le coup joué)
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('id', 'arrow');
    svg.setAttribute('viewBox', '0 0 ' + size + ' ' + size);
    svg.style.display = 'none';
    svg.innerHTML = '<defs><marker id="head" markerWidth="9" markerHeight="9" refX="7" refY="4.5" orient="auto"><path d="M0,0 L9,4.5 L0,9 z" fill="#22c55e"/></marker></defs>';
    if (m.best_move) {
      const a = center(m.best_move.from.file, m.best_move.from.rank, sq);
      const b = center(m.best_move.to.file, m.best_move.to.rank, sq);
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', a.x); line.setAttribute('y1', a.y);
      line.setAttribute('x2', b.x); line.setAttribute('y2', b.y);
      line.setAttribute('stroke', '#22c55e'); line.setAttribute('stroke-width', '5');
      line.setAttribute('stroke-linecap', 'round'); line.setAttribute('opacity', '0.92');
      line.setAttribute('marker-end', 'url(#head)');
      svg.appendChild(line);
    }
    state.arrow = svg;
    state.showBest = false;
    board.appendChild(svg);

    // Pièces concernées par l'animation
    const from = m.move.from, to = m.move.to;
    state.mover = state.pieceEls.find((it) => it.p.file === from.file && it.p.rank === from.rank) || null;
    state.captured = null;
    if (m.move.captured) {
      state.captured = state.pieceEls.find((it) =>
        it.p.file === m.move.captured.file && it.p.rank === m.move.captured.rank
      ) || null;
    }
    state.rook = null;
    if (m.move.rook_move) {
      state.rook = state.pieceEls.find((it) =>
        it.p.file === m.move.rook_move.from.file && it.p.rank === m.move.rook_move.from.rank
      ) || null;
    }

    if (animateHighlights) {
      const flash = document.createElement('div');
      flash.className = 'hl';
      flash.style.color = couleurNiveau(m.perte);
      flash.style.left = left(to.file, sq) + 'px';
      flash.style.top = top(to.rank, sq) + 'px';
      flash.style.width = flash.style.height = sq + 'px';
      flash.style.opacity = '0.9';
      board.appendChild(flash);
      later(() => { flash.style.opacity = '0'; }, 420);
    }
  }

  function updateInfo() {
    const m = moments[state.i];
    const niveauCss = niveau(m.perte);
    badge.className = 'badge';
    if (!state.played) {
      badge.textContent = 'Position avant le coup' + (m.numero ? ' n° ' + m.numero : '');
    } else if (niveauCss === 'gaffe') {
      badge.classList.add('gaffe');
      badge.textContent = '🚨 Gaffe · ' + Math.round(m.perte) + ' cp perdus';
    } else if (niveauCss === 'erreur') {
      badge.classList.add('erreur');
      badge.textContent = '⚠️ Erreur · ' + Math.round(m.perte) + ' cp';
    } else {
      badge.classList.add('imprecision');
      badge.textContent = 'ℹ️ Imprécision · ' + Math.round(m.perte) + ' cp';
    }

    stepLabel.textContent = 'Moment ' + (state.i + 1) + ' / ' + moments.length;
    step.max = String(moments.length - 1);
    step.value = String(state.i);
    boardCaption.textContent = m.couleur + ' · ' + m.phase + ' · coup ' + (m.numero ?? '—');

    const bestTxt = m.best_move ? m.best : (m.best || '—');
    info.innerHTML =
      '<div class="kv"><div class="k">Coup joué</div><div class="v">' + escapeHtml(m.played) + '</div></div>' +
      '<div class="kv"><div class="k">Meilleur coup</div><div class="v" style="color:#86efac">' + escapeHtml(bestTxt) + '</div></div>' +
      '<div class="kv"><div class="k">Perte</div><div class="v" style="color:' + couleurNiveau(m.perte) + '">' + Math.round(m.perte) + ' cp</div></div>' +
      '<div class="kv"><div class="k">Phase</div><div class="v">' + escapeHtml(m.phase) + '</div></div>' +
      '<div class="kv"><div class="k">Évaluation avant</div><div class="v">' + escapeHtml(String(m.eval_avant)) + ' cp</div></div>' +
      '<div class="kv"><div class="k">Évaluation après</div><div class="v">' + escapeHtml(String(m.eval_apres)) + ' cp</div></div>';

    playBtn.textContent = state.played ? '↻ Rejouer' : '▶ Jouer le coup';
    autoBtn.textContent = state.auto ? '⏸ Stop' : '▶▶ Tout lire';
    firstBtn.disabled = state.i === 0;
    prevBtn.disabled = state.i === 0;
    nextBtn.disabled = state.i === moments.length - 1;
    if (state.arrow) state.arrow.style.display = (state.showBest && moments[state.i].best_move) ? 'block' : 'none';
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }

  function loadMoment(i, opts) {
    opts = opts || {};
    clearTimers();
    state.i = Math.max(0, Math.min(moments.length - 1, i));
    state.played = false;
    const m = moments[state.i];
    renderBoard(m, true);
    state.showBest = false;
    updateInfo();
    if (opts.play || state.auto) {
      later(playMove, 420);
    }
  }

  function playMove() {
    if (state.played) return;
    const m = state.m;
    if (!m) return;
    state.played = true;
    updateInfo();

    const sq = state.sq;
    const mover = state.mover;
    const captured = state.captured;
    const rook = state.rook;

    if (mover) {
      mover.el.style.zIndex = '8';
      mover.el.style.transform = 'scale(1.10)';
      later(() => {
        mover.el.style.left = left(m.move.to.file, sq) + 'px';
        mover.el.style.top = top(m.move.to.rank, sq) + 'px';
      }, 140);
      if (m.move.promotion) {
        later(() => {
          const promo = String(m.move.promotion).toUpperCase();
          const mapW = { Q: '♕', R: '♖', B: '♗', N: '♘' };
          const mapB = { Q: '♛', R: '♜', B: '♝', N: '♞' };
          mover.el.textContent = mover.p.color === 'w' ? (mapW[promo] || '♕') : (mapB[promo] || '♛');
        }, 560);
      }
    }
    if (captured) {
      later(() => {
        captured.el.style.opacity = '0';
        captured.el.style.transform = 'scale(0.42)';
      }, 420);
    }
    if (rook && m.move.rook_move) {
      later(() => {
        rook.el.style.left = left(m.move.rook_move.to.file, sq) + 'px';
        rook.el.style.top = top(m.move.rook_move.to.rank, sq) + 'px';
      }, 200);
    }

    later(() => {
      if (mover) mover.el.style.transform = 'scale(1.0)';
      // Le meilleur coup apparaît après le coup joué : on compare.
      state.showBest = true;
      updateInfo();
      if (state.auto) {
        if (state.i < moments.length - 1) {
          later(() => loadMoment(state.i + 1, { play: true }), 1500);
        } else {
          state.auto = false;
          updateInfo();
        }
      }
    }, 1000);
  }

  playBtn.addEventListener('click', () => {
    state.auto = false;
    if (state.played) {
      loadMoment(state.i, { play: true });
    } else {
      playMove();
    }
  });
  firstBtn.addEventListener('click', () => { state.auto = false; loadMoment(0, { play: false }); });
  prevBtn.addEventListener('click', () => { state.auto = false; loadMoment(state.i - 1, { play: false }); });
  nextBtn.addEventListener('click', () => { state.auto = false; loadMoment(state.i + 1, { play: false }); });
  bestBtn.addEventListener('click', () => {
    state.showBest = !state.showBest;
    updateInfo();
  });
  autoBtn.addEventListener('click', () => {
    state.auto = !state.auto;
    if (state.auto) {
      if (state.played && state.i < moments.length - 1) {
        loadMoment(state.i + 1, { play: true });
      } else {
        playMove();
      }
    }
    updateInfo();
  });
  step.addEventListener('input', (e) => {
    state.auto = false;
    loadMoment(Number(e.target.value), { play: false });
  });

  loadMoment(0, { play: false });
})();
</script>
"""


def render_simulateur(partie_id: str, moments: pd.DataFrame, *, label: str | None = None) -> None:
    """Affiche le simulateur pas à pas pour une partie."""
    sequence = construire_sequence(partie_id, moments)
    if not sequence:
        components.html(
            "<div style='font-family:system-ui;color:#9aa4b2;padding:12px'>"
            "Aucun moment critique exploitable pour cette partie.</div>",
            height=90,
            scrolling=False,
        )
        return

    titre = label or f"Partie {partie_id}"
    payload = json.dumps(
        {"partie_id": partie_id, "label": titre, "moments": sequence},
        ensure_ascii=False,
        separators=(",", ":"),
    )
    html_code = TEMPLATE.replace("__TITLE__", html.escape(titre)).replace("__DATA__", payload)
    components.html(html_code, height=700, scrolling=False)


def selecteur_moments(
    df: pd.DataFrame,
    moments: pd.DataFrame,
    *,
    key_prefix: str,
) -> tuple[str | None, pd.DataFrame]:
    """Sélecteurs famille + partie, restreints aux parties visibles.

    Retourne (partie_id, moments filtrés) ou (None, DataFrame vide).
    """
    if moments.empty:
        return None, moments

    visibles = moments.merge(
        df[["partie_id", "ouverture_famille", "resultat"]],
        on="partie_id",
        how="inner",
        suffixes=("", "_partie"),
    )
    visibles = visibles[visibles["fen_avant"].notna() & visibles["coup"].notna()].copy()
    if visibles.empty:
        return None, visibles

    familles = sorted(
        str(f) for f in visibles["ouverture_famille"].dropna().unique() if str(f).strip()
    )
    col1, col2 = st.columns(2)
    with col1:
        famille = st.selectbox(
            "Famille d'ouverture",
            options=["Toutes"] + familles,
            key=f"{key_prefix}_famille",
        )
    sous = visibles if famille == "Toutes" else visibles[visibles["ouverture_famille"] == famille].copy()

    parties = (
        sous[["partie_id", "date_jeu", "resultat", "ouverture_famille"]]
        .drop_duplicates(subset=["partie_id"])
        .sort_values(["date_jeu", "partie_id"], ascending=[False, True])
    )
    labels: dict[str, str] = {}
    for row in parties.itertuples(index=False):
        date = pd.to_datetime(row.date_jeu).strftime("%Y-%m-%d") if pd.notna(row.date_jeu) else "—"
        labels[row.partie_id] = f"{row.partie_id} · {date} · {row.resultat} · {row.ouverture_famille}"

    options = parties["partie_id"].tolist()
    with col2:
        partie = st.selectbox(
            "Partie",
            options=options,
            format_func=lambda x: labels.get(x, str(x)),
            key=f"{key_prefix}_partie",
        )

    return (partie if partie in set(options) else None), sous
