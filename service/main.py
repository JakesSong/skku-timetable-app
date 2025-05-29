# service/main.py
import os
import sys
from time import sleep
from datetime import datetime, timedelta
import pickle

def load_alarms():
    """저장된 알람 정보 로드"""
    try:
        # 메인 앱과 동일한 경로에서 알람 파일 로드
        alarm_file = os.path.join(os.path.dirname(__file__), '..', 'alarms.pkl')
        with open(alarm_file, 'rb') as f:
            alarms = pickle.load(f)
            print(f"✅ 알람 {len(alarms)}개 로드 완료")
            return alarms
    except Exception as e:
        print(f"알람 데이터 로드 실패: {e}")
        return {}

def save_alarms(alarms):
    """알람 정보 저장"""
    try:
        alarm_file = os.path.join(os.path.dirname(__file__), '..', 'alarms.pkl')
        with open(alarm_file, 'wb') as f:
            pickle.dump(alarms, f)
        print(f"✅ 알람 {len(alarms)}개 저장 완료")
        return True
    except Exception as e:
        print(f"알람 데이터 저장 실패: {e}")
        return False

def create_notification(class_name, class_room, class_time, class_professor):
    """백그라운드에서 알림 생성"""
    try:
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        
        Notification = autoclass('android.app.Notification')
        NotificationManager = autoclass('android.app.NotificationManager')
        Builder = autoclass('android.app.Notification$Builder')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')
        
        # 🔥 중요: mActivity가 None일 수 있으므로 체크
        if not hasattr(PythonActivity, 'mActivity') or PythonActivity.mActivity is None:
            print("❌ PythonActivity.mActivity가 None - 서비스 환경")
            return False
        
        context = PythonActivity.mActivity
        channel_id = "timetable_alarm_channel"
        
        # 전자출결 앱 Intent
        package_name = 'edu.skku.attend'
        pm = context.getPackageManager()
        attendance_intent = pm.getLaunchIntentForPackage(package_name)
        
        if not attendance_intent:
            # 시간표 앱으로 폴백
            attendance_intent = Intent(context, PythonActivity)
            attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        
        # Android 12+ 호환 FLAG_IMMUTABLE
        FLAG_IMMUTABLE = 67108864
        FLAG_UPDATE_CURRENT = 134217728
        
        pending_intent = PendingIntent.getActivity(
            context, 
            hash(class_name) % 10000,  # 고유 request code
            attendance_intent, 
            FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE
        )
        
        # 알림 생성
        builder = Builder(context, channel_id)
        builder.setSmallIcon(context.getApplicationInfo().icon)
        builder.setContentTitle(f"🔔 수업 알림: {class_name}")
        builder.setContentText(f"{class_time} | {class_room} | {class_professor} 교수님")
        
        # 확장 텍스트
        try:
            BigTextStyle = autoclass('android.app.Notification$BigTextStyle')
            big_text_style = BigTextStyle()
            expanded_text = (
                f"📚 과목: {class_name}\n"
                f"🕐 시간: {class_time}\n"
                f"🏛️ 강의실: {class_room}\n"
                f"👨‍🏫 교수: {class_professor} 교수님\n\n"
                f"📱 전자출결하려면 터치하세요"
            )
            big_text_style.bigText(expanded_text)
            builder.setStyle(big_text_style)
        except Exception as style_e:
            print(f"BigTextStyle 설정 실패: {style_e}")
        
        builder.setPriority(Notification.PRIORITY_HIGH)
        builder.setContentIntent(pending_intent)
        builder.setAutoCancel(True)
        builder.setVibrate([0, 250, 250, 250])
        
        # 알림 표시
        notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
        notification_manager.notify(hash(class_name) % 10000, builder.build())
        
        print(f"✅ 백그라운드 알림 생성: {class_name}")
        return True
        
    except Exception as e:
        print(f"❌ 백그라운드 알림 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_alarms():
    """알람 시간 체크 및 알림 생성"""
    alarms = load_alarms()
    if not alarms:
        print("📭 확인할 알람이 없습니다")
        return
    
    now = datetime.now()
    alarms_to_remove = []
    
    print(f"⏰ 현재 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📋 등록된 알람 {len(alarms)}개 확인 중...")
    
    for alarm_id, alarm_data in alarms.items():
        try:
            # 알람 시간이 지났는지 체크
            alarm_time = alarm_data.get('alarm_time')
            if isinstance(alarm_time, str):
                # 문자열이면 datetime으로 변환
                alarm_time = datetime.fromisoformat(alarm_time)
            
            if alarm_time:
                print(f"🔍 알람 ID {alarm_id}: {alarm_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                if now >= alarm_time:
                    print(f"🔔 알람 시간 도달! ID: {alarm_id}")
                    
                    # 알림 생성
                    success = create_notification(
                        alarm_data.get('class_name', '수업'),
                        alarm_data.get('class_room', '강의실'), 
                        alarm_data.get('class_time', '시간'),
                        alarm_data.get('class_professor', '교수님')
                    )
                    
                    if success:
                        # 알람 제거 목록에 추가 (한 번만 울림)
                        alarms_to_remove.append(alarm_id)
                else:
                    time_diff = alarm_time - now
                    print(f"⏳ 알람까지 {time_diff.total_seconds() / 60:.1f}분 남음")
                
        except Exception as e:
            print(f"알람 체크 오류 (ID: {alarm_id}): {e}")
            import traceback
            traceback.print_exc()
    
    # 사용된 알람 제거
    if alarms_to_remove:
        for alarm_id in alarms_to_remove:
            if alarm_id in alarms:
                del alarms[alarm_id]
        save_alarms(alarms)
        print(f"✅ {len(alarms_to_remove)}개 알람 처리 완료")

# 🔥 중요: 문법 수정 - **name** → __name__
if __name__ == '__main__':
    print("🚀 백그라운드 알림 서비스 시작")
    
    # 포그라운드 서비스로 실행
    try:
        from jnius import autoclass
        PythonService = autoclass('org.kivy.android.PythonService')
        
        if hasattr(PythonService, 'mService') and PythonService.mService:
            PythonService.mService.setAutoRestartService(True)
            
            # 포그라운드 알림 생성 (서비스 유지용)
            PythonService.mService.startForeground(
                'timetable_service',
                '시간표 알림 서비스가 실행 중입니다'
            )
            print("✅ 포그라운드 서비스 시작")
        else:
            print("⚠️ PythonService.mService 접근 불가")
            
    except Exception as e:
        print(f"❌ 포그라운드 서비스 시작 실패: {e}")
        import traceback
        traceback.print_exc()
    
    # 메인 루프
    check_count = 0
    while True:
        try:
            check_count += 1
            print(f"\n🔄 알람 체크 #{check_count}")
            check_alarms()
            print("😴 30초 대기 중...")
            sleep(30)  # 30초마다 체크
        except Exception as e:
            print(f"서비스 오류: {e}")
            import traceback
            traceback.print_exc()
            sleep(60)  # 오류 시 1분 대기
