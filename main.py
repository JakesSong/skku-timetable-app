# -*- coding: utf-8 -*-
# University Timetable App (Using KivyMD) - Simplified Version
# Required libraries:
# pip install kivy kivymd


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
        return "Roboto"

# 폰트 설정 실행
FONT_NAME = setup_korean_font()

from kivymd.app import MDApp
from kivy.app import App 
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
        
        # 🔥 스크롤뷰 참조 저장용
        self.scroll_view = None

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
        """대화상자 생성 - 키보드 자동 스크롤 포함"""
        
        # 🔥 ScrollView로 감싸기 (키보드 가림 방지)
        self.scroll_view = ScrollView(
            size_hint_y=None,
            height=dp(400),  # 전체 높이를 줄여서 키보드 공간 확보
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4),
            scroll_type=['bars', 'content'],
            effect_cls='ScrollEffect'  # 부드러운 스크롤 효과
        )
        
        # 대화상자 내용 레이아웃
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(5),
            size_hint_y=None,
            height=dp(760),  # 높이를 조금 늘려서 충분한 스크롤 공간 확보
            padding=(dp(20), dp(20), dp(20), dp(15))
        )
        
        
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
            height=dp(20),
            spacing=dp(0),
            padding=(-40, 0, 0, 0),
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
            (0.9, 0.5, 0.2, 1),    # 주황색 (Orange)
            (0.8, 0.3, 0.6, 1),    # 분홍색 (Pink)
            (0.6, 0.2, 0.2, 1),    # 진한 빨간색 (Dark Red)
            (0.3, 0.9, 0.5, 1),    # 민트 그린 (Mint Green)  
            (0.4, 0.8, 1.0, 1),    # 하늘색 (Sky Blue)
            (0.3, 0.55, 0.96, 1),   # 진한 파란색 (Deep Blue)
            (0.5, 0.4, 0.8, 1),    # 보라색 (Purple)
            (0.7, 0.7, 0.7, 1),    # 진한 회색 (Dark Gray)
        ]
        
        self.selected_color = self.class_colors[0]  # 기본 색상
        self.color_buttons = []
    
        for i, color in enumerate(self.class_colors):
            # MDRectangleFlatButton 대신 MDCard 사용
            from kivymd.uix.card import MDCard
            color_btn = MDCard(
                size_hint=(None, None),
                size=(dp(35), dp(35)),  # 작은 크기
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
            text="Set Alarm",
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
            text="Minutes Before",
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
        
        # 🔥 키보드 가림 방지용 여분 공간 추가 (더 넉넉하게)
        extra_spacer = Widget(size_hint_y=None, height=dp(150))
        self.content.add_widget(extra_spacer)
    
        # 🔥 ScrollView에 콘텐츠 추가
        self.scroll_view.add_widget(self.content)
    
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
                            
                # 🔥 키보드 자동 스크롤 설정
                Clock.schedule_once(lambda dt: self.setup_keyboard_scroll(), 0.2)
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
                    on_release=lambda x: self.add_class()
                )
            ]
        
        # 🔥 팝업 대화상자 생성 - ScrollView를 content로 사용
        self.dialog = MDDialog(
            title="새 과목 추가" if not edit_mode else "과목 수정",
            type="custom",
            content_cls=self.scroll_view,  # ScrollView를 content로 사용
            size_hint=(0.90, 0.75),   # 높이를 75%로 조정하여 더 많은 키보드 공간 확보
            buttons=buttons
        )
        
        # 다이얼로그가 열릴 때 한 번 더 글꼴 설정 및 키보드 스크롤 설정
        self.dialog.bind(on_open=lambda *args: post_dialog_open(self.dialog))

        # 이 부분 추가
        print(f"🔍 다이얼로그 생성됨: {self.dialog}")
        print(f"🔍 버튼 개수: {len(buttons) if buttons else 0}")
        for i, btn in enumerate(buttons):
            print(f"🔍 버튼 {i}: {btn.text}")

    def setup_keyboard_scroll(self):
        """키보드 올라올 때 자동 스크롤 설정 - 개선된 버전"""
        # 각 텍스트 필드에 포커스 이벤트 바인딩
        fields = [
            self.name_field, 
            self.room_field, 
            self.professor_field, 
            self.notify_input
        ]
        
        print(f"🔧 자동 스크롤 설정: {len(fields)}개 필드")
        
        for i, field in enumerate(fields):
            print(f"   {i+1}. {field.hint_text}")
            field.bind(focus=self.on_field_focus)
            # 터치 이벤트도 추가로 바인딩
            field.bind(on_touch_down=lambda instance, touch: self.on_field_touch(instance, touch))
    
    def on_field_focus(self, instance, value):
        """텍스트 필드에 포커스가 갈 때 호출"""
        if value and self.scroll_view:  # 포커스를 얻었을 때
            print(f"🎯 필드 포커스: {instance.hint_text}")
            
            # 🔥 상단 필드들(과목명, 요일)은 스크롤하지 않음
            if hasattr(self, 'name_field') and instance == self.name_field:
                print("📝 과목명 필드 - 스크롤 안 함")
                return
            elif hasattr(self, 'day_field') and instance == self.day_field:
                print("📅 요일 필드 - 스크롤 안 함")
                return
            # 🔥 하단 필드들(교수명, 알람 설정)인 경우 최하단으로 스크롤
            elif hasattr(self, 'professor_field') and instance == self.professor_field:
                print("👨‍🏫 교수명 필드 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.5)
            elif hasattr(self, 'notify_input') and instance == self.notify_input:
                print("🔽 알람 설정 필드 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.5)
            else:
                # 중간 필드들(시간, 강의실)만 적당한 위치로 스크롤
                print("📍 중간 필드 - 적당한 위치로 스크롤")
                Clock.schedule_once(lambda dt: self.scroll_to_widget(instance), 0.6)
    
    def on_field_touch(self, instance, touch):
        """텍스트 필드 터치 시 호출"""
        if instance.collide_point(*touch.pos):
            print(f"👆 필드 터치: {instance.hint_text}")
            
            # 🔥 상단 필드들(과목명, 요일)은 스크롤하지 않음
            if hasattr(self, 'name_field') and instance == self.name_field:
                print("📝 과목명 필드 터치 - 스크롤 안 함")
                return False
            elif hasattr(self, 'day_field') and instance == self.day_field:
                print("📅 요일 필드 터치 - 스크롤 안 함")
                return False
            # 🔥 하단 필드들(교수명, 알람 설정)인 경우 최하단으로 스크롤
            elif hasattr(self, 'professor_field') and instance == self.professor_field:
                print("👨‍🏫 교수명 필드 터치 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.3)
            elif hasattr(self, 'notify_input') and instance == self.notify_input:
                print("🔽 알람 설정 필드 터치 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.3)
            else:
                # 중간 필드들만 적당한 위치로 스크롤
                print("📍 중간 필드 터치 - 적당한 위치로 스크롤")
                Clock.schedule_once(lambda dt: self.scroll_to_widget(instance), 0.3)
            return False  # 이벤트 전파 계속

    
    def scroll_to_widget(self, widget):
        """특정 위젯이 보이도록 부드럽게 스크롤 - 개선된 버전"""
        if not self.scroll_view or not widget:
            return
            
        try:
            print(f"🎯 스크롤 대상: {widget.hint_text}")
            
            # 현재 ScrollView와 Content 정보
            scroll_height = self.scroll_view.height
            content_height = self.content.height
            current_scroll = self.scroll_view.scroll_y
            
            print(f"📏 ScrollView 높이: {scroll_height}")
            print(f"📏 Content 높이: {content_height}")
            print(f"📏 현재 스크롤: {current_scroll:.2f}")
            
            # 위젯의 절대 위치 (content 기준)
            widget_y_in_content = widget.y
            widget_height = widget.height
            widget_top = widget_y_in_content + widget_height
            widget_bottom = widget_y_in_content
            
            print(f"📍 위젯 위치 (content 기준): y={widget_y_in_content}, 높이={widget_height}")
            print(f"📍 위젯 상단: {widget_top}, 하단: {widget_bottom}")
            
            # 키보드 높이 고려 (실제 가시 영역 계산)
            keyboard_height = dp(280)  # 일반적인 안드로이드 키보드 높이
            visible_height = scroll_height - keyboard_height * 0.7  # 키보드가 70% 가림
            
            print(f"⌨️ 키보드 높이: {keyboard_height}")
            print(f"👁️ 실제 가시 높이: {visible_height}")
            
            # 현재 보이는 영역 계산 (content 좌표계)
            # scroll_y = 0 (최하단), scroll_y = 1 (최상단)
            current_view_bottom = (1 - current_scroll) * content_height
            current_view_top = current_view_bottom + visible_height
            
            print(f"👀 현재 보이는 영역: 하단={current_view_bottom:.1f}, 상단={current_view_top:.1f}")
            
            # 위젯이 가시 영역에 완전히 들어와야 하는 목표 위치 계산
            margin = dp(50)  # 위젯 주변 여백
            
            # 위젯이 가시 영역 하단에 가려져 있는 경우
            if widget_bottom < current_view_bottom + margin:
                # 위젯 하단이 가시 영역 하단 근처에 오도록 스크롤
                target_view_bottom = widget_bottom - margin
                target_scroll_y = 1 - (target_view_bottom / content_height)
                action = "하단 가림 해결"
                
            # 위젯이 가시 영역 상단에 가려져 있는 경우  
            elif widget_top > current_view_top - margin:
                # 위젯 상단이 가시 영역 상단 근처에 오도록 스크롤
                target_view_top = widget_top + margin
                target_view_bottom = target_view_top - visible_height
                target_scroll_y = 1 - (target_view_bottom / content_height)
                action = "상단 가림 해결"
                
            else:
                # 위젯이 이미 보이는 상태
                print("✅ 위젯이 이미 가시 영역에 있음 - 스크롤 불필요")
                return
            
            # 스크롤 범위 제한 (0~1)
            target_scroll_y = max(0.0, min(1.0, target_scroll_y))
            
            print(f"🎯 {action}: {current_scroll:.2f} → {target_scroll_y:.2f}")
            
            # 스크롤 변화량이 너무 작으면 스킵
            if abs(target_scroll_y - current_scroll) < 0.05:
                print("📏 스크롤 변화량이 너무 작음 - 스킵")
                return
            
            # 부드러운 스크롤 애니메이션
            from kivy.animation import Animation
            anim = Animation(
                scroll_y=target_scroll_y, 
                duration=0.4,  # 조금 더 느리게
                transition='out_quart'  # 더 부드러운 전환
            )
            anim.start(self.scroll_view)
            
            print(f"🚀 스크롤 애니메이션 시작: {target_scroll_y:.2f}")
            
        except Exception as e:
            print(f"❌ 스크롤 계산 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def smart_scroll_to_bottom(self):
        """하단 필드 편집 시 자동으로 최하단으로 스크롤 - 들여쓰기 수정"""
        if not self.scroll_view:
            print("❌ scroll_view가 없음")
            return
            
        try:
            print(f"🔽 최하단 스크롤 시작")
            print(f"   현재 scroll_y: {self.scroll_view.scroll_y:.2f}")
            print(f"   목표 scroll_y: 0.0 (최하단)")
            
            # 부드럽게 최하단으로 스크롤
            from kivy.animation import Animation
            anim = Animation(
                scroll_y=0,  # 0은 최하단
                duration=0.4, 
                transition='out_cubic'
            )
            
            # 애니메이션 완료 시 콜백 - 🔥 들여쓰기 수정!
            def on_complete(animation, widget):
                print(f"✅ 최하단 스크롤 완료: {widget.scroll_y:.2f}")
            
            anim.bind(on_complete=on_complete)
            anim.start(self.scroll_view)
            
            print("🚀 최하단 스크롤 애니메이션 시작")
            
        except Exception as e:
            print(f"❌ 하단 스크롤 오류: {e}")
            import traceback
            traceback.print_exc()

    
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
        print("🔥🔥🔥 add_class 호출됨!")  # 이 줄만 추가
        name = self.name_field.text.strip()
        day = self.current_day
        start_time = self.start_time_field.text.strip()
        end_time = self.end_time_field.text.strip()
        room = self.room_field.text.strip()
        professor = self.professor_field.text.strip()
        
        # 🔥 알람 시간 가져오기 추가
        notify_before = 5  # 기본값
        if hasattr(self, 'notify_input') and self.notify_input.text.strip():
            try:
                notify_before = int(self.notify_input.text.strip())
                print(f"🔔 사용자 설정 알람: {notify_before}분")
            except ValueError:
                notify_before = 5  # 잘못된 입력시 기본값
                print(f"⚠️ 잘못된 알람 시간 입력, 기본값 사용: {notify_before}분")
        
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
        
        # 🔥 시간표에 과목 추가 (알람 시간도 함께 전달)
        success = self.screen.add_class_to_grid(
            self.next_class_id, name, day, start_time, end_time, room, professor, color_str, notify_before
        )
        
        if success:
            print(f"✅ 과목 추가 완료: {name} (ID: {self.next_class_id}, 알람: {notify_before}분)")
            self.next_class_id += 1
            # 대화상자 닫기
            self.dismiss_dialog()
        else:
            print(f"❌ 과목 추가 실패: {name}")


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
        
        # 🔥 스크롤뷰 참조 저장용
        self.scroll_view = None
        
        # 과목 색상 정의 (AddClassDialog와 동일하게 유지)
        self.class_colors = [
            (0.9, 0.5, 0.2, 1),    # 주황색 (Orange)
            (0.8, 0.3, 0.6, 1),    # 분홍색 (Pink)
            (0.6, 0.2, 0.2, 1),    # 진한 빨간색 (Dark Red)
            (0.3, 0.9, 0.5, 1),    # 민트 그린 (Mint Green)  
            (0.4, 0.8, 1.0, 1),    # 하늘색 (Sky Blue)
            (0.3, 0.55, 0.96, 1),   # 진한 파란색 (Deep Blue)
            (0.5, 0.4, 0.8, 1),    # 보라색 (Purple)
            (0.7, 0.7, 0.7, 1),    # 진한 회색 (Dark Gray)
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
        """과목 수정 대화상자 표시 - AddClassDialog와 동일한 패턴"""
        self.editing_card = card
        
        # 기존 다이얼로그가 있으면 닫기
        if self.dialog:
            self.dialog.dismiss()
            self.dialog = None
        
        # 새 다이얼로그 생성
        self.create_edit_dialog()
        
        # 기존 데이터로 필드 채우기
        self.populate_fields_with_existing_data(card.class_data)
        
        # 다이얼로그 열기
        self.dialog.open()
        
    def create_edit_dialog(self):
        """수정 다이얼로그 생성 - 키보드 자동 스크롤 포함"""
        
        # 🔥 ScrollView로 감싸기 (키보드 가림 방지)
        self.scroll_view = ScrollView(
            size_hint_y=None,
            height=dp(400),  # 전체 높이를 줄여서 키보드 공간 확보
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width=dp(4),
            scroll_type=['bars', 'content'],
            effect_cls='ScrollEffect'  # 부드러운 스크롤 효과
        )
        
        # 대화상자 내용 레이아웃
        self.content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(5),
            size_hint_y=None,
            height=dp(760),  # 높이를 조금 늘려서 충분한 스크롤 공간 확보
            padding=(dp(20), dp(20), dp(20), dp(15))
        )
        
        # 🔥 제목과의 간격을 주는 양수 스페이서 추가 (음수 대신 양수!)
        # positive_spacer = Widget(size_hint_y=None, height=dp(100))  # 🔥 20dp 간격 추가
        # self.content.add_widget(positive_spacer)
            
        # 과목명 입력
        self.name_field = MDTextField(
            hint_text="Class Name",
            helper_text="Ex: Physics1",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME
        )
        self.set_font_for_textfield(self.name_field)
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
        self.set_font_for_textfield(self.day_field)
        self.content.add_widget(self.day_field)
        
        # 요일 버튼 레이아웃
        days_layout = MDBoxLayout(
            orientation='horizontal',
            size_hint_y=None,
            height=dp(20),
            spacing=dp(0),
            padding=(-40, 0, 0, 0),
            adaptive_width=False
        )
        
        # 한글 요일 이름과 영어 요일 매핑
        day_names = {
            "Monday": "월",
            "Tuesday": "화",
            "Wednesday": "수",
            "Thursday": "목", 
            "Friday": "금"
        }
        
        for day, day_kr in day_names.items():
            day_btn = MDFlatButton(
                text=day_kr,
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
            readonly=True
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
            readonly=True
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
            font_name=FONT_NAME
        )
        self.set_font_for_textfield(self.room_field)
        self.content.add_widget(self.room_field)
        
        # 교수명
        self.professor_field = MDTextField(
            hint_text="Professor",
            helper_text="Ex: Kim Bumjun",
            helper_text_mode="on_focus",
            height=dp(20),
            font_name=FONT_NAME
        )
        self.set_font_for_textfield(self.professor_field)
        self.content.add_widget(self.professor_field)
    
        # 간격 위젯
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
    
        self.color_buttons = []
        for i, color in enumerate(self.class_colors):
            from kivymd.uix.card import MDCard
            color_btn = MDCard(
                size_hint=(None, None),
                size=(dp(35), dp(35)),
                md_bg_color=color,
                radius=[dp(2)],
                elevation=0  # 기본값
            )
            color_btn.bind(on_touch_down=lambda instance, touch, c=color, i=i: 
                        self.set_color(c, i) if instance.collide_point(*touch.pos) else None)
            
            self.color_buttons.append(color_btn)
            colors_layout.add_widget(color_btn)
                
        self.content.add_widget(colors_layout)
    
        # 간격 위젯
        spacer = Widget(size_hint_y=None, height=dp(10))
        self.content.add_widget(spacer)
    
        # 알림 설정 레이블
        self.notify_label = MDLabel(
            text="Set Alarm",
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
            text="5",  # 기본값
            font_name=FONT_NAME,
            size_hint_x=0.2,
        )
        self.set_font_for_textfield(self.notify_input)
    
        # "Minute" 레이블
        minute_label = MDLabel(
            text="Minutes Before",
            theme_text_color="Secondary",
            font_name=FONT_NAME,
            size_hint_x=0.8,
            halign="left",
            valign="center"
        )
    
        notify_layout.add_widget(self.notify_input)
        notify_layout.add_widget(minute_label)
        self.content.add_widget(notify_layout)
        
        # 🔥 키보드 가림 방지용 여분 공간 추가 (더 넉넉하게)
        extra_spacer = Widget(size_hint_y=None, height=dp(150))
        self.content.add_widget(extra_spacer)
    
        # 🔥 ScrollView에 콘텐츠 추가
        self.scroll_view.add_widget(self.content)
    
        # 폰트 설정 함수
        def post_dialog_open(dialog):
            try:
                if hasattr(dialog, '_title'):
                    dialog._title.font_name = FONT_NAME
                
                if hasattr(dialog, 'content_cls'):
                    for child in dialog.content_cls.children:
                        if isinstance(child, MDTextField):
                            self.set_font_for_textfield(child)
                            
                # 🔥 키보드 자동 스크롤 설정
                Clock.schedule_once(lambda dt: self.setup_keyboard_scroll(), 0.2)
            except Exception as e:
                print(f"다이얼로그 폰트 설정 오류: {e}")
    
        # 버튼 생성
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
        
        # 🔥 다이얼로그 생성 - ScrollView를 content로 사용
        self.dialog = MDDialog(
            title="과목 수정",
            type="custom",
            content_cls=self.scroll_view,  # ScrollView를 content로 사용
            size_hint=(0.90, 0.75),   # 높이를 75%로 조정하여 더 많은 키보드 공간 확보
            buttons=buttons
        )
        
        # 다이얼로그가 열릴 때 폰트 설정 및 키보드 스크롤 설정
        self.dialog.bind(on_open=lambda *args: post_dialog_open(self.dialog))

    def setup_keyboard_scroll(self):
        """키보드 올라올 때 자동 스크롤 설정 - 개선된 버전"""
        # 각 텍스트 필드에 포커스 이벤트 바인딩
        fields = [
            self.name_field, 
            self.room_field, 
            self.professor_field, 
            self.notify_input
        ]
        
        print(f"🔧 자동 스크롤 설정: {len(fields)}개 필드")
        
        for i, field in enumerate(fields):
            print(f"   {i+1}. {field.hint_text}")
            field.bind(focus=self.on_field_focus)
            # 터치 이벤트도 추가로 바인딩
            field.bind(on_touch_down=lambda instance, touch: self.on_field_touch(instance, touch))
    
    def on_field_focus(self, instance, value):
        """텍스트 필드에 포커스가 갈 때 호출"""
        if value and self.scroll_view:  # 포커스를 얻었을 때
            print(f"🎯 필드 포커스: {instance.hint_text}")
            
            # 🔥 상단 필드들(과목명, 요일)은 스크롤하지 않음
            if hasattr(self, 'name_field') and instance == self.name_field:
                print("📝 과목명 필드 - 스크롤 안 함")
                return
            elif hasattr(self, 'day_field') and instance == self.day_field:
                print("📅 요일 필드 - 스크롤 안 함")
                return
            # 🔥 하단 필드들(교수명, 알람 설정)인 경우 최하단으로 스크롤
            elif hasattr(self, 'professor_field') and instance == self.professor_field:
                print("👨‍🏫 교수명 필드 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.5)
            elif hasattr(self, 'notify_input') and instance == self.notify_input:
                print("🔽 알람 설정 필드 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.5)
            else:
                # 중간 필드들(시간, 강의실)만 적당한 위치로 스크롤
                print("📍 중간 필드 - 적당한 위치로 스크롤")
                Clock.schedule_once(lambda dt: self.scroll_to_widget(instance), 0.6)
    
    def on_field_touch(self, instance, touch):
        """텍스트 필드 터치 시 호출"""
        if instance.collide_point(*touch.pos):
            print(f"👆 필드 터치: {instance.hint_text}")
            
            # 🔥 상단 필드들(과목명, 요일)은 스크롤하지 않음
            if hasattr(self, 'name_field') and instance == self.name_field:
                print("📝 과목명 필드 터치 - 스크롤 안 함")
                return False
            elif hasattr(self, 'day_field') and instance == self.day_field:
                print("📅 요일 필드 터치 - 스크롤 안 함")
                return False
            # 🔥 하단 필드들(교수명, 알람 설정)인 경우 최하단으로 스크롤
            elif hasattr(self, 'professor_field') and instance == self.professor_field:
                print("👨‍🏫 교수명 필드 터치 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.3)
            elif hasattr(self, 'notify_input') and instance == self.notify_input:
                print("🔽 알람 설정 필드 터치 - 최하단으로 스크롤")
                Clock.schedule_once(lambda dt: self.smart_scroll_to_bottom(), 0.3)
            else:
                # 중간 필드들만 적당한 위치로 스크롤
                print("📍 중간 필드 터치 - 적당한 위치로 스크롤")
                Clock.schedule_once(lambda dt: self.scroll_to_widget(instance), 0.3)
            return False  # 이벤트 전파 계속
    
    def scroll_to_widget(self, widget):
        """특정 위젯이 보이도록 부드럽게 스크롤 - 개선된 버전"""
        if not self.scroll_view or not widget:
            return
            
        try:
            print(f"🎯 스크롤 대상: {widget.hint_text}")
            
            # 현재 ScrollView와 Content 정보
            scroll_height = self.scroll_view.height
            content_height = self.content.height
            current_scroll = self.scroll_view.scroll_y
            
            print(f"📏 ScrollView 높이: {scroll_height}")
            print(f"📏 Content 높이: {content_height}")
            print(f"📏 현재 스크롤: {current_scroll:.2f}")
            
            # 위젯의 절대 위치 (content 기준)
            widget_y_in_content = widget.y
            widget_height = widget.height
            widget_top = widget_y_in_content + widget_height
            widget_bottom = widget_y_in_content
            
            print(f"📍 위젯 위치 (content 기준): y={widget_y_in_content}, 높이={widget_height}")
            print(f"📍 위젯 상단: {widget_top}, 하단: {widget_bottom}")
            
            # 키보드 높이 고려 (실제 가시 영역 계산)
            keyboard_height = dp(280)  # 일반적인 안드로이드 키보드 높이
            visible_height = scroll_height - keyboard_height * 0.7  # 키보드가 70% 가림
            
            print(f"⌨️ 키보드 높이: {keyboard_height}")
            print(f"👁️ 실제 가시 높이: {visible_height}")
            
            # 현재 보이는 영역 계산 (content 좌표계)
            # scroll_y = 0 (최하단), scroll_y = 1 (최상단)
            current_view_bottom = (1 - current_scroll) * content_height
            current_view_top = current_view_bottom + visible_height
            
            print(f"👀 현재 보이는 영역: 하단={current_view_bottom:.1f}, 상단={current_view_top:.1f}")
            
            # 위젯이 가시 영역에 완전히 들어와야 하는 목표 위치 계산
            margin = dp(50)  # 위젯 주변 여백
            
            # 위젯이 가시 영역 하단에 가려져 있는 경우
            if widget_bottom < current_view_bottom + margin:
                # 위젯 하단이 가시 영역 하단 근처에 오도록 스크롤
                target_view_bottom = widget_bottom - margin
                target_scroll_y = 1 - (target_view_bottom / content_height)
                action = "하단 가림 해결"
                
            # 위젯이 가시 영역 상단에 가려져 있는 경우  
            elif widget_top > current_view_top - margin:
                # 위젯 상단이 가시 영역 상단 근처에 오도록 스크롤
                target_view_top = widget_top + margin
                target_view_bottom = target_view_top - visible_height
                target_scroll_y = 1 - (target_view_bottom / content_height)
                action = "상단 가림 해결"
                
            else:
                # 위젯이 이미 보이는 상태
                print("✅ 위젯이 이미 가시 영역에 있음 - 스크롤 불필요")
                return
            
            # 스크롤 범위 제한 (0~1)
            target_scroll_y = max(0.0, min(1.0, target_scroll_y))
            
            print(f"🎯 {action}: {current_scroll:.2f} → {target_scroll_y:.2f}")
            
            # 스크롤 변화량이 너무 작으면 스킵
            if abs(target_scroll_y - current_scroll) < 0.05:
                print("📏 스크롤 변화량이 너무 작음 - 스킵")
                return
            
            # 부드러운 스크롤 애니메이션
            from kivy.animation import Animation
            anim = Animation(
                scroll_y=target_scroll_y, 
                duration=0.4,  # 조금 더 느리게
                transition='out_quart'  # 더 부드러운 전환
            )
            anim.start(self.scroll_view)
            
            print(f"🚀 스크롤 애니메이션 시작: {target_scroll_y:.2f}")
            
        except Exception as e:
            print(f"❌ 스크롤 계산 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def smart_scroll_to_bottom(self):
        """하단 필드 편집 시 자동으로 최하단으로 스크롤 - 개선된 버전"""
        if not self.scroll_view:
            print("❌ scroll_view가 없음")
            return
            
        try:
            print(f"🔽 최하단 스크롤 시작")
            print(f"   현재 scroll_y: {self.scroll_view.scroll_y:.2f}")
            print(f"   목표 scroll_y: 0.0 (최하단)")
            
            # 부드럽게 최하단으로 스크롤
            from kivy.animation import Animation
            anim = Animation(
                scroll_y=0,  # 0은 최하단
                duration=0.4, 
                transition='out_cubic'
            )
            
            # 애니메이션 완료 시 콜백
            def on_complete(animation, widget):
                print(f"✅ 최하단 스크롤 완료: {widget.scroll_y:.2f}")
            
            anim.bind(on_complete=on_complete)
            anim.start(self.scroll_view)
            
            print("🚀 최하단 스크롤 애니메이션 시작")
            
        except Exception as e:
            print(f"❌ 하단 스크롤 오류: {e}")
            import traceback
            traceback.print_exc()
    
    def populate_fields_with_existing_data(self, class_data):
        """기존 데이터로 필드 채우기"""
        # 필드에 기존 데이터 입력
        self.name_field.text = class_data['name']
        self.room_field.text = class_data['room']
        self.professor_field.text = class_data['professor']
        self.start_time_field.text = class_data['start_time']
        self.end_time_field.text = class_data['end_time']
        
        # 요일 설정
        korean_day_map = {
            "Monday": "월",
            "Tuesday": "화", 
            "Wednesday": "수",
            "Thursday": "목",
            "Friday": "금"
        }
        self.day_field.text = korean_day_map.get(class_data['day'], "월")
        self.current_day = class_data['day']
        
        # 색상 설정
        self.selected_color = class_data['color']
        for i, color in enumerate(self.class_colors):
            if color == self.selected_color:
                self.color_buttons[i].elevation = 3
                self.selected_button_index = i
            else:
                self.color_buttons[i].elevation = 0
        
        # 알림 시간 설정
        self.notify_input.text = str(class_data.get('notify_before', 5))

    def update_class(self, *args):
        """과목 정보 업데이트 - 중복 생성 방지 + 알람 시간 반영"""
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
        
        # 1단계: 메모리에서 기존 데이터 삭제
        if class_id in self.screen.classes_data:
            del self.screen.classes_data[class_id]
            print(f"✅ 메모리에서 기존 데이터 삭제: {class_id}")
        
        # 2단계: 화면에서 기존 카드 제거
        try:
            self.screen.time_grid.remove_widget(self.editing_card)
            print(f"✅ 화면에서 기존 카드 제거: {class_id}")
        except Exception as e:
            print(f"⚠️ 카드 제거 실패: {e}")
        
        # 3단계: 기존 알람 취소
        if hasattr(self.screen, 'cancel_in_app_alarm'):
            # 3단계: 기존 인앱 알람 취소
            try:
                self.screen.cancel_in_app_alarm(class_id)
                print(f"✅ 기존 인앱 알람 취소: {class_id}")
            except Exception as e:
                print(f"⚠️ 인앱 알람 취소 실패: {e}")
        
        # 4단계: 색상 정보 준비
        color_str = f"{self.selected_color[0]},{self.selected_color[1]},{self.selected_color[2]},{self.selected_color[3]}"
        
        # 🔥 5단계: 알림 시간 가져오기 (여기가 핵심!)
        notify_before = int(self.notify_input.text) if self.notify_input.text.strip() else 5
        print(f"🔔 수정된 알람 시간: {notify_before}분")
        
        # 🔥 6단계: 새로운 카드 생성 (동일한 ID로, 알람 시간 포함!)
        success = self.screen.add_class_to_grid(
            class_id, name, day, start_time, end_time, room, professor, color_str, notify_before
        )
        
        if success:
            print(f"✅ 과목 수정 완료: {name} (ID: {class_id}, 알람: {notify_before}분 전)")
            
            # 대화상자 닫기
            self.dialog.dismiss()
        else:
            print(f"❌ 과목 수정 실패: {name}")
        
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
    
        # 🔥 AlarmManager 초기화 - 안전한 버전 (app에도 설정)
        self.alarm_manager = None
        if 'ANDROID_STORAGE' in os.environ:
            try:
                from alarm_manager import AlarmManager
                self.alarm_manager = AlarmManager(app)
                # 🔥 중요: app 객체에도 alarm_manager 속성 추가!
                self.app.alarm_manager = self.alarm_manager
                print("✅ Android 알람 매니저 초기화 완료")
            except ImportError:
                print("⚠️ alarm_manager 모듈을 찾을 수 없습니다.")
                self.alarm_manager = None
                self.app.alarm_manager = None  # 🔥 app에도 None 설정
            except Exception as e:
                print(f"❌ 알람 매니저 초기화 실패: {e}")
                self.alarm_manager = None
                self.app.alarm_manager = None  # 🔥 app에도 None 설정
        else:
            print("💻 PC 환경 - 알람 매니저 비활성화")
            self.app.alarm_manager = None  # 🔥 PC에서도 app에 설정
        
        # 초기화 상태 플래그
        self.is_initialized = False
        self.layout_created = False
        
        # 즉시 레이아웃 설정 시도
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
        """저장된 시간표 불러오기 - 중복 생성 방지"""
        
        # 🔥 1단계: 기존 카드들 모두 제거 (중복 방지)
        if hasattr(self, 'time_grid') and self.time_grid:
            print("🧹 기존 카드들 정리 중...")
            # 기존 카드들을 모두 제거
            for card in self.time_grid.children[:]:  # 복사본으로 순회
                if hasattr(card, 'class_data'):
                    self.time_grid.remove_widget(card)
                    print(f"🗑️ 기존 카드 제거: {card.class_data.get('name', '알 수 없음')}")
            
            # 메모리 정리
            self.classes_data.clear()
            print("✅ 기존 카드 및 데이터 정리 완료")
        
        # 🔥 2단계: 저장된 데이터 로드
        saved_classes = self.storage.load_classes()
        
        if not saved_classes:
            # 저장된 시간표가 없으면 빈 시간표로 시작
            print("📄 저장된 시간표가 없습니다. 새 시간표를 만드세요.")
            self.add_class_dialog.next_class_id = 1  # ID는 1부터 시작
            return
        
        # 🔥 3단계: 저장된 시간표 복원
        print(f"📚 저장된 과목 {len(saved_classes)}개 불러오는 중...")
        max_id = 0
        success_count = 0
        
        for class_id, class_data in saved_classes.items():
            try:
                # 색상 처리
                color = class_data['color']
                if isinstance(color, str) and ',' in color:
                    color_str = color
                else:
                    color_str = ','.join(map(str, color))
                
                # 🔥 과목 카드 생성 및 추가 (알람 시간 포함)
                notify_before = class_data.get('notify_before', 5)  # 저장된 알람 시간 또는 기본값 5분
                success = self.add_class_to_grid(
                    class_data['id'], 
                    class_data['name'], 
                    class_data['day'], 
                    class_data['start_time'], 
                    class_data['end_time'], 
                    class_data['room'], 
                    class_data['professor'], 
                    color_str,
                    notify_before  # 🔥 알람 시간 전달
                )
                
                if success:
                    success_count += 1
                    # 알람 시간 데이터 복원
                    if 'notify_before' in class_data:
                        self.classes_data[class_data['id']]['notify_before'] = class_data['notify_before']
                    
                    print(f"✅ 과목 복원: {class_data['name']} (ID: {class_data['id']})")
                else:
                    print(f"❌ 과목 복원 실패: {class_data['name']}")
                
                # 최대 ID 갱신
                max_id = max(max_id, int(class_data['id']))
                
            except Exception as e:
                print(f"❌ 과목 카드 생성 오류 ({class_data.get('name', '알 수 없음')}): {e}")
                import traceback
                traceback.print_exc()
        
        # 🔥 4단계: 다음 ID 설정
        self.add_class_dialog.next_class_id = max_id + 1
        
        print(f"🎉 시간표 불러오기 완료: {success_count}/{len(saved_classes)}개 성공")
        print(f"🆔 다음 과목 ID: {self.add_class_dialog.next_class_id}")

    def safe_load_timetable(self):
        """안전한 시간표 로드 - 중복 방지"""
        try:
            # time_grid가 준비되었는지 확인
            if not hasattr(self, 'time_grid') or not self.time_grid:
                print("⏳ time_grid가 아직 준비되지 않음 - 재시도")
                Clock.schedule_once(lambda dt: self.safe_load_timetable(), 0.5)
                return
            
            # 이미 카드가 있으면 중복 로드 방지
            existing_cards = [child for child in self.time_grid.children if hasattr(child, 'class_data')]
            if existing_cards:
                print(f"⚠️ 이미 {len(existing_cards)}개 카드가 있음 - 로드 스킵")
                return
            
            print("🔄 안전한 시간표 로드 시작")
            self.load_saved_timetable()

            # 🔥 새로 추가: 모든 알람 예약
            Clock.schedule_once(lambda dt: self.load_and_schedule_all_alarms(), 2.0)
            
        except Exception as e:
            print(f"❌ 안전한 시간표 로드 실패: {e}")
            import traceback
            traceback.print_exc()
            
                
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
            
            # 🔥 플로팅 액션 버튼 - 이벤트 바인딩 수정
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

            # 테스트 알람 버튼 (주석처리)
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
            
            # 🔥 시간표 로드를 더 안전하게 실행 (한 번만!)
            if not hasattr(self, '_timetable_loaded'):  # 중복 로드 방지 플래그
                Clock.schedule_once(lambda dt: self.safe_load_timetable(), 1.0)  # 1초 후 실행
                self._timetable_loaded = True
                print("📅 시간표 로드 예약됨")

            # 🔥🔥🔥 더미 데이터 추가 (새로 추가하는 부분)
            # Clock.schedule_once(lambda dt: self.add_dummy_data(), 2.0)  # 2초 후 더미 데이터 추가
            
                        
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


    def add_dummy_data(self):
        """테스트용 더미 과목 데이터 추가"""
        print("🔥 더미 데이터 추가 시작")
        
        # 더미 과목들
        dummy_classes = [
            {
                'id': 1001,
                'name': '컴퓨터프로그래밍',
                'day': 'Monday',
                'start_time': '09:00',
                'end_time': '10:30',
                'room': '61304A',
                'professor': '김교수',
                'color': '0.9,0.5,0.2,1',  # 주황색
                'notify_before': 5
            },
            {
                'id': 1002, 
                'name': '데이터구조',
                'day': 'Tuesday',
                'start_time': '13:00',
                'end_time': '14:30',
                'room': '61305B',
                'professor': '이교수',
                'color': '0.3,0.9,0.5,1',  # 민트그린
                'notify_before': 10
            },
            {
                'id': 1003,
                'name': '알고리즘',
                'day': 'Wednesday', 
                'start_time': '15:00',
                'end_time': '16:30',
                'room': '61306C',
                'professor': '박교수',
                'color': '0.4,0.8,1.0,1',  # 하늘색
                'notify_before': 15
            },
            {
                'id': 1004,
                'name': '소프트웨어공학',
                'day': 'Thursday',
                'start_time': '10:00', 
                'end_time': '11:30',
                'room': '61307D',
                'professor': '최교수',
                'color': '0.5,0.4,0.8,1',  # 보라색
                'notify_before': 5
            },
            {
                'id': 1005,
                'name': '데이터베이스',
                'day': 'Friday',
                'start_time': '14:00',
                'end_time': '15:30', 
                'room': '61308E',
                'professor': '정교수',
                'color': '0.8,0.3,0.6,1',  # 분홍색
                'notify_before': 20
            }
        ]
        
        # time_grid가 준비되었는지 확인
        if not hasattr(self, 'time_grid') or not self.time_grid:
            print("❌ time_grid가 아직 준비되지 않음")
            # 1초 후 다시 시도
            Clock.schedule_once(lambda dt: self.add_dummy_data(), 1.0)
            return
        
        success_count = 0
        for dummy_class in dummy_classes:
            try:
                success = self.add_class_to_grid(
                    dummy_class['id'],
                    dummy_class['name'], 
                    dummy_class['day'],
                    dummy_class['start_time'],
                    dummy_class['end_time'],
                    dummy_class['room'],
                    dummy_class['professor'],
                    dummy_class['color'],
                    dummy_class['notify_before']
                )
                
                if success:
                    success_count += 1
                    print(f"✅ 더미 과목 추가 성공: {dummy_class['name']}")
                else:
                    print(f"❌ 더미 과목 추가 실패: {dummy_class['name']}")
                    
            except Exception as e:
                print(f"❌ 더미 과목 추가 오류 ({dummy_class['name']}): {e}")
        
        print(f"🎉 더미 데이터 추가 완료: {success_count}/{len(dummy_classes)}개 성공")
        
        # 다음 ID 설정 (더미 데이터 이후)
        self.add_class_dialog.next_class_id = 1006

    
    def request_alarm_permission(self):
        """알람 권한 요청 (Android 12+)"""
        try:
            from jnius import autoclass
            
            Intent = autoclass('android.content.Intent')
            Settings = autoclass('android.provider.Settings')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            
            # 알람 권한 설정 페이지로 이동
            intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM)
            PythonActivity.mActivity.startActivity(intent)
            
            print("알람 권한을 허용해주세요!")
            
        except Exception as e:
            print(f"권한 요청 실패: {e}")    

    # MainScreen 클래스에 추가할 인앱 알람 시스템
    
    def calculate_next_class_time(self, class_data):
        """다음 수업 시간 계산"""
        from datetime import datetime, timedelta
        
        day_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2,
            "Thursday": 3, "Friday": 4
        }
        
        day = class_data.get("day")
        start_time = class_data.get("start_time")
        
        if not day or not start_time:
            return None
        
        target_weekday = day_map.get(day)
        if target_weekday is None:
            return None
        
        # 현재 시간
        now = datetime.now()
        today_weekday = now.weekday()
        
        # 다음 수업까지 남은 날 계산
        days_ahead = (target_weekday - today_weekday) % 7
        target_date = now + timedelta(days=days_ahead)
        
        # 수업 시간 설정
        hour, minute = map(int, start_time.split(":"))
        class_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # 오늘 수업인데 이미 지났으면 다음 주로
        if class_datetime <= now:
            class_datetime += timedelta(days=7)
        
        return class_datetime
    
    def schedule_in_app_alarm(self, class_data, notify_before=5):
        """앱 실행 중일 때만 작동하는 인앱 알람"""
        try:
            # 다음 수업 시간 계산
            class_time = self.calculate_next_class_time(class_data)
            if not class_time:
                print(f"❌ 시간 계산 실패: {class_data['name']}")
                return False
            
            # 알람 시간 계산
            from datetime import timedelta, datetime
            alarm_time = class_time - timedelta(minutes=notify_before)
            
            # 현재 시간과의 차이 계산
            now = datetime.now()
            delay_seconds = (alarm_time - now).total_seconds()
            
            if delay_seconds > 0:
                # 기존 알람이 있으면 취소
                self.cancel_in_app_alarm(class_data['id'])
                
                # Kivy Clock으로 알람 예약
                event = Clock.schedule_once(
                    lambda dt: self.show_class_notification(class_data), 
                    delay_seconds
                )
                
                # 알람 정보 저장 (취소용)
                if not hasattr(self, 'scheduled_alarms'):
                    self.scheduled_alarms = {}
                self.scheduled_alarms[class_data['id']] = event
                
                print(f"⏰ 인앱 알람 예약: {class_data['name']} - {delay_seconds/60:.1f}분 후")
                print(f"📅 수업 시간: {class_time.strftime('%Y-%m-%d %H:%M')}")
                print(f"⏰ 알람 시간: {alarm_time.strftime('%Y-%m-%d %H:%M')}")
                return True
            else:
                print(f"⏭️ 이미 지난 시간: {class_data['name']}")
                return False
                
        except Exception as e:
            print(f"❌ 인앱 알람 설정 실패: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def cancel_in_app_alarm(self, class_id):
        """특정 과목의 인앱 알람 취소"""
        try:
            if hasattr(self, 'scheduled_alarms') and class_id in self.scheduled_alarms:
                event = self.scheduled_alarms[class_id]
                event.cancel()  # Clock 이벤트 취소
                del self.scheduled_alarms[class_id]
                print(f"✅ 인앱 알람 취소됨: ID {class_id}")
                return True
        except Exception as e:
            print(f"❌ 인앱 알람 취소 실패: {e}")
        return False
    
    def cancel_all_in_app_alarms(self):
        """모든 인앱 알람 취소"""
        try:
            if hasattr(self, 'scheduled_alarms'):
                for class_id, event in self.scheduled_alarms.items():
                    event.cancel()
                self.scheduled_alarms.clear()
                print("✅ 모든 인앱 알람 취소됨")
        except Exception as e:
            print(f"❌ 모든 알람 취소 실패: {e}")
    
    def show_class_notification(self, class_data):
        """수업 알림 표시 (실제 알람이 울릴 때 호출됨)"""
        try:
            print(f"🔔 알림 표시: {class_data['name']} 수업!")
            
            # Android에서는 시스템 알림
            if 'ANDROID_STORAGE' in os.environ:
                self.create_class_notification(class_data)
            else:
                # PC에서는 콘솔 출력
                print(f"📚 {class_data['name']} 수업이 곧 시작됩니다!")
                print(f"🏛️ 강의실: {class_data['room']}")
                print(f"👨‍🏫 교수: {class_data['professor']}")
                
            # 알람이 울린 후 다음 주 알람 자동 설정
            self.schedule_in_app_alarm(class_data, class_data.get('notify_before', 5))
            
        except Exception as e:
            print(f"❌ 알림 표시 실패: {e}")
    
    def load_and_schedule_all_alarms(self):
        """저장된 모든 과목의 인앱 알람 예약"""
        try:
            if not hasattr(self, 'classes_data'):
                print("📚 시간표 데이터가 없습니다.")
                return
            
            success_count = 0
            for class_id, class_data in self.classes_data.items():
                notify_before = class_data.get('notify_before', 5)
                if self.schedule_in_app_alarm(class_data, notify_before):
                    success_count += 1
            
            print(f"🎉 인앱 알람 일괄 설정 완료: {success_count}/{len(self.classes_data)}개")
            
            # 사용자에게 안내 메시지
            if success_count > 0:
                self.show_in_app_alarm_info()
                
        except Exception as e:
            print(f"❌ 일괄 알람 설정 실패: {e}")
    
    def show_in_app_alarm_info(self):
        """인앱 알람 사용법 안내"""
        try:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            
            info_dialog = MDDialog(
                title="📱 인앱 알람 설정 완료",
                text="알람이 설정되었습니다!\n\n"
                     "⚠️ 중요: 알람이 울리려면 앱을 켜두세요.\n"
                     "앱이 꺼지면 알람이 작동하지 않습니다.\n\n"
                     "💡 팁: 앱을 백그라운드에서 실행하거나\n"
                     "배터리 절약 모드에서 제외해주세요.",
                buttons=[
                    MDFlatButton(
                        text="확인",
                        theme_text_color="Custom",
                        text_color=self.app.theme_cls.primary_color,
                        font_name=FONT_NAME,
                        on_release=lambda x: info_dialog.dismiss()
                    )
                ]
            )
            info_dialog.text_font_name = FONT_NAME
            info_dialog.open()
            
        except Exception as e:
            print(f"❌ 안내 대화상자 오류: {e}")

    # MainScreen 클래스에 추가할 포어그라운드 서비스 함수들
    # 위치: MainScreen 클래스 내부, show_in_app_alarm_info() 함수 다음에 추가
    
    
    from datetime import datetime, timedelta
    from kivy.clock import Clock
    
    def format_remaining_time(target_time):
        now = datetime.now()
        delta = target_time - now
        seconds = int(delta.total_seconds())
        if seconds <= 0:
            return "수업 시작됨!"
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{s:02d} 남음"
    
    def get_class_datetime(self, class_data):
        day_map = {
            "Monday": 0, "Tuesday": 1, "Wednesday": 2,
            "Thursday": 3, "Friday": 4,
            "월요일": 0, "화요일": 1, "수요일": 2,
            "목요일": 3, "금요일": 4
        }
        weekday = day_map.get(class_data['day'], 0)
        hour, minute = map(int, class_data['start_time'].split(":"))
        now = datetime.now()
        today = now.weekday()
        delta = (weekday - today + 7) % 7
        class_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0) + timedelta(days=delta)
        return class_time
    
    def update_foreground_notification(self, target_time):
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        Context = autoclass('android.content.Context')
        Notification = autoclass('android.app.Notification')
        Builder = autoclass('android.app.Notification$Builder')
        NotificationManager = autoclass('android.app.NotificationManager')
    
        context = PythonActivity.mActivity
        channel_id = "foreground_service_channel"
        text = format_remaining_time(target_time)
    
        builder = Builder(context, channel_id)
        builder.setSmallIcon(context.getApplicationInfo().icon)
        builder.setContentTitle("📚 수업 카운트다운")
        builder.setContentText(text)
        builder.setOngoing(True)
        builder.setPriority(Notification.PRIORITY_LOW)
    
        notification = builder.build()
        manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
        manager.notify(1001, notification)
    
    def trigger_alarm(self, class_data):
        try:
            from plyer import notification
            notification.notify(
                title=f"{class_data['name']} 수업 시작!",
                message=f"{class_data['start_time']}에 수업이 시작됩니다.",
                timeout=10
            )
            print(f"🔔 알람 울림: {class_data['name']}")
        except Exception as e:
            print(f"❌ 알림 실패: {e}")
    
    def start_countdown_notification(self, class_data):
        target_time = self.get_class_datetime(class_data)
    
        def update(dt):
            now = datetime.now()
            if (target_time - now).total_seconds() <= 0:
                Clock.unschedule(update)
                self.trigger_alarm(class_data)
            else:
                self.update_foreground_notification(target_time)
    
        Clock.schedule_interval(update, 1)
    
    def start_foreground_service(self):
            """포어그라운드 서비스 시작 - "앱이 작동중" 알림 표시"""
            try:
                if 'ANDROID_STORAGE' not in os.environ:
                    print("💻 PC 환경 - 포어그라운드 서비스 불가")
                    return False
                    
                from jnius import autoclass
                
                # Android 클래스들
                PythonActivity = autoclass('org.kivy.android.PythonActivity')
                Context = autoclass('android.content.Context')
                NotificationManager = autoclass('android.app.NotificationManager')
                NotificationChannel = autoclass('android.app.NotificationChannel')
                Notification = autoclass('android.app.Notification')
                Builder = autoclass('android.app.Notification$Builder')
                PendingIntent = autoclass('android.app.PendingIntent')
                Intent = autoclass('android.content.Intent')
                
                context = PythonActivity.mActivity
                
                # 알림 채널 생성
                channel_id = "foreground_service_channel"
                channel_name = "시간표 알람 서비스"
                importance = NotificationManager.IMPORTANCE_LOW  # 조용한 알림
                
                notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
                channel = NotificationChannel(channel_id, channel_name, importance)
                channel.setDescription("시간표 알람이 백그라운드에서 작동중입니다")
                channel.setSound(None, None)  # 소리 없음
                notification_manager.createNotificationChannel(channel)
                
                # 앱 실행 Intent (알림 터치시 앱으로 돌아가기)
                app_intent = Intent(context, PythonActivity)
                app_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                
                # PendingIntent 생성
                FLAG_IMMUTABLE = 67108864
                FLAG_UPDATE_CURRENT = 134217728
                pending_intent = PendingIntent.getActivity(
                    context, 0, app_intent, FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE
                )
                
                # 포어그라운드 알림 생성
                builder = Builder(context, channel_id)
                builder.setSmallIcon(context.getApplicationInfo().icon)
                builder.setContentTitle("📚 시간표 알람 활성화")
                builder.setContentText("수업 알람이 백그라운드에서 작동중입니다")
                builder.setOngoing(True)  # 스와이프로 삭제 불가
                builder.setPriority(Notification.PRIORITY_LOW)  # 낮은 우선순위
                builder.setContentIntent(pending_intent)
                
                notification = builder.build()
                
                # ❌ 위험한 startForeground 시도 제거
                # ✅ 바로 일반 지속 알림만 사용
                notification_manager.notify(1001, notification)
                print("✅ 백그라운드 알림 표시 완료")
                return True
                
            except Exception as e:
                print(f"❌ 백그라운드 알림 실패: {e}")
                return False
    
    def stop_foreground_service(self):
        """포어그라운드 서비스 중지"""
        try:
            if 'ANDROID_STORAGE' not in os.environ:
                return
                
            from jnius import autoclass
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            NotificationManager = autoclass('android.app.NotificationManager')
            
            context = PythonActivity.mActivity
            notification_manager = context.getSystemService(Context.NOTIFICATION_SERVICE)
            
            # 포어그라운드 알림 제거
            notification_manager.cancel(1001)
            print("✅ 포어그라운드 서비스 중지됨")
            
        except Exception as e:
            print(f"❌ 포어그라운드 서비스 중지 실패: {e}")
    
    def schedule_foreground_alarm(self, class_data, notify_before=5):
        """포어그라운드 서비스와 함께 알람 설정"""
        try:
            # 1단계: 포어그라운드 서비스 시작
            if not hasattr(self, '_foreground_started'):
                service_started = self.start_foreground_service()
                if service_started:
                    self._foreground_started = True
                    print("🔄 포어그라운드 서비스로 업그레이드")
                self.start_countdown_notification(class_data)
            
            # 2단계: 기존 인앱 알람 방식과 동일
            success = self.schedule_in_app_alarm(class_data, notify_before)
            
            if success:
                print(f"✅ 포어그라운드 알람 설정: {class_data['name']}")
                print("📱 이제 앱을 종료해도 알람이 작동합니다!")
            
            return success
            
        except Exception as e:
            print(f"❌ 포어그라운드 알람 설정 실패: {e}")
            return False
    
    def show_foreground_service_info(self):
        """포어그라운드 서비스 안내 메시지"""
        try:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            
            info_dialog = MDDialog(
                title="🚀 백그라운드 알람 활성화",
                text="포어그라운드 서비스가 시작되었습니다!\n\n"
                     "✅ 이제 앱을 종료해도 알람이 작동합니다\n"
                     "✅ '앱이 작동중입니다' 알림이 계속 표시됩니다\n"
                     "✅ 시스템이 앱을 강제 종료하지 않습니다\n\n"
                     "⚠️ 알림을 끄지 마세요 (알람이 중지됩니다)",
                buttons=[
                    MDFlatButton(
                        text="확인",
                        theme_text_color="Custom",
                        text_color=self.app.theme_cls.primary_color,
                        font_name=FONT_NAME,
                        on_release=lambda x: info_dialog.dismiss()
                    )
                ]
            )
            info_dialog.text_font_name = FONT_NAME
            info_dialog.open()
            
        except Exception as e:
            print(f"❌ 안내 대화상자 오류: {e}")
    
    
    def refresh_ui(self):
        """UI 새로고침 - 중복 방지"""
        try:
            print("🔄 UI 새로고침 시작")
            
            # 🔥 이미 초기화되었으면 시간표만 안전하게 새로고침
            if self.layout_created and hasattr(self, 'time_grid'):
                print("✅ 이미 초기화됨 - 안전한 시간표 새로고침")
                # 중복 로드 방지를 위해 safe_load_timetable 사용
                Clock.schedule_once(lambda dt: self.safe_load_timetable(), 0.1)
                return
                
            # 🔥 초기화되지 않았으면 레이아웃부터 다시 생성
            if not self.layout_created:
                print("🔧 레이아웃 재생성 필요")
                self.layout_created = False
                self._timetable_loaded = False  # 로드 플래그도 초기화
                Clock.schedule_once(self.setup_layout, 0.1)
            
            print("✅ UI 새로고침 완료")
        except Exception as e:
            print(f"UI 새로고침 오류: {e}")
    
    
        
    def add_class_to_grid(self, class_id, name, day, start_time, end_time, room, professor, color_str, notify_before=5):
        # 🔥 맨 앞에 추가: 중복 확인
        for existing_card in self.time_grid.children[:]:
            if hasattr(existing_card, 'class_data') and existing_card.class_data.get('id') == class_id:
                print(f"🔄 기존 카드 발견 - 제거 중: {class_id}")
                self.time_grid.remove_widget(existing_card)
                break
                
        # 시간 문자열을 숫자로 변환
        start_time_float = parse_time_string(start_time)
        end_time_float = parse_time_string(end_time)
    
        # 시간 값 검증
        if start_time_float is None or end_time_float is None:
            print(f"[스킵] 잘못된 시간 값: start={start_time}, end={end_time}")
            return False
        
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
            
            # 🔥 카드에 클래스 데이터 저장 (알람 시간 포함)
            card.class_data = {
                'id': class_id,
                'name': name,
                'day': day,
                'start_time': start_time,
                'end_time': end_time,
                'room': room,
                'professor': professor,
                'color': color,
                'notify_before': notify_before  # 🔥 알람 시간 저장
            }
            
            # 🔥 클래스 데이터 저장소에 추가 (알람 시간 포함)
            self.classes_data[class_id] = card.class_data.copy()
            print(f"💾 클래스 데이터 저장: {name} (알람: {notify_before}분)")
                        
            # 카드 내용 추가 - 이 부분만 교체!
            card_label = MDLabel(
                text=f"{name}\n{room}",
                halign="center",
                valign="center",
                font_name=FONT_NAME,
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1)  # 흰색으로 설정
            )
            
            # 강제로 작은 폰트 크기 적용
            Clock.schedule_once(lambda dt: setattr(card_label, 'font_size', 28), 0.1)
            card.add_widget(card_label)
            
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
            
            # 🔥 인앱 알람 설정
            class_data_for_alarm = {
                'id': class_id,
                'name': name,
                'day': day,
                'start_time': start_time,
                'end_time': end_time,
                'room': room,
                'professor': professor,
                'color': color,
                'notify_before': notify_before
            }
            
            success = self.schedule_in_app_alarm(class_data_for_alarm, notify_before)
            if success:
                print(f"✅ 인앱 알람 설정 성공: {name}")
            else:
                print(f"❌ 인앱 알람 설정 실패: {name}")
        
            # 시간표 저장 - 수정 중이 아닐 때만 저장
            if not hasattr(self, '_updating_class'):
                self.save_timetable()
        
            return True
                            
        except Exception as e:
            print(f"카드 생성 중 오류 발생: {e}")
            import traceback
            traceback.print_exc()
            return False
                        

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
                    action_text = "전자출결 앱을 "
                else:
                    # 방법 2: 직접 액티비티명 지정
                    try:
                        attendance_intent = Intent()
                        attendance_intent.setClassName(package_name, activity_name)
                        attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                        action_text = "전자출결 앱을 "
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

                # 사용자가 설정한 알람 시간 가져오기
                user_alarm_time = class_data.get('notify_before', 5)  # 기본값 5분

                
                # 알림 생성
                builder = Builder(context, channel_id)
                builder.setSmallIcon(context.getApplicationInfo().icon)
                builder.setContentTitle(f"🔔 {user_alarm_time}분 후 수업: {class_data['name']}")
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
                        f"📱 {action_text} Open 하려면 터치하세요"
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
                            notification_action_text = "전자출결 앱을 "
                            print("✅ PackageManager로 전자출결 앱 Intent 생성 성공")
                        else:
                            # 방법 2: 직접 액티비티명 지정 (로그캣에서 확인한 정확한 이름)
                            print("PackageManager 실패 - 직접 액티비티 지정 시도")
                            attendance_intent = Intent()
                            attendance_intent.setClassName(package_name, activity_name)
                            attendance_intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP)
                            notification_action_text = "전자출결 앱을 "
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
                        'name': '공학컴퓨터프로그래밍',
                        'room': '61352',
                        'professor': '황숙희',
                        'time': '15:00',
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
                            f"📱 {notification_action_text} Open 하려면 터치하세요"
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

class TimeTableApp(MDApp):
    def build(self):
        print("✅ build() 실행됨")
        Logger.info("DoubleCheck: build 시작됨")
    
        try:
            with open("/sdcard/doublecheck_log.txt", "a") as f:
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
                    Logger.info("DoubleCheck: 알림 채널 생성 성공")

            except Exception as e:
                import traceback
                try:
                    with open("/sdcard/doublecheck_error.txt", "w") as f:
                        f.write(traceback.format_exc())
                except:
                    Logger.error(f"DoubleCheck: 알림 채널 예외 - {e}")

        # Android에서 백그라운드 서비스 시작
        if 'ANDROID_STORAGE' in os.environ:
            try:
                self.start_background_service()
                print("✅ 백그라운드 알림 서비스 시작됨")
            except Exception as e:
                print(f"❌ 백그라운드 서비스 시작 실패: {e}")
        
        # 🔥 바로 메인 스크린 반환 (로딩 화면 완전 삭제)
        print("🔧 메인 스크린 바로 생성")
        self.main_screen = MainScreen(name="main", app=self)
        return self.main_screen  # 🔥 바로 메인 스크린 반환
    
    def on_start(self):
        """앱 시작시 포어그라운드 서비스 자동 시작"""
        print("✅ 앱 시작됨")
        
        # 포어그라운드 서비스 자동 시작
        if hasattr(self, 'main_screen'):
            Clock.schedule_once(
                lambda dt: self.main_screen.start_foreground_service(), 
                2.0
            )
        
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
            error_file = os.path.join(App.get_running_app().user_data_dir, "error.txt")
            with open(error_file, 'w') as f:
                f.write(traceback.format_exc())
        except:
            print(traceback.format_exc())

