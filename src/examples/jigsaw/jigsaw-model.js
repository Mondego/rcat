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
  
  img = new Image(); // large image to be sliced for the puzzle
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
      sx = c * this.PC_W; // slice from original
      sy = r * this.PC_H;
      var p = new Piece(c, r, x, y, sx, sy, this.PC_W, this.PC_H);
      this.loosePieces.push(p);
    }
  }

  // Create the puzzle grid holding dropped pieces.
  // If a piece is dropped on the correct cell,
  // the grid "magnets" it, and the piece can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  // the whole board area

}

// Holds coordinates of a puzzle piece.
// Could be {c:5,r:6} instead of a whole Piece class.
// TODO: could have an ID given by the server instead of c,r
// (that would make cheating more annoying for puzzles with lots of pieces)
function Piece(c, r, x, y, sx, sy, sw, sh) {
  // grid coordinates, column and row
  this.c = c;
  this.r = r;
  // coords of the piece on the board
  this.x = x;
  this.y = y;
  // dimensions of the slice from the original image
  this.sx = sx;
  this.sy = sy;
  this.sw = sw;
  this.sh = sh;
  // whether the piece has been correctly placed or not
  this.bound = false;
}

// Display the puzzle in a canvas
// and translate user inputs into model commands
function View() {

  console.log
  var canvasID = "canJigsaw";
  canvas = document.getElementById(canvasID);

  this.canvas = canvas;
  var ctx = canvas.getContext('2d');

  // get click position relative to the canvas's top left corner
  // adapted from http://www.quirksmode.org/js/events_properties.html
  // TODO: this does not take into account the canvas' border thickness
  function getClickPos(e) {
    var posx = 0;
    var posy = 0;
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
    res = {
      x : posx,
      y : posy
    };
    return res;
  }

  // register canvas callbacks to mouse events
  canvas.onmousedown = function(e) {
    clickpos = getClickPos(e);
  };
  canvas.onmouseup = function(e) {
  };
  canvas.onmouseout = function(e) {
  };
  canvas.onmousemove = function(e) {
  };
  OnScroll = function(e) {
  };
  canvas.addEventListener('DOMMouseScroll', OnScroll, false); // webkit
  canvas.addEventListener('mousewheel', OnScroll, false); // non-webkit

  // display config of the grid and pieces at the same scale as the model
  var GRID = {
    OFFSETX : model.GRID_X,
    OFFSETY : model.GRID_Y,
    WIDTH : model.GRID_W,
    HEIGHT : model.GRID_H,
    BOTTOM : model.GRID_Y + model.GRID_H,
    RIGHT : model.GRID_X + model.GRID_W,
    CELLW : model.GRID_W / model.COLUMNS, // TODO: beware: what if float?
    CELLH : model.GRID_H / model.ROWS
  };

  // draw a gray grid showing where pieces can be dropped
  // TODO: for now, it draws at same scale as model
  function drawGrid() {
    ctx.strokeStyle = "#222"; // gray
    ctx.lineWidth = 1;
    ctx.beginPath();
    // draw vertical grid lines
    for ( var c = 0; c <= model.COLUMNS; c++) {
      var x = GRID.OFFSETX + c * GRID.CELLW;
      ctx.moveTo(x, GRID.OFFSETY);
      ctx.lineTo(x, GRID.BOTTOM);
    }
    // draw horizontal grid lines
    for ( var r = 0; r <= model.ROWS; r++) {
      var y = GRID.OFFSETY + r * GRID.CELLH;
      ctx.moveTo(GRID.OFFSETX, y);
      ctx.lineTo(GRID.RIGHT, y);
    }
    ctx.closePath();
    ctx.stroke();
  }

  // draw pieces that are correctly placed in the grid
  function drawBoundPieces() {
    // TODO
  }

  // draw movable pieces
  function drawLoosePieces() {
    for ( var pnum in model.loosePieces) {
      drawPiece(model.loosePieces[pnum]);
    }
  }

  // Draw a piece, whether loose or bound
  function drawPiece(p) {
    var dx = p.x;
    var dy = p.y;
    var dw = GRID.CELLW;
    var dh = GRID.CELLH;
    ctx.drawImage(model.img, p.sx, p.sy, p.sw, p.sh, dx, dy, dw, dh);

  }

  // init: draw the grid, the pieces in the grid, and the loose pieces
  drawGrid();
  // drawBoundPieces();
  drawLoosePieces();
}