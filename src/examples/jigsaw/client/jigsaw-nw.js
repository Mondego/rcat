// ----------------------- NETWORK --------------- 

function Network(h) {

  if (!window.WebSocket) {
    console.log('Websocket not supported.');
    // TODO: better error handling
    return;
  }

//  var host = "ws://opensim.ics.uci.edu:8888/client";
  var host = h;
  var connected = false;
  var socket = new WebSocket(host);
  this.sendDelay = 100; // how often to send updates, in millis

  socket.onopen = function() {
    console.log('Socket opened; status = ' + socket.readyState);
    connected = true;
  };
  
  // receive handler
  socket.onmessage = function(msg) {
    m = JSON.parse(msg.data); // TODO: use json2.js for IE6 and 7
    // cf http://stackoverflow.com/a/4935684/856897
    if ('c' in m) { // Received init config
      model.init();
      var imgurl = m.c.imgurl; // puzzle image
      IMG.src = imgurl;
      var board = m.c.board; // board config
      var grid = m.c.grid; // grid config
      var dfrus = m.c.frus; // default frustum
      var pieces = m.c.pieces; // pieces
      var myid = m.c.myid; // the id given by the server to represent me
      var nclients = m.c.clients;
      var scores = m.c.scores;
      model.setConnectedUsers(nclients);
      model.setScores(scores);      
      model.startGame(board, grid, dfrus, pieces, myid);      
    } else if ('scu' in m) { //  Received update for one or more players
      var scoreUpdates = m.scu;
      for (var key in scoreUpdates) {
	      model.setUserScore(key, scoreUpdates[key]);
	  }
    } else if ('pm' in m) { // Received piece movement
      var id = m.pm.id; // piece id
      var x = m.pm.x, y = m.pm.y;
      var owner = m.pm.l; // player currently moving the piece
      model.moveRemotePiece(id, x, y, owner);
    } else if ('pd' in m) { // Received piece drop
      var id = m.pd.id, bound = m.pd.b; // piece id and isBound
      var x = m.pd.x, y = m.pd.y;
      var owner = m.pd.l; // player who dropped the piece
      model.dropRemotePiece(id, x, y, bound, owner);
    } else if ('pf' in m) {
        
    } else if ('NU' in m) {
      model.userConnected();
    } else if ('UD' in m) {
      model.userDisconnected();
    // Game Over!
    } else if ('go' in m) {
      model.endGame();
    }
  };

  // TODO: try to get back the connection every 5-10 seconds
  // TODO: re-init the board when the connection is back
  // (keeping a journal of the local changes is overkilling it)
  socket.onclose = function() {
    console.log('Socket closed; status = ' + socket.readyState);
    if (connected == true) 
      alert("Lost connection to server");
    $('#disconnect').hide();
    $('#connect').show();
    $('#numPlayersBox').html('Disconnected.');
  };

  // Tell the server that the client's frustum changed.
  this.frustumTimerMsg = null; // frustum msg to send when the timer ends
  this.sendFrustum = function(frustum) {
    var msg = {
      'rp' : {
        'v' : frustum
      }
    };
    if (this.frustumTimerMsg == null)
      setTimeout('nw.sendFrustumStopTimer()', this.sendDelay);
    this.frustumTimerMsg = msg;
    // sending is taken care of by the frustum timer
  };
  // Send the frustum and reset the timer
  this.sendFrustumStopTimer = function() {
    var msg = this.frustumTimerMsg;
    if (msg) // just in case ...
      socket.send(JSON.stringify(msg));
    else
      console.log("Warning: Frustum to send is null");
    this.frustumTimerMsg = null;
  }

  // Tell the server that the client moved a piece.
  this.pieceTimers = {}; // timer to send each piece's coords
  this.sendPieceMove = function(pid, x, y) {
    var msg = {
      'pm' : {
        'id' : pid,
        'x' : x,
        'y' : y
      }
    };
    // sending is taken care of by the frustum timer
    if (pid in this.pieceTimers) {
      this.pieceTimers[pid].msg = msg;
    } else { // start the timeout sending the frustum
      var funcCall = "nw.sendPieceStopTimer('" + pid + "')";
      var tid = setTimeout(funcCall, this.sendDelay);
      var pt = {
        'tid' : tid,
        'pid' : pid,
        'msg' : msg
      };
      this.pieceTimers[pid] = pt;
    }
  };
  // Send the piece and reset the timer
  this.sendPieceStopTimer = function(pid) {
    if (pid in this.pieceTimers) { // just in case ...
      var msg = this.pieceTimers[pid].msg;
      socket.send(JSON.stringify(msg));
      delete this.pieceTimers[pid];
    } else
      console.log("Warning: The timer for piece " + pid + " is missing.");
  };

  // Send the piece drop and cancel the piece move msg timer.
  this.sendPieceDrop = function(pid, x, y, b) {
    var msg = {
      'pd' : {
        'id' : pid,
        'x' : x,
        'y' : y,
        'b' : b
      }
    };
    if (pid in this.pieceTimers) {
      clearTimeout(this.pieceTimers[pid].tid); // stop the timer
      delete this.pieceTimers[pid];
    }
    socket.send(JSON.stringify(msg));
  };

  this.sendGameOver = function() {
	var msg = {'go': true};
	socket.send(JSON.stringify(msg));
  };
  
  this.sendUserName = function(user) {
    var msg = {'usr': user};
    socket.send(JSON.stringify(msg));
  }
  // close connection to the server
  this.close = function() {
    connected = false; // This prevents the pop-up alert from coming up every time you intentionally disconnect
    socket.close();
  };

}

function writeToScreen(element, message) { 
    var pre = document.getElementById(element); 
    pre.style.wordWrap = "break-word"; 
    pre.innerHTML = message; 
    output.appendChild(pre); 
}
