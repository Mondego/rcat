// -------------------------- VIEW + CONTROLLER -----------------------------

// Display the puzzle in a canvas
// and translate user inputs into model commands
function View() {

  // ------------------ MOUSE CONTROLLER ------------------

  // Convert screen coordinates to board coordinates.
  // Takes into account board translation and zooming.
  // When zoomed-in by 2, a point at 100px from the left of the screen
  // is actually at 50 model-units from it.
  this.toBoardPos = function(pos) {
    var frus = model.frustum;
    var res = {
      x : (pos.x / frus.scale) + frus.x,
      y : (pos.y / frus.scale) + frus.y
    };
    return res;
  }

  // The reverse of above: convert board coords to screen coords.
  this.toScreenPos = function(x, y) {
    var frus = model.frustum;
    var res = {
      x : (x - frus.x) * frus.scale,
      y : (y - frus.y) * frus.scale
    };
    return res;
  }

  // Convert boards dimensions (height, width) into screen dimensions
  this.toScreenDims = function(w, h) {
    var frus = model.frustum;
    var res = {
      w : w * frus.scale,
      h : h * frus.scale
    };
    return res;
  }

  this.toBoardDims = function(w, h) {
    var frus = model.frustum;
    var res = {
      w : w / frus.scale,
      h : h / frus.scale
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
    var pos = view.toBoardPos(screenPos); // screen to model coords
    model.selectPieceAt(pos.x, pos.y);
    // store dragging start position
    view.dragStart = {
      x : pos.x,
      y : pos.y
    };
  };

  // mouseup = drop piece or stop dragging
  canvas.onmouseup = function(e) {
    view.isMouseDown = false;
    var sPos = getScreenPos(e);
    if (model.draggedPiece) {
      var bPos = view.toBoardPos(sPos);
      model.dropMyPiece(bPos.x, bPos.y); // drop the piece
    }
    view.dragStart = null; // stop dragging board or piece
  };

  // Don't redraw the canvas if the mouse moved but was not down.
  // The modes "drag a piece" or "slide the board" are in the model logic;
  // For the view, it's only about mouse movement.
  canvas.onmousemove = function(e) {
    var screenPos = getScreenPos(e);
    if (view.isMouseDown) {
      var pos = view.toBoardPos(screenPos); // screen to model coords
      var dx = pos.x - view.dragStart.x;
      var dy = pos.y - view.dragStart.y;
      if (model.draggedPiece) // a piece is being dragged
        model.dragMyPiece(dx, dy);
      else
        model.moveBoardRelative(dx, dy); // shift the board
      // in both cases: the mouse moved => recompute the dragging origin
      pos = view.toBoardPos(screenPos);
      view.dragStart = {
        x : pos.x,
        y : pos.y
      };
    }
  };

  canvas.onmouseout = function(e) {
    view.isMouseDown = false;
    var sPos = getScreenPos(e);
    if (model.draggedPiece) {
      var bPos = view.toBoardPos(sPos);
      model.dropMyPiece(bPos.x, bPos.y); // drop the piece
    }
    view.dragStart = null; // stop dragging board or piece
  };

  this.scaleStep = 1.5; // how smooth is the zooming-in and out

  function onmousewheel(e) {
    e.preventDefault(); // dont scroll the window
    // detail for FF, wheelDelta for Chrome and IE
    var scroll = -e.wheelDelta || e.detail; // < 0 means forward/up, > 0 is down
    var isZoomingOut = scroll > 0;
    var screenPos = getScreenPos(e);
    model.zoomOnScreenPoint(isZoomingOut, view.scaleStep, screenPos);
  }
  canvas.addEventListener('DOMMouseScroll', onmousewheel, false); // FF
  canvas.addEventListener('mousewheel', onmousewheel, false); // Chrome, IE

  var keyScrollOffset = 50; // how many px of the screen to scroll when keydown
  // Use arrows or WASD to scroll the board.
  // For canvas.onkeydown, the canvas should get focus first.
  // See http://stackoverflow.com/questions/10562092/gaining-focus-on-canvas
  // keydown is repeatedly fired if user keeps pressing the key
  document.onkeydown = function(e) {
    // see http://stackoverflow.com/questions/1444477/keycode-and-charcode
    e = e || window.event;
    var keyCode = e.keyCode;
    var dx = 0, dy = 0;
    switch (keyCode) {
    case (87): // w
    case (38): // up arrow
      dy = view.toBoardDims(0, keyScrollOffset).h
      break;
    case (65): // a
    case (37): // left arrow
      dx = view.toBoardDims(keyScrollOffset, 0).w
      break;
    case (83): // s
    case (40): // down arrow
      dy = -view.toBoardDims(0, keyScrollOffset).h
      break;
    case (68): // d
    case (39): // right arrow
      dx = -view.toBoardDims(keyScrollOffset, 0).w
      break;
    }
    // Make the (eventual) piece being dragged follow the mouse
    // only if the board actually scrolled.
    // TODO: this needs debugging
    /*
    if (model.draggedPiece) {
      var oldbPos = view.toBoardPos(view.mousePos);
      model.moveBoardRelative(dx, dy);
      var newbPos = view.toBoardPos(view.mousePos);
      // pdx < dx if the frustum was near the side of the board
      // pdx = 0 if the frustum was exactly on the side
      var pdx = newbPos.x - oldbPos.x;
      var pdy = newbPos.y - oldbPos.y;
      model.dragMyPiece(pdx, pdy);
    } else {
      // no piece dragged: only scroll the board
      model.moveBoardRelative(dx, dy);
    }
    */
    model.moveBoardRelative(dx, dy);

  }

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

  // background image
  var BGIMG = new Image();
  BGIMG.src = "img/wood004.jpg";

  var BGIMGLOADED = false
  BGIMG.onload = function() {
    BGIMGLOADED = true
    console.log('bgimage loaded');
  };
  // "http://static1.grsites.com/archive/textures/wood/wood004.jpg";
  // wooden background from http://www.grsites.com/terms/
  // TODO: img.onload

  // draw the background
  function drawBoard() {
    ctx.save();
    var pattern = ctx.createPattern(BGIMG, 'repeat');
    ctx.fillStyle = pattern;
    // ctx.fillStyle = '#def'; // light blue
    var pos = view.toScreenPos(0, 0);
    var dims = view.toScreenDims(model.BOARD.w, model.BOARD.h);
    ctx.fillRect(pos.x, pos.y, dims.w, dims.h);
    ctx.restore();
  }

  // draw a gray grid showing where pieces can be dropped
  function drawGrid() {
    var g = model.GRID;
    ctx.save();
    // draw background image
    var pos = view.toScreenPos(g.x, g.y);
    var dims = view.toScreenDims(g.cellw * g.ncols, g.cellh * g.nrows);
    var w = dims.w, h = dims.h;
    ctx.fillStyle = '#fff';
    ctx.fillRect(pos.x, pos.y, dims.w, dims.h);
    ctx.globalAlpha = 0.2; // transparency
    ctx.drawImage(IMG, 0, 0, IMG.width, IMG.height, pos.x, pos.y, w, h);
    ctx.globalAlpha = 1;
    // draw grid lines
    ctx.strokeStyle = "#222"; // gray
    ctx.lineWidth = 1;
    ctx.beginPath();
    var screenPos;
    // draw vertical grid lines
    var grid_bottom = g.y + g.nrows * g.cellh;
    for ( var c = 0; c <= g.ncols; c++) {
      var x = g.x + c * g.cellw;
      screenPos = view.toScreenPos(x, g.y);
      ctx.moveTo(screenPos.x, screenPos.y);
      screenPos = view.toScreenPos(x, grid_bottom);
      ctx.lineTo(screenPos.x, screenPos.y);
    }
    // draw horizontal grid lines
    var grid_right = g.x + g.ncols * g.cellw;
    for ( var r = 0; r <= g.nrows; r++) {
      var y = g.y + r * g.cellh;
      screenPos = view.toScreenPos(g.x, y);
      ctx.moveTo(screenPos.x, screenPos.y);
      screenPos = view.toScreenPos(grid_right, y);
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
    var pos = view.toScreenPos(p.x, p.y);
    var dims = view.toScreenDims(grid.cellw, grid.cellh);
    var dw = dims.w, dh = dims.h;
    ctx.save();
    while (IMGLOADED == false) {
      waiting = setTimeout(function() { drawPiece(p); }, 500);
      console.log("View: Image not loaded yet..");
      return;
    }
    clearTimeout(waiting);
    ctx.drawImage(IMG, p.sx, p.sy, p.sw, p.sh, pos.x, pos.y, dw, dh);
    // draw borders on top of pieces currently being dragged
    if (p.owner) { // piece is owned by another player
      ctx.strokeStyle = "#f0f"; // magenta
      ctx.globalAlpha = 0.5; // transparency
      var br = 1 / 15; // border ratio
      // screen thickness
      var t = view.toScreenDims(grid.cellw * br, grid.cellh * br).w;
      ctx.lineWidth = t;
      ctx.strokeRect(pos.x + t / 2, pos.y + t / 2, dw - t, dh - t);
    } else if (p == model.draggedPiece) { // piece I'm currently dragging
      ctx.strokeStyle = "#0ff"; // cyan
      ctx.globalAlpha = 0.5; // transparency
      var br = 1 / 15; // border ratio, in terms of cell dimensions
      // screen thickness
      var t = view.toScreenDims(grid.cellw * br, grid.cellh * br).w;
      ctx.lineWidth = t;
      ctx.strokeRect(pos.x + t / 2, pos.y + t / 2, dw - t, dh - t);
    }
    ctx.restore();
  }

  this.close = function() {
    this.cleanCanvas();
    ctx.canvas.onmouseup = null;
    ctx.canvas.onmousedown = null;
    ctx.canvas.onmousemove = null;
    ctx.canvas.onmouseout = null;
    ctx.canvas.removeEventListener('DOMMouseScroll', onmousewheel, false); // Firefox
    ctx.canvas.removeEventListener('mousewheel', onmousewheel, false); // Chrome, IE
    document.onkeydown = null;
  }

  this.cleanCanvas = function() {
    var w = ctx.canvas.width;
    var h = ctx.canvas.height;
    ctx.fillStyle = '#FFF'; // black
    ctx.fillRect(0, 0, w, h);
  }

  // first clean the whole canvas,
  // then draw in this order: grid, bound pieces, and loose pieces
  // public method of view so that model can call it
  this.drawAll = function() {
    this.cleanCanvas();
    drawBoard();
    drawGrid();
    drawPieces();
  };

}
