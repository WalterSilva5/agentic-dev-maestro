import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from maestro_local.config import load_config, save_config
from maestro_local.gui.theme import current_theme
from maestro_local.skills.catalog import CATEGORIES, SKILLS


class SkillCard(QFrame):
    def __init__(self, skill: dict, installed: bool, on_install, on_uninstall, on_preview):
        super().__init__()
        t = current_theme()
        self.setStyleSheet(
            f"SkillCard {{ background: {t.bg_card}; border: 1px solid {t.border_light}; border-radius: 10px; }}"
            f"SkillCard:hover {{ border-color: {t.border}; }}"
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        top = QHBoxLayout()
        name = QLabel(skill["name"])
        name.setStyleSheet("font-weight: 600; font-size: 14px;")
        top.addWidget(name)

        cat_label = QLabel(CATEGORIES.get(skill["category"], skill["category"]))
        cat_label.setStyleSheet(
            f"background: {t.bg_badge}; color: {t.text_muted}; "
            f"padding: 2px 8px; border-radius: 8px; font-size: 10px;"
        )
        top.addWidget(cat_label)
        top.addStretch()

        if installed:
            badge = QLabel("Instalada")
            badge.setStyleSheet(
                f"background: {t.success}; color: white; padding: 2px 8px; "
                f"border-radius: 8px; font-size: 10px; font-weight: 600;"
            )
            top.addWidget(badge)

        layout.addLayout(top)

        desc = QLabel(skill["description"])
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
        layout.addWidget(desc)

        tags_row = QHBoxLayout()
        for tag in skill.get("tags", []):
            chip = QLabel(tag)
            chip.setStyleSheet(
                f"background: {t.bg_badge}; color: {t.text_muted}; "
                f"padding: 1px 6px; border-radius: 6px; font-size: 10px;"
            )
            tags_row.addWidget(chip)
        tags_row.addStretch()
        layout.addLayout(tags_row)

        actions = QHBoxLayout()
        preview_btn = QPushButton("Ver conteudo")
        preview_btn.setProperty("flat", True)
        preview_btn.setFixedHeight(28)
        sid = skill["id"]
        preview_btn.clicked.connect(lambda: on_preview(sid))
        actions.addWidget(preview_btn)

        actions.addStretch()

        if installed:
            rm_btn = QPushButton("Desinstalar")
            rm_btn.setStyleSheet(
                f"background: transparent; color: {t.danger}; border: 1px solid {t.danger}; "
                f"border-radius: 4px; padding: 4px 12px; font-size: 12px;"
            )
            rm_btn.setFixedHeight(28)
            rm_btn.clicked.connect(lambda: on_uninstall(sid))
            actions.addWidget(rm_btn)
        else:
            inst_btn = QPushButton("Instalar")
            inst_btn.setFixedHeight(28)
            inst_btn.clicked.connect(lambda: on_install(sid))
            actions.addWidget(inst_btn)

        layout.addLayout(actions)


class SkillsView(QWidget):
    def __init__(self):
        super().__init__()
        cfg = load_config()
        self._target_dir = cfg.get("skills_target_dir")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(24, 24, 24, 24)
        main_layout.setSpacing(16)

        title = QLabel("Skills")
        title.setObjectName("sectionTitle")
        main_layout.addWidget(title)

        subtitle = QLabel(
            "Skills sao instrucoes que ensinam agentes de IA a interagir com o Maestro. "
            "Instale no diretorio .claude/skills/ do seu projeto."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("subtitle")
        main_layout.addWidget(subtitle)

        dir_row = QHBoxLayout()
        dir_label = QLabel("Diretorio destino:")
        dir_label.setStyleSheet("font-weight: 600;")
        dir_row.addWidget(dir_label)

        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("Selecione o diretorio do projeto...")
        self.dir_input.setReadOnly(True)
        if self._target_dir:
            self.dir_input.setText(self._target_dir)
        dir_row.addWidget(self.dir_input, 1)

        browse_btn = QPushButton("Selecionar")
        browse_btn.clicked.connect(self._browse_dir)
        dir_row.addWidget(browse_btn)
        main_layout.addLayout(dir_row)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Buscar skills...")
        self.search.textChanged.connect(lambda: self.refresh())
        main_layout.addWidget(self.search)

        self.preview_area = QTextEdit()
        self.preview_area.setReadOnly(True)
        self.preview_area.setVisible(False)
        self.preview_area.setMaximumHeight(200)
        self.preview_area.setStyleSheet("font-family: monospace; font-size: 12px;")

        self.preview_close = QPushButton("Fechar preview")
        self.preview_close.setProperty("flat", True)
        self.preview_close.setVisible(False)
        self.preview_close.clicked.connect(self._close_preview)

        main_layout.addWidget(self.preview_area)
        main_layout.addWidget(self.preview_close)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        self.cards_widget = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_widget)
        self.cards_layout.setSpacing(10)
        scroll.setWidget(self.cards_widget)
        main_layout.addWidget(scroll, 1)

        self.refresh()

    def _browse_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Selecionar diretorio do projeto")
        if d:
            self._target_dir = d
            self.dir_input.setText(d)
            cfg = load_config()
            cfg["skills_target_dir"] = d
            save_config(cfg)
            self.refresh()

    def _skills_dir(self):
        if not self._target_dir:
            return None
        return Path(self._target_dir) / ".claude" / "skills"

    def _is_installed(self, skill_id):
        sd = self._skills_dir()
        if not sd:
            return False
        return (sd / skill_id / "SKILL.md").exists()

    def _install(self, skill_id):
        sd = self._skills_dir()
        if not sd:
            return
        skill = next((s for s in SKILLS if s["id"] == skill_id), None)
        if not skill:
            return
        target = sd / skill["filename"]
        target.mkdir(parents=True, exist_ok=True)
        content = skill["content"]
        if "{project_dir}" in content:
            content = content.replace("{project_dir}", self._target_dir or ".")
        (target / "SKILL.md").write_text(content)
        self.refresh()

    def _uninstall(self, skill_id):
        sd = self._skills_dir()
        if not sd:
            return
        skill = next((s for s in SKILLS if s["id"] == skill_id), None)
        if not skill:
            return
        target = sd / skill["filename"] / "SKILL.md"
        if target.exists():
            target.unlink()
            parent = target.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
        self.refresh()

    def _preview(self, skill_id):
        skill = next((s for s in SKILLS if s["id"] == skill_id), None)
        if not skill:
            return
        self.preview_area.setPlainText(skill["content"])
        self.preview_area.setVisible(True)
        self.preview_close.setVisible(True)

    def _close_preview(self):
        self.preview_area.setVisible(False)
        self.preview_close.setVisible(False)

    def refresh(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        query = self.search.text().strip().lower()

        current_cat = None
        for skill in SKILLS:
            if query:
                searchable = f"{skill['name']} {skill['description']} {' '.join(skill.get('tags', []))}".lower()
                if query not in searchable:
                    continue

            if skill["category"] != current_cat:
                current_cat = skill["category"]
                t = current_theme()
                cat_header = QLabel(CATEGORIES.get(current_cat, current_cat))
                cat_header.setStyleSheet(
                    f"font-weight: 600; font-size: 13px; color: {t.text_muted}; "
                    f"padding-top: 8px; text-transform: uppercase;"
                )
                self.cards_layout.addWidget(cat_header)

            installed = self._is_installed(skill["id"])
            card = SkillCard(
                skill,
                installed,
                on_install=self._install,
                on_uninstall=self._uninstall,
                on_preview=self._preview,
            )
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()
