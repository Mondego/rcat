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

    WebSocketClient client = new WebSocketClient(URI.create("wss://irccloud.com"), new WebSocketClient.Listener() {
        //@Override
        public void onConnect() {
            Log.d(TAG, "Connected!");
        }

        //@Override
        public void onMessage(String message) {
            Log.d(TAG, String.format("Got string message! %s", message));
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
            Log.e(TAG, "Error!", error);
        }
    }, extraHeaders);

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.main);
    }

    public void onRunWebSocketTest(View view) {
        TextView t = (TextView)findViewById(R.id.statusText);
        t.setText("Running...");

        // Add here...
    }
}
