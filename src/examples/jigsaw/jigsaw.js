
// ---------------- constants ---------------

var game = null;
var canvasID = "canJigsaw";

// -------------------  code ---------------
﻿
function imageBlock(no, x, y) {

    this.no = no;
    this.x = x;
    this.y = y;
    this.isSelected = false;
}


function jigsaw() {

    var MAIN_IMG_WIDTH = 800;
    var MAIN_IMG_HEIGHT = 600;


    var BLOCK_IMG_WIDTH = 600;
    var BLOCK_IMG_HEIGHT = 450;


    var TOTAL_ROWS = 2;
    var TOTAL_COLUMNS = 2;

    var TOTAL_PIECES = TOTAL_ROWS * TOTAL_COLUMNS;

    var IMG_WIDTH = Math.round(MAIN_IMG_WIDTH / TOTAL_COLUMNS);
    var IMG_HEIGHT = Math.round(MAIN_IMG_HEIGHT / TOTAL_ROWS);


    var BLOCK_WIDTH = 0; // Math.round(BLOCK_IMG_WIDTH / TOTAL_COLUMNS);
    var BLOCK_HEIGHT = 0; // Math.round(BLOCK_IMG_HEIGHT / TOTAL_ROWS);



    image1 = new Image();
    image1.src = "img/BugsLife.jpg";
    this.image1 = image1
    
    var canvas;
    var ctx;

    this.canvasID = canvasID;
    
    this.top = 0;
    this.left = 0;

    this.imageBlockList = new Array();


    this.blockList = new Array();

    this.selectedBlock = null;


    this.mySelf = this;


    this.initDrawing = function () {
        mySelf = this;
        selectedBlock = null;
        canvas = document.getElementById(canvasID);

        // register events
        //canvas.ondblclick = handleOnMouseDbClick;
        canvas.onmousedown = handleOnMouseDown;
        canvas.onmouseup = handleOnMouseUp;
        canvas.onmouseout = handleOnMouseOut;
        canvas.onmousemove = handleOnMouseMove;

        ctx = canvas.getContext('2d');
        
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

        var x1 = BLOCK_IMG_WIDTH + 20;
        var x2 = canvas.width - 1000;
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
       
       
       ctx.strokeStyle = "#222"; //gray
        
        ctx.lineWidth = 1;
        ctx.beginPath();
        
        // draw verticle lines
        for (var i = 0; i <= TOTAL_COLUMNS; i++) {
            var x = BLOCK_WIDTH * i;
            ctx.moveTo(x, 0);
            ctx.lineTo(x, 450);
        }
        
        // draw horizontal lines
        for (var i = 0; i <= TOTAL_ROWS; i++) {
            var y = BLOCK_HEIGHT * i;
            ctx.moveTo(0, y);
            ctx.lineTo(600, y);
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
        interval = setInterval(function () { mySelf.ClearGame(); }, 100);
    }

    this.ClearGame = function () {
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
          //  alert("Congrats....");

        }
    };

    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////
    ///////////////////////////////////////// EVENTS
    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////




    function handleOnMouseOut(e) {

        // remove old selected
        if (selectedBlock != null) {

            imageBlockList[selectedBlock.no].isSelected = false;
            selectedBlock = null;
            DrawGame();

        }

    }

    function handleOnMouseDown(e) {

        //clickx = e.pageX
        //clicky = e.pageY 
        // TODO: clicking bug here?
        clickx = e.clientX
        clicky = e.clientY
        
        console.log(clickx + ' ' + clicky)
        console.log(imageBlockList)
        
        // remove old selected
        if (selectedBlock != null) {

            imageBlockList[selectedBlock.no].isSelected = false;

        }

        selectedBlock = GetImageBlock(imageBlockList, clickx, clicky);

        if (selectedBlock) {
            imageBlockList[selectedBlock.no].isSelected = true;
        }

    }


    function handleOnMouseUp(e) {

        if (selectedBlock) {
            var index = selectedBlock.no;
            //   alert(index);

            var block = GetImageBlock(blockList, e.pageX, e.pageY);
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

            selectedBlock.x = e.pageX  - 25;
            selectedBlock.y = e.pageY  - 25;

            DrawGame();

        }
    }

    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////
    ///////////////////////////////////////// HELPER METHODS
    ///////////////////////////////////////////////////////////////////////////////////////////////////////////////

    function clear(c) {
        c.clearRect(0, 0, canvas.width, canvas.height);
    }

    function randomXtoY(minVal, maxVal, decimals) {
        var randVal = minVal + (Math.random() * (maxVal - minVal));
        var val = typeof decimals == 'undefined' ? Math.round(randVal) : randVal.toFixed(decimals);

        return Math.round(val);
    }


    function GetImageBlock(imglist, x, y) {

        //for (var i = 0; i < list.length; i++) {
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
                //alert("found: " + imgBlock.no);

                var img = new imageBlock(imgBlock.no, imgBlock.x, imgBlock.y);
                //drawImageBlock(img);
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
                //drawImageBlock(img);
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

}



// ----------------- body-loaded code --------------



function LoadNewImage() {
   
   canvas = document.getElementById(canvasID);
   
   game = new jigsaw();
   game.initDrawing();
}





