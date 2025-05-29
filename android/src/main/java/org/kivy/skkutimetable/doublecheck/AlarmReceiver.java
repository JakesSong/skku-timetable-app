package org.kivy.skkutimetable.doublecheck;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.app.NotificationManager;
import android.app.Notification;
import android.app.PendingIntent;
import android.content.ComponentName;
import android.util.Log;
import android.os.Vibrator;

public class AlarmReceiver extends BroadcastReceiver {
    private static final String TAG = "AlarmReceiver";
    private static final String CHANNEL_ID = "timetable_alarm_channel";

    @Override
    public void onReceive(Context context, Intent intent) {
        // 🔥 맨 먼저 로그 출력 (이것부터 확인!)
        Log.i(TAG, "🚨🚨🚨 AlarmReceiver.onReceive() 호출됨!");
        Log.i(TAG, "📦 패키지명: " + context.getPackageName());
        Log.i(TAG, "📱 Intent: " + intent.toString());
        
        try {
            // Intent에서 데이터 추출
            String className = intent.getStringExtra("class_name");
            String classRoom = intent.getStringExtra("class_room");
            String classTime = intent.getStringExtra("class_time");
            String classProfessor = intent.getStringExtra("class_professor");
            
            // 🔥 추출된 데이터 로그 출력
            Log.i(TAG, "📚 과목명: " + className);
            Log.i(TAG, "🏛️ 강의실: " + classRoom);
            Log.i(TAG, "⏰ 시간: " + classTime);
            Log.i(TAG, "👨‍🏫 교수: " + classProfessor);
            
            // 기본값 설정
            if (className == null) className = "알 수 없는 과목";
            if (classRoom == null) classRoom = "강의실 미정";
            if (classTime == null) classTime = "시간 미정";
            if (classProfessor == null) classProfessor = "교수 미정";
            
            // 🔥 진동 먼저 실행 (즉시 반응 확인용)
            try {
                Vibrator vibrator = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
                if (vibrator != null) {
                    // 0.5초 진동
                    vibrator.vibrate(500);
                    Log.i(TAG, "📳 진동 실행 완료");
                }
            } catch (Exception e) {
                Log.e(TAG, "❌ 진동 실행 실패: " + e.getMessage());
            }
            
            // 🔥 알림 생성
            createNotification(context, className, classRoom, classTime, classProfessor);
            
            Log.i(TAG, "✅ AlarmReceiver 처리 완료!");
            
        } catch (Exception e) {
            Log.e(TAG, "❌ AlarmReceiver 처리 중 오류: " + e.getMessage());
            e.printStackTrace();
            
            // 🔥 오류 발생시에도 기본 알림 생성
            try {
                createEmergencyNotification(context, "AlarmReceiver 오류 발생");
            } catch (Exception e2) {
                Log.e(TAG, "❌ 긴급 알림 생성도 실패: " + e2.getMessage());
            }
        }
    }

    private void createNotification(Context context, String className, String classRoom, 
                                  String classTime, String classProfessor) {
        try {
            Log.i(TAG, "🔔 알림 생성 시작");
            
            NotificationManager notificationManager = 
                (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            
            if (notificationManager == null) {
                Log.e(TAG, "❌ NotificationManager가 null입니다");
                return;
            }

            // ✅ 여기에 알림 채널 생성 코드 추가!
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.O) {
                NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "TimeTable Alarm Channel",  // 사용자에게 보일 이름
                    NotificationManager.IMPORTANCE_HIGH
                );
                channel.setDescription("수업 알림용 채널입니다");
                notificationManager.createNotificationChannel(channel);
                Log.i(TAG, "✅ NotificationChannel 생성됨");
            }
            
            // 🔥 전자출결 앱 Intent 생성 (개선된 버전)
            Intent attendanceIntent = createAttendanceIntent(context);
            
            // PendingIntent 생성 (Android 12+ 호환)
            int flags = PendingIntent.FLAG_UPDATE_CURRENT;
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.M) {
                flags |= PendingIntent.FLAG_IMMUTABLE;
            }
            
            PendingIntent pendingIntent = PendingIntent.getActivity(
                context, 
                (int) System.currentTimeMillis(), // 고유한 request code
                attendanceIntent, 
                flags
            );
            
