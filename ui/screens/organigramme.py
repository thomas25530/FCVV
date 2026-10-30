from kivy.app import App
from kivy.uix.screenmanager import Screen
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line
from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.utils import platform
import os
import hashlib
import threading
import requests
import traceback

FIXED_WIDTH = dp(140)
SPACING = dp(10)  
INNER_SPACING = dp(10)

class TitleBox(BoxLayout):
    def __init__(self, text, **kwargs):
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (1, None)
        if 'height' not in kwargs:
            kwargs['height'] = dp(45)
            
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.1, 0.2, 0.4, 0.9)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),size=lambda i, s: setattr(self.rect, "size", s))

        self.lbl = Label(
            text=f"[color=ffffff][b]{text}[/b][/color]",
            markup=True,
            font_size="13sp", 
            halign="center",
            valign="middle",
        )
        # On laisse de la marge pour éviter les dépassements
        self.lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (value[0] - dp(15), None)))
        self.add_widget(self.lbl)

class MemberBox(ButtonBehavior, BoxLayout):
    def __init__(self, member_data, **kwargs):
        self.member_data = member_data
        
        self.has_extra_info = any(
            str(member_data.get(key, '')).strip() != '' 
            for key in ['tel', 'email', 'taches', 'photo_id']
        )
        
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (1, None)
        if 'height' not in kwargs:
            kwargs['height'] = dp(90)  # Hauteur légèrement augmentée pour éviter la coupe verticale
            
        super().__init__(orientation="vertical", **kwargs)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)  # Fond Blanc
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),
                  size=lambda i, s: setattr(self.rect, "size", s))

        txt = f"[color=1E3A8A][b]{member_data.get('titre', '')}[/b][/color]\n[color=333333]{member_data.get('nom', '')}[/color]"
        self.lbl = Label(
            text=txt, markup=True, font_size="12sp", halign="center", 
            valign="middle"
        )
        # On retire dp(35) de largeur pour laisser la place à la loupe et forcer le retour à la ligne propre
        self.lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (value[0] - dp(35), None)))
        self.add_widget(self.lbl)
        
        if self.has_extra_info:
            self.add_widget(Image(
                source="assets/icons/loupe.png",
                size_hint=(None, None), 
                size=(dp(20), dp(20)),
                pos_hint={'right': 0.95, 'top': 0.95},
                color=(0.6, 0.6, 0.6, 1)
            ))
            self.bind(on_release=self.show_contact_card)

    def on_press(self):
        if self.has_extra_info:
            self.canvas.before.children[0].rgba = (0.9, 0.9, 0.9, 1)

    def on_release(self):
        if self.has_extra_info:
            self.canvas.before.children[0].rgba = (1, 1, 1, 1)

    def show_contact_card(self, *args):
        if not self.has_extra_info:
            return
            
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
        
        photo_id = self.member_data.get("photo_id")
        if photo_id:
            url = f"https://drive.usercontent.google.com/download?id={photo_id}&export=download"
            cache_dir = os.path.join(App.get_running_app().user_data_dir, "member_cache")
            url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
            local_path = os.path.join(cache_dir, f"memb_{url_hash}.png")
        
            if os.path.exists(local_path):
                img_widget = Image(source=local_path, size_hint=(1, None), height=dp(200), fit_mode="contain")
            else:
                img_widget = Image(opacity=0, size_hint=(1, None), height=dp(200), fit_mode="contain")
                self.load_member_image(url, img_widget)
        else:
            img_widget = Image(source="assets/default_user.png", size_hint=(1, None), height=dp(200), fit_mode="contain")

        content.add_widget(img_widget)
        
        content.add_widget(Label(text=f"[color=FFD700][b]{self.member_data.get('titre', '')}[/b][/color]", markup=True, font_size="16sp", size_hint_y=None, height=dp(25)))
        content.add_widget(Label(text=f"[b]{self.member_data.get('nom', 'Non renseigné')}[/b]", markup=True, font_size="20sp", size_hint_y=None, height=dp(30)))
        content.add_widget(Label(text=f"Tél : {self.member_data.get('tel', 'N/A')}", size_hint_y=None, height=dp(20)))
        content.add_widget(Label(text=f"Email : {self.member_data.get('email', 'N/A')}", size_hint_y=None, height=dp(20)))
        
        content.add_widget(Label(
            text=f"Fonctions au sein du club :\n{self.member_data.get('taches', 'Aucune tâche définie')}", 
            halign="center", valign="top",
            size_hint_y=None, height=dp(60) 
        ))
        
        content.add_widget(Widget()) 
        btn_close = Button(text="Fermer", size_hint=(1, None), height=dp(50))
        
        popup = Popup(title="Fiche Contact", content=content, size_hint=(0.85, 0.85))
        btn_close.bind(on_release=popup.dismiss)
        content.add_widget(btn_close)
        
        popup.open()

    def load_member_image(self, url, img_widget):
        app = App.get_running_app()
        cache_dir = os.path.join(app.user_data_dir, "member_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        local_path = os.path.join(cache_dir, f"memb_{url_hash}.png")

        def fetch():
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
                return
            try:
                r = requests.get(url, timeout=10, verify=False)
                if r.status_code == 200:
                    with open(local_path, "wb") as f:
                        f.write(r.content)
                    Clock.schedule_once(lambda dt: self._apply_img(img_widget, local_path), 0)
            except Exception as e:
                print(f"Erreur image: {e}")

        threading.Thread(target=fetch, daemon=True).start()

    def _apply_img(self, widget, path):
        widget.source = path
        widget.reload()
        widget.opacity = 1

class ComiteBox(ButtonBehavior, BoxLayout):
    """Carte spéciale pour afficher la liste des membres du comité."""
    def __init__(self, comite_membres, **kwargs):
        self.comite_membres = comite_membres or []
        
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (1, None)
        if 'height' not in kwargs:
            kwargs['height'] = dp(90)  # Hauteur augmentée pour éviter la coupe verticale
            
        super().__init__(orientation="vertical", **kwargs)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)  # Fond blanc
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),
                  size=lambda i, s: setattr(self.rect, "size", s))

        txt = "[color=1E3A8A][b]Comité[/b][/color]\n[color=333333]Liste des membres[/color]"
        self.lbl = Label(text=txt, markup=True, font_size=dp(11.5), halign="center", valign="middle")
        # Retrait de dp(35) pour forcer le retour à la ligne avant la loupe
        self.lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (value[0] - dp(35), None)))
        
        self.add_widget(self.lbl)
        self.add_widget(Image(
            source="assets/icons/loupe.png",
            size_hint=(None, None), 
            size=(dp(20), dp(20)),
            pos_hint={'right': 0.95, 'top': 0.95},
            color=(0.6, 0.6, 0.6, 1)
        ))
        
        self.bind(on_release=self.show_comite_popup)

    def on_press(self):
        self.canvas.before.children[0].rgba = (0.9, 0.9, 0.9, 1)

    def on_release(self):
        self.canvas.before.children[0].rgba = (1, 1, 1, 1)

    def show_comite_popup(self, *args):
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        
        content.add_widget(Label(
            text="[color=FFD700][b]Membres du Comité[/b][/color]", 
            markup=True, font_size="18sp", size_hint_y=None, height=dp(40),
            halign="center", valign="middle"
        ))
        
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=0)
        list_layout = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_x=1, size_hint_y=None, padding=(dp(10), dp(10)))
        list_layout.bind(minimum_height=list_layout.setter("height"))
        
        if self.comite_membres:
            for m in self.comite_membres:
                if isinstance(m, dict):
                    display_text = f"{m.get('prenom', '')} {m.get('nom', '')}".strip() or m.get('titre', 'Membre')
                else:
                    display_text = str(m)

                lbl_m = Label(
                    text=f"[color=FFFFFF][b]{display_text}[/b][/color]",
                    markup=True, 
                    font_size=dp(15),
                    size_hint_x=1,
                    size_hint_y=None, 
                    halign="center", 
                    valign="middle"
                )
                
                def update_member_label(instance, width):
                    instance.text_size = (max(0, width - dp(20)), None)
                
                lbl_m.bind(
                    width=update_member_label,
                    texture_size=lambda instance, size:
                        setattr(instance, "height", size[1] + dp(8))
                )
                
                list_layout.add_widget(lbl_m)
        else:
            list_layout.add_widget(Label(
                text="[color=AAAAAA]Aucun membre enregistré.[/color]", 
                markup=True, font_size="14sp", size_hint_x=1, size_hint_y=None, height=dp(40),
                halign="center", valign="middle"
            ))
            
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        
        btn_close = Button(text="Fermer", size_hint=(1, None), height=dp(50))
        popup = Popup(title="Comité du Club", content=content, size_hint=(0.8, 0.8))
        btn_close.bind(on_release=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

class ArbitrageBox(ButtonBehavior, BoxLayout):
    """Carte spéciale pour afficher la liste des arbitres du club."""
    def __init__(self, arbitres_membres, **kwargs):
        self.arbitres_membres = arbitres_membres or []
        
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (1, None)
        if 'height' not in kwargs:
            kwargs['height'] = dp(90)  # Hauteur augmentée pour éviter la coupe verticale
            
        super().__init__(orientation="vertical", **kwargs)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)  # Fond blanc
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),
                  size=lambda i, s: setattr(self.rect, "size", s))

        txt = "[color=1E3A8A][b]Arbitrage[/b][/color]\n[color=333333]Liste des arbitres[/color]"
        self.lbl = Label(text=txt, markup=True, font_size=dp(11.5), halign="center", valign="middle")
        # Retrait de dp(35) pour forcer le retour à la ligne avant la loupe
        self.lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (value[0] - dp(35), None)))
        
        self.add_widget(self.lbl)
        self.add_widget(Image(
            source="assets/icons/loupe.png",
            size_hint=(None, None), 
            size=(dp(20), dp(20)),
            pos_hint={'right': 0.95, 'top': 0.95},
            color=(0.6, 0.6, 0.6, 1)
        ))
        
        self.bind(on_release=self.show_arbitrage_popup)

    def on_press(self):
        self.canvas.before.children[0].rgba = (0.9, 0.9, 0.9, 1)

    def on_release(self):
        self.canvas.before.children[0].rgba = (1, 1, 1, 1)

    def show_arbitrage_popup(self, *args):
        content = BoxLayout(orientation="vertical", padding=dp(15), spacing=dp(10))
        
        content.add_widget(Label(
            text="[color=FFD700][b]Arbitres du Club[/b][/color]", 
            markup=True, font_size="18sp", size_hint_y=None, height=dp(40),
            halign="center", valign="middle"
        ))
        
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=0)
        list_layout = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_x=1, size_hint_y=None, padding=(dp(10), dp(10)))
        list_layout.bind(minimum_height=list_layout.setter("height"))
        
        if self.arbitres_membres:
            for m in self.arbitres_membres:
                if isinstance(m, dict):
                    display_text = f"{m.get('prenom', '')} {m.get('nom', '')}".strip() or m.get('titre', 'Arbitre')
                else:
                    display_text = str(m)

                lbl_m = Label(
                    text=f"[color=FFFFFF][b]{display_text}[/b][/color]",
                    markup=True, 
                    font_size=dp(15),
                    size_hint_x=1,
                    size_hint_y=None, 
                    halign="center", 
                    valign="middle"
                )
                
                def update_member_label(instance, width):
                    instance.text_size = (max(0, width - dp(20)), None)
                
                lbl_m.bind(
                    width=update_member_label,
                    texture_size=lambda instance, size:
                        setattr(instance, "height", size[1] + dp(8))
                )
                
                list_layout.add_widget(lbl_m)
        else:
            list_layout.add_widget(Label(
                text="[color=AAAAAA]Aucun arbitre enregistré.[/color]", 
                markup=True, font_size="14sp", size_hint_x=1, size_hint_y=None, height=dp(40),
                halign="center", valign="middle"
            ))
            
        scroll.add_widget(list_layout)
        content.add_widget(scroll)
        
        btn_close = Button(text="Fermer", size_hint=(1, None), height=dp(50))
        popup = Popup(title="Arbitrage du Club", content=content, size_hint=(0.8, 0.8))
        btn_close.bind(on_release=popup.dismiss)
        content.add_widget(btn_close)
        popup.open()

class OrganigrammeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.main_col = None
        self.row_level = None
        self.nodes = {}
        self.scroll = None

    def on_enter(self):      
        self.clear_widgets()
        self.nodes = {}
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True, bar_width=0)
        is_desktop_debug = True 
        bottom_padding = dp(80) if (platform == 'android' or is_desktop_debug) else dp(40)
        self.main_col = BoxLayout(orientation="vertical", spacing=dp(60), padding=(dp(10), dp(40), dp(10), bottom_padding), size_hint=(1, None))
        self.main_col.bind(minimum_height=self.main_col.setter("height"))
        self.scroll.add_widget(self.main_col)
        self.add_widget(self.scroll)
        
        data = (App.get_running_app().app_config.get("fcvv", {}).get("appli", {}).get("organigramme", []))
        
        # 1. BLOC DIRECTION
        dir_data = next((i for i in data if i["groupe"] == "Direction"), None)
        if dir_data:
            node = self.build_group_node(dir_data)
            self.nodes["Direction"] = node
            self.main_col.add_widget(node)
            
        self.main_col.add_widget(Widget(size_hint_y=None, height=dp(20)))
        
        # 2. BLOC DES 3 COLONNES
        groupes = ["Bureau", "Dirigeants", "Équipe Technique"]
        max_membres = 0
        for g in groupes:
            g_data = next((i for i in data if i["groupe"] == g), None)
            if g_data:
                count = len(g_data.get("membres", []))
                if g == "Bureau":
                    count += 1  # Carte Comité
                if g == "Équipe Technique":  # Ajuster si vous placez l'arbitrage ici
                    count += 1  # Carte Arbitrage
                max_membres = max(max_membres, count) 
                
        computed_row_height = dp(45) + (max_membres * dp(90)) + (max_membres * dp(10)) + dp(20)
        self.row_level = BoxLayout(orientation="horizontal", spacing=SPACING, size_hint=(1, None), height=computed_row_height)
        
        for g in groupes:
            group_data = next((i for i in data if i["groupe"] == g), None)
            col = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None))
            col.bind(minimum_height=col.setter("height"))
            if group_data:
                node = self.build_group_node(group_data)
                self.nodes[g] = node
                col.add_widget(node)
            col_anchor = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(1/3, 1))
            col_anchor.add_widget(col)
            self.row_level.add_widget(col_anchor)
            
        self.main_col.add_widget(self.row_level)
        
        if platform == 'android' or is_desktop_debug:
            self.main_col.add_widget(Widget(size_hint_y=None, height=dp(30)))
            
        self.main_col.bind(size=self.trigger_draw, pos=self.trigger_draw)
        self.row_level.bind(size=self.trigger_draw, pos=self.trigger_draw)

    def trigger_draw(self, *args):
        Clock.unschedule(self.draw_lines)
        Clock.schedule_once(self.draw_lines, 0.1)

    def draw_lines(self, *args):
        if not self.main_col or not self.row_level:
            return
        if self.main_col.width == 0 or self.main_col.height == 0:
            return
        self.main_col.canvas.after.clear()
        dir_node = self.nodes.get("Direction")
        bureau = self.nodes.get("Bureau")
        dirigeants = self.nodes.get("Dirigeants")
        equipe_tech = self.nodes.get("Équipe Technique")
        if not dir_node or not bureau or not dirigeants or not equipe_tech:
            return
        with self.main_col.canvas.after:
            Color(1, 1, 1, 1) 
            y_top_direction = self.main_col.height - dp(40)
            y_dir_bottom = y_top_direction - dir_node.height
            y_top_colonnes = self.row_level.y + self.row_level.height
            y_mid = y_top_colonnes + ((y_dir_bottom - y_top_colonnes) / 2)
            w_total = self.main_col.width
            center_x = w_total / 2
            cx_bureau = w_total / 6
            cx_tech = (5 * w_total) / 6  # Correction de la syntaxe de la ligne précédente
            
            Line(points=[center_x, y_dir_bottom, center_x, y_mid], width=1.5)
            Line(points=[cx_bureau, y_mid, cx_tech, y_mid], width=1.5)
            Line(points=[cx_bureau, y_mid, cx_bureau, y_top_colonnes], width=1.5)
            Line(points=[center_x, y_mid, center_x, y_top_colonnes], width=1.5)
            Line(points=[cx_tech, y_mid, cx_tech, y_top_colonnes], width=1.5)

    def build_group_node(self, group_item):
        group_name = group_item.get("groupe", "")
        membres = group_item.get("membres", [])
        if group_name == "Direction":
            node = BoxLayout(orientation="vertical", spacing=dp(15), size_hint=(1, None))
            node.bind(minimum_height=node.setter("height"))
            node.add_widget(TitleBox(group_name, size_hint=(1, None), height=dp(45)))
            president = next((m for m in membres if "président" in m.get("titre", "").lower()), None)
            autres = [m for m in membres if m != president]
            container = BoxLayout(orientation="horizontal", spacing=INNER_SPACING, size_hint=(1, None), height=dp(90))
            m1 = autres[0] if len(autres) > 0 else None
            m2 = president
            m3 = autres[1] if len(autres) > 1 else None
            for m in [m1, m2, m3]:
                if m:
                    container.add_widget(MemberBox(m, size_hint=(1/3, None), height=dp(90)))
                else:
                    container.add_widget(Widget(size_hint=(1/3, None), height=dp(90)))      
            node.add_widget(container)
            return node
        else:
            node = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(1, None))
            node.bind(minimum_height=node.setter("height"))
            node.add_widget(TitleBox(group_name, size_hint=(1, None), height=dp(45)))
            for m in membres:
                node.add_widget(MemberBox(m, size_hint=(1, None), height=dp(90)))  
                
            if group_name == "Bureau":
                comite_membres = group_item.get("comite_membres", [])
                node.add_widget(ComiteBox(comite_membres, size_hint=(1, None), height=dp(90)))
                
            # Exemple : Ajout de la box Arbitrage dans l'Équipe Technique (ou un autre groupe si vous préférez)
            if group_name == "Équipe Technique":
                arbitres_membres = group_item.get("arbitres_membres", [])
                node.add_widget(ArbitrageBox(arbitres_membres, size_hint=(1, None), height=dp(90)))
                
            return node
