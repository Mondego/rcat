//------------------------- GLOBAL --------------------

var model, view, nw;
var $canvas;

// ------------------------ MODEL --------------------------

// stores game logic and data
function Model(usr) {
  // -------- INITIALIZATION ---------------------------
  this.init = function() {

    this.topOfflineUsers = {}; // map user name to score for the top 20 scores.
    this.sortedTopOfflineUsers = new Array(); // array, max 20 users, ordered by
    // score
    this.onlineUsers = {}; // map user name to id+score for connected players.
    this.sortedOnlineUsers = new Array(); // ordered by score

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
    this.IMG = new Image(); // IMG.onload happens after model.startGame
    this.puzzleImageLoaded = false;
    
    this.myName = usr;
    this.myid = null; // the id given by the server to represent me

    // which part of the board is currently being viewed by the user
    this.frustum = {
      x : null,
      y : null,
      scale : null, // zooming scale; >1 is zoomed in, <1 is zoomed out
      w : null,
      h : null
    };
  };

  // -------- PLAYERS AND SCORES --------------------

  // topScores is a list of 20 or less players and scores,
  // numTopScores is the number of top scores known by the server among top 20.
  // If numTopScores == 20 and topScores.length == 13,
  // it means that only 13 players ever connected, and 7 new players connect,
  // the client will consider them in the top20 directly.
  this.setUsers = function(givenOnlineUsers, givenTopUsers, numTopScores) {
    // fill online users
    this.onlineUsers = {};// user name -> id and score
    this.sortedOnlineUsers = new Array(); // ordered by score
    var len = givenOnlineUsers.length, user = null;
    for ( var i = 0; i < len; i++) {
      user = givenOnlineUsers[i];
      this.onlineUsers[user.user] = {
        'uid' : user.uid,
        'score' : user.score
      };
      this.sortedOnlineUsers.push({
        'name' : user.user,
        'score' : user.score,
        'uid' : user.uid
      });
    }
    // Sort from larger to smaller score, then alphabetically by user name.
    this.sortedOnlineUsers.sort(function(user1, user2) {
      var scoreComp = user2.score - user1.score;
      if (scoreComp != 0) { // different scores: no need to look at names
        return scoreComp;
      } else { // same score: look at names, ignoring case
        var nameComp = null;
        var n1 = user1.name.toLowerCase(), n2 = user2.name.toLowerCase();
        if (n1 < n2) {
          nameComp = -1;
        } else if (n1 > n2) {
          nameComp = 1;
        } else {
          nameComp = 0; // Same name and same score.
        }
        return nameComp;
      }
    });
    // Fill top offline users.
    // Remove any online user from the top offline list.
    this.topOfflineUsers = {}; // map user id to score for the top 20 scores
    var len = givenTopUsers.length, user = null;
    this.sortedTopOfflineUsers = new Array();
    for ( var i = 0; i < len; i++) {
      user = givenTopUsers[i];
      if (!this.onlineUsers[user.user]) {
        this.topOfflineUsers[user.user] = user.score; // index by name
        this.sortedTopOfflineUsers.push({
          'name' : user.user,
          'score' : user.score
        });
      }
    }
    // Sort from larger to smaller score, then alphabetically by user name.
    this.sortedTopOfflineUsers.sort(function(user1, user2) {
      var scoreComp = user2.score - user1.score;
      if (scoreComp != 0) { // different scores: no need to look at names
        return scoreComp;
      } else { // same score: look at names
        var nameComp = null;
        var n1 = user1.name.toLowerCase(), n2 = user2.name.toLowerCase();
        if (n1 < n2) {
          nameComp = -1;
        } else if (n1 > n2) {
          nameComp = 1;
        } else {
          nameComp = 0; // Same name and same score.
        }
        return nameComp;
      }
    });
    this.numTopScores = numTopScores;
    // display
    view.initUserScores(this.sortedOnlineUsers, this.sortedTopOfflineUsers);
  }

  // Keep the number of top scores down to 20.
  // Notify the view if an offline score should be removed.
  var trimTopOfflineScoresIfNeeded = function() {
    var numRemoved = model.sortedTopOfflineUsers.length - model.numTopScores;
    if (numRemoved > 0) {
      var removedUsers = model.sortedTopOfflineUsers.splice(model.numTopScores,
          numRemoved);
      // Adjust the view and the model's mapping of user name -> user score.
      var name = null, score = null;
      for ( var i = 0; i < numRemoved; i++) {
        name = removedUsers[i].name;
        score = removedUsers[i].score;
        delete model.topOfflineUsers[name];
        view.removeUserFromTopList(name, score);
      }
    }
  }

  // Remove a user from the list of offline users WITHOUT notifying the view.
  var removeFromOfflineUsers = function(name) {
    var users = model.topOfflineUsers;
    var sortedUsers = model.sortedTopOfflineUsers;
    if (name in users) {
      // remove user from dict
      delete users[name];
      // remove user from array
      var len = sortedUsers.length;
      for ( var i = 0; i < len; i++) {
        if (sortedUsers[i].name == name) {
          sortedUsers.splice(i, 1);
          break;
        }
      }
    }
  }

  // Remove a user from the list of online users WITHOUT notifying the view.
  // Return the user name and score.
  var removeFromOnlineUsers = function(uid) {
    var users = model.onlineUsers;
    var sortedUsers = model.sortedOnlineUsers;
    var len = sortedUsers.length;
    var name = null, score = null;
    for ( var i = 0; i < len; i++) {
      if (sortedUsers[i].uid == uid) {
        name = sortedUsers[i].name;
        score = sortedUsers[i].score;
        sortedUsers.splice(i, 1); // remove user from the array
        delete users[name];
        return {
          'name' : name,
          'score' : score
        };
      }
    }
    return null;
  }

  // Insert a user and his score in the offline user scores.
  // If the user is already offline, remove and re-add him from offline users.
  var insertIntoOfflineUsers = function(name, score) {
    var users = model.topOfflineUsers;
    var sortedUsers = model.sortedTopOfflineUsers;
    // remove from offline users
    if (name in model.topOfflineUsers) {
      removeFromOfflineUsers(name);
    }
    // Compute rank of the user's score among offline users.
    var rank = null; // position of the user
    var len = sortedUsers.length;
    if (len == 0) { // no one was online
      rank = 0;
    } else {// Iterate down the list.
      for ( var i = 0; i < len; i++) {
        if (score >= sortedUsers[i].score) {
          rank = i;
          break;
        }
      }
      if (rank == null) { // lower score than any score in current top
        if (len < model.numTopScores) { // take the empty spot(s)
          rank = len;
        }
      }
    }
    // Add user to offline top scores.
    if (rank != null) { // score was high enough, or there was room
      var user = {
        'name' : name,
        'score' : score
      };
      sortedUsers.splice(rank, 0, user);// insert at pos #rank
      users[name] = score;
    }
    // Keep the offline top score list down to 20 rows.
    trimTopOfflineScoresIfNeeded();
    // Tell the view about the user disconnection.
    // If rank is null, the view won't add a row about the user.
    view.userScoredOffline(name, score, rank);
  }

  // Insert a user and his score in the online user scores.
  // If the user is already online, remove and re-add him to online users.
  var insertIntoOnlineUsers = function(uid, name, score) {
    var users = model.onlineUsers;
    var sortedUsers = model.sortedOnlineUsers;
    // remove from online users
    if (name in model.onlineUsers) {
      removeFromOnlineUsers(uid);
    }
    // Compute rank of the user's score among online users.
    var rank = null; // position of the user
    var len = sortedUsers.length;
    if (len == 0) { // no one was online
      rank = 0;
    } else {// Iterate down the list.
      for ( var i = 0; i < len; i++) {
        if (score >= sortedUsers[i].score) {
          rank = i;
          break;
        }
      }
      if (rank == null) { // lower score than any online users
        rank = len; // add to bottom
      }
    }
    // Add user to online top scores.
    var user = {
      'name' : name,
      'score' : score,
      'uid' : uid
    };
    sortedUsers.splice(rank, 0, user);// insert at pos #rank in array
    users[name] = {
      'uid' : uid,
      'score' : score
    };
    // display
    view.userScoredOnline(name, score, rank);
  }

  // User joined: add him to online scores.
  this.userJoined = function(uid, name, score) {
    removeFromOfflineUsers(name);
    insertIntoOnlineUsers(uid, name, score);
  }

  // User left: remove him from the online scores.
  // Add him to top scores if his score is high enough or there is room.
  this.userLeft = function(uid) {
    var user = removeFromOnlineUsers(uid);
    if (user != null) {
      // update model and notifies view
      insertIntoOfflineUsers(user.name, user.score);
    } else {
      console.log('Error: could not find user with uid = ' + uid
          + ' in model.sortedOnlineUsers');
    }
  }

  // Update the score of a user.
  this.setUserScore = function(uid, name, score) {
    if (uid == null && name in this.topOfflineUsers) {
      // score of offline user changed
      insertIntoOfflineUsers(name, score); // update score and notify view.
    }
    if (name in this.onlineUsers) { // score of online user changed
      insertIntoOnlineUsers(uid, name, score); // update score and notify view
    }
  }

  // -------- GAME START AND END ---------------------------

  // Starting the game takes 3 steps:
  // 1- Build the model right away with the most recent server data.
  // This enables us to process incoming movement messages right away.
  // 2- Start downloading the puzzle image.
  // 3- Build the view when the heavy puzzle image has been received.
  // That way, we only display the view when everything is ready.
  this.startGame = function(board, grid, dfrus, piecesData, myid, img) {

    // Init board, grid, and frustum from server config.
    this.BOARD = board;
    this.GRID = grid;
    this.myid = myid;

    // Send back the frustum's w and h to the server,
    // as they are determined by the client's canvas size.
    this.frustum.x = dfrus.x;
    this.frustum.y = dfrus.y;
    this.frustum.scale = dfrus.scale;
    var dims = view.toBoardDims($canvas.prop('width'), $canvas.prop('height'));
    this.frustum.w = dims.w;
    this.frustum.h = dims.h;
    nw.sendFrustum(this.frustum);

    // Also create the pieces from server data.
    this.loosePieces = {}; // hash table of movable pieces
    this.boundPieces = {}; // pieces that have been dropped in the correct cell
    var x, y; // coords of the piece on the board
    var sx, sy; // dimensions of the slice from the original image
    var w = grid.cellw;
    var h = grid.cellh;
    // each piece contains a sw * sh slice of the original image
    var sw = img.img_w / grid.ncols;
    var sh = img.img_h / grid.nrows;
    var pdata, p, sx, sy;
    var id;
    for (id in piecesData) {
      pd = piecesData[id];
      sx = pd.c * sw; // coords of image sliced from original
      sy = pd.r * sh;
      p = new Piece(id, pd.b, pd.c, pd.r, pd.x, pd.y, w, h, sx, sy, sw, sh);
    }
    nw.sendUserName(this.myName);

    view.startRendering();

    // Only init the view when the puzzle image has been downloaded.
    // Weirdly, img.onload gets triggered every time a game restarts in FF, 
    // but only when joining the game in Chrome ... 
    this.IMG.onload = function() {
      this.puzzleImageLoaded = true; 
      view.setDirty(); // set the view to dirty
    };
    this.IMG.src = img.img_url;
    // if the image was already loaded, onload may not trigger: dirty the view 
    if (this.puzzleImageLoaded) {
      view.setDirty();
    }
  };

  // end the game: stop the rendering
  // TODO: should display a "game over" message
  this.endGame = function() {
    view.stopRendering();
  }

  // -------- GAME SETTINGS -------------------------

  // Frustum primitive.
  // Fix the frustum if user scrolled past board edges
  this.keepFrustumOnBoard = function() {
    var fru = this.frustum;
    // canvas dimensions in board coords
    var cdims = view.toBoardDims($canvas.prop('width'), $canvas.prop('height'));
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
    if (found) { // at least one free piece collides: prepare to drag it around
      this.draggedPiece = p;
      this.dragMyPiece(0, 0);
    }
  };

  // Drag a piece locally, and send the move to the server.
  // TODO: if piece near the board edges, scroll the board too
  this.dragMyPiece = function(dx, dy) {
    var p = this.draggedPiece;
    p.moveRelative(dx, dy);
    nw.sendPieceMove(p.id, p.x, p.y);
    view.setDirty();
  };

  // Scroll the board in opposite direction of the mouse movement.
  this.moveBoardRelative = function(dx, dy) {
    this.scrollRelative(dx, dy);
    nw.sendFrustum(this.frustum);
    view.setDirty();
  };

  // Zoom in/out on the given screen coord.
  // Called by the view (hence, it's NOT a frustum primitive).
  this.zoomOnScreenPoint = function(isZoomingOut, factor, sPos) {
    var bPos = view.toBoardPos(sPos);
    this.zoom(isZoomingOut, factor);
    var offset = view.toBoardDims(sPos.x, sPos.y);
    model.scrollAbsolute(bPos.x - offset.w, bPos.y - offset.h);
    nw.sendFrustum(this.frustum);
    view.setDirty();
  };

  // If a piece is dropped on the correct cell, the grid "magnets" it,
  // and the piece becomes "bound": it can't be moved anymore.
  // TODO: should display an effect when the piece is magnetted.
  this.dropMyPiece = function(x, y) {
    var p = this.draggedPiece;
    this.draggedPiece = null;
    var cell = this.getCellFromPos(x, y); // or p.x + p.w/2 instead? or both?
    if (cell != null && cell.c == p.c && cell.r == p.r) { // correct cell
      p.x = cell.x; // magnet the piece
      p.y = cell.y;
      p.bind();
    }
    nw.sendPieceDrop(p.id, p.x, p.y, p.bound);
    view.setDirty();
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
        if (!(id in this.boundPieces)) {
          var p = this.loosePieces[id];
          p.x = x;
          p.y = y;
          p.owner = null;
          if (bound)
            p.bind();
        }
      }
      view.setDirty();
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
      view.setDirty(); // TODO: redraw only if piece was or is in the frustum
    }
  };

} // end of model

// TODO: could have an ID given by the server instead of c,r
// (that would make cheating more annoying for puzzles with lots of pieces)
function Piece(id, b, c, r, x, y, w, h, sx, sy, sw, sh) {

  this.id = id; // id
  this.owner = null; // remote player currently dragging (+ locking) the piece

  // whether the piece has been correctly placed or not
  this.bound = b;
  if (b)
    model.boundPieces[id] = this;
  else
    model.loosePieces[id] = this;

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
    return (this.owner && this.owner != model.myid);
  }

  // bind a piece: the piece has been correctly placed,
  // it's not draggable anymore
  this.bind = function() {
    if (this.id in model.loosePieces) {
      delete model.loosePieces[this.id];
      model.boundPieces[this.id] = this;
      this.bound = true;
      if (model.loosePieces.length == 0) {
        nw.sendGameOver();
      }
    }
  };

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
