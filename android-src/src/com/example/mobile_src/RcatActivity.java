package com.example.mobile_src;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.os.Handler;
import android.view.View;
import android.widget.TextView;
import com.external.websockets.WebSocketClient;
import org.apache.http.message.BasicNameValuePair;

import java.net.URI;
import java.nio.channels.NotYetConnectedException;
import java.util.Arrays;
import java.util.List;

public class RcatActivity extends Activity {
    /**
     * Called when the activity is first created.
     */

    private static final String TAG = "RCATClient";

    List<BasicNameValuePair> extraHeaders = Arrays.asList(
            new BasicNameValuePair("Cookie", "session=abcd")
    );

    WebSocketClient client = new WebSocketClient(URI.create("ws://10.0.2.2:9998/echo"), new WebSocketClient.Listener() {
        //@Override
        public void onConnect() {
            TextView t = (TextView)findViewById(R.id.statusText);
            t.setText("Connected successfully \n");
            Log.d(TAG, "Connected!");
        }

        //@Override
        public void onMessage(String message) {
            //TextView t = (TextView)findViewById(R.id.statusText);
            Log.d(TAG, String.format("Got string message! %s", message));
            //t.append("Message");
        }

        //@Override
        public void onMessage(byte[] data) {
            Log.d(TAG, String.format("Got binary message! %s", data.toString()));
        }

        //@Override
        public void onDisconnect(int code, String reason) {
            Log.d(TAG, String.format("Disconnected! Code: %d Reason: %s", code, reason));
        }

        //@Override
        public void onError(Exception error) {
            TextView t = (TextView)findViewById(R.id.statusText);
            Log.e(TAG, "Error!", error);
            t.append(("Error! " + error.getMessage()));
        }
    }, extraHeaders);

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.main);
    }

    public void onRunWebSocketTest(View view) {
        //client.connect();
    }
}
