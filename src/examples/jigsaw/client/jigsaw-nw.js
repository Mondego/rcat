// ----------------------- NETWORK --------------- 

function Network(host) {

  if (!window.WebSocket) {
    $('#connectionStatus').html("Error: websocket not supported.");
    return;
  }

  // var host = "ws://opensim.ics.uci.edu:8888/client";
  this.host = host;
  var socket = new WebSocket(host);
  $('#connectionStatus').html("Connecting");
  this.sendDelay = 100; // how often to send piece move updates, in millis

  socket.onopen = function() {
    $('#connectionStatus').html("Connected.");
  };

  // receive handler
  socket.onmessage = function(msg) {
    m = JSON.parse(msg.data); // TODO: use json2.js for IE6 and 7
    // cf http://stackoverflow.com/a/4935684/856897
    if ('c' in m) { // init config
      model.init();
      console.log(m.c.scores);
      var topUsers = m.c.scores.top;
      var numTopScores = m.c.scores.numTop;
      var connectedUsers = m.c.scores.connected;

      console.log(m.c)

      model.setUsers(connectedUsers, topUsers, numTopScores);

      var board = m.c.board; // board config
      var grid = m.c.grid; // grid config
      var dfrus = m.c.frus; // default frustum
      var pieces = m.c.pieces; // pieces
      var myid = m.c.myid; // the id given by the server to represent me
      var img = m.c.img; // url and size of puzzle image
      model.startGame(board, grid, dfrus, pieces, myid, img);
    } else if ('scu' in m) { // score updates for 1 or more players
      console.log(m)

      var scoreUpdates = m.scu;
      var len = scoreUpdates.length, update = null;
      for ( var i = 0; i < len; i++) {
        update = scoreUpdates[i];
        model.setUserScore(update.uid, update.user, update.score);
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
    } else if ('pf' in m) {// player frustum update
    } else if ('NU' in m) { // new user(s): 1+ players just logged in

      console.log(m)
      
      var len = m.NU.length;
      var name, score, uid;
      for ( var i = 0; i < len; i++) {
        uid = m.NU[i].uid;
        name = m.NU[i].user;
        score = m.NU[i].score;
        model.userJoined(uid, name, score);
      }
    } else if ('UD' in m) { // user disconnected

      console.log(m)

      var userId = m.UD;
      model.userLeft(userId);
    } else if ('go' in m) {// Game Over
      model.endGame();
    }
  };

  // TODO: try to get back the connection every 5-10 seconds a la gmail
  // TODO: re-init the board when the connection is back
  socket.onclose = function() {
    // if (connected == true){
    // alert("Lost connection to server");}
    $('#disconnect').hide();
    $('#connectionStatus').html('Disconnected.');
    // TODO: close the model and view
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
      setTimeout(function() {
        nw.sendFrustumStopTimer()
      }, this.sendDelay);
    this.frustumTimerMsg = msg;
    // sending is taken care of by the frustum timer
  };

  // Send the frustum and reset the timer
  this.sendFrustumStopTimer = function() {
    var msg = this.frustumTimerMsg;
    if (msg) { // just in case ...
      this.sendMessage(msg);
    } else {
      console.log("Warning: Frustum to send is null");
    }
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
    // sending is taken care of by each piece's timer callback
    if (pid in this.pieceTimers) { // the piece was moved very recently
      this.pieceTimers[pid].msg = msg; // update the piece coords in the msg
    } else {// The piece is moved for the first time in a while:
      this.sendMessage(msg);// send move right away
      var tid = setTimeout(function() { // start periodic callback
        nw.sendPieceMoveStopTimer(pid)
      }, this.sendDelay);
      var pt = {
        'tid' : tid,
        'pid' : pid,
        'msg' : msg
      };
      this.pieceTimers[pid] = pt;
    }
  };

  // Send the piece and reset the timer
  this.sendPieceMoveStopTimer = function(pid) {
    if (pid in this.pieceTimers) {
      var msg = this.pieceTimers[pid].msg;
      this.sendMessage(msg);
      delete this.pieceTimers[pid];
    } else { // should never happen ...
      console.log("Warning: Missing timer for piece " + pid);
    }
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
    this.sendMessage(msg);
  };

  this.sendGameOver = function() {
    var msg = {
      'go' : true
    };
    this.sendMessage(msg);
  };

  this.sendUserName = function(user) {
    var msg = {
      'usr' : user
    };
    console.log('sent user name')
    this.sendMessage(msg);
  }

  // Convert a message in JSON and send it right away.
  this.sendMessage = function(msg) {
    socket.send(JSON.stringify(msg));
  }

  // close connection to the server
  this.close = function() {
    socket.close();
  };

}
