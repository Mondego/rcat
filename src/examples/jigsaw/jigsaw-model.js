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
      }
    }
    if (found) {// at least one free piece collides: prepare to drag it around
      this.draggedPiece = p;
    }
  };

  // fix the frustum if user scrolled past board edges
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

  // Pieces are moved as they are dragged (not just when they are dropped)
  // If no piece is being dragged, then slide the board.
  this.scrollRelative = function(dx, dy) {
    var p = this.draggedPiece;
    if (p) { // drag the piece around
      p.moveRelative(dx, dy);
      // TODO: if piece near the board edges, scroll the board too
    } else { // scroll board in opposite direction of the mouse movement
      this.frustum.x -= dx;
      this.frustum.y -= dy;
      this.keepFrustumOnBoard();
      nw.sendFrustum(this.frustum);
    }
    view.drawAll();
  };

  // Scroll so that the given coordinates are at the top left of the frustum.
  this.scrollAbsolute = function(x, y) {
    this.frustum.x = x;
    this.frustum.y = y;
    this.keepFrustumOnBoard();
    nw.sendFrustum(this.frustum); // TODO: should happen in zoom
    view.drawAll();
  };

  // Cap zoom-in and zoom-out
  this.zoom = function(isZoomingOut, scaleStep) {
    if (isZoomingOut && this.frustum.scale > this.BOARD.minScale) {
      this.frustum.scale /= scaleStep;
      this.frustum.w *= scaleStep;
      this.frustum.h *= scaleStep;
    } else if (!isZoomingOut && this.frustum.scale < this.BOARD.maxScale) {
      this.frustum.scale *= scaleStep;
      this.frustum.w /= scaleStep;
      this.frustum.h /= scaleStep;
    } else { // reached max scale or min scale
      return;
    }
    // TODO: this is useless, since the controller will call the model again
    // TODO: should ask to send frustum to server?
    view.drawAll();
  };

  // If a piece is dropped on the correct cell,
  // the grid "magnets" it, and the piece becomes "bound":
  // it can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  this.release = function(x, y) {
    if (this.draggedPiece) { // stop dragging a piece
      var p = this.draggedPiece;
      nw.sendPieceDrop(p.id, p.x, p.y); // TODO: send msg when dropped?
      this.draggedPiece = null;
      var cell = this.getCellFromPos(x, y);
      if (cell != null && cell.c == p.c && cell.r == p.r) { // correct cell
        // magnet the piece
        // TODO: this should happen on the server instead
        // p.x = cell.x;
        // p.y = cell.y;
        // bind the piece
        // this.bindPiece(p);
        if (this.gameIsOver()) {
          // TODO: should display an animation
          // this.startGame(); // TODO: should come from the server
        }
        view.drawAll();
      }
    }
  }

  // The game is over when all the pieces are dropped on their correct cell.
  this.gameIsOver = function() {
    return this.loosePieces == {};
  }

  // Bind piece: remove it from the loose pieces and add it to the bound pieces.
  // TODO: should happen on the server side
  this.bindPiece = function(piece) {
    delete this.loosePieces[piece.id];
    this.boundPieces[piece.id] = piece;
  }

  // Move a piece to a given position IF the lock owner is not me.
  // We dont care about messages about me since my local version is more recent.
  this.movePiece = function(id, x, y, owner) {
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
  }

  // Drop a piece at a given position.
  // If I was dragging the piece, but did not own it, then stop dragging it.
  // We dont care about messages about me since my local version is more recent.
  this.dropPiece = function(id, x, y, owner) {
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
  }

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
    nw.sendPieceMove(this.id, this.x, this.y);
  }
}