            // 알림 생성
            Notification.Builder builder = new Notification.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("🔔 " + className + " 수업 알림")
                .setContentText(classTime + " | " + classRoom + " | " + classProfessor + " 교수님")
                .setPriority(Notification.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setContentIntent(pendingIntent)
                .setVibrate(new long[]{0, 250, 250, 250});
            
            // 확장된 알림 스타일 (BigTextStyle)
            try {
                String expandedText = String.format(
                    "📚 과목: %s\n🕐 시간: %s\n🏛️ 강의실: %s\n👨‍🏫 교수: %s\n\n📱 전자출결하려면 터치하세요",
                    className, classTime, classRoom, classProfessor
                );
                
                Notification.BigTextStyle bigTextStyle = new Notification.BigTextStyle()
                    .bigText(expandedText)
                    .setSummaryText("수업 알림");
                    
                builder.setStyle(bigTextStyle);
                Log.i(TAG, "📝 BigTextStyle 설정 완료");
                
            } catch (Exception e) {
                Log.w(TAG, "⚠️ BigTextStyle 설정 실패: " + e.getMessage());
            }
            
            // 알림 표시
            int notificationId = className.hashCode(); // 과목별 고유 ID
            notificationManager.notify(notificationId, builder.build());
            
            Log.i(TAG, "✅ 알림 생성 완료: " + className);
            
        } catch (Exception e) {
            Log.e(TAG, "❌ 알림 생성 실패: " + e.getMessage());
            e.printStackTrace();
        }
    }
    
    private Intent createAttendanceIntent(Context context) {
        try {
            // 🔥 방법 1: PackageManager로 전자출결 앱 Intent 가져오기
            String attendancePackage = "edu.skku.attend";
            Intent intent = context.getPackageManager().getLaunchIntentForPackage(attendancePackage);
            
            if (intent != null) {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
                Log.i(TAG, "✅ 전자출결 앱 Intent 생성 성공 (PackageManager)");
                return intent;
            }
            
            // 🔥 방법 2: 직접 액티비티 지정
            intent = new Intent();
            intent.setComponent(new ComponentName(
                attendancePackage, 
                "edu.skku.attend.ui.activity.IntroActivity"
            ));
            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
            Log.i(TAG, "✅ 전자출결 앱 Intent 생성 성공 (직접 지정)");
            return intent;
            
        } catch (Exception e) {
            Log.w(TAG, "⚠️ 전자출결 앱 Intent 생성 실패: " + e.getMessage());
        }
        
        // 🔥 방법 3: 실패시 Play Store로
        try {
            Intent storeIntent = new Intent(Intent.ACTION_VIEW);
            storeIntent.setData(android.net.Uri.parse("market://details?id=edu.skku.attend"));
            storeIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            Log.i(TAG, "📱 Play Store Intent로 대체");
            return storeIntent;
        } catch (Exception e2) {
            Log.e(TAG, "❌ Play Store Intent도 실패: " + e2.getMessage());
        }
        
        // 🔥 최후의 수단: 시간표 앱 자체 열기
        Intent fallbackIntent = new Intent(context, org.kivy.android.PythonActivity.class);
        fallbackIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        Log.i(TAG, "🔄 시간표 앱으로 대체");
        return fallbackIntent;
    }
    
    private void createEmergencyNotification(Context context, String errorMessage) {
        try {
            Log.i(TAG, "🚨 긴급 알림 생성: " + errorMessage);
            
            NotificationManager notificationManager = 
                (NotificationManager) context.getSystemService(Context.NOTIFICATION_SERVICE);
            
            if (notificationManager == null) return;
            
            Notification.Builder builder = new Notification.Builder(context, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("🚨 알람 시스템 오류")
                .setContentText(errorMessage)
                .setPriority(Notification.PRIORITY_HIGH)
                .setAutoCancel(true)
                .setVibrate(new long[]{0, 500, 200, 500});
            
            notificationManager.notify(99999, builder.build());
            Log.i(TAG, "✅ 긴급 알림 생성 완료");
            
        } catch (Exception e) {
            Log.e(TAG, "❌ 긴급 알림 생성도 실패: " + e.getMessage());
        }
    }
}
