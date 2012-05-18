var model, view;

window.onload = function() {
  // The model tracks the game state and executes commands.
  // The model is also in charge of the network.
  // The model should be created before the view
  // so that the view can render it at init.
  model = new Model();
  // The view renders the game from the model.
  // The view is also in charge of converting user input into model commands.
  view = new View();
}

// stores game logic and data
function Model() {

  // game areas: board = grid + empty space around the grid
  this.BOARD_W = 800, this.BOARD_H = 600;
  // grid = where pieces can be dropped
  this.GRID_X = 50, this.GRID_Y = 50;
  this.GRID_W = 400, this.GRID_H = 300;

  // puzzle difficulty
  this.ROWS = 2, this.COLUMNS = 2; // simple 2-by-2 puzzle, 4 pieces
  this.CELL_W = this.GRID_W / this.ROWS; // TODO: beware: what if float?
  this.CELL_H = this.GRID_H / this.COLUMNS;

  var img = new Image(); // large image to be sliced for the puzzle
  img.src = "img/BugsLife.jpg"; // 800 x 600 px
  this.img = img;
  // each piece contains PC_W x PC_H from the original image
  this.PC_W = img.width / this.COLUMNS;
  this.PC_H = img.height / this.ROWS;

  // Create the pieces.
  this.loosePieces = []; // set of movable pieces
  this.boundPieces = []; // pieces that have been dropped in the correct cell
  var x, y; // coords of the piece on the board
  var sx, sy; // dimensions of the slice from the original image
  for ( var c = 0; c < this.COLUMNS; c++) {
    for ( var r = 0; r < this.ROWS; r++) {
      x = Math.random() * (this.BOARD_W - this.PC_W);
      y = Math.random() * (this.BOARD_H - this.PC_H);
      w = this.GRID_W / this.COLUMNS;
      h = this.GRID_H / this.ROWS;
      sx = c * this.PC_W; // slice from original
      sy = r * this.PC_H;
      var p = new Piece(c, r, x, y, w, h, sx, sy, this.PC_W, this.PC_H);
      this.loosePieces.push(p);
    }
  }

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
      return p;
    } else { // no piece collides: prepare to translate the board
      return null;
    }
  }

  // which loose piece is currently being dragged
  this.draggedPiece = null;

  // Pieces are moved as they are dragged (not just when they are dropped)
  // If no piece is being dragged, then slide the board.
  this.dragRelative = function(dx, dy) {
    var p = this.draggedPiece;
    if (p) { // drag a piece around
      p.x = p.x + dx;
      p.y = p.y + dy;
    } else { // no piece is being dragged: translate the board
      // TODO
    }
    view.drawAll();
  }

  // If a piece is dropped on the correct cell,
  // the grid "magnets" it, and the piece becomes "bound":
  // it can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  this.dropPiece = function(x, y) {
    // stop dragging
    var p = this.draggedPiece;
    this.draggedPiece = null;
    var cell = this.getCellFromPos(x, y);
    if (cell != null && cell.c == p.c && cell.r == p.r) { // correct cell
      // magnet the piece
      p.x = cell.x;
      p.y = cell.y;
      // bind the piece
      this.bindPiece(p);
      view.drawAll();
    }
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
    var col = Math.floor((mousex - this.GRID_X) / this.CELL_W);
    var row = Math.floor((mousey - this.GRID_Y) / this.CELL_H);
    var res = null;
    if (col >= 0 && col < this.COLUMNS && row >= 0 && row < this.ROWS) {
      var cellx = this.GRID_X + this.CELL_W * col;
      var celly = this.GRID_Y + this.CELL_H * row;
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
  }
}

// -------------------------- VIEW ----------------------------------

