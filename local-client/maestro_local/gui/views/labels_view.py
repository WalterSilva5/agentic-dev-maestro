from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from maestro_local.db.models import Label, Task, get_session
from maestro_local.gui.theme import current_theme

COLOR_PALETTE = [
    "#E03131", "#E8590C", "#2F9E44", "#1971C2", "#6741D9", "#C2255C",
    "#4C6EF5", "#0CA678", "#F08C00", "#0C8599", "#66A80F", "#868E96",
]


class LabelCard(QFrame):
    def __init__(self, label_data, on_delete):
        super().__init__()
        t = current_theme()
        color = label_data["color"] or "#868E96"

        self.setStyleSheet(
            f"LabelCard {{ background: {t.bg_card}; border: 1px solid {t.border_light}; "
            f"border-left: 4px solid {color}; border-radius: 10px; }}"
            f"LabelCard:hover {{ border-color: {t.border}; }}"
        )

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(12)

        dot = QLabel()
        dot.setFixedSize(20, 20)
        dot.setStyleSheet(f"background: {color}; border-radius: 10px; border: none;")
        row.addWidget(dot)

        info = QVBoxLayout()
        info.setSpacing(2)
        name = QLabel(label_data["name"])
        name.setStyleSheet(f"font-weight: 600; font-size: 14px; color: {t.text_primary}; border: none;")
        info.addWidget(name)

        usage = QLabel(f"{label_data['task_count']} tarefas")
        usage.setStyleSheet(f"color: {t.text_muted}; font-size: 11px; border: none;")
        info.addWidget(usage)
        row.addLayout(info, 1)

        del_btn = QPushButton("Excluir")
        del_btn.setStyleSheet(
            f"background: transparent; color: {t.danger}; border: 1px solid {t.danger}; "
            f"border-radius: 4px; padding: 4px 12px; font-size: 12px;"
        )
        del_btn.setFixedHeight(28)
        del_btn.setCursor(Qt.PointingHandCursor)
        lid = label_data["id"]
        del_btn.clicked.connect(lambda: on_delete(lid))
        row.addWidget(del_btn)


class LabelsView(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Labels")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)

        subtitle = QLabel("Organize suas tarefas com labels coloridas")
        subtitle.setObjectName("subtitle")
        layout.addWidget(subtitle)

        form_frame = QFrame()
        form_frame.setProperty("class", "card")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(12)

        form_title = QLabel("Nova label")
        form_title.setProperty("class", "cardTitle")
        form_layout.addWidget(form_title)

        name_row = QHBoxLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nome da label")
        self.name_input.returnPressed.connect(self._create)
        name_row.addWidget(self.name_input, 1)
        form_layout.addLayout(name_row)

        colors_row = QHBoxLayout()
        colors_lbl = QLabel("Cor:")
        colors_lbl.setProperty("class", "sectionLabel")
        colors_row.addWidget(colors_lbl)

        self.selected_color = COLOR_PALETTE[0]
        self.color_btns = []
        for c in COLOR_PALETTE:
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(
                f"background: {c}; border-radius: 14px; border: 2px solid transparent; min-height: 0;"
            )
            btn.clicked.connect(lambda checked, color=c: self._select_color(color))
            self.color_btns.append((btn, c))
            colors_row.addWidget(btn)

        colors_row.addStretch()

        add_btn = QPushButton("Criar label")
        add_btn.setFixedHeight(32)
        add_btn.clicked.connect(self._create)
        colors_row.addWidget(add_btn)

        form_layout.addLayout(colors_row)
        layout.addWidget(form_frame)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.cards_widget)
        layout.addWidget(scroll, 1)

        self._select_color(self.selected_color)
        self.refresh()

    def _select_color(self, color):
        self.selected_color = color
        t = current_theme()
        for btn, c in self.color_btns:
            if c == color:
                btn.setStyleSheet(
                    f"background: {c}; border-radius: 14px; border: 3px solid {t.text_primary}; min-height: 0;"
                )
            else:
                btn.setStyleSheet(
                    f"background: {c}; border-radius: 14px; border: 2px solid transparent; min-height: 0;"
                )

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        s = get_session()
        try:
            labels = s.query(Label).order_by(Label.name).all()

            if not labels:
                t = current_theme()
                empty = QLabel("Nenhuma label criada")
                empty.setAlignment(Qt.AlignCenter)
                empty.setStyleSheet(f"color: {t.text_muted}; font-size: 14px; padding: 40px;")
                self.cards_layout.addWidget(empty)
            else:
                for lbl in labels:
                    task_count = len(lbl.tasks) if lbl.tasks else 0
                    data = {
                        "id": lbl.id,
                        "name": lbl.name,
                        "color": lbl.color,
                        "task_count": task_count,
                    }
                    card = LabelCard(data, self._delete)
                    self.cards_layout.addWidget(card)

            self.cards_layout.addStretch()
        finally:
            s.close()

    def _create(self):
        name = self.name_input.text().strip()
        if not name:
            return
        s = get_session()
        try:
            s.add(Label(name=name, color=self.selected_color))
            s.commit()
            self.name_input.clear()
            self.refresh()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def _delete(self, label_id):
        reply = QMessageBox.question(
            self, "Confirmar exclusao",
            "Tem certeza que deseja excluir esta label?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        s = get_session()
        try:
            lbl = s.query(Label).get(label_id)
            if lbl:
                s.delete(lbl)
                s.commit()
                self.refresh()
        finally:
            s.close()
