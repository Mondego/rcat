// ----------------- GLOBAL ------------------- 

// The splash image and puzzle background image
// start fetching their content when the page is ready.
var SPLASHIMG = new Image();
var BGIMG = new Image();

// ------------------------ button binders/controllers ----------------

// when the page and DOM are ready, wire the controller logic to view elements,
$(function() {

  // set the canvas global var
  $canvas = $('#jigsaw'); // this is actually an array with 1 html object in it
  
  var triggerGame = function(playerName) {
    // Instantiate the global model, view, and nw, and reveal the game screen.
    $('#loadingScreen').hide();
    $('#gameScreen').show();
    // debug footer
    $('#connectionStatus').html("Connecting");
    $('#disconnect').show();
    // instantiate the MVC
    model = new Model(playerName);
    view = new View();
    // connect to the server
    var host = $('#serverUrl').val();
    nw = new Network(host);
  };
  
  // wire the JOIN GAME button
  $('#connect').bind('click', function(e) {
    // e.preventDefault();
    var playerName = $('#playerName').val();
    $.cookie('jigsawPlayerName', playerName); // set the cookie
    triggerGame(playerName);
  });
  
  var playerName = $.cookie('jigsawPlayerName'); // cookie storing player name
  if (playerName == null) {// ask the player his/her name
    $('#loadingScreen').show();
    $('#gameScreen').hide();
  } else { // if a user name cookie is found, start the game directly
    $('#playerName').val(playerName);
    triggerGame(playerName);
  }

  // when the player logs out, close the view and network socket
  $('#disconnect').bind('click', function(e) {
    // e.preventDefault();
    nw.close();
    view.close();
    $('#gameScreen').hide();
    $('#loadingScreen').show();
    $('#connectionStatus').html('Disconnected.');
    $.removeCookie('jigsawUserName');
  });

  // splash image callback
  SPLASHIMG.onload = function() {
    var ctx = $canvas.get(0).getContext('2d');
    ctx.drawImage(SPLASHIMG, 10, 12);
  };
  SPLASHIMG.src = "img/SplashImage.png";

  // background image callback
  BGIMG.onload = function() {
    BGIMG.loaded = true;
  };
  // http://static1.grsites.com/archive/textures/wood/wood004.jpg
  // wooden background from http://www.grsites.com/terms/
  BGIMG.loaded = false;
  BGIMG.src = "img/wood004.jpg";

});

// -------------------------- VIEW + CONTROLLER -----------------------------

