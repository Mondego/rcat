// ------------------------- GLOBAL --------------------

// start by downloading the large image to be sliced for the puzzle
// TODO: async image loading instead
var img = new Image();
img.onload = function() {
  // console.log('image loaded');
  // TODO: time the image loading + async img load
};
img.src = "img/BugsLife.jpg"; // 800 x 600
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_150KB.jpg'; // 640 x 480
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_1MB.jpg'; // 1600 x 1200
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_2MB.jpg'; // 9000 x 6000
// img.src = 'http://ics.uci.edu/~tdebeauv/rCAT/diablo_150KB.jpg';

var model, view;
window.onload = function() {
  var canvas = document.getElementById("jigsaw");
  // The model tracks the game state and executes commands.
  // The model is also in charge of the network.
  // The model should be created before the view
  // so that the view can render it at init.
  model = new Model(canvas);
  // The view renders the game from the model.
  // The view is also in charge of converting user input into model commands.
  view = new View(canvas);
  model.startGame();
}

// ------------------------ MODEL --------------------------

// stores game logic and data
function Model(canvas) {

  // board = grid + empty space around the grid
  this.BOARD = {
    w : 900, // width and height of the whole board
    h : 600,
    maxScale : 8, // cap zooming in and out
    minScale : 1
  };

  // grid = where pieces can be dropped
  this.GRID = {
    x : 50, // position relative to the board
    y : 100,
    ncols : 2, // puzzle difficulty
    nrows : 2,
    cellw : 200, // cell dimensions
    cellh : 150
  };

  // Init: create the pieces.
  this.startGame = function() {
    var board = this.BOARD;
    var grid = this.GRID;
    this.loosePieces = []; // set of movable pieces
    this.boundPieces = []; // pieces that have been dropped in the correct cell
    var x, y; // coords of the piece on the board
    var sx, sy; // dimensions of the slice from the original image
    var w = grid.cellw;
    var h = grid.cellh;
    // each piece contains a pc_w x pc_h slice of the original image
    var pc_w = img.width / this.GRID.ncols;
    var pc_h = img.height / this.GRID.nrows;
    for ( var c = 0; c < grid.ncols; c++) {
      for ( var r = 0; r < grid.nrows; r++) {
        // place randomly on the board
        // x = Math.random() * (board.w - w);
        // y = Math.random() * (board.h - h);
        x = 2 * (1 - c) * grid.cellw + 100;
        y = 2 * (1 - r) * grid.cellh + 10;
        sx = c * pc_w; // coords of image sliced from original
        sy = r * pc_h;
        var p = new Piece(c, r, x, y, w, h, sx, sy, pc_w, pc_h);
        this.loosePieces.push(p);
      }
    }
    view.drawAll();
  };

  // which loose piece is currently being dragged
  this.draggedPiece = null;

  // Return a loose piece colliding with the given board coords.
  // Return null if no loose piece collides.
  // TODO: index loose pieces spatially for faster collision detection
  this.getCollidedPiece = function(x, y) {
    // iterate over all pieces
    var pnum = this.loosePieces.length - 1;
    var p;
    while (pnum >= 0) {
      p = this.loosePieces[pnum];
      if (p.collides(x, y)) {
        break;
      }
      pnum--;
    }
    if (pnum >= 0) { // at least a piece collides: prepare to drag it around
      p = this.loosePieces[pnum];
      this.draggedPiece = p;
      // TODO: view draws a shiny border around the piece to show it's selected
    }
  };

  // which part of the board is currently being viewed by the user
  this.frustum = {
    x : 0,
    y : 0,
    scale : 1, // zooming scale; >1 is zoomed in, <1 is zoomed out
    w : canvas.width,
    h : canvas.height
  };

  // fix the frustum if user scrolled past board edges
  this.keepFrustumOnBoard = function() {
    var fru = this.frustum;
    if (fru.x < 0)
      this.frustum.x = 0;
    if (fru.x + fru.w > this.BOARD.w)
      this.frustum.x = this.BOARD.w - canvas.width / fru.scale;
    if (fru.y < 0)
      this.frustum.y = 0;
    if (fru.y + fru.h > this.BOARD.h)
      this.frustum.y = this.BOARD.h - canvas.height / fru.scale;
  };

  // Pieces are moved as they are dragged (not just when they are dropped)
  // If no piece is being dragged, then slide the board.
  this.scrollRelative = function(dx, dy) {
    var p = this.draggedPiece;
    if (p) { // drag a piece around
      p.x += dx;
      p.y += dy;
      // fix eventual past-board-edges overflows
      if (p.x < 0)
        p.x = 0;
      if (p.x + p.w > this.BOARD.w)
        p.x = this.BOARD.w - p.w;
      if (p.y < 0)
        p.y = 0;
      if (p.y + p.h > this.BOARD.h)
        p.y = this.BOARD.h - p.h;
      // TODO: if piece near the board edges, scroll the board too
    } else { // scroll board in opposite direction of the mouse movement
      this.frustum.x -= dx;
      this.frustum.y -= dy;
      this.keepFrustumOnBoard();
    }
    view.drawAll();
  };

  // Scroll so that the given coordinates are at the top left of the frustum.
  this.scrollAbsolute = function(x, y) {
    this.frustum.x = x;
    this.frustum.y = y;
    this.keepFrustumOnBoard();
    view.drawAll();
  };

  // Zoom in or out
  this.zoom = function(isZoomingOut, scaleStep) {
    var scale = this.frustum.scale;
    // cap zoom-in and zoom-out
    if (isZoomingOut && scale > this.BOARD.minScale) {
      this.frustum.scale /= scaleStep;
      this.frustum.w *= scaleStep;
      this.frustum.h *= scaleStep;
    } else if (!isZoomingOut && scale < this.BOARD.maxScale) {
      this.frustum.scale *= scaleStep;
      this.frustum.w /= scaleStep;
      this.frustum.h /= scaleStep;
    } else { // reached max scale or min scale
      return;
    }
    // TODO: this is useless, since the controller will call the model again
    view.drawAll();
  };

  // If a piece is dropped on the correct cell,
  // the grid "magnets" it, and the piece becomes "bound":
  // it can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  this.release = function(x, y) {
    if (this.draggedPiece) { // stop dragging a piece
      var p = this.draggedPiece;
      this.draggedPiece = null;
      var cell = this.getCellFromPos(x, y);
      if (cell != null && cell.c == p.c && cell.r == p.r) { // correct cell
        // magnet the piece
        p.x = cell.x;
        p.y = cell.y;
        // bind the piece
        this.bindPiece(p);
        if (this.gameIsOver()) {
          // TODO: should display an animation
          this.startGame();
        }
        view.drawAll();
      }
    }
  }

  // The game is over when all the pieces are dropped on their correct cell.
  this.gameIsOver = function() {
    return this.loosePieces.length == 0;
  }

  // Bind piece: remove it from the loose pieces and add it to the bound pieces.
  this.bindPiece = function(piece) {
    var c = piece.c, r = piece.r;
    // iterate over all the pieces to find the one with that c and r
    var pnum = this.loosePieces.length - 1;
    var p;
    while (pnum >= 0) {
      p = model.loosePieces[pnum];
      if (p == piece) {
        break;
      }
      pnum--;
    }
    if (pnum >= 0) { // the piece was found in the loose pieces
      this.loosePieces.splice(pnum, 1);
      this.boundPieces.push(p);
    } else {
      console.log('Error in model.bindPiece: piece not found in loosePieces');
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
function Piece(c, r, x, y, w, h, sx, sy, sw, sh) {

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

  // whether the piece has been correctly placed or not
  this.bound = false;

  // whether a click (x,y) collides with the piece
  this.collides = function(x, y) {
    return x >= this.x && x <= this.x + this.w && y >= this.y
        && y <= this.y + this.h
  };
}
