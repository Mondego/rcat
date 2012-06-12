// ------------------------- GLOBAL --------------------

// start by downloading the large image to be sliced for the puzzle
// TODO: async image loading instead
var IMG = new Image();
IMG.onload = function() {
  // console.log('image loaded');
  // TODO: time the image loading + async img load
};
// img.src = "img/BugsLife.jpg"; // 800 x 600
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_150KB.jpg'; // 640 x 480
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_1MB.jpg'; // 1600 x 1200
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_2MB.jpg'; // 9000 x 6000
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_150KB.jpg';

var model, view, nw;
var canvas;

window.onload = function() {
  canvas = document.getElementById("jigsaw");
  model = new Model();
  view = new View();
  nw = new Network();
}

// ------------------------ MODEL --------------------------

// stores game logic and data
function Model() {

  this.BOARD = {// board = grid + empty space around the grid
    w : null,
    h : null,
    maxScale : null,
    minScale : null
  };
  this.GRID = { // grid = where pieces can be dropped
    x : null,
    y : null,
    ncols : null,
    nrows : null,
    cellw : null,
    cellh : null
  };
  this.myid = null; // the id given by the server to represent me

  // which part of the board is currently being viewed by the user
  this.frustum = {
    x : null,
    y : null,
    scale : null, // zooming scale; >1 is zoomed in, <1 is zoomed out
    w : null,
    h : null
  };

  // Frustum primitive.
  // Fix the frustum if user scrolled past board edges
  this.keepFrustumOnBoard = function() {
    var fru = this.frustum;
    // canvas dimensions in board coords
    var cdims = view.toBoardDims(canvas.width, canvas.height);
    // horizontally
    var tooLeft = fru.x < 0;
    var tooRight = fru.x + fru.w > this.BOARD.w;
    if (tooLeft && !tooRight)
      this.frustum.x = 0;
    else if (tooRight && !tooLeft)
      this.frustum.x = this.BOARD.w - cdims.w;
    // vertically
    var tooHigh = fru.y < 0;
    var tooLow = fru.y + fru.h > this.BOARD.h;
    if (tooHigh && !tooLow)
      this.frustum.y = 0;
    else if (tooLow && !tooHigh)
      this.frustum.y = this.BOARD.h - cdims.h;
  };

  // A frustum primitive.
  // Shift the frustum's topleft by the given offset.
  this.scrollRelative = function(dx, dy) {
    this.frustum.x -= dx;
    this.frustum.y -= dy;
    this.keepFrustumOnBoard();
  };

  // A frustum primitive.
  // Position the frustum's topleft at the given board coords.
  this.scrollAbsolute = function(x, y) {
    this.frustum.x = x;
    this.frustum.y = y;
    this.keepFrustumOnBoard();
  };

  // A frustum primitive. Zoom in/out by the given factor.
  // Maintain zoom within the board's min/max zooming scales.
  // Return true if a zoom was actually performed.
  this.zoom = function(isZoomingOut, factor) {
    if (isZoomingOut && this.frustum.scale > this.BOARD.minScale) {
      this.frustum.scale /= factor;
      this.frustum.w *= factor;
      this.frustum.h *= factor;
    } else if (!isZoomingOut && this.frustum.scale < this.BOARD.maxScale) {
      this.frustum.scale *= factor;
      this.frustum.w /= factor;
      this.frustum.h /= factor;
    }
  };

  // Init board, grid, and frustum from server config.
  // Also create the pieces from server data.
  this.startGame = function(board, grid, dfrus, piecesData, myid) {

    this.BOARD = board;
    this.GRID = grid;
    this.myid = myid;

    // Send back the frustum's w and h to the server,
    // as they are determined by the client's canvas size.
    this.frustum.x = dfrus.x;
    this.frustum.y = dfrus.y;
    this.frustum.scale = dfrus.scale;
    var dims = view.toBoardDims(canvas.width, canvas.height);
    this.frustum.w = dims.w;
    this.frustum.h = dims.h;
    nw.sendFrustum(this.frustum);

    // piece creations
    this.loosePieces = {}; // hash table of movable pieces
    this.boundPieces = {}; // pieces that have been dropped in the correct cell
    var x, y; // coords of the piece on the board
    var sx, sy; // dimensions of the slice from the original image
    var w = grid.cellw;
    var h = grid.cellh;
    // each piece contains a sw x sh slice of the original image
    var sw = IMG.width / grid.ncols;
    var sh = IMG.height / grid.nrows;
    var pdata, p, sx, sy;
    for ( var id in piecesData) {
      pd = piecesData[id];
      sx = pd.c * sw; // coords of image sliced from original
      sy = pd.r * sh;
      p = new Piece(id, pd.b, pd.c, pd.r, pd.x, pd.y, w, h, sx, sy, sw, sh);
      this.loosePieces[id] = p;
    }
    view.drawAll();
  };

  // -------- COMMANDS ISSUED BY THE CONTROLLER --------------

  // which loose piece is currently being dragged
  this.draggedPiece = null;

  // Select a piece that collides with the click coords.
  // The piece must not be already owned by someone else.
  // TODO: index loose pieces spatially for faster collision detection
  this.selectPieceAt = function(x, y) {
    var p;
    var found = false;
    // iterate over all pieces
    for ( var pid in this.loosePieces) {
      p = this.loosePieces[pid];
      if (p.collides(x, y) && (!p.isLocked())) {
        found = true;
        break;
        // TODO: get the piece that collides with highest z-index
      }
    }
    if (found) // at least one free piece collides: prepare to drag it around
      this.draggedPiece = p;
  };

  // Drag a piece locally, and send the move to the server.
  // TODO: if piece near the board edges, scroll the board too
  this.dragMyPiece = function(dx, dy) {
    var p = this.draggedPiece;
    p.moveRelative(dx, dy);
    nw.sendPieceMove(p.id, p.x, p.y);
    view.drawAll();
  };

  // Scroll the board in opposite direction of the mouse movement.
  this.moveBoardRelative = function(dx, dy) {
    this.scrollRelative(dx, dy);
    nw.sendFrustum(this.frustum);
    view.drawAll();
  };

  // Zoom in/out on the given screen coord.
  // Called by the view (hence, it's NOT a frustum primitive).
  this.zoomOnScreenPoint = function(isZoomingOut, factor, sPos) {
    var bPos = view.toBoardPos(sPos);
    this.zoom(isZoomingOut, factor);
    var offset = view.toBoardDims(sPos.x, sPos.y);
    model.scrollAbsolute(bPos.x - offset.w, bPos.y - offset.h);
    nw.sendFrustum(this.frustum);
    view.drawAll();
  };

  // If a piece is dropped on the correct cell, the grid "magnets" it,
  // and the piece becomes "bound": it can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  this.dropMyPiece = function(x, y) {
    var p = this.draggedPiece;
    var bound = false; // whether the piece becomes bound
    this.draggedPiece = null;
    var cell = this.getCellFromPos(x, y); // or p.x + p.w/2 instead? or both?
    if (cell != null && cell.c == p.c && cell.r == p.r) { // correct cell
      bound = true;
      p.x = cell.x; // magnet the piece
      p.y = cell.y;
      delete this.loosePieces[p.id]; // bind piece
      this.boundPieces[p.id] = p;
    }
    nw.sendPieceDrop(p.id, p.x, p.y, bound);
    view.drawAll();
  };

  // Return cell (grid col+row, board x+y) from board coords.
  // Return null if out of grid.
  this.getCellFromPos = function(mousex, mousey) {
    var grid = this.GRID;
    var col = Math.floor((mousex - grid.x) / grid.cellw);
    var row = Math.floor((mousey - grid.y) / grid.cellh);
    var res = null;
    if (col >= 0 && col < grid.ncols && row >= 0 && row < grid.nrows) {
      var cellx = grid.x + grid.cellw * col;
      var celly = grid.y + grid.cellh * row;
      res = {
        c : col,
        r : row,
        x : cellx,
        y : celly
      };
    }
    return res;
  };

  // The game is over when all the pieces are dropped on their correct cell.
  this.gameIsOver = function() {
    return this.loosePieces == {};
  };

  // ------------- COMMANDS ISSUED BY THE NETWORK -----------

  // Drop a piece at a given position.
  // If I was dragging the piece, but did not own it, then stop dragging it.
  // We dont care about messages about me since my local version is more recent.
  this.dropRemotePiece = function(id, x, y, bound, owner) {
    if (owner != this.myid) {
      if (this.draggedPiece && this.draggedPiece.id == id) {
        this.draggedPiece = null; // stop dragging
        // TODO: display an effect?
      } else {
        var p = this.loosePieces[id];
        p.x = x;
        p.y = y;
        p.owner = null;
      }
      view.drawAll();
    }
  };

  // Move a piece to a given position IF the lock owner is not me.
  // We dont care about messages about me since my local version is more recent.
  this.moveRemotePiece = function(id, x, y, owner) {
    if (owner != this.myid) {
      if (this.draggedPiece && this.draggedPiece.id == id) {
        this.draggedPiece = null; // stop dragging
        // TODO: display an effect?
      } else {
        var p = this.loosePieces[id];
        p.x = x;
        p.y = y;
        p.owner = owner;
      }
      view.drawAll(); // TODO: redraw only if piece was or is in the frustum
    }
  };

} // end of model

