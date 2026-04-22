let board = null;
let game = null;         // chess.js instance for client-side validation
let sessionId = null;
let playerColor = 'white';
let selectedElo = 1500;
let moveCount = 0;
let locked = false;      // prevent moves while waiting for server
let gameStartTime = null;

// ── Screen helpers ──────────────────────────────────────────────
function showScreen(id) {
  document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
}

// ── Setup screen ────────────────────────────────────────────────
document.querySelectorAll('.color-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
  });
});

document.getElementById('start-btn').addEventListener('click', startGame);

async function startGame() {
  selectedElo = parseInt(document.getElementById('elo-select').value);
  const colorBtn = document.querySelector('.color-btn.active');
  const requestedColor = colorBtn ? colorBtn.dataset.color : 'white';

  const res = await fetch('/api/new_game', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ elo: selectedElo, player_color: requestedColor }),
  });

  if (!res.ok) {
    alert('Failed to start game: ' + (await res.text()));
    return;
  }

  const state = await res.json();
  sessionId = state.session_id;
  playerColor = state.player_color;
  moveCount = 0;
  gameStartTime = Date.now();

  document.getElementById('maia-elo-badge').textContent = selectedElo;
  document.getElementById('move-history').innerHTML = '';
  document.getElementById('end-overlay').classList.add('hidden');

  initBoard(state);
  showScreen('game-screen');

  // If player is black, Maia goes first — trigger with a dummy request
  // We send a special "maia_first" signal by requesting state, then
  // asking server to make Maia move when it's Maia's turn
  if (playerColor === 'black') {
    await triggerMaiaFirst();
  }
}

// ── Board init ──────────────────────────────────────────────────
function initBoard(state) {
  game = new Chess();

  const orientation = playerColor === 'black' ? 'black' : 'white';

  if (board) board.destroy();

  board = Chessboard('board', {
    position: state.fen,
    orientation: orientation,
    draggable: true,
    onDragStart: onDragStart,
    onDrop: onDrop,
    onSnapEnd: onSnapEnd,
    pieceTheme: 'https://chessboardjs.com/img/chesspieces/wikipedia/{piece}.png',
  });

  updateStatus(state);
}

// ── Drag & drop handlers ────────────────────────────────────────
function onDragStart(source, piece) {
  if (locked) return false;
  if (game.game_over()) return false;

  const myPieceColor = playerColor === 'white' ? 'w' : 'b';
  if (piece.charAt(0) !== myPieceColor) return false;
  if (game.turn() !== myPieceColor) return false;

  return true;
}

async function onDrop(source, target) {
  // Try promotion to queen by default
  const move = game.move({ from: source, to: target, promotion: 'q' });
  if (move === null) return 'snapback';

  locked = true;
  updateStatusText('Maia is thinking...');

  const res = await fetch('/api/move', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, move: source + target + (move.promotion || '') }),
  });

  if (!res.ok) {
    game.undo();
    board.position(game.fen());
    locked = false;
    updateStatusText('Invalid move, try again.');
    return;
  }

  const state = await res.json();

  // Sync chess.js with server state
  game.load(state.fen);
  board.position(state.fen);

  appendHistory(move.san, state.maia_move ? toSan(state.maia_move, state) : null);
  updateStatus(state);
  locked = false;
}

function onSnapEnd() {
  board.position(game.fen());
}

// ── Maia first move (player is black) ───────────────────────────
async function triggerMaiaFirst() {
  locked = true;
  updateStatusText('Maia is thinking...');

  // Send a sentinel move "maia" — server handles this by making Maia move
  // Actually we need a different approach: call a dedicated endpoint or
  // repurpose /api/move with no player move. We'll use GET /api/state to
  // check, then POST a special empty move. Since our server only has /api/move,
  // we need to call it. But we can't send a player move here.
  // Solution: add a flag on the server via query param, or just make a GET
  // to a dedicated trigger. We'll do it cleanly by fetching /api/maia_move.
  // Since that endpoint doesn't exist yet, we'll call /api/move with move=""
  // and handle it server-side. Actually — simpler: we load from state and
  // the server already made Maia move during /api/new_game if player=black.
  // Let's re-fetch state to see if Maia already moved.

  // Re-check: the server new_game returns initial state before any moves.
  // Maia hasn't moved yet. We need to trigger it.
  // We'll call a GET /api/maia_move/{session_id} — but that doesn't exist.
  // Best fix: handle it in main.py new_game response. For now, call /api/move
  // with a special "skip" that the server interprets. Instead, let's just
  // POST to /api/maia_move which we'll add to main.py.

  const res = await fetch(`/api/maia_move/${sessionId}`, { method: 'POST' });
  if (!res.ok) { locked = false; return; }

  const state = await res.json();
  game.load(state.fen);
  board.position(state.fen);

  if (state.maia_move) {
    appendHistory(null, toSan(state.maia_move, state));
  }

  updateStatus(state);
  locked = false;
}

// ── History & status ────────────────────────────────────────────
function appendHistory(playerSan, maiaSan) {
  const container = document.getElementById('move-history');
  if (playerSan) {
    moveCount++;
    const row = document.createElement('div');
    row.innerHTML = `<span style="color:#888">${moveCount}.</span> <span style="color:#e0e0e0">${playerSan}</span>`;
    container.appendChild(row);
  }
  if (maiaSan) {
    const last = container.lastElementChild;
    if (last && !last.dataset.maia) {
      last.innerHTML += ` <span style="color:#e94560">${maiaSan}</span>`;
      last.dataset.maia = '1';
    } else {
      moveCount++;
      const row = document.createElement('div');
      row.innerHTML = `<span style="color:#888">${moveCount}.</span> … <span style="color:#e94560">${maiaSan}</span>`;
      row.dataset.maia = '1';
      container.appendChild(row);
    }
  }
  container.scrollTop = container.scrollHeight;
}

function toSan(uci) {
  // chess.js SAN from UCI using current game state before the move was applied
  // We approximate: just show the UCI string if we can't derive SAN cleanly
  return uci;
}

function updateStatusText(text) {
  document.getElementById('status-bar').textContent = text;
}

function updateStatus(state) {
  if (state.is_game_over) {
    showResult(state.result);
    return;
  }
  const isMyTurn = state.turn === playerColor;
  updateStatusText(isMyTurn ? 'Your turn' : 'Maia is thinking...');
}

function formatDuration(ms) {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function showResult(result) {
  let msg;
  if (result === '1/2-1/2') {
    msg = "It's a Draw!";
  } else if (
    (result === '1-0' && playerColor === 'white') ||
    (result === '0-1' && playerColor === 'black')
  ) {
    msg = 'You Win!';
  } else {
    msg = 'Maia Wins!';
  }
  document.getElementById('result-text').textContent = msg;
  document.getElementById('stat-moves').textContent = game.history().length;
  document.getElementById('stat-duration').textContent = formatDuration(Date.now() - gameStartTime);
  document.getElementById('end-overlay').classList.remove('hidden');
  updateStatusText(msg);
}

// ── New game & resign ───────────────────────────────────────────
document.getElementById('new-game-btn').addEventListener('click', () => {
  showScreen('setup-screen');
});

document.getElementById('resign-btn').addEventListener('click', () => {
  if (locked) return;
  showResult(playerColor === 'white' ? '0-1' : '1-0');
});
