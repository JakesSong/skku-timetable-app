import json
import os
from datetime import datetime

class TimeTableStorage:
    def __init__(self):
        # 데이터 파일 경로 설정 (사용자 홈 디렉토리에 저장)
        self.data_dir = os.path.join(os.path.expanduser("~"), ".timetable_app")
        self.data_file = os.path.join(self.data_dir, "timetable_data.json")
        
        # 데이터 디렉토리가 없으면 생성
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def save_classes(self, classes_data):
        """시간표 데이터를 JSON 파일로 저장"""
        try:
            # 리스트로 변환
            serializable_data = []
            for class_id, class_data in classes_data.items():
                # 색상값 처리 (튜플 → 문자열)
                if isinstance(class_data['color'], tuple):
                    class_data['color'] = ','.join(map(str, class_data['color']))
                
                # 복사본 만들기 (원본 데이터 변경 방지)
                class_copy = class_data.copy()
                serializable_data.append(class_copy)
            
            # 저장 시간 추가
            metadata = {
                "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "version": "1.0"
            }
            
            # 최종 저장 데이터
            save_data = {
                "metadata": metadata,
                "classes": serializable_data
            }
            
            # JSON 파일로 저장
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            print(f"시간표 데이터 저장 완료: {self.data_file}")
            return True
        except Exception as e:
            print(f"시간표 데이터 저장 오류: {e}")
            return False
    
    def load_classes(self):
        """저장된 시간표 데이터 불러오기"""
        if not os.path.exists(self.data_file):
            print("저장된 시간표 데이터가 없습니다.")
            return {}
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 새 형식과 이전 형식 모두 지원
            classes_list = data.get("classes", data) if isinstance(data, dict) else data
            
            # 딕셔너리로 변환
            classes_data = {}
            for class_data in classes_list:
                # 색상 문자열을 튜플로 변환 (필요한 경우)
                if isinstance(class_data['color'], str) and ',' in class_data['color']:
                    class_data['color'] = tuple(map(float, class_data['color'].split(',')))
                
                class_id = class_data['id']
                classes_data[class_id] = class_data
            
            print(f"시간표 데이터 불러오기 완료: {len(classes_data)}개 과목")
            return classes_data
        except Exception as e:
            print(f"시간표 데이터 불러오기 오류: {e}")
            return {}