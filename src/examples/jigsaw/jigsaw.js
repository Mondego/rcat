
//---------------- constants ---------------

var canvas;
var ctx; // canvas context
var canvasID = "canJigsaw";

var lastX=400, lastY=300;
var dragStart,dragged;

var MAIN_IMG_WIDTH = 800;
var MAIN_IMG_HEIGHT = 600;

var BLOCK_IMG_WIDTH = 400;
var BLOCK_IMG_HEIGHT = 300;

var scaleFactor = 1.1;

var TOTAL_ROWS = 2;
var TOTAL_COLUMNS = 2;

var TOTAL_PIECES = TOTAL_ROWS * TOTAL_COLUMNS;

var IMG_WIDTH = Math.round(MAIN_IMG_WIDTH / TOTAL_COLUMNS);
var IMG_HEIGHT = Math.round(MAIN_IMG_HEIGHT / TOTAL_ROWS);

var BLOCK_WIDTH = 0; // Math.round(BLOCK_IMG_WIDTH / TOTAL_COLUMNS);
var BLOCK_HEIGHT = 0; // Math.round(BLOCK_IMG_HEIGHT / TOTAL_ROWS);

var image1 = new Image();
image1.src = "img/BugsLife.jpg";


//------------------- code ---------------
﻿
function imageBlock(no, x, y) {
  this.no = no;
  this.x = x;
  this.y = y;
  this.isSelected = false;
}


function Jigsaw() {
  canvas = document.getElementById(canvasID); 
  ctx = canvas.getContext('2d');

  top = 0;
  left = 0;

  imageBlockList = [];
  blockList = [];

  selectedBlock = null;
  initDrawing();

}


function initDrawing () {

  selectedBlock = null;

  // register events
  canvas.onmousedown = handleOnMouseDown;
  canvas.onmouseup = handleOnMouseUp;
  canvas.onmouseout = handleOnMouseOut;
  canvas.onmousemove = handleOnMouseMove;
  canvas.addEventListener('DOMMouseScroll',handleScroll,false); // webkit
  // browsers
  canvas.addEventListener('mousewheel',handleScroll,false); // non-webkit
  // browsers
  trackTransforms(ctx);
  initializeNewGame();
};


function initializeNewGame() {

  // Set block
  BLOCK_WIDTH = Math.round(BLOCK_IMG_WIDTH / TOTAL_COLUMNS);
  BLOCK_HEIGHT = Math.round(BLOCK_IMG_HEIGHT / TOTAL_ROWS);


  // Draw image
  SetImageBlock();
  DrawGame();
}



function SetImageBlock() {

  var total = TOTAL_PIECES;
  imageBlockList = new Array();// blocks of movable images
  blockList = new Array();// blocks of correct images

  var x1 = BLOCK_IMG_WIDTH + 50;
  var x2 = canvas.width - 100;
  var y2 = BLOCK_IMG_HEIGHT;
  for (var i = 0; i < total; i++) {

    var randomX = randomXtoY(x1, x2, 2);
    var randomY = randomXtoY(0, y2, 2);

    var imgBlock = new imageBlock(i, randomX, randomY);

    imageBlockList.push(imgBlock);

    var x = (i % TOTAL_COLUMNS) * BLOCK_WIDTH;
    var y = Math.floor(i / TOTAL_COLUMNS) * BLOCK_HEIGHT;

    var block = new imageBlock(i, x, y);
    blockList.push(block);

  }

}



function DrawGame() {

  clear(ctx);
  drawLines();
  drawAllImages();

  if (selectedBlock) {
    drawImageBlock(selectedBlock);
  }
}





function drawLines() {

  ctx.strokeStyle = "#222"; // gray

  ctx.lineWidth = 1;
  ctx.beginPath();

  // draw vertical grid lines
  for (var i = 0; i <= TOTAL_COLUMNS; i++) {
    var x = BLOCK_WIDTH * i;
    ctx.moveTo(x, 0);
    ctx.lineTo(x, 300);
  }

  // draw horizontal grid lines
  for (var i = 0; i <= TOTAL_ROWS; i++) {
    var y = BLOCK_HEIGHT * i;
    ctx.moveTo(0, y);
    ctx.lineTo(400, y);
  }

  ctx.closePath();
  ctx.stroke();
}



