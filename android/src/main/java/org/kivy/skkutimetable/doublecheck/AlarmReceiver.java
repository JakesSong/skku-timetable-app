// AlarmReceiver.java
package org.kivy.skkutimetable.doublecheck;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;

public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "AlarmReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "🔔 알람 수신됨");

        // 수업 정보 가져오기
        int classId = intent.getIntExtra("class_id", 0);
        String className = intent.getStringExtra("class_name");
        String classRoom = intent.getStringExtra("class_room");
        String classTime = intent.getStringExtra("class_time");
        String classProfessor = intent.getStringExtra("class_professor");

        // 알림 처리 → 서비스 실행
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

        // ⏰ 다음 주 알람 재등록
        long intervalMillis = 7L * 24 * 60 * 60 * 1000;  // 1주일
        long nextTriggerTime = System.currentTimeMillis() + intervalMillis;

        Intent nextIntent = new Intent(context, AlarmReceiver.class);
        nextIntent.putExtra("class_id", classId);
        nextIntent.putExtra("class_name", className);
        nextIntent.putExtra("class_room", classRoom);
        nextIntent.putExtra("class_time", classTime);
        nextIntent.putExtra("class_professor", classProfessor);

        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }

        PendingIntent pendingIntent = PendingIntent.getBroadcast(
                context, classId, nextIntent, flags
        );

        AlarmManager alarmManager = (AlarmManager) context.getSystemService(Context.ALARM_SERVICE);
        if (alarmManager != null) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                alarmManager.setExactAndAllowWhileIdle(
                        AlarmManager.RTC_WAKEUP, nextTriggerTime, pendingIntent
                );
            } else {
                alarmManager.setExact(
                        AlarmManager.RTC_WAKEUP, nextTriggerTime, pendingIntent
                );
            }
            Log.d(TAG, "🔁 다음 주 알람 재등록 완료");
        } else {
            Log.e(TAG, "AlarmManager is null!");
        }
    }
}
