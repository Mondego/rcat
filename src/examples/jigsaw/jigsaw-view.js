// -------------------------- VIEW + CONTROLLER -----------------------------

// Display the puzzle in a canvas
// and translate user inputs into model commands
function View(canvas) {

  // ------------------ MOUSE CONTROLLER ------------------

  // Convert screen coordinates to board coordinates.
  // Takes into account board translation and zooming.
  // When zoomed-in by 2, a point at 100px from the left of the screen
  // is actually at 50 model-units from it.
  function toBoardPos(pos) {
    var frus = model.frustum;
    var res = {
      x : (pos.x / frus.scale) + frus.x,
      y : (pos.y / frus.scale) + frus.y
    };
    return res;
  }

  // The reverse of above: convert board coords to screen coords.
  function toScreenPos(x, y) {
    var frus = model.frustum;
    var res = {
      x : (x - frus.x) * frus.scale,
      y : (y - frus.y) * frus.scale
    };
    return res;
  }

  this.isMouseDown = false;
  this.dragStart = null; // last position recorded when dragging the mouse
  var view = this; // in canvas callbacks, 'this' is the canvas, not the view

  // register canvas callbacks to mouse events
  canvas.onmousedown = function(e) {
    // TODO: what about right clicks? http://stackoverflow.com/a/322827/856897
    view.isMouseDown = true;
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos); // screen to model coords
    model.getCollidedPiece(pos.x, pos.y);
    // store dragging start position
    view.dragStart = {
      x : pos.x,
      y : pos.y
    };
  };

  canvas.onmouseup = function(e) {
    view.isMouseDown = false;
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos); // screen to model coords
    // release the piece where the user mouse-upped
    model.release(pos.x, pos.y);
    view.dragStart = null;
  };

  // Don't redraw the canvas if the mouse moved but was not down.
  // The modes "drag a piece" or "slide the board" are in the model logic;
  // For the view, it's only about mouse movement.
  canvas.onmousemove = function(e) {
    if (view.isMouseDown) {
      var screenPos = getScreenPos(e);
      var pos = toBoardPos(screenPos); // screen to model coords
      var dx = pos.x - view.dragStart.x;
      var dy = pos.y - view.dragStart.y;
      model.dragRelative(dx, dy); // shift the model's frustum
      // board moved => need to recompute mouse-to-board coords in new frustum
      pos = toBoardPos(screenPos);
      view.dragStart = {
        x : pos.x,
        y : pos.y
      };
    }
  };

  canvas.onmouseout = function(e) {
    view.isMouseDown = false;
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos); // screen to model coords
    model.release(pos.x, pos.y);
  };

  this.scaleStep = 2; // how smooth is the zooming-in and out

  function onmousewheel(e) {
    e.preventDefault(); // dont scroll the window
    // detail for FF, wheelDelta for Chrome and IE
    var scroll = e.wheelDelta || e.detail; // < 0 means forward/up, > 0 is down
    var isZoomingOut = scroll > 0; // boolean
    var screenPos = getScreenPos(e);
    var pos = toBoardPos(screenPos); // screen to model coords
    model.zoom(isZoomingOut, view.scaleStep);
    var frus = model.frustum;
    var newx = pos.x - screenPos.x / frus.scale;
    var newy = pos.y - screenPos.y / frus.scale;
    model.scrollTo(newx, newy);
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

  // ---------------------- VIEW ------------------------------

  var ctx = canvas.getContext('2d');

  // draw a white board background
  function drawBoard() {
    ctx.save();
    ctx.fillStyle = '#fff';
    var scale = model.frustum.scale;
    var topleft = toScreenPos(0, 0);
    var w = model.BOARD.w * scale;
    var h = model.BOARD.h * scale;
    ctx.fillRect(topleft.x, topleft.y, w, h)
    ctx.restore();
  }

  // draw a gray grid showing where pieces can be dropped
  function drawGrid() {
    var grid = model.GRID;
    ctx.save();
    ctx.strokeStyle = "#222"; // gray
    ctx.lineWidth = 1;
    ctx.beginPath();
    var screenPos;
    // draw vertical grid lines
    var grid_bottom = grid.y + grid.nrows * grid.cellh;
    for ( var c = 0; c <= grid.ncols; c++) {
      var x = grid.x + c * grid.cellw;
      screenPos = toScreenPos(x, grid.y);
      ctx.moveTo(screenPos.x, screenPos.y);
      screenPos = toScreenPos(x, grid_bottom);
      ctx.lineTo(screenPos.x, screenPos.y);
    }
    // draw horizontal grid lines
    var grid_right = grid.x + grid.ncols * grid.cellw;
    for ( var r = 0; r <= grid.nrows; r++) {
      var y = grid.y + r * grid.cellh;
      screenPos = toScreenPos(grid.x, y);
      ctx.moveTo(screenPos.x, screenPos.y);
      screenPos = toScreenPos(grid_right, y);
      ctx.lineTo(screenPos.x, screenPos.y);
    }
    ctx.closePath();
    ctx.stroke();
    ctx.restore();
  }

  // draw pieces that are correctly placed in the grid (bound pieces)
  // and draw pieces that are movable (loose pieces)
  function drawPieces() {
    var p;
    for ( var pnum in model.boundPieces) {
      p = model.boundPieces[pnum];
      drawPiece(p);
    }
    for ( var pnum in model.loosePieces) {
      p = model.loosePieces[pnum];
      drawPiece(p);
    }
  }

  // Draw a piece, whether loose or bound
  function drawPiece(p) {
    var grid = model.GRID;
    var dest = toScreenPos(p.x, p.y);
    var destBotRight = toScreenPos(p.x + grid.cellw, p.y + grid.cellh);
    var dw = destBotRight.x - dest.x;
    var dh = destBotRight.y - dest.y;
    ctx.save();
    ctx.drawImage(img, p.sx, p.sy, p.sw, p.sh, dest.x, dest.y, dw, dh);
    ctx.restore();
  }

  // first clean the whole canvas,
  // then draw in this order: grid, bound pieces, and loose pieces
  // public method of view so that model can call it
  this.drawAll = function() {
    var w = ctx.canvas.width;
    var h = ctx.canvas.height;
    ctx.fillStyle = '#000'; // black
    ctx.fillRect(0, 0, w, h);
    drawBoard();
    drawGrid();
    drawPieces();
  };

}