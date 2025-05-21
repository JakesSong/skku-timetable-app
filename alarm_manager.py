# alarm_manager.py
from datetime import datetime, timedelta
import os
import pickle

class AlarmManager:
    def __init__(self, app=None):
        self.app = app
        self.alarms = {}  # class_id를 키로 사용
        self.load_alarms()
        
    def load_alarms(self):
        """저장된 알람 데이터 로드"""
        try:
            # Android 환경에서는 환경 변수 사용
            if 'ANDROID_STORAGE' in os.environ:
                alarms_file = os.path.join(os.getenv('ANDROID_STORAGE', ''), 'alarms.pkl')
            else:
                alarms_file = 'alarms.pkl'
                
            if os.path.exists(alarms_file):
                with open(alarms_file, 'rb') as f:
                    self.alarms = pickle.load(f)
                print(f"알람 {len(self.alarms)}개 로드됨")
        except Exception as e:
            print(f"알람 로드 오류: {e}")
            self.alarms = {}
    
    def save_alarms(self):
        """알람 데이터 저장"""
        try:
            # Android 환경에서는 환경 변수 사용
            if 'ANDROID_STORAGE' in os.environ:
                alarms_file = os.path.join(os.getenv('ANDROID_STORAGE', ''), 'alarms.pkl')
            else:
                alarms_file = 'alarms.pkl'
                
            with open(alarms_file, 'wb') as f:
                pickle.dump(self.alarms, f)
            print(f"알람 {len(self.alarms)}개 저장됨")
            return True
        except Exception as e:
            print(f"알람 저장 오류: {e}")
            return False
    
    def schedule_alarm(self, class_id, class_data, minutes_before=5):
        """수업 알람 예약"""
        if not class_data:
            return False
            
        from jnius import autoclass
        import time
        
        try:
            # Android 클래스들
            Context = autoclass('android.content.Context')
            PendingIntent = autoclass('android.app.PendingIntent')
            Intent = autoclass('android.content.Intent')
            Calendar = autoclass('java.util.Calendar')
            AlarmManager = autoclass('android.app.AlarmManager')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            # 현재 컨텍스트와 알람 매니저 가져오기
            context = PythonActivity.mActivity.getApplicationContext()
            alarm_service = context.getSystemService(Context.ALARM_SERVICE)
            
            # 요일 매핑
            day_map = {
                "Monday": Calendar.MONDAY,
                "Tuesday": Calendar.TUESDAY,
                "Wednesday": Calendar.WEDNESDAY,
                "Thursday": Calendar.THURSDAY,
                "Friday": Calendar.FRIDAY,
                "월요일": Calendar.MONDAY,
                "화요일": Calendar.TUESDAY,
                "수요일": Calendar.WEDNESDAY,
                "목요일": Calendar.THURSDAY,
                "금요일": Calendar.FRIDAY
            }
            
            # 시간 파싱
            start_time = class_data['start_time']
            hour, minute = map(int, start_time.split(':'))
            
            # 알람 시간 계산 (수업 시작 N분 전)
            calendar = Calendar.getInstance()
            calendar.setTimeInMillis(int(time.time() * 1000))
            calendar.set(Calendar.DAY_OF_WEEK, day_map[class_data['day']])
            calendar.set(Calendar.HOUR_OF_DAY, hour)
            calendar.set(Calendar.MINUTE, minute - minutes_before)
            calendar.set(Calendar.SECOND, 0)
            
            # 현재 시간보다 이전이면 다음 주로 설정
            if calendar.getTimeInMillis() < int(time.time() * 1000):
                calendar.add(Calendar.WEEK_OF_YEAR, 1)
            
            # 브로드캐스트 인텐트 생성
            intent = Intent()
            intent.setClassName(context, 'org.kivy.android.AlarmReceiver')
            intent.putExtra('class_name', class_data['name'])
            intent.putExtra('class_room', class_data['room'])
            intent.putExtra('class_time', class_data['start_time'])
            intent.putExtra('class_professor', class_data['professor'])
            
            # 각 알람에 고유한 ID 사용
            alarm_id = int(class_id)
            
            # PendingIntent 생성 (FLAG_IMMUTABLE 필요)
            FLAG_IMMUTABLE = 67108864  # PendingIntent.FLAG_IMMUTABLE의 값
            pending_intent = PendingIntent.getBroadcast(
                context, alarm_id, intent, 
                PendingIntent.FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE
            )
            
            # 알람 예약 (매주 반복)
            alarm_service.setRepeating(
                AlarmManager.RTC_WAKEUP, 
                calendar.getTimeInMillis(),
                7 * 24 * 60 * 60 * 1000,  # 일주일마다 반복
                pending_intent
            )
            
            # 알람 정보 저장
            self.alarms[class_id] = {
                'alarm_id': alarm_id,
                'class_data': class_data,
                'minutes_before': minutes_before,
                'next_alarm_time': calendar.getTimeInMillis()
            }
            self.save_alarms()
            
            print(f"알람 예약 성공: {class_data['name']} - {start_time}의 {minutes_before}분 전")
            return True
            
        except Exception as e:
            print(f"알람 예약 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cancel_alarm(self, class_id):
        """수업 알람 취소"""
        if class_id not in self.alarms:
            return False
            
        try:
            from jnius import autoclass
            
            # Android 클래스들
            Context = autoclass('android.content.Context')
            PendingIntent = autoclass('android.app.PendingIntent')
            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            AlarmManager = autoclass('android.app.AlarmManager')
            
            # 현재 컨텍스트와 알람 매니저 가져오기
            context = PythonActivity.mActivity.getApplicationContext()
            alarm_service = context.getSystemService(Context.ALARM_SERVICE)
            
            # 알람 정보 가져오기
            alarm_info = self.alarms[class_id]
            alarm_id = alarm_info['alarm_id']
            
            # 인텐트 및 PendingIntent 생성
            intent = Intent()
            intent.setClassName(context, 'org.kivy.android.AlarmReceiver')
            
            # FLAG_IMMUTABLE 값
            FLAG_IMMUTABLE = 67108864
            pending_intent = PendingIntent.getBroadcast(
                context, alarm_id, intent, 
                PendingIntent.FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE
            )
            
            # 알람 취소
            alarm_service.cancel(pending_intent)
            
            # 알람 정보 삭제
            del self.alarms[class_id]
            self.save_alarms()
            
            print(f"알람 취소 성공: ID {alarm_id}")
            return True
            
        except Exception as e:
            print(f"알람 취소 오류: {e}")
            return False