function View() {
  // Display the puzzle in a canvas
  // and translate user inputs into model commands

  this.isGameOver = false;
  this.newGame = function() {
    this.isGameOver = false;
  }

  this.endGame = function() {
    this.isGameOver = true;
  }

  // ------------------ SCORE CONTROLLER ------------------
  this.scoreTable = $("#scoreTable").get(0);
  this.scoreDict = {};

  this.createScoreTable = function(scores) {
    while (this.scoreTable.rows.length > 1) {
      this.scoreTable.deleteRow(this.scoreTable.rows.length - 1);
    }
    this.scoreDict = {};
    for ( var userName in scores) {
      var row = this.scoreTable.insertRow(0);
      var userCell = row.insertCell(0);
      var scoreCell = row.insertCell(1);

      userCell.innerHTML = userName;
      scoreCell.innerHTML = scores[userName];
      this.scoreDict[userName] = row;
    }
  }

  this.updateUserScore = function(user, newvalue) {
    // Get row where entry is currently located
    if (user in this.scoreDict) {
      var row = this.scoreDict[user];
      var cell = row.cells[1];
      cell.innerHTML = newvalue;
    } else {
      var row = this.scoreTable.insertRow(0);
      var userCell = row.insertCell(0);
      var scoreCell = row.insertCell(1);

      userCell.innerHTML = user;
      scoreCell.innerHTML = newvalue;
      this.scoreDict[user] = row;
    }
  }

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
  $canvas.mousedown(function(e) {
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
  });

  // mouseup = drop piece or stop dragging
  $canvas.mouseup(function(e) {
    view.isMouseDown = false;
    var sPos = getScreenPos(e);
    if (model.draggedPiece) {
      var bPos = view.toBoardPos(sPos);
      model.dropMyPiece(bPos.x, bPos.y); // drop the piece
    }
    view.dragStart = null; // stop dragging board or piece
  });

  // Don't redraw the canvas if the mouse moved but was not down.
  // The modes "drag a piece" or "slide the board" are in the model logic;
  // For the view, it's only about mouse movement.
  $canvas.mousemove(function(e) {
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
  });

  // 
  $canvas.mouseout(function(e) {
    view.isMouseDown = false;
    var sPos = getScreenPos(e);
    if (model.draggedPiece) {
      var bPos = view.toBoardPos(sPos);
      model.dropMyPiece(bPos.x, bPos.y); // drop the piece
    }
    view.dragStart = null; // stop dragging board or piece
  });

  // how smooth is the zooming-in and out
  // 5/4=1.25 is better than 4/3=1.333...334 to prevent floating point errors
  this.scaleStep = 1.25;

  // mouse wheel from https://github.com/brandonaaron/jquery-mousewheel
  // for complete doc, see http://www.quirksmode.org/js/events_properties.html
  $canvas.mousewheel(function(e, delta, deltaX, deltaY) {
    e.preventDefault(); // dont scroll the window
    // in jquery.mousewheel, delta = 1 for forward/up, -1 for down/backward
    var isZoomingOut = delta < 0;
    var screenPos = getScreenPos(e);
    model.zoomOnScreenPoint(isZoomingOut, view.scaleStep, screenPos);
  });

  var keyScrollOffset = 50; // how many px of the screen to scroll when keydown
  // Use arrows or WASD to scroll the board.
  // For canvas.onkeydown, the canvas should get focus first.
  // See http://stackoverflow.com/questions/10562092/gaining-focus-on-canvas
  // keydown is repeatedly fired if user keeps pressing the key
  $(document).bind('keypress keydown', function(e) {
    // see http://stackoverflow.com/questions/1444477/keycode-and-charcode
    e = e || window.event;
    var keyCode = e.keyCode;
    var dx = 0, dy = 0;
    switch (keyCode) {
    case (87): // w
      // case (38): // up arrow
      dy = view.toBoardDims(0, keyScrollOffset).h
      break;
    case (65): // a
      // case (37): // left arrow
      dx = view.toBoardDims(keyScrollOffset, 0).w
      break;
    case (83): // s
      // case (40): // down arrow
      dy = -view.toBoardDims(0, keyScrollOffset).h
      break;
    case (68): // d
      // case (39): // right arrow
      dx = -view.toBoardDims(keyScrollOffset, 0).w
      break;
    }
    // Make the (eventual) piece being dragged follow the mouse
    // only if the board actually scrolled.
    // TODO: this needs debugging
    /*
     * if (model.draggedPiece) { var oldbPos = view.toBoardPos(view.mousePos);
     * model.moveBoardRelative(dx, dy); var newbPos =
     * view.toBoardPos(view.mousePos); // pdx < dx if the frustum was near the
     * side of the board // pdx = 0 if the frustum was exactly on the side var
     * pdx = newbPos.x - oldbPos.x; var pdy = newbPos.y - oldbPos.y;
     * model.dragMyPiece(pdx, pdy); } else { // no piece dragged: only scroll
     * the board model.moveBoardRelative(dx, dy); }
     */
    model.moveBoardRelative(dx, dy);
  });

  // get click position relative to the canvas's top left corner
  // adapted from http://www.quirksmode.org/js/events_properties.html
  // TODO: this does not take into account the canvas' border thickness
  function getScreenPos(e) {
    var posx;
    var posy;
    if (!e) {
      var e = window.event;
    }
    if (e.pageX || e.pageY) {
      // posx = e.pageX - canvas.offsetLeft;
      // posy = e.pageY - canvas.offsetTop;
      posx = e.pageX - $canvas.offset().left;
      posy = e.pageY - $canvas.offset().top;
    } else if (e.clientX || e.clientY) {
      posx = e.clientX + document.body.scrollLeft
          + document.documentElement.scrollLeft - $canvas.offset().left;
      posy = e.clientY + document.body.scrollTop
          + document.documentElement.scrollTop - $canvas.offset().top;
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

  var ctx = $canvas.get(0).getContext('2d');

  // draw the background
  this.drawBoard = function() {
    ctx.save();
    // only draw the bg img if the bg img successfully downloaded
    if (BGIMG.loaded) {
      var pattern = ctx.createPattern(BGIMG, 'repeat');
      ctx.fillStyle = pattern;
    } else {
      // img did not load yet: single-color bg
      ctx.fillStyle = '#feb'; // light brown
    }
    var pos = this.toScreenPos(0, 0);
    var dims = this.toScreenDims(model.BOARD.w, model.BOARD.h);
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
    var img = model.IMG
    ctx.drawImage(img, 0, 0, img.width, img.height, pos.x, pos.y, w, h);
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
    ctx.drawImage(model.IMG, p.sx, p.sy, p.sw, p.sh, pos.x, pos.y, dw, dh);
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
    $canvas.unbind('mouseup');
    $canvas.unbind('mousedown');
    $canvas.unbind('mousemove');
    $canvas.unbind('mouseout');
    $canvas.unmousewheel();
    $(document).unbind('keypress keydown'); // WASD and arrow-key movement
    ctx.drawImage(SPLASHIMG, 10, 12);
  }

  this.cleanCanvas = function() {
    var w = $canvas.prop('width');
    var h = $canvas.prop('height');
    ctx.fillStyle = '#FFF'; // black
    ctx.fillRect(0, 0, w, h);
  }

  // first clean the whole canvas,
  // then draw in this order: grid, bound pieces, and loose pieces
  // public method of view so that model can call it
  this.drawAll = function() {
    if (!this.isGameOver) {
      this.cleanCanvas();
      this.drawBoard();
      drawGrid();
      drawPieces();
    }
  };

  this.gameOver = function() {
    this.isGameOver = true;
    this.close();
    ctx.font = "40pt Calibri";
    ctx.fillStyle = "blue";
    ctx.fillText("Game Over! Your score was " + model.getMyScore(), 100, 100);
    ctx.fillText("Click on Screen to Restart Game", 100, 200);
  }
}
