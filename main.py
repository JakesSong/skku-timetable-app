# -*- coding: utf-8 -*-
# University Timetable App (Using KivyMD) - Simplified Version
# Required libraries:
# pip install kivy kivymd

# 기존 폰트 설정 코드를 모두 삭제하고 다음으로 교체

# 한글 지원을 위한 설정
import os
os.environ['KIVY_TEXT'] = 'sdl2'
os.environ['LANG'] = 'ko_KR.UTF-8'

from kivy.core.text import LabelBase

# APK용 폰트 설정
def setup_korean_font():
    FONT_NAME = "KoreanFont"
    
    # 현재 디렉토리에서 폰트 파일 찾기
    current_dir = os.path.dirname(os.path.abspath(__file__))
    font_candidates = [
        os.path.join(current_dir, 'NanumSquareR.ttf'),
        os.path.join(current_dir, 'fonts', 'NanumSquareR.ttf'),
    ]
    
    # Android 환경인 경우 추가 경로
    if 'ANDROID_STORAGE' in os.environ:
        font_candidates.extend([
            "/system/fonts/NotoSansCJK-Regular.ttc",
            "/system/fonts/DroidSansFallback.ttf"
        ])
    
    # 폰트 등록 시도
    for font_path in font_candidates:
        if os.path.exists(font_path):
            try:
                LabelBase.register(FONT_NAME, font_path)
                print(f"✅ 폰트 등록 성공: {font_path}")
                return FONT_NAME
            except Exception as e:
                print(f"폰트 등록 실패: {font_path} - {e}")
                continue
    
    # 폰트를 찾을 수 없는 경우 안전한 처리
    print("한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
    try:
        # 기본 폰트로 등록 (None 대신 빈 문자열 사용)
        LabelBase.register(FONT_NAME, fn_regular="")
        return FONT_NAME
    except:
        # 최후의 수단
        return "Roboto"

# 폰트 설정 실행
FONT_NAME = setup_korean_font()

from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDFloatingActionButton, MDFlatButton, MDRaisedButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.card import MDCard
from kivymd.uix.behaviors import TouchBehavior
from kivymd.uix.dialog import MDDialog
from kivymd.uix.textfield import MDTextField
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.menu import MDDropdownMenu
from db_handler import TimeTableStorage
from kivy.logger import Logger
from kivy.utils import platform 

from kivy.metrics import dp
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line, Rectangle
from datetime import datetime, timedelta
from functools import partial
import random

class ClassCard(MDCard, TouchBehavior):
    """Custom card class for classes with touch behavior"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.class_data = {}
        self.ripple_behavior = True  # Enable ripple effect
        self.elevation = 2
        self.radius = [dp(5)]
        
    def on_release(self):
        # This will be called when the card is released after being pressed
        if hasattr(self, 'on_release_callback') and self.on_release_callback:
            self.on_release_callback(self)

# 시간 문자열을 숫자(float)로 바꾸는 함수
def parse_time_string(time_str):
    try:
        hour, minute = map(int, time_str.split(':'))
        return hour + (minute / 60)
    except Exception as e:
        print(f"[시간 파싱 오류] {time_str} → {e}")
        return None
    
# 📌 비율 기반 레이아웃 설정
class LayoutConfig:
    num_days = 5
    time_col_ratio = 0.15
    spacing_ratio = 0.01

    @classmethod
    def calculate(cls, total_width, total_height=None):
        # 기존 코드와의 호환성을 위해 total_height에 기본값 설정
        if total_height is None:
            from kivy.core.window import Window
            total_height = Window.height
        
        # 화면 비율에 따른 레이아웃 계산
        grid_width = total_width * 0.95
        header_height = total_height * 0.15
        grid_height = total_height * 0.75
        
        spacing = grid_width * cls.spacing_ratio
        time_col_width = grid_width * cls.time_col_ratio
        remaining_width = grid_width - time_col_width - spacing * (cls.num_days - 1)
        day_col_width = remaining_width / cls.num_days

        return {
            'spacing': spacing,
            'time_col_width': time_col_width,
            'day_col_width': day_col_width,
            'grid_height': grid_height,
            'header_height': header_height,
            'total_height': total_height,
            'grid_width': grid_width,
            'total_width': total_width,
            'start_hour': 9,  # 시작 시간 (9:00)
            'end_hour': 20    # 종료 시간 (19:00)
        }
    
    # 📌 시간표 그리드 위젯
class TimeGridWidget(Widget):
    def __init__(self, layout_data, **kwargs):
        super().__init__(**kwargs)
        self.size_hint_y = None
        self.height = dp(600)
        self.size_hint_x = None

        self.time_col_width = 0  # 중요: 시간 열 너비를 0으로 설정 (이미 time_column에 있음)
        self.day_col_width = layout_data['day_col_width']
        self.spacing = layout_data['spacing']
        self.num_days = LayoutConfig.num_days
        self.width = layout_data['grid_width'] - layout_data['time_col_width']  # 시간 열 제외한 너비
        self.start_hour = layout_data['start_hour']  # 시작 시간
        self.end_hour = layout_data['end_hour']      # 종료 시간

        # 요일 컬럼 시작 위치를 저장
        self.day_columns = []
        x_start = self.x
        for i in range(self.num_days):
            col_x = x_start + i * (self.day_col_width + self.spacing)
            self.day_columns.append(col_x)

        self.bind(pos=self.update_canvas, size=self.update_canvas)
        
    def get_day_column_x(self, day_index):
        """요일 인덱스에 따른 x 좌표 반환 (요일 열의 중앙에 맞춤)"""
        if 0 <= day_index < len(self.day_columns):
            # 요일 열의 중앙으로 맞추기 위해 x 좌표 계산
            # (day_columns에는 열의 왼쪽 경계가 저장되어 있음)
            return self.day_columns[day_index]
        return self.x  # 기본값

    def update_canvas(self, *args):
        """그리드 캔버스 업데이트 - 그리드 라인 그리기"""
        self.canvas.clear()
        with self.canvas:
            # 배경 설정
            Color(0.95, 0.95, 0.95, 1)
            Rectangle(pos=self.pos, size=self.size)

            # 수평선 그리기 (시간대 구분선)
            hours_count = self.end_hour - self.start_hour
            hour_height = self.height / hours_count
            
            # 주요 시간 구분선 (실선)
            Color(0.8, 0.8, 0.8, 1)
            # 위에서 아래로 시간이 증가하도록 그리기
            for i in range(hours_count + 1):  # + 1 to draw the bottom line
                y = self.y + self.height - i * hour_height  # 위에서부터 그리기 시작
                Line(points=[self.x, y, self.x + self.width, y], width=1)

            # 15분 간격 라인 (약한 점선)
            Color(0.9, 0.9, 0.9, 1)
            for i in range(hours_count):
                for j in range(1, 4):  # 15분, 30분, 45분
                    y = self.y + self.height - (i * hour_height + j * (hour_height / 4))
                    Line(points=[self.x, y, self.x + self.width, y], width=0.5)

            # 요일 구분 수직선 그리기
            Color(0.8, 0.8, 0.8, 1)
            # 첫 번째 세로선 (시간 열과 월요일 구분)
            Line(points=[self.x, self.y, self.x, self.y + self.height], width=1)
            
            # 나머지 요일 구분선
            for i in range(1, self.num_days):
                x = self.x + i * (self.day_col_width + self.spacing)
                Line(points=[x, self.y, x, self.y + self.height], width=1)
            
            # 마지막 세로선 (금요일 끝)
            x_end = self.x + self.num_days * (self.day_col_width + self.spacing) - self.spacing
            Line(points=[x_end, self.y, x_end, self.y + self.height], width=1)
            
            # 요일 컬럼 위치 업데이트 (각 요일 열의 왼쪽 경계 저장)
            self.day_columns = []
            for i in range(self.num_days):
                col_x = self.x + i * (self.day_col_width + self.spacing)
                self.day_columns.append(col_x)

def create_headers(layout_data):
    headers = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(60),
        spacing=layout_data['spacing'],
        size_hint_x=None,
        width=layout_data['grid_width']  # 그리드 너비와 동일하게 설정
    )

    # 시간 열 헤더
    headers.add_widget(MDLabel(
        text="  시간",
        halign="center",
        valign="center",
        size_hint_x=None,
        width=layout_data['time_col_width'],
        font_name=FONT_NAME  # FONT_NAME 변수 사용
    ))

    # 요일 헤더
    days = ["월요일", "화요일", "수요일", "목요일", "금요일"]
    for day in days:
        headers.add_widget(MDLabel(
            text=day,
            halign="center",
            valign="center",
            size_hint_x=None,
            width=layout_data['day_col_width'],
            font_name=FONT_NAME  # FONT_NAME 변수 사용
        ))

    return headers

class AddClassDialog:
    """과목 추가 대화상자 클래스"""
    def __init__(self, screen):
        self.screen = screen
        self.dialog = None
        self.day_dropdown = None
        self.current_day = "Monday"  # 기본값
        
        # 현재 등록된 가장 높은 클래스 ID 찾기
        self.next_class_id = 1

        # 시간 드롭다운 변수 초기화
        self.start_time_dropdown = None
        self.end_time_dropdown = None

    def show_start_time_dropdown(self, instance, value):
        """시작 시간 드롭다운 메뉴 표시"""
        if value:  # 텍스트 필드가 포커스를 얻으면
            # 시간 옵션 생성 (09:00부터 18:45까지 15분 간격)
            time_options = []
            for hour in range(9, 19):  # 9시부터 18시까지
                for minute in [0, 15, 30, 45]:  # 15분 간격
                    time_str = f"{hour:02d}:{minute:02d}"
                    time_options.append({
                        "text": time_str,
                        "viewclass": "OneLineListItem",
                        "on_release": lambda x=time_str: self.set_start_time(x),
                    })
            
            # 드롭다운 메뉴 생성 (높이 제한 및 스크롤 가능)
            self.start_time_dropdown = MDDropdownMenu(
                caller=instance,  # 텍스트 필드를 기준으로 표시
                items=time_options,
                width_mult=3,  # width_mult
                max_height=dp(250),  # 높이 제한
                position="auto"  # 자동 위치
            )
            self.start_time_dropdown.open()

    def show_end_time_dropdown(self, instance, value):
        """종료 시간 드롭다운 메뉴 표시"""
        if value:  # 텍스트 필드가 포커스를 얻으면
            # 시간 옵션 생성 (09:15부터 19:00까지 15분 간격)
            time_options = []
            
            # 시작 시간이 선택되지 않았으면 모든 시간 표시
            if not self.start_time_field.text:
                start_hour = 9
                start_minute = 0
            else:
                # 시작 시간이 선택되었으면 그 이후 시간만 표시
                start_time = self.start_time_field.text
                start_hour, start_minute = map(int, start_time.split(':'))
            
            # 시작 시간 이후의 옵션만 생성
            for hour in range(9, 20):  # 9시부터 19시까지
                for minute in [0, 15, 30, 45]:  # 15분 간격
                    # 시작 시간보다 늦은 시간만 포함
                    if (hour > start_hour) or (hour == start_hour and minute > start_minute):
                        time_str = f"{hour:02d}:{minute:02d}"
                        time_options.append({
                            "text": time_str,
                            "viewclass": "OneLineListItem",
                            "on_release": lambda x=time_str: self.set_end_time(x),
                        })
            
            # 드롭다운 메뉴 생성 (높이 제한 및 스크롤 가능)
            self.end_time_dropdown = MDDropdownMenu(
                caller=instance,  # 텍스트 필드를 기준으로 표시
                items=time_options,
                width_mult=3,  # width_mult 대신 직접 너비 설정
                max_height=dp(250),  # 높이 제한
                position="auto"  # 자동 위치
            )
            self.end_time_dropdown.open()
            
    def set_start_time(self, time_str):
        """시작 시간 설정"""
        self.start_time_field.text = time_str
        self.start_time_field.focus = False  # 포커스 해제
        
        if hasattr(self, 'start_time_dropdown'):
            self.start_time_dropdown.dismiss()  # 드롭다운 닫기
        
        # 종료 시간이 설정되어 있고 시작 시간보다 빠르다면 초기화
        if self.end_time_field.text and self.end_time_field.text <= time_str:
            self.end_time_field.text = ""

    def set_end_time(self, time_str):
        """종료 시간 설정"""
        self.end_time_field.text = time_str
        self.end_time_field.focus = False  # 포커스 해제
        
        if hasattr(self, 'end_time_dropdown'):
            self.end_time_dropdown.dismiss()  # 드롭다운 닫기

    # ← 여기에 새 메서드들 추가!
    def on_start_time_touch(self, instance, touch):
        """시작 시간 필드 터치 이벤트"""
        if instance.collide_point(*touch.pos):
            self.show_start_time_dropdown(instance, True)
            return True
        return False

    def on_end_time_touch(self, instance, touch):
        """종료 시간 필드 터치 이벤트"""
        if instance.collide_point(*touch.pos):
            self.show_end_time_dropdown(instance, True)
            return True
        return False    
    
    # 여기에 새 메서드를 추가합니다
    def apply_fonts_to_dialog(self, instance):
        """다이얼로그 내 모든 위젯에 폰트 설정"""
        try:
            # 다이얼로그 타이틀에 폰트 설정
            if hasattr(self.dialog, '_title'):
                self.dialog._title.font_name = FONT_NAME
            
            # content_cls 내부의 모든 위젯에 폰트 설정
            if hasattr(self.dialog, 'content_cls'):
                # 모든 텍스트 필드에 폰트 적용
                for child in self.dialog.content_cls.children:
                    if isinstance(child, MDTextField):
                        self.set_font_for_textfield(child)
                    elif isinstance(child, MDLabel):
                        child.font_name = FONT_NAME
                        # 레이블 폰트 크기 증가
                        child.font_size = "16sp"
                    elif isinstance(child, MDBoxLayout):
                        # 중첩된 레이아웃 내부의 버튼에도 폰트 적용
                        for grandchild in child.children:
                            if hasattr(grandchild, 'font_name'):
                                grandchild.font_name = FONT_NAME

            # 버튼에 폰트 설정
            if hasattr(self.dialog, 'buttons'):
                for button in self.dialog.buttons:
                    button.font_name = FONT_NAME
        except Exception as e:
            print(f"다이얼로그 폰트 설정 오류: {e}")

    def set_font_for_textfield(self, textfield):
        """MDTextField의 폰트 속성을 직접 설정하기 위한 함수"""
        # TextField의 모든 하위 위젯에 폰트 설정 시도
        try:
            textfield.font_name = FONT_NAME
            # 힌트 텍스트와 헬퍼 텍스트도 함께 설정
            if hasattr(textfield, '_hint_lbl'):
                textfield._hint_lbl.font_name = FONT_NAME
            if hasattr(textfield, '_helper_text'):
                textfield._helper_text.font_name = FONT_NAME
            # 메인 텍스트 레이블 설정
            if hasattr(textfield, '_line_lbl'):
                textfield._line_lbl.font_name = FONT_NAME
        except Exception as e:
            print(f"텍스트 필드 폰트 설정 오류: {e}")

    def set_color(self, color, index):
        """선택된 색상 설정"""
        self.selected_color = color
        # 버튼 높이를 업데이트하여 선택 표시
        for i, btn in enumerate(self.color_buttons):
            btn.elevation = 3 if i == index else 0
        self.selected_button_index = index
        
    def show_dialog(self, *args):
        """과목 추가 대화상자 표시"""
        if not self.dialog:
            self.create_dialog(edit_mode=False)
        self.dialog.open()


        
    def create_dialog(self, edit_mode=False, class_id=None):
        """대화상자 생성"""
        # 대화상자 내용 레이아웃
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(5),
            size_hint_y=None,
            height=dp(590),
            padding=(dp(20), dp(10), dp(20), dp(15))
        )
    
        # 🔥 제목과의 간격을 줄이는 음수 스페이서 추가
        negative_spacer = Widget(size_hint_y=None, height=dp(-50))
        self.content.add_widget(negative_spacer)
        
        # MDTextField의 폰트 속성을 직접 설정하기 위한 함수
        def set_font_for_textfield(textfield):
            # TextField의 모든 하위 위젯에 폰트 설정 시도
            try:
                textfield.font_name = FONT_NAME
                # 힌트 텍스트와 헬퍼 텍스트도 함께 설정
                if hasattr(textfield, '_hint_lbl'):
                    textfield._hint_lbl.font_name = FONT_NAME
                if hasattr(textfield, '_helper_text'):
                    textfield._helper_text.font_name = FONT_NAME
                # 메인 텍스트 레이블 설정
                if hasattr(textfield, '_line_lbl'):
                    textfield._line_lbl.font_name = FONT_NAME
            except Exception as e:
                print(f"텍스트 필드 폰트 설정 오류: {e}")
        
        # 과목명 입력
        self.name_field = MDTextField(
            hint_text="Class Name",
            helper_text="Ex: Physics1",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME  # FONT_NAME 변수 사용
        )
        set_font_for_textfield(self.name_field)
        self.content.add_widget(self.name_field)
        
        
        # 요일 선택 필드
        self.day_field = MDTextField(
            hint_text="Day of the week",
            helper_text_mode="on_focus",
            font_name=FONT_NAME,
            height=dp(20),
            readonly=True
        )

        self.day_field.font_size = "15.5sp" 
        set_font_for_textfield(self.day_field)
        self.content.add_widget(self.day_field)
        
        # 요일 버튼 레이아웃 추가
        days_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(30),
            spacing=dp(0),
            padding=(0, 0, 0, 0),
            adaptive_width=False
        )
        
        # 한글 요일 이름과 영어 요일 매핑 사용
        day_names = {
            "Monday": "월",
            "Tuesday": "화",
            "Wednesday": "수",
            "Thursday": "목", 
            "Friday": "금"
        }
        
        for day, day_kr in day_names.items():
            day_btn = MDFlatButton(
                text=day_kr,  # 한글 요일 표시
                font_name=FONT_NAME,
                on_release=lambda x, d=day, k=day_names[day]: self.set_day(d, k),
                size_hint_x=None,
                width=dp(20)
            )
            days_layout.add_widget(day_btn)
        
        self.content.add_widget(days_layout)

        # 시작 시간 - 텍스트 필드를 드롭다운 선택으로 변경
        self.start_time_field = MDTextField(
            hint_text="Start Time",
            helper_text="Click to select time",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            readonly=True  # 직접 입력 불가능하게 설정
        )
        self.start_time_field.bind(on_touch_down=self.on_start_time_touch)
        set_font_for_textfield(self.start_time_field)
        self.content.add_widget(self.start_time_field)
        
        # 종료 시간 - 텍스트 필드를 드롭다운 선택으로 변경
        self.end_time_field = MDTextField(
            hint_text="End Time",
            helper_text="Click to select time",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            readonly=True  # 직접 입력 불가능하게 설정
        )
        self.end_time_field.bind(on_touch_down=self.on_end_time_touch)
        set_font_for_textfield(self.end_time_field)
        self.content.add_widget(self.end_time_field)
        
        # 강의실
        self.room_field = MDTextField(
            hint_text="Class Room",
            helper_text="Ex: 61304A",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME
        )
        set_font_for_textfield(self.room_field)
        self.content.add_widget(self.room_field)
        
        # 교수명
        self.professor_field = MDTextField(
            hint_text="Professor",
            helper_text="Ex: Kim Bumjun",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME
        )
        set_font_for_textfield(self.professor_field)
        self.content.add_widget(self.professor_field)

        
        # 시작 시간 필드와 days_layout 사이에 작은 간격 위젯 추가
        spacer = Widget(size_hint_y=None, height=dp(10))  # 아주 작은 간격
        self.content.add_widget(spacer)

        # 색상 선택 라벨
        self.color_label = MDLabel(
            text="Color Selection", 
            theme_text_color="Secondary",
            font_style="Body2",
            font_name=FONT_NAME,  # FONT_NAME 변수 사용
            size_hint_y=None,
            height=dp(16)
        )
        self.color_label.font_size = "15.5sp" 
        self.content.add_widget(self.color_label)

        # 색상 선택 버튼들
        colors_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),  # 작은 높이
            spacing=dp(2)   # 좁은 간격
        )

        # 과목 색상 정의
        self.class_colors = [
            (0.6, 0.2, 0.8, 1),  # Purple
            (0.2, 0.6, 0.8, 1),  # Blue
            (0.2, 0.8, 0.2, 1),  # Green
            (0.8, 0.6, 0.2, 1),  # Orange
            (0.8, 0.2, 0.2, 1),  # Red
            (1.0, 0.4, 0.8, 1),  # Pink
            (0.5, 0.5, 0.5, 1),  # Gray
        ]
        self.selected_color = self.class_colors[0]  # 기본 색상
        self.color_buttons = []

        for i, color in enumerate(self.class_colors):
            # MDRectangleFlatButton 대신 MDCard 사용
            from kivymd.uix.card import MDCard
            color_btn = MDCard(
                size_hint=(None, None),
                size=(dp(40), dp(30)),  # 작은 크기
                md_bg_color=color,
                radius=[dp(2)],  # 약간의 모서리 둥글기
                elevation=1 if i == 0 else 0  # 첫 번째 버튼은 선택된 상태로 표시
            )
            # 터치 이벤트 추가
            color_btn.bind(on_touch_down=lambda instance, touch, c=color, i=i: 
                        self.set_color(c, i) if instance.collide_point(*touch.pos) else None)
            
            self.color_buttons.append(color_btn)
            colors_layout.add_widget(color_btn)
        
        # 첫 번째 버튼을 선택된 상태로 설정
        self.selected_button_index = 0
        self.color_buttons[0].elevation = 3
        self.content.add_widget(colors_layout)


        # 시작 시간 필드와 days_layout 사이에 작은 간격 위젯 추가
        spacer = Widget(size_hint_y=None, height=dp(10))  # 아주 작은 간격
        self.content.add_widget(spacer)

        self.notify_label = MDLabel(
            text="Set Alarm (Before)",
            theme_text_color="Secondary",
            font_style="Body2",
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(20)
        )

        self.notify_label.font_size = "15.5sp" 
        self.content.add_widget(self.notify_label)

        # 입력창과 "Minute" 텍스트를 함께 표시할 수평 레이아웃
        notify_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(5),
            padding=[0, 0, 0, 0]
        )

        # 숫자 입력 필드 (더 좁게 설정)
        self.notify_input = MDTextField(
            hint_text="",  # 힌트 텍스트 제거
            input_filter="int",
            text="5",
            font_name=FONT_NAME,
            size_hint_x=0.2,  # 너비 30%로 제한
        )

        set_font_for_textfield(self.notify_input)

        # "Minute" 레이블
        minute_label = MDLabel(
            text="Minute",
            theme_text_color="Secondary",
            font_name=FONT_NAME,
            size_hint_x=0.8,  # 나머지 70% 차지
            halign="left",
            valign="center"
        )


        # 레이아웃에 위젯 추가
        notify_layout.add_widget(self.notify_input)
        notify_layout.add_widget(minute_label)

        # 메인 컨텐트에 레이아웃 추가
        self.content.add_widget(notify_layout)

        # 다이얼로그 생성 후 글꼴 설정을 위한 함수
        def post_dialog_open(dialog):
            try:
                # 다이얼로그 타이틀 폰트 설정
                if hasattr(dialog, '_title'):
                    dialog._title.font_name = FONT_NAME
                
                # content_cls 내부의 모든 텍스트 필드에 폰트 설정
                if hasattr(dialog, 'content_cls'):
                    for child in dialog.content_cls.children:
                        if isinstance(child, MDTextField):
                            set_font_for_textfield(child)
            except Exception as e:
                print(f"다이얼로그 폰트 설정 오류: {e}")
                
        # 버튼을 모드에 따라 다르게 설정
        if edit_mode:
            # 수정 모드: 취소, 삭제, 저장
            buttons = [
                MDFlatButton(
                    text="취소",
                    font_name=FONT_NAME,
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDFlatButton(
                    text="삭제", 
                    font_name=FONT_NAME,
                    theme_text_color="Custom",
                    text_color=[1, 0.3, 0.3, 1],
                    on_release=lambda x: self.screen.confirm_delete_class(class_id)
                ),
                MDRaisedButton(
                    text="저장",
                    font_name=FONT_NAME,
                    on_release=lambda x: self.screen.save_edited_class(class_id)
                )
            ]
        else:
            # 추가 모드: 취소, 추가
            buttons = [
                MDFlatButton(
                    text="취소",
                    font_name=FONT_NAME,
                    on_release=lambda x: self.dialog.dismiss()
                ),
                MDRaisedButton(
                    text="추가",
                    font_name=FONT_NAME,
                    on_release=self.add_class
                )
            ]
        
        # 팝업 대화상자 생성
        self.dialog = MDDialog(
            title="새 과목 추가" if not edit_mode else "과목 수정",
            type="custom",
            content_cls=self.content,
            size_hint=(0.90, None),
            buttons=buttons
        )
        
        # 다이얼로그가 열릴 때 한 번 더 글꼴 설정 시도
        self.dialog.bind(on_open=lambda *args: post_dialog_open(self.dialog))

    
    def set_day(self, english_day, korean_day):
        """요일 설정"""
        self.current_day = english_day
        self.day_field.text = korean_day
        # 포커스 해제
        self.day_field.focus = False
            
    def dismiss_dialog(self, *args):
        """대화상자 닫기"""
        if self.dialog:
            self.dialog.dismiss()
            
    def add_class(self, *args):
        """새 과목 추가"""
        # 입력값 가져오기
        name = self.name_field.text.strip()
        day = self.current_day
        start_time = self.start_time_field.text.strip()
        end_time = self.end_time_field.text.strip()
        room = self.room_field.text.strip()
        professor = self.professor_field.text.strip()
        
        # 입력 검증
        if not all([name, day, start_time, end_time, room, professor]):
            # 경고 대화상자 표시 (한글 처리 개선)
            warning_dialog = MDDialog(
                title="입력 오류",
                text="모든 필드를 입력해주세요.",
                buttons=[
                    MDFlatButton(
                        text="확인",
                        theme_text_color="Custom",
                        text_color=self.screen.app.theme_cls.primary_color,
                        font_name=FONT_NAME,
                        on_release=lambda x: warning_dialog.dismiss()
                    )
                ]
            )
            # 경고 다이얼로그의 텍스트에 폰트 설정
            warning_dialog.text_font_name = FONT_NAME
            warning_dialog.open()
            return
            
        # 색상 정보 준비
        color_str = f"{self.selected_color[0]},{self.selected_color[1]},{self.selected_color[2]},{self.selected_color[3]}"
        
        # 시간표에 과목 추가
        self.screen.add_class_to_grid(
            self.next_class_id, name, day, start_time, end_time, room, professor, color_str
        )
            # 디버깅 로그 추가
        print(f"과목 추가 후 ID: {self.next_class_id}")
        self.next_class_id += 1
        
        # 대화상자 닫기
        self.dismiss_dialog()


class EditClassDialog:
    """과목 수정 대화상자 클래스 - 완전히 독립적인 구현"""
    def __init__(self, screen):
        self.screen = screen
        self.dialog = None
        self.editing_card = None
        self.day_dropdown = None
        self.current_day = "Monday"  # 기본값
        
        # 시간 드롭다운 변수 초기화
        self.start_time_dropdown = None
        self.end_time_dropdown = None
        self.selected_color = None
        self.color_buttons = []
        
        # 색상 정의 (AddClassDialog와 동일하게 유지)
        self.class_colors = [
            (0.6, 0.2, 0.8, 1),  # Purple
            (0.2, 0.6, 0.8, 1),  # Blue
            (0.2, 0.8, 0.2, 1),  # Green
            (0.8, 0.6, 0.2, 1),  # Orange
            (0.8, 0.2, 0.2, 1),  # Red
            (1.0, 0.4, 0.8, 1),  # Pink
            (0.5, 0.5, 0.5, 1),  # Gray
        ]
        self.selected_button_index = 0
    
    def show_start_time_dropdown(self, instance, value):
        """시작 시간 드롭다운 메뉴 표시"""
        if value:  # 텍스트 필드가 포커스를 얻으면
            # 시간 옵션 생성 (09:00부터 18:45까지 15분 간격)
            time_options = []
            for hour in range(9, 19):  # 9시부터 18시까지
                for minute in [0, 15, 30, 45]:  # 15분 간격
                    time_str = f"{hour:02d}:{minute:02d}"
                    time_options.append({
                        "text": time_str,
                        "viewclass": "OneLineListItem",
                        "on_release": lambda x=time_str: self.set_start_time(x),
                    })
            
            # 드롭다운 메뉴 생성 (높이 제한 및 스크롤 가능)
            self.start_time_dropdown = MDDropdownMenu(
                caller=instance,  # 텍스트 필드를 기준으로 표시
                items=time_options,
                width_mult=3,  # width_mult
                max_height=dp(250),  # 높이 제한
                position="auto"  # 자동 위치
            )
            self.start_time_dropdown.open()

    def show_end_time_dropdown(self, instance, value):
        """종료 시간 드롭다운 메뉴 표시"""
        if value:  # 텍스트 필드가 포커스를 얻으면
            # 시간 옵션 생성 (09:15부터 19:00까지 15분 간격)
            time_options = []
            
            # 시작 시간이 선택되지 않았으면 모든 시간 표시
            if not self.start_time_field.text:
                start_hour = 9
                start_minute = 0
            else:
                # 시작 시간이 선택되었으면 그 이후 시간만 표시
                start_time = self.start_time_field.text
                start_hour, start_minute = map(int, start_time.split(':'))
            
            # 시작 시간 이후의 옵션만 생성
            for hour in range(9, 20):  # 9시부터 19시까지
                for minute in [0, 15, 30, 45]:  # 15분 간격
                    # 시작 시간보다 늦은 시간만 포함
                    if (hour > start_hour) or (hour == start_hour and minute > start_minute):
                        time_str = f"{hour:02d}:{minute:02d}"
                        time_options.append({
                            "text": time_str,
                            "viewclass": "OneLineListItem",
                            "on_release": lambda x=time_str: self.set_end_time(x),
                        })
            
            # 드롭다운 메뉴 생성 (높이 제한 및 스크롤 가능)
            self.end_time_dropdown = MDDropdownMenu(
                caller=instance,  # 텍스트 필드를 기준으로 표시
                items=time_options,
                width_mult=3,  # width_mult 대신 직접 너비 설정
                max_height=dp(250),  # 높이 제한
                position="auto"  # 자동 위치
            )
            self.end_time_dropdown.open()
            
    def set_start_time(self, time_str):
        """시작 시간 설정"""
        self.start_time_field.text = time_str
        self.start_time_field.focus = False  # 포커스 해제
        
        if hasattr(self, 'start_time_dropdown'):
            self.start_time_dropdown.dismiss()  # 드롭다운 닫기
        
        # 종료 시간이 설정되어 있고 시작 시간보다 빠르다면 초기화
        if self.end_time_field.text and self.end_time_field.text <= time_str:
            self.end_time_field.text = ""

    def set_end_time(self, time_str):
        """종료 시간 설정"""
        self.end_time_field.text = time_str
        self.end_time_field.focus = False  # 포커스 해제
        
        if hasattr(self, 'end_time_dropdown'):
            self.end_time_dropdown.dismiss()  # 드롭다운 닫기
    
    def on_start_time_touch(self, instance, touch):
        """시작 시간 필드 터치 이벤트"""
        if instance.collide_point(*touch.pos):
            self.show_start_time_dropdown(instance, True)
            return True
        return False

    def on_end_time_touch(self, instance, touch):
        """종료 시간 필드 터치 이벤트"""
        if instance.collide_point(*touch.pos):
            self.show_end_time_dropdown(instance, True)
            return True
        return False
    
    def set_day(self, english_day, korean_day):
        """요일 설정"""
        self.current_day = english_day
        self.day_field.text = korean_day
        # 포커스 해제
        self.day_field.focus = False
    
    def set_color(self, color, index):
        """선택된 색상 설정"""
        self.selected_color = color
        # 버튼 높이를 업데이트하여 선택 표시
        for i, btn in enumerate(self.color_buttons):
            btn.elevation = 3 if i == index else 0
        self.selected_button_index = index
        
    def apply_fonts_to_dialog(self, instance):
        """다이얼로그 내 모든 위젯에 폰트 설정"""
        try:
            # 다이얼로그 타이틀에 폰트 설정
            if hasattr(self.dialog, '_title'):
                self.dialog._title.font_name = FONT_NAME
            
            # content_cls 내부의 모든 위젯에 폰트 설정
            if hasattr(self.dialog, 'content_cls'):
                # 모든 텍스트 필드에 폰트 적용
                for child in self.dialog.content_cls.children:
                    if isinstance(child, MDTextField):
                        self.set_font_for_textfield(child)
                    elif isinstance(child, MDLabel):
                        child.font_name = FONT_NAME
                        # 레이블 폰트 크기 증가
                        child.font_size = "16sp"
                    elif isinstance(child, MDBoxLayout):
                        # 중첩된 레이아웃 내부의 버튼에도 폰트 적용
                        for grandchild in child.children:
                            if hasattr(grandchild, 'font_name'):
                                grandchild.font_name = FONT_NAME

            # 버튼에 폰트 설정
            if hasattr(self.dialog, 'buttons'):
                for button in self.dialog.buttons:
                    button.font_name = FONT_NAME
        except Exception as e:
            print(f"다이얼로그 폰트 설정 오류: {e}")

    def set_font_for_textfield(self, textfield):
        """MDTextField의 폰트 속성을 직접 설정하기 위한 함수"""
        # TextField의 모든 하위 위젯에 폰트 설정 시도
        try:
            textfield.font_name = FONT_NAME
            # 힌트 텍스트와 헬퍼 텍스트도 함께 설정
            if hasattr(textfield, '_hint_lbl'):
                textfield._hint_lbl.font_name = FONT_NAME
            if hasattr(textfield, '_helper_text'):
                textfield._helper_text.font_name = FONT_NAME
            # 메인 텍스트 레이블 설정
            if hasattr(textfield, '_line_lbl'):
                textfield._line_lbl.font_name = FONT_NAME
        except Exception as e:
            print(f"텍스트 필드 폰트 설정 오류: {e}")
    
    def show_edit_dialog(self, card):
        """과목 수정 대화상자 표시"""
        self.editing_card = card  # 편집할 카드 참조 저장
        class_data = card.class_data
        
        # 대화상자 내용 레이아웃
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(5),
            size_hint_y=None,
            height=dp(590),
            padding=(dp(20), dp(10), dp(20), dp(15))
        )
    
        # 🔥 제목과의 간격을 줄이는 음수 스페이서 추가
        negative_spacer = Widget(size_hint_y=None, height=dp(-50))
        self.content.add_widget(negative_spacer)
        
        # 과목명 입력
        self.name_field = MDTextField(
            hint_text="Class Name",
            helper_text="Ex: Physics1",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            text=class_data['name']
        )
        self.set_font_for_textfield(self.name_field)
        self.content.add_widget(self.name_field)
        
        # 요일 선택 필드
        self.day_field = MDTextField(
            hint_text="Day of the week",
            helper_text_mode="on_focus",
            font_name=FONT_NAME,
            height=dp(20),
            readonly=True,
            text=korean_day_map.get(class_data['day'], "월")
        )
        self.current_day = class_data['day']
        self.day_field.font_size = "15.5sp" 
        self.set_font_for_textfield(self.day_field)
        self.content.add_widget(self.day_field)
        
        # 요일 버튼 레이아웃 추가
        days_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(30),
            spacing=dp(0),
            padding=(0, 0, 0, 0),
            adaptive_width=False
        )
        
        # 한글 요일 이름과 영어 요일 매핑 사용
        day_names = {
            "Monday": "월",
            "Tuesday": "화",
            "Wednesday": "수",
            "Thursday": "목", 
            "Friday": "금"
        }
        
        for day, day_kr in day_names.items():
            day_btn = MDFlatButton(
                text=day_kr,  # 한글 요일 표시
                font_name=FONT_NAME,
                on_release=lambda x, d=day, k=day_names[day]: self.set_day(d, k),
                size_hint_x=None,
                width=dp(20)
            )
            days_layout.add_widget(day_btn)
        
        self.content.add_widget(days_layout)

        # 시작 시간
        self.start_time_field = MDTextField(
            hint_text="Start Time",
            helper_text="Click to select time",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            readonly=True,
            text=class_data['start_time']
        )
        self.start_time_field.bind(on_touch_down=self.on_start_time_touch)
        self.set_font_for_textfield(self.start_time_field)
        self.content.add_widget(self.start_time_field)
        
        # 종료 시간
        self.end_time_field = MDTextField(
            hint_text="End Time",
            helper_text="Click to select time",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            readonly=True,
            text=class_data['end_time']
        )
        self.end_time_field.bind(on_touch_down=self.on_end_time_touch)
        self.set_font_for_textfield(self.end_time_field)
        self.content.add_widget(self.end_time_field)
        
        # 강의실
        self.room_field = MDTextField(
            hint_text="Class Room",
            helper_text="Ex: 61304A",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            text=class_data['room']
        )
        self.set_font_for_textfield(self.room_field)
        self.content.add_widget(self.room_field)
        
        # 교수명
        self.professor_field = MDTextField(
            hint_text="Professor",
            helper_text="Ex: Kim Bumjun",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME,
            text=class_data['professor']
        )
        self.set_font_for_textfield(self.professor_field)
        self.content.add_widget(self.professor_field)

        # 작은 간격 위젯 추가
        spacer = Widget(size_hint_y=None, height=dp(10))
        self.content.add_widget(spacer)

        # 색상 선택 라벨
        self.color_label = MDLabel(
            text="Color Selection", 
            theme_text_color="Secondary",
            font_style="Body2",
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(16)
        )
        self.color_label.font_size = "15.5sp" 
        self.content.add_widget(self.color_label)

        # 색상 선택 버튼들
        colors_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(40),
            spacing=dp(2)
        )

        # 현재 색상 정보
        self.selected_color = class_data['color']
        self.color_buttons = []

        for i, color in enumerate(self.class_colors):
            from kivymd.uix.card import MDCard
            color_btn = MDCard(
                size_hint=(None, None),
                size=(dp(40), dp(30)),
                md_bg_color=color,
                radius=[dp(2)],
                # 현재 색상과 일치하면 강조 표시
                elevation=3 if color == self.selected_color else 0
            )
            # 터치 이벤트 추가
            color_btn.bind(on_touch_down=lambda instance, touch, c=color, i=i: 
                        self.set_color(c, i) if instance.collide_point(*touch.pos) else None)
            
            self.color_buttons.append(color_btn)
            colors_layout.add_widget(color_btn)
        
        # 선택된 버튼 인덱스 설정
        for i, color in enumerate(self.class_colors):
            if color == self.selected_color:
                self.selected_button_index = i
                break
                
        self.content.add_widget(colors_layout)

        # 작은 간격 위젯 추가
        spacer = Widget(size_hint_y=None, height=dp(10))
        self.content.add_widget(spacer)

        # 알림 설정 레이블
        self.notify_label = MDLabel(
            text="Set Alarm (Before)",
            theme_text_color="Secondary",
            font_style="Body2",
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(20)
        )
        self.notify_label.font_size = "15.5sp" 
        self.content.add_widget(self.notify_label)

        # 알림 시간 입력 레이아웃
        notify_layout = MDBoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(45),
            spacing=dp(5),
            padding=[0, 0, 0, 0]
        )

        # 알림 시간 입력 필드
        self.notify_input = MDTextField(
            hint_text="",
            input_filter="int",
            # 기존 알림 시간 표시 (기본값: 5분)
            text=str(class_data.get('notify_before', 5)),
            font_name=FONT_NAME,
            size_hint_x=0.2,
        )
        self.set_font_for_textfield(self.notify_input)

        # "Minute" 레이블
        minute_label = MDLabel(
            text="Minute",
            theme_text_color="Secondary",
            font_name=FONT_NAME,
            size_hint_x=0.8,
            halign="left",
            valign="center"
        )

        # 레이아웃에 위젯 추가
        notify_layout.add_widget(self.notify_input)
        notify_layout.add_widget(minute_label)
        self.content.add_widget(notify_layout)

        # 버튼 생성 (취소, 삭제, 저장)
        buttons = [
            MDFlatButton(
                text="취소",
                font_name=FONT_NAME,
                on_release=lambda x: self.dialog.dismiss()
            ),
            MDFlatButton(
                text="삭제",
                font_name=FONT_NAME,
                theme_text_color="Custom",
                text_color=[1, 0.3, 0.3, 1],
                on_release=lambda x: self.delete_class()
            ),
            MDRaisedButton(
                text="저장",
                font_name=FONT_NAME,
                on_release=lambda x: self.update_class()
            )
        ]
        
        # 팝업 대화상자 생성 - halign 속성 없음!
        self.dialog = MDDialog(
            title="과목 수정",
            type="custom",
            content_cls=self.content,
            size_hint=(0.90, None),
            buttons=buttons
        )
        
        # 다이얼로그 열기
        self.dialog.open()
        
        # 폰트 설정 적용
        self.apply_fonts_to_dialog(self.dialog)

    def update_class(self, *args):
        """과목 정보 업데이트"""
        if not self.editing_card:
            return
            
        # 입력값 가져오기
        name = self.name_field.text.strip()
        day = self.current_day
        start_time = self.start_time_field.text.strip()
        end_time = self.end_time_field.text.strip()
        room = self.room_field.text.strip()
        professor = self.professor_field.text.strip()
        
        # 입력 검증
        if not all([name, day, start_time, end_time, room, professor]):
            warning_dialog = MDDialog(
                title="입력 오류",
                text="모든 필드를 입력해주세요.",
                buttons=[
                    MDFlatButton(
                        text="확인",
                        theme_text_color="Custom",
                        text_color=self.screen.app.theme_cls.primary_color,
                        font_name=FONT_NAME,
                        on_release=lambda x: warning_dialog.dismiss()
                    )
                ]
            )
            warning_dialog.text_font_name = FONT_NAME
            warning_dialog.open()
            return
            
        # 기존 카드의 클래스 ID 가져오기
        class_id = self.editing_card.class_data['id']
        
        # 색상 정보 준비
        color_str = f"{self.selected_color[0]},{self.selected_color[1]},{self.selected_color[2]},{self.selected_color[3]}"
        
        # 알림 시간 가져오기
        notify_before = int(self.notify_input.text) if self.notify_input.text.strip() else 5
        
        # 기존 카드 제거
        self.screen.time_grid.remove_widget(self.editing_card)
        
        # 스토리지에서 해당 클래스 정보 삭제
        if class_id in self.screen.classes_data:
            # 기존 알람 취소 (Android 환경인 경우)
            if 'ANDROID_STORAGE' in os.environ and hasattr(self.screen, 'alarm_manager'):
                self.screen.alarm_manager.cancel_alarm(class_id)
            
            del self.screen.classes_data[class_id]
        
        # 카드 다시 추가 (업데이트된 정보로)
        self.screen.add_class_to_grid(
            class_id, name, day, start_time, end_time, room, professor, color_str
        )
        
        # 알림 설정 업데이트 (데이터만 저장)
        if class_id in self.screen.classes_data:
            self.screen.classes_data[class_id]['notify_before'] = notify_before
            
            # 알람 관리자에 알람 갱신 (있을 경우)
            if hasattr(self.screen, 'alarm_manager') and self.screen.alarm_manager is not None:
                try:
                    self.screen.alarm_manager.schedule_class_alarm(
                        class_id, name, day, start_time, room, professor, notify_before
                    )
                except Exception as e:
                    print(f"알람 설정 오류: {e}")
        
        # 시간표 저장
        self.screen.save_timetable()
        
        # 대화상자 닫기
        self.dialog.dismiss()
        
    def delete_class(self, *args):
        """과목 삭제"""
        if not self.editing_card:
            return
            
        # 확인 대화상자 표시
        confirm_dialog = MDDialog(
            title="과목 삭제",
            text=f"'{self.editing_card.class_data['name']}' 과목을 삭제하시겠습니까?",
            buttons=[
                MDFlatButton(
                    text="취소",
                    theme_text_color="Custom",
                    text_color=self.screen.app.theme_cls.primary_color,
                    font_name=FONT_NAME,
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDFlatButton(
                    text="삭제",
                    theme_text_color="Custom",
                    text_color=(0.8, 0.2, 0.2, 1),  # 빨간색
                    font_name=FONT_NAME,
                    on_release=lambda x: self.confirm_delete(confirm_dialog)
                ),
            ]
        )
        confirm_dialog.text_font_name = FONT_NAME
        confirm_dialog.open()
        
    def confirm_delete(self, confirm_dialog):
        """삭제 확인 후 처리"""
        # 확인 대화상자 닫기
        confirm_dialog.dismiss()
        
        # 삭제할 카드의 클래스 ID
        class_id = self.editing_card.class_data['id']
        
        # 카드 위젯 제거
        self.screen.time_grid.remove_widget(self.editing_card)
        
        # 스토리지에서 해당 클래스 정보 삭제
        if class_id in self.screen.classes_data:
            # 알람 취소 (Android 환경인 경우)
            if 'ANDROID_STORAGE' in os.environ and hasattr(self.screen, 'alarm_manager') and self.screen.alarm_manager is not None:
                try:
                    self.screen.alarm_manager.cancel_alarm(class_id)
                except Exception as e:
                    print(f"알람 취소 오류: {e}")
            
            del self.screen.classes_data[class_id]
            self.screen.save_timetable()  # 저장
        
        # 수정 대화상자 닫기
        self.dialog.dismiss()

# 영어-한글 요일 매핑
korean_day_map = {
    "Monday": "월요일",
    "Tuesday": "화요일",
    "Wednesday": "수요일",
    "Thursday": "목요일",
    "Friday": "금요일"
}

class MainScreen(MDScreen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.add_class_dialog = AddClassDialog(self)
        self.edit_class_dialog = EditClassDialog(self)
        self.classes_data = {}
        self.storage = TimeTableStorage()
        self.subtitle_text = "2025년 1학기 소재부품융합공학과"
        
        # 🔥 초기화 상태 플래그 추가
        self.is_initialized = False
        self.layout_created = False
        
        # 🔥 즉시 레이아웃 설정 시도 (Window가 준비되었을 때)
        Clock.schedule_once(self.setup_layout, 0)

    def show_subtitle_edit_dialog(self, instance):
        """부제목 편집 대화상자 표시"""
        self.subtitle_field = MDTextField(
            text=self.subtitle_text,
            hint_text="Edit",
            font_name=FONT_NAME,
            size_hint_y=None,
            height=dp(50)
        )
        
        content = MDBoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(60),
            spacing=dp(5)
        )
        content.add_widget(self.subtitle_field)
        
        self.subtitle_dialog = MDDialog(
            title="부제목 편집",
            type="custom",
            content_cls=content,
            buttons=[
                MDFlatButton(
                    text="취소",
                    theme_text_color="Custom",
                    text_color=self.app.theme_cls.primary_color,
                    font_name=FONT_NAME,
                    on_release=lambda x: self.subtitle_dialog.dismiss()
                ),
                MDFlatButton(
                    text="저장",
                    theme_text_color="Custom", 
                    text_color=self.app.theme_cls.primary_color,
                    font_name=FONT_NAME,
                    on_release=self.save_subtitle
                ),
            ],
        )
        self.subtitle_dialog.open()
    
    def save_subtitle(self, *args):
        """부제목 저장"""
        new_text = self.subtitle_field.text.strip()
        if new_text:
            self.subtitle_text = new_text
            self.subtitle_label.text = new_text
            
            # 부제목 저장 (간단하게 파일로)
            try:
                with open('subtitle.txt', 'w', encoding='utf-8') as f:
                    f.write(new_text)
            except:
                pass
        
        self.subtitle_dialog.dismiss()
    
    def load_subtitle(self):
        """저장된 부제목 불러오기"""
        try:
            with open('subtitle.txt', 'r', encoding='utf-8') as f:
                self.subtitle_text = f.read().strip()
        except:
            self.subtitle_text = "2025년 1학기 소재부품융합공학과"  # 기본값

            
    def open_attendance_app(self, instance):
            """전자출결 앱 열기 (로그캣으로 확인한 정확한 액티비티명 사용)"""
            try:
                if platform == 'android':
                    from jnius import autoclass
                    Intent = autoclass('android.content.Intent')
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    
                    package_name = 'edu.skku.attend'
                    activity_name = 'edu.skku.attend.ui.activity.IntroActivity'  # 로그캣에서 확인한 정확한 이름
                    context = PythonActivity.mActivity
                    
                    # 방법 1: PackageManager 사용
                    pm = context.getPackageManager()
                    intent = pm.getLaunchIntentForPackage(package_name)
                    
                    if intent:
                        context.startActivity(intent)
                        print("✅ PackageManager로 전자출결 앱 실행 성공")
                    else:
                        # 방법 2: 직접 액티비티명 지정
                        intent = Intent()
                        intent.setClassName(package_name, activity_name)
                        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                        context.startActivity(intent)
                        print(f"✅ 직접 액티비티로 전자출결 앱 실행 성공: {activity_name}")
                        
                else:
                    # PC 환경에서는 웹브라우저로 안내
                    import webbrowser
                    webbrowser.open("https://play.google.com/store/apps/details?id=edu.skku.attend")
                    
            except Exception as e:
                print(f"❌ 전자출결 앱 실행 실패: {e}")
                # 실패 시 플레이스토어로 이동
                self.open_store()
        
    def show_attendance_error_dialog(self):
        """전자출결 앱 실행 오류 대화상자 표시"""
        error_dialog = MDDialog(
            title="전자출결 앱 오류",
            text="전자출결 앱을 실행할 수 없습니다. 앱이 설치되어 있는지 확인하세요.",
            buttons=[
                MDFlatButton(
                    text="확인",
                    theme_text_color="Custom",
                    text_color=self.app.theme_cls.primary_color,
                    font_name=FONT_NAME,
                    on_release=lambda x: error_dialog.dismiss()
                ),
                MDFlatButton(
                    text="앱 설치",
                    theme_text_color="Custom",
                    text_color=self.app.theme_cls.primary_color,
                    font_name=FONT_NAME,
                    on_release=lambda x: self.open_store()
                )
            ]
        )
        error_dialog.text_font_name = FONT_NAME
        error_dialog.open()

    def open_store(self):
        """앱스토어에서 전자출결 앱 페이지 열기"""
        try:
            # 안드로이드 환경인지 확인
            if 'ANDROID_STORAGE' in os.environ:
                # 안드로이드 환경
                from jnius import autoclass
                
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                
                # 성균관대 전자출결 앱 실제 Play 스토어 주소
                store_uri = Uri.parse("market://details?id=edu.skku.attend")
                intent = Intent(Intent.ACTION_VIEW, store_uri)
                
                currentActivity = PythonActivity.mActivity
                currentActivity.startActivity(intent)
            else:
                # 안드로이드가 아닌 환경 (개발 PC)에서는 웹브라우저 URL로 열기
                import webbrowser
                webbrowser.open("https://play.google.com/store/apps/details?id=edu.skku.attend")
        except Exception as e:
            print(f"스토어 열기 오류: {e}")
            # 마지막 시도: 웹브라우저로 직접 열기
            try:
                import webbrowser
                webbrowser.open("https://play.google.com/store/apps/details?id=edu.skku.attend")
            except Exception as web_e:
                print(f"웹브라우저 열기 오류: {web_e}")

    def load_saved_timetable(self):
        """저장된 시간표 불러오기"""
        self.classes_data = self.storage.load_classes()
        
        if not self.classes_data:
            # 저장된 시간표가 없으면 빈 시간표로 시작
            print("저장된 시간표가 없습니다. 새 시간표를 만드세요.")
            self.add_class_dialog.next_class_id = 1  # ID는 1부터 시작
        else:
            # 저장된 시간표 표시
            max_id = 0
            for class_id, class_data in self.classes_data.items():
                # 색상 처리
                color = class_data['color']
                if isinstance(color, str) and ',' in color:
                    color_str = color
                else:
                    color_str = ','.join(map(str, color))
                
                # 과목 카드 생성 및 추가
                try:
                    self.add_class_to_grid(
                        class_data['id'], 
                        class_data['name'], 
                        class_data['day'], 
                        class_data['start_time'], 
                        class_data['end_time'], 
                        class_data['room'], 
                        class_data['professor'], 
                        color_str
                    )
                    # 최대 ID 갱신
                    max_id = max(max_id, int(class_data['id']))
                except Exception as e:
                    print(f"과목 카드 생성 오류 ({class_data['name']}): {e}")
            
            # 다음 ID 설정
            self.add_class_dialog.next_class_id = max_id + 1
                
    def setup_layout(self, dt):
        # 🔥 중복 초기화 방지
        if self.layout_created:
            return
            
        try:
            self.load_subtitle()
            
            # 🔥 Window 크기가 준비되지 않았으면 다시 스케줄링
            if Window.width <= 100 or Window.height <= 100:
                print(f"Window 크기가 아직 준비되지 않음: {Window.width}x{Window.height}")
                Clock.schedule_once(self.setup_layout, 0.1)
                return
                
            self.layout_data = LayoutConfig.calculate(Window.width)
            
            # 🔥 기존 레이아웃이 있으면 제거
            if hasattr(self, 'layout') and self.layout:
                self.remove_widget(self.layout)
                
            self.layout = MDBoxLayout(orientation="vertical")
            self.add_widget(self.layout)

            self.layout.add_widget(MDLabel(
                text="성균관대학교 시간표",
                halign="center",
                theme_text_color="Primary",
                font_style="H5",
                font_name=FONT_NAME,  # FONT_NAME 변수 사용
                size_hint_y=None,
                height=dp(50)
            ))
        
            # 편집 가능한 부제목
            self.subtitle_label = MDLabel(
                text=self.subtitle_text,  # 저장된 텍스트 사용
                halign="center",
                theme_text_color="Secondary",
                font_style="Subtitle1",
                font_name=FONT_NAME,
                size_hint_y=None,
                height=dp(30)
            )
        
            # 부제목 클릭 시 편집 가능하도록
            self.subtitle_label.bind(on_touch_down=self.on_subtitle_touch)
            self.layout.add_widget(self.subtitle_label)
            
            # 스크롤뷰 설정 - 전체 화면 너비 사용
            self.scroll_view = ScrollView(
                do_scroll_x=True,
                do_scroll_y=True,
                size_hint=(1, 1),
                height=dp(600),
                bar_width=dp(10),
                scroll_type=['bars', 'content'],
                bar_color=self.app.theme_cls.primary_color,
                bar_inactive_color=(0.7, 0.7, 0.7, 0.5)
            )
            self.layout.add_widget(self.scroll_view)

            # 그리드 컨테이너 설정 - 그리드 너비로 설정 (전체 화면의 90%)
            self.grid_container = MDBoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(660),
                size_hint_x=None,
                width=self.layout_data['grid_width']  # 그리드 너비 (전체의 90%)
            )
            self.scroll_view.add_widget(self.grid_container)

            # 헤더 추가
            self.headers = create_headers(self.layout_data)
            self.grid_container.add_widget(self.headers)

            # 시간표 레이아웃 설정
            self.time_grid_layout = MDBoxLayout(
                orientation="horizontal",
                size_hint_y=None,
                height=dp(600),
                spacing=self.layout_data['spacing'],
                size_hint_x=None,
                width=self.layout_data['grid_width']  # 그리드 너비와 동일
            )

            # 시간 열 설정
            self.time_column = MDBoxLayout(
                orientation="vertical",
                size_hint_x=None,
                width=self.layout_data['time_col_width'],
                spacing=0
            )

            # 시간 열에 시간 레이블 추가
            hours_count = self.layout_data['end_hour'] - self.layout_data['start_hour']
            hour_height = dp(600) / hours_count  # 전체 높이를 시간대 수로 나눔
            
            # 시간을 위에서 아래로 순서대로 표시 (09:00부터 18:00까지)
            for hour in range(self.layout_data['start_hour'], self.layout_data['end_hour']):
                self.time_column.add_widget(MDLabel(
                    text=f"{hour:02d}:00",
                    halign="center",
                    valign="top",
                    size_hint_y=None,
                    height=hour_height,
                    theme_text_color="Secondary",
                    font_name=FONT_NAME  # FONT_NAME 변수 사용
                ))

            self.time_grid_layout.add_widget(self.time_column)

            # 시간표 그리드 추가
            self.time_grid = TimeGridWidget(layout_data=self.layout_data)
            self.time_grid_layout.add_widget(self.time_grid)
            self.grid_container.add_widget(self.time_grid_layout)
            
            # 플로팅 액션 버튼 (과목 추가)
            self.add_class_button = MDFloatingActionButton(
                icon="plus",
                pos_hint={"right": 0.98, "y": 0.02},
                md_bg_color=self.app.theme_cls.primary_color,
                on_release=self.add_class_dialog.show_dialog
            )
            self.add_widget(self.add_class_button)

            # 전자출결 앱 실행 버튼
            self.attendance_button = MDFloatingActionButton(
                icon="qrcode-scan",  # QR 코드 아이콘
                pos_hint={"right": 0.98, "y": 0.12},  # add_class_button보다 위에 위치
                md_bg_color=self.app.theme_cls.accent_color,  # 다른 색상으로 구분
                on_release=self.open_attendance_app
            )
            self.add_widget(self.attendance_button)

            # 기존 버튼들 뒤에 추가
            self.test_button = MDFloatingActionButton(
                icon="bell-ring",
                pos_hint={"right": 0.98, "y": 0.22},  # 다른 버튼들 위에
                md_bg_color=[1, 0.5, 0, 1],  # 주황색
                on_release=lambda x: self.test_notification()
            )
            self.add_widget(self.test_button)

            # 🔥 초기화 완료 플래그 설정
            self.layout_created = True
            print("✅ 레이아웃 설정 완료")
            
            # 🔥 시간표 로드를 좀 더 늦게 실행
            Clock.schedule_once(lambda dt: self.load_saved_timetable(), 0.8)
            
        except Exception as e:
            print(f"레이아웃 설정 오류: {e}")
            import traceback
            traceback.print_exc()
            # 오류 발생 시 다시 시도
            Clock.schedule_once(self.setup_layout, 0.5)

    def on_subtitle_touch(self, instance, touch):
        """부제목 터치 이벤트"""
        if instance.collide_point(*touch.pos):
            self.show_subtitle_edit_dialog(instance)
            return True
        return False
        
    def save_timetable(self):  
        """현재 시간표 저장"""
        success = self.storage.save_classes(self.classes_data)
        # 알람 데이터도 함께 저장 (Android용)
        if hasattr(self, 'alarm_manager') and self.alarm_manager is not None:
            try:
                import pickle
                # 앱의 내부 저장소에 저장 (app.alarm_file_path 사용)
                with open(self.app.alarm_file_path, 'wb') as f:
                    pickle.dump(self.alarm_manager.alarms, f)
                print("✅ Android 알람 시스템 초기화 완료")
            except Exception as e:
                print(f"알람 데이터 저장 오류: {e}")
        
        if success:
            print("시간표 저장 완료")

    def refresh_ui(self):
        """UI 새로고침"""
        try:
            print("🔄 UI 새로고침 시작")
            
            # 🔥 이미 초기화되었으면 다시 초기화하지 않음
            if self.layout_created and hasattr(self, 'time_grid'):
                print("✅ 이미 초기화됨 - 시간표만 새로고침")
                self.load_saved_timetable()
                return
                
            # 🔥 초기화되지 않았으면 레이아웃부터 다시 생성
            if not self.layout_created:
                print("🔧 레이아웃 재생성 필요")
                self.layout_created = False
                Clock.schedule_once(self.setup_layout, 0.1)
            
            print("✅ UI 새로고침 완료")
        except Exception as e:
            print(f"UI 새로고침 오류: {e}")
    
    def populate_edit_fields(self, class_id):
        """수정할 과목 데이터로 필드 채우기"""
        if class_id in self.classes_data:
            data = self.classes_data[class_id]
            
            # 필드에 기존 데이터 입력
            self.add_class_dialog.name_field.text = data['name']
            self.add_class_dialog.room_field.text = data['room']
            self.add_class_dialog.professor_field.text = data['professor']
            self.add_class_dialog.start_time_field.text = data['start_time']
            self.add_class_dialog.end_time_field.text = data['end_time']
            
            # 요일 설정
            day_kr_map = {"Monday": "월", "Tuesday": "화", "Wednesday": "수", "Thursday": "목", "Friday": "금"}
            self.add_class_dialog.day_field.text = day_kr_map.get(data['day'], "월")
            self.add_class_dialog.current_day = data['day']
            
            # 색상 설정
            self.add_class_dialog.selected_color = data['color']
            for i, color in enumerate(self.add_class_dialog.class_colors):
                if color == data['color']:
                    self.add_class_dialog.color_buttons[i].elevation = 3
                    self.add_class_dialog.selected_button_index = i
                else:
                    self.add_class_dialog.color_buttons[i].elevation = 0
    
    def confirm_delete_class(self, class_id):
        """과목 삭제 확인 다이얼로그"""
        self.add_class_dialog.dialog.dismiss()
        
        confirm_dialog = MDDialog(
            title="과목 삭제",
            text="정말로 이 과목을 삭제하시겠습니까?",
            buttons=[
                MDFlatButton(
                    text="취소",
                    font_name=FONT_NAME,
                    on_release=lambda x: confirm_dialog.dismiss()
                ),
                MDRaisedButton(
                    text="삭제",
                    font_name=FONT_NAME,
                    theme_bg_color="Custom",
                    md_bg_color=[1, 0.3, 0.3, 1],
                    on_release=lambda x: self.delete_class_confirmed(class_id, confirm_dialog)
                )
            ]
        )
        confirm_dialog.open()
    
    def delete_class_confirmed(self, class_id, dialog):
        """과목 삭제 실행"""
        # 화면에서 카드 제거
        for card in self.time_grid.children[:]:  # 복사본으로 순회
            if hasattr(card, 'class_data') and card.class_data.get('id') == class_id:
                self.time_grid.remove_widget(card)
                break
        
        # 데이터에서 삭제
        if class_id in self.classes_data:
            del self.classes_data[class_id]
        
        # 저장
        self.save_timetable()
        dialog.dismiss()
    
    def save_edited_class(self, class_id):
        """수정된 과목 저장"""
        # 기존 카드 제거
        for card in self.time_grid.children[:]:
            if hasattr(card, 'class_data') and card.class_data.get('id') == class_id:
                self.time_grid.remove_widget(card)
                break
        
        # 새 데이터로 카드 다시 생성
        name = self.add_class_dialog.name_field.text.strip()
        day = self.add_class_dialog.current_day
        start_time = self.add_class_dialog.start_time_field.text.strip()
        end_time = self.add_class_dialog.end_time_field.text.strip()
        room = self.add_class_dialog.room_field.text.strip()
        professor = self.add_class_dialog.professor_field.text.strip()
        
        if not all([name, day, start_time, end_time, room, professor]):
            return
        
        color_str = f"{self.add_class_dialog.selected_color[0]},{self.add_class_dialog.selected_color[1]},{self.add_class_dialog.selected_color[2]},{self.add_class_dialog.selected_color[3]}"
        
        # 카드 다시 추가
        self.add_class_to_grid(class_id, name, day, start_time, end_time, room, professor, color_str)
        
        self.add_class_dialog.dialog.dismiss()
        
    def add_class_to_grid(self, class_id, name, day, start_time, end_time, room, professor, color_str):
        
        # 시간 문자열을 숫자로 변환
        start_time_float = parse_time_string(start_time)
        end_time_float = parse_time_string(end_time)
    
        # 시간 값 검증
        if start_time_float is None or end_time_float is None:
            print(f"[스킵] 잘못된 시간 값: start={start_time}, end={end_time}")
            return
        
        layout_data = self.layout_data
        
        # 영어 또는 한글 요일 이름을 인덱스로 변환
        day_index = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4,
                    "월요일": 0, "화요일": 1, "수요일": 2, "목요일": 3, "금요일": 4}.get(day, 0)
        
        # TimeGridWidget의 get_day_column_x 메소드로 요일 열의 왼쪽 경계 가져오기
        day_column_left = self.time_grid.get_day_column_x(day_index)
        
        # 카드 크기 및 위치 계산
        day_col_width = layout_data['day_col_width']
        if day_index == 4:  # 금요일
            card_width = day_col_width - (layout_data['spacing'] * 2.0)  # 오른쪽 여백 늘림
        else:
            card_width = day_col_width - (layout_data['spacing'] * 1.1)  # 기존 너비 유지
        
        x = day_column_left + (layout_data['spacing'] * 1)
        
        
        # 시간대별 높이 계산
        hours_count = layout_data['end_hour'] - layout_data['start_hour']
        hour_height = self.time_grid.height / hours_count
        
        # 시작 시간과 그리드 시작 시간의 차이를 기준으로 시작 위치 계산
        start_offset_from_top = (start_time_float - layout_data['start_hour']) * hour_height
        
        # 뒤집어서 위에서부터 계산 (그리드 상단에서 시작)
        duration_height = (end_time_float - start_time_float) * hour_height
        y = self.time_grid.y + self.time_grid.height - start_offset_from_top - duration_height
        
        
        # 색상 문자열을 튜플로 변환
        try:
            color = tuple(map(float, color_str.split(',')))
        except Exception as e:
            print(f"색상 변환 오류: {e}, 기본색 사용")
            color = (0.6, 0.2, 0.8, 1)  # 기본 보라색
        
        try:
            # 카드 생성 및 위치 조정
            card = ClassCard(
                size_hint=(None, None),
                size=(card_width, duration_height),
                pos=(x, y),
                elevation=4,
                md_bg_color=color,
                radius=[dp(5)],
                ripple_behavior=True
            )
    
            print(f"카드 생성: 크기=({card_width}, {duration_height}), 위치=({x}, {y})")
            
            # 카드에 클래스 데이터 저장
            card.class_data = {
                'id': class_id,
                'name': name,
                'day': day,
                'start_time': start_time,
                'end_time': end_time,
                'room': room,
                'professor': professor,
                'color': color
            }
            
            # 클래스 데이터 저장소에 추가
            self.classes_data[class_id] = card.class_data.copy()
            
            # 카드 내용 추가
            card.add_widget(MDLabel(
                text=f"{name}\n{room}",
                halign="center",
                valign="center",
                font_name=FONT_NAME,
                font_size="4sp",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1)  # 흰색으로 설정
            ))
            
            # 시간표 그리드에 카드 추가
            self.time_grid.add_widget(card)
            
            # try-except 블록 밖에서 터치 핸들러 정의
            def make_touch_handler(card_instance, class_id):
                def handle_touch(instance, touch):
                    if instance.collide_point(*touch.pos):
                        self.edit_class_dialog.show_edit_dialog(card_instance)
                        return True
                    return False
                return handle_touch
    
            card.bind(on_touch_down=make_touch_handler(card, class_id))
            
            print(f"카드 생성: 크기=({card_width}, {duration_height}), 위치=({x}, {y})")
            
            # 클릭 이벤트 연결
            card.on_release_callback = lambda card: self.edit_class_dialog.show_edit_dialog(card)
            
            # 시간표 저장 - 카드가 성공적으로 추가된 후에 저장
            self.save_timetable()
                        
            # 알람 설정 (Android인 경우에만)
            if 'ANDROID_STORAGE' in os.environ and hasattr(self, 'alarm_manager') and self.alarm_manager is not None:
                # 알람 시간 (기본값: 5분 전)
                minutes_before = 5
                if hasattr(self.add_class_dialog, 'notify_input'):
                    try:
                        minutes_before = int(self.add_class_dialog.notify_input.text)
                    except:
                        minutes_before = 5
                
                # 알람 예약
                try:
                    self.alarm_manager.schedule_alarm(class_id, card.class_data, minutes_before)
                except Exception as e:
                    print(f"알람 스케줄링 오류: {e}")
                                    
            return True
                        
        except Exception as e:
            print(f"카드 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
                        
    def test_notification(self):
            """과목 알림 테스트 - 실제 과목 정보 포함"""
            try:
                if 'ANDROID_STORAGE' in os.environ:
                    # 시스템 알림 직접 호출
                    from jnius import autoclass
                    PythonActivity = autoclass('org.kivy.android.PythonActivity')
                    Context = autoclass('android.content.Context')
                    
                    # Android 기본 Notification 클래스 사용
                    Notification = autoclass('android.app.Notification')
                    NotificationManager = autoclass('android.app.NotificationManager')
                    Builder = autoclass('android.app.Notification$Builder')
                    
                    Intent = autoclass('android.content.Intent')
                    PendingIntent = autoclass('android.app.PendingIntent')
                    
                    # 컨텍스트 가져오기
                    context = PythonActivity.mActivity
                    
                    # 알림 채널 ID
                    channel_id = "timetable_alarm_channel"
                    
                    # 🔥 전자출결 앱 Intent (로그캣으로 확인한 정확한 액티비티명 사용)
                    try:
                        package_name = 'edu.skku.attend'
                        activity_name = 'edu.skku.attend.ui.activity.IntroActivity'  # 로그캣에서 확인한 정확한 이름
                        
                        # 방법 1: PackageManager 사용 (가장 안전)
                        pm = context.getPackageManager()
                        attendance_intent = pm.getLaunchIntentForPackage(package_name)
                        
                        if attendance_intent:
                            notification_action_text = "전자출결 앱 열기"
                            print("✅ PackageManager로 전자출결 앱 Intent 생성 성공")
                        else:
                            # 방법 2: 직접 액티비티명 지정 (로그캣에서 확인한 정확한 이름)
                            print("PackageManager 실패 - 직접 액티비티 지정 시도")
                            attendance_intent = Intent()
                            attendance_intent.setClassName(package_name, activity_name)
                            attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                            notification_action_text = "전자출결 앱 열기"
                            print(f"✅ 직접 액티비티 지정: {activity_name}")
                            
                    except Exception as e:
                        print(f"전자출결 앱 Intent 생성 오류: {e}")
                        # 실패 시 Play Store로
                        try:
                            Uri = autoclass('android.net.Uri')
                            store_uri = Uri.parse("market://details?id=edu.skku.attend")
                            attendance_intent = Intent(Intent.ACTION_VIEW, store_uri)
                            notification_action_text = "전자출결 앱 설치"
                            print("❌ 전자출결 앱 실행 실패 - Play Store로 이동")
                        except:
                            # 최후의 수단: 시간표 앱 실행
                            attendance_intent = Intent(context, PythonActivity)
                            attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                            notification_action_text = "시간표 앱 열기"
                    
                    # 🔥 Android 12+ 호환성을 위한 FLAG_IMMUTABLE 설정
                    FLAG_IMMUTABLE = 67108864  # PendingIntent.FLAG_IMMUTABLE
                    FLAG_UPDATE_CURRENT = 134217728  # PendingIntent.FLAG_UPDATE_CURRENT
                    
                    # PendingIntent 생성 (크래시 방지를 위해 FLAG_IMMUTABLE 필수)
                    pending_intent = PendingIntent.getActivity(
                        context, 
                        12345,  # 고유한 request code
                        attendance_intent, 
                        FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE  # 🔥 중요: FLAG_IMMUTABLE 추가
                    )
                    
                    # 📚 샘플 과목 정보 (실제로는 현재 시간에 해당하는 과목 정보 사용)
                    sample_class = {
                        'name': '소재부품융합공학',
                        'room': '61304A',
                        'professor': '김범준',
                        'time': '14:00',
                        'day': '월요일'
                    }
                    
                    # 알림 빌더 생성
                    builder = Builder(context, channel_id)
                    builder.setSmallIcon(context.getApplicationInfo().icon)
                    
                    # 📚 과목 정보가 포함된 알림 내용
                    builder.setContentTitle(f"🔔 수업 알림: {sample_class['name']}")
                    builder.setContentText(f"{sample_class['time']} | {sample_class['room']} | {sample_class['professor']} 교수님")
                    
                    # 확장된 알림 스타일 (BigTextStyle 사용)
                    try:
                        BigTextStyle = autoclass('android.app.Notification$BigTextStyle')
                        big_text_style = BigTextStyle()
                        expanded_text = (
                            f"📚 과목: {sample_class['name']}\n"
                            f"🕐 시간: {sample_class['day']} {sample_class['time']}\n"
                            f"🏛️ 강의실: {sample_class['room']}\n"
                            f"👨‍🏫 교수: {sample_class['professor']} 교수님\n\n"
                            f"📱 {notification_action_text}하려면 터치하세요"
                        )
                        big_text_style.bigText(expanded_text)
                        builder.setStyle(big_text_style)
                    except Exception as e:
                        print(f"BigTextStyle 설정 오류: {e}")
                    
                    # 알림 속성 설정
                    builder.setPriority(Notification.PRIORITY_HIGH)
                    builder.setContentIntent(pending_intent)  # 터치 시 실행될 Intent
                    builder.setAutoCancel(True)  # 터치 시 알림 자동 삭제
                    
                    # 진동 패턴 설정
                    try:
                        builder.setVibrate([0, 250, 250, 250])  # 진동 패턴
                    except:
                        pass
                    
                    # 알림 표시
                    notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
                    notification_manager.notify(9999, builder.build())
                    
                    print("✅ 과목 알림 전송 완료 (전자출결 앱 연동)")
                    
                else:
                    # PC 환경에서는 플라이어 사용
                    from plyer import notification
                    notification.notify(
                        title="🔔 수업 알림: 소재부품융합공학",
                        message="14:00 | 61304A | 김범준 교수님\n전자출결을 잊지 마세요!",
                        timeout=10
                    )
                    print("✅ PC용 알림 전송 완료")
                        
            except Exception as e:
                print(f"❌ 알림 테스트 실패: {e}")
                import traceback
                traceback.print_exc()
        
    def create_class_notification(self, class_data, minutes_before=5):
            """실제 과목 정보로 알림 생성"""
            try:
                if 'ANDROID_STORAGE' not in os.environ:
                    return  # Android 환경이 아니면 건너뛰기
                    
                from jnius import autoclass
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                
                Notification = autoclass('android.app.Notification')
                NotificationManager = autoclass('android.app.NotificationManager')
                Builder = autoclass('android.app.Notification$Builder')
                Intent = autoclass('android.content.Intent')
                PendingIntent = autoclass('android.app.PendingIntent')
                
                context = PythonActivity.mActivity
                channel_id = "timetable_alarm_channel"
                
                # 전자출결 앱 Intent 생성 (로그캣으로 확인한 정확한 액티비티명 사용)
                package_name = 'edu.skku.attend'
                activity_name = 'edu.skku.attend.ui.activity.IntroActivity'
                
                # 방법 1: PackageManager 사용
                pm = context.getPackageManager()
                attendance_intent = pm.getLaunchIntentForPackage(package_name)
                
                if attendance_intent:
                    action_text = "전자출결하기"
                else:
                    # 방법 2: 직접 액티비티명 지정
                    try:
                        attendance_intent = Intent()
                        attendance_intent.setClassName(package_name, activity_name)
                        attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                        action_text = "전자출결하기"
                    except:
                        # 실패 시 Play Store로
                        Uri = autoclass('android.net.Uri')
                        store_uri = Uri.parse("market://details?id=edu.skku.attend")
                        attendance_intent = Intent(Intent.ACTION_VIEW, store_uri)
                        action_text = "전자출결 앱 설치"
                
                # FLAG_IMMUTABLE 설정 (Android 12+ 필수)
                FLAG_IMMUTABLE = 67108864
                FLAG_UPDATE_CURRENT = 134217728
                
                pending_intent = PendingIntent.getActivity(
                    context,
                    int(class_data['id']),  # 과목 ID를 request code로 사용
                    attendance_intent,
                    FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE
                )
                
                # 요일을 한글로 변환
                day_kr = {
                    'Monday': '월요일', 'Tuesday': '화요일', 'Wednesday': '수요일',
                    'Thursday': '목요일', 'Friday': '금요일'
                }.get(class_data['day'], class_data['day'])
                
                # 알림 생성
                builder = Builder(context, channel_id)
                builder.setSmallIcon(context.getApplicationInfo().icon)
                builder.setContentTitle(f"🔔 {minutes_before}분 후 수업: {class_data['name']}")
                builder.setContentText(f"{class_data['start_time']} | {class_data['room']} | {class_data['professor']} 교수님")
                
                # 확장된 알림 내용
                try:
                    BigTextStyle = autoclass('android.app.Notification$BigTextStyle')
                    big_text_style = BigTextStyle()
                    expanded_text = (
                        f"📚 과목: {class_data['name']}\n"
                        f"🕐 시간: {day_kr} {class_data['start_time']}\n"
                        f"🏛️ 강의실: {class_data['room']}\n"
                        f"👨‍🏫 교수: {class_data['professor']} 교수님\n\n"
                        f"📱 {action_text}하려면 터치하세요"
                    )
                    big_text_style.bigText(expanded_text)
                    builder.setStyle(big_text_style)
                except:
                    pass
                
                builder.setPriority(Notification.PRIORITY_HIGH)
                builder.setContentIntent(pending_intent)
                builder.setAutoCancel(True)
                builder.setVibrate([0, 250, 250, 250])
                
                # 알림 표시
                notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
                notification_manager.notify(int(class_data['id']), builder.build())
                
                print(f"✅ {class_data['name']} 과목 알림 생성 완료")
                
            except Exception as e:
                print(f"❌ 과목 알림 생성 실패: {e}")
                import traceback
                traceback.print_exc()

class TimeTableApp(MDApp):
    def build(self):
        print("✅ build() 실행됨")
        Logger.info("MetaCheck: build 시작됨")
    
        try:
            with open("/sdcard/metacheck_log.txt", "a") as f:
                f.write("✅ build() 진입\n")
        except:
            pass  # PC에서는 이 경로가 없으므로 무시

        # 데이터 디렉토리 설정
        if 'ANDROID_STORAGE' in os.environ:
            # Android 환경에서 데이터 디렉토리 생성
            data_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "timetable_data"
            )
            if not os.path.exists(data_dir):
                os.makedirs(data_dir)
            print(f"Android 환경: 데이터 디렉토리 = {data_dir}")
            print(f"✅ 데이터 디렉토리 확인/생성 완료: {data_dir}")
            
            # 알람 파일 경로 설정 - 중요!
            self.alarm_file_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "alarms.pkl"
            )
            print(f"Android 알람 파일 경로: {self.alarm_file_path}")
        else:
            # PC 환경에서 기본 경로 설정
            self.alarm_file_path = "alarms.pkl"

        # 안드로이드에서는 윈도우 크기 설정하지 않음
        if 'ANDROID_STORAGE' not in os.environ:
            # PC 개발환경에서만 윈도우 크기 설정
            Window.size = (480, 800)
            
        # 🔥 Window 준비 대기 - 인자 수정!
        def wait_for_window(dt):  # ← dt 인자 추가!
            if Window.width > 100 and Window.height > 100:
                print(f"✅ Window 준비됨: {Window.width}x{Window.height}")
                return False  # 스케줄링 중단
            else:
                print(f"⏳ Window 대기 중: {Window.width}x{Window.height}")
                return True  # 계속 대기
        
        # Window가 준비될 때까지 대기
        Clock.schedule_interval(wait_for_window, 0.1)
        
        # 한글 폰트 설정
        self.theme_cls.font_styles.update({
            "H5": [FONT_NAME, 24, False, 0.15],
            "H6": [FONT_NAME, 20, False, 0.15],
            "Subtitle1": [FONT_NAME, 16, False, 0.15],
            "Subtitle2": [FONT_NAME, 14, True, 0.1],
            "Body1": [FONT_NAME, 16, False, 0.5],
            "Body2": [FONT_NAME, 14, False, 0.25],
            "Button": [FONT_NAME, 14, True, 1.25],
            "Caption": [FONT_NAME, 12, False, 0.4],
            "Overline": [FONT_NAME, 10, True, 1.5],
        })

        # 테마 설정
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.accent_palette = "Teal"
        self.theme_cls.theme_style = "Light"

        # Android에서 알림 채널 생성
        if 'ANDROID_STORAGE' in os.environ:
            try:
                from jnius import autoclass

                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                PythonActivity = autoclass('org.kivy.android.PythonActivity')

                context = PythonActivity.mActivity.getApplicationContext()
                notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)

                if notification_manager:
                    channel_id = "timetable_alarm_channel"
                    name = "시간표 알람"
                    description = "수업 시작 전 알람 알림"
                    importance = NotificationManager.IMPORTANCE_HIGH

                    channel = NotificationChannel(channel_id, name, importance)
                    channel.setDescription(description)
                    channel.enableVibration(True)
                    channel.setVibrationPattern([0, 250, 250, 250])
                    notification_manager.createNotificationChannel(channel)

                    print("✅ 알림 채널 생성 완료")
                    Logger.info("MetaCheck: 알림 채널 생성 성공")

            except Exception as e:
                import traceback
                try:
                    with open("/sdcard/metacheck_error.txt", "w") as f:
                        f.write(traceback.format_exc())
                except:
                    Logger.error(f"MetaCheck: 알림 채널 예외 - {e}")

        # 🔥 바로 메인 스크린 반환 (로딩 화면 완전 삭제)
        print("🔧 메인 스크린 바로 생성")
        self.main_screen = MainScreen(name="main", app=self)
        return self.main_screen  # 🔥 바로 메인 스크린 반환
    
    def on_start(self):
        """앱 시작 시 호출"""
        print("✅ 앱 시작됨")
        
    def on_resume(self):
        """백그라운드에서 돌아올 때 호출"""
        print("✅ 앱 재개됨")
        try:
            # UI 다시 초기화
            if hasattr(self, 'main_screen') and self.main_screen:
                Clock.schedule_once(lambda dt: self.main_screen.refresh_ui(), 0.1)
        except Exception as e:
            print(f"앱 재개 오류: {e}")
            
    def on_pause(self):
        """백그라운드로 갈 때 호출"""
        print("📱 앱 일시정지됨")
        return True  # True 반환해야 앱이 종료되지 않음
    
    def show_alarm_notification(self, class_name, class_room, class_time, class_professor):
        try:
            from plyer import notification
            title = f"수업 알림: {class_name}"
            message = f"{class_time}에 {class_room}에서 {class_professor} 교수님 수업이 있습니다."

            notification.notify(
                title=title,
                message=message,
                app_name="대학교 시간표",
                timeout=10
            )
        except Exception as e:
            print(f"알림 표시 오류: {e}")

if __name__ == "__main__":
    import sys
    print("✅ __main__ 진입")
    print(f"기본 인코딩: {sys.getdefaultencoding()}")
    print(f"사용 폰트: {FONT_NAME}")

    try:
        TimeTableApp().run()
    except Exception as e:
        import traceback
        try:
            with open("/sdcard/metacheck_error.txt", "w") as f:
                f.write(traceback.format_exc())
        except:
            print(traceback.format_exc())
