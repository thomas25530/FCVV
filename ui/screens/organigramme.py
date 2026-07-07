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
import os
import hashlib
import threading
import requests
import traceback # Importé pour inspecter les coupables

FIXED_WIDTH = dp(140)
SPACING = dp(10)  
INNER_SPACING = dp(10)

class TitleBox(BoxLayout):
    def __init__(self, text, **kwargs):
        # Hauteur augmentée pour gérer deux lignes
        if 'size' not in kwargs:
            kwargs['size'] = (dp(120), dp(45)) 
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (None, None)
            
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(0.1, 0.2, 0.4, 0.9)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(5)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),
                  size=lambda i, s: setattr(self.rect, "size", s))

        # Police plus grande, text_size permet le retour à la ligne
        lbl = Label(
            text=f"[color=ffffff][b]{text}[/b][/color]",
            text_size=(self.width - dp(10), None),
            markup=True,
            font_size="13sp", 
            halign="center",
            valign="middle"
        )
        # Assurer que le texte se recalcule si la taille change
        lbl.bind(size=lambda instance, value: setattr(instance, "text_size", (self.width - dp(10), None)))
        self.add_widget(lbl)


class MemberBox(ButtonBehavior, BoxLayout):
    def __init__(self, member_data, **kwargs):
        self.member_data = member_data
        
        if 'size' not in kwargs:
            kwargs['size'] = (FIXED_WIDTH, dp(85))
        if 'size_hint' not in kwargs:
            kwargs['size_hint'] = (None, None)
            
        super().__init__(orientation="vertical", **kwargs)
        
        with self.canvas.before:
            Color(1, 1, 1, 1)  # Couleur de fond par défaut (Blanc)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(8)])
        self.bind(pos=lambda i, p: setattr(self.rect, "pos", p),
                  size=lambda i, s: setattr(self.rect, "size", s))

        # Texte principal
        txt = f"[color=1E3A8A][b]{member_data.get('titre', '')}[/b][/color]\n[color=333333]{member_data.get('nom', '')}[/color]"
        lbl = Label(
            text=txt, markup=True, font_size="12sp", halign="center", 
            valign="middle", text_size=(self.width, None)
        )
        self.bind(size=lambda instance, value: setattr(lbl, "text_size", (value[0], None)))
        self.add_widget(lbl)
        
        # Indicateur visuel "i"
        self.add_widget(Label(
            text="[color=000000]+[/color]", markup=True, font_size="20sp",
            size_hint=(None, None), size=(dp(15), dp(15)),
            pos_hint={'right': 1, 'top': 1}
        ))
        
        self.bind(on_release=self.show_contact_card)

    def on_press(self):
        # Effet visuel au clic : on change la couleur de fond
        self.canvas.before.children[0].rgba = (0.9, 0.9, 0.9, 1)

    def on_release(self):
        # Retour à la couleur d'origine
        self.canvas.before.children[0].rgba = (1, 1, 1, 1)

    def show_contact_card(self, *args):
        content = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
        
        # 1. Photo (taille fixe)
        img_widget = Image(
            source='assets/default_user.png', 
            size_hint=(1, None), 
            height=dp(130), 
            fit_mode="contain"
        )
        content.add_widget(img_widget)
        
        # 2. Gestion asynchrone... (votre code existant)
        photo_id = self.member_data.get('photo_id')
        if photo_id and photo_id.strip() != "":
            url = f"https://drive.usercontent.google.com/download?id={photo_id}&export=download"
            self.load_member_image(url, img_widget)
        
        # 3. Informations (tous avec size_hint_y=None)
        content.add_widget(Label(text=f"[color=1E3A8A][b]{self.member_data.get('titre', '')}[/b][/color]", markup=True, font_size="16sp", size_hint_y=None, height=dp(25)))
        content.add_widget(Label(text=f"[b]{self.member_data.get('nom', 'Non renseigné')}[/b]", markup=True, font_size="20sp", size_hint_y=None, height=dp(30)))
        content.add_widget(Label(text=f"Tél : {self.member_data.get('tel', 'N/A')}", size_hint_y=None, height=dp(20)))
        content.add_widget(Label(text=f"Email : {self.member_data.get('email', 'N/A')}", size_hint_y=None, height=dp(20)))
        
        content.add_widget(Label(
            text=f"Fonctions au sein du club :\n{self.member_data.get('taches', 'Aucune tâche définie')}", 
            halign="center", valign="top",
            size_hint_y=None, 
            height=dp(60) 
        ))
        
        # --- AJOUT CRUCIAL : Pousse tout le reste vers le haut ---
        content.add_widget(Widget()) 
        
        # 4. Bouton Fermer
        btn_close = Button(text="Fermer", size_hint=(1, None), height=dp(50))
        
        popup = Popup(title="Fiche Contact", content=content, size_hint=(0.8, 0.8))
        btn_close.bind(on_release=popup.dismiss)
        content.add_widget(btn_close)
        
        popup.open()

    def load_member_image(self, url, img_widget):
        """Télécharge l'image dans le dossier cache de l'app."""
        app = App.get_running_app()
        cache_dir = os.path.join(app.user_data_dir, "member_cache")
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            
        url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
        local_path = os.path.join(cache_dir, f"memb_{url_hash}.png")

        def fetch():
            # Si déjà en cache, on l'utilise
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
        
class OrganigrammeScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Initialisation explicite des attributs pour éviter les erreurs d'accès
        self.main_col = None
        self.row_level = None
        self.nodes = {}
        self.scroll = None

    def on_enter(self):      
        self.clear_widgets()
        self.nodes = {}

        self.scroll = ScrollView(
            size_hint=(1, 1), 
            do_scroll_x=False,
            do_scroll_y=True,
            bar_width = 0
        )

        self.main_col = BoxLayout(
            orientation="vertical",
            spacing=dp(60),
            padding=(dp(10), dp(40), dp(10), dp(40)),
            size_hint_y=None  
        )
        
        self.main_col.bind(minimum_height=self.main_col.setter("height"))
        
        self.scroll.add_widget(self.main_col)
        self.add_widget(self.scroll)

        data = (
            App.get_running_app()
            .app_config
            .get("fcvv", {})
            .get("appli", {})
            .get("organigramme", [])
        )

        # 1. BLOC DIRECTION
        dir_data = next((i for i in data if i["groupe"] == "Direction"), None)
        if dir_data:
            node = self.build_group_node(dir_data)
            self.nodes["Direction"] = node
            wrapper = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(1, None), height=node.height)
            wrapper.add_widget(node)
            self.main_col.add_widget(wrapper)

        # --- AJOUT DU WIDGET ESPACEUR ICI ---
        spacer = Widget(size_hint=(1, None), height=dp(40)) 
        self.main_col.add_widget(spacer)
        
        
        # 2. BLOC DES 3 COLONNES
        groupes = ["Bureau", "Dirigeants", "Équipe Technique"]
        
        # Calcul de la hauteur nécessaire pour éviter les sauts de scroll
        max_membres = 0
        for g in groupes:
            g_data = next((i for i in data if i["groupe"] == g), None)
            if g_data:
                max_membres = max(max_membres, len(g_data.get("membres", [])))
        
        # Calcul : (titre 35dp) + (nb * 75dp membres) + (nb * 15dp espacement) + padding
        computed_row_height = dp(35) + (max_membres * dp(75)) + (max_membres * dp(15)) + dp(20)

        self.row_level = BoxLayout(
            orientation="horizontal",
            spacing=SPACING,
            size_hint=(1, None),
            height=computed_row_height  # Hauteur fixe ici pour stabiliser le ScrollView
        )

        for g in groupes:
            group_data = next((i for i in data if i["groupe"] == g), None)
            col = BoxLayout(
                orientation="vertical", 
                spacing=dp(15), 
                size_hint=(None, None),
                width=FIXED_WIDTH
            )
            col.bind(minimum_height=col.setter("height"))

            if group_data:
                node = self.build_group_node(group_data)
                self.nodes[g] = node
                col.add_widget(node)

            # AnchorLayout pour forcer l'alignement en haut malgré la hauteur fixe de row_level
            col_anchor = AnchorLayout(anchor_x="center", anchor_y="top", size_hint=(1/3, 1))
            col_anchor.add_widget(col)
            self.row_level.add_widget(col_anchor)

        self.main_col.add_widget(self.row_level)

        # Binds sécurisés : on bind après que tout soit ajouté à l'arbre
        self.main_col.bind(size=self.trigger_draw, pos=self.trigger_draw)
        self.row_level.bind(size=self.trigger_draw, pos=self.trigger_draw)

    def trigger_draw(self, *args):
        Clock.unschedule(self.draw_lines)
        Clock.schedule_once(self.draw_lines, 0.1)

    def draw_lines(self, *args):
        # Protection contre les accès avant construction complète
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
            y_dir_bottom = y_top_direction - dp(125)
            y_top_colonnes = self.row_level.y + self.row_level.height
            y_mid = y_top_colonnes + ((y_dir_bottom - y_top_colonnes) / 2)

            w_total = self.main_col.width
            center_x = w_total / 2
            cx_bureau = w_total / 6
            cx_tech = 5 * w_total / 6

            Line(points=[center_x, y_dir_bottom, center_x, y_mid], width=1.5)
            Line(points=[cx_bureau, y_mid, cx_tech, y_mid], width=1.5)
            Line(points=[cx_bureau, y_mid, cx_bureau, y_top_colonnes], width=1.5)
            Line(points=[center_x, y_mid, center_x, y_top_colonnes], width=1.5)
            Line(points=[cx_tech, y_mid, cx_tech, y_top_colonnes], width=1.5)

    def build_group_node(self, group_item):
        group_name = group_item.get("groupe", "")
        membres = group_item.get("membres", [])
        
        if group_name == "Direction":
            node = BoxLayout(orientation="vertical", spacing=dp(15), size_hint=(None, None))
            node.bind(minimum_size=node.setter("size"))
            
            # Utilisation de dp(45) pour correspondre au nouveau TitleBox
            title_w = (3 * FIXED_WIDTH) + (2 * INNER_SPACING)
            node.add_widget(TitleBox(group_name, size=(title_w, dp(45))))

            president = next((m for m in membres if "président" in m.get("titre", "").lower()), None)
            autres = [m for m in membres if m != president]
            
            container = BoxLayout(orientation="horizontal", spacing=INNER_SPACING, size_hint=(None, None))
            container.bind(minimum_size=container.setter("size"))

            # On passe le dictionnaire complet 'm' à chaque MemberBox
            # Si le membre n'existe pas, on met un placeholder
            if len(autres) > 0:
                container.add_widget(MemberBox(autres[0]))
            else:
                container.add_widget(Label(size_hint=(None, None), size=(FIXED_WIDTH, dp(85))))
            
            if president:
                container.add_widget(MemberBox(president))
            else:
                container.add_widget(Label(size_hint=(None, None), size=(FIXED_WIDTH, dp(85))))
                
            if len(autres) > 1:
                container.add_widget(MemberBox(autres[1]))
            else:
                container.add_widget(Label(size_hint=(None, None), size=(FIXED_WIDTH, dp(85))))
            
            node.add_widget(container)
            return node
            
        else:
            # Groupes standards (Bureau, Dirigeants, etc.)
            node = BoxLayout(orientation="vertical", spacing=dp(10), size_hint=(None, None), width=FIXED_WIDTH)
            node.bind(minimum_height=node.setter("height"))
            
            # Utilisation de dp(45) pour le titre
            node.add_widget(TitleBox(group_name, size=(FIXED_WIDTH, dp(45))))
            
            for m in membres:
                # Passage du dictionnaire complet
                node.add_widget(MemberBox(m))
                
            return node