function drawAllImages() {

  for (var i = 0; i < imageBlockList.length; i++) {
    var imgBlock = imageBlockList[i];
    if (imgBlock.isSelected == false) {

      drawImageBlock(imgBlock);
    }
  }
}



function drawImageBlock(imgBlock) {

  drawFinalImage(imgBlock.no, imgBlock.x, imgBlock.y, BLOCK_WIDTH, BLOCK_HEIGHT);
}

function drawFinalImage(index, destX, destY, destWidth, destHeight) {

  ctx.save();

  var srcX = (index % TOTAL_COLUMNS) * IMG_WIDTH;
  var srcY = Math.floor(index / TOTAL_COLUMNS) * IMG_HEIGHT;

  ctx.drawImage(this.image1, srcX, srcY, IMG_WIDTH, IMG_HEIGHT, destX, destY, destWidth, destHeight);

  ctx.restore();
}

function drawImage(image) {

  ctx.save();

  ctx.drawImage(image, 0, 0, BLOCK_WIDTH, BLOCK_WIDTH, 10, 10, BLOCK_WIDTH, BLOCK_WIDTH);

  ctx.restore();
}

var interval = null;
var remove_width;
var remove_height;

function OnFinished() {

  remove_width = BLOCK_WIDTH;
  remove_height = BLOCK_HEIGHT;
  // Clear Board
  interval = setInterval(function () { ClearGame(); }, 100);
}


function ClearGame() {
  remove_width -= 30;
  remove_height -= 20;

  if (remove_width > 0 && remove_height > 0) {

    clear(ctx);

    for (var i = 0; i < imageBlockList.length; i++) {
      var imgBlock = imageBlockList[i];

      imgBlock.x += 10;
      imgBlock.y += 10;

      drawFinalImage(imgBlock.no, imgBlock.x, imgBlock.y, remove_width, remove_height);
    }

    // DrawGame();
  } else {

    clearInterval(interval);

    // Restart game
    initializeNewGame(); 


  }
};

///////////////////////////////////////////////////
///////////////////////////////////////// EVENTS
/////////////////////////////////////////////////////




function handleOnMouseOut(e) {

  // remove old selected
  if (selectedBlock != null) {

    imageBlockList[selectedBlock.no].isSelected = false;
    selectedBlock = null;
    DrawGame();

  }

}

function handleOnMouseDown(e) {

  var clicked = ctx.fromGlobalCoord(e.pageX,e.pageY);

  clickx = clicked.x;
  clicky = clicked.y;
  console.log(clicked);

  // remove old selected
  if (selectedBlock != null) {

    imageBlockList[selectedBlock.no].isSelected = false;

  }

  selectedBlock = GetImageBlock(imageBlockList, clickx, clicky);

  if (selectedBlock) {
    imageBlockList[selectedBlock.no].isSelected = true;
    offsetx = selectedBlock.x - clickx
    offsety = selectedBlock.y - clicky
  }

}


function handleOnMouseUp(e) {
  var clicked = ctx.fromGlobalCoord(e.pageX,e.pageY);
  if (selectedBlock) {
    var index = selectedBlock.no;

    var block = GetImageBlock(blockList, clicked.x, clicked.y);
    if (block) {

      var blockOldImage = GetImageBlockOnEqual(imageBlockList, block.x, block.y);
      if (blockOldImage == null) {
        imageBlockList[index].x = block.x;
        imageBlockList[index].y = block.y;
      }
    }
    else {
      imageBlockList[index].x = selectedBlock.x;
      imageBlockList[index].y = selectedBlock.y;
    }

    imageBlockList[index].isSelected = false;
    selectedBlock = null;
    DrawGame();

    if (isFinished()) {
      OnFinished();
    }

  }
}

function handleOnMouseMove(e) {

  if (selectedBlock) {
    var clicked = ctx.fromGlobalCoord(e.pageX,e.pageY);

    selectedBlock.x = clicked.x + offsetx;
    selectedBlock.y = clicked.y + offsety;

    DrawGame();

  }
}

///////////////////////////////////////////
///////////////////////////////////////// HELPER METHODS
////////////////////////////////////////////

