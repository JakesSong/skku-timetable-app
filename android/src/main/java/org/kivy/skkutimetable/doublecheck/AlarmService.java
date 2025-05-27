// AlarmService.java
package org.kivy.skkutimetable.doublecheck;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.util.Log;
import org.kivy.android.PythonActivity;

public class AlarmService extends Service {
    private static final String TAG = "AlarmService";
    private static final String CHANNEL_ID = "timetable_alarm_channel";
    private static final int NOTIFICATION_ID = 1000;
    
    @Override
    public void onCreate() {
        super.onCreate();
        Log.d(TAG, "알람 서비스 생성됨");
    }
    
    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        Log.d(TAG, "알람 서비스 시작됨");
        
        if (intent == null) {
            return START_NOT_STICKY;
        }
        
        String className = intent.getStringExtra("class_name");
        String classRoom = intent.getStringExtra("class_room");
        String classTime = intent.getStringExtra("class_time");
        String classProfessor = intent.getStringExtra("class_professor");
        
        // 알림 표시
        showNotification(className, classRoom, classTime, classProfessor);
        
        return START_NOT_STICKY;
    }
    
    private void showNotification(String className, String classRoom, String classTime, String classProfessor) {
        NotificationManager notificationManager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        
        // Android Oreo 이상에서는 채널 필요
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID,
                "수업 알림",
                NotificationManager.IMPORTANCE_HIGH
            );
            channel.setDescription("수업 시작 전 알림");
            channel.enableVibration(true);
            
            notificationManager.createNotificationChannel(channel);
        }
        
        // 메인 액티비티로 이동하는 인텐트
        Intent intent = new Intent(this, PythonActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        
        // FLAG_IMMUTABLE 필요
        int flags = PendingIntent.FLAG_UPDATE_CURRENT;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            flags |= PendingIntent.FLAG_IMMUTABLE;
        }
        
        PendingIntent pendingIntent = PendingIntent.getActivity(this, 0, intent, flags);
        
        // 알림 내용
        String title = "수업 알림: " + className;
        String message = classTime + "에 " + classRoom + "에서 " + classProfessor + " 교수님 수업이 있습니다.";
        
        // 알림 생성
        Notification.Builder builder;
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            builder = new Notification.Builder(this, CHANNEL_ID);
        } else {
            builder = new Notification.Builder(this);
        }
        
        Notification notification = builder
            .setContentTitle(title)
            .setContentText(message)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build();
        
        // 포그라운드 서비스 시작 (Android Oreo 이상 필요)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForeground(NOTIFICATION_ID, notification);
        }
        
        // 알림 표시
        notificationManager.notify(NOTIFICATION_ID, notification);
        
        // 서비스 종료
        stopSelf();
    }
    
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
