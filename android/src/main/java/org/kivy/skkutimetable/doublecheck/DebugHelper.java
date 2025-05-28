package org.kivy.skkutimetable.debug;

import android.util.Log;

public class DebugHelper {
    private static final String TAG = "DebugHelper";

    public static void printDebugMessage() {
        Log.d(TAG, "✅ DebugHelper 작동 확인 완료");
    }
}