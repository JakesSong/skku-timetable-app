import json
import os
from datetime import datetime

class TimeTableStorage:
    def __init__(self):
        # Android 환경 감지 및 적절한 경로 설정
        if 'ANDROID_STORAGE' in os.environ:
            # Android 앱 전용 데이터 디렉토리 사용
            android_data_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_dir = os.path.join(android_data_dir, 'timetable_data')
            print(f"Android 환경: 데이터 디렉토리 = {self.data_dir}")
        else:
            # PC 개발 환경
            self.data_dir = os.path.join(os.path.expanduser("~"), ".timetable_app")
            print(f"PC 환경: 데이터 디렉토리 = {self.data_dir}")
        
        self.data_file = os.path.join(self.data_dir, "timetable_data.json")
        
        # 디렉토리 생성 (안전하게)
        try:
            if not os.path.exists(self.data_dir):
                os.makedirs(self.data_dir)
            print(f"✅ 데이터 디렉토리 확인/생성 완료: {self.data_dir}")
        except PermissionError as e:
            print(f"❌ 디렉토리 생성 실패: {e}")
            # 대체 경로 시도 (앱 내부 디렉토리)
            self.data_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_file = os.path.join(self.data_dir, "timetable_data.json")
            print(f"🔄 대체 경로 사용: {self.data_dir}")
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            # 최후의 수단: 현재 디렉토리 사용
            self.data_dir = "."
            self.data_file = "timetable_data.json"
            print(f"🆘 최후 대체 경로: {self.data_dir}")
    
    def save_classes(self, classes_data):
        """시간표 데이터를 JSON 파일로 저장"""
        try:
            # 리스트로 변환
            serializable_data = []
            for class_id, class_data in classes_data.items():
                # 데이터 복사 (원본 보호)
                class_copy = class_data.copy()
                
                # 색상값 처리 (튜플 → 문자열)
                if isinstance(class_copy['color'], tuple):
                    class_copy['color'] = ','.join(map(str, class_copy['color']))
                
                serializable_data.append(class_copy)
            
            # 저장 시간 추가
            metadata = {
                "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0",
                "platform": "android" if 'ANDROID_STORAGE' in os.environ else "pc"
            }
            
            # 최종 저장 데이터
            save_data = {
                "metadata": metadata,
                "classes": serializable_data
            }
            
            # JSON 파일로 저장
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 시간표 데이터 저장 완료: {self.data_file}")
            print(f"📊 저장된 과목 수: {len(serializable_data)}")
            return True
            
        except PermissionError as e:
            print(f"❌ 권한 오류로 저장 실패: {e}")
            return False
        except Exception as e:
            print(f"❌ 시간표 데이터 저장 오류: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_classes(self):
        """저장된 시간표 데이터 불러오기"""
        if not os.path.exists(self.data_file):
            print("📁 저장된 시간표 데이터가 없습니다.")
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 새 형식과 이전 형식 모두 지원
            if isinstance(data, dict) and "classes" in data:
                # 새 형식 (메타데이터 포함)
                classes_list = data["classes"]
                metadata = data.get("metadata", {})
                print(f"📅 데이터 저장 시간: {metadata.get('last_saved', '알 수 없음')}")
                print(f"🖥️ 저장 플랫폼: {metadata.get('platform', '알 수 없음')}")
            else:
                # 이전 형식 (직접 리스트)
                classes_list = data if isinstance(data, list) else [data]
                print("📄 이전 형식의 데이터 감지")
            
            # 딕셔너리로 변환
            classes_data = {}
            for class_data in classes_list:
                try:
                    # 색상 문자열을 튜플로 변환 (필요한 경우)
                    if isinstance(class_data['color'], str) and ',' in class_data['color']:
                        color_parts = class_data['color'].split(',')
                        class_data['color'] = tuple(map(float, color_parts))
                    elif isinstance(class_data['color'], list):
                        class_data['color'] = tuple(class_data['color'])
                    
                    # 알림 시간 기본값 설정
                    if 'notify_before' not in class_data:
                        class_data['notify_before'] = 5
                    
                    class_id = class_data['id']
                    classes_data[class_id] = class_data
                    
                except Exception as item_error:
                    print(f"⚠️ 개별 과목 데이터 처리 오류: {item_error}")
                    continue
            
            print(f"✅ 시간표 데이터 불러오기 완료: {len(classes_data)}개 과목")
            
            # 불러온 데이터 검증
            for class_id, class_data in classes_data.items():
                required_fields = ['id', 'name', 'day', 'start_time', 'end_time', 'room', 'professor', 'color']
                missing_fields = [field for field in required_fields if field not in class_data]
                if missing_fields:
                    print(f"⚠️ 과목 ID {class_id}: 누락된 필드 {missing_fields}")
            
            return classes_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 오류: {e}")
            return {}
        except PermissionError as e:
            print(f"❌ 권한 오류로 불러오기 실패: {e}")
            return {}
        except Exception as e:
            print(f"❌ 시간표 데이터 불러오기 오류: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def backup_data(self):
        """데이터 백업 생성"""
        try:
            if not os.path.exists(self.data_file):
                print("📁 백업할 데이터가 없습니다.")
                return False
            
            # 백업 파일명 생성 (타임스탬프 포함)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.data_dir, f"timetable_backup_{timestamp}.json")
            
            # 파일 복사
            import shutil
            shutil.copy2(self.data_file, backup_file)
            
            print(f"✅ 백업 생성 완료: {backup_file}")
            return True
            
        except Exception as e:
            print(f"❌ 백업 생성 오류: {e}")
            return False
    
    def get_data_info(self):
        """데이터 파일 정보 반환"""
        info = {
            "data_dir": self.data_dir,
            "data_file": self.data_file,
            "file_exists": os.path.exists(self.data_file),
            "file_size": 0,
            "last_modified": None
        }
        
        try:
            if info["file_exists"]:
                stat = os.stat(self.data_file)
                info["file_size"] = stat.st_size
                info["last_modified"] = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(f"❌ 파일 정보 가져오기 오류: {e}")
        
        return info
    
    def clear_data(self):
        """저장된 데이터 삭제"""
        try:
            if os.path.exists(self.data_file):
                os.remove(self.data_file)
                print(f"✅ 데이터 파일 삭제 완료: {self.data_file}")
                return True
            else:
                print("📁 삭제할 데이터 파일이 없습니다.")
                return False
        except Exception as e:
            print(f"❌ 데이터 삭제 오류: {e}")
            return False