// Holds coordinates of a puzzle piece.
// Could be an object {c:5,r:6} instead of a whole Piece class.
// TODO: could have an ID given by the server instead of c,r
// (that would make cheating more annoying for puzzles with lots of pieces)
function Piece(id, b, c, r, x, y, w, h, sx, sy, sw, sh) {

  this.id = id; // id
  this.owner = null; // player currently dragging (and locking) the piece

  // whether the piece has been correctly placed or not
  this.bound = b;

  // grid coordinates, column and row
  this.c = c;
  this.r = r;

  // coords and dimensions of the piece on the board
  this.x = x;
  this.y = y;
  this.w = w;
  this.h = h;

  // dimensions of the slice from the original image
  this.sx = sx;
  this.sy = sy;
  this.sw = sw;
  this.sh = sh;

  // whether a click (x,y) collides with the piece
  this.collides = function(x, y) {
    return x >= this.x && x <= this.x + this.w && y >= this.y
        && y <= this.y + this.h
  };

  // return whether the piece is currently being dragged by someone else
  this.isLocked = function() {
    return (this.owner && this.owner == model.myid);
  }

  // drag a piece to the given coords, making sure it stays on the board
  this.moveRelative = function(dx, dy) {
    this.x += dx;
    this.y += dy;
    // fix eventual past-board-edges overflows
    if (this.x < 0)
      this.x = 0;
    if (this.x + this.w > model.BOARD.w)
      this.x = model.BOARD.w - this.w;
    if (this.y < 0)
      this.y = 0;
    if (this.y + this.h > model.BOARD.h)
      this.y = model.BOARD.h - this.h;
  };
}
