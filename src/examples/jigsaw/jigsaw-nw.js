// ----------------------- NETWORK --------------- 

function Network() {

  if (!window.WebSocket) {
    console.log('Websocket not supported.');
    // TODO: better error handling
    return;
  }

  var host = "ws://localhost:9000/test";
  var socket = new WebSocket(host);

  socket.onopen = function() {
    console.log('Socket opened; status = ' + socket.readyState);
  };

  // receive handler
  socket.onmessage = function(msg) {
    m = JSON.parse(msg.data); // TODO: use json2.js for IE6 and 7
    // cf http://stackoverflow.com/a/4935684/856897
    if ('c' in m) { // Received init config
      var imgurl = m.c.imgurl; // puzzle image
      img.src = imgurl;
      var board = m.c.board; // board config
      var grid = m.c.grid; // grid config
      var dfrus = m.c.frus; // default frustum
      var pieces = m.c.pieces; // pieces
      model.startGame(board, grid, dfrus, pieces);
    } else if ('p' in m) { // Received piece movement
      var id = m.p.id;
      var x = m.p.x, y = m.p.y;
      model.movePiece(id, x, y);
    }
  };

  // TODO: try to get back the connection every 5-10 seconds
  // TODO: re-init the board when the connection is back
  // (keeping a journal of the local changes is overkilling it)
  socket.onclose = function() {
    console.log('Socket closed; status = ' + socket.readyState);
  };

  // Tell the server that the client's frustum changed.
  this.sendFrustum = function(frustum) {
    var msg = {
      'rp' : {
        'v' : frustum
      }
    };
    socket.send(JSON.stringify(msg));
  };

  // Tell the server that the client moved a piece.
  this.sendPieceMove = function(id, x, y) {
    var msg = {
      'p' : {
        'id' : id,
        'x' : x,
        'y' : y
      }
    };
    socket.send(JSON.stringify(msg));
  }

  // close connection from the server
  this.close = function() {
    socket.close();
  };

}