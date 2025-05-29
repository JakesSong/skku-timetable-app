// AlarmReceiver.java - 수정된 버전
package org.kivy.skkutimetable.doublecheck;

import android.app.AlarmManager;
import android.app.PendingIntent;
import android.app.NotificationManager;
import android.app.NotificationChannel;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.util.Log;
import androidx.core.app.NotificationCompat; 

public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "AlarmReceiver";

    @Override
    public void onReceive(Context context, Intent intent) {
        Log.d(TAG, "🔔 알람 수신됨!");
        
        // 🔥 즉시 테스트 알림 표시
        showTestNotification(context);

        // 수업 정보 가져오기
        int classId = intent.getIntExtra("class_id", 0);
        String className = intent.getStringExtra("class_name");
        String classRoom = intent.getStringExtra("class_room");
        String classTime = intent.getStringExtra("class_time");
        String classProfessor = intent.getStringExtra("class_professor");

        Log.d(TAG, String.format("📚 수업 정보: %s, %s, %s, %s", 
               className, classRoom, classTime, classProfessor));

        // 알림 처리 → 서비스 실행
        Intent serviceIntent = new Intent(context, AlarmService.class);
        serviceIntent.putExtra("class_name", className);
        serviceIntent.putExtra("class_room", classRoom);
        serviceIntent.putExtra("class_time", classTime);
        serviceIntent.putExtra("class_professor", classProfessor);

        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(serviceIntent);
            } else {
                context.startService(serviceIntent);
            }
            Log.d(TAG, "✅ 서비스 시작 성공");
        } catch (Exception e) {
            Log.e(TAG, "❌ 서비스 시작 실패: " + e.getMessage());
        }

        // ⏰ 다음 주 알람 재등록
        scheduleNextWeekAlarm(context, intent, classId, className, classRoom, classTime, classProfessor);
    }
    
    private void showTestNotification(Context context) {
        try {
            NotificationManager notificationManager = 
                (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            
            // 채널 생성 (Android O 이상)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                NotificationChannel channel = new NotificationChannel(
                    "timetable_alarm_channel",
                    "시간표 알람",
                    NotificationManager.IMPORTANCE_HIGH
                );
                notificationManager.createNotificationChannel(channel);
            }
            
            // 📱 즉시 테스트 알림 표시
            NotificationCompat.Builder builder = new NotificationCompat.Builder(context, "timetable_alarm_channel")
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle("🔔 알람 테스트 성공!")
                .setContentText("AlarmReceiver가 성공적으로 호출되었습니다.")
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true);
            
            notificationManager.notify(9999, builder.build());
            Log.d(TAG, "✅ 테스트 알림 표시 완료");
            
        } catch (Exception e) {
            Log.e(TAG, "❌ 테스트 알림 표시 실패: " + e.getMessage());
        }
    }
    
    private void scheduleNextWeekAlarm(Context context, Intent originalIntent, 
                                     int classId, String className, String classRoom, 
                                     String classTime, String classProfessor) {
        try {
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
                Log.e(TAG, "❌ AlarmManager is null!");
            }
        } catch (Exception e) {
            Log.e(TAG, "❌ 다음 주 알람 재등록 실패: " + e.getMessage());
        }
    }
}
