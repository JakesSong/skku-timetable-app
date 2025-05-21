from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class SimpleTimeTableApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        
        title = Label(
            text='성균관대학교 시간표',
            font_size='20sp',
            size_hint_y=None,
            height=50
        )
        
        btn1 = Button(text='월요일', size_hint_y=None, height=50)
        btn2 = Button(text='화요일', size_hint_y=None, height=50)
        btn3 = Button(text='수요일', size_hint_y=None, height=50)
        btn4 = Button(text='목요일', size_hint_y=None, height=50)
        btn5 = Button(text='금요일', size_hint_y=None, height=50)
        
        layout.add_widget(title)
        layout.add_widget(btn1)
        layout.add_widget(btn2)
        layout.add_widget(btn3)
        layout.add_widget(btn4)
        layout.add_widget(btn5)
        
        return layout

if __name__ == '__main__':
    SimpleTimeTableApp().run()