function clear(c) {
	var p1 = c.transformedPoint(0,0);
	var p2 = c.transformedPoint(canvas.width,canvas.height);
	ctx.clearRect(p1.x,p1.y,p2.x-p1.x,p2.y-p1.y);
}

function clear_all() {
	var p1 = ctx.transformedPoint(0,0);
	var p2 = ctx.transformedPoint(canvas.width,canvas.height);
	//var p3 = ctx.transformedPoint(100,100);
	//console.log(p3);
        //console.log(ctx.toGlobalCoord(p3.x,p3.y));
	ctx.clearRect(p1.x,p1.y,p2.x-p1.x,p2.y-p1.y);
}

function randomXtoY(minVal, maxVal, decimals) {
  var randVal = minVal + (Math.random() * (maxVal - minVal));
  var val = typeof decimals == 'undefined' ? Math.round(randVal) : randVal.toFixed(decimals);

  return Math.round(val);
}


function GetImageBlock(imglist, x, y) {

  for (var i = imglist.length - 1; i >= 0; i--) {
    var imgBlock = imglist[i];

    var x1 = imgBlock.x;
    var x2 = x1 + BLOCK_WIDTH;

    var y1 = imgBlock.y;
    var y2 = y1 + BLOCK_HEIGHT;

    if (
        (x >= x1 && x <= x2) &&
        (y >= y1 && y <= y2)
    ) {

      var img = new imageBlock(imgBlock.no, imgBlock.x, imgBlock.y);
      return img;

    }
  }

  return null;
}


function GetImageBlockOnEqual(list, x, y) {

  for (var i = 0; i < list.length; i++) {
    var imgBlock = list[i];

    var x1 = imgBlock.x;
    var y1 = imgBlock.y;

    if (
        (x == x1) &&
        (y == y1)
    ) {

      var img = new imageBlock(imgBlock.no, imgBlock.x, imgBlock.y);
      return img;

    }
  }

  return null;
}


function isFinished() {

  var total = TOTAL_PIECES;
  for (var i = 0; i < total; i++) {

    var img = imageBlockList[i];
    var block = blockList[i];

    if (
        (img.x != block.x) ||
        (img.y != block.y)
    ) {
      return false;
    }
  }

  return true;
}

//------- zoom from http://phrogz.net/tmp/canvas_zoom_to_cursor.html
function zoom(delta) {
//  Uncomment to add section zooming
//  var pt = ctx.transformedPoint(lastX,lastY);
//  ctx.translate(pt.x,pt.y);
  var factor = Math.pow(scaleFactor,delta);
  ctx.scale(factor,factor);
//  ctx.translate(-pt.x,-pt.y);
  clear_all();
  DrawGame();
}	

function handleScroll (evt){
  // evt.wheelDelta for non-webkit, evt.detail for webkit
  var delta = evt.wheelDelta ? evt.wheelDelta/40 : evt.detail ? -evt.detail : 0;
  if (delta) 
    zoom(delta);
  return evt.preventDefault() && false;
};

function trackTransforms(ctx) {
  var svg = document.createElementNS("http://www.w3.org/2000/svg",'svg');
  var xform = svg.createSVGMatrix();
  xform = xform.translate(0,0);
  console.log(xform);
  ctx.getTransform = function(){ return xform; };

  var scale = ctx.scale;
  ctx.scale = function(sx,sy){
    xform = xform.scaleNonUniform(sx,sy);
    console.log(xform);
    return scale.call(ctx,sx,sy);
  };

  var translate = ctx.translate;
  ctx.translate = function(dx,dy){
    xform = xform.translate(dx,dy);
    return translate.call(ctx,dx,dy);
  };

  var pt  = svg.createSVGPoint();
  ctx.transformedPoint = function(x,y){
    pt.x=x; pt.y=y;
    return pt.matrixTransform(xform.inverse());
  }

  ctx.fromGlobalCoord = function(x,y){
    pt.x=x; pt.y=y;
    return pt.matrixTransform(xform.inverse());
  }

  ctx.toGlobalCoord = function(x,y){
    pt.x=x; pt.y=y;
    return pt.matrixTransform(xform);
  }
}



//----------------- body-loaded code --------------



function LoadNewImage() {

  canvas = document.getElementById(canvasID);

  game = new Jigsaw();

}