// Display the puzzle in a canvas
// and translate user inputs into model commands
function View() {

  // private vars
  var canvasID = "canJigsaw";
  var canvas = document.getElementById(canvasID);
  var ctx = canvas.getContext('2d');
  var view = this; // in canvas callbacks, 'this' is the canvas, not the view

  this.dragStartx = null;
  this.dragStarty = null;

  // register canvas callbacks to mouse events
  // left click to select a piece or drag the board
  canvas.onmousedown = function(e) {
    // TODO: what about right clicks? http://stackoverflow.com/a/322827/856897
    // view.mousedown = true;
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos.x, screenPos.y); // screen to model coords
    var p = model.getCollidedPiece(pos.x, pos.y);
    // modes such as "dragging a piece" or "sliding the board"
    // are stored in the model
    if (p) { // piece is selected
      // remember initial screen dragging position
      view.dragStartx = pos.x;
      view.dragStarty = pos.y;
    } else { // TODO: drag the board
    }
    // TODO: draw a shiny border around the piece to show it is selected
  };

  canvas.onmouseup = function(e) {
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos.x, screenPos.y); // screen to model coords
    // release the piece where the user mouseupped
    model.dropPiece(pos.x, pos.y);
    view.dragStartx = null;
    view.dragStarty = null;
  };

  canvas.onmousemove = function(e) {
    var screenPos = getScreenPos(e);
    // convert screen coords to model coords
    var pos = toBoardPos(screenPos.x, screenPos.y);
    var dx = pos.x - view.dragStartx;
    var dy = pos.y - view.dragStarty;
    // reset the dragging origin
    view.dragStartx = pos.x;
    view.dragStarty = pos.y;
    model.dragRelative(dx, dy);
  };

  canvas.onmouseout = function(e) {
  };

  function onmousewheel(e) {
  }
  canvas.addEventListener('DOMMouseScroll', onmousewheel, false); // FF
  canvas.addEventListener('mousewheel', onmousewheel, false); // Chrome, IE

  // get click position relative to the canvas's top left corner
  // adapted from http://www.quirksmode.org/js/events_properties.html
  // TODO: this does not take into account the canvas' border thickness
  function getScreenPos(e) {
    var posx;
    var posy;
    if (!e)
      var e = window.event;
    if (e.pageX || e.pageY) {
      posx = e.pageX - canvas.offsetLeft;
      posy = e.pageY - canvas.offsetTop;
    } else if (e.clientX || e.clientY) {
      posx = e.clientX + document.body.scrollLeft
          + document.documentElement.scrollLeft - canvas.offsetLeft;
      posy = e.clientY + document.body.scrollTop
          + document.documentElement.scrollTop - canvas.offsetTop;
    } else {
      console.log('Error: event did not contain mouse position.')
    }
    var res = {
      x : posx,
      y : posy
    };
    return res;
  }

  // Convert screen coordinates to board coordinates.
  // TODO: Should take into account translations.
  // TODO: Should take into account zooming.
  function toBoardPos(x, y) {
    var res = {
      x : x,
      y : y
    };
    return res;
  }
  // The reverse of above: convert board coords to screen coords.
  function toScreenPos(x, y) {
    var res = {
      x : x,
      y : y
    };
    return res;
  }

  // ---------------------- VIEW ------------------------------

  // config of the board, grid, and pieces at the same scale as the model
  // TODO: should be in toScreenPos?

  var CFG = {
    OFFSETX : model.GRID_X,
    OFFSETY : model.GRID_Y,
    GRID_BOTTOM : model.GRID_Y + model.GRID_H,
    GRID_RIGHT : model.GRID_X + model.GRID_W,
    CELL_W : model.CELL_W,
    CELL_H : model.CELL_H,
    BOARD_W : model.BOARD_W,
    BOARD_H : model.BOARD_H
  };

  // draw a gray grid showing where pieces can be dropped
  // TODO: for now, it draws at same scale as model
  function drawGrid() {
    ctx.save();
    ctx.strokeStyle = "#222"; // gray
    ctx.lineWidth = 1;
    ctx.beginPath();
    // draw vertical grid lines
    for ( var c = 0; c <= model.COLUMNS; c++) {
      var x = CFG.OFFSETX + c * CFG.CELL_W;
      ctx.moveTo(x, CFG.OFFSETY);
      ctx.lineTo(x, CFG.GRID_BOTTOM);
    }
    // draw horizontal grid lines
    for ( var r = 0; r <= model.ROWS; r++) {
      var y = CFG.OFFSETY + r * CFG.CELL_H;
      ctx.moveTo(CFG.OFFSETX, y);
      ctx.lineTo(CFG.GRID_RIGHT, y);
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }

  // draw pieces that are correctly placed in the grid
  function drawBoundPieces() {
    var p;
    for ( var pnum in model.boundPieces) {
      p = model.boundPieces[pnum];
      drawPiece(p);
    }
  }

  // draw movable pieces
  function drawLoosePieces() {
    var p;
    for ( var pnum in model.loosePieces) {
      p = model.loosePieces[pnum];
      drawPiece(p);
    }
  }

  // Draw a piece, whether loose or bound
  function drawPiece(p) {
    var dx = p.x;
    var dy = p.y;
    var dw = CFG.CELL_W;
    var dh = CFG.CELL_H;
    ctx.save();
    ctx.drawImage(model.img, p.sx, p.sy, p.sw, p.sh, dx, dy, dw, dh);
    ctx.restore();
  }

  // draw everything in this order: grid, bound pieces, and loose pieces
  // public method of view so that model can call it
  this.drawAll = function() {
    ctx.clearRect(0, 0, CFG.BOARD_W, CFG.BOARD_H);
    drawGrid();
    drawBoundPieces();
    drawLoosePieces();
  }

  // init: draw everything
  this.drawAll();
}