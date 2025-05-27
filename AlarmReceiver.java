// AlarmReceiver.java
package org.kivy.skkutimetable.doublecheck;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "AlarmReceiver";
    
    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "알람 수신됨");
        
        String className = intent.getStringExtra("class_name");
        String classRoom = intent.getStringExtra("class_room");
        String classTime = intent.getStringExtra("class_time");
        String classProfessor = intent.getStringExtra("class_professor");
        
        // 알림 서비스 시작
        Intent serviceIntent = new Intent(context, AlarmService.class);
        serviceIntent.putExtra("class_name", className);
        serviceIntent.putExtra("class_room", classRoom);
        serviceIntent.putExtra("class_time", classTime);
        serviceIntent.putExtra("class_professor", classProfessor);
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            context.startForegroundService(serviceIntent);
        } else {
            context.startService(serviceIntent);
        }
    }
}
