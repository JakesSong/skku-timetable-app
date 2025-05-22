from datetime import datetime, timedelta
import os
import pickle

class AlarmManager:
    def __init__(self, app=None):
        self.app = app
        self.alarms = {}  # class_id를 키로 사용
        self.is_android = 'ANDROID_STORAGE' in os.environ
        
        # 알람 파일 경로 설정
        if self.is_android:
            android_data_dir = os.path.dirname(os.path.abspath(__file__))
            self.alarms_file = os.path.join(android_data_dir, 'alarms.pkl')
            print(f"Android 알람 파일 경로: {self.alarms_file}")
        else:
            self.alarms_file = 'alarms.pkl'
            print(f"PC 알람 파일 경로: {self.alarms_file}")
        
        # Android 알람 관련 초기화
        if self.is_android:
            self.init_android_alarm()
        
        # 저장된 알람 데이터 로드
        self.load_alarms()
        
    def init_android_alarm(self):
        """Android 알람 시스템 초기화"""
        try:
            from jnius import autoclass
            
            # Android 클래스들 미리 로드
            self.Context = autoclass('android.content.Context')
            self.PendingIntent = autoclass('android.app.PendingIntent')
            self.Intent = autoclass('android.content.Intent')
            self.Calendar = autoclass('java.util.Calendar')
            self.AlarmManager = autoclass('android.app.AlarmManager')
            self.PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            # 컨텍스트와 알람 매니저 가져오기
            self.context = self.PythonActivity.mActivity.getApplicationContext()
            self.alarm_service = self.context.getSystemService(self.Context.ALARM_SERVICE)
            
            # FLAG 값들
            self.FLAG_IMMUTABLE = 67108864  # PendingIntent.FLAG_IMMUTABLE
            self.FLAG_UPDATE_CURRENT = 134217728  # PendingIntent.FLAG_UPDATE_CURRENT
            
            print("✅ Android 알람 시스템 초기화 완료")
            
        except Exception as e:
            print(f"❌ Android 알람 시스템 초기화 실패: {e}")
            import traceback
            traceback.print_exc()
            self.is_android = False
        
    def load_alarms(self):
        """저장된 알람 데이터 로드"""
        try:
            if os.path.exists(self.alarms_file):
                with open(self.alarms_file, 'rb') as f:
                    self.alarms = pickle.load(f)
                print(f"✅ 알람 {len(self.alarms)}개 로드됨")
            else:
                print("📁 저장된 알람 데이터가 없습니다.")
                self.alarms = {}
        except Exception as e:
            print(f"❌ 알람 로드 오류: {e}")
            self.alarms = {}
    
    def save_alarms(self):
        """알람 데이터 저장"""
        try:
            # 디렉토리 생성 (필요한 경우)
            alarm_dir = os.path.dirname(self.alarms_file)
            if alarm_dir and not os.path.exists(alarm_dir):
                os.makedirs(alarm_dir, exist_ok=True)
            
            with open(self.alarms_file, 'wb') as f:
                pickle.dump(self.alarms, f)
            print(f"✅ 알람 {len(self.alarms)}개 저장됨")
            return True
        except Exception as e:
            print(f"❌ 알람 저장 오류: {e}")
            return False
    
    def schedule_alarm(self, class_id, class_data, minutes_before=5):
        """수업 알람 예약"""
        if not class_data:
            print("❌ 클래스 데이터가 없습니다.")
            return False
        
        if not self.is_android:
            print(f"💻 PC 환경: {class_data['name']} 알람 예약 시뮬레이션")
            # PC 환경에서는 데이터만 저장
            self.alarms[class_id] = {
                'class_data': class_data,
                'minutes_before': minutes_before,
                'created_at': datetime.now().isoformat()
            }
            self.save_alarms()
            return True
        
        try:
            # 요일 매핑
            day_map = {
                "Monday": self.Calendar.MONDAY,
                "Tuesday": self.Calendar.TUESDAY,
                "Wednesday": self.Calendar.WEDNESDAY,
                "Thursday": self.Calendar.THURSDAY,
                "Friday": self.Calendar.FRIDAY,
                "월요일": self.Calendar.MONDAY,
                "화요일": self.Calendar.TUESDAY,
                "수요일": self.Calendar.WEDNESDAY,
                "목요일": self.Calendar.THURSDAY,
                "금요일": self.Calendar.FRIDAY
            }
            
            class_day = class_data['day']
            if class_day not in day_map:
                print(f"❌ 지원하지 않는 요일: {class_day}")
                return False
            
            # 시간 파싱
            try:
                start_time = class_data['start_time']
                hour, minute = map(int, start_time.split(':'))
            except Exception as e:
                print(f"❌ 시간 파싱 오류: {e}")
                return False
            
            # 알람 시간 계산 (수업 시작 N분 전)
            calendar = self.Calendar.getInstance()
            current_time = int(datetime.now().timestamp() * 1000)
            calendar.setTimeInMillis(current_time)
            
            # 해당 요일로 설정
            calendar.set(self.Calendar.DAY_OF_WEEK, day_map[class_day])
            calendar.set(self.Calendar.HOUR_OF_DAY, hour)
            calendar.set(self.Calendar.MINUTE, minute - minutes_before)
            calendar.set(self.Calendar.SECOND, 0)
            calendar.set(self.Calendar.MILLISECOND, 0)
            
            # 현재 시간보다 이전이면 다음 주로 설정
            if calendar.getTimeInMillis() <= current_time:
                calendar.add(self.Calendar.WEEK_OF_YEAR, 1)
            
            # 브로드캐스트 인텐트 생성
            intent = self.Intent()
            intent.setAction("org.kivy.skkutimetable.TIMETABLE_ALARM")
            intent.putExtra('class_id', str(class_id))
            intent.putExtra('class_name', class_data['name'])
            intent.putExtra('class_room', class_data['room'])
            intent.putExtra('class_time', class_data['start_time'])
            intent.putExtra('class_professor', class_data['professor'])
            intent.putExtra('minutes_before', minutes_before)
            
            # 각 알람에 고유한 ID 사용
            alarm_id = int(class_id) if isinstance(class_id, (int, str)) else hash(str(class_id)) % 1000000
            
            # PendingIntent 생성
            pending_intent = self.PendingIntent.getBroadcast(
                self.context, 
                alarm_id, 
                intent, 
                self.FLAG_UPDATE_CURRENT | self.FLAG_IMMUTABLE
            )
            
            # 알람 예약 (매주 반복)
            alarm_time = calendar.getTimeInMillis()
            one_week_millis = 7 * 24 * 60 * 60 * 1000  # 일주일
            
            self.alarm_service.setRepeating(
                self.AlarmManager.RTC_WAKEUP, 
                alarm_time,
                one_week_millis,
                pending_intent
            )
            
            # 알람 정보 저장
            alarm_datetime = datetime.fromtimestamp(alarm_time / 1000)
            self.alarms[class_id] = {
                'alarm_id': alarm_id,
                'class_data': class_data,
                'minutes_before': minutes_before,
                'next_alarm_time': alarm_time,
                'next_alarm_datetime': alarm_datetime.isoformat(),
                'created_at': datetime.now().isoformat()
            }
            self.save_alarms()
            
            print(f"✅ 알람 예약 성공: {class_data['name']}")
            print(f"📅 다음 알람 시간: {alarm_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"⏰ 수업 시작 {minutes_before}분 전 알림")
            return True
            
        except Exception as e:
            print(f"❌ 알람 예약 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cancel_alarm(self, class_id):
        """수업 알람 취소"""
        if class_id not in self.alarms:
            print(f"⚠️ 알람 ID {class_id}를 찾을 수 없습니다.")
            return False
        
        if not self.is_android:
            print(f"💻 PC 환경: 클래스 {class_id} 알람 취소 시뮬레이션")
            del self.alarms[class_id]
            self.save_alarms()
            return True
            
        try:
            # 알람 정보 가져오기
            alarm_info = self.alarms[class_id]
            alarm_id = alarm_info['alarm_id']
            
            # 인텐트 생성 (취소용)
            intent = self.Intent()
            intent.setAction("org.kivy.skkutimetable.TIMETABLE_ALARM")
            
            # PendingIntent 생성 (취소용)
            pending_intent = self.PendingIntent.getBroadcast(
                self.context, 
                alarm_id, 
                intent, 
                self.FLAG_UPDATE_CURRENT | self.FLAG_IMMUTABLE
            )
            
            # 알람 취소
            self.alarm_service.cancel(pending_intent)
            
            # 알람 정보 삭제
            class_name = alarm_info['class_data']['name']
            del self.alarms[class_id]
            self.save_alarms()
            
            print(f"✅ 알람 취소 성공: {class_name} (ID: {alarm_id})")
            return True
            
        except Exception as e:
            print(f"❌ 알람 취소 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def schedule_class_alarm(self, class_id, name, day, start_time, room, professor, minutes_before):
        """편의 메서드: 클래스 정보로 알람 예약"""
        class_data = {
            'id': class_id,
            'name': name,
            'day': day,
            'start_time': start_time,
            'room': room,
            'professor': professor
        }
        return self.schedule_alarm(class_id, class_data, minutes_before)
    
    def get_scheduled_alarms(self):
        """예약된 알람 목록 반환"""
        alarm_list = []
        for class_id, alarm_info in self.alarms.items():
            class_data = alarm_info['class_data']
            alarm_summary = {
                'class_id': class_id,
                'class_name': class_data['name'],
                'day': class_data['day'],
                'start_time': class_data['start_time'],
                'room': class_data['room'],
                'minutes_before': alarm_info['minutes_before'],
                'created_at': alarm_info.get('created_at', 'Unknown')
            }
            
            if 'next_alarm_datetime' in alarm_info:
                alarm_summary['next_alarm'] = alarm_info['next_alarm_datetime']
            
            alarm_list.append(alarm_summary)
        
        return alarm_list
    
    def clear_all_alarms(self):
        """모든 알람 취소"""
        if not self.alarms:
            print("📭 취소할 알람이 없습니다.")
            return True
        
        alarm_count = len(self.alarms)
        cancelled_count = 0
        
        # 모든 알람 취소
        for class_id in list(self.alarms.keys()):
            if self.cancel_alarm(class_id):
                cancelled_count += 1
        
        print(f"✅ {cancelled_count}/{alarm_count}개 알람 취소 완료")
        return cancelled_count == alarm_count
    
    def update_alarm(self, class_id, class_data, minutes_before=5):
        """알람 업데이트 (기존 알람 취소 후 새로 생성)"""
        # 기존 알람 취소
        if class_id in self.alarms:
            self.cancel_alarm(class_id)
        
        # 새 알람 생성
        return self.schedule_alarm(class_id, class_data, minutes_before)
    
    def get_alarm_info(self, class_id):
        """특정 알람 정보 반환"""
        if class_id in self.alarms:
            return self.alarms[class_id]
        else:
            print(f"⚠️ 알람 ID {class_id}를 찾을 수 없습니다.")
            return None
    
    def is_alarm_set(self, class_id):
        """알람 설정 여부 확인"""
        return class_id in self.alarms
    
    def get_next_alarm_time(self, class_id):
        """다음 알람 시간 반환"""
        if class_id in self.alarms and 'next_alarm_datetime' in self.alarms[class_id]:
            return self.alarms[class_id]['next_alarm_datetime']
        return None
